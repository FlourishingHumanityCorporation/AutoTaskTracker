"""
PostgreSQL-only database management module for AutoTaskTracker.
Provides centralized PostgreSQL database access and query methods.
"""

import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
import pandas as pd
from contextlib import contextmanager
import logging
from urllib.parse import urlparse
from autotasktracker.config import get_config
from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.config_reader import get_pensieve_config
from autotasktracker.core.exceptions import DatabaseError, PensieveIntegrationError

# PostgreSQL imports (required)
try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extras import RealDictCursor
    from psycopg2 import sql, Error as PostgreSQLError
    POSTGRESQL_AVAILABLE = True
except ImportError:
    raise ImportError("PostgreSQL dependencies required. Install: pip install psycopg2-binary")

# Import performance monitoring (with fallback if not available)
try:
    from autotasktracker.pensieve.performance_monitor import record_database_query, start_timer, end_timer
    PERFORMANCE_MONITORING_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
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
    """PostgreSQL-only database manager with connection pooling and performance optimizations."""
    
    def __init__(self, db_path: Optional[str] = None, use_pensieve_api: bool = True):
        """
        Initialize PostgreSQL DatabaseManager with connection pooling.
        
        Args:
            db_path: PostgreSQL URI. If None, uses config.
            use_pensieve_api: Whether to use Pensieve API when available.
        """
        self.use_pensieve_api = use_pensieve_api
        self._pensieve_client = None
        self._api_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # Check API health every 30 seconds
        
        # PostgreSQL connection pool
        self._postgresql_pool = None
        self._postgresql_config = None
        self._postgresql_initialized = False
        
        # Initialize intelligent caching
        from autotasktracker.pensieve.cache_manager import get_cache_manager
        self.cache = get_cache_manager()
        
        if db_path is None:
            # Always use AutoTaskTracker config for PostgreSQL URL
            config = get_config()
            self.db_path = config.get_database_url()
            logger.info(f"Using AutoTaskTracker PostgreSQL database: {self.db_path}")
            
            # Try Pensieve API for additional features if available
            if use_pensieve_api:
                try:
                    self._pensieve_client = get_pensieve_client()
                    self._api_healthy = self._pensieve_client.is_healthy()
                    logger.info(f"Pensieve API available (healthy: {self._api_healthy})")
                except Exception as e:
                    logger.debug(f"Pensieve API not available: {e}")
                    self._api_healthy = False
        else:
            self.db_path = db_path
        
        # Validate PostgreSQL URI
        if not self.db_path.startswith(('postgresql://', 'postgres://')):
            raise DatabaseError(f"Invalid PostgreSQL URI: {self.db_path}")
    
    def _ensure_postgresql_initialized(self):
        """Ensure PostgreSQL connection pool is initialized (lazy initialization)."""
        if not self._postgresql_initialized:
            self._initialize_postgresql()
            self._postgresql_initialized = True

    def _initialize_postgresql(self):
        """Initialize PostgreSQL connection pool."""
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
                maxconn=10,
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
    
    @contextmanager
    def _get_postgresql_connection(self, readonly: bool = True):
        """Get PostgreSQL connection from pool."""
        self._ensure_postgresql_initialized()
        
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
    
    @contextmanager
    def get_connection(self, readonly: bool = True):
        """Get database connection."""
        with self._get_postgresql_connection(readonly) as conn:
            yield conn
    
    def test_connection(self) -> bool:
        """Test if PostgreSQL connection can be established."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    def get_database_type(self) -> str:
        """Get database type."""
        return "postgresql"
    
    def fetch_tasks(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100,
                   offset: int = 0,
                   include_ai_fields: bool = False,
                   time_filter: Optional[str] = None) -> pd.DataFrame:
        """Fetch tasks from PostgreSQL database."""
        
        timer_name = f"fetch_tasks_{limit}_{offset}"
        start_timer(timer_name)
        
        try:
            # Handle time_filter convenience parameter
            if time_filter and not start_date:
                start_date = self._get_start_date_from_filter(time_filter)
            
            # Build query - simple version that works with current schema
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
                e.filepath IS NOT NULL
            """
            
            params = []
            
            # Add date filters
            if start_date:
                query += " AND e.created_at >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND e.created_at <= %s"
                params.append(end_date)
            
            query += " ORDER BY e.created_at DESC LIMIT %s"
            params.append(limit)
            
            if offset > 0:
                query += " OFFSET %s"
                params.append(offset)
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    if results:
                        df = pd.DataFrame([dict(row) for row in results])
                        return df
                    else:
                        return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
            raise DatabaseError(f"Failed to fetch tasks: {e}") from e
        finally:
            duration = end_timer(timer_name)
            record_database_query(duration, "fetch_tasks")
    
    def _get_start_date_from_filter(self, time_filter: str) -> Optional[datetime]:
        """Convert time filter string to start date."""
        now = datetime.now()
        
        if time_filter == "Today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "Last 24 Hours":
            return now - timedelta(days=1)
        elif time_filter == "Last 7 Days":
            return now - timedelta(days=7)
        elif time_filter == "Last 30 Days":
            return now - timedelta(days=30)
        elif time_filter == "Last Hour":
            return now - timedelta(hours=1)
        elif time_filter == "Last 15 Minutes":
            return now - timedelta(minutes=15)
        else:
            return None
    
    def get_entity_count(self) -> int:
        """Get total number of entities."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM entities")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get entity count: {e}")
            return 0
    
    def get_metadata_count(self) -> int:
        """Get total number of metadata entries."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM metadata_entries")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get metadata count: {e}")
            return 0
    
    def close_all_connections(self):
        """Close all pooled connections."""
        logger.info("Closing PostgreSQL connections")
        
        if hasattr(self, '_postgresql_initialized') and self._postgresql_initialized and self._postgresql_pool:
            try:
                self._postgresql_pool.closeall()
                logger.info("PostgreSQL connection pool closed")
            except Exception as e:
                logger.warning(f"Error closing PostgreSQL pool: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        return {
            "type": "postgresql",
            "config": self._postgresql_config,
            "pool_active": hasattr(self, '_postgresql_initialized') and self._postgresql_initialized and self._postgresql_pool is not None,
            "db_path": self.db_path
        }


# Create a default instance
_default_db_manager = None

def get_default_db_manager() -> DatabaseManager:
    """Get the default DatabaseManager instance."""
    global _default_db_manager
    if _default_db_manager is None:
        _default_db_manager = DatabaseManager()
    return _default_db_manager