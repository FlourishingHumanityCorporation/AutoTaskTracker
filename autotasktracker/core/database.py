"""
Database management module for AutoTaskTracker.
Provides centralized database access and query methods.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from contextlib import contextmanager
import logging


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and provides query methods."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DatabaseManager.
        
        Args:
            db_path: Path to the database. If None, uses default path.
        """
        if db_path is None:
            self.db_path = os.path.expanduser("~/.memos/database.db")
        else:
            self.db_path = db_path
        
        self._connection_pool = []
        self._max_connections = 5
    
    @contextmanager
    def get_connection(self, readonly: bool = True):
        """
        Get a database connection with context manager support.
        
        Args:
            readonly: If True, opens connection in read-only mode
            
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            if readonly:
                conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
            else:
                conn = sqlite3.connect(self.db_path)
            
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.OperationalError as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """Test if database connection can be established."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                return True
        except sqlite3.OperationalError:
            return False
    
    def fetch_tasks(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100,
                   offset: int = 0) -> pd.DataFrame:
        """
        Fetch tasks (screenshots with metadata) from the database.
        
        Args:
            start_date: Start date filter
            end_date: End date filter  
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            DataFrame with task data
        """
        query = """
        SELECT
            e.id,
            e.filepath,
            e.filename,
            datetime(e.created_at, 'localtime') as created_at,
            e.file_created_at,
            e.last_scan_at,
            me.value as ocr_text,
            me2.value as active_window
        FROM
            entities e
            LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
        WHERE
            e.file_type_group = 'image'
        """
        
        params = []
        
        if start_date:
            query += " AND datetime(e.created_at, 'localtime') >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND datetime(e.created_at, 'localtime') <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
        except pd.io.sql.DatabaseError as e:
            logger.error(f"Error fetching tasks: {e}")
            return pd.DataFrame()
    
    def fetch_tasks_by_time_filter(self, time_filter: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetch tasks based on predefined time filters.
        
        Args:
            time_filter: One of "Last 15 Minutes", "Last Hour", "Today", 
                        "Last 24 Hours", "Last 7 Days", "All Time"
            limit: Maximum number of records
            
        Returns:
            DataFrame with task data
        """
        now = datetime.now()
        
        time_filters = {
            "Last 15 Minutes": now - timedelta(minutes=15),
            "Last Hour": now - timedelta(hours=1),
            "Today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "Last 24 Hours": now - timedelta(days=1),
            "Last 7 Days": now - timedelta(days=7),
            "All Time": datetime(2000, 1, 1)
        }
        
        start_date = time_filters.get(time_filter, datetime(2000, 1, 1))
        return self.fetch_tasks(start_date=start_date, limit=limit)
    
    def get_screenshot_count(self, date: Optional[datetime] = None) -> int:
        """
        Get count of screenshots for a specific date.
        
        Args:
            date: Date to check. If None, uses today.
            
        Returns:
            Screenshot count
        """
        if date is None:
            date = datetime.now()
        
        query = """
        SELECT COUNT(*) as count
        FROM entities 
        WHERE file_type_group = 'image' 
        AND date(created_at, 'localtime') = date(?, 'localtime')
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date.isoformat(),))
                result = cursor.fetchone()
                return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Error getting screenshot count: {e}")
            return 0
    
    def get_unique_applications(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        Get list of unique applications used in a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of unique application names
        """
        query = """
        SELECT DISTINCT me.value as active_window
        FROM entities e
        JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'active_window'
        WHERE e.file_type_group = 'image'
        AND datetime(e.created_at, 'localtime') BETWEEN ? AND ?
        AND me.value IS NOT NULL
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (start_date.isoformat(), end_date.isoformat()))
                return [row['active_window'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting unique applications: {e}")
            return []
    
    def get_activity_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get activity summary statistics for a date.
        
        Args:
            date: Date to summarize. If None, uses today.
            
        Returns:
            Dictionary with summary statistics
        """
        if date is None:
            date = datetime.now()
        
        # Get basic stats
        screenshot_count = self.get_screenshot_count(date)
        
        # Get time range
        query = """
        SELECT 
            MIN(datetime(created_at, 'localtime')) as first_activity,
            MAX(datetime(created_at, 'localtime')) as last_activity
        FROM entities
        WHERE file_type_group = 'image'
        AND date(created_at, 'localtime') = date(?, 'localtime')
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date.isoformat(),))
                result = cursor.fetchone()
                
                if result and result['first_activity']:
                    first = datetime.fromisoformat(result['first_activity'])
                    last = datetime.fromisoformat(result['last_activity'])
                    duration_hours = (last - first).total_seconds() / 3600
                else:
                    duration_hours = 0
                
                return {
                    'screenshot_count': screenshot_count,
                    'duration_hours': duration_hours,
                    'avg_screenshots_per_hour': screenshot_count / max(duration_hours, 1)
                }
        except sqlite3.Error as e:
            logger.error(f"Error getting activity summary: {e}")
            return {
                'screenshot_count': screenshot_count,
                'duration_hours': 0,
                'avg_screenshots_per_hour': 0
            }
    
    def search_activities(self, search_term: str, limit: int = 50) -> pd.DataFrame:
        """
        Search activities by text in OCR content or window titles.
        
        Args:
            search_term: Term to search for
            limit: Maximum results
            
        Returns:
            DataFrame with matching activities
        """
        query = """
        SELECT
            e.id,
            e.filepath,
            datetime(e.created_at, 'localtime') as created_at,
            me.value as ocr_text,
            me2.value as active_window
        FROM entities e
        LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
        WHERE e.file_type_group = 'image'
        AND (
            me.value LIKE ? OR 
            me2.value LIKE ?
        )
        ORDER BY e.created_at DESC
        LIMIT ?
        """
        
        search_pattern = f'%{search_term}%'
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=(search_pattern, search_pattern, limit))
                return df
        except pd.io.sql.DatabaseError as e:
            logger.error(f"Error searching activities: {e}")
            return pd.DataFrame()


# Singleton instance for convenience
_default_db_manager = None


def get_default_db_manager() -> DatabaseManager:
    """Get the default database manager instance."""
    global _default_db_manager
    if _default_db_manager is None:
        _default_db_manager = DatabaseManager()
    return _default_db_manager