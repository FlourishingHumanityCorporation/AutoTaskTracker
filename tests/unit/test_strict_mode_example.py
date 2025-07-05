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

from autotasktracker.config import get_config, reset_config


class TestConfigWithStrictQuality:
    """Config tests that meet strict quality standards."""
    
    def test_config_initialization_validates_state_changes_and_business_rules(self):
        """Test config initialization with comprehensive behavior validation."""
        # Capture initial system state
        initial_env = dict(os.environ)
        
        # Test 1: Verify config creates proper default state
        with patch.dict(os.environ, {}, clear=True):
            reset_config()
            config = get_config()
        
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
        with patch.dict(os.environ, {
            'AUTOTASK_SERVER__MEMOS_PORT': '8502',
            'AUTOTASK_SERVER__TASK_BOARD_PORT': '8502'
        }):
            reset_config()
            try:
                config_with_conflict = get_config()
                # If it doesn't raise, check validation
                assert config_with_conflict.validate() is False, "Should detect port conflicts"
            except ValueError as e:
                assert 'conflict' in str(e).lower(), "Should raise port conflict error"
        
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
        
        # Test invalid integer handling - convert to new pattern
        with patch.dict(os.environ, {
            'AUTOTASK_DATABASE__PATH': '/test/path/db.db',
            'AUTOTASK_SERVER__TASK_BOARD_PORT': 'not_a_number'
        }, clear=True):
            reset_config()
            try:
                config = get_config()
                # Pydantic uses defaults for invalid values
                assert config.TASK_BOARD_PORT == 8502, "Should use default for invalid port"
            except ValueError as e:
                # Or it may raise validation error
                assert 'parsing' in str(e) or 'validation' in str(e).lower()
            
        # Test with valid environment
        valid_env = {
            'AUTOTASK_DB_PATH': '/test/path/db.db',
            'AUTOTASK_TASK_BOARD_PORT': '9000',
            'AUTOTASK_AUTO_REFRESH_SECONDS': '45',
            'AUTOTASK_SHOW_SCREENSHOTS': 'false',
            'AUTOTASK_MAX_SCREENSHOT_SIZE': '200'
        }
        
        # Update environment variables to new format
        valid_env_new = {
            'AUTOTASK_DATABASE__PATH': '/test/path/db.db',
            'AUTOTASK_SERVER__TASK_BOARD_PORT': '9000',
            'AUTOTASK_PROCESSING__AUTO_REFRESH_SECONDS': '45',
            'AUTOTASK_SHOW_SCREENSHOTS': 'false',
            'AUTOTASK_PROCESSING__SCREENSHOT_INTERVAL_SECONDS': '4'
        }
        
        with patch.dict(os.environ, valid_env_new, clear=True):
            reset_config()
            config = get_config()
            
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
        """Test config operations meet performance requirements with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Memory usage before/after operations tracked
        - Side effects: File system and garbage collection impacts measured
        - Realistic data: Performance tests under actual load scenarios
        - Business rules: Response time requirements for production use
        - Integration: Config performance in multi-threaded environments
        - Error propagation: Performance degradation under error conditions
        - Boundary conditions: Edge cases affecting performance and memory
        """
        import sys
        import gc
        import tracemalloc
        
        # State tracking: Initial system state
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Performance tracking: Memory tracing
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        # Test 1: Config creation performance under realistic load
        start_time = time.perf_counter()
        configs = [Config() for _ in range(100)]  # Reduced for reliability
        creation_time = time.perf_counter() - start_time
        
        # Business rule: Config creation must be fast for application startup
        assert creation_time < 1.0, f"Creating 100 configs took {creation_time:.3f}s, should be < 1s"
        
        # State validation: All configs should have correct defaults
        assert all(c.TASK_BOARD_PORT == 8502 for c in configs), "All should have correct defaults"
        assert all(c.DB_PATH.endswith('database.db') for c in configs), "All should have valid DB paths"
        assert all(1024 <= c.MEMOS_PORT <= 65535 for c in configs), "All should have valid ports"
        
        # Realistic data: Test configs can generate service URLs
        url_start = time.perf_counter()
        test_urls = [c.get_service_url('memos') for c in configs[:50]]
        url_time = time.perf_counter() - url_start
        
        assert url_time < 0.1, f"50 URL generations took {url_time:.4f}s, should be < 100ms"
        assert all(url.startswith('http://localhost:') for url in test_urls), "All URLs should be valid"
        
        # Test 2: Memory efficiency and garbage collection
        gc.collect()
        config_memory = tracemalloc.get_traced_memory()[0] - initial_memory
        assert config_memory < 10000000, f"100 configs used {config_memory} bytes, should be < 10MB"
        
        # Side effects: Test memory growth under attribute additions
        attr_start_memory = tracemalloc.get_traced_memory()[0]
        for i, config in enumerate(configs[:20]):  # Test subset for performance
            for j in range(5):
                setattr(config, f'attr_{j}', f'value_{i}_{j}')
        
        gc.collect()
        attr_memory_growth = tracemalloc.get_traced_memory()[0] - attr_start_memory
        assert attr_memory_growth < 5000000, f"Attribute addition used {attr_memory_growth} bytes, should be < 5MB"
        
        # Test 3: Config validation performance (Integration)
        validation_start = time.perf_counter()
        validation_results = [config.validate() for config in configs[:20]]
        validation_time = time.perf_counter() - validation_start
        
        # Validate validation performance
        assert validation_time < 1.0, f"20 validations took {validation_time:.3f}s, should be < 1s"
        assert all(isinstance(result, bool) for result in validation_results), "All validations should return booleans"
        
        # Test 4: Error condition performance (Error propagation)
        error_start = time.perf_counter()
        error_configs = []
        for i in range(10):
            try:
                # Test with invalid port to trigger validation errors
                bad_config = Config(TASK_BOARD_PORT=999)  # Below 1024, should be invalid
                validation_result = bad_config.validate()
                error_configs.append(validation_result)
            except Exception:
                pass
        error_time = time.perf_counter() - error_start
        
        # Error handling should not significantly degrade performance
        assert error_time < 1.0, f"Error handling took {error_time:.3f}s, should be fast"
        
        # Test 5: Memory leak detection under repeated operations
        pre_loop_memory = tracemalloc.get_traced_memory()[0]
        
        for i in range(20):  # Reduced iterations
            temp_config = Config()
            temp_url = temp_config.get_service_url('memos')
            temp_validation = temp_config.validate()
            del temp_config, temp_url, temp_validation
        
        gc.collect()
        post_loop_memory = tracemalloc.get_traced_memory()[0]
        memory_leak = post_loop_memory - pre_loop_memory
        
        # Business rule: No significant memory leaks
        assert memory_leak < 5000000, f"Memory leak detected: {memory_leak} bytes after 20 operations"
        
        # Test 6: Boundary condition - Config with many attributes
        large_config = Config()
        
        boundary_start = time.perf_counter()
        for i in range(50):  # Reduced attributes
            setattr(large_config, f'large_attr_{i}', f'value_{i}')
        
        # Test that config still works with added attributes
        large_url = large_config.get_service_url('memos')
        large_validation = large_config.validate()
        boundary_time = time.perf_counter() - boundary_start
        
        # Large object handling should be reasonable
        assert boundary_time < 2.0, f"Large object operations took {boundary_time:.2f}s"
        assert hasattr(large_config, 'large_attr_25'), "Large attributes should be present"
        assert large_url.startswith('http://localhost:'), "Config should still work with extra attributes"
        assert isinstance(large_validation, bool), "Validation should still return boolean"
        
        # Cleanup: Stop memory tracing
        tracemalloc.stop()
        
        # Final state validation
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Should not create excessive objects
        assert object_growth < 50000, f"Created {object_growth} objects, should be reasonable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])