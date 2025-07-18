"""
Enhanced task extraction combining all AI features.
Integrates VLM, OCR enhancement, and embeddings for superior task detection.

VLM Integration Note:
- VLM data is stored with key 'minicpm_v_result' in the database
- Requires memos watch service to be running for continuous processing
- Fixed in 2025-07-03: Database queries updated to use correct VLM key
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from autotasktracker.core import TaskExtractor
from autotasktracker.ai import VLMTaskExtractor, extract_vlm_enhanced_task
from autotasktracker.ai import OCREnhancer
from autotasktracker.ai import EmbeddingsSearchEngine
from autotasktracker.core import ActivityCategorizer

logger = logging.getLogger(__name__)


class AIEnhancedTaskExtractor:
    """
    Enhanced task extractor that combines all AI features for better task detection.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize with all AI components."""
        # Base extractors
        self.base_extractor = TaskExtractor()
        self.vlm_extractor = VLMTaskExtractor()
        self.ocr_enhancer = OCREnhancer()
        
        # Embeddings for similarity
        if db_path:
            self.embeddings_engine = EmbeddingsSearchEngine(db_path)
        else:
            self.embeddings_engine = None
    
    def extract_enhanced_task(self, 
                            window_title: str = None,
                            ocr_text: str = None,
                            vlm_description: str = None,
                            entity_id: int = None) -> Dict[str, any]:
        """
        Extract task using all available AI features.
        
        Args:
            window_title: Window title text
            ocr_text: Raw OCR JSON from Pensieve
            vlm_description: VLM description if available
            entity_id: Entity ID for embedding lookups
            
        Returns:
            Enhanced task information dictionary
        """
        # Start with base extraction
        base_task = self.base_extractor.extract_task(window_title) if window_title else None
        
        # Enhance with OCR analysis
        ocr_enhancement = None
        if ocr_text:
            ocr_enhancement = self.ocr_enhancer.enhance_task_with_ocr(ocr_text, base_task)
            
            # If OCR provides high-quality task info, use it
            if ocr_enhancement and ocr_enhancement.get('ocr_quality') in ['excellent', 'good']:
                base_task = ocr_enhancement.get("tasks", base_task)
        
        # Enhance with VLM if available
        vlm_task = None
        if vlm_description:
            vlm_result = extract_vlm_enhanced_task(vlm_description, window_title, ocr_text)
            if vlm_result and vlm_result['confidence'] > 0.7:
                vlm_task = vlm_result
                
                # Use VLM task if more specific than base
                if vlm_task['task_title'] != "Activity":
                    base_task = self.vlm_extractor.enhance_task_with_vlm(
                        base_task or "Activity",
                        self.vlm_extractor.extract_from_vlm_description(vlm_description, window_title, ocr_text)
                    )
        
        # Get category
        category = ActivityCategorizer.categorize(window_title) if window_title else ActivityCategorizer.DEFAULT_CATEGORY
        
        # Find similar tasks if embeddings available
        similar_tasks = []
        if self.embeddings_engine and entity_id:
            try:
                similar = self.embeddings_engine.semantic_search(
                    entity_id, 
                    limit=3,
                    similarity_threshold=0.8,
                    time_window_hours=4
                )
                similar_tasks = [
                    {
                        "tasks": self.base_extractor.extract_task(s.get("active_window", '')),
                        'similarity': s['similarity_score'],
                        'time': s['created_at']
                    }
                    for s in similar
                ]
            except Exception as e:
                logger.error(f"Error finding similar tasks: {e}")
        
        # Combine all information
        result = {
            "tasks": base_task or "Activity Captured",
            "category": category,
            'confidence': 0.5,  # Base confidence
            'ai_features': {
                'ocr_quality': ocr_enhancement.get('ocr_quality') if ocr_enhancement else None,
                'ocr_confidence': ocr_enhancement.get('confidence') if ocr_enhancement else None,
                'has_code': ocr_enhancement.get('has_code', False) if ocr_enhancement else False,
                'vlm_available': vlm_task is not None,
                'vlm_confidence': vlm_task.get('confidence') if vlm_task else None,
                'embeddings_available': len(similar_tasks) > 0
            },
            'similar_tasks': similar_tasks
        }
        
        # Adjust confidence based on AI features
        if ocr_enhancement and ocr_enhancement.get('ocr_quality') == 'excellent':
            result['confidence'] = max(result['confidence'], 0.85)
        elif ocr_enhancement and ocr_enhancement.get('ocr_quality') == 'good':
            result['confidence'] = max(result['confidence'], 0.75)
        
        if vlm_task and vlm_task.get('confidence', 0) > 0.8:
            result['confidence'] = max(result['confidence'], vlm_task['confidence'])
            
        # Add VLM-specific insights if available
        if vlm_task:
            result['ui_state'] = vlm_task.get('ui_state')
            result['visual_context'] = vlm_task.get('visual_context')
            result['subtasks'] = vlm_task.get('subtasks', [])
        
        # Add OCR-specific insights if available
        if ocr_enhancement:
            result['title_text'] = ocr_enhancement.get('title_text')
            result['text_regions'] = ocr_enhancement.get('text_regions')
        
        return result
    
    def group_similar_tasks(self, tasks: List[Dict], similarity_threshold: float = 0.8) -> List[List[Dict]]:
        """
        Group tasks based on embedding similarity.
        
        Args:
            tasks: List of task dictionaries with entity_ids
            similarity_threshold: Minimum similarity for grouping
            
        Returns:
            List of task groups
        """
        if not self.embeddings_engine or not tasks:
            return [[t] for t in tasks]  # Each task in its own group
        
        # Use embeddings engine to find groups
        try:
            groups = self.embeddings_engine.find_similar_task_groups(
                min_group_size=2,
                similarity_threshold=similarity_threshold,
                time_window_hours=24
            )
            
            # Map back to original tasks
            grouped_tasks = []
            used_ids = set()
            
            for group in groups:
                task_group = []
                for item in group:
                    # Find matching task
                    for task in tasks:
                        if task.get('id') == item['id'] and task['id'] not in used_ids:
                            task_group.append(task)
                            used_ids.add(task['id'])
                            break
                
                if task_group:
                    grouped_tasks.append(task_group)
            
            # Add ungrouped tasks
            for task in tasks:
                if task.get('id') not in used_ids:
                    grouped_tasks.append([task])
            
            return grouped_tasks
            
        except Exception as e:
            logger.error(f"Error grouping tasks: {e}")
            return [[t] for t in tasks]
    
    def get_task_insights(self, entity_id: int) -> Dict[str, any]:
        """
        Get AI-powered insights for a specific task.
        
        Args:
            entity_id: The entity ID to analyze
            
        Returns:
            Dictionary with task insights
        """
        insights = {
            'has_similar_tasks': False,
            'task_context': [],
            'suggested_category': None,
            'confidence_factors': []
        }
        
        if not self.embeddings_engine:
            return insights
        
        try:
            # Get context (similar nearby tasks)
            context = self.embeddings_engine.get_task_context(entity_id, context_size=5)
            
            if context:
                insights['has_similar_tasks'] = True
                insights['task_context'] = [
                    {
                        "tasks": self.base_extractor.extract_task(c.get("active_window", '')),
                        'time_ago': self._time_ago(c['created_at']),
                        'similarity': c['similarity_score']
                    }
                    for c in context
                ]
                
                # Suggest category based on similar tasks
                categories = [
                    ActivityCategorizer.categorize(c.get("active_window", ''))
                    for c in context
                ]
                # Most common category
                if categories:
                    insights['suggested_category'] = max(set(categories), key=categories.count)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting task insights: {e}")
            return insights
    
    def _time_ago(self, timestamp: str) -> str:
        """Convert timestamp to human-readable time ago."""
        try:
            then = datetime.fromisoformat(timestamp)
            now = datetime.now()
            delta = now - then
            
            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}m ago"
            else:
                return "just now"
        except (ValueError, TypeError, AttributeError):
            return timestamp