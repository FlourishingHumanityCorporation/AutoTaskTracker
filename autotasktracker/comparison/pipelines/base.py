"""
Base pipeline interface for AI comparison.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BasePipeline(ABC):
    """Base class for all processing pipelines."""
    
    def __init__(self):
        self.name = "Base Pipeline"
        self.description = "Base pipeline interface"
    
    @abstractmethod
    def process_screenshot(self, screenshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a screenshot and return task extraction results.
        
        Args:
            screenshot_data: Dictionary containing screenshot metadata
                - active_window: Window title
                - ocr_text: OCR results  
                - vlm_description: VLM analysis
                - id: Entity ID
        
        Returns:
            Dictionary containing:
                - task: Extracted task name
                - category: Task category
                - confidence: Confidence score (0-1)
                - features_used: List of features used
                - details: Additional processing details
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get pipeline information."""
        return {
            'name': self.name,
            'description': self.description
        }