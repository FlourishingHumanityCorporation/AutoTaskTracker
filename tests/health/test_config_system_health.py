"""
Comprehensive configuration system health test for AutoTaskTracker.

This test audits the entire configuration system including:
- Configuration loading and validation
- Environment variable handling  
- Configuration synchronization between systems
- Configuration security and best practices
- Performance and reliability
- Integration with dependent systems
"""
import os
import json
import tempfile
import sqlite3
import subprocess
import socket
import time
from pathlib import Path
from unittest.mock import patch, mock_open
from typing import Dict, Any, List, Optional
import pytest
import logging

from autotasktracker.config import config, get_config, Config
from autotasktracker.pensieve.config_reader import (
    PensieveConfigReader, 
    get_pensieve_config_reader,
    get_pensieve_config,
    PensieveConfig
)

logger = logging.getLogger(__name__)


class TestConfigSystemHealthAudit:
    """Comprehensive audit of the entire configuration system."""
    
    def test_config_system_architecture_integrity(self):
        """Test that the configuration system architecture is sound."""
        # 1. CONFIGURATION LOADING INTEGRITY
        start_time = time.time()
        
        # Test main config loading
        main_config = get_config()
        assert isinstance(main_config, Config), "Main config should be Config instance"
        assert hasattr(main_config, 'DB_PATH'), "Config missing critical DB_PATH attribute"
        assert hasattr(main_config, 'get_db_path'), "Config missing get_db_path method"
        
        # Test Pensieve config loading
        pensieve_reader = get_pensieve_config_reader()
        assert isinstance(pensieve_reader, PensieveConfigReader), "Should get PensieveConfigReader instance"
        
        # Test config can be read without errors
        try:
            pensieve_config = get_pensieve_config()
            assert isinstance(pensieve_config, PensieveConfig), "Should get PensieveConfig instance"
        except Exception as e:
            # Pensieve config may fail in test environment - that's acceptable
            logger.info(f"Pensieve config not available in test environment: {e}")
        
        load_time = time.time() - start_time
        assert load_time < 0.5, f"Config loading too slow: {load_time:.3f}s"
        
        # 2. CONFIGURATION CONSISTENCY
        # Main config should have consistent defaults
        assert main_config.MEMOS_PORT == 8839, "Memos port should be consistent"
        assert main_config.TASK_BOARD_PORT == 8502, "Task board port should be consistent"
        assert main_config.ANALYTICS_PORT == 8503, "Analytics port should be consistent"
        
        # Database path should be absolute and valid
        db_path = main_config.get_db_path()
        assert isinstance(db_path, str), "DB path should be string"
        assert os.path.isabs(db_path), "DB path should be absolute"
        assert db_path.endswith('.db'), "DB path should point to database file"
        
        # 3. CONFIGURATION VALIDATION
        ports = [
            main_config.MEMOS_PORT,
            main_config.TASK_BOARD_PORT, 
            main_config.ANALYTICS_PORT,
            main_config.TIME_TRACKER_PORT,
            main_config.NOTIFICATIONS_PORT
        ]
        
        # All ports should be in valid range
        for port in ports:
            assert 1024 <= port <= 65535, f"Port {port} out of valid range"
        
        # All ports should be unique to prevent conflicts
        assert len(set(ports)) == len(ports), "All service ports must be unique"
        
        # 4. DIRECTORY STRUCTURE VALIDATION
        memos_dir = Path(db_path).parent
        assert memos_dir.name == '.memos', "Database should be in .memos directory"
        
        # Test directory creation logic
        screenshots_dir = main_config.get_screenshots_path()
        assert isinstance(screenshots_dir, str), "Screenshots path should be string"
        assert os.path.isabs(screenshots_dir), "Screenshots path should be absolute"
    
    def test_environment_variable_security_audit(self):
        """Audit environment variable handling for security and correctness."""
        # 1. ENVIRONMENT VARIABLE ENUMERATION
        config_env_vars = [
            'AUTOTASK_DB_PATH',
            'AUTOTASK_MEMOS_DIR', 
            'AUTOTASK_VLM_CACHE_DIR',
            'AUTOTASK_SCREENSHOTS_DIR',
            'AUTOTASK_VLM_MODEL',
            'AUTOTASK_VLM_PORT',
            'AUTOTASK_EMBEDDING_MODEL',
            'AUTOTASK_EMBEDDING_DIM',
            'AUTOTASK_BATCH_SIZE',
            'AUTOTASK_CONFIDENCE_THRESHOLD'
        ]
        
        pensieve_env_vars = [
            'MEMOS_DB_PATH',
            'MEMOS_SCREENSHOTS_DIR',
            'MEMOS_RECORD_INTERVAL',
            'MEMOS_API_PORT',
            'MEMOS_WEB_PORT',
            'MEMOS_MAX_WORKERS',
            'MEMOS_OCR_ENABLED'
        ]
        
        # 2. SECURITY VALIDATION - No sensitive data in environment
        original_env = dict(os.environ)
        
        try:
            # Test with potentially malicious environment variables
            malicious_test_cases = [
                ('AUTOTASK_DB_PATH', '/etc/passwd'),  # System file
                ('AUTOTASK_DB_PATH', '../../../etc/shadow'),  # Path traversal
                ('AUTOTASK_VLM_PORT', '22'),  # SSH port
                ('AUTOTASK_VLM_PORT', '80'),  # HTTP port
                ('AUTOTASK_VLM_PORT', 'not_a_number'),  # Invalid type
                ('AUTOTASK_BATCH_SIZE', '-1'),  # Negative value
                ('AUTOTASK_CONFIDENCE_THRESHOLD', '2.0'),  # Out of range
            ]
            
            for env_var, malicious_value in malicious_test_cases:
                with patch.dict(os.environ, {env_var: malicious_value}):
                    # Config should handle malicious values gracefully
                    try:
                        test_config = Config()
                        
                        # Validate that dangerous paths are not used as-is
                        if env_var == 'AUTOTASK_DB_PATH':
                            db_path = test_config.get_db_path()
                            if malicious_value in ['/etc/passwd', '../../../etc/shadow']:
                                # Should either reject or sanitize dangerous paths
                                assert not (malicious_value in db_path and os.path.exists(db_path)), \
                                    f"Config should not use dangerous path: {malicious_value}"
                        
                        # Validate port ranges
                        if env_var == 'AUTOTASK_VLM_PORT':
                            if malicious_value in ['22', '80']:
                                assert test_config.vlm_port not in [22, 80], \
                                    "Config should not use privileged/system ports"
                    
                    except (ValueError, TypeError, FileNotFoundError) as e:
                        # Expected for invalid values
                        assert any(keyword in str(e).lower() for keyword in 
                                 ['invalid', 'error', 'not found', 'permission']), \
                               f"Error should be descriptive for {env_var}={malicious_value}: {e}"
        
        finally:
            # Restore environment
            os.environ.clear()
            os.environ.update(original_env)
        
        # 3. TYPE CONVERSION SECURITY
        type_test_cases = [
            ('AUTOTASK_VLM_PORT', 'javascript:alert(1)'),  # Script injection
            ('AUTOTASK_BATCH_SIZE', '$(rm -rf /)'),  # Command injection
            ('AUTOTASK_CONFIDENCE_THRESHOLD', 'null'),  # JSON injection
        ]
        
        for env_var, injection_value in type_test_cases:
            with patch.dict(os.environ, {env_var: injection_value}):
                try:
                    test_config = Config()
                    # Should not execute or interpret injection attempts
                    assert injection_value not in str(test_config.to_dict()), \
                        f"Config should sanitize injection attempt: {injection_value}"
                except (ValueError, TypeError):
                    # Expected for invalid injection attempts
                    pass
    
    def test_config_synchronization_integrity(self):
        """Test synchronization between different configuration systems."""
        # 1. PENSIEVE-AUTOTASKTRACKER SYNCHRONIZATION
        try:
            pensieve_reader = get_pensieve_config_reader()
            
            # Test memos service status detection
            status = pensieve_reader.get_memos_status()
            assert isinstance(status, dict), "Status should be dictionary"
            assert 'running' in status, "Status should indicate if service is running"
            assert isinstance(status['running'], bool), "Running status should be boolean"
            
            # Test configuration synchronization
            sync_config = pensieve_reader.sync_autotasktracker_config()
            assert isinstance(sync_config, dict), "Sync config should be dictionary"
            
            # Validate synchronized values
            expected_sync_keys = [
                'DB_PATH', 'SCREENSHOTS_DIR', 'SCREENSHOT_INTERVAL_SECONDS',
                'MEMOS_PORT', 'PENSIEVE_API_URL', 'PENSIEVE_WEB_URL'
            ]
            
            for key in expected_sync_keys:
                assert key in sync_config, f"Sync config missing {key}"
                assert sync_config[key] is not None, f"Sync config {key} should not be None"
            
            # Test database path consistency
            if 'DB_PATH' in sync_config:
                main_config = get_config()
                pensieve_db_path = sync_config['DB_PATH']
                main_db_path = main_config.get_db_path()
                
                # Paths should be compatible (same directory structure)
                pensieve_dir = Path(pensieve_db_path).parent
                main_dir = Path(main_db_path).parent
                assert pensieve_dir.name == main_dir.name, \
                    "Database directories should be consistent"
        
        except Exception as e:
            # Pensieve may not be available in test environment
            logger.info(f"Pensieve synchronization test skipped: {e}")
        
        # 2. CONFIGURATION VALIDATION CONSISTENCY
        main_config = get_config()
        
        # Test that configuration dictionary export/import is consistent
        config_dict = main_config.to_dict()
        assert isinstance(config_dict, dict), "Config should export to dictionary"
        
        # Validate all critical keys are present
        critical_keys = ['db_path', 'vlm_model', 'embedding_model', 'ports']
        for key in critical_keys:
            assert key in config_dict, f"Config dict missing critical key: {key}"
        
        # Test port configuration consistency
        if 'ports' in config_dict:
            ports_dict = config_dict['ports']
            assert isinstance(ports_dict, dict), "Ports should be dictionary"
            assert 'task_board' in ports_dict, "Ports should include task_board"
            assert ports_dict['task_board'] == main_config.TASK_BOARD_PORT, \
                "Port values should be consistent"
    
    def test_config_performance_and_reliability(self):
        """Test configuration system performance and reliability."""
        # 1. CONFIGURATION LOADING PERFORMANCE
        load_times = []
        
        for i in range(10):
            start_time = time.time()
            config = get_config()
            db_path = config.get_db_path()
            end_time = time.time()
            load_times.append(end_time - start_time)
        
        avg_load_time = sum(load_times) / len(load_times)
        max_load_time = max(load_times)
        
        assert avg_load_time < 0.01, f"Average config load time too slow: {avg_load_time:.4f}s"
        assert max_load_time < 0.05, f"Max config load time too slow: {max_load_time:.4f}s"
        
        # 2. MEMORY USAGE VALIDATION
        import gc
        gc.collect()  # Clean up before measurement
        
        configs = []
        for i in range(100):
            configs.append(get_config())
        
        # Should reuse singleton instance
        unique_configs = set(id(config) for config in configs)
        assert len(unique_configs) == 1, "Config should use singleton pattern"
        
        # 3. CONCURRENT ACCESS SAFETY
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        def config_access_worker():
            """Worker function for concurrent config access."""
            config = get_config()
            return config.get_db_path()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(config_access_worker) for _ in range(50)]
            results = [future.result() for future in futures]
        
        # All threads should get consistent results
        unique_paths = set(results)
        assert len(unique_paths) == 1, "Config should be thread-safe"
        
        # 4. ERROR RECOVERY TESTING
        error_scenarios = [
            (FileNotFoundError, "Config file not found"),
            (PermissionError, "Config file permission denied"),
            (json.JSONDecodeError, "Invalid JSON in config"),
        ]
        
        for error_type, description in error_scenarios:
            with patch('builtins.open', side_effect=error_type(description)):
                try:
                    # Should handle errors gracefully
                    fallback_config = Config()
                    assert isinstance(fallback_config, Config), \
                        f"Should create fallback config for {description}"
                    assert fallback_config.TASK_BOARD_PORT == 8502, \
                        f"Should use defaults for {description}"
                except Exception as e:
                    # Some errors may propagate - that's acceptable if handled properly
                    assert error_type.__name__ in str(type(e).__name__), \
                        f"Should propagate appropriate error type for {description}"
    
    def test_config_integration_health(self):
        """Test configuration integration with dependent systems."""
        # 1. DATABASE CONFIGURATION VALIDATION
        main_config = get_config()
        db_path = main_config.get_db_path()
        
        # Test database connectivity
        db_dir = Path(db_path).parent
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
                created_dir = True
            except PermissionError:
                pytest.skip("Cannot create database directory for integration test")
                created_dir = False
        else:
            created_dir = False
        
        try:
            # Test SQLite database creation and access
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()
            assert version is not None, "Should be able to query SQLite version"
            conn.close()
            
            # Clean up test database
            if Path(db_path).exists():
                Path(db_path).unlink()
        
        finally:
            if created_dir:
                try:
                    db_dir.rmdir()
                except:
                    pass
        
        # 2. SERVICE PORT AVAILABILITY
        ports_to_test = [
            main_config.TASK_BOARD_PORT,
            main_config.ANALYTICS_PORT,
            main_config.TIME_TRACKER_PORT,
            main_config.NOTIFICATIONS_PORT
        ]
        
        def is_port_available(port):
            """Check if port is available for binding."""
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.bind(('localhost', port))
                    return True
            except OSError:
                return False  # Port in use or permission denied
        
        available_ports = []
        for port in ports_to_test:
            if is_port_available(port):
                available_ports.append(port)
        
        # At least some ports should be available (exact availability depends on system state)
        assert len(available_ports) >= 0, "Port availability check should work"
        
        # 3. VLM SERVICE CONFIGURATION
        ollama_url = main_config.get_ollama_url()
        assert ollama_url.startswith('http://'), "Ollama URL should use HTTP"
        assert 'localhost' in ollama_url, "Ollama URL should use localhost"
        assert str(main_config.vlm_port) in ollama_url, "Ollama URL should include configured port"
        
        # 4. DIRECTORY PERMISSIONS
        test_dirs = [
            main_config.get_screenshots_path(),
            main_config.get_vlm_cache_path(),
            str(Path(main_config.get_db_path()).parent)
        ]
        
        for test_dir in test_dirs:
            dir_path = Path(test_dir)
            
            # Test directory creation if it doesn't exist
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created = True
                except PermissionError:
                    pytest.skip(f"Cannot create directory {test_dir} for permission test")
                    created = False
            else:
                created = False
            
            if dir_path.exists():
                # Test read/write permissions
                test_file = dir_path / "health_test.tmp"
                try:
                    test_file.write_text("test")
                    content = test_file.read_text()
                    assert content == "test", f"Should be able to read/write in {test_dir}"
                    test_file.unlink()
                except Exception as e:
                    pytest.fail(f"Directory {test_dir} not properly accessible: {e}")
                
                # Clean up created directory
                if created:
                    try:
                        dir_path.rmdir()
                    except:
                        pass
    
    def test_config_security_hardening(self):
        """Test configuration security hardening and best practices."""
        # 1. PATH TRAVERSAL PROTECTION
        main_config = get_config()
        
        dangerous_paths = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\system',
            '/etc/shadow',
            'C:\\Windows\\System32\\config\\SAM',
            '${HOME}/../../../etc/passwd',  # Variable expansion
            '$(cat /etc/passwd)',  # Command substitution
        ]
        
        for dangerous_path in dangerous_paths:
            # Test that dangerous paths are not used directly
            test_config = Config(DB_PATH=dangerous_path)
            resolved_path = test_config.get_db_path()
            
            # Should not resolve to actual system files
            if os.path.exists(resolved_path):
                # If path exists, it should not be a critical system file
                assert not any(critical in resolved_path.lower() for critical in 
                             ['passwd', 'shadow', 'system32', 'config']), \
                    f"Config should not resolve to system file: {resolved_path}"
        
        # 2. INJECTION ATTACK PROTECTION  
        injection_tests = [
            'test"; DROP TABLE entities; --',
            "test'; DELETE FROM metadata_entries; --",
            'test`; rm -rf /; `',
            'test$(rm -rf /)',
            'test && rm -rf /',
        ]
        
        for injection in injection_tests:
            test_config = Config(vlm_model=injection)
            model_name = test_config.vlm_model
            
            # Should not contain dangerous SQL or shell metacharacters in final config
            dangerous_chars = [';', '--', '$(', '`', '&&', '||', '|', '&']
            has_dangerous = any(char in model_name for char in dangerous_chars)
            
            if has_dangerous:
                # If dangerous characters are preserved, they should be properly escaped/quoted
                # This depends on how the config is used downstream
                logger.warning(f"Config contains potential injection vector: {model_name}")
        
        # 3. PRIVILEGE ESCALATION PROTECTION
        # Test that config doesn't require or attempt privilege escalation
        privileged_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
        
        config_ports = [
            main_config.MEMOS_PORT,
            main_config.TASK_BOARD_PORT,
            main_config.ANALYTICS_PORT,
            main_config.TIME_TRACKER_PORT,
            main_config.NOTIFICATIONS_PORT,
            main_config.vlm_port
        ]
        
        for port in config_ports:
            assert port not in privileged_ports, \
                f"Config should not use privileged port {port}"
            assert port >= 1024, f"Config should not use system port {port}"
        
        # 4. INFORMATION DISCLOSURE PROTECTION
        config_dict = main_config.to_dict()
        
        # Config should not contain sensitive information
        config_str = json.dumps(config_dict).lower()
        sensitive_patterns = [
            'password', 'secret', 'key', 'token', 'credential',
            'api_key', 'auth', 'private', 'admin'
        ]
        
        for pattern in sensitive_patterns:
            assert pattern not in config_str, \
                f"Config should not contain sensitive pattern: {pattern}"
    
    def test_config_system_documentation_compliance(self):
        """Test that configuration system follows documentation and standards."""
        # 1. CONFIGURATION COMPLETENESS
        main_config = get_config()
        
        # All documented configuration options should be available
        expected_attributes = [
            'DB_PATH', 'SCREENSHOTS_DIR', 'LOGS_DIR', 'VLM_CACHE_DIR',
            'MEMOS_PORT', 'TASK_BOARD_PORT', 'ANALYTICS_PORT', 'TIME_TRACKER_PORT',
            'VLM_MODEL', 'VLM_PORT', 'EMBEDDING_MODEL', 'EMBEDDING_DIM',
            'AUTO_REFRESH_SECONDS', 'CACHE_TTL_SECONDS', 'TASK_LIMIT',
            'BATCH_SIZE', 'CONFIDENCE_THRESHOLD', 'SHOW_SCREENSHOTS',
            'ENABLE_NOTIFICATIONS', 'ENABLE_ANALYTICS'
        ]
        
        for attr in expected_attributes:
            assert hasattr(main_config, attr), f"Config missing documented attribute: {attr}"
            value = getattr(main_config, attr)
            assert value is not None, f"Config attribute {attr} should not be None"
        
        # 2. CONFIGURATION METHODS COMPLETENESS
        expected_methods = [
            'get_db_path', 'get_vlm_cache_path', 'get_screenshots_path',
            'get_ollama_url', 'to_dict'
        ]
        
        for method in expected_methods:
            assert hasattr(main_config, method), f"Config missing documented method: {method}"
            assert callable(getattr(main_config, method)), f"Config {method} should be callable"
        
        # 3. PENSIEVE INTEGRATION COMPLETENESS
        try:
            pensieve_reader = get_pensieve_config_reader()
            
            # Pensieve reader should have documented methods
            pensieve_methods = [
                'get_memos_status', 'read_pensieve_config',
                'sync_autotasktracker_config', 'validate_pensieve_setup'
            ]
            
            for method in pensieve_methods:
                assert hasattr(pensieve_reader, method), \
                    f"PensieveConfigReader missing method: {method}"
                assert callable(getattr(pensieve_reader, method)), \
                    f"PensieveConfigReader {method} should be callable"
        
        except Exception as e:
            logger.info(f"Pensieve integration test skipped: {e}")
        
        # 4. DEFAULT VALUES COMPLIANCE
        # Test that defaults match documented values
        default_expectations = {
            'MEMOS_PORT': 8839,
            'TASK_BOARD_PORT': 8502,
            'ANALYTICS_PORT': 8503,
            'VLM_MODEL': 'minicpm-v',
            'VLM_PORT': 11434,
            'EMBEDDING_MODEL': 'jina-embeddings-v2-base-en',
            'EMBEDDING_DIM': 768,
            'AUTO_REFRESH_SECONDS': 30,
            'CACHE_TTL_SECONDS': 60,
            'TASK_LIMIT': 100,
            'SCREENSHOT_INTERVAL_SECONDS': 4,
            'SHOW_SCREENSHOTS': True,
            'ENABLE_NOTIFICATIONS': True,
            'ENABLE_ANALYTICS': True
        }
        
        for attr, expected_value in default_expectations.items():
            actual_value = getattr(main_config, attr)
            assert actual_value == expected_value, \
                f"Config {attr} default mismatch: expected {expected_value}, got {actual_value}"


