"""
Text processing utilities for repository classes.

Extracted from repositories.py to improve maintainability and reusability.
"""

import re
import logging
from typing import Dict, List, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class WindowTitleNormalizer:
    """Normalizes window titles for consistent categorization."""
    
    def __init__(self):
        """Initialize normalizer with common patterns."""
        self.browser_patterns = [
            r' - Google Chrome$',
            r' - Mozilla Firefox$',
            r' - Safari$',
            r' - Microsoft Edge$',
            r' - Brave$'
        ]
        
        self.ide_patterns = [
            r' - Visual Studio Code$',
            r' - IntelliJ IDEA$',
            r' - PyCharm$',
            r' - Sublime Text$',
            r' - Atom$'
        ]
        
        self.office_patterns = [
            r' - Microsoft Word$',
            r' - Microsoft Excel$',
            r' - Microsoft PowerPoint$',
            r' - Google Docs$',
            r' - Google Sheets$'
        ]
    
    def normalize(self, window_title: str) -> str:
        """Normalize window title by removing app suffixes."""
        if not window_title:
            return "Unknown"
        
        title = window_title.strip()
        
        # Remove browser suffixes
        for pattern in self.browser_patterns:
            title = re.sub(pattern, '', title)
        
        # Remove IDE suffixes  
        for pattern in self.ide_patterns:
            title = re.sub(pattern, '', title)
        
        # Remove office app suffixes
        for pattern in self.office_patterns:
            title = re.sub(pattern, '', title)
        
        # Clean up extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Handle common file patterns
        title = self._clean_file_patterns(title)
        
        return title if title else "Unknown"
    
    def _clean_file_patterns(self, title: str) -> str:
        """Clean up common file path patterns."""
        # Remove file paths, keep just filename
        if '/' in title or '\\' in title:
            # Extract filename from path
            filename = title.split('/')[-1].split('\\')[-1]
            if filename:
                return filename
        
        # Remove file extensions for cleaner display
        title = re.sub(r'\.(txt|py|js|html|css|md|json|xml|csv)$', '', title, flags=re.IGNORECASE)
        
        return title


class TaskContextExtractor:
    """Extracts meaningful context from window titles and content."""
    
    def __init__(self):
        """Initialize context extractor."""
        self.programming_keywords = {
            'python', 'javascript', 'java', 'cpp', 'c++', 'html', 'css', 'sql',
            'bash', 'shell', 'git', 'github', 'gitlab', 'docker', 'kubernetes',
            'aws', 'azure', 'react', 'vue', 'angular', 'node', 'django', 'flask'
        }
        
        self.business_keywords = {
            'meeting', 'presentation', 'report', 'analysis', 'strategy', 'planning',
            'budget', 'finance', 'marketing', 'sales', 'customer', 'client',
            'project', 'task', 'deadline', 'milestone', 'sprint', 'agile'
        }
        
        self.research_keywords = {
            'research', 'documentation', 'tutorial', 'guide', 'learn', 'study',
            'course', 'training', 'reference', 'manual', 'wiki', 'stackoverflow',
            'blog', 'article', 'paper', 'thesis'
        }
    
    def extract_context(self, title: str) -> str:
        """Extract meaningful context from title."""
        if not title:
            return "General"
        
        title_lower = title.lower()
        
        # Check for programming context
        if any(keyword in title_lower for keyword in self.programming_keywords):
            return self._extract_programming_context(title_lower)
        
        # Check for business context
        if any(keyword in title_lower for keyword in self.business_keywords):
            return self._extract_business_context(title_lower)
        
        # Check for research/learning context
        if any(keyword in title_lower for keyword in self.research_keywords):
            return self._extract_research_context(title_lower)
        
        # Check for web browsing context
        if self._is_web_content(title):
            return self._extract_web_context(title)
        
        # Extract file type context
        file_context = self._extract_file_context(title)
        if file_context != "File":
            return file_context
        
        return "General"
    
    def _extract_programming_context(self, title_lower: str) -> str:
        """Extract programming-specific context."""
        if any(word in title_lower for word in ['test', 'testing', 'unit', 'integration']):
            return "Programming - Testing"
        elif any(word in title_lower for word in ['debug', 'error', 'fix', 'bug']):
            return "Programming - Debugging"
        elif any(word in title_lower for word in ['deploy', 'build', 'ci', 'cd']):
            return "Programming - DevOps"
        elif any(word in title_lower for word in ['review', 'pull request', 'merge']):
            return "Programming - Code Review"
        else:
            return "Programming - Development"
    
    def _extract_business_context(self, title_lower: str) -> str:
        """Extract business-specific context."""
        if any(word in title_lower for word in ['meeting', 'call', 'zoom', 'teams']):
            return "Business - Meetings"
        elif any(word in title_lower for word in ['report', 'analysis', 'dashboard']):
            return "Business - Analysis"
        elif any(word in title_lower for word in ['project', 'task', 'sprint', 'agile']):
            return "Business - Project Management"
        else:
            return "Business - General"
    
    def _extract_research_context(self, title_lower: str) -> str:
        """Extract research/learning context."""
        if any(word in title_lower for word in ['tutorial', 'guide', 'how to']):
            return "Research - Tutorial"
        elif any(word in title_lower for word in ['documentation', 'docs', 'reference']):
            return "Research - Documentation"
        elif any(word in title_lower for word in ['course', 'training', 'learn']):
            return "Research - Learning"
        else:
            return "Research - General"
    
    def _is_web_content(self, title: str) -> bool:
        """Check if title indicates web content."""
        web_indicators = [
            'http', 'www.', '.com', '.org', '.net', '.io',
            'google', 'youtube', 'github', 'stackoverflow'
        ]
        title_lower = title.lower()
        return any(indicator in title_lower for indicator in web_indicators)
    
    def _extract_web_context(self, title: str) -> str:
        """Extract web browsing context."""
        title_lower = title.lower()
        
        if any(site in title_lower for site in ['youtube', 'netflix', 'spotify']):
            return "Web - Entertainment"
        elif any(site in title_lower for site in ['google', 'search', 'stackoverflow']):
            return "Web - Search/Research"
        elif any(site in title_lower for site in ['github', 'gitlab', 'bitbucket']):
            return "Web - Development"
        elif any(site in title_lower for site in ['linkedin', 'email', 'slack']):
            return "Web - Communication"
        else:
            return "Web - Browsing"
    
    def _extract_file_context(self, title: str) -> str:
        """Extract context based on file type."""
        title_lower = title.lower()
        
        if any(ext in title_lower for ext in ['.py', '.js', '.java', '.cpp']):
            return "File - Code"
        elif any(ext in title_lower for ext in ['.txt', '.md', '.doc', '.pdf']):
            return "File - Document"
        elif any(ext in title_lower for ext in ['.xlsx', '.csv', '.json']):
            return "File - Data"
        elif any(ext in title_lower for ext in ['.png', '.jpg', '.gif', '.svg']):
            return "File - Image"
        else:
            return "File"


