"""Production-optimized caching strategies for mutation testing.

This module provides enhanced caching capabilities specifically designed
for production workloads with high performance and reliability requirements.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
import threading
import weakref
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar, Generic
import sqlite3
import zlib

from .constants import CacheConfiguration

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    
    key: str
    data: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl_seconds: float
    tags: List[str] = field(default_factory=list)
    compression_ratio: float = 1.0


@dataclass
class CacheStats:
    """Cache performance statistics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    average_access_time_ms: float = 0.0
    compression_savings_bytes: int = 0


class LRUMemoryCache(Generic[T]):
    """High-performance in-memory LRU cache with thread safety."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        start_time = time.perf_counter()
        
        try:
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    
                    # Check TTL
                    if time.time() - entry.created_at > entry.ttl_seconds:
                        del self._cache[key]
                        self._stats.misses += 1
                        self._stats.evictions += 1
                        return None
                    
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    entry.last_accessed = time.time()
                    entry.access_count += 1
                    
                    self._stats.hits += 1
                    return entry.data
                else:
                    self._stats.misses += 1
                    return None
        
        finally:
            # Update average access time
            access_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_average_access_time(access_time_ms)
    
    def set(self, key: str, value: T, ttl_seconds: Optional[float] = None) -> bool:
        """Set value in cache."""
        with self._lock:
            # Calculate size estimate
            try:
                size_bytes = len(pickle.dumps(value))
            except (pickle.PickleError, TypeError):
                size_bytes = 1024  # Estimate for unpicklable objects
            
            # Create entry
            entry = CacheEntry(
                key=key,
                data=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds or self.ttl_seconds
            )
            
            # Add to cache
            self._cache[key] = entry
            self._cache.move_to_end(key)
            
            # Update stats
            self._stats.entry_count = len(self._cache)
            self._stats.size_bytes += size_bytes
            
            # Evict if necessary
            while len(self._cache) > self.max_size:
                self._evict_lru()
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._stats.size_bytes -= entry.size_bytes
                self._stats.entry_count = len(self._cache)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._stats.size_bytes -= entry.size_bytes
            self._stats.evictions += 1
            self._stats.entry_count = len(self._cache)
    
    def _update_average_access_time(self, access_time_ms: float):
        """Update running average of access times."""
        alpha = 0.1  # Smoothing factor
        self._stats.average_access_time_ms = (
            alpha * access_time_ms + 
            (1 - alpha) * self._stats.average_access_time_ms
        )
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            stats = CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size_bytes=self._stats.size_bytes,
                entry_count=len(self._cache),
                hit_rate=self._stats.hits / max(1, self._stats.hits + self._stats.misses) * 100,
                average_access_time_ms=self._stats.average_access_time_ms
            )
            return stats


class PersistentCache:
    """SQLite-based persistent cache with compression and advanced features."""
    
    def __init__(self, 
                 db_path: Path,
                 max_size_mb: int = 500,
                 compression_enabled: bool = True,
                 cleanup_interval_hours: int = 24):
        self.db_path = db_path
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.compression_enabled = compression_enabled
        self.cleanup_interval = cleanup_interval_hours * 3600
        self.last_cleanup = time.time()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    size_bytes INTEGER NOT NULL,
                    ttl_seconds REAL NOT NULL,
                    tags TEXT,  -- JSON array
                    compressed BOOLEAN DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_last_accessed 
                ON cache_entries(last_accessed)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_created_at 
                ON cache_entries(created_at)
            """)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from persistent cache."""
        start_time = time.perf_counter()
        
        self._maybe_cleanup()
        
        try:
            with self._lock:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.execute("""
                            SELECT data, created_at, ttl_seconds, compressed, access_count
                            FROM cache_entries WHERE key = ?
                        """, (key,))
                        
                        row = cursor.fetchone()
                        if not row:
                            self._stats.misses += 1
                            return None
                        
                        data_blob, created_at, ttl_seconds, compressed, access_count = row
                        
                        # Check TTL
                        if time.time() - created_at > ttl_seconds:
                            # Expired, delete and return None
                            conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                            self._stats.misses += 1
                            self._stats.evictions += 1
                            return None
                        
                        # Update access stats
                        conn.execute("""
                            UPDATE cache_entries 
                            SET last_accessed = ?, access_count = access_count + 1
                            WHERE key = ?
                        """, (time.time(), key))
                        
                        # Decompress and deserialize data
                        if compressed:
                            data_blob = zlib.decompress(data_blob)
                        
                        data = pickle.loads(data_blob)
                        
                        self._stats.hits += 1
                        return data
                        
                except (sqlite3.Error, pickle.PickleError, zlib.error) as e:
                    logger.warning(f"Cache read error for key {key}: {e}")
                    self._stats.misses += 1
                    # Remove corrupted entry
                    self._delete_key(key)
                    return None
        
        finally:
            access_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_average_access_time(access_time_ms)
    
    def set(self, key: str, data: Any, ttl_seconds: float = 3600, tags: Optional[List[str]] = None) -> bool:
        """Set value in persistent cache."""
        with self._lock:
            try:
                # Serialize data
                data_blob = pickle.dumps(data)
                original_size = len(data_blob)
                
                # Compress if enabled and beneficial
                compressed = False
                if self.compression_enabled and original_size > 1024:  # Only compress larger items
                    compressed_blob = zlib.compress(data_blob)
                    if len(compressed_blob) < original_size * 0.9:  # Only if compression saves >10%
                        data_blob = compressed_blob
                        compressed = True
                        compression_savings = original_size - len(data_blob)
                        self._stats.compression_savings_bytes += compression_savings
                
                # Store in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (key, data, created_at, last_accessed, access_count, 
                         size_bytes, ttl_seconds, tags, compressed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        key, data_blob, time.time(), time.time(), 1,
                        len(data_blob), ttl_seconds, 
                        json.dumps(tags or []), compressed
                    ))
                
                # Update stats
                self._update_size_stats()
                
                # Cleanup if cache is too large
                self._enforce_size_limit()
                
                return True
                
            except (sqlite3.Error, pickle.PickleError) as e:
                logger.error(f"Cache write error for key {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        return self._delete_key(key)
    
    def delete_by_tags(self, tags: List[str]) -> int:
        """Delete all entries with any of the specified tags."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Find entries with matching tags
                    cursor = conn.execute("SELECT key, tags FROM cache_entries")
                    keys_to_delete = []
                    
                    for key, tags_json in cursor.fetchall():
                        if tags_json:
                            entry_tags = json.loads(tags_json)
                            if any(tag in entry_tags for tag in tags):
                                keys_to_delete.append(key)
                    
                    # Delete matching entries
                    deleted_count = 0
                    for key in keys_to_delete:
                        conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                        deleted_count += 1
                    
                    self._update_size_stats()
                    return deleted_count
                    
            except (sqlite3.Error, json.JSONDecodeError) as e:
                logger.error(f"Error deleting by tags {tags}: {e}")
                return 0
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM cache_entries")
                self._stats = CacheStats()
            except sqlite3.Error as e:
                logger.error(f"Error clearing cache: {e}")
    
    def _delete_key(self, key: str) -> bool:
        """Delete a specific key."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    deleted = cursor.rowcount > 0
                    if deleted:
                        self._update_size_stats()
                    return deleted
            except sqlite3.Error as e:
                logger.error(f"Error deleting key {key}: {e}")
                return False
    
    def _maybe_cleanup(self):
        """Perform cleanup if interval has passed."""
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            self.last_cleanup = time.time()
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        with self._lock:
            try:
                current_time = time.time()
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        DELETE FROM cache_entries 
                        WHERE created_at + ttl_seconds < ?
                    """, (current_time,))
                    
                    deleted_count = cursor.rowcount
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired cache entries")
                        self._stats.evictions += deleted_count
                        self._update_size_stats()
                        
            except sqlite3.Error as e:
                logger.error(f"Error during cache cleanup: {e}")
    
    def _enforce_size_limit(self):
        """Remove oldest entries if cache exceeds size limit."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Check current size
                    cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
                    current_size = cursor.fetchone()[0] or 0
                    
                    if current_size > self.max_size_bytes:
                        # Delete oldest entries until under limit
                        target_size = self.max_size_bytes * 0.8  # Target 80% of limit
                        
                        cursor = conn.execute("""
                            SELECT key, size_bytes FROM cache_entries 
                            ORDER BY last_accessed ASC
                        """)
                        
                        for key, size_bytes in cursor.fetchall():
                            if current_size <= target_size:
                                break
                            
                            conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                            current_size -= size_bytes
                            self._stats.evictions += 1
                        
                        logger.info(f"Enforced cache size limit, removed entries to reach {current_size} bytes")
                        
            except sqlite3.Error as e:
                logger.error(f"Error enforcing size limit: {e}")
    
    def _update_size_stats(self):
        """Update cache size statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) 
                    FROM cache_entries
                """)
                count, size_bytes = cursor.fetchone()
                
                self._stats.entry_count = count
                self._stats.size_bytes = size_bytes
                
        except sqlite3.Error as e:
            logger.error(f"Error updating size stats: {e}")
    
    def _update_average_access_time(self, access_time_ms: float):
        """Update running average of access times."""
        alpha = 0.1
        self._stats.average_access_time_ms = (
            alpha * access_time_ms + 
            (1 - alpha) * self._stats.average_access_time_ms
        )
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._update_size_stats()
            
            stats = CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size_bytes=self._stats.size_bytes,
                entry_count=self._stats.entry_count,
                hit_rate=self._stats.hits / max(1, self._stats.hits + self._stats.misses) * 100,
                average_access_time_ms=self._stats.average_access_time_ms,
                compression_savings_bytes=self._stats.compression_savings_bytes
            )
            return stats


class TieredCache:
    """Multi-tiered cache with memory (L1) and disk (L2) layers."""
    
    def __init__(self,
                 cache_dir: Path,
                 memory_size: int = 1000,
                 disk_size_mb: int = 500,
                 memory_ttl: float = 1800,  # 30 minutes
                 disk_ttl: float = 86400):   # 24 hours
        
        self.l1_cache = LRUMemoryCache[Any](max_size=memory_size, ttl_seconds=memory_ttl)
        self.l2_cache = PersistentCache(
            db_path=cache_dir / "tier2.db",
            max_size_mb=disk_size_mb
        )
        
        self._stats = {
            'l1_promotions': 0,  # L2 -> L1 promotions
            'l2_stores': 0,      # L1 evictions -> L2
            'total_hits': 0,
            'total_misses': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from tiered cache."""
        # Try L1 first
        value = self.l1_cache.get(key)
        if value is not None:
            self._stats['total_hits'] += 1
            return value
        
        # Try L2
        value = self.l2_cache.get(key)
        if value is not None:
            # Promote to L1
            self.l1_cache.set(key, value)
            self._stats['l1_promotions'] += 1
            self._stats['total_hits'] += 1
            return value
        
        self._stats['total_misses'] += 1
        return None
    
    def set(self, key: str, value: Any, tags: Optional[List[str]] = None) -> bool:
        """Set value in tiered cache."""
        # Always store in L1
        l1_success = self.l1_cache.set(key, value)
        
        # Also store in L2 for persistence
        l2_success = self.l2_cache.set(key, value, tags=tags)
        if l2_success:
            self._stats['l2_stores'] += 1
        
        return l1_success or l2_success
    
    def delete(self, key: str) -> bool:
        """Delete from both tiers."""
        l1_deleted = self.l1_cache.delete(key)
        l2_deleted = self.l2_cache.delete(key)
        return l1_deleted or l2_deleted
    
    def delete_by_tags(self, tags: List[str]) -> int:
        """Delete by tags (L2 only, L1 entries will expire)."""
        return self.l2_cache.delete_by_tags(tags)
    
    def clear(self):
        """Clear both tiers."""
        self.l1_cache.clear()
        self.l2_cache.clear()
        self._stats = {'l1_promotions': 0, 'l2_stores': 0, 'total_hits': 0, 'total_misses': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()
        
        return {
            'l1': {
                'hits': l1_stats.hits,
                'misses': l1_stats.misses,
                'hit_rate': l1_stats.hit_rate,
                'size_bytes': l1_stats.size_bytes,
                'entry_count': l1_stats.entry_count,
                'evictions': l1_stats.evictions
            },
            'l2': {
                'hits': l2_stats.hits,
                'misses': l2_stats.misses,
                'hit_rate': l2_stats.hit_rate,
                'size_bytes': l2_stats.size_bytes,
                'entry_count': l2_stats.entry_count,
                'evictions': l2_stats.evictions,
                'compression_savings_bytes': l2_stats.compression_savings_bytes
            },
            'tiered': {
                'total_hits': self._stats['total_hits'],
                'total_misses': self._stats['total_misses'],
                'overall_hit_rate': self._stats['total_hits'] / max(1, self._stats['total_hits'] + self._stats['total_misses']) * 100,
                'l1_promotions': self._stats['l1_promotions'],
                'l2_stores': self._stats['l2_stores']
            }
        }


class CacheKeyGenerator:
    """Generates consistent cache keys for different types of data."""
    
    @staticmethod
    def file_content_key(file_path: Path) -> str:
        """Generate cache key based on file path and modification time."""
        try:
            stat = file_path.stat()
            content = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            return hashlib.md5(content.encode()).hexdigest()
        except OSError:
            # Fall back to just path
            return hashlib.md5(str(file_path).encode()).hexdigest()
    
    @staticmethod
    def mutation_result_key(test_file: Path, source_file: Path, mutation_hash: str) -> str:
        """Generate cache key for mutation test results."""
        content = f"mutation:{test_file}:{source_file}:{mutation_hash}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @staticmethod
    def effectiveness_report_key(test_file: Path, config_hash: str) -> str:
        """Generate cache key for effectiveness reports."""
        file_key = CacheKeyGenerator.file_content_key(test_file)
        content = f"effectiveness:{file_key}:{config_hash}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @staticmethod
    def config_hash(config_obj: Any) -> str:
        """Generate hash for configuration objects."""
        try:
            # Try to serialize config to get a stable hash
            config_str = json.dumps(config_obj.__dict__, sort_keys=True, default=str)
            return hashlib.md5(config_str.encode()).hexdigest()[:16]
        except (TypeError, AttributeError):
            # Fallback to string representation
            return hashlib.md5(str(config_obj).encode()).hexdigest()[:16]


class ProductionCacheManager:
    """Production-ready cache manager with monitoring and optimization."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tiered cache
        self.cache = TieredCache(
            cache_dir=cache_dir,
            memory_size=2000,    # Larger memory cache for production
            disk_size_mb=1000,   # 1GB disk cache
            memory_ttl=3600,     # 1 hour memory TTL
            disk_ttl=86400 * 7   # 1 week disk TTL
        )
        
        self.key_generator = CacheKeyGenerator()
        
        # Performance monitoring
        self._start_time = time.time()
        self._operation_times: List[float] = []
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache")
    
    async def get_async(self, key: str) -> Optional[Any]:
        """Asynchronous cache get operation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.cache.get, key)
    
    async def set_async(self, key: str, value: Any, tags: Optional[List[str]] = None) -> bool:
        """Asynchronous cache set operation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            lambda: self.cache.set(key, value, tags)
        )
    
    def cache_mutation_result(self, 
                              test_file: Path, 
                              source_file: Path, 
                              mutation: Dict[str, Any], 
                              result: Dict[str, Any]) -> bool:
        """Cache mutation test result."""
        mutation_hash = hashlib.md5(json.dumps(mutation, sort_keys=True).encode()).hexdigest()
        key = self.key_generator.mutation_result_key(test_file, source_file, mutation_hash)
        
        # Tag with file names for easy invalidation
        tags = [f"test:{test_file.name}", f"source:{source_file.name}"]
        
        return self.cache.set(key, result, tags=tags)
    
    def get_mutation_result(self, 
                            test_file: Path, 
                            source_file: Path, 
                            mutation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached mutation test result."""
        mutation_hash = hashlib.md5(json.dumps(mutation, sort_keys=True).encode()).hexdigest()
        key = self.key_generator.mutation_result_key(test_file, source_file, mutation_hash)
        return self.cache.get(key)
    
    def cache_effectiveness_report(self, 
                                   test_file: Path, 
                                   config: Any, 
                                   report: Any) -> bool:
        """Cache effectiveness report."""
        config_hash = self.key_generator.config_hash(config)
        key = self.key_generator.effectiveness_report_key(test_file, config_hash)
        
        tags = [f"test:{test_file.name}", "effectiveness_report"]
        
        return self.cache.set(key, report, tags=tags)
    
    def get_effectiveness_report(self, test_file: Path, config: Any) -> Optional[Any]:
        """Get cached effectiveness report."""
        config_hash = self.key_generator.config_hash(config)
        key = self.key_generator.effectiveness_report_key(test_file, config_hash)
        return self.cache.get(key)
    
    def invalidate_file_caches(self, file_path: Path):
        """Invalidate all caches related to a specific file."""
        # Delete by tags
        tags_to_delete = [f"test:{file_path.name}", f"source:{file_path.name}"]
        deleted_count = 0
        
        for tag in tags_to_delete:
            deleted_count += self.cache.delete_by_tags([tag])
        
        logger.info(f"Invalidated {deleted_count} cache entries for {file_path}")
        return deleted_count
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        cache_stats = self.cache.get_stats()
        uptime = time.time() - self._start_time
        
        return {
            'uptime_seconds': uptime,
            'cache_stats': cache_stats,
            'average_operation_time_ms': sum(self._operation_times) / max(1, len(self._operation_times)),
            'total_operations': len(self._operation_times),
            'memory_efficiency': cache_stats['l1']['hit_rate'],
            'disk_efficiency': cache_stats['l2']['hit_rate'],
            'overall_efficiency': cache_stats['tiered']['overall_hit_rate']
        }
    
    def optimize_cache(self):
        """Perform cache optimization operations."""
        logger.info("Starting cache optimization...")
        
        # Get current stats
        stats = self.cache.get_stats()
        
        # If L1 hit rate is low, consider increasing memory cache size
        if stats['l1']['hit_rate'] < 60:
            logger.warning(f"L1 cache hit rate is low: {stats['l1']['hit_rate']:.1f}%")
        
        # If L2 compression savings are low, consider disabling compression
        l2_compression_ratio = (
            stats['l2']['compression_savings_bytes'] / max(1, stats['l2']['size_bytes'])
        )
        if l2_compression_ratio < 0.1:
            logger.info(f"L2 compression ratio is low: {l2_compression_ratio:.1%}")
        
        # Cleanup expired entries manually
        if hasattr(self.cache.l2_cache, '_cleanup_expired'):
            self.cache.l2_cache._cleanup_expired()
        
        logger.info("Cache optimization completed")
    
    def shutdown(self):
        """Shutdown cache manager and cleanup resources."""
        self._executor.shutdown(wait=True)
        logger.info("Production cache manager shutdown completed")