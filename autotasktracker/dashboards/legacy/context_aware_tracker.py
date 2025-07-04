#!/usr/bin/env python3
"""
Context-Aware Task Tracker

Tracks tasks based on user behavior and context, not just window titles.
Maintains task context across window switches and implements smart task boundaries.
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import hashlib

@dataclass
class Task:
    """Represents a single task with context"""
    task_id: str
    name: str
    category: str
    main_app: str
    start_time: datetime
    end_time: datetime
    context_windows: List[str] = field(default_factory=list)
    total_screenshots: int = 0
    active_duration: float = 0.0  # minutes
    context_hash: str = ""
    
    def add_context(self, window_title: str):
        """Add a window to this task's context"""
        if window_title not in self.context_windows:
            self.context_windows.append(window_title)
            
    def update_end_time(self, timestamp: datetime):
        """Update task end time and duration"""
        self.end_time = timestamp
        self.active_duration = (self.end_time - self.start_time).total_seconds() / 60

class ContextAwareTimeTracker:
    """
    Advanced time tracker that understands task context and user patterns
    """
    
    def __init__(self, 
                 context_switch_threshold_seconds=30,
                 task_return_threshold_minutes=5,
                 min_task_duration_minutes=1):
        """
        Initialize context-aware tracker
        
        Args:
            context_switch_threshold_seconds: Time before considering a true task switch
            task_return_threshold_minutes: Time window to return to previous task
            min_task_duration_minutes: Minimum duration to count as a task
        """
        self.context_threshold = context_switch_threshold_seconds
        self.return_threshold = task_return_threshold_minutes
        self.min_duration = min_task_duration_minutes
        
        # Task tracking state
        self.active_task: Optional[Task] = None
        self.recent_tasks: List[Task] = []  # Last 10 tasks for context
        self.task_stack: List[Task] = []    # Stack for task returns
        
        # Pattern recognition
        self.app_patterns = {
            'email': {
                'apps': ['mail', 'gmail', 'outlook', 'thunderbird'],
                'patterns': [r'compose', r'reply', r'forward', r'new message'],
                'context_apps': ['chrome', 'firefox', 'safari', 'finder', 'explorer']
            },
            'coding': {
                'apps': ['code', 'vscode', 'sublime', 'vim', 'pycharm', 'intellij'],
                'patterns': [r'\.py', r'\.js', r'\.tsx', r'\.java'],
                'context_apps': ['terminal', 'iterm', 'chrome', 'stackoverflow']
            },
            'document': {
                'apps': ['word', 'docs', 'pages', 'notion', 'obsidian'],
                'patterns': [r'\.docx', r'\.doc', r'\.md'],
                'context_apps': ['chrome', 'finder', 'explorer']
            },
            'communication': {
                'apps': ['slack', 'teams', 'discord', 'messages', 'whatsapp'],
                'patterns': [r'chat', r'channel', r'conversation'],
                'context_apps': []
            },
            'meeting': {
                'apps': ['zoom', 'meet', 'webex', 'teams'],
                'patterns': [r'meeting', r'call'],
                'context_apps': ['calendar', 'notes']
            }
        }
        
    def extract_task_context(self, window_title: str) -> Dict[str, str]:
        """
        Extract detailed context from window title
        
        Returns:
            Dictionary with app, document, person, project info
        """
        context = {
            'app': '',
            'document': '',
            'person': '',
            'project': '',
            'category': 'other',
            'details': ''
        }
        
        if not window_title:
            return context
            
        # Extract app name (usually after last dash or at start)
        parts = window_title.split(' - ')
        if len(parts) > 1:
            context['app'] = parts[-1].strip().lower()
            context['document'] = parts[0].strip()
        else:
            context['app'] = window_title.lower()
            
        # Detect category based on app and patterns
        for category, config in self.app_patterns.items():
            if any(app in context['app'] for app in config['apps']):
                context['category'] = category
                break
            elif any(re.search(pattern, window_title.lower()) for pattern in config['patterns']):
                context['category'] = category
                break
                
        # Extract email recipient if composing email
        if context['category'] == 'email' or 'gmail' in context['app'] or 'mail' in context['app']:
            context['category'] = 'email'
            # Look for "To: Person" or "Reply to Person" or "Compose: Subject" patterns
            compose_match = re.search(r'compose:\s*([^-]+)', window_title, re.I)
            reply_match = re.search(r'reply (?:to)?:?\s*([^-]+)', window_title, re.I)
            
            if compose_match:
                subject = compose_match.group(1).strip()
                # Try to extract person from subject
                person_match = re.search(r'(?:with|for|to)\s+(\w+)', subject, re.I)
                if person_match:
                    context['person'] = person_match.group(1)
                    context['details'] = f"Email: {subject}"
                else:
                    context['details'] = f"Email: {subject}"
                    context['document'] = subject  # Use subject as document for consistency
            elif reply_match:
                context['person'] = reply_match.group(1).strip()
                context['details'] = f"Email to {context['person']}"
            elif 'compose' in window_title.lower():
                context['details'] = "Composing new email"
                
        # Extract project/file for coding
        elif context['category'] == 'coding':
            # Extract filename
            file_match = re.search(r'([^/\\]+\.\w+)', window_title)
            if file_match:
                context['document'] = file_match.group(1)
                # Try to extract project from path
                proj_match = re.search(r'([^/\\]+)[/\\][^/\\]+\.\w+', window_title)
                if proj_match:
                    context['project'] = proj_match.group(1)
                    
        # Extract document name
        elif context['category'] == 'document':
            doc_match = re.search(r'([^/\\]+\.(?:docx?|pdf|md|txt))', window_title, re.I)
            if doc_match:
                context['document'] = doc_match.group(1)
                
        return context
        
    def should_create_new_task(self, current_context: Dict, current_window: str, previous_task: Task) -> bool:
        """
        Determine if we should create a new task or continue existing one
        
        Smart detection based on:
        1. Different main application
        2. Different document/email recipient
        3. Significant time gap
        4. Category change (unless it's a supporting app)
        """
        if not previous_task:
            return True
            
        time_gap = (datetime.now() - previous_task.end_time).total_seconds()
        
        # Always new task if too much time passed
        if time_gap > self.return_threshold * 60:
            return True
            
        # Check if returning to exact same window from task history
        if current_window in previous_task.context_windows:
            return False  # Continue the task
            
        # Extract previous context from first window (main task)
        prev_context = self.extract_task_context(previous_task.context_windows[0])
        
        # Check if this is a supporting app for the previous task
        if self.is_supporting_app(current_context, prev_context):
            return False
            
        # For emails, check if same subject/person
        if current_context['category'] == 'email' and prev_context['category'] == 'email':
            # Same email subject/document = same task
            if current_context.get('document') and current_context['document'] == prev_context.get('document'):
                return False
            # Different person = new task
            if current_context.get('person') and prev_context.get('person'):
                if current_context['person'] != prev_context['person']:
                    return True
                    
        # Different document = new task
        if current_context.get('document') and prev_context.get('document'):
            if current_context['document'] != prev_context['document']:
                return True
                
        # Category change (not to supporting app) = new task
        if current_context['category'] != prev_context['category']:
            return True
            
        return False
        
    def is_supporting_app(self, current_context: Dict, main_context: Dict) -> bool:
        """
        Check if current app is supporting the main task
        
        E.g., Chrome while writing email, Terminal while coding
        """
        main_category = main_context.get('category', '')
        current_app = current_context.get('app', '')
        
        if main_category in self.app_patterns:
            supporting_apps = self.app_patterns[main_category].get('context_apps', [])
            return any(app in current_app for app in supporting_apps)
            
        return False
        
    def find_recent_matching_task(self, context: Dict, window_title: str, timestamp: datetime) -> Optional[Task]:
        """
        Find a recent task that matches the current context
        
        Used for returning to previous tasks (e.g., back to email after research)
        """
        # First check if we're returning to exact same window
        for task in reversed(self.task_stack[-5:]):  # Check last 5 tasks
            if window_title in task.context_windows:
                time_gap = (timestamp - task.end_time).total_seconds() / 60
                if time_gap <= self.return_threshold:
                    # Remove from stack to reactivate
                    self.task_stack.remove(task)
                    return task
        
        # Then check for matching context
        for task in reversed(self.task_stack[-5:]):  # Check last 5 tasks
            task_context = self.extract_task_context(task.context_windows[0])
            
            # Same email subject
            if context.get('details') and context['details'] == task.name:
                time_gap = (timestamp - task.end_time).total_seconds() / 60
                if time_gap <= self.return_threshold:
                    self.task_stack.remove(task)
                    return task
                    
            # Same document/email
            if context.get('document') and task_context.get('document') and context['document'] == task_context['document']:
                time_gap = (timestamp - task.end_time).total_seconds() / 60
                if time_gap <= self.return_threshold:
                    self.task_stack.remove(task)
                    return task
                    
            # Same email recipient
            if context.get('person') and task_context.get('person') and context['person'] == task_context['person']:
                time_gap = (timestamp - task.end_time).total_seconds() / 60
                if time_gap <= self.return_threshold:
                    self.task_stack.remove(task)
                    return task
                    
        return None
        
    def create_task_name(self, context: Dict, window_title: str) -> str:
        """
        Create a meaningful task name from context
        """
        if context.get('details'):
            return context['details']
        elif context.get('document'):
            return f"{context['category'].title()}: {context['document']}"
        elif context.get('person'):
            return f"Email: {context['person']}"
        else:
            # Fallback to cleaned window title
            parts = window_title.split(' - ')
            return parts[0].strip() if parts else window_title
            
    def process_screenshot(self, window_title: str, timestamp: datetime) -> Task:
        """
        Process a new screenshot and update task tracking
        
        Returns the current active task
        """
        context = self.extract_task_context(window_title)
        
        # Check if we should create new task or continue existing
        if self.active_task and not self.should_create_new_task(context, window_title, self.active_task):
            # Continue existing task
            self.active_task.add_context(window_title)
            self.active_task.update_end_time(timestamp)
            self.active_task.total_screenshots += 1
            return self.active_task
            
        # Check if returning to recent task
        matching_task = self.find_recent_matching_task(context, window_title, timestamp)
        if matching_task:
            # Reactivate previous task
            self.active_task = matching_task
            self.active_task.add_context(window_title)
            self.active_task.update_end_time(timestamp)
            self.active_task.total_screenshots += 1
            return self.active_task
            
        # Create new task
        if self.active_task:
            # Save current task to stack
            self.task_stack.append(self.active_task)
            self.recent_tasks.append(self.active_task)
            if len(self.recent_tasks) > 10:
                self.recent_tasks.pop(0)
                
        # Generate unique task ID
        task_id = hashlib.md5(f"{timestamp}{window_title}".encode()).hexdigest()[:8]
        
        task_name = self.create_task_name(context, window_title)
        
        self.active_task = Task(
            task_id=task_id,
            name=task_name,
            category=context['category'],
            main_app=context['app'],
            start_time=timestamp,
            end_time=timestamp,
            context_windows=[window_title],
            total_screenshots=1
        )
        
        return self.active_task
        
    def get_completed_tasks(self, min_duration_minutes: Optional[float] = None) -> List[Task]:
        """
        Get all completed tasks that meet minimum duration
        """
        if min_duration_minutes is None:
            min_duration_minutes = self.min_duration
            
        completed = [task for task in self.recent_tasks 
                    if task.active_duration >= min_duration_minutes]
                    
        # Add current task if it meets criteria
        if self.active_task and self.active_task.active_duration >= min_duration_minutes:
            completed.append(self.active_task)
            
        return completed


