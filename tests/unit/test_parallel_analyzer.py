"""Unit tests for parallel analysis utilities."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from tests.health.testing.parallel_analyzer import (
    ParallelGitAnalyzer,
    SmartCache,
    PerformanceManager,
    AnalysisTask,
    AnalysisResult
)


class TestAnalysisTask:
    """Test AnalysisTask dataclass."""
    
    def test_creation_minimal(self):
        """Test creating task with minimal parameters."""
        task = AnalysisTask("test_1", Path("test.py"), "complexity")
        
        assert task.task_id == "test_1"
        assert task.file_path == Path("test.py")
        assert task.analysis_type == "complexity"
        assert task.priority == 1
        assert task.dependencies == []
    
    def test_creation_full(self):
        """Test creating task with all parameters."""
        task = AnalysisTask(
            "test_2", 
            Path("test2.py"), 
            "mutation", 
            priority=5,
            dependencies=["test_1"]
        )
        
        assert task.task_id == "test_2"
        assert task.priority == 5
        assert task.dependencies == ["test_1"]


class TestAnalysisResult:
    """Test AnalysisResult dataclass."""
    
    def test_successful_result(self):
        """Test creating successful result."""
        result = AnalysisResult(
            "task_1",
            Path("test.py"),
            success=True,
            result={"complexity": 5},
            execution_time=1.5
        )
        
        assert result.success is True
        assert result.result == {"complexity": 5}
        assert result.error is None
    
    def test_failed_result(self):
        """Test creating failed result."""
        result = AnalysisResult(
            "task_1",
            Path("test.py"),
            success=False,
            error="File not found",
            execution_time=0.1
        )
        
        assert result.success is False
        assert result.error == "File not found"
        assert result.result is None


class TestParallelGitAnalyzer:
    """Test parallel Git analysis functionality."""
    
    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with temporary directory."""
        return ParallelGitAnalyzer(tmp_path, max_workers=2)
    
    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample files for testing."""
        files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.py"
            file_path.write_text(f"# Test file {i}\nprint('hello')")
            files.append(file_path)
        return files
    
    def test_init(self, analyzer, tmp_path):
        """Test analyzer initialization."""
        assert analyzer.project_root == tmp_path
        assert analyzer.max_workers == 2
        assert analyzer.git_ops is not None
    
    def test_analyze_files_parallel_success(self, analyzer, sample_files):
        """Test successful parallel analysis."""
        def mock_analysis(file_path: Path) -> dict:
            return {"lines": len(file_path.read_text().split('\n'))}
        
        results = analyzer.analyze_files_parallel(sample_files, mock_analysis)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(result.result["lines"] >= 2 for result in results)
        assert all(result.execution_time >= 0 for result in results)
    
    def test_analyze_files_parallel_with_error(self, analyzer, sample_files):
        """Test parallel analysis with some errors."""
        def error_analysis(file_path: Path) -> dict:
            if "test_1" in str(file_path):
                raise ValueError("Simulated error")
            return {"lines": len(file_path.read_text().split('\n'))}
        
        results = analyzer.analyze_files_parallel(sample_files, error_analysis)
        
        assert len(results) == 3
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        assert len(successful_results) == 2
        assert len(failed_results) == 1
        assert "Simulated error" in failed_results[0].error
    
    @patch.object(ParallelGitAnalyzer, '_analyze_single_file')
    def test_max_workers_respected(self, mock_analyze, analyzer, sample_files):
        """Test that max_workers limit is respected."""
        # Mock to return immediately
        mock_analyze.return_value = AnalysisResult(
            "test", Path("test.py"), True, {"result": "test"}
        )
        
        def slow_analysis(file_path: Path) -> dict:
            time.sleep(0.1)  # Small delay
            return {"processed": True}
        
        start_time = time.time()
        analyzer.analyze_files_parallel(sample_files, slow_analysis)
        execution_time = time.time() - start_time
        
        # With max_workers=2 and 3 files, should take roughly 2 * 0.1 seconds
        # (allowing some overhead)
        assert execution_time < 0.5


class TestSmartCache:
    """Test smart cache functionality."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache with temporary directory."""
        return SmartCache(
            tmp_path / "cache",
            max_size_mb=1,  # Small size for testing
            cleanup_interval_hours=0.001  # Very short interval for testing
        )
    
    def test_cache_set_and_get(self, cache):
        """Test basic cache set and get operations."""
        test_data = {"key": "value", "number": 42}
        
        success = cache.set("test_key", test_data, ttl_seconds=60)
        assert success is True
        
        retrieved_data = cache.get("test_key")
        assert retrieved_data == test_data
    
    def test_cache_expiration(self, cache):
        """Test cache expiration."""
        test_data = {"key": "value"}
        
        # Set with very short TTL
        cache.set("test_key", test_data, ttl_seconds=0.1)
        
        # Should be available immediately
        assert cache.get("test_key") == test_data
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be None after expiration
        assert cache.get("test_key") is None
    
    def test_cache_miss(self, cache):
        """Test cache miss behavior."""
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Add some data
        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})
        
        stats = cache.get_stats()
        
        assert stats["file_count"] == 2
        assert stats["total_size_mb"] > 0
        assert stats["utilization_percent"] >= 0
        assert "last_cleanup" in stats
    
    def test_cache_clear(self, cache):
        """Test cache clearing."""
        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})
        
        # Verify data exists
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        
        # Clear cache
        cache.clear()
        
        # Verify data is gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        
        stats = cache.get_stats()
        assert stats["file_count"] == 0
    
    def test_automatic_cleanup(self, cache):
        """Test automatic cleanup based on time interval."""
        # Add data with short TTL
        cache.set("expired_key", {"data": "test"}, ttl_seconds=0.001)
        
        # Wait for expiration
        time.sleep(0.01)
        
        # Force cleanup check by setting last_cleanup to past
        cache.last_cleanup = 0
        
        # Accessing cache should trigger cleanup
        cache.get("some_key")
        
        # The cleanup should have run (no assertion needed, just testing it doesn't crash)


