"""
Performance benchmark tests for critical AutoTaskTracker operations.

These tests ensure that key operations complete within acceptable time limits
and help identify performance regressions.
"""
import pytest
import time
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pandas as pd
from pathlib import Path

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.ai.sensitive_filter import SensitiveDataFilter
from autotasktracker.dashboards.cache import DashboardCache, QueryCache
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository


class TestDatabasePerformance:
    """Benchmark database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db_manager = DatabaseManager(db_path)
        yield db_manager
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    def test_database_connection_performance(self, temp_db):
        """Test database connection establishment time."""
        start_time = time.perf_counter()
        
        # Perform 100 connection open/close cycles
        for _ in range(100):
            with temp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / 100
        
        # Should average less than 5ms per connection
        assert avg_time < 0.005, f"Connection too slow: {avg_time*1000:.2f}ms avg"
        
        # Also test that connections are properly released
        assert temp_db._connection_count == 0, "Connections not properly released"
    
    def test_bulk_insert_performance(self, temp_db):
        """Test bulk data insertion performance."""
        # Create test table
        with temp_db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_screenshots (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    filepath TEXT,
                    window_title TEXT
                )
            """)
        
        # Prepare 1000 rows of test data
        test_data = [
            (f"2024-01-01 00:{i//60:02d}:{i%60:02d}", f"/path/screenshot_{i}.png", f"Window {i}")
            for i in range(100)
        ]
        
        start_time = time.perf_counter()
        
        # Bulk insert
        with temp_db.get_connection() as conn:
            conn.executemany(
                "INSERT INTO test_screenshots (timestamp, filepath, window_title) VALUES (?, ?, ?)",
                test_data
            )
            conn.commit()
        
        elapsed = time.perf_counter() - start_time
        
        # Should complete in under 100ms for 1000 rows
        assert elapsed < 0.1, f"Bulk insert too slow: {elapsed*1000:.0f}ms for 1000 rows"
        
        # Verify data was inserted
        with temp_db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM test_screenshots").fetchone()[0]
            assert count == 1000, "Not all rows inserted"
    
    def test_complex_query_performance(self, temp_db):
        """Test complex query with joins and aggregations."""
        # Create and populate test tables
        with temp_db.get_connection() as conn:
            # Create tables
            conn.executescript("""
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT,
                    filepath TEXT
                );
                
                CREATE TABLE metadata_entries (
                    id INTEGER PRIMARY KEY,
                    entity_id INTEGER,
                    key TEXT,
                    value TEXT,
                    FOREIGN KEY(entity_id) REFERENCES entities(id)
                );
                
                CREATE INDEX idx_metadata_entity ON metadata_entries(entity_id);
                CREATE INDEX idx_metadata_key ON metadata_entries(key);
            """)
            
            # Insert test data
            for i in range(500):
                conn.execute(
                    "INSERT INTO entities (created_at, filepath) VALUES (?, ?)",
                    (f"2024-01-01 00:{i//60:02d}:{i%60:02d}", f"/path/screenshot_{i}.png")
                )
                entity_id = conn.lastrowid
                
                # Add metadata
                conn.executemany(
                    "INSERT INTO metadata_entries (entity_id, key, value) VALUES (?, ?, ?)",
                    [
                        (entity_id, "ocr_result", f'Sample text {i}'),
                        (entity_id, "active_window", f'Window {i}'),
                        (entity_id, 'category', f'Category{i % 5}')
                    ]
                )
        
        # Test complex query performance
        query = """
            SELECT 
                e.created_at,
                e.filepath,
                GROUP_CONCAT(CASE WHEN m.key = "active_window" THEN m.value END) as window_title,
                GROUP_CONCAT(CASE WHEN m.key = 'category' THEN m.value END) as category
            FROM entities e
            LEFT JOIN metadata_entries m ON e.id = m.entity_id
            WHERE e.created_at >= ? AND e.created_at <= ?
            GROUP BY e.id
            ORDER BY e.created_at DESC
            LIMIT 100
        """
        
        start_time = time.perf_counter()
        
        with temp_db.get_connection() as conn:
            df = pd.read_sql_query(
                query,
                conn,
                params=('2024-01-01 00:00:00', '2024-01-01 23:59:59')
            )
        
        elapsed = time.perf_counter() - start_time
        
        # Should complete in under 50ms
        assert elapsed < 0.05, f"Complex query too slow: {elapsed*1000:.0f}ms"
        assert len(df) == 100, "Query didn't return expected results"