class ContentAnalyzer:
    """Analyzes content for categorization and insights."""
    
    def __init__(self):
        """Initialize content analyzer."""
        self.title_normalizer = WindowTitleNormalizer()
        self.context_extractor = TaskContextExtractor()
    
    def analyze_task_content(self, window_title: str, ocr_text: str = None) -> Dict[str, str]:
        """Analyze task content and return categorization."""
        # Normalize window title
        normalized_title = self.title_normalizer.normalize(window_title)
        
        # Extract context
        context = self.context_extractor.extract_context(window_title)
        
        # Analyze OCR text if available
        content_summary = self._summarize_content(ocr_text) if ocr_text else None
        
        return {
            'normalized_title': normalized_title,
            'context': context,
            'content_summary': content_summary,
            'category': self._determine_category(context, ocr_text)
        }
    
    def _summarize_content(self, ocr_text: str) -> str:
        """Create a brief summary of OCR content."""
        if not ocr_text or len(ocr_text.strip()) < 20:
            return None
        
        # Simple content summarization
        lines = ocr_text.split('\n')
        meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 5]
        
        if not meaningful_lines:
            return None
        
        # Take first few meaningful lines as summary
        summary_lines = meaningful_lines[:3]
        summary = ' | '.join(summary_lines)
        
        # Truncate if too long
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return summary
    
    def _determine_category(self, context: str, ocr_text: str = None) -> str:
        """Determine high-level category."""
        if context.startswith('Programming'):
            return 'Development'
        elif context.startswith('Business'):
            return 'Business'
        elif context.startswith('Research'):
            return 'Research'
        elif context.startswith('Web'):
            return 'Browsing'
        elif context.startswith('File'):
            return 'File Management'
        else:
            return 'General'


# Utility functions for common text operations
def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text

def extract_keywords(text: str, min_length: int = 3) -> Set[str]:
    """Extract keywords from text."""
    if not text:
        return set()
    
    # Simple keyword extraction
    words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + ',}\b', text.lower())
    
    # Filter out common stop words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'must'
    }
    
    keywords = set(word for word in words if word not in stop_words)
    return keywords

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."