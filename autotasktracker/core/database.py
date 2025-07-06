"""
Database management module for AutoTaskTracker.
Provides centralized database access and query methods.
"""

import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from queue import Queue, Empty
import pandas as pd
from contextlib import contextmanager
import logging
from urllib.parse import urlparse
from autotasktracker.config import get_config
from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.config_reader import get_pensieve_config
from autotasktracker.core.exceptions import DatabaseError, PensieveIntegrationError

# PostgreSQL imports with fallback
try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extras import RealDictCursor
    from psycopg2 import sql, Error as PostgreSQLError
    POSTGRESQL_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("PostgreSQL dependencies not available. Install psycopg2-binary for PostgreSQL support.")
    POSTGRESQL_AVAILABLE = False
    PostgreSQLError = Exception  # Fallback for type hints

# Import performance monitoring (with fallback if not available)
try:
    from autotasktracker.pensieve.performance_monitor import record_database_query, start_timer, end_timer
    PERFORMANCE_MONITORING_AVAILABLE = True
except ImportError:
    logger.debug("Performance monitoring not available")
    PERFORMANCE_MONITORING_AVAILABLE = False
    
    def record_database_query(duration_ms: float, query_type: str = "unknown"):
        pass
    
    def start_timer(timer_name: str):
        pass
    
    def end_timer(timer_name: str, metadata=None) -> float:
        return 0.0


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections with connection pooling and performance optimizations.
    
    Supports both SQLite and PostgreSQL backends with automatic detection.
    """
    
    def __init__(self, db_path: Optional[str] = None, use_pensieve_api: bool = True):
        """
        Initialize DatabaseManager with connection pooling and Pensieve integration.
        
        Args:
            db_path: Path to the database or PostgreSQL URI. If None, uses Pensieve config.
            use_pensieve_api: Whether to use Pensieve API when available.
        """
        self.use_pensieve_api = use_pensieve_api
        self._pensieve_client = None
        self._api_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # Check API health every 30 seconds
        
        # Database type detection
        self._is_postgresql = False
        self._postgresql_pool = None
        self._postgresql_config = None
        
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
                except (ImportError, AttributeError) as e:
                    logger.warning(f"Pensieve module not properly installed: {e}")
                    self._api_healthy = False
                    config = get_config()
                    self.db_path = config.get_db_path()
                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"Failed to connect to Pensieve API: {e}")
                    self._api_healthy = False
                    config = get_config()
                    self.db_path = config.get_db_path()
                except PensieveAPIError as e:
                    logger.warning(f"Pensieve API error during initialization: {e}")
                    config = get_config()
                    self.db_path = config.get_db_path()
                except Exception as e:
                    logger.warning(f"Unexpected error initializing Pensieve client: {e}")
                    config = get_config()
                    self.db_path = config.get_db_path()
            else:
                config = get_config()
                self.db_path = config.get_db_path()
        else:
            self.db_path = db_path
        
        # Detect database type and configure accordingly
        self._detect_database_type()
        if self._is_postgresql:
            self._initialize_postgresql()
        else:
            # Initialize SQLite connection pools
            self._initialize_sqlite()
        
    def _detect_database_type(self):
        """Detect whether the database is PostgreSQL or SQLite."""
        if self.db_path and isinstance(self.db_path, str):
            # Check if the path contains a PostgreSQL URI (even if it's a file path)
            if ('postgresql://' in self.db_path or 'postgres://' in self.db_path):
                # Extract the actual PostgreSQL URI from the path
                if self.db_path.startswith('postgresql://') or self.db_path.startswith('postgres://'):
                    # Direct URI
                    uri = self.db_path
                else:
                    # URI embedded in file path - extract it
                    import re
                    match = re.search(r'postgres(?:ql)?://[^/\s]+/\w+', self.db_path)
                    if match:
                        uri = match.group(0)
                    else:
                        # Fallback to the full path for now
                        uri = self.db_path
                
                self.db_path = uri  # Use the extracted URI
                self._is_postgresql = True
                logger.info(f"Detected PostgreSQL database: {uri}")
            else:
                self._is_postgresql = False
                logger.info("Detected SQLite database")
        else:
            self._is_postgresql = False
            logger.info("Defaulting to SQLite database")
    
    def _initialize_postgresql(self):
        """Initialize PostgreSQL connection pool."""
        if not POSTGRESQL_AVAILABLE:
            raise DatabaseError("PostgreSQL dependencies not available. Install psycopg2-binary")
        
        try:
            # Parse PostgreSQL URI
            parsed = urlparse(self.db_path)
            self._postgresql_config = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/') or 'postgres',
                'user': parsed.username or 'postgres',
                'password': parsed.password or ''
            }
            
            # Create connection pool with timeouts
            self._postgresql_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                connect_timeout=10,
                **self._postgresql_config
            )
            
            logger.info(f"PostgreSQL connection pool initialized for {self._postgresql_config['host']}:{self._postgresql_config['port']}/{self._postgresql_config['database']}")
            
            # Test connection
            conn = self._postgresql_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    logger.info(f"PostgreSQL version: {version}")
            finally:
                self._postgresql_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise DatabaseError(f"PostgreSQL initialization failed: {e}") from e
    
    def _initialize_sqlite(self):
        """Initialize SQLite connection pools."""
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
        except sqlite3.Error as e:
            logger.warning(f"Database error during connection pool warm-up: {e}")
        except OSError as e:
            logger.warning(f"OS error during connection pool warm-up (check disk space/permissions): {e}")
    
    def _create_connection(self, readonly: bool = False) -> sqlite3.Connection:
        """Create a new database connection with optimizations."""
        # Check if db_path is actually a PostgreSQL URI
        if 'postgresql://' in str(self.db_path):
            raise DatabaseError(
                f"Cannot create SQLite connection to PostgreSQL URI: {self.db_path}. "
                "Use Pensieve API methods instead."
            )
            
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
            raise DatabaseError(f"SQLite connection failed: {e}") from e
    
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
        if self._is_postgresql:
            with self._get_postgresql_connection(readonly) as conn:
                yield conn
            return
        
        conn = None
        try:
            conn = self._get_pooled_connection(readonly)
            yield conn
        except sqlite3.OperationalError as e:
            logger.error(f"SQLite connection error: {e}")
            raise DatabaseError(f"SQLite connection failed: {e}") from e
        except sqlite3.DatabaseError as e:
            logger.error(f"SQLite database error: {e}")
            raise DatabaseError(f"SQLite operation failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise DatabaseError(f"Unexpected database error: {e}") from e
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
    
    @contextmanager
    def _get_postgresql_connection(self, readonly: bool = True):
        """Get PostgreSQL connection from pool."""
        if not self._postgresql_pool:
            raise DatabaseError("PostgreSQL pool not initialized")
        
        conn = None
        try:
            conn = self._postgresql_pool.getconn()
            conn.autocommit = readonly  # Read-only queries use autocommit
            yield conn
        except PostgreSQLError as e:
            logger.error(f"PostgreSQL connection error: {e}")
            raise DatabaseError(f"PostgreSQL connection failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected PostgreSQL error: {e}")
            raise DatabaseError(f"Unexpected PostgreSQL error: {e}") from e
        finally:
            if conn:
                try:
                    self._postgresql_pool.putconn(conn)
                except Exception as e:
                    logger.debug(f"Failed to return PostgreSQL connection to pool: {e}")
    
    def test_connection(self) -> bool:
        """Test if database connection can be established."""
        # If using Pensieve API, test API health instead of SQLite connection
        if self.use_pensieve_api and self._pensieve_client:
            try:
                return self._check_api_health()
            except Exception as e:
                logger.debug(f"Pensieve API health check failed: {e}")
                return False
        
        # Test SQLite connection
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                return True
        except (sqlite3.OperationalError, DatabaseError, PensieveIntegrationError) as e:
            logger.debug(f"SQLite connection test failed: {e}")
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
                   offset: int = 0,
                   include_ai_fields: bool = False,
                   time_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Unified method to fetch tasks with optional AI fields and time filters.
        Consolidates fetch_tasks, fetch_tasks_by_time_filter, and fetch_tasks_with_ai.
        
        Args:
            start_date: Start date filter
            end_date: End date filter  
            limit: Maximum number of records to return
            offset: Number of records to skip
            include_ai_fields: If True, includes VLM descriptions and embedding status
            time_filter: Convenience time filter ("Last 15 Minutes", "Today", etc.)
            
        Returns:
            DataFrame with task data
        """
        # Handle time_filter convenience parameter
        if time_filter and not start_date:
            start_date = self._get_start_date_from_filter(time_filter)
        
        # Create cache key for this query
        cache_key = f"fetch_tasks_{start_date}_{end_date}_{limit}_{offset}_{include_ai_fields}"
        
        # Try cache first for exact same query
        cached_df = self.cache.get(cache_key)
        if cached_df is not None:
            logger.debug(f"Cache hit for fetch_tasks query")
            return cached_df
        
        # Try API-first approach (if no date filters and not requesting AI fields)
        if self.use_pensieve_api and not start_date and not end_date and offset == 0 and not include_ai_fields:
            try:
                entities = self.get_entities_via_api(limit=limit, processed_only=False)
                if entities:
                    # Convert entities to DataFrame format
                    df_data = []
                    for entity in entities:
                        # Extract metadata for compatibility
                        metadata = entity.get('metadata', {})
                        ocr_text = metadata.get('ocr_result', '')
                        active_window = metadata.get('active_window', '')
                        
                        df_data.append({
                            'id': entity['id'],
                            'filepath': entity['filepath'],
                            'filename': entity.get('filename', ''),
                            'created_at': entity['created_at'],
                            'file_created_at': entity.get('file_created_at'),
                            'last_scan_at': entity.get('last_scan_at'),
                            'file_type_group': entity.get('file_type_group', 'image'),
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
        
        # Use different query based on whether AI fields are requested
        if include_ai_fields:
            # Use the more complex query with AI metadata joins
            query = self._get_ai_enhanced_query()
        else:
            # Use standard query from schema adapter
            query = PensieveSchemaAdapter.adapt_fetch_tasks_query()
        
        params = []
        
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
        
        if self._is_postgresql:
            # PostgreSQL uses $1, $2 syntax and different LIMIT/OFFSET
            query += " ORDER BY e.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        else:
            # SQLite uses ? parameters
            query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        try:
            with self.get_connection() as conn:
                if self._is_postgresql:
                    # PostgreSQL execution with psycopg2
                    df = self._execute_postgresql_query(conn, query, params)
                else:
                    # SQLite execution
                    df = pd.read_sql_query(query, conn, params=params)
                
                # Apply schema adaptation to add missing columns
                df = PensieveSchemaAdapter.adapt_dataframe(df)
                
                # Cache the result
                self.cache.set(cache_key, df, ttl=300)
                
                db_type = "PostgreSQL" if self._is_postgresql else "SQLite"
                logger.info(f"Fetched {len(df)} tasks via {db_type}")
                return df
                
        except DatabaseError as e:
            logger.error(f"Database connection error: {e}")
            return pd.DataFrame()
        except pd.io.sql.DatabaseError as e:
            logger.error(f"Database error fetching tasks: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Unexpected error fetching tasks: {e}")
            return pd.DataFrame()
    
    def fetch_tasks_by_time_filter(self, time_filter: str, limit: int = 100) -> pd.DataFrame:
        """
        Convenience method for fetching tasks by time filter.
        Now delegates to the unified fetch_tasks method.
        
        Args:
            time_filter: One of "Last 15 Minutes", "Last Hour", "Today", 
                        "Last 24 Hours", "Last 7 Days", "All Time"
            limit: Maximum number of records
            
        Returns:
            DataFrame with task data
        """
        return self.fetch_tasks(time_filter=time_filter, limit=limit)
    
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
        Convenience method for fetching tasks with AI fields.
        Now delegates to the unified fetch_tasks method.
        
        Args:
            start_date: Start date filter
            end_date: End date filter  
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            DataFrame with task and AI data
        """
        return self.fetch_tasks(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            include_ai_fields=True
        )
    
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
    
    def _get_start_date_from_filter(self, time_filter: str) -> datetime:
        """Convert time filter string to start date."""
        now = datetime.now()
        
        time_filters = {
            "Last 15 Minutes": now - timedelta(minutes=15),
            "Last Hour": now - timedelta(hours=1),
            "Today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "Last 24 Hours": now - timedelta(days=1),
            "Last 7 Days": now - timedelta(days=7),
            "All Time": datetime(2000, 1, 1)
        }
        
        return time_filters.get(time_filter, datetime(2000, 1, 1))
    
    def _get_ai_enhanced_query(self) -> str:
        """Get SQL query for fetching tasks with AI metadata."""
        return """
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
    
    def close_all_connections(self):
        """Close all pooled connections."""
        logger.info("Closing all database connections")
        
        if self._is_postgresql:
            if self._postgresql_pool:
                try:
                    self._postgresql_pool.closeall()
                    logger.info("PostgreSQL connection pool closed")
                except Exception as e:
                    logger.warning(f"Error closing PostgreSQL pool: {e}")
        else:
            # Close SQLite connections
            while not self._readonly_pool.empty():
                try:
                    conn = self._readonly_pool.get_nowait()
                    conn.close()
                except (Empty, sqlite3.Error):
                    pass
            
            # Close read-write connections
            while not self._readwrite_pool.empty():
                try:
                    conn = self._readwrite_pool.get_nowait()
                    conn.close()
                except (Empty, sqlite3.Error):
                    pass
            
            with self._pool_lock:
                self._active_connections = 0

    def __del__(self):
        """Cleanup connections when object is destroyed."""
        try:
            self.close_all_connections()
        except Exception as e:
            logger.debug(f"Error during connection cleanup: {e}")
    
    def get_database_type(self) -> str:
        """Get the database type (postgresql or sqlite)."""
        return "postgresql" if self._is_postgresql else "sqlite"
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging."""
        if self._is_postgresql:
            return {
                "type": "postgresql",
                "config": self._postgresql_config,
                "pool_active": self._postgresql_pool is not None
            }
        else:
            return {
                "type": "sqlite",
                "path": self.db_path,
                "active_connections": self._active_connections,
                "wal_mode": self._wal_mode_enabled
            }

    def get_tables(self) -> List[str]:
        """Get list of tables in the database."""
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
            logger.error(f"Failed to get tables: {e}")
            return []
    
    def _execute_postgresql_query(self, conn, query: str, params: List[Any]) -> pd.DataFrame:
        """Execute a query on PostgreSQL and return DataFrame."""
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                # Handle empty result sets
                if cursor.description is None:
                    return pd.DataFrame()
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                # Convert to DataFrame
                if not rows:
                    # Return empty DataFrame with correct columns
                    return pd.DataFrame(columns=columns)
                
                data = []
                for row in rows:
                    data.append(dict(row))
                
                return pd.DataFrame(data)
                
        except PostgreSQLError as e:
            logger.error(f"PostgreSQL query error: {e}")
            raise DatabaseError(f"PostgreSQL query failed: {e}") from e


# Singleton instance for convenience
_default_db_manager = None


def get_default_db_manager() -> DatabaseManager:
    """Get the default database manager instance."""
    global _default_db_manager
    if _default_db_manager is None:
        _default_db_manager = DatabaseManager()
    return _default_db_manager