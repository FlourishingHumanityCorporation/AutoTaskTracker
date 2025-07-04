"""
Basic pattern matching pipeline.
"""
from typing import Dict, Any

from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.core.categorizer import ActivityCategorizer
from .base import BasePipeline


class BasicPipeline(BasePipeline):
    """Basic pattern matching pipeline using only window titles."""
    
    def __init__(self):
        super().__init__()
        self.name = "Basic Pattern Matching"
        self.description = "Original method using window title patterns and keyword matching"
        self.extractor = TaskExtractor()
    
    def process_screenshot(self, screenshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot using basic pattern matching."""
        window_title = screenshot_data.get('active_window', '')
        ocr_text = screenshot_data.get('ocr_text', '')
        
        task = self.extractor.extract_task(window_title) if window_title else "Unknown Activity"
        category = ActivityCategorizer.categorize(window_title, ocr_text)
        
        return {
            'task': task,
            'category': category,
            'confidence': 0.5,  # Fixed confidence for basic method
            'features_used': ['Window Title'],
            'details': {
                'method': 'Pattern matching on window title',
                'data_sources': ['Window title only'],
                'processing_time': 'Instant',
                'pattern_matched': bool(task != "Unknown Activity")
            }
        }