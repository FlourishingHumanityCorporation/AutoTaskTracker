"""
Advanced task extraction module for AutoTaskTracker.
Provides intelligent extraction of task descriptions from window titles and OCR data.
"""

import re
import json
import logging
from typing import Optional, Dict, List, Tuple, Callable

from autotasktracker.config import get_config
from autotasktracker.core.database import DatabaseManager

logger = logging.getLogger(__name__)


class TaskExtractor:
    """Advanced task extraction with application-specific patterns."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        
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
                'pattern': r'(.*?)\s*[—–-]\s*(?:✳\s*)?(.*?)\s*[—–-]\s*claude',
                'extract': self._extract_claude_task
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
            config = get_config()
            port_apps = {
                '3000': 'React app', '4200': 'Angular app', '5000': 'Flask app',
                '8000': 'Django app', '8080': 'Web app', '8501': 'Streamlit app',
                str(config.TASK_BOARD_PORT): 'Task Board', 
                str(config.ANALYTICS_PORT): 'Analytics Dashboard', 
                str(config.TIMETRACKER_PORT): 'Time Tracker', 
                str(config.ADVANCED_ANALYTICS_PORT): 'Advanced Analytics'
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
    
    def _extract_claude_task(self, match) -> str:
        """Extract task from Claude AI window title."""
        parts = match.groups()
        if len(parts) >= 2:
            project = parts[0].strip()
            task_type = parts[1].strip()
            
            # Clean up project name
            project = self._clean_project_name(project)
            
            # If task type is meaningful, include it
            if task_type and task_type not in ['claude', 'Claude']:
                return f"{task_type}: {project}"
            else:
                return f"AI Development: {project}"
        
        return "Using Claude AI"
    
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
    
    def extract_and_store_task(self, entity_id: int, window_title: str, ocr_text: Optional[str] = None) -> Optional[str]:
        """Extract task and store it in database using DatabaseManager.
        
        Args:
            entity_id: Entity ID to store the extracted task for
            window_title: Window title to extract task from
            ocr_text: Optional OCR text for enhanced extraction
            
        Returns:
            Extracted task string or None
        """
        try:
            # Extract the task
            task = self.extract_task(window_title, ocr_text)
            
            if task:
                # Store the extracted task using DatabaseManager
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Check if task metadata already exists
                    cursor.execute(
                        "SELECT id FROM metadata_entries WHERE entity_id = ? AND key = 'tasks'",
                        (entity_id,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing task
                        cursor.execute(
                            "UPDATE metadata_entries SET value = ? WHERE entity_id = ? AND key = 'tasks'",
                            (task, entity_id)
                        )
                        logger.debug(f"Updated task for entity {entity_id}: {task}")
                    else:
                        # Insert new task metadata
                        cursor.execute(
                            """INSERT INTO metadata_entries 
                            (entity_id, key, value, source_type, source, data_type) 
                            VALUES (?, 'tasks', ?, 'task_extractor', 'realtime', 'text')""",
                            (entity_id, task)
                        )
                        logger.debug(f"Stored new task for entity {entity_id}: {task}")
                    
                    conn.commit()
                
                # Also extract and store subtasks if OCR text available
                if ocr_text:
                    subtasks = self.extract_subtasks_from_ocr(ocr_text)
                    if subtasks:
                        self._store_subtasks(entity_id, subtasks)
                
                return task
            
        except Exception as e:
            logger.error(f"Error extracting and storing task for entity {entity_id}: {e}")
        
        return None
    
    def _store_subtasks(self, entity_id: int, subtasks: List[str]) -> None:
        """Store subtasks in database."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Store subtasks as JSON array
                subtasks_json = json.dumps(subtasks)
                
                # Check if subtasks metadata already exists
                cursor.execute(
                    "SELECT id FROM metadata_entries WHERE entity_id = ? AND key = 'subtasks'",
                    (entity_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute(
                        "UPDATE metadata_entries SET value = ? WHERE entity_id = ? AND key = 'subtasks'",
                        (subtasks_json, entity_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, source, data_type) 
                        VALUES (?, 'subtasks', ?, 'task_extractor', 'realtime', 'text')""",
                        (entity_id, subtasks_json)
                    )
                
                conn.commit()
                logger.debug(f"Stored {len(subtasks)} subtasks for entity {entity_id}")
                
        except Exception as e:
            logger.error(f"Error storing subtasks for entity {entity_id}: {e}")
    
    def get_recent_tasks(self, limit: int = 100) -> List[Dict[str, any]]:
        """Get recently extracted tasks using DatabaseManager.
        
        Args:
            limit: Maximum number of tasks to retrieve
            
        Returns:
            List of task dictionaries with entity info
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get recent tasks with entity information
                cursor.execute("""
                    SELECT 
                        e.id,
                        e.created_at,
                        e.filepath,
                        m1.value as task,
                        m2.value as active_window,
                        m3.value as category,
                        m4.value as subtasks
                    FROM entities e
                    LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'tasks'
                    LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
                    LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'category'
                    LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'subtasks'
                    WHERE m1.value IS NOT NULL
                    ORDER BY e.created_at DESC
                    LIMIT ?
                """, (limit,))
                
                results = cursor.fetchall()
                
                tasks = []
                for row in results:
                    task_dict = {
                        'entity_id': row[0],
                        'created_at': row[1],
                        'filepath': row[2],
                        'task': row[3],
                        'active_window': row[4],
                        'category': row[5],
                        'subtasks': json.loads(row[6]) if row[6] else []
                    }
                    tasks.append(task_dict)
                
                logger.debug(f"Retrieved {len(tasks)} recent tasks")
                return tasks
                
        except Exception as e:
            logger.error(f"Error retrieving recent tasks: {e}")
            return []
    
    def get_task_patterns_analysis(self) -> Dict[str, any]:
        """Analyze task patterns using DatabaseManager to identify common activities.
        
        Returns:
            Dictionary with pattern analysis results
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all tasks for pattern analysis
                cursor.execute("""
                    SELECT 
                        m1.value as task,
                        m2.value as active_window,
                        COUNT(*) as frequency
                    FROM metadata_entries m1
                    LEFT JOIN metadata_entries m2 ON m1.entity_id = m2.entity_id AND m2.key = 'active_window'
                    WHERE m1.key = 'tasks' AND m1.value IS NOT NULL
                    GROUP BY m1.value, m2.value
                    ORDER BY frequency DESC
                    LIMIT 50
                """)
                
                results = cursor.fetchall()
                
                # Analyze patterns
                app_patterns = {}
                task_frequency = {}
                
                for task, window, frequency in results:
                    task_frequency[task] = task_frequency.get(task, 0) + frequency
                    
                    # Extract app from window title
                    if window:
                        app = window.split(' — ')[-1] if ' — ' in window else window.split(' - ')[-1] if ' - ' in window else window
                        app = app.split()[0]  # First word usually the app
                        
                        if app not in app_patterns:
                            app_patterns[app] = []
                        app_patterns[app].append((task, frequency))
                
                # Sort patterns by frequency
                for app in app_patterns:
                    app_patterns[app] = sorted(app_patterns[app], key=lambda x: x[1], reverse=True)[:10]
                
                top_tasks = sorted(task_frequency.items(), key=lambda x: x[1], reverse=True)[:20]
                
                analysis = {
                    'total_unique_tasks': len(task_frequency),
                    'top_tasks': top_tasks,
                    'app_patterns': app_patterns,
                    'most_active_app': max(app_patterns.keys(), key=lambda x: sum(freq for _, freq in app_patterns[x])) if app_patterns else None
                }
                
                logger.debug(f"Analyzed {len(results)} task patterns")
                return analysis
                
        except Exception as e:
            logger.error(f"Error analyzing task patterns: {e}")
            return {
                'total_unique_tasks': 0,
                'top_tasks': [],
                'app_patterns': {},
                'most_active_app': None
            }


# Singleton instance
_task_extractor = None

def get_task_extractor() -> TaskExtractor:
    """Get the singleton TaskExtractor instance."""
    global _task_extractor
    if _task_extractor is None:
        _task_extractor = TaskExtractor()
    return _task_extractor