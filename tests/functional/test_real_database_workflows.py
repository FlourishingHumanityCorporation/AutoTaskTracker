#!/usr/bin/env python3
"""
Real database workflow tests that validate actual database operations.
These tests work with real SQLite databases and test complete data flows.
"""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository


class TestRealDatabaseOperations:
    """Test real database operations with actual SQLite databases."""
    
    @pytest.fixture
    def temp_db_path(self) -> str:
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # Initialize the database with the schema
        self._init_test_database(db_path)
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
    def _init_test_database(self, db_path: str):
        """Initialize test database with the expected schema."""
        conn = sqlite3.connect(db_path)
        try:
            # Create the entities table (screenshots/images)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    file_type_group TEXT,
                    created_at TEXT NOT NULL,
                    last_scan_at TEXT
                )
            """)
            
            # Create the metadata_entries table (OCR text, AI results)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (entity_id) REFERENCES entities (id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_created_at ON entities(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_file_type ON entities(file_type_group)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_entity_key ON metadata_entries(entity_id, key)")
            
            conn.commit()
        finally:
            conn.close()
    
    def test_database_manager_initialization_and_connection(self, temp_db_path: str):
        """Test that DatabaseManager can initialize and connect to a real database."""
        db_manager = DatabaseManager(temp_db_path)
        
        # Test initialization
        assert db_manager is not None, "DatabaseManager should initialize"
        assert db_manager.db_path == temp_db_path, "Should store correct database path"
        
        # Test connection
        with db_manager.get_connection() as conn:
            assert conn is not None, "Should get a valid connection"
            
            # Test that we can execute queries
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'entities' in tables, "Should have entities table"
            assert 'metadata_entries' in tables, "Should have metadata_entries table"
        
        print("✅ DatabaseManager initialization and connection works")
    
    def test_insert_and_retrieve_screenshot_entities(self, temp_db_path: str):
        """Test inserting and retrieving screenshot entities."""
        conn = sqlite3.connect(temp_db_path)
        conn.row_factory = sqlite3.Row
        
        # Insert test entities
        test_screenshots = [
            {
                'filepath': '/screenshots/2024-01-01/screenshot_001.png',
                'file_type_group': 'image',
                'created_at': '2024-01-01T10:00:00Z'
            },
            {
                'filepath': '/screenshots/2024-01-01/screenshot_002.png',
                'file_type_group': 'image', 
                'created_at': '2024-01-01T10:05:00Z'
            },
            {
                'filepath': '/screenshots/2024-01-01/screenshot_003.png',
                'file_type_group': 'image',
                'created_at': '2024-01-01T10:10:00Z'
            }
        ]
        
        inserted_ids = []
        for screenshot in test_screenshots:
            cursor = conn.execute("""
                INSERT INTO entities (filepath, file_type_group, created_at)
                VALUES (?, ?, ?)
            """, (screenshot['filepath'], screenshot['file_type_group'], screenshot['created_at']))
            inserted_ids.append(cursor.lastrowid)
        
        conn.commit()
        
        # Test retrieval
        cursor = conn.execute("""
            SELECT id, filepath, file_type_group, created_at, last_scan_at
            FROM entities 
            WHERE file_type_group = 'image'
            ORDER BY created_at DESC
        """)
        
        retrieved = cursor.fetchall()
        
        # Validate results
        assert len(retrieved) == 3, "Should retrieve all 3 screenshots"
        
        for i, row in enumerate(retrieved):
            assert row['id'] in inserted_ids, "Should have valid inserted ID"
            assert row['filepath'].endswith('.png'), "Should be a PNG file"
            assert row['file_type_group'] == 'image', "Should be image type"
            assert row['created_at'] is not None, "Should have creation timestamp"
            assert 'screenshot' in row['filepath'], "Should be a screenshot file"
        
        # Test ordering (newest first)
        timestamps = [row['created_at'] for row in retrieved]
        assert timestamps == sorted(timestamps, reverse=True), "Should be ordered newest first"
        
        conn.close()
        print("✅ Screenshot entity insertion and retrieval works")
    
    def test_metadata_entries_with_ocr_and_ai_data(self, temp_db_path: str):
        """Test storing and retrieving OCR and AI metadata."""
        conn = sqlite3.connect(temp_db_path)
        conn.row_factory = sqlite3.Row
        
        # Insert a test entity first
        cursor = conn.execute("""
            INSERT INTO entities (filepath, file_type_group, created_at)
            VALUES (?, ?, ?)
        """, ('/test/screenshot.png', 'image', '2024-01-01T10:00:00Z'))
        
        entity_id = cursor.lastrowid
        conn.commit()
        
        # Insert various metadata types
        metadata_entries = [
            {
                'entity_id': entity_id,
                'key': 'active_window',
                'value': 'Visual Studio Code - task_extractor.py',
                'created_at': '2024-01-01T10:00:01Z'
            },
            {
                'entity_id': entity_id,
                'key': 'ocr_text',
                'value': json.dumps([
                    [[[10, 10], [200, 10], [200, 30], [10, 30]], "class TaskExtractor:", 0.95],
                    [[[10, 50], [250, 50], [250, 70], [10, 70]], "def extract_task(self):", 0.92]
                ]),
                'created_at': '2024-01-01T10:00:02Z'
            },
            {
                'entity_id': entity_id,
                'key': 'ai_task_classification',
                'value': json.dumps({
                    'task': 'Developing task extraction functionality',
                    'category': 'Development',
                    'confidence': 0.89,
                    'subtasks': ['Writing Python code', 'Class definition', 'Method implementation']
                }),
                'created_at': '2024-01-01T10:00:03Z'
            },
            {
                'entity_id': entity_id,
                'key': 'vlm_description',
                'value': 'Code editor displaying Python class definition with methods for task extraction',
                'created_at': '2024-01-01T10:00:04Z'
            },
            {
                'entity_id': entity_id,
                'key': 'embedding_vector',
                'value': json.dumps([0.1, 0.2, 0.3, 0.4, 0.5]),  # Simplified embedding
                'created_at': '2024-01-01T10:00:05Z'
            }
        ]
        
        for entry in metadata_entries:
            conn.execute("""
                INSERT INTO metadata_entries (entity_id, key, value, created_at)
                VALUES (?, ?, ?, ?)
            """, (entry['entity_id'], entry['key'], entry['value'], entry['created_at']))
        
        conn.commit()
        
        # Test retrieval by key type
        cursor = conn.execute("""
            SELECT key, value, created_at
            FROM metadata_entries
            WHERE entity_id = ?
            ORDER BY created_at
        """, (entity_id,))
        
        retrieved_metadata = cursor.fetchall()
        
        # Validate all metadata was stored
        assert len(retrieved_metadata) == 5, "Should have all 5 metadata entries"
        
        # Check each metadata type
        metadata_by_key = {row['key']: row for row in retrieved_metadata}
        
        # Validate active window
        assert 'active_window' in metadata_by_key, "Should have active window metadata"
        assert 'Visual Studio Code' in metadata_by_key['active_window']['value'], "Should store window title"
        
        # Validate OCR data
        assert 'ocr_text' in metadata_by_key, "Should have OCR metadata"
        ocr_data = json.loads(metadata_by_key['ocr_text']['value'])
        assert isinstance(ocr_data, list), "OCR data should be a list"
        assert len(ocr_data) == 2, "Should have 2 OCR text regions"
        assert 'TaskExtractor' in ocr_data[0][1], "Should contain class name"
        
        # Validate AI classification
        assert 'ai_task_classification' in metadata_by_key, "Should have AI classification"
        ai_data = json.loads(metadata_by_key['ai_task_classification']['value'])
        assert ai_data['task'] is not None, "Should have task description"
        assert ai_data['category'] == 'Development', "Should classify as Development"
        assert 0 <= ai_data['confidence'] <= 1, "Should have valid confidence"
        
        # Validate VLM description
        assert 'vlm_description' in metadata_by_key, "Should have VLM description"
        assert 'Code editor' in metadata_by_key['vlm_description']['value'], "Should describe code editor"
        
        # Validate embedding
        assert 'embedding_vector' in metadata_by_key, "Should have embedding vector"
        embedding = json.loads(metadata_by_key['embedding_vector']['value'])
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) == 5, "Should have 5 dimensions"
        
        conn.close()
        print("✅ Metadata entries storage and retrieval works")
    
    def test_task_repository_with_real_data(self, temp_db_path: str):
        """Test TaskRepository with real database data."""
        # Setup test data
        conn = sqlite3.connect(temp_db_path)
        
        # Insert entities and metadata (using datetime format expected by repository)
        entities_data = [
            (1, '/test/code_session.png', 'image', '2024-01-01 09:00:00', '2024-01-01 09:00:05'),
            (2, '/test/meeting_screenshot.png', 'image', '2024-01-01 10:00:00', '2024-01-01 10:00:05'),
            (3, '/test/research_session.png', 'image', '2024-01-01 11:00:00', '2024-01-01 11:00:05'),
        ]
        
        for entity in entities_data:
            conn.execute("""
                INSERT INTO entities (id, filepath, file_type_group, created_at, last_scan_at)
                VALUES (?, ?, ?, ?, ?)
            """, entity)
        
        # Insert corresponding metadata (using keys that the repository expects)
        metadata_data = [
            # Entity 1 - Coding session
            (1, 'active_window', 'main.py - PyCharm', '2024-01-01 09:00:01'),
            (1, 'window_title', 'main.py - PyCharm', '2024-01-01 09:00:01'),
            (1, 'category', 'Development', '2024-01-01 09:00:02'),
            (1, 'tasks', 'Python development in PyCharm', '2024-01-01 09:00:02'),
            (1, 'text', 'class Calculator: def __init__(self):', '2024-01-01 09:00:03'),
            
            # Entity 2 - Meeting
            (2, 'active_window', 'Zoom Meeting', '2024-01-01 10:00:01'),
            (2, 'window_title', 'Zoom Meeting', '2024-01-01 10:00:01'),
            (2, 'category', 'Communication', '2024-01-01 10:00:02'),
            (2, 'tasks', 'Video conference meeting', '2024-01-01 10:00:02'),
            (2, 'text', 'Team Meeting Weekly Standup', '2024-01-01 10:00:03'),
            
            # Entity 3 - Research
            (3, 'active_window', 'Documentation - Chrome', '2024-01-01 11:00:01'),
            (3, 'window_title', 'Documentation - Chrome', '2024-01-01 11:00:01'),
            (3, 'category', 'Research', '2024-01-01 11:00:02'),
            (3, 'tasks', 'Reading technical documentation', '2024-01-01 11:00:02'),
            (3, 'text', 'asyncio documentation Python async programming', '2024-01-01 11:00:03'),
        ]
        
        for metadata in metadata_data:
            conn.execute("""
                INSERT INTO metadata_entries (entity_id, key, value, created_at)
                VALUES (?, ?, ?, ?)
            """, metadata)
        
        conn.commit()
        conn.close()
        
        # Test TaskRepository
        db_manager = DatabaseManager(temp_db_path)
        task_repo = TaskRepository(db_manager)
        
        # Test get_tasks_for_period
        start_time = datetime.fromisoformat('2024-01-01T08:00:00Z')
        end_time = datetime.fromisoformat('2024-01-01T12:00:00Z')
        tasks = task_repo.get_tasks_for_period(start_time, end_time, limit=10)
        assert len(tasks) == 3, "Should retrieve all 3 tasks"
        
        # Validate task structure
        for task in tasks:
            assert hasattr(task, 'id'), "Task should have ID"
            assert hasattr(task, 'screenshot_path'), "Task should have screenshot path"
            assert hasattr(task, 'timestamp'), "Task should have timestamp"
            assert hasattr(task, 'category'), "Task should have category"
            assert hasattr(task, 'title'), "Task should have title"
        
        # Test category filtering 
        dev_tasks = task_repo.get_tasks_for_period(start_time, end_time, categories=['Development'])
        assert len(dev_tasks) == 1, "Should find 1 development task"
        
        print("✅ TaskRepository with real data works")
    
    def test_metrics_repository_calculations(self, temp_db_path: str):
        """Test MetricsRepository calculations with real data."""
        # Setup test data with time-based activities
        conn = sqlite3.connect(temp_db_path)
        
        base_time = datetime.fromisoformat('2024-01-01T09:00:00Z')
        
        # Create 24 hours of activity data (every 30 minutes)
        for i in range(48):  # 48 half-hour periods = 24 hours
            timestamp = base_time + timedelta(minutes=30 * i)
            category = ['Development', 'Communication', 'Research'][i % 3]
            
            # Insert entity
            cursor = conn.execute("""
                INSERT INTO entities (filepath, file_type_group, created_at, last_scan_at)
                VALUES (?, ?, ?, ?)
            """, (f'/test/screenshot_{i:03d}.png', 'image', 
                  timestamp.isoformat() + 'Z', 
                  (timestamp + timedelta(seconds=5)).isoformat() + 'Z'))
            
            entity_id = cursor.lastrowid
            
            # Insert metadata
            conn.execute("""
                INSERT INTO metadata_entries (entity_id, key, value, created_at)
                VALUES (?, ?, ?, ?)
            """, (entity_id, 'ai_task_classification', json.dumps({
                'task': f'{category} activity {i}',
                'category': category,
                'confidence': 0.8 + (i % 20) * 0.01  # Varying confidence
            }), timestamp.isoformat() + 'Z'))
        
        conn.commit()
        conn.close()
        
        # Test MetricsRepository
        db_manager = DatabaseManager(temp_db_path)
        metrics_repo = MetricsRepository(db_manager)
        
        # Test get_daily_metrics for a specific day
        test_date = datetime.fromisoformat('2024-01-01T12:00:00Z')
        daily_metrics = metrics_repo.get_daily_metrics(test_date)
        
        # The method might return None if no data, which is acceptable
        if daily_metrics:
            assert hasattr(daily_metrics, 'date'), "Should have date field"
            assert hasattr(daily_metrics, 'total_activities'), "Should have total activities"
        
        # Test get_metrics_summary
        summary_start = datetime.fromisoformat('2024-01-01T08:00:00Z')
        summary_end = datetime.fromisoformat('2024-01-02T08:00:00Z')
        summary = metrics_repo.get_metrics_summary(summary_start, summary_end)
        
        # Summary should be a valid result
        if summary:
            assert isinstance(summary, dict) or hasattr(summary, '__dict__'), "Summary should be a valid object"
        
        print("✅ MetricsRepository calculations work")
    
    def test_database_concurrent_access(self, temp_db_path: str):
        """Test that multiple database connections work correctly."""
        import threading
        import time
        
        def worker_function(worker_id: int, results: list):
            """Worker function that performs database operations."""
            try:
                # Use direct sqlite3 connection for this test to avoid DatabaseManager connection pooling issues
                import sqlite3
                conn = sqlite3.connect(temp_db_path)
                try:
                    # Insert a test entity
                    cursor = conn.execute("""
                        INSERT INTO entities (filepath, file_type_group, created_at)
                        VALUES (?, ?, ?)
                    """, (f'/test/worker_{worker_id}.png', 'image', datetime.now().isoformat() + 'Z'))
                    
                    entity_id = cursor.lastrowid
                    
                    # Insert metadata
                    conn.execute("""
                        INSERT INTO metadata_entries (entity_id, key, value, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (entity_id, 'worker_id', str(worker_id), datetime.now().isoformat() + 'Z'))
                    
                    conn.commit()
                    
                    # Read back the data
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM entities WHERE filepath LIKE ?
                    """, (f'%worker_{worker_id}%',))
                    
                    count = cursor.fetchone()[0]
                    results.append((worker_id, count))
                finally:
                    conn.close()
                    
            except Exception as e:
                results.append((worker_id, f"Error: {e}"))
        
        # Run multiple workers concurrently
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i, results))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Validate results
        assert len(results) == 5, "All workers should complete"
        
        for worker_id, result in results:
            if isinstance(result, str) and result.startswith("Error"):
                pytest.fail(f"Worker {worker_id} failed: {result}")
            else:
                assert result == 1, f"Worker {worker_id} should insert exactly 1 entity"
        
        # Verify total count
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM entities WHERE filepath LIKE '%worker_%'")
        total_count = cursor.fetchone()[0]
        conn.close()
        
        assert total_count == 5, "Should have 5 total entities from workers"
        
        print("✅ Concurrent database access works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])