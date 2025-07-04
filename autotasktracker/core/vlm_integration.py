"""
VLM (Vision Language Model) integration module for AutoTaskTracker.
Provides enhanced task extraction using visual descriptions from Pensieve's VLM plugin.
"""

import re
from typing import Optional, Dict, List, Tuple


class VLMTaskExtractor:
    """Extract meaningful tasks from VLM descriptions."""
    
    def __init__(self):
        # VLM description patterns that indicate specific activities
        self.activity_patterns = {
            # Coding activities
            'coding': {
                'keywords': ['code editor', 'programming', 'function', 'class', 'debugging', 
                           'terminal', 'console', 'syntax highlighting', 'line numbers'],
                'patterns': [
                    r'writing\s+(\w+)\s+code',
                    r'editing\s+a?\s*(\w+)\s+file',
                    r'debugging\s+(.*?)\s+in',
                    r'implementing\s+(.*?)\s+function',
                    r'reviewing\s+code\s+in\s+(.*)',
                ],
                'task_template': 'Coding: {detail}'
            },
            
            # Design activities
            'design': {
                'keywords': ['design', 'mockup', 'wireframe', 'layout', 'ui elements', 
                           'color palette', 'typography', 'components', 'prototype'],
                'patterns': [
                    r'designing\s+(.*?)\s+interface',
                    r'creating\s+(.*?)\s+mockup',
                    r'working\s+on\s+(.*?)\s+design',
                    r'prototyping\s+(.*)',
                ],
                'task_template': 'Design: {detail}'
            },
            
            # Testing activities
            'testing': {
                'keywords': ['test results', 'test output', 'passed', 'failed', 'pytest', 
                           'unit test', 'test suite', 'coverage'],
                'patterns': [
                    r'running\s+(.*?)\s+tests',
                    r'(\d+)\s+tests?\s+passed',
                    r'testing\s+(.*?)\s+functionality',
                ],
                'task_template': 'Testing: {detail}'
            },
            
            # Documentation
            'documentation': {
                'keywords': ['documentation', 'readme', 'markdown', 'writing docs', 
                           'api documentation', 'user guide'],
                'patterns': [
                    r'writing\s+(.*?)\s+documentation',
                    r'documenting\s+(.*)',
                    r'updating\s+(.*?)\s+readme',
                ],
                'task_template': 'Documentation: {detail}'
            },
            
            # Communication
            'communication': {
                'keywords': ['chat', 'message', 'email', 'slack', 'teams', 'discussing'],
                'patterns': [
                    r'chatting\s+(?:with|in)\s+(.*)',
                    r'writing\s+an?\s+email\s+(?:to|about)\s+(.*)',
                    r'discussing\s+(.*)',
                ],
                'task_template': 'Communication: {detail}'
            },
            
            # Research
            'research': {
                'keywords': ['reading', 'searching', 'browsing', 'stack overflow', 
                           'documentation page', 'tutorial', 'article'],
                'patterns': [
                    r'reading\s+about\s+(.*)',
                    r'searching\s+for\s+(.*)',
                    r'researching\s+(.*)',
                    r'looking\s+up\s+(.*)',
                ],
                'task_template': 'Research: {detail}'
            }
        }
        
        # UI state indicators
        self.ui_states = {
            'active_editing': ['cursor visible', 'text being typed', 'active text field'],
            'reviewing': ['scrolling', 'reading', 'no active cursor'],
            'debugging': ['breakpoint', 'debug panel', 'variable inspector'],
            'idle': ['screensaver', 'lock screen', 'no activity'],
        }
    
    def extract_task_from_vlm(self, vlm_description: str, 
                             window_title: Optional[str] = None,
                             ocr_text: Optional[str] = None) -> Optional[str]:
        """
        Extract a meaningful task from VLM description.
        
        Args:
            vlm_description: Description from VLM model
            window_title: Optional window title for context
            ocr_text: Optional OCR text for additional context
            
        Returns:
            Extracted task description or None
        """
        if not vlm_description:
            return None
        
        vlm_lower = vlm_description.lower()
        
        # Check each activity category
        for activity_type, config in self.activity_patterns.items():
            # Check keywords
            if any(keyword in vlm_lower for keyword in config['keywords']):
                # Try to extract specific details with patterns
                for pattern in config['patterns']:
                    match = re.search(pattern, vlm_lower)
                    if match:
                        detail = match.group(1) if match.groups() else match.group(0)
                        return config['task_template'].format(detail=detail.strip())
                
                # Generic task for this category
                return config['task_template'].format(detail=activity_type)
        
        # Check for specific UI states
        ui_state = self._detect_ui_state(vlm_description)
        if ui_state == 'idle':
            return None  # Don't create tasks for idle states
        
        # Extract action words and objects
        task = self._extract_action_and_object(vlm_description)
        if task:
            return task
        
        # Fallback: summarize the VLM description
        return self._summarize_description(vlm_description)
    
    def _detect_ui_state(self, vlm_description: str) -> Optional[str]:
        """Detect the UI state from VLM description."""
        vlm_lower = vlm_description.lower()
        
        for state, indicators in self.ui_states.items():
            if any(indicator in vlm_lower for indicator in indicators):
                return state
        
        return None
    
    def _extract_action_and_object(self, vlm_description: str) -> Optional[str]:
        """Extract action verbs and their objects from description."""
        # Common action patterns
        action_patterns = [
            r'(?:user is |person is |someone is )?(\w+ing)\s+(?:a |an |the )?(.*?)(?:\.|,|$)',
            r'shows?\s+(?:a |an |the )?(.*?)\s+being\s+(\w+ed)',
        ]
        
        vlm_lower = vlm_description.lower()
        
        for pattern in action_patterns:
            match = re.search(pattern, vlm_lower)
            if match:
                if match.groups()[0]:  # First pattern
                    action = match.group(1)
                    obj = match.group(2).strip()
                    if obj and len(obj) < 50:  # Reasonable length
                        return f"{action.capitalize()} {obj}"
                else:  # Second pattern
                    obj = match.group(1)
                    action = match.group(2)
                    if obj and len(obj) < 50:
                        return f"{action.capitalize()} {obj}"
        
        return None
    
    def _summarize_description(self, vlm_description: str) -> str:
        """Create a concise summary of the VLM description."""
        # Remove common prefixes
        prefixes_to_remove = [
            'the screenshot shows',
            'the image shows', 
            'this appears to be',
            'the screen displays',
            'a screenshot of',
        ]
        
        summary = vlm_description.lower()
        for prefix in prefixes_to_remove:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
        
        # Capitalize and truncate
        summary = summary[0].upper() + summary[1:] if summary else summary
        if len(summary) > 60:
            summary = summary[:57] + "..."
        
        return summary
    
    def enhance_task_with_vlm(self, base_task: str, vlm_description: str) -> str:
        """
        Enhance an existing task with VLM context.
        
        Args:
            base_task: Task extracted from window title/OCR
            vlm_description: VLM description
            
        Returns:
            Enhanced task description
        """
        if not vlm_description:
            return base_task
        
        # If base task is generic, try to get more specific from VLM
        generic_tasks = ['Activity Captured', 'Web browsing', 'Other', 'Working']
        if base_task in generic_tasks:
            vlm_task = self.extract_task_from_vlm(vlm_description)
            if vlm_task:
                return vlm_task
        
        # Otherwise, add context from VLM if it provides additional detail
        ui_state = self._detect_ui_state(vlm_description)
        if ui_state == 'active_editing':
            return f"{base_task} (actively editing)"
        elif ui_state == 'debugging':
            return f"{base_task} (debugging)"
        elif ui_state == 'reviewing':
            return f"{base_task} (reviewing)"
        
        return base_task
    
    def categorize_from_vlm(self, vlm_description: str) -> Optional[str]:
        """
        Determine activity category from VLM description.
        
        Returns:
            Category string with emoji prefix or None
        """
        if not vlm_description:
            return None
        
        vlm_lower = vlm_description.lower()
        
        # Category mapping
        category_indicators = {
            '🧑‍💻 Coding': ['code editor', 'programming', 'terminal', 'debugging', 'ide'],
            '🎨 Design': ['design', 'figma', 'sketch', 'mockup', 'prototype', 'ui elements'],
            '📝 Documentation': ['documentation', 'markdown', 'writing docs', 'readme'],
            '🔍 Research/Browsing': ['browser', 'searching', 'reading', 'article', 'tutorial'],
            '💬 Communication': ['chat', 'slack', 'email', 'message', 'teams'],
            '🎥 Meetings': ['video call', 'meeting', 'participants', 'screen share'],
            '📊 Data Analysis': ['spreadsheet', 'chart', 'graph', 'data', 'analytics'],
            '🧪 Testing': ['test results', 'pytest', 'unit test', 'test suite'],
        }
        
        for category, indicators in category_indicators.items():
            if any(indicator in vlm_lower for indicator in indicators):
                return category
        
        return None


