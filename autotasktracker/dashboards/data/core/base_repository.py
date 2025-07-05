"""Base repository with common functionality using composition pattern."""

import logging
import time
from typing import Optional, Dict, Any
import pandas as pd

from autotasktracker.core.database import DatabaseManager
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter
from autotasktracker.pensieve.api_client import PensieveAPIClient
from autotasktracker.dashboards.data.core.cache_coordinator import CacheCoordinator
from autotasktracker.dashboards.data.core.circuit_breaker import CircuitBreaker
from autotasktracker.dashboards.data.core.query_router import QueryRouter

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common functionality using composition pattern."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, use_pensieve: bool = True):
        self.db = db_manager or DatabaseManager()
        self.use_pensieve = use_pensieve
        self.pg_adapter = get_postgresql_adapter() if use_pensieve else None
        
        # Initialize Pensieve API client for REST operations
        try:
            self.api_client = PensieveAPIClient() if use_pensieve else None
        except Exception as e:
            logger.debug(f"PensieveAPIClient initialization failed: {e}")
            self.api_client = None
        
        # Initialize composed components
        self.cache_coordinator = CacheCoordinator()
        self.circuit_breaker = CircuitBreaker()
        self.query_router = QueryRouter(self.api_client, self.circuit_breaker)
        
        # Maintain backward compatibility with direct access to cache and performance stats
        self.cache = self.cache_coordinator.cache
        self.performance_stats = self.cache_coordinator.performance_stats
    
    def _execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pd.DataFrame:
        """Execute query with API-first approach, intelligent caching and error handling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        start_time = time.time()
        
        # Create cache key and try cache first
        cache_key = self.cache_coordinator.get_cache_key(query, params)
        cached_result = self.cache_coordinator.get_cached_result(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return self.cache_coordinator.restore_dataframe_from_cache(cached_result)
        
        # Try Pensieve API first for data queries
        if self.query_router.can_route_to_api(query):
            api_start = time.time()
            try:
                api_result = self.query_router.execute_api_query(query, params)
                if api_result is not None:
                    api_time = time.time() - api_start
                    self.cache_coordinator.record_api_request(api_time)
                    
                    # Cache the API result
                    self.cache_coordinator.set_cached_result(cache_key, api_result, ttl=cache_ttl)
                    logger.debug(f"API query successful: {api_result.shape} rows ({api_time:.3f}s)")
                    
                    total_time = time.time() - start_time
                    self.cache_coordinator.record_total_response_time(total_time)
                    return api_result
            except Exception as e:
                self.cache_coordinator.record_api_failure()
                logger.debug(f"API query failed, falling back to database: {e}")
        
        # Fallback to database
        return self._execute_database_query(query, params, cache_key, cache_ttl, start_time)
    
    def _execute_database_query(self, query: str, params: tuple, cache_key: str, 
                               cache_ttl: int, start_time: float) -> pd.DataFrame:
        """Execute query against database with fallback handling."""
        db_start = time.time()
        try:
            # Fallback to DatabaseManager's connection context manager
            with self.db.get_connection() as conn:
                # Check if query has complex JOINs that pandas struggles with
                query_lower = query.lower()
                has_complex_join = 'join' in query_lower and 'metadata_entries' in query_lower
                
                if has_complex_join:
                    # Use direct cursor for complex JOINs to avoid pandas issues
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    
                    # Fetch column names
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    # Fetch all rows
                    rows = cursor.fetchall()
                    
                    # Convert to DataFrame
                    result = pd.DataFrame(rows, columns=columns)
                    logger.debug(f"Used direct cursor for complex JOIN query")
                else:
                    # Use pandas for simple queries
                    result = pd.read_sql_query(query, conn, params=params)
                
                db_time = time.time() - db_start
                self.cache_coordinator.record_database_query(db_time)
                
                # Cache the result
                self.cache_coordinator.set_cached_result(cache_key, result, ttl=cache_ttl)
                logger.debug(f"Database query successful: {result.shape} rows ({db_time:.3f}s)")
                
                total_time = time.time() - start_time
                self.cache_coordinator.record_total_response_time(total_time)
                return result
        except Exception as e:
            self.cache_coordinator.record_database_failure()
            logger.error(f"Query execution failed: {e}")
            # Return empty DataFrame on error instead of raising
            return pd.DataFrame()
    
    # Delegate methods for backward compatibility
    def invalidate_cache(self, pattern: str = None):
        """Invalidate cached query results."""
        return self.cache_coordinator.invalidate_cache(pattern)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache_coordinator.get_cache_stats()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for API vs database usage."""
        return self.cache_coordinator.get_performance_stats()
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self.circuit_breaker.get_circuit_status()
    
    def reset_circuit_breaker(self, endpoint: str = 'general'):
        """Reset circuit breaker for an endpoint."""
        return self.circuit_breaker.reset_circuit(endpoint)