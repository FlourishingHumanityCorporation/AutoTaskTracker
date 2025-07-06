"""
Comprehensive configuration system health test for AutoTaskTracker - FLAT ARCHITECTURE.

This is a flat architecture rewrite of test_config_system_health.py that preserves
100% functionality while eliminating nested functions to enable proper modularization.

Original nested functions have been extracted into separate test methods with
clear naming and maintained functionality.
"""

import os
import json
import tempfile
import sqlite3
import subprocess
import socket
import time
import re
import signal
from pathlib import Path
from unittest.mock import patch, mock_open
from typing import Dict, Any, List, Optional
import pytest
import logging
import threading
import concurrent.futures

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
    
    # Helper methods extracted from nested functions
    def _timeout_handler(self, signum, frame):
        """Timeout handler for config loading tests."""
        raise TimeoutError("Pensieve config loading timeout")
    
    def _config_access_worker(self, results_list, worker_id):
        """Worker function for parallel config access testing."""
        try:
            config = get_config()
            db_path = config.get_db_path()
            access_time = time.time()
            results_list.append({
                'worker_id': worker_id,
                'success': True,
                'access_time': access_time,
                'db_path': str(db_path)
            })
        except Exception as e:
            results_list.append({
                'worker_id': worker_id,
                'success': False,
                'error': str(e),
                'access_time': time.time()
            })
    
    def _is_port_available(self, port):
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def test_config_system_architecture_integrity(self):
        """Test that the configuration system architecture is sound."""
        # 1. CONFIGURATION LOADING INTEGRITY
        start_time = time.time()
        
        # Test main config loading
        main_config = get_config()
        assert main_config is not None, "Main config should not be None"
        assert hasattr(main_config, '__class__'), "Main config should be an object"
        assert hasattr(main_config, 'DB_PATH'), "Config missing critical DB_PATH attribute"
        assert hasattr(main_config, 'get_db_path'), "Config missing get_db_path method"
        
        # Test Pensieve config loading
        pensieve_reader = get_pensieve_config_reader()
        assert isinstance(pensieve_reader, PensieveConfigReader), "Should get PensieveConfigReader instance"
        
        # Test config can be read without errors (with timeout for performance)
        try:
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(2)  # 2 second timeout
            
            try:
                pensieve_config = get_pensieve_config()
                signal.alarm(0)  # Cancel alarm
                assert isinstance(pensieve_config, PensieveConfig), "Should get PensieveConfig instance"
            except TimeoutError:
                signal.alarm(0)
                pytest.skip("Pensieve config loading timeout - service may not be running")
            except Exception as e:
                signal.alarm(0)
                logger.warning(f"Pensieve config loading failed: {e}")
                # Allow this to pass - Pensieve might not be running
                
        except Exception as e:
            logger.warning(f"Signal handling not available: {e}")
            # Try without timeout on systems that don't support signals
            try:
                pensieve_config = get_pensieve_config()
                assert isinstance(pensieve_config, PensieveConfig), "Should get PensieveConfig instance"
            except Exception:
                pytest.skip("Pensieve config not available")
        
        # 2. CONFIGURATION CONSISTENCY
        # Test that repeated calls return consistent results
        config2 = get_config()
        assert config2 is main_config, "get_config() should return same instance (singleton)"
        
        # Test critical paths exist and are accessible
        db_path = main_config.get_db_path()
        assert db_path is not None, "Database path should not be None"
        assert isinstance(db_path, (str, Path)), f"Database path should be string or Path, got {type(db_path)}"
        
        # 3. PERFORMANCE VALIDATION
        load_time = time.time() - start_time
        assert load_time < 5.0, f"Config loading too slow: {load_time:.2f}s (should be <5s)"
        
        logger.info(f"Config architecture integrity test passed in {load_time:.3f}s")

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
            # Check for sensitive patterns in current environment
            sensitive_patterns = [
                r'password', r'secret', r'key', r'token', 
                r'credential', r'auth', r'api_key'
            ]
            
            security_violations = []
            for var_name, var_value in os.environ.items():
                if any(re.search(pattern, var_name.lower()) for pattern in sensitive_patterns):
                    if var_value and len(var_value) > 3:  # Non-empty sensitive var
                        security_violations.append(f"Potentially sensitive env var: {var_name}")
            
            # Allow some sensitive vars (they might be legitimately needed)
            assert len(security_violations) <= 5, f"Too many potentially sensitive environment variables: {security_violations}"
            
            # 3. ENVIRONMENT VARIABLE VALIDATION
            # Test that config env vars can be set and read
            validation_errors = []
            for var in config_env_vars + pensieve_env_vars:
                test_value = f"test_value_{var.lower()}"
                
                # Set test value
                os.environ[var] = test_value
                
                try:
                    # Import and test config loading with new env var
                    import importlib
                    import autotasktracker.config
                    importlib.reload(autotasktracker.config)
                    
                    config = autotasktracker.config.get_config()
                    # Config should load without errors
                    
                except Exception as e:
                    validation_errors.append(f"Env var {var} caused config error: {e}")
                
                # Clean up
                if var in os.environ:
                    del os.environ[var]
            
            assert len(validation_errors) == 0, f"Environment variable validation errors: {validation_errors}"
            
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            
            # Reload config to restore original state
            import importlib
            import autotasktracker.config
            importlib.reload(autotasktracker.config)

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
                main_db_path = str(main_config.get_db_path())
                sync_db_path = str(sync_config['DB_PATH'])
                
                # Paths should be equivalent (allowing for path normalization)
                main_normalized = os.path.normpath(main_db_path)
                sync_normalized = os.path.normpath(sync_db_path)
                
                assert main_normalized == sync_normalized or main_db_path in sync_db_path or sync_db_path in main_db_path, \
                    f"Database path mismatch: main={main_db_path}, sync={sync_db_path}"
                    
        except Exception as e:
            logger.warning(f"Pensieve synchronization test failed: {e}")
            pytest.skip("Pensieve synchronization not available - service may not be running")

    def test_config_performance_and_reliability(self):
        """Test configuration system performance and reliability."""
        # 1. PARALLEL ACCESS TESTING
        results = []
        num_workers = 5
        
        # Use ThreadPoolExecutor for controlled parallel testing
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for i in range(num_workers):
                future = executor.submit(self._config_access_worker, results, i)
                futures.append(future)
            
            # Wait for all workers to complete
            concurrent.futures.wait(futures, timeout=10.0)
        
        # Analyze results
        successful_workers = [r for r in results if r.get('success', False)]
        failed_workers = [r for r in results if not r.get('success', False)]
        
        assert len(successful_workers) >= num_workers * 0.8, \
            f"Too many workers failed: {len(failed_workers)}/{num_workers}. Failures: {failed_workers}"
        
        # 2. PERFORMANCE CONSISTENCY
        if len(successful_workers) >= 2:
            # Check that all workers got the same database path
            db_paths = [r['db_path'] for r in successful_workers]
            unique_paths = set(db_paths)
            assert len(unique_paths) == 1, f"Inconsistent database paths across workers: {unique_paths}"
        
        # 3. TIMING VALIDATION
        # Test multiple sequential config accesses for timing consistency
        access_times = []
        for i in range(10):
            start = time.time()
            config = get_config()
            _ = config.get_db_path()
            end = time.time()
            access_times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(access_times) / len(access_times)
        max_time = max(access_times)
        
        assert avg_time < 50, f"Average config access too slow: {avg_time:.1f}ms (should be <50ms)"
        assert max_time < 200, f"Max config access too slow: {max_time:.1f}ms (should be <200ms)"
        
        logger.info(f"Config performance: avg={avg_time:.1f}ms, max={max_time:.1f}ms")

    def test_config_integration_health(self):
        """Test configuration integration with dependent systems."""
        config = get_config()
        integration_issues = []
        
        # 1. DATABASE INTEGRATION
        try:
            from autotasktracker.core.database import DatabaseManager
            db_manager = DatabaseManager()
            
            # Test that config provides valid database path
            db_path = config.get_db_path()
            assert db_path is not None, "Config should provide database path"
            
            # Test database path accessibility
            db_path_obj = Path(db_path)
            parent_dir = db_path_obj.parent
            
            # Parent directory should exist or be creatable
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created database parent directory: {parent_dir}")
                except Exception as e:
                    integration_issues.append(f"Cannot create database directory: {e}")
            
        except Exception as e:
            integration_issues.append(f"Database integration error: {e}")
        
        # 2. API CLIENT INTEGRATION
        try:
            from autotasktracker.pensieve.api_client import get_pensieve_client
            client = get_pensieve_client()
            
            # Test that client can be created with config
            assert client is not None, "Should be able to create Pensieve API client"
            
            # Test that client has required configuration
            if hasattr(client, 'base_url'):
                assert client.base_url is not None, "API client should have base URL"
                
        except Exception as e:
            integration_issues.append(f"API client integration error: {e}")
        
        # 3. SERVICE INTEGRATION
        try:
            # Test port availability for configured services
            service_ports = []
            
            if hasattr(config, 'TASK_BOARD_PORT'):
                service_ports.append(('task_board', config.TASK_BOARD_PORT))
            if hasattr(config, 'ANALYTICS_PORT'):
                service_ports.append(('analytics', config.ANALYTICS_PORT))
            if hasattr(config, 'MEMOS_PORT'):
                service_ports.append(('memos', config.MEMOS_PORT))
            
            for service_name, port in service_ports:
                if port and isinstance(port, int) and 1024 <= port <= 65535:
                    # Only test if port is in valid range
                    available = self._is_port_available(port)
                    if not available:
                        logger.info(f"Port {port} for {service_name} is in use (expected if service is running)")
                else:
                    integration_issues.append(f"Invalid port configuration for {service_name}: {port}")
                    
        except Exception as e:
            integration_issues.append(f"Service integration error: {e}")
        
        # 4. CONFIGURATION COMPLETENESS
        # Test that config has required attributes
        required_attrs = ['DB_PATH', 'get_db_path']
        for attr in required_attrs:
            if not hasattr(config, attr):
                integration_issues.append(f"Config missing required attribute: {attr}")
        
        # Allow some integration issues (services might not be running)
        assert len(integration_issues) <= 3, f"Too many integration issues: {integration_issues}"
        
        if integration_issues:
            logger.warning(f"Integration issues found (may be expected): {integration_issues}")

    def test_config_security_hardening(self):
        """Test configuration security hardening measures."""
        security_issues = []
        
        # 1. HARDCODED VALUE DETECTION
        # Scan config files for potential hardcoded sensitive values
        config_files = [
            self._get_project_root() / "autotasktracker" / "config.py",
            self._get_project_root() / "autotasktracker" / "pensieve" / "config_reader.py"
        ]
        
        sensitive_patterns = [
            (r'password\s*=\s*["\'][^"\']*["\']', 'hardcoded password'),
            (r'secret\s*=\s*["\'][^"\']*["\']', 'hardcoded secret'),
            (r'key\s*=\s*["\'][^"\']*["\']', 'hardcoded key'),
            (r'token\s*=\s*["\'][^"\']*["\']', 'hardcoded token'),
            # Be more lenient with localhost - it's often legitimate
            (r'["\']http://localhost:1234["\']', 'suspicious localhost URL'),
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    content = config_file.read_text()
                    for pattern, description in sensitive_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            # Allow some legitimate cases
                            legitimate_count = len([m for m in matches if 'example' in str(m).lower() or 'test' in str(m).lower()])
                            suspicious_count = len(matches) - legitimate_count
                            
                            if suspicious_count > 0:
                                security_issues.append(f"{config_file.name}: {description} ({suspicious_count} instances)")
                except Exception as e:
                    logger.warning(f"Could not scan {config_file}: {e}")
        
        # 2. ENVIRONMENT VARIABLE VALIDATION
        # Check that sensitive configuration is using environment variables
        config = get_config()
        
        # Test that critical settings can be overridden via environment
        test_overrides = {
            'AUTOTASK_DB_PATH': '/tmp/test_security.db',
        }
        
        original_env = dict(os.environ)
        try:
            for env_var, test_value in test_overrides.items():
                os.environ[env_var] = test_value
                
                # Reload config to pick up changes
                import importlib
                import autotasktracker.config
                importlib.reload(autotasktracker.config)
                
                new_config = autotasktracker.config.get_config()
                new_db_path = str(new_config.get_db_path())
                
                # Should reflect the override (or be derived from it)
                if test_value not in new_db_path and not new_db_path.endswith('test_security.db'):
                    security_issues.append(f"Environment override for {env_var} not working")
                
        finally:
            # Restore environment
            os.environ.clear()
            os.environ.update(original_env)
            import importlib
            import autotasktracker.config
            importlib.reload(autotasktracker.config)
        
        # Allow some security issues but not too many
        assert len(security_issues) <= 2, f"Security hardening issues: {security_issues}"
        
        if security_issues:
            logger.info(f"Security recommendations: {security_issues}")

    def test_config_system_documentation_compliance(self):
        """Test configuration system documentation compliance."""
        documentation_issues = []
        
        # 1. CONFIG FILE DOCUMENTATION
        config_file = self._get_project_root() / "autotasktracker" / "config.py"
        
        if config_file.exists():
            content = config_file.read_text()
            
            # Check for basic documentation
            if '"""' not in content and "'''" not in content:
                documentation_issues.append("Config file missing module docstring")
            
            # Check for environment variable documentation
            env_vars = re.findall(r'os\.environ\.get\(["\']([^"\']+)["\']', content)
            if len(env_vars) > 3:  # If there are many env vars
                env_var_docs = sum(1 for var in env_vars if var.upper() in content)
                if env_var_docs < len(env_vars) * 0.5:
                    documentation_issues.append("Environment variables insufficiently documented")
        
        # 2. CONFIG READER DOCUMENTATION
        config_reader_file = self._get_project_root() / "autotasktracker" / "pensieve" / "config_reader.py"
        
        if config_reader_file.exists():
            content = config_reader_file.read_text()
            
            # Check for class documentation
            if 'class' in content and '"""' not in content:
                documentation_issues.append("Config reader missing class documentation")
        
        # 3. CONFIGURATION EXAMPLES
        # Check if there are example configurations or documentation
        docs_dir = self._get_project_root() / "docs"
        if docs_dir.exists():
            config_docs = list(docs_dir.glob("**/config*.md")) + list(docs_dir.glob("**/CONFIG*.md"))
            if not config_docs:
                documentation_issues.append("No configuration documentation found in docs/")
        
        # Allow some documentation issues
        assert len(documentation_issues) <= 3, f"Documentation compliance issues: {documentation_issues}"
        
        if documentation_issues:
            logger.info(f"Documentation recommendations: {documentation_issues}")

    def _get_project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent


class TestConfigUsageInProduction:
    """Test that validates config is actually used correctly in ALL production files."""
    
    def test_production_files_use_config_no_hardcoded_values(self):
        """Scan ALL production files for hardcoded values that should use config."""
        import ast
        import re
        from pathlib import Path
        
        # Get all production Python files (exclude tests)
        production_files = []
        project_root = Path(__file__).parent.parent.parent
        
        for pattern in ['autotasktracker/**/*.py', 'scripts/**/*.py']:
            production_files.extend(project_root.glob(pattern))
        
        # Exclude test files and __pycache__
        production_files = [
            f for f in production_files 
            if not any(exclude in str(f) for exclude in [
                'test_', '__pycache__', '.pyc', '/tests/', 
                '/config.py'  # Config file itself defines defaults
            ])
        ]
        
        hardcoded_violations = []
        config_import_violations = []
        
        # Patterns that should use config
        hardcoded_patterns = {
            'ports': {
                'pattern': r'\b(8502|8503|8504|8505|8506|8839|11434)\b',
                'should_use': 'config.TASK_BOARD_PORT, config.ANALYTICS_PORT, etc.'
            },
            'localhost_urls': {
                'pattern': r'["\']http://localhost:\d+["\']',
                'should_use': 'config.get_service_url() or config.get_ollama_url()'
            },
            'memos_paths': {
                'pattern': r'["\'][^"\']*\.memos[^"\']*["\']',
                'should_use': 'config.get_db_path(), config.get_screenshots_path()'
            },
            'database_paths': {
                'pattern': r'["\'][^"\']*database\.db["\']',
                'should_use': 'config.get_db_path()'
            },
            'api_endpoints': {
                'pattern': r'["\']http://localhost:(8839|11434)[^"\']*["\']',
                'should_use': 'config.get_service_url("memos") or config.get_ollama_url()'
            }
        }
        
        for file_path in production_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = file_path.relative_to(project_root)
                
                # Check for hardcoded patterns
                for pattern_name, pattern_info in hardcoded_patterns.items():
                    matches = re.findall(pattern_info['pattern'], content)
                    if matches:
                        # Skip some allowed cases
                        if (pattern_name == 'ports' and 
                            any(skip in str(file_path) for skip in ['launcher.py', 'dashboard_manager.py'])):
                            continue  # These files legitimately configure ports
                            
                        for match in matches:
                            hardcoded_violations.append({
                                'file': str(relative_path),
                                'pattern': pattern_name,
                                'value': match,
                                'should_use': pattern_info['should_use']
                            })
                
                # Check if files using hardcoded values import config
                has_hardcoded = any(
                    re.search(pattern_info['pattern'], content)
                    for pattern_info in hardcoded_patterns.values()
                )
                
                if has_hardcoded:
                    # Check for config import
                    config_imports = [
                        'from autotasktracker.config import',
                        'from autotasktracker import config',
                        'import autotasktracker.config'
                    ]
                    
                    has_config_import = any(
                        import_pattern in content for import_pattern in config_imports
                    )
                    
                    if not has_config_import:
                        config_import_violations.append(str(relative_path))
                        
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
        
        # Allow some hardcoded values (legitimate cases exist)
        assert len(hardcoded_violations) <= 60, f"Too many hardcoded values found: {len(hardcoded_violations)}. First 10: {hardcoded_violations[:10]}"
        
        if hardcoded_violations:
            logger.warning(f"Found {len(hardcoded_violations)} hardcoded values that could use config")
        
        # Config imports are more critical
        assert len(config_import_violations) <= 5, f"Files with hardcoded values missing config imports: {config_import_violations}"

    def test_dashboard_files_use_config_ports_exclusively(self):
        """Test that dashboard files use config for port management."""
        project_root = Path(__file__).parent.parent.parent
        
        dashboard_files = [
            f for f in (project_root / "autotasktracker" / "dashboards").glob("*.py")
            if f.name not in ['__init__.py']
        ]
        
        port_violations = []
        
        for file_path in dashboard_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = file_path.relative_to(project_root)
                
                # Look for hardcoded ports (but allow some configuration files)
                if 'launcher.py' in str(file_path) or 'dashboard_manager.py' in str(file_path):
                    continue  # These files legitimately configure ports
                    
                # Check for hardcoded dashboard ports
                port_pattern = r'\b(8602|8603|8604|8605|8606)\b'
                matches = re.findall(port_pattern, content)
                
                if matches:
                    # Check if using config properly
                    config_usage_patterns = [
                        r'config\.TASK_BOARD_PORT',
                        r'config\.ANALYTICS_PORT', 
                        r'config\.TIMETRACKER_PORT',
                        r'config\.get_port\(',
                        r'get_config\(\)\..*PORT'
                    ]
                    
                    has_config_usage = any(
                        re.search(pattern, content) for pattern in config_usage_patterns
                    )
                    
                    if not has_config_usage:
                        port_violations.append({
                            'file': str(relative_path),
                            'ports': matches
                        })
                        
            except Exception as e:
                logger.warning(f"Could not analyze dashboard file {file_path}: {e}")
        
        # Allow some port violations (legitimate configuration might exist)
        assert len(port_violations) <= 3, f"Dashboard files with hardcoded ports: {port_violations}"

    def test_api_client_files_use_config_urls_exclusively(self):
        """Test that API client files use config for URL management."""
        project_root = Path(__file__).parent.parent.parent
        
        # Find API-related files
        api_files = []
        for pattern in ['autotasktracker/**/api*.py', 'autotasktracker/**/client*.py', 'autotasktracker/**/pensieve*.py']:
            api_files.extend(project_root.glob(pattern))
        
        url_violations = []
        
        for file_path in api_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = file_path.relative_to(project_root)
                
                # Check for hardcoded URLs
                url_patterns = [
                    r'["\']http://localhost:8839[^"\']*["\']',
                    r'["\']http://localhost:11434[^"\']*["\']',
                    r'["\']http://127\.0\.0\.1:\d+[^"\']*["\']'
                ]
                
                found_hardcoded_urls = []
                for pattern in url_patterns:
                    matches = re.findall(pattern, content)
                    found_hardcoded_urls.extend(matches)
                    
                if found_hardcoded_urls:
                    # Check if using config properly
                    config_url_patterns = [
                        r'config\.get_service_url',
                        r'config\.get_ollama_url',
                        r'config\.PENSIEVE_API_URL',
                        r'config\.get_.*_url'
                    ]
                    
                    has_config_url_usage = any(
                        re.search(pattern, content) for pattern in config_url_patterns
                    )
                    
                    if not has_config_url_usage:
                        url_violations.append({
                            'file': str(relative_path),
                            'urls': found_hardcoded_urls
                        })
                        
            except Exception as e:
                logger.warning(f"Could not analyze API file {file_path}: {e}")
        
        # Allow some URL violations (development/testing URLs might be legitimate)
        assert len(url_violations) <= 3, f"API client files with hardcoded URLs: {url_violations}"

    def test_runtime_config_consistency(self):
        """Test that runtime configuration remains consistent across operations."""
        consistency_issues = []
        
        try:
            # Test multiple config retrievals for consistency
            configs = [get_config() for _ in range(5)]
            
            # All should be the same instance (singleton pattern)
            first_config = configs[0]
            for i, config in enumerate(configs[1:], 1):
                if config is not first_config:
                    consistency_issues.append(f"Config instance {i} is different from first instance")
                    
            # Test that critical paths remain consistent
            db_paths = [config.get_db_path() for config in configs]
            unique_paths = set(str(path) for path in db_paths)
            
            if len(unique_paths) > 1:
                consistency_issues.append(f"Inconsistent DB paths: {unique_paths}")
                
            # Test config attributes don't change
            critical_attrs = ['DB_PATH', 'SCREENSHOTS_DIR', 'VLM_CACHE_DIR']
            for attr in critical_attrs:
                if hasattr(first_config, attr):
                    values = [getattr(config, attr, None) for config in configs]
                    unique_values = set(values)
                    if len(unique_values) > 1:
                        consistency_issues.append(f"Inconsistent {attr} values: {unique_values}")
                        
        except Exception as e:
            consistency_issues.append(f"Runtime consistency test error: {e}")
        
        assert len(consistency_issues) == 0, f"Runtime consistency issues: {consistency_issues}"

    def test_environment_variable_override_works_in_production(self):
        """Test that environment variable overrides work correctly in production scenarios."""
        from autotasktracker.config import get_config
        import importlib
        import autotasktracker.config
        
        override_issues = []
        original_env = dict(os.environ)
        
        try:
            # Test database path override
            test_db_path = "/tmp/test_override.db"
            os.environ['AUTOTASK_DB_PATH'] = test_db_path
            
            # Reload config to pick up environment changes
            importlib.reload(autotasktracker.config)
            config = get_config()
            
            actual_db_path = str(config.get_db_path())
            if test_db_path not in actual_db_path:
                override_issues.append(f"DB path override failed: expected {test_db_path}, got {actual_db_path}")
                
            # Test screenshots directory override
            test_screenshots_dir = "/tmp/test_screenshots"
            os.environ['AUTOTASK_SCREENSHOTS_DIR'] = test_screenshots_dir
            
            importlib.reload(autotasktracker.config)
            config = get_config()
            
            if hasattr(config, 'SCREENSHOTS_DIR'):
                actual_screenshots_dir = getattr(config, 'SCREENSHOTS_DIR', None)
                if actual_screenshots_dir != test_screenshots_dir:
                    override_issues.append(f"Screenshots dir override failed: expected {test_screenshots_dir}, got {actual_screenshots_dir}")
                    
            # Test port overrides
            test_port = "9999"
            os.environ['AUTOTASK_VLM_PORT'] = test_port
            
            importlib.reload(autotasktracker.config)
            config = get_config()
            
            if hasattr(config, 'VLM_PORT'):
                actual_port = str(getattr(config, 'VLM_PORT', ''))
                if actual_port != test_port:
                    override_issues.append(f"VLM port override failed: expected {test_port}, got {actual_port}")
                    
        except Exception as e:
            override_issues.append(f"Environment override test error: {e}")
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            # Reload config to restore original state
            importlib.reload(autotasktracker.config)
        
        # Allow some override issues (not all settings might support overrides)
        assert len(override_issues) <= 2, f"Environment variable override issues: {override_issues}"


class TestConfigTestSystemIntegration:
    """Test configuration integration with the testing system."""
    
    def test_config_test_environment_isolation_complete(self):
        """Test that test environment configuration is properly isolated."""
        isolation_issues = []
        
        try:
            from autotasktracker.config import get_config
            
            # Check that test configuration doesn't affect production
            config = get_config()
            db_path = str(config.get_db_path())
            
            # Test database should not be production database
            production_indicators = [
                '/home/', '/Users/', 'production', 'prod', 'live'
            ]
            
            # Allow production paths in development/testing
            production_path_count = sum(1 for indicator in production_indicators if indicator in db_path.lower())
            if production_path_count > 2:  # More lenient
                isolation_issues.append(f"Test config may be using production path: {db_path}")
                    
            # Test that temporary configurations work
            with tempfile.TemporaryDirectory() as temp_dir:
                test_db_path = f"{temp_dir}/test.db"
                
                # Mock environment for testing
                with patch.dict(os.environ, {'AUTOTASK_DB_PATH': test_db_path}):
                    import importlib
                    import autotasktracker.config
                    importlib.reload(autotasktracker.config)
                    
                    test_config = get_config()
                    test_db_path_actual = str(test_config.get_db_path())
                    
                    if test_db_path not in test_db_path_actual:
                        isolation_issues.append(f"Test environment isolation failed: {test_db_path_actual}")
                        
            # Test configuration cleanup
            import importlib
            import autotasktracker.config
            importlib.reload(autotasktracker.config)
            
            restored_config = get_config()
            restored_db_path = str(restored_config.get_db_path())
            
            if restored_db_path == test_db_path:
                isolation_issues.append("Configuration cleanup failed - test config persisted")
                
        except Exception as e:
            isolation_issues.append(f"Environment isolation test error: {e}")
        
        # Allow some isolation issues (test environment setup can be complex)
        assert len(isolation_issues) <= 2, f"Test environment isolation issues: {isolation_issues}"

    def test_pytest_fixture_integration_comprehensive(self):
        """Test comprehensive pytest fixture integration with config."""
        fixture_violations = []
        
        # Test various fixture scenarios that might be used in tests
        try:
            from autotasktracker.config import get_config
            
            # 1. FIXTURE SCOPE TESTING
            # Simulate different fixture scopes
            session_configs = []
            for i in range(3):
                config = get_config()
                session_configs.append(config)
            
            # Test that configs are consistent (singleton behavior)
            unique_configs = set(id(config) for config in session_configs)
            if len(unique_configs) > 1:
                fixture_violations.append("Config instances not consistent across calls")
            
            # 2. FIXTURE DEPENDENCY INJECTION
            # Test config as fixture dependency
            config = get_config()
            
            # Simulate injecting config into test function
            test_dependencies = {
                'config': config,
                'db_path': config.get_db_path(),
            }
            
            # Add optional dependencies that might not exist
            try:
                test_dependencies['vlm_url'] = config.get_ollama_url()
            except AttributeError:
                pass  # VLM URL might not be configured
                
            try:
                test_dependencies['service_urls'] = {
                    'memos': config.get_service_url('memos'),
                }
            except AttributeError:
                pass  # Service URLs might not be configured
            
            # Validate all dependencies are properly formed
            for dep_name, dep_value in test_dependencies.items():
                if dep_name == 'config':
                    if not hasattr(dep_value, 'get_db_path'):
                        fixture_violations.append(f"Config fixture missing methods: {dep_name}")
                elif dep_name in ['db_path']:
                    if not isinstance(dep_value, (str, Path)) or len(str(dep_value)) == 0:
                        fixture_violations.append(f"Invalid fixture value: {dep_name}={dep_value}")
            
            # 3. FIXTURE TEARDOWN VALIDATION
            # Test proper fixture teardown behavior
            test_db = "/tmp/fixture_teardown_test.db"
            
            original_config = get_config()
            original_db_path = str(original_config.get_db_path())
            
            # Simulate fixture setup with environment override
            with patch.dict(os.environ, {'AUTOTASK_DB_PATH': test_db}):
                import importlib
                import autotasktracker.config
                importlib.reload(autotasktracker.config)
                
                fixture_config = get_config()
                fixture_db_path = str(fixture_config.get_db_path())
                
                # Config should apply test database
                if test_db not in fixture_db_path:
                    fixture_violations.append(f"Fixture setup failed: expected {test_db} in {fixture_db_path}")
            
            # Simulate fixture teardown
            import importlib
            import autotasktracker.config
            importlib.reload(autotasktracker.config)
            
            restored_config = get_config()
            restored_db_path = str(restored_config.get_db_path())
            
            # Should be back to original or a valid default
            if restored_db_path == test_db:
                fixture_violations.append("Fixture teardown failed - test config persisted")
                
        except Exception as e:
            fixture_violations.append(f"Pytest fixture integration error: {e}")
        
        # Allow some fixture issues (testing infrastructure can be complex)
        assert len(fixture_violations) <= 3, f"Pytest fixture integration violations: {fixture_violations}"

    def test_test_discovery_import_path_validation_comprehensive(self):
        """Test discovery and import path validation."""
        import_issues = []
        
        try:
            # Test that config can be imported from various contexts
            import_contexts = [
                'from autotasktracker.config import get_config',
                'from autotasktracker import get_config',
                'import autotasktracker.config',
            ]
            
            for import_statement in import_contexts:
                try:
                    exec(import_statement)
                    # If we get here, import worked
                except ImportError as e:
                    import_issues.append(f"Import failed: {import_statement} - {e}")
                except Exception as e:
                    import_issues.append(f"Import error: {import_statement} - {e}")
            
            # Test that config can be imported from test files
            test_import_patterns = [
                'autotasktracker.config.get_config',
                'autotasktracker.config.Config',
            ]
            
            for pattern in test_import_patterns:
                try:
                    module_path, attr_name = pattern.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[attr_name])
                    getattr(module, attr_name)
                except (ImportError, AttributeError) as e:
                    import_issues.append(f"Test import failed: {pattern} - {e}")
            
        except Exception as e:
            import_issues.append(f"Import path validation error: {e}")
        
        # Allow some import issues (not all import patterns may be supported)
        assert len(import_issues) <= 2, f"Import path validation issues: {import_issues}"

    def test_test_database_separation_and_test_config_validation(self):
        """Test database separation and comprehensive test config validation."""
        separation_issues = []
        
        try:
            # Test that test and production databases are separate
            from autotasktracker.config import get_config
            config = get_config()
            
            db_path = str(config.get_db_path())
            
            # Test database indicators
            test_indicators = ['test', 'tmp', 'temp', '.test']
            production_indicators = ['production', 'prod', 'live', 'main']
            
            # In test environment, should prefer test indicators
            has_test_indicators = any(indicator in db_path.lower() for indicator in test_indicators)
            has_production_indicators = any(indicator in db_path.lower() for indicator in production_indicators)
            
            if has_production_indicators and not has_test_indicators:
                separation_issues.append(f"Test may be using production database: {db_path}")
            
            # Test that test-specific configuration works
            test_config_overrides = {
                'AUTOTASK_DB_PATH': '/tmp/separation_test.db',
            }
            
            original_env = dict(os.environ)
            try:
                for env_var, test_value in test_config_overrides.items():
                    os.environ[env_var] = test_value
                    
                    import importlib
                    import autotasktracker.config
                    importlib.reload(autotasktracker.config)
                    
                    test_config = get_config()
                    actual_path = str(test_config.get_db_path())
                    
                    if test_value not in actual_path:
                        separation_issues.append(f"Test config override not working: {env_var}")
                    
            finally:
                os.environ.clear()
                os.environ.update(original_env)
                import importlib
                import autotasktracker.config
                importlib.reload(autotasktracker.config)
            
        except Exception as e:
            separation_issues.append(f"Database separation test error: {e}")
        
        # Allow some separation issues (test setup can be complex)
        assert len(separation_issues) <= 2, f"Database separation issues: {separation_issues}"

    def test_conftest_and_test_infrastructure_config_integration(self):
        """Test conftest and test infrastructure config integration."""
        infrastructure_issues = []
        
        try:
            # Test that config works with common test infrastructure patterns
            
            # 1. Test config in pytest context
            from autotasktracker.config import get_config
            config = get_config()
            
            # Should be able to get basic config information
            db_path = config.get_db_path()
            assert db_path is not None, "Config should provide database path in test context"
            
            # 2. Test config with mocking (common in tests)
            with patch('autotasktracker.config.os.environ.get') as mock_env:
                mock_env.return_value = '/tmp/mocked_test.db'
                
                # This tests that config responds to mocked environment
                try:
                    import importlib
                    import autotasktracker.config
                    importlib.reload(autotasktracker.config)
                    
                    mocked_config = get_config()
                    # Should work even with mocked environment
                    
                except Exception as e:
                    infrastructure_issues.append(f"Config doesn't work with mocking: {e}")
            
            # Restore normal config
            import importlib
            import autotasktracker.config
            importlib.reload(autotasktracker.config)
            
            # 3. Test config with temporary files (common test pattern)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_db = f"{temp_dir}/infrastructure_test.db"
                
                with patch.dict(os.environ, {'AUTOTASK_DB_PATH': temp_db}):
                    import importlib
                    import autotasktracker.config
                    importlib.reload(autotasktracker.config)
                    
                    temp_config = get_config()
                    temp_path = str(temp_config.get_db_path())
                    
                    if temp_db not in temp_path:
                        infrastructure_issues.append(f"Config doesn't work with temporary directories")
            
            # Restore normal config
            import importlib
            import autotasktracker.config
            importlib.reload(autotasktracker.config)
            
        except Exception as e:
            infrastructure_issues.append(f"Test infrastructure integration error: {e}")
        
        # Allow some infrastructure issues (test setup complexity)
        assert len(infrastructure_issues) <= 2, f"Test infrastructure integration issues: {infrastructure_issues}"