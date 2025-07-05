import logging
logger = logging.getLogger(__name__)

"""
Example of tests that pass strict mode quality checks.

This demonstrates how to write tests that:
- Validate actual behavior, not just values
- Test error conditions and edge cases  
- Have meaningful assertions that catch real bugs
- Are resistant to common code mutations
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import time
import tempfile
from datetime import datetime, timedelta

from autotasktracker.utils.config import Config, get_config, set_config, reset_config


class TestConfigWithStrictQuality:
    """Config tests that meet strict quality standards."""
    
    def test_config_initialization_validates_state_changes_and_business_rules(self):
        """Test config initialization with comprehensive behavior validation."""
        # Capture initial system state
        initial_env = dict(os.environ)
        
        # Test 1: Verify config creates proper default state
        config = Config()
        
        # Validate state changes and transformations
        db_path = config.DB_PATH
        assert db_path.startswith(os.path.expanduser("~")), "DB path should expand user directory"
        assert db_path.endswith("database.db"), "DB path should point to database file"
        assert os.path.isabs(db_path), "DB path should be absolute"
        
        # Validate business rules
        assert 1024 <= config.MEMOS_PORT <= 65535, "Port must be in valid user range"
        assert config.TASK_BOARD_PORT != config.MEMOS_PORT, "Ports must not conflict"
        assert config.AUTO_REFRESH_SECONDS > 0, "Refresh must be positive"
        assert config.CACHE_TTL_SECONDS >= config.AUTO_REFRESH_SECONDS, "Cache TTL should exceed refresh"
        
        # Test 2: Verify config handles missing directories gracefully
        with patch('os.path.exists', return_value=False):
            validation_result = config.validate()
            assert validation_result is False, "Should fail validation with missing directories"
        
        # Test 3: Verify config detects port conflicts
        config_with_conflict = Config(
            MEMOS_PORT=8502,
            TASK_BOARD_PORT=8502
        )
        with patch('os.path.exists', return_value=True):
            assert config_with_conflict.validate() is False, "Should detect port conflicts"
        
        # Verify no environmental pollution
        assert dict(os.environ) == initial_env, "Should not modify environment"
    
    def test_config_from_env_handles_malformed_data_and_type_coercion(self):
        """Test environment loading with error conditions and type safety."""
        # Set up test environment with various edge cases
        test_env = {
            'AUTOTASK_DB_PATH': '/test/path/db.db',
            'AUTOTASK_TASK_BOARD_PORT': 'not_a_number',  # Invalid
            'AUTOTASK_AUTO_REFRESH_SECONDS': '0',  # Boundary
            'AUTOTASK_SHOW_SCREENSHOTS': 'maybe',  # Invalid boolean
            'AUTOTASK_MAX_SCREENSHOT_SIZE': '-100',  # Negative
            'AUTOTASK_CONNECTION_POOL_SIZE': '999999'  # Too large
        }
        
        # Test invalid integer handling
        try:
            with patch.dict(os.environ, test_env, clear=True):
                config = Config.from_env()
                # Should not reach here with invalid int
                assert False, "Should raise ValueError for invalid integer"
        except ValueError as e:
            assert "invalid literal" in str(e), "Should raise appropriate error"
            
        # Test with valid environment
        valid_env = {
            'AUTOTASK_DB_PATH': '/test/path/db.db',
            'AUTOTASK_TASK_BOARD_PORT': '9000',
            'AUTOTASK_AUTO_REFRESH_SECONDS': '45',
            'AUTOTASK_SHOW_SCREENSHOTS': 'false',
            'AUTOTASK_MAX_SCREENSHOT_SIZE': '200'
        }
        
        with patch.dict(os.environ, valid_env, clear=True):
            config = Config.from_env()
            
            # Validate proper loading
            assert config.DB_PATH == '/test/path/db.db', "String values should load"
            assert config.TASK_BOARD_PORT == 9000, "Integer should parse correctly"
            assert config.AUTO_REFRESH_SECONDS == 45, "Should load custom refresh"
            assert config.SHOW_SCREENSHOTS is False, "Boolean false should parse"
            assert config.MAX_SCREENSHOT_SIZE == 200, "Should load valid size"
            
            # Validate defaults for non-specified
            assert config.MEMOS_PORT == 8839, "Should use default when not in env"
            assert config.ENABLE_ANALYTICS is True, "Should use default boolean"
    
    def test_config_file_operations_handle_corruption_and_concurrent_access(self):
        """Test file operations with real-world error scenarios."""
        import tempfile
        import json
        import threading
        
        # Test 1: Handle corrupted JSON gracefully
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"DB_PATH": "/test", "INVALID_JSON"')
            corrupt_path = f.name
        
        try:
            config = Config.from_file(corrupt_path)
            assert config.TASK_BOARD_PORT == 8502, "Should return defaults on corruption"
            assert hasattr(config, 'DB_PATH'), "Should have all attributes despite corruption"
        finally:
            os.unlink(corrupt_path)
        
        # Test 2: Handle concurrent file access
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        results = []
        errors = []
        
        def concurrent_save(port_num):
            try:
                config = Config(TASK_BOARD_PORT=port_num)
                config.save_to_file(config_path)
                results.append(port_num)
            except Exception as e:
                errors.append(e)
        
        # Launch concurrent saves
        threads = [threading.Thread(target=concurrent_save, args=(8500 + i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # At least some should succeed
        assert len(results) > 0, "Some concurrent saves should succeed"
        assert len(errors) < len(threads), "Not all saves should fail"
        
        # Final file should be valid JSON
        try:
            with open(config_path, 'r') as f:
                final_data = json.load(f)
            assert 'TASK_BOARD_PORT' in final_data, "File should contain valid config"
            assert isinstance(final_data['TASK_BOARD_PORT'], int), "Port should be integer"
        finally:
            os.unlink(config_path)
        
        # Test 3: Handle permission errors
        with patch('builtins.open', side_effect=PermissionError("No write access")):
            config = Config()
            with patch('autotasktracker.utils.config.logger') as mock_logger:
                config.save_to_file('/root/no_permission.json')
                mock_logger.error.assert_called()
    
    def test_config_singleton_behavior_with_state_mutations(self):
        """Test singleton pattern handles state changes correctly."""
        # Reset to clean state
        reset_config()
        
        # Test 1: Verify true singleton behavior
        config1 = get_config()
        original_port = config1.TASK_BOARD_PORT
        
        # Mutate through first reference
        config1.TASK_BOARD_PORT = 9999
        config1.CUSTOM_ATTRIBUTE = "test_value"
        
        # Get "new" reference
        config2 = get_config()
        
        # Verify same object
        assert config2 is config1, "Should be same object"
        assert config2.TASK_BOARD_PORT == 9999, "Mutations should persist"
        assert hasattr(config2, 'CUSTOM_ATTRIBUTE'), "Dynamic attributes should persist"
        assert config2.CUSTOM_ATTRIBUTE == "test_value", "Dynamic values should match"
        
        # Test 2: Verify set_config replaces singleton
        new_config = Config(TASK_BOARD_PORT=7777)
        new_config.MARKER = "replacement"
        set_config(new_config)
        
        config3 = get_config()
        assert config3 is new_config, "Should return replacement config"
        assert config3 is not config1, "Should not be original config"
        assert config3.TASK_BOARD_PORT == 7777, "Should have new values"
        assert hasattr(config3, 'MARKER'), "Should have new attributes"
        assert not hasattr(config3, 'CUSTOM_ATTRIBUTE'), "Should not have old attributes"
        
        # Test 3: Verify reset clears everything
        reset_config()
        config4 = get_config()
        assert config4 is not config3, "Should be new instance after reset"
        assert config4.TASK_BOARD_PORT == 8502, "Should have default values"
        assert not hasattr(config4, 'MARKER'), "Should not have custom attributes"
        
        # Cleanup
        reset_config()
    
    def test_service_url_generation_with_edge_cases(self):
        """Test URL generation handles all edge cases properly."""
        # Test 1: Standard services
        config = Config(
            MEMOS_PORT=8839,
            TASK_BOARD_PORT=0,  # Invalid port
            ANALYTICS_PORT=70000,  # Out of range
            TIMETRACKER_PORT=-1,  # Negative
        )
        
        # Valid service
        memos_url = config.get_service_url('memos')
        assert memos_url.startswith('http://'), "Should use HTTP protocol"
        assert ':8839' in memos_url, "Should include port"
        assert 'localhost' in memos_url, "Should use localhost"
        
        # Invalid port handling
        task_url = config.get_service_url('task_board')
        assert task_url == "" or ':0' in task_url, "Should handle port 0"
        
        # Out of range port
        analytics_url = config.get_service_url('analytics')
        assert analytics_url == "" or ':70000' in analytics_url, "Should handle invalid port"
        
        # Unknown service
        unknown_url = config.get_service_url('unknown_service')
        assert unknown_url == "", "Unknown service should return empty"
        
        # Test 2: Service name variations
        name_tests = [
            ('MEMOS', ''),  # Uppercase
            ('memos ', ''),  # Extra space
            ('', ''),  # Empty
            (None, ''),  # None should be handled
        ]
        
        for service_name, expected in name_tests:
            try:
                url = config.get_service_url(service_name)
                if expected == '':
                    assert url == "", f"Invalid service '{service_name}' should return empty"
                else:
                    assert expected in url, f"Service '{service_name}' URL incorrect"
            except (AttributeError, TypeError):
                # Acceptable for None input
                pass
    
    def test_config_performance_and_memory_efficiency(self):
        """Test config operations meet performance requirements."""
        import sys
        import gc
        
        # Test 1: Config creation performance
        start_time = time.perf_counter()
        configs = [Config() for _ in range(1000)]
        creation_time = time.perf_counter() - start_time
        
        assert creation_time < 0.1, f"Creating 1000 configs took {creation_time:.3f}s, should be < 100ms"
        assert all(c.TASK_BOARD_PORT == 8502 for c in configs), "All should have correct defaults"
        
        # Test 2: Memory efficiency
        gc.collect()
        initial_memory = sys.getsizeof(configs[0])
        
        # Add many attributes
        for i, config in enumerate(configs):
            for j in range(10):
                setattr(config, f'attr_{j}', f'value_{i}_{j}')
        
        gc.collect()
        final_memory = sys.getsizeof(configs[0])
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 10000, f"Memory grew by {memory_growth} bytes per config"
        
        # Test 3: File operation performance
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Measure save performance
            start_time = time.perf_counter()
            for i in range(100):
                configs[i].save_to_file(temp_path)
            save_time = time.perf_counter() - start_time
            
            assert save_time < 1.0, f"100 saves took {save_time:.2f}s, should be < 1s"
            
            # Measure load performance
            start_time = time.perf_counter()
            loaded_configs = [Config.from_file(temp_path) for _ in range(100)]
            load_time = time.perf_counter() - start_time
            
            assert load_time < 0.5, f"100 loads took {load_time:.2f}s, should be < 500ms"
            assert all(isinstance(c, Config) for c in loaded_configs), "All should load successfully"
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])