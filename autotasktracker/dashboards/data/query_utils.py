"""
Database query utilities for repository classes.

Extracted from repositories.py to improve maintainability and reusability.
"""

import logging
import time
import pandas as pd
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for API failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                return False
            return True
        return False
    
    def record_failure(self, error_message: str):
        """Record an API failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == 'HALF_OPEN':
            self.reset()
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'
        logger.info("Circuit breaker reset to closed state")


class QueryRouter:
    """Routes queries to appropriate endpoints based on query type."""
    
    def __init__(self):
        """Initialize query router."""
        self.circuit_breaker = CircuitBreaker()
    
    def classify_query(self, query: str) -> str:
        """Classify query type for routing."""
        query_lower = query.lower().strip()
        
        if self._is_search_query(query):
            return 'search'
        elif self._is_entity_listing_query(query):
            return 'entity_listing'
        elif self._is_entity_specific_query(query):
            return 'entity_specific'
        elif self._is_data_query(query):
            return 'data'
        else:
            return 'generic'
    
    def _is_data_query(self, query: str) -> bool:
        """Check if query is a data retrieval query."""
        data_keywords = ['SELECT', 'COUNT', 'AVG', 'SUM', 'GROUP BY']
        query_upper = query.upper()
        return any(keyword in query_upper for keyword in data_keywords)
    
    def _is_search_query(self, query: str) -> bool:
        """Check if query is a search operation."""
        return ('LIKE' in query.upper() or 
                'MATCH' in query.upper() or
                'FTS' in query.upper())
    
    def _is_entity_listing_query(self, query: str) -> bool:
        """Check if query is listing entities."""
        query_upper = query.upper()
        return ('FROM entities' in query_upper and 
                'LIMIT' in query_upper and
                'ORDER BY' in query_upper)
    
    def _is_entity_specific_query(self, query: str) -> bool:
        """Check if query is for specific entity."""
        query_upper = query.upper()
        return ('WHERE' in query_upper and 
                ('entity_id' in query_upper or 'entities.id' in query_upper))
    
    def should_use_api(self, query_type: str) -> bool:
        """Determine if API should be used for this query type."""
        if self.circuit_breaker.is_open():
            return False
        
        # API is preferred for these query types
        api_preferred = ['search', 'entity_listing', 'entity_specific']
        return query_type in api_preferred
    
    def record_api_result(self, success: bool, error_message: str = None):
        """Record API call result for circuit breaker."""
        if success:
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure(error_message or "API call failed")


class QueryCache:
    """Simple in-memory query cache with TTL."""
    
    def __init__(self, default_ttl: int = 300):
        """Initialize query cache."""
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get cached query result."""
        if cache_key in self.cache:
            result, expiry_time = self.cache[cache_key]
            if time.time() < expiry_time:
                return result.copy()  # Return copy to avoid mutation
            else:
                del self.cache[cache_key]
        return None
    
    def set(self, cache_key: str, result: pd.DataFrame, ttl: int = None):
        """Cache query result with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        expiry_time = time.time() + ttl
        self.cache[cache_key] = (result.copy(), expiry_time)
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries."""
        if pattern is None:
            self.cache.clear()
            logger.info("Query cache cleared completely")
        else:
            # Simple pattern matching - remove keys containing pattern
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        expired_entries = 0
        current_time = time.time()
        
        for _, (_, expiry_time) in self.cache.items():
            if current_time >= expiry_time:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries
        }


class DatabaseQueryExecutor:
    """Executes database queries with fallback and error handling."""
    
    def __init__(self, db_manager, query_cache: QueryCache = None):
        """Initialize query executor."""
        self.db_manager = db_manager
        self.query_cache = query_cache or QueryCache()
        self.query_router = QueryRouter()
        self.performance_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'api_queries': 0,
            'sqlite_queries': 0,
            'avg_query_time': 0.0
        }
    
    def execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pd.DataFrame:
        """Execute query with caching and fallback."""
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(query, params)
            
            # Try cache first
            cached_result = self.query_cache.get(cache_key)
            if cached_result is not None:
                self.performance_stats['cache_hits'] += 1
                return cached_result
            
            # Determine query routing
            query_type = self.query_router.classify_query(query)
            
            # Try API first if appropriate
            result = None
            if self.query_router.should_use_api(query_type):
                result = self._execute_api_query(query, params, query_type)
                if result is not None:
                    self.performance_stats['api_queries'] += 1
                    self.query_router.record_api_result(True)
            
            # Fallback to SQLite
            if result is None:
                result = self._execute_sqlite_query(query, params)
                self.performance_stats['sqlite_queries'] += 1
                if self.query_router.should_use_api(query_type):
                    self.query_router.record_api_result(False, "API query failed")
            
            # Cache successful result
            if result is not None and not result.empty:
                self.query_cache.set(cache_key, result, cache_ttl)
            
            # Update performance stats
            query_time = time.time() - start_time
            self.performance_stats['total_queries'] += 1
            self.performance_stats['avg_query_time'] = (
                (self.performance_stats['avg_query_time'] * (self.performance_stats['total_queries'] - 1) + query_time) 
                / self.performance_stats['total_queries']
            )
            
            return result if result is not None else pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return pd.DataFrame()
    
    def _generate_cache_key(self, query: str, params: tuple) -> str:
        """Generate cache key for query and parameters."""
        import hashlib
        query_hash = hashlib.md5(f"{query}_{params}".encode(), usedforsecurity=False).hexdigest()
        return f"query_{query_hash}"
    
    def _execute_api_query(self, query: str, params: tuple, query_type: str) -> Optional[pd.DataFrame]:
        """Execute query via Pensieve API."""
        try:
            # This would interface with the actual Pensieve API
            # For now, return None to indicate API not available
            return None
        except Exception as e:
            logger.debug(f"API query failed: {e}")
            return None
    
    def _execute_sqlite_query(self, query: str, params: tuple) -> pd.DataFrame:
        """Execute query directly against SQLite."""
        try:
            with self.db_manager.get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            logger.error(f"SQLite query failed: {e}")
            return pd.DataFrame()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        stats = self.performance_stats.copy()
        stats['cache_stats'] = self.query_cache.get_stats()
        stats['circuit_breaker_state'] = self.query_router.circuit_breaker.state
        return stats