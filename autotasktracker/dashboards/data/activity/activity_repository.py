"""Activity repository for activity/screenshot data access."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd

from autotasktracker.core.categorizer import extract_window_title
from autotasktracker.dashboards.data.core.base_repository import BaseRepository
from autotasktracker.dashboards.data.models import Activity

logger = logging.getLogger(__name__)


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
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = "ocr_result"
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "active_window"  
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = "tasks"
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = "category"
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
                window_title=extract_window_title(row.get("active_window", '')) or row.get("active_window", 'Unknown'),
                category=row.get("category", 'Other'),
                ocr_text=row.get("ocr_result"),
                tasks=None,  # TODO: Parse tasks safely from JSON/string
                screenshot_path=row.get('filepath'),
                active_window=row.get("active_window")
            )
            activities.append(activity)
            
        return activities
    
    def _convert_task_dicts_to_activities(self, task_dicts: List[Dict[str, Any]]) -> List[Activity]:
        """Convert PostgreSQL adapter results to Activity objects."""
        # Timezone conversion disabled - using local time directly
        
        activities = []
        for task_dict in task_dicts:
            # Handle timestamp conversion
            timestamp = task_dict.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            # Use timestamp directly - timezone conversion disabled
            local_timestamp = timestamp or datetime.now()
            
            # Extract window title
            window_title = extract_window_title(task_dict.get("active_window", '')) or task_dict.get("active_window", 'Unknown')
            
            activity = Activity(
                id=task_dict.get('id'),
                timestamp=local_timestamp,
                window_title=window_title,
                category=task_dict.get("category", 'Other'),
                ocr_text=task_dict.get("ocr_result"),
                tasks=task_dict.get("tasks"),  # Keep tasks data if available
                screenshot_path=task_dict.get('filepath'),
                active_window=task_dict.get("active_window")
            )
            activities.append(activity)
            
        return activities