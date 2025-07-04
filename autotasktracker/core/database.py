"""
Database management module for AutoTaskTracker.
Provides centralized database access and query methods.
"""

import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from queue import Queue, Empty
import pandas as pd
from contextlib import contextmanager
import logging
from autotasktracker.config import get_config


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections with connection pooling and performance optimizations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DatabaseManager with connection pooling.
        
        Args:
            db_path: Path to the database. If None, uses default path.
        """
        if db_path is None:
            config = get_config()
            self.db_path = config.get_db_path()
        else:
            self.db_path = db_path
        
        # Connection pooling - separate pools for read-only and read-write
        self._readonly_pool = Queue(maxsize=16)
        self._readwrite_pool = Queue(maxsize=4)
        self._max_connections = 20
        self._active_connections = 0
        self._pool_lock = threading.Lock()
        self._wal_mode_enabled = False
        
        # Initialize database with optimizations
        self._initialize_database()
        
        # Create initial connections
        self._warm_up_pool()
    
    def _initialize_database(self):
        """Initialize database with performance optimizations."""
        try:
            # Create a connection to set up optimizations
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            
            # Performance optimizations
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster than FULL
            conn.execute("PRAGMA cache_size=10000")    # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")   # Use memory for temp tables
            conn.execute("PRAGMA mmap_size=268435456") # 256MB memory map
            
            # Create indexes if they don't exist
            self._create_indexes(conn)
            
            conn.commit()
            conn.close()
            
            self._wal_mode_enabled = True
            logger.info("Database initialized with WAL mode and performance optimizations")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """Create performance indexes for VLM queries."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_metadata_entity_key ON metadata_entries(entity_id, key)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata_entries(key)",
            "CREATE INDEX IF NOT EXISTS idx_entities_created_at ON entities(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_entities_file_type ON entities(file_type_group)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_created_at ON metadata_entries(created_at)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
                logger.debug(f"Created index: {index_sql.split()[-1]}")
            except sqlite3.Error as e:
                logger.warning(f"Failed to create index: {e}")
    
    def _warm_up_pool(self):
        """Create initial connections to warm up the pools."""
        try:
            # Create read-only connections (most common)
            for _ in range(2):
                conn = self._create_connection(readonly=True)
                self._readonly_pool.put(conn)
                with self._pool_lock:
                    self._active_connections += 1
                    
            # Create one read-write connection
            conn = self._create_connection(readonly=False)
            self._readwrite_pool.put(conn)
            with self._pool_lock:
                self._active_connections += 1
        except Exception as e:
            logger.warning(f"Failed to warm up connection pool: {e}")
    
    def _create_connection(self, readonly: bool = False) -> sqlite3.Connection:
        """Create a new database connection with optimizations."""
        try:
            if readonly and self._wal_mode_enabled:
                # Read-only connections in WAL mode
                conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True, timeout=30)
            else:
                conn = sqlite3.connect(self.db_path, timeout=30)
            
            conn.row_factory = sqlite3.Row
            
            # Set pragmas for this connection
            if not readonly:
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                # Ensure autocommit is enabled for bulk operations
                conn.isolation_level = None
            
            return conn
            
        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def _get_pooled_connection(self, readonly: bool = True) -> sqlite3.Connection:
        """Get a connection from the pool or create a new one."""
        pool = self._readonly_pool if readonly else self._readwrite_pool
        
        try:
            # Try to get from appropriate pool first
            conn = pool.get_nowait()
            # Test if connection is still valid
            conn.execute("SELECT 1")
            return conn
        except (Empty, sqlite3.Error):
            # Pool empty or connection invalid, create new one
            with self._pool_lock:
                if self._active_connections < self._max_connections:
                    self._active_connections += 1
                    return self._create_connection(readonly)
                else:
                    # Wait for a connection to become available
                    try:
                        conn = pool.get(timeout=10)
                        conn.execute("SELECT 1")  # Test connection
                        return conn
                    except (Empty, sqlite3.Error):
                        # Fallback: create connection anyway (exceeds pool limit)
                        logger.warning("Connection pool exhausted, creating additional connection")
                        return self._create_connection(readonly)
    
    def _return_connection(self, conn: sqlite3.Connection, readonly: bool = True):
        """Return a connection to the appropriate pool."""
        pool = self._readonly_pool if readonly else self._readwrite_pool
        
        try:
            # Test if connection is still valid
            conn.execute("SELECT 1")
            # Put back in appropriate pool if there's space
            pool.put_nowait(conn)
        except (sqlite3.Error, Exception):
            # Connection invalid or pool full, close it
            try:
                conn.close()
            except sqlite3.Error:
                pass
            with self._pool_lock:
                self._active_connections = max(0, self._active_connections - 1)
    
    @contextmanager
    def get_connection(self, readonly: bool = True):
        """
        Get a database connection with connection pooling and context manager support.
        
        Args:
            readonly: If True, opens connection in read-only mode
            
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = self._get_pooled_connection(readonly)
            yield conn
        except sqlite3.OperationalError as e:
            logger.error(f"Database connection error: {e}")
            raise  # Re-raise the exception instead of double yield
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise
        finally:
            if conn:
                if readonly:
                    self._return_connection(conn, readonly=True)
                else:
                    # For write connections, close immediately to avoid transaction issues
                    try:
                        conn.close()
                    except sqlite3.Error:
                        pass
                    with self._pool_lock:
                        self._active_connections = max(0, self._active_connections - 1)
    
    def test_connection(self) -> bool:
        """Test if database connection can be established."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                return True
        except sqlite3.OperationalError:
            return False
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._pool_lock:
            return {
                'active_connections': self._active_connections,
                'max_connections': self._max_connections,
                'readonly_pooled': self._readonly_pool.qsize(),
                'readwrite_pooled': self._readwrite_pool.qsize(),
                'wal_mode_enabled': self._wal_mode_enabled
            }
    
    def close_all_connections(self):
        """Close all pooled connections."""
        # Close read-only pool
        while not self._readonly_pool.empty():
            try:
                conn = self._readonly_pool.get_nowait()
                conn.close()
            except (sqlite3.Error, Exception):
                pass
        
        # Close read-write pool
        while not self._readwrite_pool.empty():
            try:
                conn = self._readwrite_pool.get_nowait()
                conn.close()
            except (sqlite3.Error, Exception):
                pass
        
        with self._pool_lock:
            self._active_connections = 0
        
        logger.info("Closed all database connections")
    
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
            # Convert start_date to UTC for comparison with e.created_at (which is stored in UTC)
            query += " AND e.created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            # Convert end_date to UTC for comparison with e.created_at (which is stored in UTC)
            query += " AND e.created_at <= ?"
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
    
    def fetch_tasks_with_ai(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 100,
                           offset: int = 0) -> pd.DataFrame:
        """
        Fetch tasks with AI-enhanced data (VLM descriptions and embeddings).
        
        Args:
            start_date: Start date filter
            end_date: End date filter  
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            DataFrame with task and AI data
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
            me2.value as active_window,
            me3.value as vlm_description,
            CASE WHEN me4.value IS NOT NULL THEN 1 ELSE 0 END as has_embedding
        FROM
            entities e
            LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
            LEFT JOIN metadata_entries me3 ON e.id = me3.entity_id AND me3.key IN ('minicpm_v_result', 'vlm_structured')
            LEFT JOIN metadata_entries me4 ON e.id = me4.entity_id AND me4.key = 'embedding'
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
            logger.error(f"Error fetching tasks with AI data: {e}")
            return pd.DataFrame()
    
    def get_ai_coverage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about AI feature coverage in the database.
        
        Returns:
            Dictionary with coverage statistics
        """
        # Optimized query using indexes
        query = """
        SELECT 
            COUNT(DISTINCT e.id) as total_screenshots,
            COUNT(DISTINCT me_ocr.entity_id) as with_ocr,
            COUNT(DISTINCT me_vlm.entity_id) as with_vlm,
            COUNT(DISTINCT me_emb.entity_id) as with_embeddings
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr.key = 'ocr_result'
        LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm.key IN ('minicpm_v_result', 'vlm_structured')
        LEFT JOIN metadata_entries me_emb ON e.id = me_emb.entity_id AND me_emb.key = 'embedding'
        WHERE e.file_type_group = 'image'
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                
                if result:
                    total = result['total_screenshots']
                    return {
                        'total_screenshots': total,
                        'ocr_count': result['with_ocr'],
                        'ocr_percentage': (result['with_ocr'] / total * 100) if total > 0 else 0,
                        'vlm_count': result['with_vlm'],
                        'vlm_percentage': (result['with_vlm'] / total * 100) if total > 0 else 0,
                        'embedding_count': result['with_embeddings'],
                        'embedding_percentage': (result['with_embeddings'] / total * 100) if total > 0 else 0
                    }
                return {}
        except sqlite3.Error as e:
            logger.error(f"Error getting AI coverage stats: {e}")
            return {}
    
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