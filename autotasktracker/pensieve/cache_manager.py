"""
Intelligent caching system for Pensieve API responses.
Provides multi-tier caching with automatic invalidation.
"""

import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import performance monitoring (with fallback if not available)
try:
    from autotasktracker.pensieve.performance_monitor import record_cache_hit, record_cache_miss
    PERFORMANCE_MONITORING_AVAILABLE = True
except ImportError:
    logger.debug("Performance monitoring not available")
    PERFORMANCE_MONITORING_AVAILABLE = False
    
    def record_cache_hit(cache_type: str = "default"):
        pass
    
    def record_cache_miss(cache_type: str = "default"):
        pass


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0


class PensieveCacheManager:
    """
    Multi-tier caching system for Pensieve API responses.
    
    Features:
    - Memory cache for hot data (recent screenshots, frequent queries)
    - Disk cache for persistent storage
    - Automatic cache invalidation based on TTL and events
    - LRU eviction for memory management
    - Cache warming for improved performance
    """
    
    def __init__(self, 
                 memory_size_limit: int = 1000,
                 disk_cache_dir: Optional[str] = None,
                 default_ttl: int = 300):  # 5 minutes default TTL
        """
        Initialize cache manager.
        
        Args:
            memory_size_limit: Maximum number of items in memory cache
            disk_cache_dir: Directory for disk cache (default: /Users/paulrohde/AutoTaskTracker.memos/autotask_cache)
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self.memory_size_limit = memory_size_limit
        self.default_ttl = default_ttl
        
        # Memory cache (hot data)
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_lock = threading.RLock()
        
        # Disk cache setup
        if disk_cache_dir is None:
            disk_cache_dir = Path.home() / ".memos" / "autotask_cache"
        self.disk_cache_dir = Path(disk_cache_dir)
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache statistics
        self.stats = {
            'memory_hits': 0,
            'memory_misses': 0,
            'disk_hits': 0,
            'disk_misses': 0,
            'invalidations': 0,
            'evictions': 0
        }
        
        # Start background cleanup
        self._cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"Initialized PensieveCacheManager with memory limit {memory_size_limit}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with automatic tier promotion.
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        # Try memory cache first
        with self._memory_lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if not self._is_expired(entry):
                    entry.access_count += 1
                    entry.last_accessed = time.time()
                    self.stats['memory_hits'] += 1
                    # Record performance monitoring
                    record_cache_hit("memory")
                    return entry.value
                else:
                    # Expired entry
                    del self._memory_cache[key]
                    self.stats['invalidations'] += 1
        
        self.stats['memory_misses'] += 1
        # Record performance monitoring
        record_cache_miss("memory")
        
        # Try disk cache
        disk_value = self._get_from_disk(key)
        if disk_value is not None:
            self.stats['disk_hits'] += 1
            # Record performance monitoring
            record_cache_hit("disk")
            # Promote to memory cache
            self._set_memory(key, disk_value, self.default_ttl)
            return disk_value
        
        self.stats['disk_misses'] += 1
        # Record performance monitoring
        record_cache_miss("disk")
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with automatic tier management.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: uses default_ttl)
        """
        if ttl is None:
            ttl = self.default_ttl
            
        # Always set in memory for hot access
        self._set_memory(key, value, ttl)
        
        # Set in disk for persistence
        self._set_disk(key, value, ttl)
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if key was found and invalidated
        """
        invalidated = False
        
        # Remove from memory
        with self._memory_lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                invalidated = True
        
        # Remove from disk
        disk_file = self._get_disk_path(key)
        if disk_file.exists():
            disk_file.unlink()
            invalidated = True
        
        if invalidated:
            self.stats['invalidations'] += 1
            
        return invalidated
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (simple string contains)
            
        Returns:
            Number of entries invalidated
        """
        count = 0
        
        # Memory cache
        with self._memory_lock:
            keys_to_remove = [k for k in self._memory_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._memory_cache[key]
                count += 1
        
        # Disk cache
        for cache_file in self.disk_cache_dir.glob("*.cache"):
            if pattern in cache_file.stem:
                cache_file.unlink()
                count += 1
        
        self.stats['invalidations'] += count
        return count
    
    def invalidate_entity(self, entity_id: int) -> int:
        """
        Invalidate all cache entries related to a specific entity.
        
        Args:
            entity_id: Entity ID to invalidate
            
        Returns:
            Number of entries invalidated
        """
        return self.invalidate_pattern(f"entity_{entity_id}")
    
    def warm_cache(self, entities: List[Dict[str, Any]]) -> None:
        """
        Warm cache with entity data for improved performance.
        
        Args:
            entities: List of entity dictionaries to cache
        """
        logger.info(f"Warming cache with {len(entities)} entities")
        
        for entity in entities:
            entity_id = entity['id']
            
            # Cache entity data
            self.set(f"entity_{entity_id}", entity, ttl=600)  # 10 minute TTL
            
            # Cache metadata if available
            if 'metadata' in entity and entity['metadata']:
                self.set(f"entity_metadata_{entity_id}", entity['metadata'], ttl=600)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._memory_lock:
            memory_size = len(self._memory_cache)
            
        disk_size = len(list(self.disk_cache_dir.glob("*.cache")))
        
        total_requests = (self.stats['memory_hits'] + self.stats['memory_misses'] + 
                         self.stats['disk_hits'] + self.stats['disk_misses'])
        
        hit_rate = 0.0
        if total_requests > 0:
            total_hits = self.stats['memory_hits'] + self.stats['disk_hits']
            hit_rate = (total_hits / total_requests) * 100
        
        return {
            **self.stats,
            'memory_size': memory_size,
            'disk_size': disk_size,
            'hit_rate_percent': hit_rate,
            'total_requests': total_requests
        }
    
    def clear(self) -> None:
        """Clear all cache data."""
        # Clear memory
        with self._memory_lock:
            self._memory_cache.clear()
        
        # Clear disk
        for cache_file in self.disk_cache_dir.glob("*.cache"):
            cache_file.unlink()
        
        logger.info("Cleared all cache data")
    
    def _set_memory(self, key: str, value: Any, ttl: int) -> None:
        """Set value in memory cache with LRU eviction."""
        with self._memory_lock:
            # Check if we need to evict
            if len(self._memory_cache) >= self.memory_size_limit and key not in self._memory_cache:
                self._evict_lru()
            
            # Create cache entry
            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl,
                access_count=1,
                last_accessed=now
            )
            
            self._memory_cache[key] = entry
    
    def _get_from_disk(self, key: str) -> Any:
        """Get value from disk cache."""
        cache_file = self._get_disk_path(key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check expiration
            if time.time() > data.get('expires_at', 0):
                cache_file.unlink()  # Remove expired file
                return None
            
            return data.get('value')
            
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Failed to read cache file {cache_file}: {e}")
            # Remove corrupted file
            try:
                cache_file.unlink()
            except OSError as e:
                logger.debug(f"Could not remove corrupted cache file {cache_file}: {e}")
            return None
    
    def _set_disk(self, key: str, value: Any, ttl: int) -> None:
        """Set value in disk cache."""
        cache_file = self._get_disk_path(key)
        
        try:
            data = {
                'key': key,
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + ttl
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, default=str)  # default=str handles datetime serialization
                
        except (OSError, TypeError) as e:
            logger.warning(f"Failed to write cache file {cache_file}: {e}")
    
    def _get_disk_path(self, key: str) -> Path:
        """Get disk cache file path for a key."""
        # Create safe filename from key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.disk_cache_dir / f"{safe_key}.cache"
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        return time.time() > entry.expires_at
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry from memory cache."""
        if not self._memory_cache:
            return
        
        # Find LRU entry
        lru_key = min(self._memory_cache.keys(), 
                     key=lambda k: self._memory_cache[k].last_accessed)
        
        del self._memory_cache[lru_key]
        self.stats['evictions'] += 1
    
    def _background_cleanup(self) -> None:
        """Background thread for cleaning up expired entries."""
        while True:
            try:
                # Clean up memory cache
                with self._memory_lock:
                    expired_keys = [k for k, entry in self._memory_cache.items() 
                                  if self._is_expired(entry)]
                    for key in expired_keys:
                        del self._memory_cache[key]
                        self.stats['invalidations'] += 1
                
                # Clean up disk cache
                for cache_file in self.disk_cache_dir.glob("*.cache"):
                    try:
                        with open(cache_file, 'r') as f:
                            data = json.load(f)
                        
                        if time.time() > data.get('expires_at', 0):
                            cache_file.unlink()
                            self.stats['invalidations'] += 1
                            
                    except (json.JSONDecodeError, OSError):
                        # Remove corrupted files
                        try:
                            cache_file.unlink()
                        except OSError as e:
                            logger.debug(f"Could not remove corrupted cache file {cache_file}: {e}")
                
                # Sleep for 5 minutes before next cleanup
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")
                time.sleep(60)  # Shorter sleep on error


# Global cache instance
_cache_instance: Optional[PensieveCacheManager] = None


def get_cache_manager() -> PensieveCacheManager:
    """Get global cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = PensieveCacheManager()
    return _cache_instance


def reset_cache_manager():
    """Reset global cache manager (useful for testing)."""
    global _cache_instance
    if _cache_instance:
        _cache_instance.clear()
    _cache_instance = None