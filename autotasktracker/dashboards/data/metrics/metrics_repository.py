"""Metrics repository for analytics and metrics data access."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from collections import defaultdict

from autotasktracker.core.categorizer import extract_window_title
from autotasktracker.dashboards.data.core.base_repository import BaseRepository
from autotasktracker.dashboards.data.models import DailyMetrics

logger = logging.getLogger(__name__)


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
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "active_window"
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = "category"
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
        categories = df["category"].value_counts().to_dict()
        
        # Calculate productive time (Development + Productivity categories)
        productive_categories = ['Development', 'Productivity']
        productive_tasks = df[df["category"].isin(productive_categories)]
        productive_time_minutes = len(productive_tasks) * 5  # 5 min per capture
        
        # Most used apps (by time spent)
        app_time = defaultdict(float)
        for _, row in df.iterrows():
            window = extract_window_title(row.get("active_window", '')) or row.get("active_window", 'Unknown')
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
    
    def _calculate_daily_metrics_from_tasks(self, task_dicts: List[Dict[str, Any]], date) -> Optional[DailyMetrics]:
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
            category = task_dict.get("category", 'Other')
            categories[category] += 1
            
            window_title = task_dict.get("active_window", 'Unknown')
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
        # PostgreSQL adapter temporarily disabled due to metadata join issues
        # TODO: Fix PostgreSQL adapter to properly join with metadata_entries
        # if self.use_pensieve and self.pg_adapter:
        #     try:
        #         task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, None, 50000)
        #         return self._calculate_metrics_summary_from_tasks(task_dicts, start_date, end_date)
        #     except Exception as e:
        #         logger.warning(f"PostgreSQL adapter failed for metrics summary, falling back to SQLite: {e}")
        
        # Use direct SQLite query (reliable)
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
        WHERE m.key = "category" 
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
        
        # Use longer cache TTL for aggregated metrics (10 minutes for historical, 2 minutes for today)
        metrics_cache_ttl = 120 if (datetime.now().date() == start_date.date()) else 600
        
        df_categories = self._execute_query(category_query, (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ), cache_ttl=metrics_cache_ttl)
        
        df_windows = self._execute_query(window_query, (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ), cache_ttl=metrics_cache_ttl)
        
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
            category = task_dict.get("category")
            if category:
                unique_categories.add(category)
            
            # Track unique windows
            window_title = task_dict.get("active_window")
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