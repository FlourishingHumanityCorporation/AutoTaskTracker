"""
Advanced task extraction module for AutoTaskTracker.
Provides intelligent extraction of task descriptions from window titles and OCR data.
"""

import re
import json
from typing import Optional, Dict, List, Tuple, Callable


class TaskExtractor:
    """Advanced task extraction with application-specific patterns."""
    
    def __init__(self):
        # Application-specific patterns
        self.app_patterns = {
            # IDEs and Editors
            'vscode': {
                'pattern': r'(.*?)\s*[—–\-]\s*(.*?)\s*[—–\-]\s*Visual Studio Code',
                'extract': lambda m: f"Edited {self._clean_project_name(m.group(1).strip())} in {m.group(2).strip()}" if m.group(1).strip() else "Coding in VS Code"
            },
            'sublime': {
                'pattern': r'(.*?)\s*[—–-]\s*Sublime Text',
                'extract': lambda m: f"Edited {m.group(1).strip()}"
            },
            'vim': {
                'pattern': r'(.*?)\s*[—–-]\s*VIM',
                'extract': lambda m: f"Edited {m.group(1).strip()} in Vim"
            },
            'pycharm': {
                'pattern': r'(.*?)\s*[—–-]\s*(.*?)\s*[—–-]\s*PyCharm',
                'extract': lambda m: f"Developed {m.group(1).strip()} in {m.group(2).strip() if m.group(2) else 'PyCharm'}"
            },
            
            # Terminals
            'terminal': {
                'pattern': r'(.*?)\s*[—–-]\s*(.*?)(?:\s*[—–-]|$)',
                'extract': self._extract_terminal_task
            },
            'iterm': {
                'pattern': r'(.*?)\s*[—–-]\s*(.*?)\s*[—–-]\s*iTerm2',
                'extract': self._extract_terminal_task
            },
            
            # Browsers
            'chrome': {
                'pattern': r'(.*?)\s*[—–-]\s*(?:Google\s*)?Chrome',
                'extract': self._extract_browser_task
            },
            'firefox': {
                'pattern': r'(.*?)\s*[—–-]\s*Mozilla Firefox',
                'extract': self._extract_browser_task
            },
            'safari': {
                'pattern': r'(.*?)\s*[—–-]\s*Safari',
                'extract': self._extract_browser_task
            },
            
            # Communication
            'slack': {
                'pattern': r'(.*?)\s*[—–-]\s*(.*?)\s*[—–-]\s*Slack',
                'extract': lambda m: f"Slack: {m.group(1).strip()}" if m.group(1) else "Using Slack"
            },
            'zoom': {
                'pattern': r'Zoom Meeting.*?(?:Meeting ID:\s*(\d+))?',
                'extract': lambda m: f"Zoom Meeting{' #' + m.group(1) if m.group(1) else ''}"
            },
            
            # Claude/AI
            'claude': {
                'pattern': r'(.*?)\s*[—–-]\s*.*?[—–-]\s*claude',
                'extract': lambda m: f"AI Coding: {self._clean_project_name(m.group(1))}"
            }
        }
        
        # Common file extensions
        self.code_extensions = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', 
            '.jsx': 'React', '.tsx': 'React TypeScript', '.java': 'Java',
            '.cpp': 'C++', '.c': 'C', '.go': 'Go', '.rs': 'Rust',
            '.rb': 'Ruby', '.php': 'PHP', '.swift': 'Swift', '.kt': 'Kotlin',
            '.cs': 'C#', '.r': 'R', '.sql': 'SQL', '.sh': 'Shell',
            '.yaml': 'YAML', '.yml': 'YAML', '.json': 'JSON', '.xml': 'XML',
            '.md': 'Markdown', '.rst': 'reStructuredText', '.txt': 'Text'
        }
        
        # Website patterns
        self.website_patterns = {
            'github.com': self._extract_github_task,
            'stackoverflow.com': self._extract_stackoverflow_task,
            'google.com/search': lambda t: f"Googled: {self._extract_search_query(t)}",
            'docs.python.org': lambda t: "Reading Python docs",
            'developer.mozilla.org': lambda t: "Reading MDN docs",
            'npmjs.com': lambda t: f"NPM: {t.split('/package/')[-1] if '/package/' in t else 'browsing packages'}",
            'pypi.org': lambda t: f"PyPI: {t.split('/project/')[-1].split('/')[0] if '/project/' in t else 'browsing packages'}",
            'medium.com': lambda t: "Reading Medium article",
            'dev.to': lambda t: "Reading dev.to article",
            'reddit.com/r/': lambda t: f"Reddit: r/{t.split('/r/')[-1].split('/')[0]}",
            'youtube.com': lambda t: "Watching YouTube",
            'localhost': self._extract_localhost_task,
        }
    
    def extract_task(self, window_title: str, ocr_text: Optional[str] = None) -> Optional[str]:
        """Extract a meaningful task from window title and optional OCR text."""
        if not window_title:
            return None
        
        # Clean the window title
        window_title = window_title.strip()
        
        # Try to parse JSON window data if provided
        if window_title.startswith('{'):
            try:
                data = json.loads(window_title)
                window_title = data.get('title', window_title)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.debug(f"Error parsing JSON window data: {e}")
        
        # Check application-specific patterns
        window_lower = window_title.lower()
        for app_key, app_info in self.app_patterns.items():
            if app_key in window_lower:
                match = re.search(app_info['pattern'], window_title, re.IGNORECASE)
                if match:
                    task = app_info['extract'](match)
                    if task and task != window_title:
                        return task
        
        # If no specific pattern matched, try generic extraction
        return self._generic_extraction(window_title, ocr_text)
    
    def _extract_terminal_task(self, match) -> str:
        """Extract task from terminal window title."""
        parts = match.groups()
        if len(parts) >= 2 and parts[1]:
            # Parse the command/directory info
            cmd_info = parts[1].strip()
            
            # Check for git commands
            if 'git' in cmd_info.lower():
                return f"Git operations in {parts[0].strip()}"
            
            # Check for specific tools
            tools = ['npm', 'yarn', 'pip', 'cargo', 'make', 'pytest', 'python']
            for tool in tools:
                if tool in cmd_info.lower():
                    return f"Running {tool} in {parts[0].strip()}"
            
            # Check for directory navigation
            if cmd_info.startswith('~') or cmd_info.startswith('/'):
                return f"Terminal: {parts[0].strip()}"
            
        return f"Terminal work: {parts[0].strip() if parts[0] else 'command line'}"
    
    def _extract_browser_task(self, match) -> str:
        """Extract task from browser window title."""
        page_title = match.group(1).strip() if match.group(1) else ""
        
        if not page_title:
            return "Web browsing"
        
        # Check for specific websites
        page_lower = page_title.lower()
        for domain, extractor in self.website_patterns.items():
            if domain in page_lower:
                return extractor(page_title)
        
        # Generic page title processing
        # Remove common suffixes
        for suffix in [' - Google Search', ' | MDN', ' - Stack Overflow', ' - YouTube']:
            page_title = page_title.replace(suffix, '')
        
        # Truncate if too long
        if len(page_title) > 60:
            page_title = page_title[:57] + "..."
        
        return f"Reading: {page_title}"
    
    def _extract_github_task(self, title: str) -> str:
        """Extract specific GitHub activity."""
        if '/pull/' in title:
            pr_match = re.search(r'#(\d+)', title)
            if pr_match:
                return f"Reviewing PR #{pr_match.group(1)}"
            return "Reviewing GitHub PR"
        elif '/issues/' in title:
            return "GitHub: Issue tracking"
        elif '/commits/' in title:
            return "GitHub: Reviewing commits"
        elif re.search(r'[\w-]+/[\w-]+', title):
            repo_match = re.search(r'([\w-]+/[\w-]+)', title)
            if repo_match:
                return f"GitHub: {repo_match.group(1)}"
        return "Browsing GitHub"
    
    def _extract_stackoverflow_task(self, title: str) -> str:
        """Extract Stack Overflow activity."""
        # Remove the site suffix
        question = title.replace(' - Stack Overflow', '').strip()
        if len(question) > 50:
            question = question[:47] + "..."
        return f"SO: {question}"
    
    def _extract_search_query(self, title: str) -> str:
        """Extract search query from Google search page."""
        # Try to extract the search query
        query_match = re.search(r'^(.*?)\s*-\s*Google Search', title)
        if query_match:
            return query_match.group(1).strip()
        return "search query"
    
    def _extract_localhost_task(self, title: str) -> str:
        """Extract task from localhost development."""
        port_match = re.search(r':(\d+)', title)
        if port_match:
            port = port_match.group(1)
            # Common port mappings
            port_apps = {
                '3000': 'React app', '4200': 'Angular app', '5000': 'Flask app',
                '8000': 'Django app', '8080': 'Web app', '8501': 'Streamlit app',
                '8502': 'Task Board', '8503': 'Analytics Dashboard', 
                '8504': 'Time Tracker', '8507': 'Task Discovery'
            }
            app_type = port_apps.get(port, f'app on :{port}')
            return f"Testing {app_type}"
        return "Local development"
    
    def _clean_project_name(self, name: str) -> str:
        """Clean up project/folder names."""
        # Remove common path indicators
        name = name.strip()
        if '/' in name:
            name = name.split('/')[-1]
        if '\\' in name:
            name = name.split('\\')[-1]
        
        # Remove file extensions for cleaner display
        for ext in self.code_extensions:
            if name.endswith(ext):
                lang = self.code_extensions[ext]
                base_name = name[:-len(ext)]
                return f"{base_name} ({lang})"
        
        return name
    
    def _generic_extraction(self, window_title: str, ocr_text: Optional[str]) -> str:
        """Fallback generic extraction when no patterns match."""
        # Try to extract the most meaningful part
        if ' - ' in window_title:
            parts = window_title.split(' - ')
            # Usually the first part is most meaningful
            return parts[0].strip()[:80]
        
        # Return truncated window title
        if len(window_title) > 60:
            return window_title[:57] + "..."
        
        return window_title

    def extract_subtasks_from_ocr(self, ocr_text: str) -> List[str]:
        """Extract potential subtasks from OCR text."""
        subtasks = []
        
        if not ocr_text:
            return subtasks
        
        try:
            ocr_data = json.loads(ocr_text) if isinstance(ocr_text, str) else ocr_text
            if isinstance(ocr_data, list):
                # Look for high-confidence text that might indicate actions
                action_keywords = [
                    'created', 'updated', 'deleted', 'modified', 'added', 'removed',
                    'fixed', 'implemented', 'refactored', 'tested', 'deployed',
                    'committed', 'pushed', 'pulled', 'merged', 'reviewed',
                    'installed', 'configured', 'debugged', 'optimized'
                ]
                
                texts = []
                for item in ocr_data:
                    if isinstance(item, dict) and 'rec_txt' in item and item.get('score', 0) > 0.8:
                        text = item['rec_txt'].strip()
                        if len(text) > 5:  # Meaningful text
                            texts.append(text)
                
                # Look for action patterns in the text
                combined = ' '.join(texts).lower()
                for keyword in action_keywords:
                    if keyword in combined:
                        # Try to extract context around the keyword
                        pattern = rf'\b\w*{keyword}\w*\s+\w+(?:\s+\w+)?'
                        matches = re.findall(pattern, combined)
                        for match in matches[:2]:  # Limit subtasks
                            subtasks.append(match.title())
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"Error extracting subtasks from VLM data: {e}")
        
        return subtasks


# Singleton instance
_task_extractor = None

def get_task_extractor() -> TaskExtractor:
    """Get the singleton TaskExtractor instance."""
    global _task_extractor
    if _task_extractor is None:
        _task_extractor = TaskExtractor()
    return _task_extractor