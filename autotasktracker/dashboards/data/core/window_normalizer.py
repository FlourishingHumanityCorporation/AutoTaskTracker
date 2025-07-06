"""Window title normalization for meaningful task context extraction."""

import re
import logging
from typing import Dict, Pattern

logger = logging.getLogger(__name__)


class WindowTitleNormalizer:
    """Normalizes window titles into meaningful task descriptions.
    
    Transforms generic app titles into contextual work descriptions.
    Examples:
    - "AutoTaskTracker — ✳ Project Premortem — claude" → "Project Premortem (AI Consultation)"
    - "Gmail — Inbox (5) — paul@example.com" → "Email Management"
    - "VS Code — task_board.py — AutoTaskTracker" → "Code Development (task_board.py)"
    """
    
    def __init__(self):
        """Initialize with predefined application patterns."""
        self._app_patterns = self._build_app_patterns()
    
    def _build_app_patterns(self) -> Dict[str, str]:
        """Build application pattern mapping for context extraction.
        
        Returns:
            Dictionary mapping regex patterns to replacement templates
        """
        return {
            # Development - handle both VS Code and Visual Studio Code
            r'(?:VS Code|Visual Studio Code).*?—\s*([^—]+\.(?:py|js|ts|jsx|tsx|html|css|sql|md))': r'Code Development (\1)',
            r'(?:Terminal|iTerm2?).*?—\s*([^—]+)': r'Terminal Work (\1)',
            r'Xcode.*?—\s*([^—]+)': r'iOS Development (\1)',
            
            # Communication
            r'(?:Gmail|Mail).*?(?:Inbox|Compose)': 'Email Management',
            r'Slack.*?—\s*([^—]+)': r'Team Communication (\1)',
            r'Zoom.*?—\s*([^—]+)': r'Video Meeting (\1)',
            r'Teams.*?—\s*([^—]+)': r'Team Meeting (\1)',
            
            # Productivity - handle Microsoft Office variants
            r'(?:Excel|Microsoft Excel).*?—\s*([^—]+\.xlsx?)': r'Spreadsheet Analysis (\1)',
            r'(?:Word|Microsoft Word).*?—\s*([^—]+\.docx?)': r'Document Writing (\1)',
            r'(?:PowerPoint|Microsoft PowerPoint).*?—\s*([^—]+\.pptx?)': r'Presentation Creation (\1)',
            r'Notion.*?—\s*([^—]+)': r'Documentation (\1)',
            
            # Web browsing with context
            r'(?:Chrome|Google Chrome).*?Stack Overflow': 'Research & Problem Solving',
            r'(?:Chrome|Google Chrome|Safari).*?GitHub': 'Code Repository Management',
            r'(?:Chrome|Safari).*?(?:Confluence|Jira)': 'Project Management',
            r'Safari.*?LinkedIn': 'Professional Networking',
            
            # AI Tools
            r'AutoTaskTracker.*?✳\s*([^—]+)': r'\1 (AI Consultation)',
            r'(?:ChatGPT|Claude)': 'AI Research & Development',
            
            # Design
            r'Figma.*?—\s*([^—]+)': r'Design Work (\1)',
            r'Sketch.*?—\s*([^—]+)': r'UI Design (\1)',
            
            # Database
            r'(?:MySQL|PostgreSQL|SQLite).*?—\s*([^—]+)': r'Database Management (\1)',
            r'TablePlus.*?—\s*([^—]+)': r'Database Analysis (\1)',
        }
    
    def normalize(self, window_title: str) -> str:
        """Normalize window title into meaningful task description.
        
        Args:
            window_title: Raw window title from system
            
        Returns:
            Meaningful task description for grouping
        """
        if not window_title or not window_title.strip():
            return "Unknown Activity"
        
        # Clean up session-specific noise first
        cleaned_title = self._clean_noise(window_title)
        
        # Extract meaningful task context
        task_name = self._extract_context(cleaned_title)
        
        return task_name
    
    def _clean_noise(self, title: str) -> str:
        """Remove session-specific noise from window title.
        
        Args:
            title: Raw window title
            
        Returns:
            Cleaned title with noise removed
        """
        normalized = title
        
        # Remove common session artifacts
        noise_patterns = [
            r'MallocNanoZone=\d+',                    # Memory debugging
            r'—\s*\d+×\d+$',                         # Window dimensions
            r'—\s*▸\s*\w+',                          # Terminal shell indicators
            r'\([a-f0-9]{7,}\)',                     # Git hashes
        ]
        
        for pattern in noise_patterns:
            normalized = re.sub(pattern, '', normalized)
        
        # Clean up multiple dashes and whitespace
        normalized = re.sub(r'—+', '—', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _extract_context(self, title: str) -> str:
        """Extract meaningful task context from normalized title.
        
        Args:
            title: Cleaned window title
            
        Returns:
            Meaningful task context description
        """
        # Try to match specific application patterns
        for pattern, replacement in self._app_patterns.items():
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                if '(' in replacement and '\\1' in replacement:
                    # Extract and clean captured group
                    context = match.group(1).strip()
                    context = re.sub(r'[—\-]+.*$', '', context).strip()
                    if context:
                        return replacement.replace('\\1', context)
                else:
                    return replacement
        
        # Fallback: Extract app name and main context
        return self._extract_generic_context(title)
    
    def _extract_generic_context(self, title: str) -> str:
        """Extract generic context when no specific pattern matches.
        
        Args:
            title: Window title
            
        Returns:
            Generic context description
        """
        if ' — ' not in title:
            return title
        
        parts = [p.strip() for p in title.split(' — ') if p.strip()]
        if len(parts) < 2:
            return title
        
        app_name = parts[0]
        context = parts[1]
        
        # Skip generic markers
        if context in ['✳', '✳ ', '']:
            context = parts[2] if len(parts) > 2 else app_name
        
        # Create meaningful task name based on app type
        return self._create_meaningful_name(app_name, context)
    
    def _create_meaningful_name(self, app_name: str, context: str) -> str:
        """Create meaningful name from app and context.
        
        Args:
            app_name: Application name
            context: Context information
            
        Returns:
            Meaningful task name
        """
        app_lower = app_name.lower()
        
        # Browser activities
        if app_lower in ['chrome', 'safari', 'firefox']:
            return f"Web Research ({context})"
        
        # Terminal activities
        if app_lower in ['terminal', 'iterm', 'iterm2']:
            return f"Terminal Work ({context})"
        
        # Generic formatting
        if context != app_name:
            return f"{context} ({app_name})"
        else:
            return app_name
    
    def add_custom_pattern(self, pattern: str, replacement: str) -> None:
        """Add custom application pattern for normalization.
        
        Args:
            pattern: Regex pattern to match
            replacement: Replacement template (use \\1 for captured groups)
        """
        self._app_patterns[pattern] = replacement
        logger.info(f"Added custom pattern: {pattern} -> {replacement}")
    
    def get_patterns(self) -> Dict[str, str]:
        """Get current application patterns.
        
        Returns:
            Dictionary of pattern -> replacement mappings
        """
        return self._app_patterns.copy()


# Global instance for reuse
_normalizer_instance = None


def get_window_normalizer() -> WindowTitleNormalizer:
    """Get shared window title normalizer instance.
    
    Returns:
        WindowTitleNormalizer instance
    """
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = WindowTitleNormalizer()
    return _normalizer_instance