"""Tests for production-optimized caching system.

This test suite validates the enhanced caching capabilities
designed for production workloads.
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock
import json

from tests.health.testing.production_cache import (
    LRUMemoryCache,
    PersistentCache,
    TieredCache,
    CacheKeyGenerator,
    ProductionCacheManager,
    CacheEntry,
    CacheStats
)


class TestLRUMemoryCache:
    """Test the LRU memory cache implementation."""
    
    @pytest.fixture
    def memory_cache(self):
        """Create a memory cache for testing."""
        return LRUMemoryCache[str](max_size=3, ttl_seconds=10)
    
    def test_cache_initialization(self, memory_cache):
        """Test cache initialization."""
        assert memory_cache.max_size == 3
        assert memory_cache.ttl_seconds == 10
        
        stats = memory_cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.entry_count == 0
    
    def test_cache_set_and_get(self, memory_cache):
        """Test basic set and get operations."""
        # Set value
        assert memory_cache.set("key1", "value1") is True
        
        # Get value
        value = memory_cache.get("key1")
        assert value == "value1"
        
        # Check stats
        stats = memory_cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 0
        assert stats.entry_count == 1
    
    def test_cache_miss(self, memory_cache):
        """Test cache miss behavior."""
        value = memory_cache.get("nonexistent")
        assert value is None
        
        stats = memory_cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 1
    
    def test_lru_eviction(self, memory_cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")
        memory_cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        memory_cache.get("key1")
        
        # Add another item, should evict key2 (least recently used)
        memory_cache.set("key4", "value4")
        
        assert memory_cache.get("key1") == "value1"  # Still there
        assert memory_cache.get("key2") is None      # Evicted
        assert memory_cache.get("key3") == "value3"  # Still there
        assert memory_cache.get("key4") == "value4"  # New item
        
        stats = memory_cache.get_stats()
        assert stats.evictions == 1
    
    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = LRUMemoryCache[str](max_size=10, ttl_seconds=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        
        # Immediately available
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get("key1") is None
        
        stats = cache.get_stats()
        assert stats.evictions == 1  # Expired item counts as eviction
    
    def test_cache_clear(self, memory_cache):
        """Test cache clearing."""
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")
        
        memory_cache.clear()
        
        assert memory_cache.get("key1") is None
        assert memory_cache.get("key2") is None
        
        stats = memory_cache.get_stats()
        assert stats.entry_count == 0
        assert stats.size_bytes == 0
    
    def test_delete_operation(self, memory_cache):
        """Test explicit delete operations."""
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")
        
        # Delete existing key
        assert memory_cache.delete("key1") is True
        assert memory_cache.get("key1") is None
        assert memory_cache.get("key2") == "value2"
        
        # Delete non-existent key
        assert memory_cache.delete("nonexistent") is False
    
    def test_hit_rate_calculation(self, memory_cache):
        """Test hit rate calculation."""
        memory_cache.set("key1", "value1")
        
        # 1 hit, 0 misses
        memory_cache.get("key1")
        stats = memory_cache.get_stats()
        assert stats.hit_rate == 100.0
        
        # 1 hit, 1 miss
        memory_cache.get("nonexistent")
        stats = memory_cache.get_stats()
        assert stats.hit_rate == 50.0


class TestPersistentCache:
    """Test the SQLite-based persistent cache."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def persistent_cache(self, temp_cache_dir):
        """Create a persistent cache for testing."""
        return PersistentCache(
            db_path=temp_cache_dir / "test_cache.db",
            max_size_mb=1,  # Small size for testing
            compression_enabled=True
        )
    
    def test_cache_initialization(self, persistent_cache):
        """Test persistent cache initialization."""
        assert persistent_cache.db_path.exists()
        
        stats = persistent_cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.entry_count == 0
    
    def test_persistent_set_and_get(self, persistent_cache):
        """Test persistent cache set and get."""
        test_data = {"key": "value", "number": 42}
        
        # Set data
        assert persistent_cache.set("test_key", test_data, ttl_seconds=60) is True
        
        # Get data
        retrieved_data = persistent_cache.get("test_key")
        assert retrieved_data == test_data
        
        stats = persistent_cache.get_stats()
        assert stats.hits == 1
        assert stats.entry_count == 1
    
    def test_compression_functionality(self, persistent_cache):
        """Test data compression functionality."""
        # Large data that should be compressed
        large_data = "x" * 2000  # 2KB of repetitive data
        
        persistent_cache.set("large_key", large_data)
        retrieved_data = persistent_cache.get("large_key")
        
        assert retrieved_data == large_data
        
        # Check compression savings
        stats = persistent_cache.get_stats()
        assert stats.compression_savings_bytes > 0
    
    def test_tags_functionality(self, persistent_cache):
        """Test cache entry tagging and deletion by tags."""
        # Set entries with tags
        persistent_cache.set("key1", "value1", tags=["group1", "test"])
        persistent_cache.set("key2", "value2", tags=["group1"])
        persistent_cache.set("key3", "value3", tags=["group2"])
        
        # Delete by tags
        deleted_count = persistent_cache.delete_by_tags(["group1"])
        assert deleted_count == 2
        
        # Check what remains
        assert persistent_cache.get("key1") is None
        assert persistent_cache.get("key2") is None
        assert persistent_cache.get("key3") == "value3"
    
    def test_ttl_expiration_persistent(self, persistent_cache):
        """Test TTL expiration in persistent cache."""
        # Set with very short TTL
        persistent_cache.set("short_key", "short_value", ttl_seconds=0.1)
        
        # Immediately available
        assert persistent_cache.get("short_key") == "short_value"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired and cleaned up
        assert persistent_cache.get("short_key") is None
    
    def test_size_limit_enforcement(self, persistent_cache):
        """Test cache size limit enforcement."""
        # Fill cache with data to exceed size limit
        large_data = "x" * 100000  # 100KB each
        
        for i in range(20):  # Try to store 2MB total (exceeds 1MB limit)
            persistent_cache.set(f"large_key_{i}", large_data)
        
        # Cache should have evicted some entries to stay under limit
        stats = persistent_cache.get_stats()
        assert stats.size_bytes < 1024 * 1024  # Should be under 1MB
        assert stats.evictions > 0


