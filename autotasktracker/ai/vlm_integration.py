"""
VLM (Vision Language Model) integration for enhanced task extraction.
This module provides enhanced task detection using VLM descriptions when available.
"""
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VLMEnhancedTask:
    """Enhanced task information extracted from VLM descriptions."""
    task_title: str
    category: str
    confidence: float
    ui_state: Optional[str] = None
    visual_context: Optional[str] = None
    subtasks: List[str] = None
    
    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []


class VLMTaskExtractor:
    """Extract enhanced task information from VLM descriptions."""
    
    def __init__(self):
        # Activity patterns that VLM might describe
        self.activity_patterns = {
            # Coding activities
            r'writing\s+code|coding|programming|debugging': ('Coding', 0.9),
            r'reviewing\s+code|code\s+review': ('Code Review', 0.85),
            r'running\s+tests|testing': ('Testing', 0.85),
            
            # Design activities
            r'designing|creating\s+mockup|wireframe': ('Design Work', 0.9),
            r'editing\s+image|photo\s+editing': ('Image Editing', 0.85),
            r'creating\s+presentation|slides': ('Presentation Creation', 0.85),
            
            # Communication
            r'writing\s+email|composing\s+message': ('Email/Messaging', 0.85),
            r'video\s+call|meeting|conference': ('Video Meeting', 0.9),
            r'chatting|instant\s+messaging': ('Chat Communication', 0.85),
            
            # Research
            r'reading\s+documentation|browsing\s+docs': ('Reading Documentation', 0.85),
            r'searching|googling|web\s+search': ('Web Research', 0.8),
            r'watching\s+video|tutorial': ('Learning/Tutorial', 0.85),
            
            # File management
            r'organizing\s+files|file\s+management': ('File Organization', 0.85),
            r'downloading|uploading': ('File Transfer', 0.8),
        }
        
        # UI state patterns
        self.ui_state_patterns = {
            r'empty\s+document|blank\s+page|new\s+file': 'Starting new work',
            r'multiple\s+tabs|many\s+windows': 'Multi-tasking',
            r'error\s+message|exception|stack\s+trace': 'Debugging/Error handling',
            r'terminal|command\s+line|console': 'Command line work',
            r'form|input\s+fields|data\s+entry': 'Data entry',
            r'graph|chart|visualization': 'Data analysis',
        }
        
        # Visual context indicators
        self.visual_indicators = {
            r'dark\s+theme|dark\s+mode': 'dark_theme',
            r'light\s+theme|light\s+mode': 'light_theme',
            r'split\s+screen|side\s+by\s+side': 'split_view',
            r'full\s+screen': 'fullscreen',
            r'minimized|background': 'background_task',
        }
    
    def extract_from_vlm_description(self, vlm_description: str, 
                                   window_title: str = None,
                                   ocr_text: str = None) -> VLMEnhancedTask:
        """
        Extract enhanced task information from VLM description.
        
        Args:
            vlm_description: The VLM-generated description of the screenshot
            window_title: Optional window title for additional context
            ocr_text: Optional OCR text for additional context
            
        Returns:
            VLMEnhancedTask with extracted information
        """
        if not vlm_description:
            return None
            
        vlm_lower = vlm_description.lower()
        
        # Extract primary activity
        task_title = "Activity"
        category = "Other"
        confidence = 0.5
        
        for pattern, (activity, conf) in self.activity_patterns.items():
            if re.search(pattern, vlm_lower):
                task_title = activity
                confidence = conf
                category = self._categorize_activity(activity)
                break
        
        # If no specific activity found, try to extract from description
        if task_title == "Activity" and window_title:
            task_title = self._extract_task_from_context(vlm_description, window_title)
        
        # Extract UI state
        ui_state = None
        for pattern, state in self.ui_state_patterns.items():
            if re.search(pattern, vlm_lower):
                ui_state = state
                break
        
        # Extract visual context
        visual_context = []
        for pattern, indicator in self.visual_indicators.items():
            if re.search(pattern, vlm_lower):
                visual_context.append(indicator)
        
        # Extract subtasks from VLM description
        subtasks = self._extract_subtasks_from_description(vlm_description)
        
        return VLMEnhancedTask(
            task_title=task_title,
            category=category,
            confidence=confidence,
            ui_state=ui_state,
            visual_context=', '.join(visual_context) if visual_context else None,
            subtasks=subtasks
        )
    
    def _categorize_activity(self, activity: str) -> str:
        """Categorize activity based on type."""
        activity_lower = activity.lower()
        
        if any(word in activity_lower for word in ['coding', 'debug', 'test', 'review']):
            return '💻 Coding'
        elif any(word in activity_lower for word in ['design', 'mockup', 'wireframe', 'image']):
            return '🎨 Design'
        elif any(word in activity_lower for word in ['email', 'chat', 'meeting', 'call']):
            return '💬 Communication'
        elif any(word in activity_lower for word in ['documentation', 'research', 'search', 'learning']):
            return '🔍 Research'
        elif any(word in activity_lower for word in ['file', 'organize', 'download', 'upload']):
            return '📁 File Management'
        else:
            return '📋 Other'
    
    def _extract_task_from_context(self, vlm_description: str, window_title: str) -> str:
        """Extract task from context when no specific activity pattern matches."""
        # Try to extract the main action from VLM description
        action_patterns = [
            r'user is (\w+ing)',
            r'shows? (\w+)',
            r'displaying (\w+)',
            r'contains? (\w+)',
        ]
        
        for pattern in action_patterns:
            match = re.search(pattern, vlm_description.lower())
            if match:
                action = match.group(1)
                return f"{action.capitalize()} in {window_title}"
        
        # Fallback to window title
        return f"Working in {window_title}"
    
    def _extract_subtasks_from_description(self, vlm_description: str) -> List[str]:
        """Extract potential subtasks from VLM description."""
        subtasks = []
        
        # Look for lists or multiple items mentioned
        list_patterns = [
            r'(?:shows?|displays?|contains?)\s+(?:a\s+)?list\s+of\s+(\w+)',
            r'multiple\s+(\w+)',
            r'several\s+(\w+)',
        ]
        
        for pattern in list_patterns:
            matches = re.findall(pattern, vlm_description.lower())
            for match in matches:
                subtasks.append(f"Working with {match}")
        
        # Look for specific file or item mentions
        item_patterns = [
            r'file\s+named?\s+"([^"]+)"',
            r'working\s+on\s+"([^"]+)"',
            r'editing\s+"([^"]+)"',
        ]
        
        for pattern in item_patterns:
            matches = re.findall(pattern, vlm_description, re.IGNORECASE)
            for match in matches:
                subtasks.append(f"Working on: {match}")
        
        return subtasks[:5]  # Limit to 5 subtasks
    
    def enhance_task_with_vlm(self, base_task: str, vlm_task: VLMEnhancedTask) -> str:
        """
        Enhance a base task description with VLM insights.
        
        Args:
            base_task: The original task extracted from window title/OCR
            vlm_task: The VLM-enhanced task information
            
        Returns:
            Enhanced task description
        """
        if not vlm_task or vlm_task.confidence < 0.7:
            return base_task
        
        # If VLM provides high-confidence specific activity, use it
        if vlm_task.confidence >= 0.85 and vlm_task.task_title != "Activity":
            enhanced = vlm_task.task_title
            
            # Add UI state if relevant
            if vlm_task.ui_state and vlm_task.ui_state in ['Debugging/Error handling', 'Starting new work']:
                enhanced = f"{enhanced} ({vlm_task.ui_state})"
            
            return enhanced
        
        # Otherwise, enhance the base task with VLM context
        if vlm_task.ui_state:
            return f"{base_task} - {vlm_task.ui_state}"
        
        return base_task


def extract_vlm_enhanced_task(vlm_description: str, 
                            window_title: str = None,
                            ocr_text: str = None) -> Dict[str, any]:
    """
    Convenience function to extract VLM-enhanced task information.
    
    Returns a dictionary with task information that can be easily integrated
    with existing task extraction logic.
    """
    extractor = VLMTaskExtractor()
    vlm_task = extractor.extract_from_vlm_description(vlm_description, window_title, ocr_text)
    
    if not vlm_task:
        return None
    
    return {
        'task_title': vlm_task.task_title,
        'category': vlm_task.category,
        'confidence': vlm_task.confidence,
        'ui_state': vlm_task.ui_state,
        'visual_context': vlm_task.visual_context,
        'subtasks': vlm_task.subtasks,
        'is_vlm_enhanced': True
    }