class TestTaskExtractionPerformance:
    """Benchmark task extraction operations."""
    
    def test_task_extraction_speed(self):
        """Test speed of task extraction from window titles."""
        extractor = TaskExtractor()
        
        # Test various window title patterns
        test_titles = [
            "main.py - Visual Studio Code",
            "AutoTaskTracker - Google Chrome",
            "Terminal - bash - 80x24",
            "Slack | general | MyWorkspace",
            "README.md — project-name",
            "Zoom Meeting",
            "untitled - Notepad++",
            "Document.docx - Microsoft Word"
        ] * 100  # 800 titles total
        
        start_time = time.perf_counter()
        
        # Extract tasks
        results = [extractor.extract_task(title, None) for title in test_titles]
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / len(test_titles)
        
        # Should average less than 0.5ms per extraction
        assert avg_time < 0.0005, f"Extraction too slow: {avg_time*1000:.3f}ms avg"
        assert len(results) == len(test_titles), "Not all titles processed"
        assert all(results), "Some extractions returned empty"
    
    def test_ocr_subtask_extraction_performance(self):
        """Test OCR text processing performance."""
        extractor = TaskExtractor()
        
        # Simulate OCR output
        sample_ocr = {
            "text": " ".join([
                "def calculate_total(items):",
                "    return sum(item.price for item in items)",
                "TODO: Add error handling",
                "FIXME: Handle empty list case",
                "# Calculate tax and shipping",
                "Bug: Decimal precision issues"
            ] * 20)  # Repeat to make it substantial
        }
        
        ocr_json = str(sample_ocr)
        
        start_time = time.perf_counter()
        
        # Run extraction 100 times
        for _ in range(100):
            subtasks = extractor.extract_subtasks_from_ocr(ocr_json)
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / 100
        
        # Should average less than 5ms per extraction
        assert avg_time < 0.005, f"OCR extraction too slow: {avg_time*1000:.1f}ms avg"


class TestSensitiveDataFilterPerformance:
    """Benchmark sensitive data filtering."""
    
    def test_sensitivity_scoring_performance(self):
        """Test performance of sensitivity scoring."""
        filter = SensitiveDataFilter()
        
        # Test texts of varying complexity
        test_texts = [
            "Regular meeting notes about project timeline",
            "Password: admin123, please change ASAP",
            "Contact John at 555-123-4567 or john@example.com",
            "SSN: 123-45-6789, DOB: 01/01/1990",
            "API_KEY=sk-1234567890abcdef, DATABASE_URL=postgres://user:pass@localhost",
            "Credit card: 4111-1111-1111-1111, CVV: 123, Exp: 12/25"
        ] * 50  # 300 texts total
        
        start_time = time.perf_counter()
        
        # Score all texts
        scores = [filter.calculate_sensitivity_score(text) for text in test_texts]
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / len(test_texts)
        
        # Should average less than 1ms per text
        assert avg_time < 0.001, f"Scoring too slow: {avg_time*1000:.2f}ms avg"
        assert len(scores) == len(test_texts), "Not all texts scored"
        assert all(0.0 <= s <= 1.0 for s in scores), "Invalid scores returned"
    
    def test_image_filtering_decision_performance(self):
        """Test performance of image filtering decisions."""
        filter = SensitiveDataFilter()
        
        # Mock image path and metadata
        test_cases = [
            ("/path/to/screenshot1.png", "Password Manager - KeePass"),
            ("/path/to/screenshot2.png", "Visual Studio Code - main.py"),
            ("/path/to/screenshot3.png", "Banking - Chase Online"),
            ("/path/to/screenshot4.png", "Slack | general"),
        ] * 100  # 400 cases
        
        start_time = time.perf_counter()
        
        # Make filtering decisions
        decisions = []
        for image_path, window_title in test_cases:
            should_process, score, metadata = filter.should_process_image(image_path, window_title)
            decisions.append((should_process, score))
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / len(test_cases)
        
        # Should average less than 0.5ms per decision
        assert avg_time < 0.0005, f"Filtering too slow: {avg_time*1000:.3f}ms avg"
        assert len(decisions) == len(test_cases), "Not all cases processed"