def process_screenshots_with_context(screenshots_df):
    """
    Process screenshots dataframe with context-aware tracking
    
    Returns a dataframe of tasks with proper start/end times
    """
    tracker = ContextAwareTimeTracker(
        context_switch_threshold_seconds=30,
        task_return_threshold_minutes=5,
        min_task_duration_minutes=1
    )
    
    # Sort by timestamp
    screenshots_df = screenshots_df.sort_values('created_at')
    
    # Process each screenshot
    for idx, row in screenshots_df.iterrows():
        window_title = row.get('active_window', '')
        timestamp = row['created_at']
        
        tracker.process_screenshot(window_title, timestamp)
        
    # Get completed tasks
    tasks = tracker.get_completed_tasks()
    
    # Convert to dataframe
    tasks_data = []
    for task in tasks:
        tasks_data.append({
            'task_id': task.task_id,
            'task_name': task.name,
            'category': task.category,
            'main_app': task.main_app,
            'start_time': task.start_time,
            'end_time': task.end_time,
            'duration_minutes': task.active_duration,
            'screenshots': task.total_screenshots,
            'context_windows': len(task.context_windows),
            'all_windows': ', '.join(task.context_windows[:3]) + ('...' if len(task.context_windows) > 3 else '')
        })
        
    return pd.DataFrame(tasks_data)