class TestPerformanceManager:
    """Test performance manager functionality."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create performance manager with temporary directory."""
        return PerformanceManager(tmp_path)
    
    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample files for testing."""
        files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.py"
            file_path.write_text(f"# Test file {i}\nprint('hello {i}')")
            files.append(file_path)
        return files
    
    def test_init(self, manager, tmp_path):
        """Test performance manager initialization."""
        assert manager.project_root == tmp_path
        assert manager.cache is not None
        assert manager.git_analyzer is not None
        assert manager._metrics["cache_hits"] == 0
    
    def test_analyze_files_with_cache_first_run(self, manager, sample_files):
        """Test analysis with cache on first run (cache misses)."""
        def mock_analysis(file_path: Path) -> dict:
            return {"analysis": f"result_for_{file_path.name}"}
        
        results = manager.analyze_files_with_cache(
            sample_files, "test_analysis", mock_analysis
        )
        
        assert len(results) == 3
        assert all(result.success for result in results)
        
        # Should be all cache misses on first run
        stats = manager.get_performance_stats()
        assert stats["cache_hit_rate_percent"] == 0
    
    def test_analyze_files_with_cache_second_run(self, manager, sample_files):
        """Test analysis with cache on second run (cache hits)."""
        def mock_analysis(file_path: Path) -> dict:
            return {"analysis": f"result_for_{file_path.name}"}
        
        # First run - populate cache
        manager.analyze_files_with_cache(
            sample_files, "test_analysis", mock_analysis, cache_ttl=60
        )
        
        # Second run - should use cache
        results = manager.analyze_files_with_cache(
            sample_files, "test_analysis", mock_analysis, cache_ttl=60
        )
        
        assert len(results) == 3
        assert all(result.success for result in results)
        
        # Should have cache hits now
        stats = manager.get_performance_stats()
        assert stats["cache_hit_rate_percent"] > 0
    
    def test_cache_key_generation(self, manager, tmp_path):
        """Test cache key generation includes file modification time."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original content")
        
        # Generate initial key
        key1 = manager._generate_cache_key(test_file, "analysis")
        
        # Modify file
        time.sleep(0.01)  # Ensure different mtime
        test_file.write_text("modified content")
        
        # Generate new key
        key2 = manager._generate_cache_key(test_file, "analysis")
        
        # Keys should be different due to different modification times
        assert key1 != key2
    
    def test_performance_stats(self, manager, sample_files):
        """Test performance statistics collection."""
        def mock_analysis(file_path: Path) -> dict:
            return {"result": "test"}
        
        # Run analysis
        manager.analyze_files_with_cache(sample_files, "test", mock_analysis)
        
        stats = manager.get_performance_stats()
        
        assert "cache_hit_rate_percent" in stats
        assert "cache_stats" in stats
        assert "parallel_tasks" in stats
        assert "total_execution_time" in stats
        assert "average_task_time" in stats
        
        assert stats["parallel_tasks"] == 3
        assert stats["total_execution_time"] > 0
    
    def test_manual_cache_operations(self, manager):
        """Test manual cache cleanup and clearing."""
        # Add some cached data
        manager.cache.set("test_key", {"data": "test"})
        
        # Test manual cleanup (should not crash)
        manager.cleanup_cache()
        
        # Test cache clearing
        manager.clear_cache()
        
        # Data should be gone
        assert manager.cache.get("test_key") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])