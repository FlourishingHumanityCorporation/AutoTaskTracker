"""
Dual-Model Processor for AutoTaskTracker
Coordinates VLM (MiniCPM-V) and session reasoning (Llama3) for enhanced workflow analysis.
"""
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from autotasktracker.config import get_config
from autotasktracker.ai.vlm_processor import SmartVLMProcessor
from autotasktracker.ai.session_processor import LlamaSessionProcessor, create_session_processor
from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.error_handler import measure_latency, get_error_handler, get_metrics

logger = logging.getLogger(__name__)


@dataclass
class DualModelResult:
    """Result from dual-model processing."""
    vlm_result: Dict
    session_analysis: Optional[Dict]
    session_id: str
    processing_time: float
    success: bool
    error: Optional[str] = None


class DualModelProcessor:
    """
    Coordinates dual-model processing using VLM for screenshot analysis 
    and Llama3 for session-level workflow reasoning.
    """
    
    def __init__(self, enable_session_processing: bool = True):
        """Initialize dual-model processor."""
        self.config = get_config()
        
        # Initialize individual processors
        self.vlm_processor = SmartVLMProcessor()
        self.session_processor = create_session_processor() if enable_session_processing else None
        
        # Database connection
        self.db = DatabaseManager()
        
        # Error handling and metrics
        self.error_handler = get_error_handler()
        self.metrics = get_metrics()
        
        # Configuration
        self.enable_dual_model = self.config.ENABLE_DUAL_MODEL
        self.session_batch_size = 10  # Process sessions in batches
        self.session_timeout_minutes = 30  # Max time between screenshots in same session
        
        # Session tracking
        self.current_session_id = None
        self.session_screenshots = []
        self.last_screenshot_time = None
        
        logger.info(f"Dual-model processor initialized (dual_model_enabled: {self.enable_dual_model})")
    
    def _generate_session_id(self, timestamp: datetime = None) -> str:
        """Generate unique session identifier."""
        if timestamp is None:
            timestamp = datetime.now()
        
        return f"session_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    
    def _should_start_new_session(self, current_time: datetime) -> bool:
        """Determine if a new session should be started."""
        if self.last_screenshot_time is None:
            return True
        
        time_gap = (current_time - self.last_screenshot_time).total_seconds() / 60
        return time_gap > self.session_timeout_minutes
    
    def _save_dual_model_metadata(self, entity_id: str, vlm_result: Dict, 
                                 session_analysis: Optional[Dict], session_id: str):
        """Save dual-model results to database as metadata."""
        if not entity_id:
            logger.debug("Skipping metadata save - no entity_id provided")
            return
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use INSERT ... ON CONFLICT to handle potential duplicates
                # Save session ID
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (%s, 'session_id', %s, 'dual_model', 'text', NOW(), NOW())
                    ON CONFLICT (entity_id, key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """, (entity_id, session_id))
                
                # Save dual-model processing flag
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (%s, 'dual_model_processed', 'true', 'dual_model', 'text', NOW(), NOW())
                    ON CONFLICT (entity_id, key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """, (entity_id,))
                
                # Save dual-model version
                model_version = f"v1.0_{self.config.VLM_MODEL_NAME}_{self.config.LLAMA3_MODEL_NAME}"
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (%s, 'dual_model_version', %s, 'dual_model', 'text', NOW(), NOW())
                    ON CONFLICT (entity_id, key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """, (entity_id, model_version))
                
                # Save session analysis if available
                if session_analysis:
                    cursor.execute("""
                        INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, data_type, created_at, updated_at)
                        VALUES (%s, 'llama3_session_result', %s, 'llama3', 'json', NOW(), NOW())
                        ON CONFLICT (entity_id, key) 
                        DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """, (entity_id, json.dumps(session_analysis)))
                
                conn.commit()
                logger.debug(f"Saved dual-model metadata for entity {entity_id}")
                
        except Exception as e:
            logger.error(f"Failed to save dual-model metadata for entity {entity_id}: {e}")
            # Don't re-raise - metadata save failures shouldn't break processing
    
    def process_screenshot(self, image_path: str, window_title: str = None, 
                          entity_id: str = None, timestamp: datetime = None) -> DualModelResult:
        """
        Process a single screenshot using dual-model approach.
        
        Args:
            image_path: Path to screenshot
            window_title: Active window title
            entity_id: Database entity ID
            timestamp: Screenshot timestamp
            
        Returns:
            DualModelResult containing both VLM and session analysis
        """
        start_time = time.time()
        
        if timestamp is None:
            timestamp = datetime.now()
        
        logger.info(f"Processing screenshot with dual-model: {image_path}")
        
        try:
            # Step 1: VLM Processing (always done)
            vlm_result = self.vlm_processor.process_image(
                image_path=image_path,
                window_title=window_title,
                priority="normal",
                entity_id=entity_id
            )
            
            if not vlm_result or vlm_result == {}:
                logger.warning(f"VLM processing returned empty result for {image_path}")
                # Use a default result to maintain workflow continuity
                vlm_result = {
                    "task_type": "Unknown",
                    "confidence": 0.0,
                    "description": "VLM processing failed",
                    "window_title": window_title or "Unknown",
                    "processing_error": True
                }
            
            # Step 2: Session Management
            if self._should_start_new_session(timestamp):
                # Process accumulated session if it exists
                if self.session_screenshots and self.session_processor:
                    self._process_accumulated_session()
                
                # Start new session
                self.current_session_id = self._generate_session_id(timestamp)
                self.session_screenshots = []
                logger.info(f"Started new session: {self.current_session_id}")
            
            # Add to current session
            session_data = {
                'entity_id': entity_id,
                'image_path': image_path,
                'vlm_result': vlm_result,
                'timestamp': timestamp.isoformat(),
                'window_title': window_title
            }
            self.session_screenshots.append(session_data)
            self.last_screenshot_time = timestamp
            
            # Step 3: Session Analysis (if enabled and enough data)
            session_analysis = None
            if (self.enable_dual_model and self.session_processor and 
                len(self.session_screenshots) >= 3):  # Minimum for meaningful analysis
                
                try:
                    session_analysis = self.session_processor.analyze_session_workflow(
                        self.session_screenshots
                    )
                    
                    if session_analysis and 'error' not in session_analysis:
                        logger.info(f"Session analysis completed: {session_analysis.get('workflow_type', 'unknown')}")
                    else:
                        logger.warning("Session analysis returned error or empty result")
                        session_analysis = None
                        
                except Exception as e:
                    logger.error(f"Session analysis failed: {e}")
                    session_analysis = None
            
            # Step 4: Save dual-model metadata
            if entity_id:
                self._save_dual_model_metadata(
                    entity_id, vlm_result, session_analysis, self.current_session_id
                )
            
            processing_time = time.time() - start_time
            logger.info(f"Dual-model processing completed in {processing_time:.2f}s")
            
            return DualModelResult(
                vlm_result=vlm_result,
                session_analysis=session_analysis,
                session_id=self.current_session_id,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Dual-model processing failed: {e}")
            
            return DualModelResult(
                vlm_result=vlm_result if 'vlm_result' in locals() else {},
                session_analysis=None,
                session_id=self.current_session_id or "",
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
    
    def _process_accumulated_session(self):
        """Process accumulated screenshots for session analysis."""
        if not self.session_screenshots or not self.session_processor:
            return
        
        try:
            logger.info(f"Processing accumulated session with {len(self.session_screenshots)} screenshots")
            
            # Run comprehensive session analysis
            workflow_analysis = self.session_processor.chunk_and_summarize_workflow(
                self.session_screenshots
            )
            
            if workflow_analysis and 'error' not in workflow_analysis:
                # Save workflow analysis to database for the session
                self._save_workflow_analysis(workflow_analysis)
                logger.info("Workflow analysis saved for completed session")
            else:
                logger.warning("Workflow analysis failed for completed session")
                
        except Exception as e:
            logger.error(f"Failed to process accumulated session: {e}")
    
    def _save_workflow_analysis(self, workflow_analysis: Dict):
        """Save comprehensive workflow analysis to database."""
        try:
            # Find entities in current session to attach workflow analysis
            entity_ids = [item.get('entity_id') for item in self.session_screenshots if item.get('entity_id')]
            
            if not entity_ids:
                logger.warning("No entity IDs found for workflow analysis")
                return
            
            # Save to the most recent entity in the session
            primary_entity_id = entity_ids[-1]
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (%s, 'workflow_analysis', %s, 'dual_model', 'json', NOW(), NOW())
                    ON CONFLICT (entity_id, key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """, (primary_entity_id, json.dumps(workflow_analysis)))
                
                conn.commit()
                logger.debug(f"Saved workflow analysis for entity {primary_entity_id}")
                
        except Exception as e:
            logger.error(f"Failed to save workflow analysis: {e}")
            # Don't re-raise - workflow analysis save failures shouldn't break processing
    
    def finalize_session(self):
        """Finalize current session and process accumulated data."""
        if self.session_screenshots:
            logger.info(f"Finalizing session {self.current_session_id} with {len(self.session_screenshots)} screenshots")
            self._process_accumulated_session()
            
            # Clear session state
            self.session_screenshots = []
            self.current_session_id = None
            self.last_screenshot_time = None
    
    def get_session_status(self) -> Dict:
        """Get current session status and statistics."""
        # Get VLM processor stats if the method exists
        vlm_stats = None
        if hasattr(self.vlm_processor, 'get_processing_stats'):
            try:
                vlm_stats = self.vlm_processor.get_processing_stats()
            except Exception as e:
                logger.debug(f"Failed to get VLM stats: {e}")
        
        # Get session processor stats if available
        session_stats = None
        if self.session_processor and hasattr(self.session_processor, 'get_processing_stats'):
            try:
                session_stats = self.session_processor.get_processing_stats()
            except Exception as e:
                logger.debug(f"Failed to get session stats: {e}")
        
        return {
            'current_session_id': self.current_session_id,
            'session_screenshot_count': len(self.session_screenshots),
            'last_screenshot_time': self.last_screenshot_time.isoformat() if self.last_screenshot_time else None,
            'enable_dual_model': self.enable_dual_model,
            'session_timeout_minutes': self.session_timeout_minutes,
            'vlm_processor_stats': vlm_stats,
            'session_processor_stats': session_stats
        }
    
    def batch_process_screenshots(self, screenshot_paths: List[str], 
                                 window_titles: List[str] = None,
                                 entity_ids: List[str] = None) -> List[DualModelResult]:
        """
        Process multiple screenshots efficiently with dual-model approach.
        
        Args:
            screenshot_paths: List of screenshot file paths
            window_titles: List of window titles (optional)
            entity_ids: List of entity IDs (optional)
            
        Returns:
            List of DualModelResult objects
        """
        logger.info(f"Batch processing {len(screenshot_paths)} screenshots with dual-model")
        
        results = []
        
        # Ensure lists are same length
        if window_titles is None:
            window_titles = [None] * len(screenshot_paths)
        if entity_ids is None:
            entity_ids = [None] * len(screenshot_paths)
        
        # Process sequentially to maintain session order
        for i, (path, title, entity_id) in enumerate(zip(screenshot_paths, window_titles, entity_ids)):
            timestamp = datetime.now() + timedelta(seconds=i)  # Simulate time progression
            
            result = self.process_screenshot(
                image_path=path,
                window_title=title,
                entity_id=entity_id,
                timestamp=timestamp
            )
            
            results.append(result)
            
            if i % 10 == 0:
                logger.info(f"Batch progress: {i}/{len(screenshot_paths)}")
        
        # Finalize any remaining session
        self.finalize_session()
        
        logger.info(f"Batch processing completed: {len(results)} results")
        return results


# Convenience functions
def create_dual_model_processor(enable_session_processing: bool = True) -> DualModelProcessor:
    """Create and return a new dual-model processor instance."""
    return DualModelProcessor(enable_session_processing=enable_session_processing)


def process_screenshot_dual_model(image_path: str, window_title: str = None, 
                                 entity_id: str = None) -> DualModelResult:
    """
    Convenience function to process a single screenshot with dual-model approach.
    
    Args:
        image_path: Path to screenshot
        window_title: Active window title
        entity_id: Database entity ID
        
    Returns:
        DualModelResult containing both VLM and session analysis
    """
    processor = create_dual_model_processor()
    return processor.process_screenshot(image_path, window_title, entity_id)