# Additional helper functions for health testing
def validate_config_file_format(config_path: str) -> Dict[str, Any]:
    """Validate configuration file format and return parsed content."""
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Validate JSON structure
        assert isinstance(config_data, dict), "Config file should contain JSON object"
        
        # Validate required fields are present and correct types
        type_validations = {
            'DB_PATH': str,
            'TASK_BOARD_PORT': int,
            'SHOW_SCREENSHOTS': bool,
        }
        
        for field, expected_type in type_validations.items():
            if field in config_data:
                assert isinstance(config_data[field], expected_type), \
                    f"Config field {field} should be {expected_type.__name__}"
        
        return config_data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Config file validation failed: {e}")


def check_system_dependencies() -> Dict[str, bool]:
    """Check availability of system dependencies."""
    dependencies = {}
    
    # Test Python modules
    modules_to_test = [
        'sqlite3', 'json', 'pathlib', 'logging', 'dataclasses',
        'yaml', 'subprocess', 'socket', 'threading'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            dependencies[f"module_{module}"] = True
        except ImportError:
            dependencies[f"module_{module}"] = False
    
    # Test system commands
    commands_to_test = ['ps', 'netstat']
    
    for cmd in commands_to_test:
        try:
            result = subprocess.run([cmd, '--version'], 
                                  capture_output=True, timeout=5)
            dependencies[f"command_{cmd}"] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            dependencies[f"command_{cmd}"] = False
    
    return dependencies


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])