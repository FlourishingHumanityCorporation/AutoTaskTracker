"""Data repositories for dashboard data access."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from collections import defaultdict
import re

from autotasktracker.core import DatabaseManager
from autotasktracker.core.categorizer import extract_window_title
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter, PostgreSQLAdapter
from autotasktracker.pensieve.cache_manager import get_cache_manager
from autotasktracker.core.exceptions import DatabaseError, CacheError
from .models import Task, Activity, TaskGroup, DailyMetrics
from .core.window_normalizer import get_window_normalizer

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, use_pensieve: bool = True):
        self.db = db_manager or DatabaseManager()
        self.use_pensieve = use_pensieve
        self.pg_adapter = get_postgresql_adapter() if use_pensieve else None
        self.cache = get_cache_manager()  # Integrate cache manager
        
    def _execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pd.DataFrame:
        """Execute query with intelligent caching and error handling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        import hashlib
        
        # Create cache key from query and params
        cache_key = f"query_{hashlib.md5(f'{query}_{params}'.encode()).hexdigest()}"
        
        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            # Convert back to DataFrame if it was serialized
            if isinstance(cached_result, dict) and 'data' in cached_result:
                return pd.DataFrame(cached_result['data'])
            return cached_result
        
        try:
            # Use the DatabaseManager's connection context manager
            with self.db.get_connection() as conn:
                result = pd.read_sql_query(query, conn, params=params)
                
                # Cache the result (serialize DataFrame for caching)
                cache_data = {
                    'data': result.to_dict('records'),
                    'columns': list(result.columns),
                    'shape': result.shape
                }
                self.cache.set(cache_key, cache_data, ttl=cache_ttl)
                logger.debug(f"Cached query result: {result.shape} rows")
                
                return result
        except pd.errors.DatabaseError as e:
            logger.error(f"Database error executing query: {e}")
            return pd.DataFrame()
        except DatabaseError as e:
            logger.error(f"AutoTaskTracker database error: {e}")
            return pd.DataFrame()
        except CacheError as e:
            logger.warning(f"Cache error (continuing without cache): {e}")
            # Retry without cache
            try:
                with self.db.get_connection() as conn:
                    return pd.read_sql_query(query, conn, params=params)
            except Exception as retry_e:
                logger.error(f"Retry failed: {retry_e}")
                return pd.DataFrame()
        except Exception as e:
            logger.exception(f"Unexpected error executing query: {e}")
            return pd.DataFrame()
    
    def invalidate_cache(self, pattern: str = None):
        """Invalidate cached query results.
        
        Args:
            pattern: Pattern to match for selective invalidation (default: all queries)
        """
        if pattern:
            count = self.cache.invalidate_pattern(pattern)
            logger.info(f"Invalidated {count} cached queries matching pattern: {pattern}")
        else:
            count = self.cache.invalidate_pattern("query_")
            logger.info(f"Invalidated {count} cached queries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache.get_stats()
    
    def _parse_tasks_safely(self, tasks_data: Any) -> Optional[List[str]]:
        """Safely parse task data from various formats.
        
        Args:
            tasks_data: Task data in various formats (string, JSON string, list, dict)
            
        Returns:
            List of task strings or None if parsing fails
        """
        if not tasks_data:
            return None
            
        try:
            # Already a list
            if isinstance(tasks_data, list):
                return [str(task) for task in tasks_data]
            
            # Try to parse as JSON string
            if isinstance(tasks_data, str):
                # Check if it's a JSON string
                if tasks_data.strip().startswith(('[', '{')):
                    parsed = json.loads(tasks_data)
                    
                    # Handle different JSON structures
                    if isinstance(parsed, list):
                        return [str(task) for task in parsed]
                    elif isinstance(parsed, dict):
                        # Check common task field names
                        if 'tasks' in parsed:
                            tasks = parsed['tasks']
                            if isinstance(tasks, list):
                                return tasks
                            elif isinstance(tasks, str):
                                return [tasks]
                        elif 'task' in parsed:
                            return [str(parsed['task'])]
                        elif 'subtasks' in parsed:
                            return parsed['subtasks']
                        # If dict but no recognized fields, convert to string
                        return [str(parsed)]
                else:
                    # Plain string task
                    return [tasks_data]
            
            # Other types - convert to string
            return [str(tasks_data)]
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.debug(f"Failed to parse tasks data: {e}")
            # Fallback - treat as single task string
            if tasks_data:
                return [str(tasks_data)]
            return None

class TaskRepository(BaseRepository):
    """Repository for task-related data access."""
    
    def count_tasks_today(self) -> int:
        """Count the number of tasks recorded today.
        
        Returns:
            int: Number of tasks recorded today
        """
        from datetime import datetime, time
        
        # Get today's date at midnight
        today_start = datetime.combine(datetime.today(), time.min)
        today_end = datetime.combine(datetime.today(), time.max)
        
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                task_dicts = self.pg_adapter.get_tasks_optimized(
                    start_date=today_start,
                    end_date=today_end,
                    limit=10000  # High limit to ensure we get all of today's tasks
                )
                return len(task_dicts)
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"PostgreSQL connection failed, falling back to SQLite: {e}")
            except ValueError as e:
                logger.warning(f"Invalid parameters for PostgreSQL adapter: {e}")
            except Exception as e:
                logger.warning(f"Unexpected PostgreSQL adapter error, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        query = """
        SELECT COUNT(*) as task_count
        FROM tasks
        WHERE timestamp BETWEEN ? AND ?
        """
        
        params = (
            today_start.strftime('%Y-%m-%d %H:%M:%S'),
            today_end.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        try:
            result = self._execute_query(query, params)
            return int(result.iloc[0]['task_count']) if not result.empty else 0
        except Exception as e:
            logger.error(f"Error counting today's tasks: {e}")
            return 0
    
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
        """Fallback SQLite implementation with intelligent caching."""
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.filepath,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category,
            m5.value as minicpm_v_result,
            m6.value as vlm_result,
            m7.value as subtasks,
            m8.value as tasks_json
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = "ocr_result"
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "active_window"
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = "tasks"
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = "category"
        LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = "minicpm_v_result"
        LEFT JOIN metadata_entries m6 ON e.id = m6.entity_id AND m6.key = "vlm_result"
        LEFT JOIN metadata_entries m7 ON e.id = m7.entity_id AND m7.key = "subtasks"
        LEFT JOIN metadata_entries m8 ON e.id = m8.entity_id AND m8.key = "tasks"
        WHERE e.created_at >= ? AND e.created_at <= ?
        """
        
        # Convert local time range to UTC for database query (Pensieve stores UTC)
        from autotasktracker.core.timezone_manager import get_timezone_manager
        
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
        
        # Use shorter cache TTL for recent data (60 seconds), longer for historical (5 minutes)
        cache_ttl = 60 if (datetime.now() - end_date).days < 1 else 300
        df = self._execute_query(query, tuple(params), cache_ttl=cache_ttl)
        
        tasks = []
        for _, row in df.iterrows():
            # Use extracted task if available, fallback to window title
            window_title = extract_window_title(row.get("active_window", '')) or row.get("active_window", 'Unknown')
            task_title = row.get("tasks") or window_title
            
            # Convert UTC timestamp from database to local time for display
            utc_timestamp = pd.to_datetime(row['created_at'])
            local_timestamp = tz_manager.utc_to_local(utc_timestamp)
            
            # Parse AI metadata if available
            metadata = {}
            
            # Parse AI results if they exist
            if 'minicpm_v_result' in row and row['minicpm_v_result']:
                try:
                    metadata['minicpm_v_result'] = row['minicpm_v_result']
                except Exception as e:
                    logger.warning(f"Failed to parse minicpm_v_result for task {row['id']}: {e}")
            
            if 'vlm_result' in row and row['vlm_result']:
                try:
                    metadata['vlm_result'] = row['vlm_result']
                except Exception as e:
                    logger.warning(f"Failed to parse vlm_result for task {row['id']}: {e}")
            
            if 'subtasks' in row and row['subtasks']:
                try:
                    metadata['subtasks'] = row['subtasks']
                except Exception as e:
                    logger.warning(f"Failed to parse subtasks for task {row['id']}: {e}")
            
            if 'tasks_json' in row and row['tasks_json']:
                try:
                    metadata['tasks'] = row['tasks_json']
                except Exception as e:
                    logger.warning(f"Failed to parse tasks_json for task {row['id']}: {e}")
            
            task = Task(
                id=row['id'],
                title=task_title,
                category=row.get("category", 'Other'),
                timestamp=local_timestamp,
                duration_minutes=5,  # Default 5 min per capture
                window_title=window_title,
                ocr_text=row.get("ocr_text"),
                screenshot_path=row.get('filepath'),
                metadata=metadata if metadata else None
            )
            tasks.append(task)
            
        return tasks
    
    def _convert_task_dicts_to_objects(self, task_dicts: List[Dict[str, Any]]) -> List[Task]:
        """Convert PostgreSQL adapter results to Task objects with AI metadata."""
        from autotasktracker.core.timezone_manager import get_timezone_manager
        tz_manager = get_timezone_manager()
        
        tasks = []
        for task_dict in task_dicts:
            # Extract task title from tasks array or use window title
            task_title = task_dict.get("active_window", 'Unknown')
            tasks_data = None
            
            if task_dict.get("tasks"):
                # Use first task title if available
                first_task = task_dict["tasks"][0] if isinstance(task_dict["tasks"], list) else task_dict["tasks"]
                if isinstance(first_task, dict) and 'title' in first_task:
                    task_title = first_task['title']
                    tasks_data = task_dict["tasks"]
                elif isinstance(first_task, str):
                    task_title = first_task
            
            # Extract window title
            window_title = extract_window_title(task_dict.get("active_window", '')) or task_dict.get("active_window", 'Unknown')
            
            # Handle timestamp conversion
            timestamp = task_dict.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            if timestamp and hasattr(timestamp, 'tz_localize'):
                # Convert UTC to local time for display
                local_timestamp = tz_manager.utc_to_local(timestamp)
            else:
                local_timestamp = timestamp or datetime.now()
            
            # Prepare AI metadata
            metadata = {}
            ai_fields = [
                'minicpm_v_result', 'vlm_result', 'subtasks', 'tasks'
            ]
            
            for field in ai_fields:
                if field in task_dict and task_dict[field]:
                    try:
                        # Handle potential JSON strings
                        if isinstance(task_dict[field], str):
                            metadata[field] = json.loads(task_dict[field])
                        else:
                            metadata[field] = task_dict[field]
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse {field} for task {task_dict.get('id')}: {e}")
                        metadata[field] = task_dict[field]  # Keep original if parsing fails
            
            # If we have tasks data from earlier, ensure it's in the metadata
            if tasks_data and 'tasks' not in metadata:
                metadata['tasks'] = tasks_data
            
            task = Task(
                id=task_dict.get('id'),
                title=task_title,
                category=task_dict.get("category", 'Other'),
                timestamp=local_timestamp,
                duration_minutes=5,  # Default 5 min per capture
                window_title=window_title,
                ocr_text=task_dict.get("ocr_result"),
                screenshot_path=task_dict.get('filepath'),
                metadata=metadata if metadata else None
            )
            tasks.append(task)
            
        return tasks
        
    def _normalize_window_title(self, window_title: str) -> str:
        """Normalize window title for better task context extraction.
        
        Uses the WindowTitleNormalizer to transform generic app titles 
        into meaningful work descriptions.
        
        Args:
            window_title: Raw window title
            
        Returns:
            Meaningful task description for grouping
        """
        normalizer = get_window_normalizer()
        return normalizer.normalize(window_title)
    
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
                    "category": task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    "tasks": [task]
                }
            elif (normalized_window == current_group["normalized_window"] and
                  (task.timestamp - current_group['end_time']).total_seconds() / 60 <= gap_threshold_minutes):
                # Continue current group (using normalized window for comparison)
                current_group['end_time'] = task.timestamp
                current_group["tasks"].append(task)
            else:
                # Save current group and start new one
                duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
                if duration >= min_duration_minutes or len(current_group["tasks"]) >= 3:  # Include if has many activities
                    groups.append(TaskGroup(
                        window_title=current_group["normalized_window"],  # Use normalized title
                        category=current_group["category"],
                        start_time=current_group['start_time'],
                        end_time=current_group['end_time'],
                        duration_minutes=max(duration, len(current_group["tasks"]) * 0.25),  # Minimum duration based on activity count
                        task_count=len(current_group["tasks"]),
                        tasks=current_group["tasks"]
                    ))
                    
                # Start new group
                current_group = {
                    "active_window": task.window_title,
                    "normalized_window": normalized_window,
                    "category": task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    "tasks": [task]
                }
                
        # Don't forget last group
        if current_group:
            duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
            if duration >= min_duration_minutes or len(current_group["tasks"]) >= 3:
                groups.append(TaskGroup(
                    window_title=current_group["normalized_window"],
                    category=current_group["category"],
                    start_time=current_group['start_time'],
                    end_time=current_group['end_time'],
                    duration_minutes=max(duration, len(current_group["tasks"]) * 0.25),
                    task_count=len(current_group["tasks"]),
                    tasks=current_group["tasks"]
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
                tasks=self._parse_tasks_safely(row.get('tasks')),
                screenshot_path=row.get('filepath'),
                active_window=row.get("active_window")
            )
            activities.append(activity)
            
        return activities
    
    def _convert_task_dicts_to_activities(self, task_dicts: List[Dict[str, Any]]) -> List[Activity]:
        """Convert PostgreSQL adapter results to Activity objects."""
        from autotasktracker.core.timezone_manager import get_timezone_manager
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
