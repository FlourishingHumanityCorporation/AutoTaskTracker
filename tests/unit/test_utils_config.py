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

from autotasktracker.utils.config import Config, get_config, set_config, reset_config


class TestConfig:
    """Test the Config class."""
    
    def test_config_initialization_with_defaults(self):
        """Test that Config initializes with correct default values."""
        config = Config()
        
        # Test database settings defaults
        assert config.DB_PATH == os.path.expanduser("~/.memos/database.db")
        assert config.SCREENSHOTS_DIR == os.path.expanduser("~/.memos/screenshots")
        assert config.LOGS_DIR == os.path.expanduser("~/.memos/logs")
        
        # Test server ports
        assert config.MEMOS_PORT == 8839
        assert config.TASK_BOARD_PORT == 8502
        assert config.ANALYTICS_PORT == 8503
        assert config.TIMETRACKER_PORT == 8504
        assert config.NOTIFICATIONS_PORT == 8505
        
        # Test application settings
        assert config.AUTO_REFRESH_SECONDS == 30
        assert config.CACHE_TTL_SECONDS == 60
        assert config.DEFAULT_TASK_LIMIT == 100
        assert config.GROUP_INTERVAL_MINUTES == 5
        assert config.SCREENSHOT_INTERVAL_SECONDS == 4
        
        # Test time tracking settings
        assert config.MIN_SESSION_DURATION_SECONDS == 30
        assert config.MAX_SESSION_GAP_SECONDS == 600
        assert config.IDLE_THRESHOLD_SECONDS == 300
        
        # Test feature flags
        assert config.SHOW_SCREENSHOTS is True
        assert config.ENABLE_NOTIFICATIONS is True
        assert config.ENABLE_ANALYTICS is True
        
        # Test performance settings
        assert config.MAX_SCREENSHOT_SIZE == 300
        assert config.CONNECTION_POOL_SIZE == 5
        assert config.QUERY_TIMEOUT_SECONDS == 30
    
    def test_config_from_env_with_all_types(self):
        """Test loading configuration from environment variables with type conversion."""
        env_vars = {
            'AUTOTASK_DB_PATH': '/custom/path/database.db',
            'AUTOTASK_TASK_BOARD_PORT': '9000',
            'AUTOTASK_AUTO_REFRESH_SECONDS': '45',
            'AUTOTASK_SHOW_SCREENSHOTS': 'false',
            'AUTOTASK_ENABLE_NOTIFICATIONS': 'true',
            'AUTOTASK_ENABLE_ANALYTICS': '1',
            'AUTOTASK_MAX_SCREENSHOT_SIZE': '500'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config.from_env()
        
        # Test string values
        assert config.DB_PATH == '/custom/path/database.db'
        
        # Test integer conversion
        assert config.TASK_BOARD_PORT == 9000
        assert config.AUTO_REFRESH_SECONDS == 45
        assert config.MAX_SCREENSHOT_SIZE == 500
        
        # Test boolean conversion
        assert config.SHOW_SCREENSHOTS is False
        assert config.ENABLE_NOTIFICATIONS is True
        assert config.ENABLE_ANALYTICS is True
        
        # Test defaults for non-specified variables
        assert config.ANALYTICS_PORT == 8503  # Default value
    
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
            assert config.ANALYTICS_PORT == 8503
        finally:
            os.unlink(config_path)
    
    def test_config_from_file_io_error(self):
        """Test handling of file IO errors."""
        with patch('autotasktracker.utils.config.logger') as mock_logger:
            config = Config.from_file('/nonexistent/config.json')
            
            # Should return default config on error
            assert config.TASK_BOARD_PORT == 8502
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
                assert config.TASK_BOARD_PORT == 8502
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
        """Test handling of save errors."""
        config = Config()
        
        with patch('autotasktracker.utils.config.logger') as mock_logger:
            # Try to save to invalid path
            config.save_to_file('/root/cannot_write_here.json')
            assert mock_logger.error.called
    
    def test_get_service_url(self):
        """Test service URL generation."""
        config = Config(
            MEMOS_PORT=8839,
            TASK_BOARD_PORT=8502,
            ANALYTICS_PORT=8503,
            TIMETRACKER_PORT=8504,
            NOTIFICATIONS_PORT=8505
        )
        
        assert config.get_service_url('memos') == 'http://localhost:8839'
        assert config.get_service_url('task_board') == 'http://localhost:8502'
        assert config.get_service_url('analytics') == 'http://localhost:8503'
        assert config.get_service_url('timetracker') == 'http://localhost:8504'
        assert config.get_service_url('notifications') == 'http://localhost:8505'
        
        # Test invalid service
        assert config.get_service_url('invalid_service') == ""
    
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
        
        # Test edge case - empty path
        config_empty = Config(DB_PATH='')
        empty_dir = config_empty.memos_dir
        assert isinstance(empty_dir, Path)
        assert str(empty_dir) == '.'  # Path('').parent returns current directory
        
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
        """Test getting Ollama URL with default."""
        config = Config()
        
        # Test default value
        assert config.get_ollama_url() == 'http://localhost:11434'
    
    def test_get_ollama_url_from_env(self):
        """Test getting Ollama URL from environment variable."""
        config = Config()
        
        with patch.dict(os.environ, {'OLLAMA_URL': 'http://custom:8080'}):
            assert config.get_ollama_url() == 'http://custom:8080'


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
            assert config.TASK_BOARD_PORT == 8502
        
        # Test error condition - file exists but is unreadable
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                with patch('autotasktracker.utils.config.logger') as mock_logger:
                    # Reset config AFTER setting up the patches to ensure fresh state
                    reset_config()
                    config = get_config()
                    assert isinstance(config, Config)
                    assert config.TASK_BOARD_PORT == 8502  # Should fall back to defaults
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
                    assert config.TASK_BOARD_PORT == 8502  # Should fall back to defaults
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
                    assert config.TASK_BOARD_PORT == 8502  # Should use defaults
                    mock_logger.error.assert_called()
    
    def test_get_config_singleton(self):
        """Test that get_config returns same instance on subsequent calls."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_set_config(self):
        """Test setting custom config."""
        custom_config = Config(TASK_BOARD_PORT=9999)
        set_config(custom_config)
        
        retrieved_config = get_config()
        assert retrieved_config is custom_config
        assert retrieved_config.TASK_BOARD_PORT == 9999
    
    def test_reset_config(self):
        """Test resetting config."""
        # Set a custom config
        custom_config = Config(TASK_BOARD_PORT=9999)
        set_config(custom_config)
        
        # Reset
        reset_config()
        
        # Next get_config should create new instance
        new_config = get_config()
        assert new_config is not custom_config
        assert new_config.TASK_BOARD_PORT == 8502  # Default value


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
            MEMOS_PORT=8839,
            TASK_BOARD_PORT=8502,
            ANALYTICS_PORT=8503,
            TIMETRACKER_PORT=8504,
            NOTIFICATIONS_PORT=8505
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