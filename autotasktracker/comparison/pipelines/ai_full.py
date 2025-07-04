"""
Full AI-enhanced pipeline.
"""
import os
import sys
from typing import Dict, Any

# Import from package structure

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.enhanced_task_extractor import AIEnhancedTaskExtractor
from autotasktracker.ai.vlm_integration import VLMTaskExtractor
from .base import BasePipeline


class AIFullPipeline(BasePipeline):
    """Full AI-enhanced pipeline with all features."""
    
    def __init__(self):
        super().__init__()
        self.name = "Full AI Enhanced"
        self.description = "Complete AI pipeline with semantic similarity and VLM analysis"
        self.db_manager = DatabaseManager()
        self.ai_extractor = AIEnhancedTaskExtractor(self.db_manager.db_path)
        self.vlm_extractor = VLMTaskExtractor()
    
    def process_screenshot(self, screenshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot using full AI enhancement."""
        window_title = screenshot_data.get('active_window', '')
        ocr_text = screenshot_data.get('ocr_text', '')
        vlm_description = screenshot_data.get('vlm_description', '')
        entity_id = screenshot_data.get('id')
        
        enhanced_result = self.ai_extractor.extract_enhanced_task(
            window_title=window_title,
            ocr_text=ocr_text,
            vlm_description=vlm_description,
            entity_id=entity_id
        )
        
        features_used = ['Window Title']
        data_sources = ['Window title']
        
        if ocr_text:
            features_used.extend(['OCR Analysis', 'Text Layout'])
            data_sources.extend(['OCR text', 'Layout analysis'])
        
        if vlm_description:
            features_used.extend(['VLM Description', 'Visual Context'])
            data_sources.extend(['Visual analysis', 'Scene understanding'])
        
        similar_tasks = enhanced_result.get('similar_tasks', [])
        if similar_tasks:
            features_used.append('Semantic Similarity')
            data_sources.append('Historical patterns')
        
        return {
            'task': enhanced_result['task'],
            'category': enhanced_result['category'],
            'confidence': enhanced_result['confidence'],
            'features_used': features_used,
            'details': {
                'method': 'Full AI enhancement',
                'similar_tasks_count': len(similar_tasks),
                'ai_features': enhanced_result.get('ai_features', {}),
                'data_sources': data_sources,
                'processing_time': 'Medium (~500ms)',
                'has_semantic_search': len(similar_tasks) > 0,
                'has_vlm_analysis': bool(vlm_description)
            }
        }