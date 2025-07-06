"""
Simplified database manager for dashboard use.
Avoids connection pooling timeouts by using direct connections.
"""

import logging
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# PostgreSQL imports with fallback
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import Error as PostgreSQLError
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    PostgreSQLError = Exception

import sqlite3


class SimpleDatabaseManager:
    """Simplified database manager for dashboards without connection pooling."""
    
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
        self._is_postgresql = self._detect_database_type()
        logger.info(f"SimpleDatabaseManager initialized: {self.get_database_type()}")
    
    def _detect_database_type(self) -> bool:
        """Detect if database is PostgreSQL or SQLite."""
        return self.db_path.startswith(('postgresql://', 'postgres://'))
    
    def get_database_type(self) -> str:
        """Get database type."""
        return "postgresql" if self._is_postgresql else "sqlite"
    
    @contextmanager
    def get_connection(self, readonly: bool = True):
        """Get database connection."""
        if self._is_postgresql:
            if not POSTGRESQL_AVAILABLE:
                raise Exception("PostgreSQL dependencies not available")
            
            conn = psycopg2.connect(self.db_path)
            conn.autocommit = readonly
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    def fetch_tasks(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100,
                   offset: int = 0,
                   include_ai_fields: bool = False,
                   time_filter: Optional[str] = None) -> pd.DataFrame:
        """Fetch tasks with simplified query."""
        
        # Handle time_filter convenience parameter
        if time_filter and not start_date:
            start_date = self._get_start_date_from_filter(time_filter)
        
        # Simple query that works for both databases
        query = """
        SELECT
            e.id,
            e.filepath,
            e.created_at,
            me1.value as ocr_text,
            me2.value as active_window
        FROM
            entities e
            LEFT JOIN metadata_entries me1 ON e.id = me1.entity_id AND me1.key = 'ocr_result'
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
        WHERE
            (e.filepath LIKE '%.png' 
             OR e.filepath LIKE '%.jpg' 
             OR e.filepath LIKE '%.jpeg'
             OR e.filepath LIKE '%.webp')
        """
        
        params = []
        
        # Add date filters
        if start_date:
            if self._is_postgresql:
                query += " AND e.created_at >= %s"
            else:
                query += " AND e.created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            if self._is_postgresql:
                query += " AND e.created_at <= %s"
            else:
                query += " AND e.created_at <= ?"
            params.append(end_date.isoformat())
        
        # Add ordering and limit
        if self._is_postgresql:
            query += " ORDER BY e.created_at DESC LIMIT %s OFFSET %s"
        else:
            query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with self.get_connection() as conn:
                if self._is_postgresql:
                    return self._execute_postgresql_query(conn, query, params)
                else:
                    return pd.read_sql_query(query, conn, params=params)
                    
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return pd.DataFrame()
    
    def _execute_postgresql_query(self, conn, query: str, params: List[Any]) -> pd.DataFrame:
        """Execute PostgreSQL query and return DataFrame."""
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                if cursor.description is None:
                    return pd.DataFrame()
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                if not rows:
                    return pd.DataFrame(columns=columns)
                
                data = [dict(row) for row in rows]
                df = pd.DataFrame(data)
                
                # Add missing columns for compatibility
                return self._adapt_dataframe(df)
                
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            return pd.DataFrame()
    
    def _adapt_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add missing columns for dashboard compatibility."""
        if df.empty:
            return pd.DataFrame(columns=[
                'id', 'filepath', 'filename', 'created_at', 
                'file_created_at', 'last_scan_at', 'ocr_text', 'active_window'
            ])
        
        # Add filename from filepath
        if 'filename' not in df.columns and 'filepath' in df.columns:
            import os
            df['filename'] = df['filepath'].apply(lambda x: os.path.basename(x) if x else None)
        
        # Add missing timestamp columns
        if 'file_created_at' not in df.columns and 'created_at' in df.columns:
            df['file_created_at'] = df['created_at']
        
        if 'last_scan_at' not in df.columns and 'created_at' in df.columns:
            df['last_scan_at'] = df['created_at']
        
        return df
    
    def _get_start_date_from_filter(self, time_filter: str) -> Optional[datetime]:
        """Convert time filter to start date."""
        from datetime import timedelta
        now = datetime.now()
        
        if time_filter == "Last 15 Minutes":
            return now - timedelta(minutes=15)
        elif time_filter == "Last Hour":
            return now - timedelta(hours=1)
        elif time_filter == "Today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "Last 24 Hours":
            return now - timedelta(days=1)
        elif time_filter == "Last 7 Days":
            return now - timedelta(days=7)
        else:  # "All Time"
            return None
    
    def get_screenshot_count(self, date: Optional[datetime] = None) -> int:
        """Get screenshot count."""
        try:
            query = "SELECT COUNT(*) as count FROM entities WHERE filepath LIKE '%.png' OR filepath LIKE '%.jpg'"
            with self.get_connection() as conn:
                if self._is_postgresql:
                    with conn.cursor() as cursor:
                        cursor.execute(query)
                        return cursor.fetchone()[0]
                else:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting screenshot count: {e}")
            return 0
    
    def get_tables(self) -> List[str]:
        """Get list of tables."""
        try:
            with self.get_connection() as conn:
                if self._is_postgresql:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                        return [row[0] for row in cursor.fetchall()]
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []