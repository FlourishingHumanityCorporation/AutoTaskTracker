"""Database performance tests for AutoTaskTracker."""
import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from autotasktracker.core.database import DatabaseManager


class TestDatabasePerformance:
    """Test database performance under various conditions."""

    @pytest.fixture
    def db_manager(self):
        """Create a test database manager."""
        return DatabaseManager()

    def test_connection_pool_performance(self, db_manager):
        """Test database connection pool performance."""
        connection_times = []
        
        # Test multiple rapid connections
        for _ in range(10):
            start_time = time.time()
            with db_manager.get_connection() as conn:
                # Perform a simple query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result is not None
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
        
        # Analyze performance
        avg_connection_time = sum(connection_times) / len(connection_times)
        max_connection_time = max(connection_times)
        
        # Performance thresholds
        assert avg_connection_time < 0.1, f"Average connection time too slow: {avg_connection_time:.3f}s"
        assert max_connection_time < 0.5, f"Max connection time too slow: {max_connection_time:.3f}s"

    def test_concurrent_connections(self, db_manager):
        """Test concurrent database connections."""
        def worker_task(worker_id):
            """Worker task for concurrent testing."""
            results = []
            for i in range(5):
                start_time = time.time()
                try:
                    with db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM entities")
                        count = cursor.fetchone()
                        results.append({
                            'worker_id': worker_id,
                            'iteration': i,
                            'time': time.time() - start_time,
                            'count': count[0] if count else 0,
                            'success': True
                        })
                except Exception as e:
                    results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'time': time.time() - start_time,
                        'error': str(e),
                        'success': False
                    })
            return results
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            all_results = []
            
            for future in as_completed(futures):
                results = future.result()
                all_results.extend(results)
        
        # Analyze results
        successful_operations = [r for r in all_results if r['success']]
        failed_operations = [r for r in all_results if not r['success']]
        
        # Performance assertions
        success_rate = len(successful_operations) / len(all_results)
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
        
        if successful_operations:
            avg_time = sum(r['time'] for r in successful_operations) / len(successful_operations)
            assert avg_time < 0.2, f"Average query time under load too slow: {avg_time:.3f}s"

    def test_large_result_set_performance(self, db_manager):
        """Test performance with large result sets."""
        # Test query with increasing result sizes
        sizes = [100, 500, 1000]
        times = []
        
        for size in sizes:
            start_time = time.time()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM entities LIMIT {size}")
                results = cursor.fetchall()
                assert len(results) <= size
            query_time = time.time() - start_time
            times.append(query_time)
        
        # Check that time doesn't grow exponentially
        for i in range(1, len(times)):
            # Time should scale roughly linearly, not exponentially
            time_ratio = times[i] / times[i-1]
            size_ratio = sizes[i] / sizes[i-1]
            
            # Allow some overhead, but shouldn't be more than 2x the size ratio
            assert time_ratio <= size_ratio * 2, f"Performance degrades too quickly with size: {time_ratio:.2f}x vs {size_ratio:.2f}x"

    def test_query_optimization(self, db_manager):
        """Test query performance optimization."""
        # Test different query patterns
        queries = [
            ("SELECT * FROM entities WHERE id = ?", [1]),
            ("SELECT COUNT(*) FROM entities", []),
            ("SELECT * FROM entities ORDER BY created_at DESC LIMIT 10", []),
            ("SELECT e.*, m.value FROM entities e LEFT JOIN metadata_entries m ON e.id = m.entity_id LIMIT 10", [])
        ]
        
        query_times = {}
        
        for query, params in queries:
            times = []
            # Run each query multiple times
            for _ in range(3):
                start_time = time.time()
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                query_time = time.time() - start_time
                times.append(query_time)
            
            avg_time = sum(times) / len(times)
            query_times[query[:30] + "..."] = avg_time
        
        # All queries should complete reasonably quickly
        for query_desc, avg_time in query_times.items():
            assert avg_time < 1.0, f"Query too slow: {query_desc} took {avg_time:.3f}s"

    def test_memory_usage_patterns(self, db_manager):
        """Test memory usage patterns during database operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        for _ in range(10):
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                # Large query that might consume memory
                cursor.execute("SELECT * FROM entities LIMIT 1000")
                results = cursor.fetchall()
                
                # Process results to simulate real usage
                processed_count = len([r for r in results if r])
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB)
        max_growth = 50 * 1024 * 1024  # 50MB
        assert memory_growth < max_growth, f"Excessive memory growth: {memory_growth / 1024 / 1024:.1f}MB"

    def test_connection_recovery(self, db_manager):
        """Test database connection recovery after failures."""
        # Test normal operation
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        
        # Simulate connection failure and recovery
        original_test_connection = db_manager.test_connection
        
        # Mock a temporary connection failure
        failure_count = 0
        def mock_test_connection():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Fail first 2 attempts
                return False
            return original_test_connection()
        
        with patch.object(db_manager, 'test_connection', side_effect=mock_test_connection):
            # This should still work after retries
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1

    def test_transaction_performance(self, db_manager):
        """Test transaction performance."""
        # Test individual operations vs batch operations
        
        # Individual operations
        start_time = time.time()
        for i in range(10):
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entities")
                cursor.fetchone()
        individual_time = time.time() - start_time
        
        # Batch operations
        start_time = time.time()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            for i in range(10):
                cursor.execute("SELECT COUNT(*) FROM entities")
                cursor.fetchone()
        batch_time = time.time() - start_time
        
        # Batch should be significantly faster
        improvement = (individual_time - batch_time) / individual_time
        assert improvement > 0.2, f"Batch operations should be faster: {improvement:.1%} improvement"

    def test_postgresql_vs_sqlite_performance(self, db_manager):
        """Test performance differences between PostgreSQL and SQLite."""
        # This test adapts based on the actual database type
        is_postgresql = db_manager._is_postgresql
        
        # Basic performance test
        start_time = time.time()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM entities")
            count = cursor.fetchone()
        query_time = time.time() - start_time
        
        if is_postgresql:
            # PostgreSQL might be slightly slower due to network overhead
            max_time = 0.5
        else:
            # SQLite should be very fast for simple queries
            max_time = 0.1
        
        assert query_time < max_time, f"Query too slow for {('PostgreSQL' if is_postgresql else 'SQLite')}: {query_time:.3f}s"


class TestCachePerformance:
    """Test cache performance specifically."""

    @pytest.fixture
    def cache_manager(self):
        """Create a test cache manager."""
        from autotasktracker.pensieve.cache_manager import PensieveCacheManager
        return PensieveCacheManager()

    def test_cache_hit_performance(self, cache_manager):
        """Test cache hit vs miss performance."""
        # Clear cache
        cache_manager.clear()
        
        # Test cache miss (first access)
        start_time = time.time()
        result1 = cache_manager.get("test_key")
        miss_time = time.time() - start_time
        
        # Set a value
        cache_manager.set("test_key", {"data": "test_value"})
        
        # Test cache hit
        start_time = time.time()
        result2 = cache_manager.get("test_key")
        hit_time = time.time() - start_time
        
        # Cache hit should be much faster than miss
        if miss_time > 0:  # Avoid division by zero
            improvement = (miss_time - hit_time) / miss_time
            assert improvement > 0.5, f"Cache hit should be significantly faster: {improvement:.1%} improvement"

    def test_cache_memory_efficiency(self, cache_manager):
        """Test cache memory usage efficiency."""
        # Clear cache and get initial stats
        cache_manager.clear()
        initial_stats = cache_manager.get_stats()
        
        # Add test data
        test_data = {"large_data": "x" * 1000}  # 1KB of data
        for i in range(100):
            cache_manager.set(f"key_{i}", test_data)
        
        # Check memory usage
        final_stats = cache_manager.get_stats()
        
        # Should track memory usage
        if 'memory_usage' in final_stats:
            memory_usage = final_stats['memory_usage']
            # Should be reasonable (less than 1MB for this test)
            assert memory_usage < 1024 * 1024, f"Cache using too much memory: {memory_usage} bytes"

    def test_cache_eviction_performance(self, cache_manager):
        """Test cache eviction performance."""
        cache_manager.clear()
        
        # Fill cache beyond capacity (if it has limits)
        large_data = {"data": "x" * 10000}  # 10KB per item
        
        times = []
        for i in range(50):
            start_time = time.time()
            cache_manager.set(f"large_key_{i}", large_data)
            set_time = time.time() - start_time
            times.append(set_time)
        
        # Performance shouldn't degrade significantly over time
        if len(times) > 10:
            early_avg = sum(times[:10]) / 10
            late_avg = sum(times[-10:]) / 10
            
            # Later operations shouldn't be more than 2x slower
            if early_avg > 0:
                degradation = late_avg / early_avg
                assert degradation < 2.0, f"Cache performance degrades too much: {degradation:.2f}x slower"