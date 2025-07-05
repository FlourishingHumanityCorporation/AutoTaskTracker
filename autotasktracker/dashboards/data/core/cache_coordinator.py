"""Cache coordination and performance monitoring for repository operations."""

import logging
from typing import Dict, Any, Optional
from autotasktracker.pensieve.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class CacheCoordinator:
    """Coordinates cache operations and performance monitoring for repositories."""
    
    def __init__(self):
        self.cache = get_cache_manager()
        
        # Performance monitoring
        self.performance_stats = {
            'api_requests': 0,
            'api_failures': 0,
            'database_queries': 0,
            'database_failures': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_response_time': 0.0,
            'api_response_time': 0.0,
            'db_response_time': 0.0
        }
    
    def get_cache_key(self, query: str, params: tuple) -> str:
        """Generate cache key from query and parameters."""
        import hashlib
        return f"query_{hashlib.md5(f'{query}_{params}'.encode(), usedforsecurity=False).hexdigest()}"
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available."""
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            self.performance_stats['cache_hits'] += 1
            logger.debug(f"Cache hit for key: {cache_key[:20]}...")
            return cached_result
        
        self.performance_stats['cache_misses'] += 1
        return None
    
    def set_cached_result(self, cache_key: str, result: Any, ttl: int = 300):
        """Store result in cache with TTL."""
        import pandas as pd
        
        # Convert DataFrame to cacheable format
        if isinstance(result, pd.DataFrame):
            cache_data = {
                'data': result.to_dict('records'),
                'columns': list(result.columns),
                'shape': result.shape
            }
            self.cache.set(cache_key, cache_data, ttl=ttl)
        else:
            self.cache.set(cache_key, result, ttl=ttl)
    
    def restore_dataframe_from_cache(self, cached_result: Any) -> Any:
        """Restore DataFrame from cached format."""
        import pandas as pd
        
        if isinstance(cached_result, dict) and 'data' in cached_result:
            return pd.DataFrame(cached_result['data'])
        return cached_result
    
    def record_api_request(self, response_time: float):
        """Record API request performance."""
        self.performance_stats['api_requests'] += 1
        self.performance_stats['api_response_time'] += response_time
    
    def record_api_failure(self):
        """Record API failure."""
        self.performance_stats['api_failures'] += 1
    
    def record_database_query(self, response_time: float):
        """Record database query performance."""
        self.performance_stats['database_queries'] += 1
        self.performance_stats['db_response_time'] += response_time
    
    def record_database_failure(self):
        """Record database failure."""
        self.performance_stats['database_failures'] += 1
    
    def record_total_response_time(self, response_time: float):
        """Record total response time."""
        self.performance_stats['total_response_time'] += response_time
    
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
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for API vs database usage."""
        stats = self.performance_stats.copy()
        
        # Calculate derived metrics
        total_requests = stats['api_requests'] + stats['database_queries']
        if total_requests > 0:
            stats['api_usage_percentage'] = (stats['api_requests'] / total_requests) * 100
            stats['database_usage_percentage'] = (stats['database_queries'] / total_requests) * 100
        else:
            stats['api_usage_percentage'] = 0
            stats['database_usage_percentage'] = 0
        
        # Calculate average response times
        if stats['api_requests'] > 0:
            stats['avg_api_response_time'] = stats['api_response_time'] / stats['api_requests']
        else:
            stats['avg_api_response_time'] = 0
            
        if stats['database_queries'] > 0:
            stats['avg_db_response_time'] = stats['db_response_time'] / stats['database_queries']
        else:
            stats['avg_db_response_time'] = 0
        
        # Calculate success rates
        if stats['api_requests'] > 0:
            stats['api_success_rate'] = ((stats['api_requests'] - stats['api_failures']) / stats['api_requests']) * 100
        else:
            stats['api_success_rate'] = 100
            
        if stats['database_queries'] > 0:
            stats['db_success_rate'] = ((stats['database_queries'] - stats['database_failures']) / stats['database_queries']) * 100
        else:
            stats['db_success_rate'] = 100
        
        # Calculate cache hit ratio
        total_cache_requests = stats['cache_hits'] + stats['cache_misses']
        if total_cache_requests > 0:
            stats['cache_hit_ratio'] = (stats['cache_hits'] / total_cache_requests) * 100
        else:
            stats['cache_hit_ratio'] = 0
        
        return stats