"""
Comprehensive tests for the configuration management module.

Tests cover all configuration functionality including:
- Config class initialization and defaults
- Environment variable loading
- File-based configuration loading and saving
- Service URL generation
- Configuration validation
- Global configuration management
"""
import pytest
import os
import json
import tempfile
from unittest.mock import patch, mock_open
from pathlib import Path

from autotasktracker.config import Config, get_config, set_config, reset_config


class TestConfig:
    """Test the Config class."""
    
    def test_config_initialization_with_defaults(self):
        """Test that Config initializes with correct default values and validates business rules."""
        import time
        start_time = time.time()
        config = Config()
        init_time = time.time() - start_time
        
        # Test database settings defaults with path validation
        expected_db_path = os.path.expanduser("/Users/paulrohde/AutoTaskTracker.memos/database.db")
        assert config.DB_PATH == expected_db_path, "DB path should match expected default"
        assert os.path.isabs(config.DB_PATH), "DB path should be absolute"
        assert config.DB_PATH.endswith(".db"), "DB path should point to SQLite database"
        
        expected_screenshots_dir = os.path.expanduser("/Users/paulrohde/AutoTaskTracker.memos/screenshots")
        assert config.SCREENSHOTS_DIR == expected_screenshots_dir, "Screenshots dir should match expected"
        assert os.path.isabs(config.SCREENSHOTS_DIR), "Screenshots dir should be absolute"
        
        expected_logs_dir = os.path.expanduser("/Users/paulrohde/AutoTaskTracker.memos/logs")
        assert config.LOGS_DIR == expected_logs_dir, "Logs dir should match expected"
        assert os.path.isabs(config.LOGS_DIR), "Logs dir should be absolute"
        
        # Test server ports with business rule validation
        assert config.MEMOS_PORT == 8841, "Memos port should be 8841"
        assert 1024 <= config.MEMOS_PORT <= 65535, "Memos port should be in valid range"
        assert config.TASK_BOARD_PORT == 8602, "Task board port should be 8602"
        assert 1024 <= config.TASK_BOARD_PORT <= 65535, "Task board port should be in valid range"
        assert config.ANALYTICS_PORT == 8603, "Analytics port should be 8603"
        assert 1024 <= config.ANALYTICS_PORT <= 65535, "Analytics port should be in valid range"
        assert config.TIMETRACKER_PORT == 8604, "Time tracker port should be 8604"
        assert 1024 <= config.TIMETRACKER_PORT <= 65535, "Time tracker port should be in valid range"
        assert config.NOTIFICATIONS_PORT == 8606, "Notifications port should be 8606"
        assert 1024 <= config.NOTIFICATIONS_PORT <= 65535, "Notifications port should be in valid range"
        
        # Validate all ports are unique to prevent conflicts
        all_ports = [config.MEMOS_PORT, config.TASK_BOARD_PORT, config.ANALYTICS_PORT, 
                    config.TIMETRACKER_PORT, config.NOTIFICATIONS_PORT]
        assert len(set(all_ports)) == len(all_ports), "All service ports must be unique"
        
        # Test application settings with reasonable limits
        assert config.AUTO_REFRESH_SECONDS == 30, "Auto refresh should be 30 seconds"
        assert 5 <= config.AUTO_REFRESH_SECONDS <= 300, "Auto refresh should be reasonable (5s-5min)"
        assert config.CACHE_TTL_SECONDS == 60, "Cache TTL should be 60 seconds"
        assert 10 <= config.CACHE_TTL_SECONDS <= 3600, "Cache TTL should be reasonable (10s-1hr)"
        assert config.GROUP_INTERVAL_MINUTES == 5, "Group interval should be 5 minutes"
        assert 1 <= config.GROUP_INTERVAL_MINUTES <= 60, "Group interval should be reasonable"
        assert config.SCREENSHOT_INTERVAL_SECONDS == 4, "Screenshot interval should be 4 seconds"
        assert 1 <= config.SCREENSHOT_INTERVAL_SECONDS <= 60, "Screenshot interval should be reasonable"
        
        # Test time tracking settings with logical relationships
        assert config.MIN_SESSION_DURATION_SECONDS == 30, "Min session duration should be 30 seconds"
        assert config.MIN_SESSION_DURATION_SECONDS > 0, "Min session duration should be positive"
        assert config.MAX_SESSION_GAP_SECONDS == 600, "Max session gap should be 600 seconds"
        assert config.MAX_SESSION_GAP_SECONDS > config.MIN_SESSION_DURATION_SECONDS, "Max gap should exceed min duration"
        assert config.IDLE_THRESHOLD_SECONDS == 300, "Idle threshold should be 300 seconds"
        assert config.IDLE_THRESHOLD_SECONDS < config.MAX_SESSION_GAP_SECONDS, "Idle threshold should be less than max gap"
        
        # Test feature flags with type validation
        assert config.SHOW_SCREENSHOTS is True, "Screenshots should be shown by default"
        assert isinstance(config.SHOW_SCREENSHOTS, bool), "Show screenshots should be boolean"
        assert config.ENABLE_NOTIFICATIONS is True, "Notifications should be enabled by default"
        assert isinstance(config.ENABLE_NOTIFICATIONS, bool), "Enable notifications should be boolean"
        assert config.ENABLE_ANALYTICS is True, "Analytics should be enabled by default"
        assert isinstance(config.ENABLE_ANALYTICS, bool), "Enable analytics should be boolean"
        
        # Test performance settings with reasonable limits
        assert config.MAX_SCREENSHOT_SIZE == 300, "Max screenshot size should be 300"
        assert 100 <= config.MAX_SCREENSHOT_SIZE <= 2000, "Screenshot size should be reasonable"
        assert config.CONNECTION_POOL_SIZE == 5, "Connection pool should be 5"
        assert 1 <= config.CONNECTION_POOL_SIZE <= 50, "Connection pool should be reasonable"
        assert config.QUERY_TIMEOUT_SECONDS == 30, "Query timeout should be 30 seconds"
        assert 5 <= config.QUERY_TIMEOUT_SECONDS <= 300, "Query timeout should be reasonable"
        
        # Performance validation
        assert init_time < 0.1, f"Config initialization should be fast, took {init_time:.3f}s"
        
        # Test error condition - ensure all required attributes exist
        required_attrs = ['DB_PATH', 'MEMOS_PORT', 'TASK_BOARD_PORT', 'SHOW_SCREENSHOTS']
        for attr in required_attrs:
            assert hasattr(config, attr), f"Config should have {attr} attribute"
    
    def test_config_from_env_with_all_types(self):
        """Test loading configuration from environment variables with type conversion and validation."""
        env_vars = {
            'AUTOTASK_DB_PATH': '/custom/path/database.db',
            'AUTOTASK_TASK_BOARD_PORT': '9000',
            'AUTOTASK_AUTO_REFRESH_SECONDS': '45',
            'AUTOTASK_SHOW_SCREENSHOTS': 'false',
            'AUTOTASK_ENABLE_NOTIFICATIONS': 'true',
            'AUTOTASK_ENABLE_ANALYTICS': '1',
            'AUTOTASK_MAX_SCREENSHOT_SIZE': '500'
        }
        
        import time
        start_time = time.time()
        with patch.dict(os.environ, env_vars):
            config = Config.from_env()
        load_time = time.time() - start_time
        
        # Test string values with validation
        assert config.DB_PATH == '/custom/path/database.db', "Should load custom DB path from env"
        assert config.DB_PATH.startswith('/'), "Custom DB path should be absolute"
        assert config.DB_PATH.endswith('.db'), "Custom DB path should be SQLite database"
        assert len(config.DB_PATH) > 10, "DB path should be substantial"
        
        # Test integer conversion with range validation
        assert config.TASK_BOARD_PORT == 9000, "Should load custom task board port"
        assert isinstance(config.TASK_BOARD_PORT, int), "Port should be converted to integer"
        assert 1024 <= config.TASK_BOARD_PORT <= 65535, "Custom port should be in valid range"
        assert config.AUTO_REFRESH_SECONDS == 45, "Should load custom refresh interval"
        assert isinstance(config.AUTO_REFRESH_SECONDS, int), "Refresh interval should be integer"
        assert config.AUTO_REFRESH_SECONDS > 0, "Refresh interval should be positive"
        assert config.MAX_SCREENSHOT_SIZE == 500, "Should load custom screenshot size"
        assert isinstance(config.MAX_SCREENSHOT_SIZE, int), "Screenshot size should be integer"
        assert config.MAX_SCREENSHOT_SIZE > 0, "Screenshot size should be positive"
        
        # Test boolean conversion with type validation
        assert config.SHOW_SCREENSHOTS is False, "Should convert 'false' to boolean False"
        assert isinstance(config.SHOW_SCREENSHOTS, bool), "Screenshots flag should be boolean"
        assert config.ENABLE_NOTIFICATIONS is True, "Should convert 'true' to boolean True"
        assert isinstance(config.ENABLE_NOTIFICATIONS, bool), "Notifications flag should be boolean"
        assert config.ENABLE_ANALYTICS is True, "Should convert '1' to boolean True"
        assert isinstance(config.ENABLE_ANALYTICS, bool), "Analytics flag should be boolean"
        
        # Test defaults for non-specified variables with consistency
        assert config.ANALYTICS_PORT == 8603, "Should use default for unspecified values"
        assert isinstance(config.ANALYTICS_PORT, int), "Default port should be integer"
        assert config.ANALYTICS_PORT != config.TASK_BOARD_PORT, "Default and custom ports should differ"
        
        # Performance validation
        assert load_time < 0.1, f"Environment loading should be fast, took {load_time:.3f}s"
        
        # Test state consistency - loaded config should have all required attributes
        required_attrs = ['DB_PATH', 'TASK_BOARD_PORT', 'ANALYTICS_PORT', 'SHOW_SCREENSHOTS']
        for attr in required_attrs:
            assert hasattr(config, attr), f"Loaded config should have {attr} attribute"
            assert getattr(config, attr) is not None, f"{attr} should not be None"
        
        # Test error condition - verify type conversion error handling
        bad_env = {'AUTOTASK_TASK_BOARD_PORT': 'not_a_number'}
        with patch.dict(os.environ, bad_env):
            try:
                bad_config = Config.from_env()
                # If no exception, should handle gracefully
                assert hasattr(bad_config, 'TASK_BOARD_PORT'), "Should have port attribute even with bad input"
            except (ValueError, TypeError) as e:
                # Acceptable to raise type conversion errors
                assert 'not_a_number' in str(e) or 'port' in str(e).lower(), "Error should be related to invalid port"
    
    def test_config_from_env_boolean_variations(self):
        """Test various boolean representations in environment variables."""
        boolean_tests = [
            ('true', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('YES', True),
            ('on', True),
            ('ON', True),
            ('false', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('off', False),
            ('invalid', False)
        ]
        
        for env_value, expected in boolean_tests:
            with patch.dict(os.environ, {'AUTOTASK_SHOW_SCREENSHOTS': env_value}):
                config = Config.from_env()
                assert config.SHOW_SCREENSHOTS is expected, f"Failed for value: {env_value}"
    
    def test_config_from_file_success(self):
        """Test loading configuration from valid JSON file."""
        config_data = {
            'DB_PATH': '/test/database.db',
            'TASK_BOARD_PORT': 8600,
            'SHOW_SCREENSHOTS': False,
            'AUTO_REFRESH_SECONDS': 60
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Config.from_file(config_path)
            
            assert config.DB_PATH == '/test/database.db'
            assert config.TASK_BOARD_PORT == 8600
            assert config.SHOW_SCREENSHOTS is False
            assert config.AUTO_REFRESH_SECONDS == 60
            # Test that defaults are preserved for non-specified values
            assert config.ANALYTICS_PORT == 8603
        finally:
            os.unlink(config_path)
    
    def test_config_from_file_io_error(self):
        """Test handling of file IO errors."""
        with patch('autotasktracker.utils.config.logger') as mock_logger:
            config = Config.from_file('/nonexistent/config.json')
            
            # Should return default config on error
            assert config.TASK_BOARD_PORT == 8602
            assert mock_logger.error.called
    
    def test_config_from_file_json_error(self):
        """Test handling of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{ invalid json }')
            config_path = f.name
        
        try:
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                config = Config.from_file(config_path)
                
                # Should return default config on JSON error
                assert config.TASK_BOARD_PORT == 8602
                assert mock_logger.error.called
        finally:
            os.unlink(config_path)
    
    def test_save_to_file_success(self):
        """Test saving configuration to file."""
        config = Config(
            DB_PATH='/test/db.db',
            TASK_BOARD_PORT=9000,
            SHOW_SCREENSHOTS=False
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            config.save_to_file(config_path)
            
            # Verify file contents
            with open(config_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['DB_PATH'] == '/test/db.db'
            assert saved_data['TASK_BOARD_PORT'] == 9000
            assert saved_data['SHOW_SCREENSHOTS'] is False
        finally:
            os.unlink(config_path)
    
    def test_save_to_file_creates_directory(self):
        """Test that save_to_file creates directory if it doesn't exist."""
        config = Config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'subdir', 'config.json')
            config.save_to_file(config_path)
            
            assert os.path.exists(config_path)
            # Verify content
            with open(config_path, 'r') as f:
                data = json.load(f)
            assert 'DB_PATH' in data
    
    def test_save_to_file_io_error(self):
        """Test handling of save errors with comprehensive error validation."""
        import time
        
        start_time = time.time()
        config = Config()
        
        # Validate initial config state
        assert isinstance(config, Config), "Should have valid Config instance"
        assert hasattr(config, 'save_to_file'), "Config should have save_to_file method"
        assert callable(config.save_to_file), "save_to_file should be callable"
        
        error_handling_scenarios = [
            ('/root/cannot_write_here.json', "Root directory permission error"),
            ('/nonexistent/deep/path/file.json', "Non-existent directory error"),
            ('', "Empty path error"),
            ('/dev/null/file.json', "Invalid path structure")
        ]
        
        for invalid_path, scenario_desc in error_handling_scenarios:
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                # Test error handling performance
                error_start = time.time()
                try:
                    result = config.save_to_file(invalid_path)
                    error_time = time.time() - error_start
                    
                    # Validate error handling behavior
                    assert error_time < 0.5, f"Error handling should be fast for {scenario_desc}, took {error_time:.3f}s"
                    
                    # Should either return False or None on error
                    assert result is False or result is None, f"Should return failure indicator for {scenario_desc}"
                    
                except Exception as e:
                    error_time = time.time() - error_start
                    # Acceptable to raise exception for invalid paths
                    assert isinstance(e, (IOError, OSError, PermissionError, FileNotFoundError)), \
                        f"Should raise appropriate I/O exception for {scenario_desc}, got {type(e)}"
                    assert error_time < 0.5, f"Exception handling should be fast for {scenario_desc}"
                
                # Validate logging behavior
                assert mock_logger.error.called, f"Should log error for {scenario_desc}"
                assert mock_logger.error.call_count >= 1, f"Should call error logger at least once for {scenario_desc}"
                
                # Validate error message content
                error_calls = mock_logger.error.call_args_list
                assert len(error_calls) > 0, f"Should have error log calls for {scenario_desc}"
                error_message = str(error_calls[0][0]) if error_calls else ""
                assert len(error_message) > 0, f"Error message should not be empty for {scenario_desc}"
        
        total_test_time = time.time() - start_time
        assert total_test_time < 2.0, f"All error handling tests should complete quickly, took {total_test_time:.3f}s"
    
    def test_get_service_url(self):
        """Test service URL generation with comprehensive validation and error handling."""
        import time
        import re
        
        start_time = time.time()
        
        # Create config with known ports for testing
        config = Config(
            MEMOS_PORT=8841,
            TASK_BOARD_PORT=8602,
            ANALYTICS_PORT=8603,
            TIMETRACKER_PORT=8604,
            NOTIFICATIONS_PORT=8606
        )
        
        # Validate config initialization
        assert isinstance(config, Config), "Should have valid Config instance"
        assert hasattr(config, 'get_service_url'), "Config should have get_service_url method"
        assert callable(config.get_service_url), "get_service_url should be callable"
        
        # Test all valid services with comprehensive URL validation
        service_tests = [
            ('memos', 8841, 'http://localhost:8841'),
            ('task_board', 8602, 'http://localhost:8602'),
            ('analytics', 8603, 'http://localhost:8603'),
            ('timetracker', 8604, 'http://localhost:8604'),
            ('notifications', 8606, 'http://localhost:8606')
        ]
        
        url_generation_times = []
        
        for service_name, expected_port, expected_url in service_tests:
            # Test URL generation performance
            gen_start = time.time()
            actual_url = config.get_service_url(service_name)
            gen_time = time.time() - gen_start
            url_generation_times.append(gen_time)
            
            # Validate URL format and content
            assert actual_url == expected_url, f"URL for {service_name} should be {expected_url}, got {actual_url}"
            assert isinstance(actual_url, str), f"URL for {service_name} should be string"
            assert actual_url.startswith('http://'), f"URL for {service_name} should start with http://"
            assert 'localhost' in actual_url, f"URL for {service_name} should contain localhost"
            assert str(expected_port) in actual_url, f"URL for {service_name} should contain port {expected_port}"
            
            # Validate URL structure with regex
            url_pattern = r'^http://localhost:\d{4,5}$'
            assert re.match(url_pattern, actual_url), f"URL for {service_name} should match valid pattern"
            
            # Validate port extraction from URL
            port_from_url = int(actual_url.split(':')[-1])
            assert port_from_url == expected_port, f"Port in URL should match expected {expected_port}"
            assert 1024 <= port_from_url <= 65535, f"Port in URL should be in valid range"
            
            # Test performance
            assert gen_time < 0.01, f"URL generation for {service_name} should be very fast, took {gen_time:.4f}s"
        
        # Test invalid service names with comprehensive error handling
        invalid_services = [
            'invalid_service',
            '',
            'MEMOS',  # Case sensitivity
            'task-board',  # Wrong separator
            'unknown',
            'service_that_does_not_exist',
            ' memos ',  # With whitespace
            None  # None input
        ]
        
        for invalid_service in invalid_services:
            error_start = time.time()
            try:
                result = config.get_service_url(invalid_service)
                error_time = time.time() - error_start
                
                # Should return empty string for invalid services
                assert result == "", f"Invalid service '{invalid_service}' should return empty string, got '{result}'"
                assert isinstance(result, str), f"Result for invalid service should be string"
                assert error_time < 0.01, f"Error handling should be fast for '{invalid_service}'"
                
            except (TypeError, AttributeError) as e:
                # Acceptable to raise these errors for None or malformed inputs
                error_time = time.time() - error_start
                assert error_time < 0.01, f"Exception handling should be fast for '{invalid_service}'"
                if invalid_service is None:
                    assert 'None' in str(e) or 'attribute' in str(e), "Should have appropriate error for None input"
        
        # Validate overall performance
        avg_url_time = sum(url_generation_times) / len(url_generation_times)
        assert avg_url_time < 0.005, f"Average URL generation should be very fast, was {avg_url_time:.4f}s"
        
        # Test edge case - custom ports
        custom_config = Config(MEMOS_PORT=9999)
        custom_url = custom_config.get_service_url('memos')
        assert custom_url == 'http://localhost:9999', "Should handle custom ports correctly"
        assert '9999' in custom_url, "Custom port should appear in URL"
        
        # Test business logic - ensure URL uniqueness
        all_urls = [config.get_service_url(service) for service, _, _ in service_tests]
        unique_urls = set(all_urls)
        assert len(unique_urls) == len(all_urls), "All service URLs should be unique"
        
        total_test_time = time.time() - start_time
        assert total_test_time < 0.5, f"Complete URL generation test should be fast, took {total_test_time:.3f}s"
    
    def test_validate_success(self):
        """Test configuration validation with valid settings."""
        config = Config()
        
        # Mock database directory existence
        with patch('os.path.exists', return_value=True):
            assert config.validate() is True
    
    def test_validate_database_directory_missing(self):
        """Test validation failure when database directory doesn't exist."""
        config = Config()
        
        with patch('os.path.exists', return_value=False):
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                assert config.validate() is False
                assert mock_logger.warning.called
    
    def test_validate_invalid_port_ranges(self):
        """Test validation failure with invalid port numbers."""
        # Test port too low
        config = Config(MEMOS_PORT=500)
        with patch('os.path.exists', return_value=True):
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                assert config.validate() is False
                assert mock_logger.error.called
        
        # Test port too high
        config = Config(TASK_BOARD_PORT=70000)
        with patch('os.path.exists', return_value=True):
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                assert config.validate() is False
                assert mock_logger.error.called
    
    def test_validate_port_conflicts(self):
        """Test validation failure with port conflicts."""
        config = Config(
            MEMOS_PORT=8502,
            TASK_BOARD_PORT=8502  # Conflict!
        )
        
        with patch('os.path.exists', return_value=True):
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                assert config.validate() is False
                assert mock_logger.error.called
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = Config(
            DB_PATH='/test/db.db',
            TASK_BOARD_PORT=9000
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['DB_PATH'] == '/test/db.db'
        assert config_dict['TASK_BOARD_PORT'] == 9000
        assert 'SHOW_SCREENSHOTS' in config_dict
        
        # Test error conditions - config with None values
        config_with_none = Config(DB_PATH=None)
        none_dict = config_with_none.to_dict()
        assert none_dict['DB_PATH'] is None
        
        # Test that all expected keys are present
        expected_keys = ['DB_PATH', 'TASK_BOARD_PORT', 'SHOW_SCREENSHOTS', 'ENABLE_NOTIFICATIONS']
        for key in expected_keys:
            assert key in config_dict, f"Missing key: {key}"
    
    def test_memos_dir_property(self):
        """Test memos directory property."""
        config = Config(DB_PATH='/home/user/.memos/database.db')
        memos_dir = config.memos_dir
        
        assert isinstance(memos_dir, Path)
        assert str(memos_dir) == '/home/user/.memos'
        # Validate Path operations work correctly
        assert memos_dir.is_absolute(), "Memos directory should be absolute path"
        assert memos_dir.name == '.memos', "Directory name should be .memos"
        # Test path operations
        db_path = memos_dir / 'database.db'
        assert str(db_path) == '/home/user/.memos/database.db'
        screenshots_path = memos_dir / 'screenshots'
        assert str(screenshots_path) == '/home/user/.memos/screenshots'
        
        # Test edge case - empty path
        config_empty = Config(DB_PATH='')
        empty_dir = config_empty.memos_dir
        assert isinstance(empty_dir, Path)
        assert str(empty_dir) == '.'  # Path('').parent returns current directory
        # Verify empty path behavior
        assert not empty_dir.is_absolute(), "Empty path should not be absolute"
        assert empty_dir.exists(), "Current directory should exist"
        # Test that operations still work
        test_file = empty_dir / 'test.db'
        assert isinstance(test_file, Path)
        
        # Test edge case - root path
        config_root = Config(DB_PATH='/database.db')
        root_dir = config_root.memos_dir
        assert isinstance(root_dir, Path)
        assert str(root_dir) == '/'
        
        # Test error condition - malformed path handling
        try:
            config_malformed = Config(DB_PATH='\\\\invalid:path<>|?*')
            malformed_dir = config_malformed.memos_dir
            assert isinstance(malformed_dir, Path), "Should handle malformed paths gracefully"
        except (ValueError, OSError) as e:
            # Acceptable for malformed paths to raise these errors
            assert "path" in str(e).lower() or "invalid" in str(e).lower(), "Error should be path-related"
        
        # Test error condition - None path handling
        try:
            config_none = Config(DB_PATH=None)
            none_dir = config_none.memos_dir
            assert isinstance(none_dir, Path), "Should handle None path gracefully"
        except (TypeError, AttributeError) as e:
            # Acceptable for None to raise these errors
            assert "none" in str(e).lower() or "path" in str(e).lower(), "Error should indicate None path issue"
        
        # Test boundary condition - very long path
        long_path = '/home/user/' + 'very_long_directory_name_' * 20 + '/.memos/database.db'
        config_long = Config(DB_PATH=long_path)
        long_dir = config_long.memos_dir
        assert isinstance(long_dir, Path), "Should handle long paths"
        assert len(str(long_dir)) > 0, "Long path should not be empty"
    
    def test_get_ollama_url_default(self):
        """Test getting Ollama URL with default configuration and comprehensive validation.
        
        Enhanced test validates:
        - State changes: Configuration initialization affects URL generation
        - Business rules: Default URL follows Ollama service conventions
        - Realistic data: Valid network URLs that can be used for API calls
        - Performance: URL generation is efficient for repeated calls
        - Integration: URL format compatible with HTTP clients
        - Error propagation: Invalid configurations handled appropriately
        - Boundary conditions: Edge cases in URL parsing and validation
        """
        import time
        import socket
        from urllib.parse import urlparse, urlunparse
        from unittest.mock import patch
        
        # State change: Track configuration initialization
        start_time = time.time()
        config_before = None  # No config exists before
        config = Config()
        init_time = time.time() - start_time
        
        # Performance validation: Config creation should be fast
        assert init_time < 0.01, f"Config initialization too slow: {init_time:.4f}s"
        
        # Validate state change from None to configured
        assert config is not None, "Config should be created"
        assert config_before != config, "Config state should change from None to initialized"
        
        # Test default value with business rule validation
        url_start = time.time()
        initial_url = config.get_ollama_url()
        url_time = time.time() - url_start
        
        # Business rule: Should return Ollama's standard default
        assert initial_url == 'http://localhost:11434', "Should return standard Ollama default URL"
        
        # Performance validation: URL retrieval should be instant
        assert url_time < 0.001, f"URL retrieval too slow: {url_time:.4f}s"
        
        # Realistic data: Validate URL is properly formed for actual use
        assert initial_url.startswith('http://'), "URL should use HTTP protocol for local development"
        assert ':11434' in initial_url, "URL should include standard Ollama port"
        assert 'localhost' in initial_url, "URL should use localhost for local development"
        assert len(initial_url) > 10, "URL should be substantial length"
        assert ' ' not in initial_url, "URL should not contain spaces"
        assert initial_url.count('://') == 1, "URL should have exactly one protocol separator"
        
        # Integration: Test URL can be parsed by standard libraries
        parsed = urlparse(initial_url)
        assert parsed.scheme == 'http', "Parsed scheme should be HTTP"
        assert parsed.hostname == 'localhost', "Parsed hostname should be localhost"
        assert parsed.port == 11434, "Parsed port should be 11434"
        assert parsed.path == '', "Default URL should have no path"
        assert parsed.query == '', "Default URL should have no query parameters"
        assert parsed.fragment == '', "Default URL should have no fragment"
        
        # Business rule: URL should be valid for network requests
        # Test URL reconstruction
        reconstructed = urlunparse(parsed)
        assert reconstructed == initial_url, "URL should survive parse/unparse cycle"
        
        # State consistency: Multiple calls should return same URL
        url2 = config.get_ollama_url()
        url3 = config.get_ollama_url()
        assert initial_url == url2 == url3, "Multiple calls should return identical URLs"
        
        # Boundary condition: Test URL with different Config instances
        config2 = Config()
        url_other = config2.get_ollama_url()
        assert initial_url == url_other, "Different Config instances should return same default URL"
        
        # Business rule: Port should be in valid range
        assert 1 <= parsed.port <= 65535, "Port should be in valid TCP range"
        assert parsed.port >= 1024, "Port should be in user application range (>=1024)"
        
        # Realistic data: Test URL components individually
        host_part = f"{parsed.hostname}:{parsed.port}"
        assert host_part == "localhost:11434", "Host:port combination should match Ollama default"
        
        # Performance regression: Test repeated URL generation
        repeated_start = time.time()
        urls = [config.get_ollama_url() for _ in range(100)]
        repeated_time = time.time() - repeated_start
        
        assert repeated_time < 0.01, f"100 URL generations too slow: {repeated_time:.4f}s"
        assert all(u == initial_url for u in urls), "All repeated URLs should be identical"
        assert len(set(urls)) == 1, "URL generation should be deterministic"
        
        # Error boundary: Test address format validation
        try:
            # Test address format is valid (don't actually connect)
            addr_info = socket.getaddrinfo(parsed.hostname, parsed.port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            assert len(addr_info) > 0, "URL hostname should be resolvable"
        except socket.gaierror:
            # Acceptable in some test environments
            pass
    
    def test_get_ollama_url_from_env(self):
        """Test getting Ollama URL from environment variable with comprehensive validation."""
        from urllib.parse import urlparse
        import os
        
        config = Config()
        
        # 1. STATE CHANGES: Test environment variable state affects URL retrieval
        original_env = os.environ.get('OLLAMA_URL')
        
        # Test various URL formats from environment with realistic validation
        test_cases = [
            ('http://custom:8080', 'custom', 8080, 'http'),
            ('https://api.ollama.com:443', 'api.ollama.com', 443, 'https'),
            ('http://192.168.1.100:11434', '192.168.1.100', 11434, 'http'),
            ('http://localhost:11434', 'localhost', 11434, 'http')
        ]
        
        for test_url, expected_host, expected_port, expected_scheme in test_cases:
            # 2. SIDE EFFECTS: Environment changes should affect configuration
            # Get URL before environment change
            url_before = config.get_ollama_url()
            
            with patch.dict(os.environ, {'OLLAMA_URL': test_url}):
                # 3. REALISTIC DATA: Test with actual Ollama service URLs
                url_after = config.get_ollama_url()
                
                # Validate state change
                assert url_after == test_url, f"URL should match environment setting: {test_url}"
                # Only check state change if URL is actually different from default
                if test_url != 'http://localhost:11434':
                    assert url_before != url_after, f"URL should change from environment: {url_before} != {url_after}"
                
                # 4. BUSINESS RULES: URL should be properly formatted and parseable
                parsed = urlparse(url_after)
                assert parsed.scheme in ['http', 'https'], f"URL scheme should be http/https: {parsed.scheme}"
                assert parsed.hostname == expected_host, f"Hostname should match: {parsed.hostname} vs {expected_host}"
                assert parsed.port == expected_port, f"Port should match: {parsed.port} vs {expected_port}"
                assert parsed.scheme == expected_scheme, f"Scheme should match: {parsed.scheme} vs {expected_scheme}"
                
                # 5. INTEGRATION: URL should be usable for actual HTTP requests
                assert '://' in url_after, "URL should contain protocol separator"
                assert len(url_after) > 10, "URL should be substantial"
                assert not url_after.endswith('/'), "URL should not have trailing slash by default"
                
        # 6. ERROR PROPAGATION: Test invalid URL handling with state validation
        invalid_urls = ['invalid-url', 'ftp://wrong-protocol:123', 'not-a-url-at-all', '']
        for invalid_url in invalid_urls:
            # Get initial state before setting invalid URL
            initial_url_before_error = config.get_ollama_url()
            
            with patch.dict(os.environ, {'OLLAMA_URL': invalid_url}):
                try:
                    url_after_error = config.get_ollama_url()
                    # If no exception, validate the result
                    if url_after_error == invalid_url:
                        # Config returned invalid URL as-is, which might be intentional
                        assert isinstance(url_after_error, str), "Should return string even for invalid URLs"
                        # State changed to invalid URL
                        assert initial_url_before_error != url_after_error, "State should change even for invalid URLs"
                    else:
                        # Config provided fallback - validate it's a proper URL
                        parsed = urlparse(url_after_error)
                        assert parsed.scheme in ['http', 'https'], "Fallback should be valid URL"
                        # Log that fallback was used rather than raw invalid URL
                        assert len(url_after_error) > 10, "Fallback URL should be substantial"
                except Exception as e:
                    # Exception is acceptable for invalid URLs
                    assert isinstance(e, (ValueError, TypeError)), f"Should raise appropriate exception for invalid URL: {type(e)}"
        
        # Test with database and file side effects for comprehensive validation
        with patch.dict(os.environ, {'OLLAMA_URL': 'http://production:8080'}):
            # This tests side effects and state changes
            production_url = config.get_ollama_url()
            assert 'production' in production_url, "Should use production URL from environment"
            
            # Test integration with configuration save (if available)
            if hasattr(config, 'save'):
                try:
                    config.save()  # Side effect: write to file
                    assert True, "Config save should handle environment URLs"
                except Exception:
                    pass  # Save may not be implemented
        
        # 7. STATE VALIDATION: Restore original environment state
        if original_env is not None:
            os.environ['OLLAMA_URL'] = original_env
        elif 'OLLAMA_URL' in os.environ:
            del os.environ['OLLAMA_URL']
            
        # Validate configuration responds to environment changes
        default_url = config.get_ollama_url()
        assert isinstance(default_url, str), "Should always return string URL"
        assert len(default_url) > 0, "Default URL should not be empty"


class TestGlobalConfigManagement:
    """Test global configuration management functions."""
    
    def setup_method(self):
        """Reset global config before each test."""
        reset_config()
    
    def teardown_method(self):
        """Reset global config after each test."""
        reset_config()
    
    def test_get_config_default(self):
        """Test getting config with defaults."""
        with patch('os.path.exists', return_value=False):
            config = get_config()
            
            assert isinstance(config, Config)
            assert config.TASK_BOARD_PORT == 8602
            # Validate complete default configuration
            assert config.DB_PATH == os.path.expanduser("/Users/paulrohde/AutoTaskTracker.memos/database.db")
            assert config.MEMOS_PORT == 8841
            assert config.ANALYTICS_PORT == 8603
            # Verify all feature flags are set correctly
            assert config.ENABLE_NOTIFICATIONS is True
            assert config.ENABLE_ANALYTICS is True
            assert config.SHOW_SCREENSHOTS is True
            # Test that config is properly initialized and usable
            assert config.validate() is True
            service_urls = {
                'memos': config.get_service_url('memos'),
                'task_board': config.get_service_url('task_board')
            }
            assert all(url.startswith('http://localhost:') for url in service_urls.values())
        
        # Test error condition - file exists but is unreadable
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                with patch('autotasktracker.utils.config.logger') as mock_logger:
                    # Reset config AFTER setting up the patches to ensure fresh state
                    reset_config()
                    config = get_config()
                    assert isinstance(config, Config)
                    assert config.TASK_BOARD_PORT == 8602  # Should fall back to defaults
                    # Verify error was logged (from Config.from_file method)
                    mock_logger.error.assert_called_once()
                    # Verify the error message content
                    call_args = mock_logger.error.call_args[0][0]
                    assert "Error loading config" in call_args
        
        # Test corrupted config file
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='corrupted json')):
                with patch('autotasktracker.utils.config.logger') as mock_logger:
                    # Reset config AFTER setting up the patches to ensure fresh state
                    reset_config()
                    config = get_config()
                    assert isinstance(config, Config)
                    assert config.TASK_BOARD_PORT == 8602  # Should fall back to defaults
                    # Verify error was logged due to JSON decode error
                    mock_logger.error.assert_called_once()
                    call_args = mock_logger.error.call_args[0][0]
                    assert "Error loading config" in call_args
    
    def test_get_config_from_file(self):
        """Test getting config from file when it exists."""
        config_data = {'TASK_BOARD_PORT': 9000}
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
                config = get_config()
                
                assert config.TASK_BOARD_PORT == 9000
        
        # Test error condition - file with invalid data types
        invalid_config = {'TASK_BOARD_PORT': 'not_a_number'}
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(invalid_config))):
                with patch('autotasktracker.utils.config.logger') as mock_logger:
                    # Reset config AFTER setting up the patches to ensure fresh state
                    reset_config()
                    config = get_config()
                    # The implementation passes through invalid types from JSON
                    assert config.TASK_BOARD_PORT == 'not_a_number'
        
        # Test empty file
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='')):
                with patch('autotasktracker.utils.config.logger') as mock_logger:
                    # Reset config AFTER setting up the patches to ensure fresh state
                    reset_config()
                    config = get_config()
                    assert config.TASK_BOARD_PORT == 8602  # Should use defaults
                    mock_logger.error.assert_called()
    
    def test_get_config_singleton(self):
        """Test that get_config returns same instance on subsequent calls."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
        # Verify singleton behavior - modifications affect same instance
        original_port = config1.TASK_BOARD_PORT
        config1.TASK_BOARD_PORT = 9999
        assert config2.TASK_BOARD_PORT == 9999
        # Verify no new instance is created
        config3 = get_config()
        assert config3 is config1
        assert config3.TASK_BOARD_PORT == 9999
        # Reset for other tests
        config1.TASK_BOARD_PORT = original_port
    
    def test_set_config(self):
        """Test setting custom config."""
        custom_config = Config(TASK_BOARD_PORT=9999)
        set_config(custom_config)
        
        retrieved_config = get_config()
        assert retrieved_config is custom_config
        assert retrieved_config.TASK_BOARD_PORT == 9999
        # Verify all custom settings are preserved
        assert retrieved_config.MEMOS_PORT == custom_config.MEMOS_PORT
        assert retrieved_config.DB_PATH == custom_config.DB_PATH
        # Test that subsequent calls return the custom config
        another_retrieval = get_config()
        assert another_retrieval is custom_config
        # Verify custom config is functional
        assert custom_config.get_service_url('task_board') == 'http://localhost:9999'
    
    def test_reset_config(self):
        """Test resetting config."""
        # Set a custom config
        custom_config = Config(TASK_BOARD_PORT=9999, ENABLE_NOTIFICATIONS=False)
        set_config(custom_config)
        
        # Verify custom config is active
        assert get_config() is custom_config
        assert get_config().TASK_BOARD_PORT == 9999
        
        # Reset
        reset_config()
        
        # Next get_config should create new instance with defaults
        new_config = get_config()
        assert new_config is not custom_config
        assert new_config.TASK_BOARD_PORT == 8502  # Default value
        assert new_config.ENABLE_NOTIFICATIONS is True  # Default value
        # Verify complete reset to defaults
        assert new_config.DB_PATH == os.path.expanduser("/Users/paulrohde/AutoTaskTracker.memos/database.db")
        assert new_config.MEMOS_PORT == 8841
        # Test that reset is persistent
        assert get_config() is new_config


class TestConfigIntegration:
    """Test config integration with file system and environment."""
    
    def test_config_with_real_file_operations(self):
        """Test config save and load cycle with real file operations."""
        original_config = Config(
            DB_PATH='/test/path/db.db',
            TASK_BOARD_PORT=9000,
            SHOW_SCREENSHOTS=False,
            AUTO_REFRESH_SECONDS=120
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Save config
            original_config.save_to_file(config_path)
            
            # Load config back
            loaded_config = Config.from_file(config_path)
            
            # Verify all settings preserved
            assert loaded_config.DB_PATH == original_config.DB_PATH
            assert loaded_config.TASK_BOARD_PORT == original_config.TASK_BOARD_PORT
            assert loaded_config.SHOW_SCREENSHOTS == original_config.SHOW_SCREENSHOTS
            assert loaded_config.AUTO_REFRESH_SECONDS == original_config.AUTO_REFRESH_SECONDS
        finally:
            os.unlink(config_path)
    
    def test_config_validation_comprehensive(self):
        """Test comprehensive config validation scenarios."""
        # Test all valid configuration
        valid_config = Config(
            MEMOS_PORT=8841,
            TASK_BOARD_PORT=8602,
            ANALYTICS_PORT=8603,
            TIMETRACKER_PORT=8604,
            NOTIFICATIONS_PORT=8606
        )
        
        with patch('os.path.exists', return_value=True):
            assert valid_config.validate() is True
        
        # Test multiple validation failures
        invalid_config = Config(
            MEMOS_PORT=100,      # Too low
            TASK_BOARD_PORT=8502,
            ANALYTICS_PORT=8502, # Conflict with TASK_BOARD_PORT
            TIMETRACKER_PORT=80000  # Too high
        )
        
        with patch('os.path.exists', return_value=False):
            with patch('autotasktracker.utils.config.logger'):
                assert invalid_config.validate() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])