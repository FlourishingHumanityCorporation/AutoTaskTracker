"""
OCR-enhanced pipeline.
"""
import os
import sys
from typing import Dict, Any

# Import from package structure

from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.core.categorizer import ActivityCategorizer
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from .base import BasePipeline


class OCRPipeline(BasePipeline):
    """OCR-enhanced pipeline with text analysis and confidence scoring."""
    
    def __init__(self):
        super().__init__()
        self.name = "OCR Enhanced"
        self.description = "Enhanced with OCR text analysis and confidence scoring"
        self.extractor = TaskExtractor()
        self.ocr_enhancer = OCREnhancer()
    
    def process_screenshot(self, screenshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot using OCR enhancement."""
        window_title = screenshot_data.get('active_window', '')
        ocr_text = screenshot_data.get("ocr_result", '')
        
        basic_task = self.extractor.extract_task(window_title) if window_title else "Unknown Activity"
        category = ActivityCategorizer.categorize(window_title, ocr_text)
        
        if ocr_text:
            ocr_enhancement = self.ocr_enhancer.enhance_task_with_ocr(ocr_text, basic_task)
            task = ocr_enhancement.get("tasks", basic_task)
            confidence = ocr_enhancement.get('confidence', 0.5)
            ocr_quality = ocr_enhancement.get('ocr_quality', 'unknown')
            features_used = ['Window Title', 'OCR Text', 'Layout Analysis']
            
            details = {
                'method': 'OCR-enhanced analysis',
                'ocr_quality': ocr_quality,
                'text_regions': ocr_enhancement.get('text_regions', {}),
                'data_sources': ['Window title', 'OCR text', 'Layout analysis'],
                'processing_time': 'Fast (~100ms)',
                'enhancement_applied': True
            }
        else:
            task = basic_task
            confidence = 0.3
            features_used = ['Window Title']
            details = {
                'method': 'Fallback to basic (no OCR)',
                'ocr_quality': 'no_text',
                'data_sources': ['Window title only'],
                'processing_time': 'Instant',
                'enhancement_applied': False
            }
        
        return {
            "tasks": task,
            'category': category,
            'confidence': confidence,
            'features_used': features_used,
            'details': details
        }