# Example usage for testing
if __name__ == "__main__":
    # Test with sample data
    test_windows = [
        ("Gmail - Compose: Meeting tomorrow - Google Chrome", "2024-01-01 10:00:00"),
        ("Google Calendar - Chrome", "2024-01-01 10:00:30"),  # Supporting task
        ("Gmail - Compose: Meeting tomorrow - Google Chrome", "2024-01-01 10:01:00"),
        ("Gmail - Reply to: John Smith - Google Chrome", "2024-01-01 10:05:00"),  # New email task
        ("LinkedIn - Chrome", "2024-01-01 10:05:30"),  # Research for email
        ("Gmail - Reply to: John Smith - Google Chrome", "2024-01-01 10:06:00"),  # Back to email
        ("VS Code - project/main.py", "2024-01-01 10:10:00"),  # New coding task
        ("Terminal - npm run test", "2024-01-01 10:10:30"),  # Supporting coding
        ("Stack Overflow - Chrome", "2024-01-01 10:11:00"),  # Supporting coding
        ("VS Code - project/main.py", "2024-01-01 10:12:00"),  # Back to coding
    ]
    
    tracker = ContextAwareTimeTracker()
    
    for window, time_str in test_windows:
        timestamp = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        task = tracker.process_screenshot(window, timestamp)
        print(f"{time_str}: {task.name} (Task ID: {task.task_id})")
        
    print("\n\nCompleted Tasks:")
    for task in tracker.get_completed_tasks():
        print(f"- {task.name}: {task.active_duration:.1f} min ({task.total_screenshots} screenshots)")