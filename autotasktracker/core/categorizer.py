"""
Activity categorization module for AutoTaskTracker.
Provides centralized logic for categorizing activities based on window titles and OCR content.
"""

import json
from typing import Optional, Dict, List, Tuple

# DatabaseManager import removed - not used in this module


class ActivityCategorizer:
    """Categorizes activities based on window titles and OCR content."""
    
    # Category definitions with keywords
    CATEGORIES: Dict[str, Tuple[str, List[str]]] = {
        'coding': (
            '🧑‍💻 Coding',
            ['code', 'vscode', 'vim', 'emacs', 'sublime', 'atom', 'pycharm', 
             'intellij', 'terminal', 'iterm', 'jupyter', 'notebook', 'git',
             'claude', 'copilot', 'localhost', 'python', 'node', 'npm', 
             '.py', '.js', '.ts', '.java', '.cpp', 'development', 'debugging']
        ),
        'communication': (
            '💬 Communication',
            ['mail', 'gmail', 'outlook', 'slack', 'teams', 'discord', 'chat', 
             'messages', 'telegram', 'whatsapp', 'signal']
        ),
        'research': (
            '🔍 Research/Browsing',
            ['chrome', 'firefox', 'safari', 'edge', 'browser', 'google', 
             'stack overflow', 'github', 'stackoverflow', 'wikipedia']
        ),
        'documentation': (
            '📝 Documentation',
            ['word', 'docs', 'pages', 'notion', 'obsidian', 'readme', 'markdown',
             'confluence', 'wiki', 'onenote', 'evernote']
        ),
        'meetings': (
            '🎥 Meetings',
            ['zoom', 'meet', 'webex', 'skype', 'hangouts', 'bluejeans', 'gotomeeting']
        ),
        'design': (
            '🎨 Design',
            ['figma', 'sketch', 'photoshop', 'illustrator', 'canva', 'miro', 'excalidraw']
        ),
        'data': (
            '📊 Data Analysis',
            ['excel', 'sheets', 'tableau', 'powerbi', 'jupyter', 'rstudio', 'spss']
        ),
        'entertainment': (
            '🎮 Entertainment',
            ['youtube', 'netflix', 'spotify', 'twitch', 'steam', 'epic games']
        ),
        'ai_tools': (
            '🤖 AI Tools',
            ['chatgpt', 'claude', 'copilot', 'bard', 'gemini', 'midjourney', 
             'stable diffusion', 'dall-e', 'openai', 'anthropic']
        )
    }
    
    DEFAULT_CATEGORY = '📋 Other'
    
    @classmethod
    def categorize(cls, window_title: Optional[str], ocr_text: Optional[str] = None) -> str:
        """
        Categorize activity based on window title and optionally OCR content.
        
        Args:
            window_title: The window title to categorize
            ocr_text: Optional OCR text for additional context
            
        Returns:
            Category string with emoji prefix
        """
        if not window_title:
            return cls.DEFAULT_CATEGORY
        
        window_lower = window_title.lower()
        
        # Priority order for overlapping keywords
        # Check coding indicators first (more specific patterns)
        if any(ext in window_lower for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs']):
            return cls.CATEGORIES['coding'][0]
        
        # Check for development/localhost
        if 'localhost' in window_lower or 'development' in window_lower:
            return cls.CATEGORIES['coding'][0]
        
        # Check for specific AI tool usage in coding context
        if any(ai_tool in window_lower for ai_tool in ['claude', 'copilot', 'chatgpt']):
            # If it has coding-related terms, categorize as coding
            if any(term in window_lower for term in ['python', 'code', 'script', 'function', 'class', 'debug']):
                return cls.CATEGORIES['coding'][0]
            # Otherwise it's AI tools
            return cls.CATEGORIES['ai_tools'][0]
        
        # Check each category
        for category_key, (category_label, keywords) in cls.CATEGORIES.items():
            if any(keyword in window_lower for keyword in keywords):
                return category_label
        
        return cls.DEFAULT_CATEGORY
    
    @classmethod
    def get_category_keywords(cls, category: str) -> List[str]:
        """Get keywords for a specific category."""
        for cat_key, (cat_label, keywords) in cls.CATEGORIES.items():
            if cat_label == category or cat_key == category:
                return keywords
        return []
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Get all available category labels."""
        categories = [label for _, (label, _) in cls.CATEGORIES.items()]
        categories.append(cls.DEFAULT_CATEGORY)
        return categories


def extract_window_title(active_window_data: str) -> Optional[str]:
    """
    Extract window title from active window data.
    
    Args:
        active_window_data: JSON string or dict containing window information
        
    Returns:
        Extracted window title or None
    """
    if not active_window_data:
        return None
    
    try:
        # Handle JSON string
        if isinstance(active_window_data, str):
            window_data = json.loads(active_window_data)
        else:
            window_data = active_window_data
        
        # Extract title from dict
        if isinstance(window_data, dict) and 'title' in window_data:
            return window_data['title']
        
        # Fallback to string representation
        return str(active_window_data)
    except (json.JSONDecodeError, TypeError):
        # If not valid JSON, return as string
        return str(active_window_data)


def extract_task_summary(ocr_text: Optional[str], active_window: Optional[str]) -> str:
    """
    Extract a meaningful task description from OCR text and window title.
    
    Args:
        ocr_text: OCR text data (JSON or string)
        active_window: Active window data (JSON or string)
        
    Returns:
        Task summary string
    """
    # Import task extractor
    try:
        from autotasktracker.core.task_extractor import get_task_extractor
        extractor = get_task_extractor()
        
        # First try to get window title
        window_title = extract_window_title(active_window)
        
        # Use advanced task extraction
        if window_title:
            task = extractor.extract_task(window_title, ocr_text)
            if task:
                return task
    except ImportError:
        # If task extractor not available, use basic extraction
        window_title = extract_window_title(active_window)
        if window_title:
            return window_title
    
    # Try to extract meaningful text from OCR
    if ocr_text:
        try:
            # Handle JSON OCR data
            if isinstance(ocr_text, str) and ocr_text.startswith('['):
                ocr_data = json.loads(ocr_text)
                if isinstance(ocr_data, list) and ocr_data:
                    # Extract high-confidence text
                    text_parts = []
                    for item in ocr_data[:10]:  # First 10 items
                        if isinstance(item, list) and len(item) >= 2:
                            bbox, text = item[0], item[1]
                            if isinstance(text, tuple) and len(text) >= 2:
                                text_content, confidence = text[0], text[1]
                                if confidence > 0.8 and text_content.strip():
                                    text_parts.append(text_content.strip())
                    
                    if text_parts:
                        combined_text = ' '.join(text_parts)
                        return combined_text[:100] + "..." if len(combined_text) > 100 else combined_text
            
            # Fallback to simple text handling
            first_line = str(ocr_text).split('\n')[0].strip()
            if first_line:
                return first_line[:100] + "..." if len(first_line) > 100 else first_line
                
        except (json.JSONDecodeError, TypeError, IndexError) as e:
            logger.debug(f"Error parsing VLM results for task description: {e}")
    
    return "Activity Captured"


# Convenience function for backward compatibility
def categorize_activity(window_title: Optional[str], ocr_text: Optional[str] = None) -> str:
    """Legacy function name for categorization."""
    return ActivityCategorizer.categorize(window_title, ocr_text)