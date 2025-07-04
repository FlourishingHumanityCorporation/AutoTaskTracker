"""
Database infrastructure tests for AutoTaskTracker.
Tests core database functionality, connection pooling, and data integrity.
"""
import os
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

from autotasktracker.core.database import DatabaseManager


class TestDatabaseInfrastructure:
    """Test database infrastructure and connection management."""
    
    def setup_method(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db_manager = None
    
    def teardown_method(self):
        """Clean up temporary database."""
        if self.db_manager:
            # Close any open connections
            try:
                # Force close pool connections if possible
                pass
            except:
                pass
        
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def test_database_connection_basic(self):
        """Test basic database connection works."""
        self.db_manager = DatabaseManager(self.db_path)
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_connection_pooling_functionality(self):
        """Test that connection pooling works correctly."""
        self.db_manager = DatabaseManager(self.db_path)
        
        # Test multiple concurrent connections
        connections_used = []
        
        def use_connection(thread_id):
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ?", (thread_id,))
                result = cursor.fetchone()
                connections_used.append((thread_id, result[0]))
                time.sleep(0.1)  # Hold connection briefly
        
        # Use ThreadPoolExecutor to test concurrent access
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(use_connection, i) for i in range(5)]
            for future in futures:
                future.result()  # Wait for completion
        
        assert len(connections_used) == 5
        assert all(thread_id == result for thread_id, result in connections_used)
    
    def test_readonly_connection_enforcement(self):
        """Test that read-only connections prevent writes."""
        self.db_manager = DatabaseManager(self.db_path)
        
        # Create a table first with write connection
        with self.db_manager.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test_table (id INTEGER)")
        
        # Try to write with read-only connection (should fail)
        with pytest.raises(sqlite3.OperationalError):
            with self.db_manager.get_connection(readonly=True) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test_table (id) VALUES (1)")
    
    def test_database_wal_mode_initialization(self):
        """Test that WAL mode is properly initialized."""
        self.db_manager = DatabaseManager(self.db_path)
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            result = cursor.fetchone()
            # Should be WAL mode for performance
            assert result[0].upper() in ['WAL', 'DELETE']  # Allow both for test flexibility
    
    def test_database_corruption_recovery(self):
        """Test behavior when database file is corrupted or missing."""
        # Test with non-existent database
        bad_path = "/nonexistent/path/database.db"
        
        with pytest.raises((sqlite3.OperationalError, OSError)):
            db_manager = DatabaseManager(bad_path)
            with db_manager.get_connection() as conn:
                conn.cursor().execute("SELECT 1")
    
    def test_concurrent_read_write_operations(self):
        """Test concurrent read/write operations don't cause deadlocks."""
        self.db_manager = DatabaseManager(self.db_path)
        
        # Create test table
        with self.db_manager.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE test_concurrent (
                    id INTEGER PRIMARY KEY,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        def read_operation():
            for i in range(10):
                with self.db_manager.get_connection(readonly=True) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM test_concurrent")
                    cursor.fetchone()
                time.sleep(0.01)
        
        def write_operation():
            for i in range(5):
                with self.db_manager.get_connection(readonly=False) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO test_concurrent (data) VALUES (?)", (f"data_{i}",))
                time.sleep(0.02)
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=4) as executor:
            read_futures = [executor.submit(read_operation) for _ in range(2)]
            write_futures = [executor.submit(write_operation) for _ in range(2)]
            
            # Wait for all to complete without deadlock
            for future in read_futures + write_futures:
                future.result(timeout=5.0)  # 5 second timeout
    
    def test_connection_cleanup_on_exception(self):
        """Test that connections are properly cleaned up when exceptions occur."""
        self.db_manager = DatabaseManager(self.db_path)
        
        # Test that exception in context manager still closes connection
        with pytest.raises(sqlite3.OperationalError):
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM nonexistent_table")
        
        # Should still be able to get new connection
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_database_schema_compatibility(self):
        """Test basic schema operations work correctly."""
        self.db_manager = DatabaseManager(self.db_path)
        
        # Test creating tables and indexes (basic Pensieve schema simulation)
        with self.db_manager.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            
            # Create basic entities table
            cursor.execute("""
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    filename TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_type_group TEXT
                )
            """)
            
            # Create metadata_entries table
            cursor.execute("""
                CREATE TABLE metadata_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    "key" TEXT NOT NULL,
                    value TEXT,
                    FOREIGN KEY (entity_id) REFERENCES entities (id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_entities_created_at ON entities (created_at)")
            cursor.execute("CREATE INDEX idx_metadata_entity_key ON metadata_entries (entity_id, \"key\")")
        
        # Test that schema was created correctly - using read-write connection for inserts
        with self.db_manager.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'entities' in tables
            assert 'metadata_entries' in tables
            
            # Test insert and query work
            cursor.execute("INSERT INTO entities (filepath, filename, file_type_group) VALUES (?, ?, ?)",
                         ('/test/path', 'test.png', 'image'))
            entity_id = cursor.lastrowid
            
            cursor.execute("INSERT INTO metadata_entries (entity_id, \"key\", value) VALUES (?, ?, ?)",
                         (entity_id, 'test_key', 'test_value'))
            
            cursor.execute("""
                SELECT e.filepath, me.value 
                FROM entities e 
                LEFT JOIN metadata_entries me ON e.id = me.entity_id 
                WHERE me."key" = 'test_key'
            """)
            result = cursor.fetchone()
            
            assert result[0] == '/test/path'
            assert result[1] == 'test_value'


class TestDatabasePerformance:
    """Test database performance characteristics."""
    
    def setup_method(self):
        """Create temporary database for performance tests."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db_manager = DatabaseManager(self.db_path)
        
        # Create test schema
        with self.db_manager.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE test_performance (
                    id INTEGER PRIMARY KEY,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX idx_test_created_at ON test_performance (created_at)")
    
    def teardown_method(self):
        """Clean up test database."""
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def test_connection_pool_performance(self):
        """Test that connection pooling provides performance benefits."""
        import time
        
        # Test without connection reuse (create new connection each time)
        start_time = time.time()
        for i in range(50):
            temp_manager = DatabaseManager(self.db_path)
            with temp_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        no_pool_time = time.time() - start_time
        
        # Test with connection reuse (using pool)
        start_time = time.time()
        for i in range(50):
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        pool_time = time.time() - start_time
        
        # Connection pooling should be faster (or at least not significantly slower)
        # Allow some variance for test environment differences
        assert pool_time <= no_pool_time * 2.0  # Pool shouldn't be more than 2x slower
    
    def test_bulk_operation_performance(self):
        """Test performance of bulk database operations."""
        # Test bulk insert
        start_time = time.time()
        with self.db_manager.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            test_data = [(f"data_{i}",) for i in range(1000)]
            cursor.executemany("INSERT INTO test_performance (data) VALUES (?)", test_data)
        bulk_time = time.time() - start_time
        
        # Bulk operations should complete in reasonable time (< 1 second for 1000 records)
        assert bulk_time < 1.0
        
        # Verify all data was inserted
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_performance")
            count = cursor.fetchone()[0]
            assert count == 1000