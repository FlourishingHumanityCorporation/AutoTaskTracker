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
from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.config_reader import get_pensieve_config

# Import performance monitoring (with fallback if not available)
try:
    from autotasktracker.pensieve.performance_monitor import record_database_query, start_timer, end_timer
    PERFORMANCE_MONITORING_AVAILABLE = True
except ImportError:
    logger.debug("Performance monitoring not available")
    PERFORMANCE_MONITORING_AVAILABLE = False
    
    def record_database_query(duration_ms: float, query_type: str = "unknown"):
            logger.debug("Optional dependency not available")
    
    def start_timer(timer_name: str):
            logger.debug("Optional dependency not available")
    
    def end_timer(timer_name: str, metadata=None) -> float:
        return 0.0


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections with connection pooling and performance optimizations."""
    
    def __init__(self, db_path: Optional[str] = None, use_pensieve_api: bool = True):
        """
        Initialize DatabaseManager with connection pooling and Pensieve integration.
        
        Args:
            db_path: Path to the database. If None, uses Pensieve config.
            use_pensieve_api: Whether to use Pensieve API when available.
        """
        self.use_pensieve_api = use_pensieve_api
        self._pensieve_client = None
        self._api_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # Check API health every 30 seconds
        
        # Initialize intelligent caching
        from autotasktracker.pensieve.cache_manager import get_cache_manager
        self.cache = get_cache_manager()
        
        if db_path is None:
            if use_pensieve_api:
                try:
                    pensieve_config = get_pensieve_config()
                    self.db_path = pensieve_config.database_path
                    self._pensieve_client = get_pensieve_client()
                    self._api_healthy = self._pensieve_client.is_healthy()
                    logger.info(f"Using Pensieve API for database access (healthy: {self._api_healthy})")
                except Exception as e:
                    logger.warning(f"Failed to initialize Pensieve client, falling back to direct DB: {e}")
                    config = get_config()
                    self.db_path = config.get_db_path()
            else:
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
        
        # Initialize database with optimizations (skip if using Pensieve API)
        if not (self.use_pensieve_api and self._pensieve_client):
            self._initialize_database()
            # Create initial connections
            self._warm_up_pool()
        else:
            logger.info("Skipping SQLite initialization - using Pensieve API")
    
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
                logger.debug(f"Created index: {index_sql.split()[-0]}")
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
            # Pool empty and connection invalid, create new one
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
            # Connection invalid and pool full, close it
            try:
                conn.close()
            except sqlite3.Error as e:
                logger.debug(f"Failed to close connection: {e}")
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
                    except sqlite3.Error as e:
                        logger.debug(f"Failed to close write connection: {e}")
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
            except (sqlite3.Error, Exception) as e:
                logger.debug(f"Failed to close readonly pool connection: {e}")
        
        # Close read-write pool
        while not self._readwrite_pool.empty():
            try:
                conn = self._readwrite_pool.get_nowait()
                conn.close()
            except (sqlite3.Error, Exception) as e:
                logger.debug(f"Failed to close readwrite pool connection: {e}")
        
        with self._pool_lock:
            self._active_connections = 0
        
        logger.info("Closed all database connections")
    
    def _check_api_health(self) -> bool:
        """Check API health with caching to avoid excessive calls."""
        current_time = time.time()
        
        # Use cached health status if within interval
        if current_time - self._last_health_check < self._health_check_interval:
            return self._api_healthy
        
        # Check health and update cache
        if self._pensieve_client:
            self._api_healthy = self._pensieve_client.is_healthy()
            self._last_health_check = current_time
            
        return self._api_healthy
    
    def get_entities_via_api(self, limit: int = 100, processed_only: bool = False) -> List[Dict[str, Any]]:
        """Get entities using Pensieve API with intelligent caching.
        
        Args:
            limit: Maximum number of entities to return
            processed_only: Only return processed entities
            
        Returns:
            List of entity dictionaries
        """
        if not self.use_pensieve_api or not self._pensieve_client:
            return []
        
        # Create cache key
        cache_key = f"entities_limit_{limit}_processed_{processed_only}"
        
        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for entities (limit={limit}, processed_only={processed_only})")
            return cached_result
        
        try:
            if not self._check_api_health():
                logger.warning("Pensieve service not healthy, falling back to direct DB access")
                return []
            
            entities = self._pensieve_client.get_entities(limit=limit)
            
            # Convert to dict format compatible with existing code
            result = []
            for entity in entities:
                entity_dict = {
                    'id': entity.id,
                    'filepath': entity.filepath,
                    'filename': entity.filename,
                    'created_at': entity.created_at,
                    'file_created_at': entity.file_created_at,
                    'last_scan_at': entity.last_scan_at,
                    'file_type_group': entity.file_type_group,
                    'metadata': entity.metadata or {}
                }
                result.append(entity_dict)
                
                # Cache individual entities for faster access
                self.cache.set(f"entity_{entity.id}", entity_dict, ttl=600)
            
            # Filter for processed entities if requested
            if processed_only:
                result = [e for e in result if e['last_scan_at'] is not None]
            
            # Cache the result
            self.cache.set(cache_key, result, ttl=300)  # 5-minute cache
            
            # Warm cache with entity data
            self.cache.warm_cache(result)
            
            logger.info(f"Retrieved {len(result)} entities via Pensieve API")
            return result
            
        except PensieveAPIError as e:
            logger.error(f"Pensieve API error: {e.message}")
            return []
        except Exception as e:
            logger.error(f"Error getting entities via API: {e}")
            return []
    
    def get_entities_objects_via_api(self, limit: int = 100, processed_only: bool = False):
        """Get entities as proper entity objects using Pensieve API.
        
        Args:
            limit: Maximum number of entities to return
            processed_only: Only return processed entities
            
        Returns:
            List of PensieveEntity objects
        """
        from autotasktracker.pensieve.api_client import PensieveEntity
        
        if not self.use_pensieve_api or not self._pensieve_client:
            return []
        
        try:
            if not self._check_api_health():
                logger.warning("Pensieve service not healthy, falling back to direct DB access")
                return []
            
            entities = self._pensieve_client.get_entities(limit=limit)
            
            # Filter for processed entities if requested
            if processed_only:
                entities = [e for e in entities if e.last_scan_at is not None]
            
            logger.info(f"Retrieved {len(entities)} entity objects via Pensieve API")
            return entities
            
        except PensieveAPIError as e:
            logger.error(f"Pensieve API error: {e.message}")
            return []
        except Exception as e:
            logger.error(f"Failed to get entities via API: {e}")
            return []
    
    def get_frames_via_api(self, limit: int = 100, processed_only: bool = False) -> List[Dict[str, Any]]:
        """Get frames using Pensieve API (legacy wrapper).
        
        DEPRECATED: Use get_entities_via_api() instead for better alignment with Pensieve API.
        
        Args:
            limit: Maximum number of frames to return
            processed_only: Only return processed frames
            
        Returns:
            List of frame dictionaries
        """
        logger.warning("get_frames_via_api() is deprecated, use get_entities_via_api() for better API alignment")
        
        entities = self.get_entities_via_api(limit=limit, processed_only=processed_only)
        
        # Convert entities to frame format for backward compatibility
        frames = []
        for entity in entities:
            frames.append({
                'id': entity['id'],
                'filepath': entity['filepath'],
                'timestamp': entity['created_at'],
                'created_at': entity['created_at'],
                'processed_at': entity['last_scan_at'],
                'metadata': entity['metadata']
            })
        
        return frames
    
    def get_entity_metadata_via_api(self, entity_id: int, key: Optional[str] = None) -> Dict[str, Any]:
        """Get entity metadata using Pensieve API.
        
        Args:
            entity_id: Entity ID
            key: Specific metadata key
            
        Returns:
            Metadata dictionary
        """
        if not self.use_pensieve_api or not self._pensieve_client:
            return {}
        
        try:
            return self._pensieve_client.get_entity_metadata(entity_id, key)
        except Exception as e:
            logger.error(f"Failed to get metadata via API: {e}")
            return {}
    
    def get_frame_metadata_via_api(self, frame_id: int, key: Optional[str] = None) -> Dict[str, Any]:
        """Get frame metadata using Pensieve API (legacy wrapper).
        
        DEPRECATED: Use get_entity_metadata_via_api() instead for better alignment with Pensieve API.
        
        Args:
            frame_id: Frame ID
            key: Specific metadata key
            
        Returns:
            Metadata dictionary
        """
        logger.warning("get_frame_metadata_via_api() is deprecated, use get_entity_metadata_via_api() for better API alignment")
        return self.get_entity_metadata_via_api(frame_id, key)
    
    def store_entity_metadata_via_api(self, entity_id: int, key: str, value: Any) -> bool:
        """Store entity metadata using Pensieve API.
        
        Args:
            entity_id: Entity ID
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if successful
        """
        if not self.use_pensieve_api or not self._pensieve_client:
            return False
        
        try:
            return self._pensieve_client.store_entity_metadata(entity_id, key, value)
        except Exception as e:
            logger.error(f"Failed to store metadata via API: {e}")
            return False
    
    def store_frame_metadata_via_api(self, frame_id: int, key: str, value: Any) -> bool:
        """Store frame metadata using Pensieve API (legacy wrapper).
        
        DEPRECATED: Use store_entity_metadata_via_api() instead for better alignment with Pensieve API.
        
        Args:
            frame_id: Frame ID
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if successful
        """
        logger.warning("store_frame_metadata_via_api() is deprecated, use store_entity_metadata_via_api() for better API alignment")
        return self.store_entity_metadata_via_api(frame_id, key, value)
    
    def fetch_tasks(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100,
                   offset: int = 0) -> pd.DataFrame:
        """
        Fetch tasks (screenshots with metadata) with API-first approach and intelligent caching.
        
        Args:
            start_date: Start date filter
            end_date: End date filter  
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            DataFrame with task data
        """
        # Create cache key for this query
        cache_key = f"fetch_tasks_{start_date}_{end_date}_{limit}_{offset}"
        
        # Try cache first for exact same query
        cached_df = self.cache.get(cache_key)
        if cached_df is not None:
            logger.debug(f"Cache hit for fetch_tasks query")
            return cached_df
        
        # Try API-first approach with new data endpoints
        if self.use_pensieve_api and self._pensieve_client and self._check_api_health():
            try:
                # Use the new screenshots endpoint which supports date filtering
                screenshots = self._pensieve_client.get_screenshots(
                    limit=limit, 
                    offset=offset,
                    start_date=start_date.isoformat() if start_date else None,
                    end_date=end_date.isoformat() if end_date else None
                )
                
                if screenshots:
                    # Convert screenshots to DataFrame format
                    df_data = []
                    for screenshot in screenshots:
                        # Extract metadata for compatibility
                        metadata = screenshot.get('metadata', {})
                        ocr_text = metadata.get('ocr_result', '')
                        active_window = metadata.get('active_window', '')
                        
                        df_data.append({
                            'id': screenshot['id'],
                            'filepath': screenshot['filepath'],
                            'filename': screenshot.get('filename', ''),
                            'created_at': screenshot['created_at'],
                            'file_created_at': screenshot.get('file_created_at'),
                            'last_scan_at': screenshot.get('last_scan_at'),
                            'file_type_group': screenshot.get('file_type_group', 'image'),
                            'ocr_text': ocr_text,
                            'active_window': active_window
                        })
                    
                    df = pd.DataFrame(df_data)
                    
                    # Apply schema adaptation
                    from autotasktracker.core import PensieveSchemaAdapter
                    df = PensieveSchemaAdapter.adapt_dataframe(df)
                    
                    # Cache the result
                    self.cache.set(cache_key, df, ttl=300)
                    
                    logger.info(f"Fetched {len(df)} tasks via Pensieve API")
                    return df
                    
            except Exception as e:
                logger.warning(f"API fetch failed, falling back to SQLite: {e}")
        
        # Fallback to SQLite with Pensieve schema adapter
        from autotasktracker.core import PensieveSchemaAdapter
        
        query = PensieveSchemaAdapter.adapt_fetch_tasks_query()
        params = []
        
        if start_date:
            query += " AND e.created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND e.created_at <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                # Apply schema adaptation to add missing columns
                df = PensieveSchemaAdapter.adapt_dataframe(df)
                
                # Cache the result
                self.cache.set(cache_key, df, ttl=300)
                
                logger.info(f"Fetched {len(df)} tasks via SQLite fallback")
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
        
        # Use Pensieve schema adapter
        from autotasktracker.core import PensieveSchemaAdapter
        query = PensieveSchemaAdapter.get_screenshot_count_query()
        
        try:
            start_timer("screenshot_count_query")
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date.isoformat(),))
                result = cursor.fetchone()
                duration = end_timer("screenshot_count_query")
                record_database_query(duration, "count")
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
        # Use Pensieve schema adapter
        from autotasktracker.core import PensieveSchemaAdapter
        query = PensieveSchemaAdapter.get_unique_applications_query()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (start_date.isoformat(), end_date.isoformat()))
                return [row["active_window"] for row in cursor.fetchall()]
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
        # Use Pensieve schema adapter
        from autotasktracker.core import PensieveSchemaAdapter
        query = PensieveSchemaAdapter.get_activity_summary_query()
        
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
            LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = "ocr_result"
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "active_window"
            LEFT JOIN metadata_entries me3 ON e.id = me3.entity_id AND me3.key IN ('minicpm_v_result', "vlm_structured")
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
        # Use Pensieve schema adapter
        from autotasktracker.core import PensieveSchemaAdapter
        query = PensieveSchemaAdapter.get_ai_coverage_query()
        
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
        # Use Pensieve schema adapter
        from autotasktracker.core import PensieveSchemaAdapter
        query = PensieveSchemaAdapter.get_search_activities_query()
        
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