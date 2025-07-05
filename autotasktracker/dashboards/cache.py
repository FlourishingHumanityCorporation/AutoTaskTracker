"""Unified caching strategy for dashboards."""

import streamlit as st
import hashlib
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class DashboardCache:
    """Centralized caching for dashboard data."""
    
    @staticmethod
    def create_cache_key(prefix: str, **kwargs) -> str:
        """Create a unique cache key from parameters.
        
        Args:
            prefix: Cache key prefix
            **kwargs: Parameters to include in key
            
        Returns:
            Unique cache key string
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, default=str)
        
        # Create hash for compact key
        hash_obj = hashlib.md5(param_str.encode())
        return f"{prefix}_{hash_obj.hexdigest()}"
    
    @staticmethod
    def get_cached(
        key: str,
        fetch_func: Callable,
        ttl_seconds: int = 300,
        force_refresh: bool = False
    ) -> Any:
        """Get cached data or fetch if expired.
        
        Args:
            key: Cache key
            fetch_func: Function to fetch data if not cached
            ttl_seconds: Time to live in seconds
            force_refresh: Force refresh cache
            
        Returns:
            Cached or freshly fetched data
        """
        cache_key = f"cache_{key}"
        timestamp_key = f"cache_ts_{key}"
        
        # Check if force refresh
        if force_refresh:
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            if timestamp_key in st.session_state:
                del st.session_state[timestamp_key]
        
        # Check if cached and not expired
        if cache_key in st.session_state and timestamp_key in st.session_state:
            cached_time = st.session_state[timestamp_key]
            if datetime.now() - cached_time < timedelta(seconds=ttl_seconds):
                logger.debug(f"Cache hit for key: {key}")
                return st.session_state[cache_key]
        
        # Fetch fresh data
        logger.debug(f"Cache miss for key: {key}, fetching fresh data")
        try:
            data = fetch_func()
            st.session_state[cache_key] = data
            st.session_state[timestamp_key] = datetime.now()
            return data
        except Exception as e:
            logger.error(f"Error fetching data for cache key {key}: {e}")
            # Return cached data if available, even if expired
            if cache_key in st.session_state:
                logger.warning("Returning expired cache due to fetch error")
                return st.session_state[cache_key]
            raise
    
    @staticmethod
    def clear_cache(pattern: Optional[str] = None):
        """Clear cache entries.
        
        Args:
            pattern: Optional pattern to match keys (clears all if None)
        """
        keys_to_remove = []
        
        for key in st.session_state:
            if key.startswith("cache_"):
                if pattern is None or pattern in key:
                    keys_to_remove.append(key)
                    # Also remove timestamp key
                    ts_key = key.replace("cache_", "cache_ts_")
                    if ts_key in st.session_state:
                        keys_to_remove.append(ts_key)
        
        for key in keys_to_remove:
            del st.session_state[key]
            
        logger.info(f"Cleared {len(keys_to_remove)} cache entries")
        

def cached_data(ttl_seconds: int = 300, key_prefix: str = "data"):
    """Decorator for caching function results.
    
    Args:
        ttl_seconds: Cache time to live
        key_prefix: Prefix for cache key
        
    Usage:
        @cached_data(ttl_seconds=600, key_prefix="tasks")
        def get_expensive_data(param1, param2):
            return expensive_operation()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = DashboardCache.create_cache_key(
                f"{key_prefix}_{func.__name__}",
                args=args,
                kwargs=kwargs
            )
            
            return DashboardCache.get_cached(
                key=cache_key,
                fetch_func=lambda: func(*args, **kwargs),
                ttl_seconds=ttl_seconds
            )
        return wrapper
    return decorator


class QueryCache:
    """Specialized cache for database queries."""
    
    @staticmethod
    @cached_data(ttl_seconds=300, key_prefix="query")
    def get_cached_query(
        query: str,
        params: tuple,
        db_manager: Any
    ) -> Any:
        """Cache database query results.
        
        Args:
            query: SQL query
            params: Query parameters
            db_manager: Database manager instance
            
        Returns:
            Query results
        """
        return db_manager.execute_query(query, params)
    
    @staticmethod
    def get_time_filtered_data(
        db_manager: Any,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
        ttl_seconds: int = 300
    ) -> Any:
        """Get cached time-filtered data.
        
        Common query used across multiple dashboards.
        """
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.file_path,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category,
            m5.value as window_title
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'text'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = "active_window"
        WHERE e.created_at >= ? AND e.created_at <= ?
        ORDER BY e.created_at DESC
        LIMIT ?
        """
        
        params = (
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S'),
            limit
        )
        
        cache_key = DashboardCache.create_cache_key(
            "time_filtered_data",
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            limit=limit
        )
        
        def _fetch_data():
            with db_manager.get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params)
        
        return DashboardCache.get_cached(
            key=cache_key,
            fetch_func=_fetch_data,
            ttl_seconds=ttl_seconds
        )


class MetricsCache:
    """Cache for computed metrics."""
    
    @staticmethod
    @cached_data(ttl_seconds=600, key_prefix="metrics")
    def get_category_breakdown(
        db_manager: Any,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """Get cached category breakdown."""
        query = """
        SELECT 
            m.value as category,
            COUNT(*) as count
        FROM entities e
        JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'category'
        WHERE e.created_at >= ? AND e.created_at <= ?
        GROUP BY m.value
        ORDER BY count DESC
        """
        
        with db_manager.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        return df.set_index('category')['count'].to_dict() if not df.empty else {}
    
    @staticmethod
    @cached_data(ttl_seconds=600, key_prefix="metrics")
    def get_hourly_activity(
        db_manager: Any,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[int, int]:
        """Get cached hourly activity breakdown."""
        query = """
        SELECT 
            CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) as hour,
            COUNT(*) as count
        FROM entities
        WHERE created_at >= ? AND created_at <= ?
        GROUP BY hour
        ORDER BY hour
        """
        
        with db_manager.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        return df.set_index('hour')['count'].to_dict() if not df.empty else {}