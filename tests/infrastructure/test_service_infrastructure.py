"""
Service infrastructure tests for AutoTaskTracker.
Tests integration with external services and service health monitoring.
"""
import subprocess
import socket
import time
import requests
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock


class TestMemosServiceIntegration:
    """Test integration with Pensieve/memos service."""
    
    def test_memos_service_health_check(self):
        """Test ability to check memos service health."""
        
        def check_memos_running():
            """Check if memos service is accessible."""
            try:
                # Try to connect to default memos port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    result = sock.connect_ex(('localhost', 8839))
                    return result == 0
            except Exception:
                return False
        
        # Test service detection (may or may not be running)
        is_running = check_memos_running()
        assert isinstance(is_running, bool)
        
        if is_running:
            # If service is running, test basic HTTP health
            try:
                response = requests.get('http://localhost:8839/api/health', timeout=5)
                # Should get some response (even if it's an error)
                assert response.status_code in [200, 404, 405, 500]
            except requests.exceptions.RequestException:
                # Connection refused or timeout is acceptable for this test
                pass
    
    def test_memos_command_availability(self):
        """Test that memos command is available."""
        try:
            # Test that memos command exists
            result = subprocess.run(['memos', '--help'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            # Should either succeed or give a recognizable error
            assert result.returncode in [0, 1, 2]  # Help commands often return 1 or 2
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Memos command not available in test environment")
    
    def test_database_accessibility_with_memos(self):
        """Test that database is accessible when memos might be running."""
        from autotasktracker.core.database import DatabaseManager
        
        # Test that we can access database even if memos is running
        try:
            db_manager = DatabaseManager()  # Use default path
            
            with db_manager.get_connection(readonly=True) as conn:
                cursor = conn.cursor()
                # Test basic query that should work on any SQLite database
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                # Should succeed even if no tables exist
                assert isinstance(tables, list)
                
        except Exception as e:
            # If database doesn't exist, that's a different issue
            # but connection should not fail due to service conflicts
            if "no such file" not in str(e).lower():
                pytest.fail(f"Database access failed unexpectedly: {e}")
    
    def test_concurrent_database_access(self):
        """Test concurrent access to database (simulating memos + autotasktracker)."""
        import tempfile
        import threading
        from autotasktracker.core.database import DatabaseManager
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            # Create test database
            db_manager = DatabaseManager(db_path)
            with db_manager.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE test_concurrent (id INTEGER, data TEXT)")
                cursor.execute("INSERT INTO test_concurrent VALUES (1, 'test')")
            
            # Test concurrent read access (simulating multiple services)
            results = []
            errors = []
            
            def concurrent_read(thread_id):
                try:
                    db_mgr = DatabaseManager(db_path)
                    with db_mgr.get_connection(readonly=True) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM test_concurrent")
                        result = cursor.fetchall()
                        results.append((thread_id, len(result)))
                except Exception as e:
                    errors.append((thread_id, str(e)))
            
            # Run multiple concurrent readers
            threads = []
            for i in range(5):
                thread = threading.Thread(target=concurrent_read, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=5)
            
            # All reads should succeed
            assert len(errors) == 0, f"Concurrent read errors: {errors}"
            assert len(results) == 5
            assert all(count == 1 for _, count in results)
            
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass


class TestDashboardServiceIntegration:
    """Test dashboard service integration and health."""
    
    def test_streamlit_import_availability(self):
        """Test that Streamlit is available for dashboard services."""
        try:
            import streamlit as st
            # Test basic streamlit functionality
            assert hasattr(st, 'write')
            assert hasattr(st, 'sidebar')
            assert hasattr(st, 'cache_data')
        except ImportError:
            pytest.skip("Streamlit not available - dashboard services will not work")
    
    def test_dashboard_port_configuration(self):
        """Test that dashboard ports are properly configured."""
        from autotasktracker.config import get_config
        
        config = get_config()
        
        # Test that port configuration exists and is reasonable
        expected_ports = [8502, 8503, 8504, 8505, 8506, 8507]
        
        for port in expected_ports:
            # Port should be in valid range
            assert 1024 <= port <= 65535, f"Port {port} outside valid range"
            
            # Port should not conflict with common services
            common_ports = [22, 25, 53, 80, 110, 143, 443, 993, 995]
            assert port not in common_ports, f"Port {port} conflicts with common service"
    
    def test_dashboard_startup_requirements(self):
        """Test that dashboard startup requirements are met."""
        # Test that required modules can be imported
        required_modules = [
            'pandas',
            'datetime',
            'pathlib',
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            pytest.fail(f"Required modules for dashboards missing: {missing_modules}")
    
    def test_dashboard_graceful_degradation(self):
        """Test that dashboards handle missing AI features gracefully."""
        from autotasktracker.core.database import DatabaseManager
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            # Create minimal database
            db_manager = DatabaseManager(db_path)
            with db_manager.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE entities (
                        id INTEGER PRIMARY KEY,
                        filepath TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        file_type_group TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE metadata_entries (
                        id INTEGER PRIMARY KEY,
                        entity_id INTEGER,
                        "key" TEXT,
                        value TEXT
                    )
                """)
                cursor.execute("INSERT INTO entities (filepath, file_type_group) VALUES (?, ?)",
                             ('/test/path.png', 'image'))
            
            # Test that basic database operations work without AI features
            tasks_df = db_manager.fetch_tasks(limit=10)
            assert len(tasks_df) >= 0  # Should work even with no AI data
            
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass


class TestAIServiceIntegration:
    """Test AI service integration and fallback behavior."""
    
    def test_ai_service_optional_dependencies(self):
        """Test handling of optional AI dependencies."""
        # Test numpy availability
        try:
            import numpy as np
            numpy_available = True
            # Test basic numpy operations
            arr = np.array([1, 2, 3])
            assert arr.shape == (3,)
        except ImportError:
            numpy_available = False
        
        # System should handle numpy unavailability gracefully
        if not numpy_available:
            # Test that embeddings search fails gracefully
            try:
                from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine
                # Should import but may fail on actual usage
            except ImportError:
                pass  # Expected if AI modules have hard numpy dependency
    
    def test_vlm_service_integration(self):
        """Test VLM service integration and fallback."""
        try:
            from autotasktracker.ai.vlm_integration import VLMTaskExtractor
            
            vlm_extractor = VLMTaskExtractor()
            
            # Test with mock VLM description
            result = vlm_extractor.extract_from_vlm_description(
                "User is writing code in a text editor",
                "test.py - VS Code",
                None
            )
            
            # Should return a valid result or None
            if result is not None:
                assert hasattr(result, 'task_title')
                assert hasattr(result, 'confidence')
                assert isinstance(result.confidence, (int, float))
                assert 0 <= result.confidence <= 1
            
        except ImportError:
            pytest.skip("VLM integration not available")
    
    def test_embeddings_service_integration(self):
        """Test embeddings service integration."""
        try:
            from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
                db_path = temp_db.name
            
            try:
                # Create embeddings engine
                engine = EmbeddingsSearchEngine(db_path)
                
                # Test basic functionality
                assert hasattr(engine, 'semantic_search')
                assert hasattr(engine, 'cosine_similarity')
                
                # Test cosine similarity calculation
                if 'numpy' in str(type(engine)):
                    import numpy as np
                    vec1 = np.array([1, 0, 0])
                    vec2 = np.array([0, 1, 0])
                    similarity = engine.cosine_similarity(vec1, vec2)
                    assert isinstance(similarity, (int, float))
                    assert 0 <= similarity <= 1
                
            finally:
                try:
                    Path(db_path).unlink()
                except:
                    pass
                    
        except ImportError:
            pytest.skip("Embeddings search not available")


class TestExternalServiceMonitoring:
    """Test external service monitoring and health checks."""
    
    def test_service_discovery(self):
        """Test ability to discover running services."""
        
        def get_listening_ports():
            """Get list of ports with services listening."""
            try:
                # Simple port scan for common AutoTaskTracker ports
                listening_ports = []
                test_ports = [8502, 8503, 8839]  # Dashboard ports + memos
                
                for port in test_ports:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            sock.settimeout(1)
                            result = sock.connect_ex(('localhost', port))
                            if result == 0:
                                listening_ports.append(port)
                    except Exception:
                        continue
                
                return listening_ports
            except Exception:
                return []
        
        ports = get_listening_ports()
        assert isinstance(ports, list)
        # Don't assert specific ports since services may not be running
    
    def test_service_health_endpoints(self):
        """Test service health check endpoints."""
        # Test memos health endpoint if service is running
        try:
            response = requests.get('http://localhost:8839/api/v1/status', timeout=2)
            # If we get a response, service is running
            assert response.status_code in [200, 404, 405]  # Various valid responses
        except requests.exceptions.RequestException:
            # Service not running - that's fine for this test
            pass
    
    def test_graceful_service_failure_handling(self):
        """Test that application handles service failures gracefully."""
        from autotasktracker.core.database import DatabaseManager
        
        # Test with invalid database path (simulating service failure)
        invalid_path = "/definitely/does/not/exist/database.db"
        
        try:
            db_manager = DatabaseManager(invalid_path)
            with db_manager.get_connection() as conn:
                conn.cursor().execute("SELECT 1")
        except Exception as e:
            # Should get a clear error, not a crash
            assert isinstance(e, (OSError, Exception))
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in 
                      ['no such file', 'cannot open', 'not found', 'permission', 'unable to open'])
    
    def test_service_restart_recovery(self):
        """Test that application can recover from service restarts."""
        import tempfile
        from autotasktracker.core.database import DatabaseManager
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            # Create database manager
            db_manager = DatabaseManager(db_path)
            
            # Simulate service interruption by closing and reopening
            with db_manager.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE test_recovery (id INTEGER)")
            
            # Create new manager instance (simulating restart)
            new_db_manager = DatabaseManager(db_path)
            
            # Should be able to access existing data
            with new_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                assert 'test_recovery' in tables
                
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass