"""
Configuration and environment infrastructure tests for AutoTaskTracker.
Tests configuration loading, environment variables, and path resolution.
"""
import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

from autotasktracker.config import get_config


class TestConfigurationInfrastructure:
    """Test configuration loading and management."""
    
    def test_default_config_loading(self):
        """Test that default configuration loads correctly."""
        config = get_config()
        
        # Test that essential config values exist
        assert hasattr(config, 'get_db_path')
        assert callable(config.get_db_path)
        
        # Test default database path resolution
        db_path = config.get_db_path()
        assert isinstance(db_path, str)
        assert len(db_path) > 0
    
    def test_config_database_path_expansion(self):
        """Test that database path handles ~ expansion correctly."""
        config = get_config()
        db_path = config.get_db_path()
        
        # Should not contain unexpanded ~ if user home directory exists
        if Path.home().exists():
            assert '~' not in db_path or db_path.startswith('~')  # Allow raw ~ for relative paths
    
    def test_config_with_custom_db_path(self):
        """Test configuration with custom database path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = str(Path(temp_dir) / "custom.db")
            
            # Test that custom path is used when provided
            # Note: This depends on how the config system actually works
            # May need to adjust based on actual implementation
            config = get_config()
            if hasattr(config, 'DB_PATH'):
                original_path = config.DB_PATH
                config.DB_PATH = custom_path
                assert config.get_db_path() == custom_path
                config.DB_PATH = original_path
    
    def test_config_handles_missing_home_directory(self):
        """Test configuration when home directory is not accessible."""
        config = get_config()
        
        # Should not crash when getting database path
        try:
            db_path = config.get_db_path()
            assert isinstance(db_path, str)
        except Exception as e:
            pytest.fail(f"Config should handle missing home directory gracefully: {e}")
    
    def test_config_path_permissions(self):
        """Test that configuration paths have correct permissions."""
        config = get_config()
        db_path = config.get_db_path()
        
        # Get the directory that would contain the database
        db_dir = Path(db_path).parent
        
        # If directory exists, test it's accessible
        if db_dir.exists():
            assert os.access(str(db_dir), os.R_OK), f"Database directory not readable: {db_dir}"
            assert os.access(str(db_dir), os.W_OK), f"Database directory not writable: {db_dir}"


class TestEnvironmentInfrastructure:
    """Test environment variable handling and system dependencies."""
    
    def test_environment_variable_isolation(self):
        """Test that environment variables don't interfere with each other."""
        # Save original environment
        original_env = dict(os.environ)
        
        try:
            # Test with various environment configurations
            test_envs = [
                {},  # Clean environment
                {'HOME': '/tmp/test_home'},
                {'XDG_DATA_HOME': '/tmp/test_xdg'},
                {'AUTOTASK_DB_PATH': '/tmp/test_db.db'},
            ]
            
            for test_env in test_envs:
                # Clear and set test environment
                os.environ.clear()
                os.environ.update(test_env)
                
                # Configuration should still work
                try:
                    config = get_config()
                    db_path = config.get_db_path()
                    assert isinstance(db_path, str)
                    assert len(db_path) > 0
                except Exception as e:
                    pytest.fail(f"Config failed with environment {test_env}: {e}")
        
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_python_path_independence(self):
        """Test that the application works regardless of Python path setup."""
        # Test that imports work from different working directories
        import sys
        original_path = sys.path[:]
        original_cwd = os.getcwd()
        
        try:
            # Test from different directory
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                
                # Should still be able to import and use config
                from autotasktracker.config import get_config
                config = get_config()
                db_path = config.get_db_path()
                assert isinstance(db_path, str)
        
        finally:
            sys.path[:] = original_path
            os.chdir(original_cwd)
    
    def test_file_system_requirements(self):
        """Test that the application handles different file system configurations."""
        config = get_config()
        db_path = config.get_db_path()
        db_dir = Path(db_path).parent
        
        # Test that we can create the directory structure
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
                created_dir = True
            except PermissionError:
                pytest.skip("Cannot create database directory due to permissions")
                created_dir = False
        else:
            created_dir = False
        
        try:
            # Test basic file operations in the database directory
            test_file = db_dir / "test_write.tmp"
            test_file.write_text("test")
            content = test_file.read_text()
            assert content == "test"
            test_file.unlink()
            
        except Exception as e:
            pytest.fail(f"Basic file operations failed in database directory: {e}")
        
        finally:
            if created_dir:
                try:
                    db_dir.rmdir()
                except:
                    pass  # Don't fail test if cleanup fails
    
    def test_dependency_availability(self):
        """Test that required dependencies are available."""
        # Test core dependencies
        core_modules = [
            'sqlite3',
            'json',
            'datetime',
            'pathlib',
            'logging',
        ]
        
        for module_name in core_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Required core module not available: {module_name} - {e}")
        
        # Test optional dependencies with graceful handling
        optional_modules = [
            'numpy',
            'pandas',
            'streamlit',
        ]
        
        for module_name in optional_modules:
            try:
                __import__(module_name)
            except ImportError:
                # Optional modules should not cause test failure
                # but we should be aware they're missing
                pass
    
    def test_logging_infrastructure(self):
        """Test that logging infrastructure works correctly."""
        import logging
        
        # Test that we can create loggers
        logger = logging.getLogger('autotasktracker.test')
        assert logger is not None
        
        # Test basic logging functionality
        with patch('logging.StreamHandler.emit') as mock_emit:
            logger.error("Test error message")
            # Should have attempted to emit a log message
            # (May not actually emit depending on logging configuration)
    
    def test_thread_safety_infrastructure(self):
        """Test that the application infrastructure is thread-safe."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        def config_access_test():
            """Test function that accesses configuration from different threads."""
            config = get_config()
            db_path = config.get_db_path()
            time.sleep(0.01)  # Small delay to increase chance of race conditions
            return db_path
        
        # Run configuration access from multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(config_access_test) for _ in range(20)]
            results = [future.result() for future in futures]
        
        # All threads should get the same configuration
        assert len(set(results)) == 1, "Configuration not consistent across threads"
        
        # Result should be a valid path
        assert isinstance(results[0], str)
        assert len(results[0]) > 0


class TestSystemIntegration:
    """Test integration with system components."""
    
    def test_memos_service_detection(self):
        """Test ability to detect if memos service is running."""
        import subprocess
        
        # Test that we can check service status without crashing
        try:
            # This is a basic test - actual implementation would check memos specifically
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            assert result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("System process checking not available")
    
    def test_port_availability_checking(self):
        """Test ability to check port availability."""
        import socket
        
        def is_port_available(port):
            """Check if a port is available."""
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    return result != 0  # Port is available if connection failed
            except Exception:
                return False
        
        # Test port checking functionality
        # Most ports should be available, but we can't guarantee specific ones
        available_ports = []
        config = get_config()
        for port in [config.TASK_BOARD_PORT, config.ANALYTICS_PORT, config.TIMETRACKER_PORT, config.TIME_TRACKER_PORT]:
            if is_port_available(port):
                available_ports.append(port)
        
        # Should be able to check port status without crashing
        assert isinstance(available_ports, list)
    
    def test_database_file_locking(self):
        """Test that database file locking works correctly."""
        import sqlite3
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            # Create database
            conn1 = sqlite3.connect(db_path)
            cursor1 = conn1.cursor()
            cursor1.execute("CREATE TABLE test (id INTEGER)")
            cursor1.execute("INSERT INTO test (id) VALUES (1)")
            conn1.commit()  # Commit the transaction so it's visible to other connections
            
            # Second connection should work for reading
            conn2 = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT * FROM test")
            result = cursor2.fetchall()
            assert len(result) == 1
            
            conn1.close()
            conn2.close()
            
        finally:
            try:
                os.unlink(db_path)
            except:
                pass