# Example usage functions
def get_enhanced_task(window_title: str, ocr_text: Optional[str], 
                     vlm_description: Optional[str]) -> str:
    """
    Get enhanced task description using all available data sources.
    
    Args:
        window_title: Window title from active window
        ocr_text: OCR extracted text
        vlm_description: VLM model description
        
    Returns:
        Best possible task description
    """
    from autotasktracker.core.task_extractor import get_task_extractor
    
    # First try traditional extraction
    extractor = get_task_extractor()
    base_task = extractor.extract_task(window_title, ocr_text)
    
    # Enhance with VLM if available
    if vlm_description:
        vlm_extractor = VLMTaskExtractor()
        
        # If we have a good base task, try to enhance it
        if base_task and base_task != "Activity Captured":
            return vlm_extractor.enhance_task_with_vlm(base_task, vlm_description)
        
        # Otherwise, extract from VLM
        vlm_task = vlm_extractor.extract_task_from_vlm(vlm_description, window_title, ocr_text)
        if vlm_task:
            return vlm_task
    
    return base_task or "Activity Captured"


def get_enhanced_category(window_title: str, ocr_text: Optional[str],
                         vlm_description: Optional[str]) -> str:
    """
    Get enhanced category using VLM description.
    
    Returns:
        Category string with emoji prefix
    """
    from autotasktracker.core.categorizer import ActivityCategorizer
    
    # Try VLM categorization first if available
    if vlm_description:
        vlm_extractor = VLMTaskExtractor()
        vlm_category = vlm_extractor.categorize_from_vlm(vlm_description)
        if vlm_category:
            return vlm_category
    
    # Fall back to traditional categorization
    return ActivityCategorizer.categorize(window_title, ocr_text)