class TestCachePerformance:
    """Benchmark caching operations."""
    
    def test_cache_key_generation_performance(self):
        """Test cache key generation speed."""
        # Test with various parameter combinations
        test_params = [
            {"table": "screenshots", "start": "2024-01-01", "end": "2024-01-31", "limit": 100},
            {"query": "complex", "filters": ["a", "b", "c"], "sort": "desc"},
            {"user_id": 12345, "session": "abc123", "timestamp": 1234567890},
        ] * 100
        
        start_time = time.perf_counter()
        
        # Generate cache keys
        keys = []
        for params in test_params:
            key = DashboardCache.create_cache_key("test", **params)
            keys.append(key)
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / len(test_params)
        
        # Should average less than 0.1ms per key
        assert avg_time < 0.0001, f"Key generation too slow: {avg_time*1000:.3f}ms avg"
        assert len(keys) == len(test_params), "Not all keys generated"
        assert len(set(keys)) == len(set(map(str, test_params))), "Keys not unique"
    
    def test_cache_retrieval_performance(self):
        """Test cache retrieval speed with varying cache sizes."""
        mock_state = {}
        
        # Pre-populate cache with data
        for i in range(100):
            cache_key = f"cache_test_key_{i}"
            timestamp_key = f"cache_ts_test_key_{i}"
            mock_state[cache_key] = f"cached_value_{i}"
            mock_state[timestamp_key] = datetime.now()
        
        with patch('streamlit.session_state', mock_state):
            fetch_count = 0
            def fetch_func():
                nonlocal fetch_count
                fetch_count += 1
                return f"new_value_{fetch_count}"
            
            start_time = time.perf_counter()
            
            # Retrieve from cache 1000 times
            results = []
            for i in range(100):
                result = DashboardCache.get_cached(
                    f"test_key_{i % 100}",  # Reuse some keys
                    fetch_func,
                    ttl_seconds=300
                )
                results.append(result)
            
            elapsed = time.perf_counter() - start_time
            avg_time = elapsed / 1000
            
            # Should average less than 0.1ms per retrieval
            assert avg_time < 0.0001, f"Cache retrieval too slow: {avg_time*1000:.3f}ms avg"
            assert len(results) == 1000, "Not all retrievals completed"


class TestRepositoryPerformance:
    """Benchmark repository operations."""
    
    def test_task_repository_batch_operations(self):
        """Test performance of batch task operations."""
        mock_db = Mock()
        repo = TaskRepository(mock_db)
        
        # Mock large dataset
        large_df = pd.DataFrame({
            'id': range(100),
            'created_at': [f'2024-01-01 00:{i//60:02d}:{i%60:02d}' for i in range(100)],
            'filepath': [f'/path/screenshot_{i}.png' for i in range(100)],
            "ocr_result": [f'Text content {i}' for i in range(100)],
            'active_window': [f'Window {i}' for i in range(100)],
            'tasks': [None] * 10000,
            'category': [f'Category{i % 10}' for i in range(100)],
            "active_window": [f'Title {i}' for i in range(100)]
        })
        
        # Mock database operations
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_db.get_connection.return_value = mock_conn
        
        with patch('pandas.read_sql_query', return_value=large_df):
            start_time = time.perf_counter()
            
            # Get tasks for period
            tasks = repo.get_tasks_for_period(
                datetime(2024, 1, 1),
                datetime(2024, 1, 31)
            )
            
            elapsed = time.perf_counter() - start_time
            
            # Should process 10k records in under 100ms
            assert elapsed < 0.1, f"Task processing too slow: {elapsed*1000:.0f}ms for 10k records"
            assert len(tasks) == 10000, "Not all tasks processed"


class TestEndToEndPerformance:
    """Test end-to-end operation performance."""
    
    def test_screenshot_processing_pipeline(self):
        """Test complete screenshot processing pipeline performance."""
        # Simulate end-to-end processing
        extractor = TaskExtractor()
        sensitive_filter = SensitiveDataFilter()
        
        # Mock screenshot data
        screenshot_data = {
            'filepath': '/path/to/screenshot.png',
            "active_window": 'main.py - Visual Studio Code',
            "ocr_result": '{"text": "def process_data():\\n    return data"}'
        }
        
        start_time = time.perf_counter()
        
        # Run 100 iterations of the pipeline
        for _ in range(100):
            # 1. Check if should process
            should_process, score, _ = sensitive_filter.should_process_image(
                screenshot_data['filepath'],
                screenshot_data["active_window"]
            )
            
            if should_process:
                # 2. Extract main task
                task = extractor.extract_task(
                    screenshot_data["active_window"],
                    screenshot_data["ocr_result"]
                )
                
                # 3. Extract subtasks
                subtasks = extractor.extract_subtasks_from_ocr(
                    screenshot_data["ocr_result"]
                )
                
                # 4. Calculate sensitivity
                sensitivity = sensitive_filter.calculate_sensitivity_score(
                    screenshot_data["ocr_result"],
                    screenshot_data["active_window"]
                )
        
        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / 100
        
        # Complete pipeline should average less than 10ms
        assert avg_time < 0.01, f"Pipeline too slow: {avg_time*1000:.1f}ms avg"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--durations=10"])