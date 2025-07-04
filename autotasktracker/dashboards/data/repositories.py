"""Data repositories for dashboard data access."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from collections import defaultdict

from ...core.database import DatabaseManager
from ...core.categorizer import extract_window_title
from .models import Task, Activity, TaskGroup, DailyMetrics

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
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
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.filepath,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category,
            m5.value as window_title
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'text'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = 'window_title'
        WHERE e.created_at >= ? AND e.created_at <= ?
        """
        
        params = [
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S')
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
            # Group by window and calculate duration
            window_title = extract_window_title(row.get('active_window', '')) or row.get('window_title', 'Unknown')
            
            task = Task(
                id=row['id'],
                title=window_title,
                category=row.get('category', 'Other'),
                timestamp=pd.to_datetime(row['created_at']),
                duration_minutes=5,  # Default 5 min per capture
                window_title=window_title,
                ocr_text=row.get('ocr_text'),
                screenshot_path=row.get('filepath')
            )
            tasks.append(task)
            
        return tasks
        
    def get_task_groups(
        self,
        start_date: datetime,
        end_date: datetime,
        min_duration_minutes: float = 1,
        gap_threshold_minutes: float = 10
    ) -> List[TaskGroup]:
        """Get grouped tasks based on continuous activity.
        
        Args:
            start_date: Start of period
            end_date: End of period
            min_duration_minutes: Minimum duration to include
            gap_threshold_minutes: Max gap between activities to group
            
        Returns:
            List of TaskGroup objects
        """
        tasks = self.get_tasks_for_period(start_date, end_date)
        
        if not tasks:
            return []
            
        # Sort by timestamp
        tasks.sort(key=lambda x: x.timestamp)
        
        groups = []
        current_group = None
        
        for task in tasks:
            if current_group is None:
                # Start new group
                current_group = {
                    'window_title': task.window_title,
                    'category': task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    'tasks': [task]
                }
            elif (task.window_title == current_group['window_title'] and
                  (task.timestamp - current_group['end_time']).total_seconds() / 60 <= gap_threshold_minutes):
                # Continue current group
                current_group['end_time'] = task.timestamp
                current_group['tasks'].append(task)
            else:
                # Save current group and start new one
                duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
                if duration >= min_duration_minutes:
                    groups.append(TaskGroup(
                        window_title=current_group['window_title'],
                        category=current_group['category'],
                        start_time=current_group['start_time'],
                        end_time=current_group['end_time'],
                        duration_minutes=duration,
                        task_count=len(current_group['tasks']),
                        tasks=current_group['tasks']
                    ))
                    
                # Start new group
                current_group = {
                    'window_title': task.window_title,
                    'category': task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    'tasks': [task]
                }
                
        # Don't forget last group
        if current_group:
            duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
            if duration >= min_duration_minutes:
                groups.append(TaskGroup(
                    window_title=current_group['window_title'],
                    category=current_group['category'],
                    start_time=current_group['start_time'],
                    end_time=current_group['end_time'],
                    duration_minutes=duration,
                    task_count=len(current_group['tasks']),
                    tasks=current_group['tasks']
                ))
                
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
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.filepath,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category,
            m5.value as window_title
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'text'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'  
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = 'window_title'
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
                window_title=extract_window_title(row.get('active_window', '')) or row.get('window_title', 'Unknown'),
                category=row.get('category', 'Other'),
                ocr_text=row.get('ocr_text'),
                tasks=None,  # TODO: Parse tasks safely from JSON/string
                screenshot_path=row.get('filepath'),
                active_window=row.get('active_window')
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
        
        # Get all data for the day
        query = """
        SELECT 
            e.created_at,
            m2.value as active_window,
            m4.value as category,
            m5.value as window_title
        FROM entities e
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = 'window_title'
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
        unique_windows = df['window_title'].nunique()
        
        # Category breakdown
        categories = df['category'].value_counts().to_dict()
        
        # Calculate productive time (Development + Productivity categories)
        productive_categories = ['Development', 'Productivity']
        productive_tasks = df[df['category'].isin(productive_categories)]
        productive_time_minutes = len(productive_tasks) * 5  # 5 min per capture
        
        # Most used apps (by time spent)
        app_time = defaultdict(float)
        for _, row in df.iterrows():
            window = extract_window_title(row.get('active_window', '')) or row.get('window_title', 'Unknown')
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
        WHERE m.key = 'window_title' 
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
