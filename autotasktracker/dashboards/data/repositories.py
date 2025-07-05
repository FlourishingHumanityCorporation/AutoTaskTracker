"""Data repositories for dashboard data access."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from collections import defaultdict
import re

from ...core.database import DatabaseManager
from ...core.categorizer import extract_window_title
from ...pensieve.postgresql_adapter import get_postgresql_adapter, PostgreSQLAdapter
from .models import Task, Activity, TaskGroup, DailyMetrics

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, use_pensieve: bool = True):
        self.db = db_manager or DatabaseManager()
        self.use_pensieve = use_pensieve
        self.pg_adapter = get_postgresql_adapter() if use_pensieve else None
        
    def _execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute query with error handling."""
        try:
            # Use the DatabaseManager's connection context manager
            with self.db.get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return pd.DataFrame()
    
            

class TaskRepository(BaseRepository):
    """Repository for task-related data access."""
    
    def get_tasks_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime,
        categories: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Task]:
        """Get tasks for a specific time period.
        
        Args:
            start_date: Start of period
            end_date: End of period  
            categories: Optional category filter
            limit: Maximum results
            
        Returns:
            List of Task objects
        """
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, categories, limit)
                return self._convert_task_dicts_to_objects(task_dicts)
            except Exception as e:
                logger.warning(f"PostgreSQL adapter failed, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        return self._get_tasks_sqlite_fallback(start_date, end_date, categories, limit)
    
    def _get_tasks_sqlite_fallback(
        self, 
        start_date: datetime, 
        end_date: datetime,
        categories: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Task]:
        """Fallback SQLite implementation."""
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.filepath,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'ocr_result'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        WHERE e.created_at >= ? AND e.created_at <= ?
        """
        
        # Convert local time range to UTC for database query (Pensieve stores UTC)
        from ...core.timezone_manager import get_timezone_manager
        
        tz_manager = get_timezone_manager()
        utc_start, utc_end = tz_manager.convert_query_range(start_date, end_date)
        
        params = [
            utc_start.strftime('%Y-%m-%d %H:%M:%S'),
            utc_end.strftime('%Y-%m-%d %H:%M:%S')
        ]
        
        if categories:
            placeholders = ','.join(['?' for _ in categories])
            query += f" AND m4.value IN ({placeholders})"
            params.extend(categories)
            
        query += " ORDER BY e.created_at DESC LIMIT ?"
        params.append(limit)
        
        df = self._execute_query(query, tuple(params))
        
        tasks = []
        for _, row in df.iterrows():
            # Use extracted task if available, fallback to window title
            window_title = extract_window_title(row.get('active_window', '')) or row.get("active_window", 'Unknown')
            task_title = row.get('tasks') or window_title
            
            # Convert UTC timestamp from database to local time for display
            utc_timestamp = pd.to_datetime(row['created_at'])
            local_timestamp = tz_manager.utc_to_local(utc_timestamp)
            
            task = Task(
                id=row['id'],
                title=task_title,
                category=row.get('category', 'Other'),
                timestamp=local_timestamp,
                duration_minutes=5,  # Default 5 min per capture
                window_title=window_title,
                ocr_text=row.get("ocr_text"),
                screenshot_path=row.get('filepath')
            )
            tasks.append(task)
            
        return tasks
    
    def _convert_task_dicts_to_objects(self, task_dicts: List[Dict[str, Any]]) -> List[Task]:
        """Convert PostgreSQL adapter results to Task objects."""
        from ...core.timezone_manager import get_timezone_manager
        tz_manager = get_timezone_manager()
        
        tasks = []
        for task_dict in task_dicts:
            # Extract task title from tasks array or use window title
            task_title = task_dict.get('window_title', 'Unknown')
            if task_dict.get('tasks'):
                # Use first task title if available
                first_task = task_dict['tasks'][0] if isinstance(task_dict['tasks'], list) else task_dict['tasks']
                if isinstance(first_task, dict) and 'title' in first_task:
                    task_title = first_task['title']
                elif isinstance(first_task, str):
                    task_title = first_task
            
            # Extract window title
            window_title = extract_window_title(task_dict.get('window_title', '')) or task_dict.get('window_title', 'Unknown')
            
            # Handle timestamp conversion
            timestamp = task_dict.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            if timestamp and hasattr(timestamp, 'tz_localize'):
                # Convert UTC to local time for display
                local_timestamp = tz_manager.utc_to_local(timestamp)
            else:
                local_timestamp = timestamp or datetime.now()
            
            task = Task(
                id=task_dict.get('id'),
                title=task_title,
                category=task_dict.get('category', 'Other'),
                timestamp=local_timestamp,
                duration_minutes=5,  # Default 5 min per capture
                window_title=window_title,
                ocr_text=task_dict.get('ocr_text'),
                screenshot_path=task_dict.get('filepath')
            )
            tasks.append(task)
            
        return tasks
        
    def _normalize_window_title(self, window_title: str) -> str:
        """Normalize window title for better task context extraction.
        
        Transforms generic app titles into meaningful work descriptions.
        Examples:
        - "AutoTaskTracker — ✳ Project Premortem — claude" → "Project Premortem (AI Consultation)"
        - "Gmail — Inbox (5) — paul@example.com" → "Email Management"
        - "VS Code — task_board.py — AutoTaskTracker" → "Code Development (task_board.py)"
        
        Args:
            window_title: Raw window title
            
        Returns:
            Meaningful task description for grouping
        """
        if not window_title:
            return "Unknown Activity"
            
        # Clean up session-specific noise first
        normalized = window_title
        normalized = re.sub(r'MallocNanoZone=\d+', '', normalized)
        normalized = re.sub(r'—\s*\d+×\d+$', '', normalized)
        normalized = re.sub(r'—\s*▸\s*\w+', '', normalized)  # Remove terminal shell indicators
        normalized = re.sub(r'\([a-f0-9]{7,}\)', '', normalized)  # Remove git hashes
        normalized = re.sub(r'—+', '—', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Extract meaningful task context
        task_name = self._extract_task_context(normalized)
        
        return task_name
    
    def _extract_task_context(self, title: str) -> str:
        """Extract meaningful task context from a normalized window title.
        
        Uses pattern matching to identify work activities and create
        human-readable task descriptions.
        """
        # Common application patterns and their work context
        app_patterns = {
            # Development
            r'VS Code.*?([^—]+\.(?:py|js|ts|jsx|tsx|html|css|sql|md))': r'Code Development (\1)',
            r'Terminal.*?([^—]+)': r'Terminal Work (\1)',
            r'Xcode.*?([^—]+)': r'iOS Development (\1)',
            
            # Communication
            r'Gmail|Mail.*?(?:Inbox|Compose)': 'Email Management',
            r'Slack.*?([^—]+)': r'Team Communication (\1)',
            r'Zoom.*?([^—]+)': r'Video Meeting (\1)',
            r'Teams.*?([^—]+)': r'Team Meeting (\1)',
            
            # Productivity
            r'Excel.*?([^—]+\.xlsx?)': r'Spreadsheet Analysis (\1)',
            r'Word.*?([^—]+\.docx?)': r'Document Writing (\1)',
            r'PowerPoint.*?([^—]+\.pptx?)': r'Presentation Creation (\1)',
            r'Notion.*?([^—]+)': r'Documentation (\1)',
            
            # Web browsing with context
            r'Chrome.*?Stack Overflow': 'Research & Problem Solving',
            r'Chrome.*?GitHub': 'Code Repository Management',
            r'Chrome.*?Confluence|Jira': 'Project Management',
            r'Safari.*?LinkedIn': 'Professional Networking',
            
            # AI Tools
            r'AutoTaskTracker.*?✳\s*([^—]+)': r'\1 (AI Consultation)',
            r'ChatGPT|Claude': 'AI Research & Development',
            
            # Design
            r'Figma.*?([^—]+)': r'Design Work (\1)',
            r'Sketch.*?([^—]+)': r'UI Design (\1)',
            
            # Database
            r'(?:MySQL|PostgreSQL|SQLite).*?([^—]+)': r'Database Management (\1)',
            r'TablePlus.*?([^—]+)': r'Database Analysis (\1)',
        }
        
        # Try to match specific patterns
        for pattern, replacement in app_patterns.items():
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                if '(' in replacement and '\\1' in replacement:
                    # Extract the captured group
                    context = match.group(1).strip()
                    # Clean up context
                    context = re.sub(r'[—\-]+.*$', '', context).strip()
                    if context:
                        return replacement.replace('\\1', context)
                else:
                    return replacement
        
        # Fallback: Extract app name and main context
        if ' — ' in title:
            parts = [p.strip() for p in title.split(' — ') if p.strip()]
            if len(parts) >= 2:
                app_name = parts[0]
                context = parts[1]
                
                # Skip generic markers
                if context in ['✳', '✳ ', '']:
                    context = parts[2] if len(parts) > 2 else app_name
                
                # Create meaningful task name
                if app_name.lower() in ['chrome', 'safari', 'firefox']:
                    return f"Web Research ({context})"
                elif app_name.lower() in ['terminal', 'iterm', 'iterm2']:
                    return f"Terminal Work ({context})"
                elif context != app_name:
                    return f"{context} ({app_name})"
                else:
                    return app_name
        
        # Final fallback: Return cleaned title
        return title.split(' — ')[0] if ' — ' in title else title
    
    def get_task_groups(
        self,
        start_date: datetime,
        end_date: datetime,
        min_duration_minutes: float = 0.5,  # Lowered threshold
        gap_threshold_minutes: float = 15   # Increased gap tolerance
    ) -> List[TaskGroup]:
        """Get grouped tasks based on continuous activity with smart grouping.
        
        Args:
            start_date: Start of period
            end_date: End of period
            min_duration_minutes: Minimum duration to include (lowered to 0.5)
            gap_threshold_minutes: Max gap between activities to group (increased to 15)
            
        Returns:
            List of TaskGroup objects
        """
        # This method uses get_tasks_for_period which now uses PostgreSQL adapter
        tasks = self.get_tasks_for_period(start_date, end_date)
        
        if not tasks:
            return []
            
        # Sort by timestamp
        tasks.sort(key=lambda x: x.timestamp)
        
        groups = []
        current_group = None
        
        for task in tasks:
            normalized_window = self._normalize_window_title(task.window_title)
            
            if current_group is None:
                # Start new group
                current_group = {
                    "active_window": task.window_title,
                    "normalized_window": normalized_window,
                    'category': task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    'tasks': [task]
                }
            elif (normalized_window == current_group["normalized_window"] and
                  (task.timestamp - current_group['end_time']).total_seconds() / 60 <= gap_threshold_minutes):
                # Continue current group (using normalized window for comparison)
                current_group['end_time'] = task.timestamp
                current_group['tasks'].append(task)
            else:
                # Save current group and start new one
                duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
                if duration >= min_duration_minutes or len(current_group['tasks']) >= 3:  # Include if has many activities
                    groups.append(TaskGroup(
                        window_title=current_group["normalized_window"],  # Use normalized title
                        category=current_group['category'],
                        start_time=current_group['start_time'],
                        end_time=current_group['end_time'],
                        duration_minutes=max(duration, len(current_group['tasks']) * 0.25),  # Minimum duration based on activity count
                        task_count=len(current_group['tasks']),
                        tasks=current_group['tasks']
                    ))
                    
                # Start new group
                current_group = {
                    "active_window": task.window_title,
                    "normalized_window": normalized_window,
                    'category': task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    'tasks': [task]
                }
                
        # Don't forget last group
        if current_group:
            duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
            if duration >= min_duration_minutes or len(current_group['tasks']) >= 3:
                groups.append(TaskGroup(
                    window_title=current_group["normalized_window"],
                    category=current_group['category'],
                    start_time=current_group['start_time'],
                    end_time=current_group['end_time'],
                    duration_minutes=max(duration, len(current_group['tasks']) * 0.25),
                    task_count=len(current_group['tasks']),
                    tasks=current_group['tasks']
                ))
                
        return groups
                
        return groups
        

class ActivityRepository(BaseRepository):
    """Repository for activity/screenshot data."""
    
    def get_recent_activities(
        self,
        limit: int = 50,
        categories: Optional[List[str]] = None
    ) -> List[Activity]:
        """Get recent activities.
        
        Args:
            limit: Maximum number of activities
            categories: Optional category filter
            
        Returns:
            List of Activity objects
        """
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                # Get recent activities using PostgreSQL adapter
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)  # Get last week of activities
                
                task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, categories, limit)
                return self._convert_task_dicts_to_activities(task_dicts)
            except Exception as e:
                logger.warning(f"PostgreSQL adapter failed for activities, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        return self._get_activities_sqlite_fallback(limit, categories)
    
    def _get_activities_sqlite_fallback(
        self,
        limit: int = 50,
        categories: Optional[List[str]] = None
    ) -> List[Activity]:
        """Fallback SQLite implementation for activities."""
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.filepath,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'ocr_result'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'  
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        WHERE 1=1
        """
        
        params = []
        
        if categories:
            placeholders = ','.join(['?' for _ in categories])
            query += f" AND m4.value IN ({placeholders})"
            params.extend(categories)
            
        query += " ORDER BY e.created_at DESC LIMIT ?"
        params.append(limit)
        
        df = self._execute_query(query, tuple(params))
        
        activities = []
        for _, row in df.iterrows():
            activity = Activity(
                id=row['id'],
                timestamp=pd.to_datetime(row['created_at']),
                window_title=extract_window_title(row.get('active_window', '')) or row.get("active_window", 'Unknown'),
                category=row.get('category', 'Other'),
                ocr_text=row.get("ocr_text"),
                tasks=None,  # TODO: Parse tasks safely from JSON/string
                screenshot_path=row.get('filepath'),
                active_window=row.get('active_window')
            )
            activities.append(activity)
            
        return activities
    
    def _convert_task_dicts_to_activities(self, task_dicts: List[Dict[str, Any]]) -> List[Activity]:
        """Convert PostgreSQL adapter results to Activity objects."""
        from ...core.timezone_manager import get_timezone_manager
        tz_manager = get_timezone_manager()
        
        activities = []
        for task_dict in task_dicts:
            # Handle timestamp conversion
            timestamp = task_dict.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            if timestamp and hasattr(timestamp, 'tz_localize'):
                # Convert UTC to local time for display
                local_timestamp = tz_manager.utc_to_local(timestamp)
            else:
                local_timestamp = timestamp or datetime.now()
            
            # Extract window title
            window_title = extract_window_title(task_dict.get('window_title', '')) or task_dict.get('window_title', 'Unknown')
            
            activity = Activity(
                id=task_dict.get('id'),
                timestamp=local_timestamp,
                window_title=window_title,
                category=task_dict.get('category', 'Other'),
                ocr_text=task_dict.get('ocr_text'),
                tasks=task_dict.get('tasks'),  # Keep tasks data if available
                screenshot_path=task_dict.get('filepath'),
                active_window=task_dict.get('window_title')
            )
            activities.append(activity)
            
        return activities
        

class MetricsRepository(BaseRepository):
    """Repository for metrics and analytics data."""
    
    def get_daily_metrics(
        self,
        date: datetime
    ) -> Optional[DailyMetrics]:
        """Get metrics for a specific day.
        
        Args:
            date: Date to get metrics for
            
        Returns:
            DailyMetrics object or None
        """
        if hasattr(date, 'date'):
            # If it's already a datetime, extract the date
            date = date.date()
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                task_dicts = self.pg_adapter.get_tasks_optimized(start, end, None, 10000)  # Get all tasks for the day
                return self._calculate_daily_metrics_from_tasks(task_dicts, date)
            except Exception as e:
                logger.warning(f"PostgreSQL adapter failed for daily metrics, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        return self._get_daily_metrics_sqlite_fallback(date, start, end)
    
    def _get_daily_metrics_sqlite_fallback(
        self,
        date,
        start: datetime,
        end: datetime
    ) -> Optional[DailyMetrics]:
        """Fallback SQLite implementation for daily metrics."""
        # Get all data for the day
        query = """
        SELECT 
            e.created_at,
            m2.value as active_window,
            m4.value as category
        FROM entities e
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        WHERE e.created_at >= ? AND e.created_at <= ?
        ORDER BY e.created_at
        """
        
        df = self._execute_query(query, (
            start.strftime('%Y-%m-%d %H:%M:%S'),
            end.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        if df.empty:
            return None
            
        # Calculate metrics
        total_tasks = len(df)
        unique_windows = df["active_window"].nunique()
        
        # Category breakdown
        categories = df['category'].value_counts().to_dict()
        
        # Calculate productive time (Development + Productivity categories)
        productive_categories = ['Development', 'Productivity']
        productive_tasks = df[df['category'].isin(productive_categories)]
        productive_time_minutes = len(productive_tasks) * 5  # 5 min per capture
        
        # Most used apps (by time spent)
        app_time = defaultdict(float)
        for _, row in df.iterrows():
            window = extract_window_title(row.get('active_window', '')) or row.get("active_window", 'Unknown')
            app_time[window] += 5  # 5 min per capture
            
        most_used = sorted(app_time.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Peak hours
        df['hour'] = pd.to_datetime(df['created_at']).dt.hour
        peak_hours = df['hour'].value_counts().head(3).index.tolist()
        
        return DailyMetrics(
            date=date,
            total_tasks=total_tasks,
            total_duration_minutes=total_tasks * 5,
            unique_windows=unique_windows,
            categories=categories,
            productive_time_minutes=productive_time_minutes,
            most_used_apps=most_used,
            peak_hours=peak_hours
        )
    
    def _calculate_daily_metrics_from_tasks(self, task_dicts: List[Dict[str, Any]], date) -> DailyMetrics:
        """Calculate daily metrics from PostgreSQL adapter task data."""
        if not task_dicts:
            return None
        
        # Calculate metrics
        total_tasks = len(task_dicts)
        
        # Extract categories and windows
        categories = defaultdict(int)
        unique_windows = set()
        app_time = defaultdict(float)
        hours = defaultdict(int)
        
        for task_dict in task_dicts:
            category = task_dict.get('category', 'Other')
            categories[category] += 1
            
            window_title = task_dict.get('window_title', 'Unknown')
            unique_windows.add(window_title)
            
            # Extract app name for time tracking
            window = extract_window_title(window_title) or window_title
            app_time[window] += 5  # 5 min per capture
            
            # Extract hour for peak analysis
            timestamp = task_dict.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                hours[timestamp.hour] += 1
        
        # Calculate productive time
        productive_categories = ['Development', 'Productivity']
        productive_tasks = sum(categories[cat] for cat in productive_categories if cat in categories)
        productive_time_minutes = productive_tasks * 5
        
        # Most used apps
        most_used = sorted(app_time.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Peak hours
        peak_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [hour for hour, _ in peak_hours]
        
        return DailyMetrics(
            date=date,
            total_tasks=total_tasks,
            total_duration_minutes=total_tasks * 5,
            unique_windows=len(unique_windows),
            categories=dict(categories),
            productive_time_minutes=productive_time_minutes,
            most_used_apps=most_used,
            peak_hours=peak_hours
        )
        
    def get_metrics_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get summary metrics for a period.
        
        Args:
            start_date: Start of period
            end_date: End of period
            
        Returns:
            Dictionary of metrics
        """
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, None, 50000)  # Get all tasks for period
                return self._calculate_metrics_summary_from_tasks(task_dicts, start_date, end_date)
            except Exception as e:
                logger.warning(f"PostgreSQL adapter failed for metrics summary, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        return self._get_metrics_summary_sqlite_fallback(start_date, end_date)
    
    def _get_metrics_summary_sqlite_fallback(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Fallback SQLite implementation for metrics summary."""
        # Get basic activity metrics
        basic_query = """
        SELECT 
            COUNT(DISTINCT e.id) as total_activities,
            COUNT(DISTINCT DATE(e.created_at)) as active_days
        FROM entities e
        WHERE e.created_at >= ? AND e.created_at <= ?
        """
        
        df_basic = self._execute_query(basic_query, (
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        if df_basic.empty:
            return {
                'total_activities': 0,
                'active_days': 0,
                'unique_windows': 0,
                'unique_categories': 0,
                'avg_daily_activities': 0
            }
            
        # Get unique categories and windows separately using DATE comparison for broader match
        category_query = """
        SELECT COUNT(DISTINCT m.value) as unique_categories
        FROM metadata_entries m 
        JOIN entities e ON m.entity_id = e.id 
        WHERE m.key = 'category' 
        AND DATE(e.created_at) >= DATE(?) 
        AND DATE(e.created_at) <= DATE(?)
        """
        
        window_query = """
        SELECT COUNT(DISTINCT m.value) as unique_windows
        FROM metadata_entries m 
        JOIN entities e ON m.entity_id = e.id 
        WHERE m.key = "active_window" 
        AND DATE(e.created_at) >= DATE(?) 
        AND DATE(e.created_at) <= DATE(?)
        """
        
        df_categories = self._execute_query(category_query, (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        df_windows = self._execute_query(window_query, (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        basic_row = df_basic.iloc[0]
        total_activities = basic_row['total_activities']
        active_days = basic_row['active_days'] or 1
        unique_categories = df_categories.iloc[0]['unique_categories'] if not df_categories.empty else 0
        unique_windows = df_windows.iloc[0]['unique_windows'] if not df_windows.empty else 0
        
        return {
            'total_activities': total_activities,
            'active_days': active_days,
            'unique_windows': unique_windows,
            'unique_categories': unique_categories,
            'avg_daily_activities': total_activities / active_days
        }
    
    def _calculate_metrics_summary_from_tasks(
        self,
        task_dicts: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate metrics summary from PostgreSQL adapter task data."""
        if not task_dicts:
            return {
                'total_activities': 0,
                'active_days': 0,
                'unique_windows': 0,
                'unique_categories': 0,
                'avg_daily_activities': 0
            }
        
        total_activities = len(task_dicts)
        unique_categories = set()
        unique_windows = set()
        active_dates = set()
        
        for task_dict in task_dicts:
            # Track unique categories
            category = task_dict.get('category')
            if category:
                unique_categories.add(category)
            
            # Track unique windows
            window_title = task_dict.get('window_title')
            if window_title:
                unique_windows.add(window_title)
            
            # Track active dates
            timestamp = task_dict.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                active_dates.add(timestamp.date())
        
        active_days = len(active_dates) or 1
        avg_daily_activities = total_activities / active_days
        
        return {
            'total_activities': total_activities,
            'active_days': active_days,
            'unique_windows': len(unique_windows),
            'unique_categories': len(unique_categories),
            'avg_daily_activities': avg_daily_activities
        }