class TestTieredCache:
    """Test the multi-tiered cache system."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def tiered_cache(self, temp_cache_dir):
        """Create a tiered cache for testing."""
        return TieredCache(
            cache_dir=temp_cache_dir,
            memory_size=3,
            disk_size_mb=1,
            memory_ttl=10,
            disk_ttl=60
        )
    
    def test_tiered_cache_initialization(self, tiered_cache):
        """Test tiered cache initialization."""
        assert tiered_cache.l1_cache is not None
        assert tiered_cache.l2_cache is not None
        
        stats = tiered_cache.get_stats()
        assert 'l1' in stats
        assert 'l2' in stats
        assert 'tiered' in stats
    
    def test_l1_hit(self, tiered_cache):
        """Test L1 cache hit."""
        tiered_cache.set("key1", "value1")
        
        # Should hit L1
        value = tiered_cache.get("key1")
        assert value == "value1"
        
        stats = tiered_cache.get_stats()
        assert stats['l1']['hits'] == 1
        assert stats['tiered']['total_hits'] == 1
    
    def test_l2_promotion(self, tiered_cache):
        """Test L2 to L1 promotion."""
        # Fill L1 to capacity and beyond to force eviction
        for i in range(5):
            tiered_cache.set(f"key{i}", f"value{i}")
        
        # Clear L1 manually to simulate L1 eviction
        tiered_cache.l1_cache.clear()
        
        # Get a value that should be in L2
        value = tiered_cache.get("key0")
        assert value == "value0"
        
        # Should now be promoted to L1
        stats = tiered_cache.get_stats()
        assert stats['tiered']['l1_promotions'] >= 1
    
    def test_both_tier_storage(self, tiered_cache):
        """Test that data is stored in both tiers."""
        tiered_cache.set("key1", "value1")
        
        # Should be in both L1 and L2
        assert tiered_cache.l1_cache.get("key1") == "value1"
        assert tiered_cache.l2_cache.get("key1") == "value1"
    
    def test_tag_deletion_tiered(self, tiered_cache):
        """Test tag-based deletion in tiered cache."""
        tiered_cache.set("key1", "value1", tags=["group1"])
        tiered_cache.set("key2", "value2", tags=["group2"])
        
        # Delete by tags
        deleted_count = tiered_cache.delete_by_tags(["group1"])
        assert deleted_count == 1
        
        # Check that L2 entry is gone (L1 may still have it until TTL)
        assert tiered_cache.l2_cache.get("key1") is None
        assert tiered_cache.l2_cache.get("key2") == "value2"


class TestCacheKeyGenerator:
    """Test cache key generation utilities."""
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("test content")
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    def test_file_content_key(self, temp_file):
        """Test file content key generation."""
        key1 = CacheKeyGenerator.file_content_key(temp_file)
        key2 = CacheKeyGenerator.file_content_key(temp_file)
        
        # Same file should generate same key
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length
    
    def test_file_content_key_changes_with_modification(self, temp_file):
        """Test that key changes when file is modified."""
        key1 = CacheKeyGenerator.file_content_key(temp_file)
        
        # Wait and modify file
        time.sleep(0.1)
        temp_file.write_text("modified content")
        
        key2 = CacheKeyGenerator.file_content_key(temp_file)
        
        # Keys should be different
        assert key1 != key2
    
    def test_mutation_result_key(self, temp_file):
        """Test mutation result key generation."""
        source_file = temp_file
        test_file = temp_file.with_suffix('.test.py')
        test_file.write_text("test")
        
        mutation_hash = "abc123"
        
        key = CacheKeyGenerator.mutation_result_key(test_file, source_file, mutation_hash)
        
        assert len(key) == 32  # MD5 hash
        
        # Same inputs should generate same key
        key2 = CacheKeyGenerator.mutation_result_key(test_file, source_file, mutation_hash)
        assert key == key2
        
        # Cleanup
        test_file.unlink()
    
    def test_config_hash(self):
        """Test configuration object hashing."""
        config1 = Mock()
        config1.__dict__ = {"setting1": "value1", "setting2": 42}
        
        config2 = Mock()
        config2.__dict__ = {"setting1": "value1", "setting2": 42}
        
        config3 = Mock()
        config3.__dict__ = {"setting1": "value1", "setting2": 43}
        
        hash1 = CacheKeyGenerator.config_hash(config1)
        hash2 = CacheKeyGenerator.config_hash(config2)
        hash3 = CacheKeyGenerator.config_hash(config3)
        
        # Same config should generate same hash
        assert hash1 == hash2
        
        # Different config should generate different hash
        assert hash1 != hash3


class TestProductionCacheManager:
    """Test the production cache manager."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create a production cache manager."""
        return ProductionCacheManager(temp_cache_dir)
    
    @pytest.fixture
    def temp_files(self, temp_cache_dir):
        """Create temporary test and source files."""
        test_file = temp_cache_dir / "test_example.py"
        source_file = temp_cache_dir / "example.py"
        
        test_file.write_text("def test_example(): pass")
        source_file.write_text("def example(): pass")
        
        return test_file, source_file
    
    def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initialization."""
        assert cache_manager.cache is not None
        assert cache_manager.key_generator is not None
        assert cache_manager.cache_dir.exists()
    
    def test_mutation_result_caching(self, cache_manager, temp_files):
        """Test caching and retrieval of mutation results."""
        test_file, source_file = temp_files
        
        mutation = {"type": "boolean_flip", "line": 1, "original": "True", "mutated": "False"}
        result = {"mutation_caught": True, "test_passed": False, "execution_time": 1.5}
        
        # Cache result
        success = cache_manager.cache_mutation_result(test_file, source_file, mutation, result)
        assert success is True
        
        # Retrieve result
        cached_result = cache_manager.get_mutation_result(test_file, source_file, mutation)
        assert cached_result == result
    
    def test_effectiveness_report_caching(self, cache_manager, temp_files):
        """Test caching and retrieval of effectiveness reports."""
        test_file, _ = temp_files
        
        config = Mock()
        config.__dict__ = {"max_mutations": 10, "timeout": 30}
        
        report = Mock()
        report.effectiveness_percentage = 75.0
        report.mutations_caught = 6
        report.mutations_total = 8
        
        # Cache report
        success = cache_manager.cache_effectiveness_report(test_file, config, report)
        assert success is True
        
        # Retrieve report
        cached_report = cache_manager.get_effectiveness_report(test_file, config)
        assert cached_report == report
    
    def test_file_cache_invalidation(self, cache_manager, temp_files):
        """Test invalidation of file-related caches."""
        test_file, source_file = temp_files
        
        # Cache some data
        mutation = {"type": "operator_change", "line": 2}
        result = {"mutation_caught": False}
        cache_manager.cache_mutation_result(test_file, source_file, mutation, result)
        
        # Invalidate caches for the test file
        deleted_count = cache_manager.invalidate_file_caches(test_file)
        assert deleted_count >= 0  # Should delete at least some entries
        
        # Cached data should be gone
        cached_result = cache_manager.get_mutation_result(test_file, source_file, mutation)
        assert cached_result is None
    
    @pytest.mark.asyncio
    async def test_async_operations(self, cache_manager):
        """Test asynchronous cache operations."""
        # Test async set
        success = await cache_manager.set_async("async_key", "async_value", tags=["async_test"])
        assert success is True
        
        # Test async get
        value = await cache_manager.get_async("async_key")
        assert value == "async_value"
    
    def test_performance_report(self, cache_manager):
        """Test performance reporting."""
        report = cache_manager.get_performance_report()
        
        assert 'uptime_seconds' in report
        assert 'cache_stats' in report
        assert 'overall_efficiency' in report
        
        # Should have valid structure
        assert isinstance(report['uptime_seconds'], (int, float))
        assert isinstance(report['cache_stats'], dict)
    
    def test_cache_optimization(self, cache_manager):
        """Test cache optimization functionality."""
        # This should not raise an exception
        cache_manager.optimize_cache()
        
        # Verify optimization ran
        report = cache_manager.get_performance_report()
        assert report is not None
    
    def test_shutdown(self, cache_manager):
        """Test cache manager shutdown."""
        # Should not raise an exception
        cache_manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])