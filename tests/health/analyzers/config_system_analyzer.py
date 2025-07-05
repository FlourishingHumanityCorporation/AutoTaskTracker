"""
Configuration System Analyzer for health testing.

Provides comprehensive analysis of configuration system integrity,
security, synchronization, and performance.
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
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ConfigSystemAnalyzer:
    """Analyzer for configuration system health and integrity."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.package_dir = project_root / "autotasktracker"
        
    def analyze_architecture_integrity(self) -> Dict[str, Any]:
        """Analyze configuration system architecture integrity."""
        from autotasktracker.config import config, get_config, Config
        from autotasktracker.pensieve.config_reader import (
            PensieveConfigReader, 
            get_pensieve_config_reader,
            get_pensieve_config,
            PensieveConfig
        )
        
        results = {
            'main_config_valid': False,
            'pensieve_config_valid': False,
            'config_attributes': [],
            'load_time_ms': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            # Test main config loading
            main_config = get_config()
            if isinstance(main_config, Config):
                results['main_config_valid'] = True
                results['config_attributes'] = [
                    attr for attr in dir(main_config) 
                    if not attr.startswith('_')
                ]
                
                # Check critical attributes
                critical_attrs = ['DB_PATH', 'get_db_path']
                for attr in critical_attrs:
                    if not hasattr(main_config, attr):
                        results['errors'].append(f"Config missing critical attribute: {attr}")
            
            # Test Pensieve config loading with timeout
            pensieve_reader = get_pensieve_config_reader()
            if isinstance(pensieve_reader, PensieveConfigReader):
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Pensieve config loading timeout")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(2)  # 2 second timeout
                
                try:
                    pensieve_config = get_pensieve_config()
                    signal.alarm(0)  # Cancel alarm
                    if isinstance(pensieve_config, PensieveConfig):
                        results['pensieve_config_valid'] = True
                except TimeoutError:
                    results['errors'].append("Pensieve config loading timeout (>2s)")
                    signal.alarm(0)
                except Exception as e:
                    results['errors'].append(f"Pensieve config loading error: {e}")
                    signal.alarm(0)
                    
        except Exception as e:
            results['errors'].append(f"Config architecture error: {e}")
            
        results['load_time_ms'] = (time.time() - start_time) * 1000
        return results
        
    def analyze_environment_variable_security(self) -> Dict[str, Any]:
        """Analyze environment variable handling for security."""
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
        
        results = {
            'security_issues': [],
            'current_env_vars': {},
            'sensitive_patterns': [],
            'validation_results': {}
        }
        
        # Store original environment
        original_env = dict(os.environ)
        
        try:
            # Check for sensitive data patterns
            sensitive_patterns = [
                r'password', r'secret', r'key', r'token', 
                r'credential', r'auth', r'api_key'
            ]
            
            for var_name, var_value in os.environ.items():
                if any(re.search(pattern, var_name.lower()) for pattern in sensitive_patterns):
                    if var_value and len(var_value) > 3:  # Non-empty sensitive var
                        results['sensitive_patterns'].append({
                            'var': var_name,
                            'length': len(var_value),
                            'masked_value': var_value[:3] + '***'
                        })
                        
                # Track config-related env vars
                if var_name.startswith(('AUTOTASK_', 'MEMOS_')):
                    results['current_env_vars'][var_name] = var_value
            
            # Test environment variable validation
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
                    results['validation_results'][var] = 'loaded_successfully'
                    
                except Exception as e:
                    results['validation_results'][var] = f'error: {e}'
                    results['security_issues'].append(f"Env var {var} caused config error: {e}")
                
                # Clean up
                if var in os.environ:
                    del os.environ[var]
                    
        except Exception as e:
            results['security_issues'].append(f"Environment analysis error: {e}")
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            
        return results
        
    def analyze_config_synchronization(self) -> Dict[str, Any]:
        """Analyze configuration synchronization between systems."""
        results = {
            'sync_status': False,
            'pensieve_status': {},
            'sync_config': {},
            'consistency_issues': [],
            'expected_keys': []
        }
        
        try:
            from autotasktracker.pensieve.config_reader import get_pensieve_config_reader
            from autotasktracker.config import get_config
            
            pensieve_reader = get_pensieve_config_reader()
            
            # Test memos service status detection
            status = pensieve_reader.get_memos_status()
            if isinstance(status, dict):
                results['pensieve_status'] = status
                if 'running' in status and isinstance(status['running'], bool):
                    results['sync_status'] = True
                    
            # Test configuration synchronization
            sync_config = pensieve_reader.sync_autotasktracker_config()
            if isinstance(sync_config, dict):
                results['sync_config'] = sync_config
                
                # Validate synchronized values
                expected_sync_keys = [
                    'DB_PATH', 'SCREENSHOTS_DIR', 'SCREENSHOT_INTERVAL_SECONDS',
                    'MEMOS_PORT', 'PENSIEVE_API_URL', 'PENSIEVE_WEB_URL'
                ]
                results['expected_keys'] = expected_sync_keys
                
                for key in expected_sync_keys:
                    if key not in sync_config:
                        results['consistency_issues'].append(f"Sync config missing {key}")
                    elif sync_config[key] is None:
                        results['consistency_issues'].append(f"Sync config {key} is None")
                        
                # Test database path consistency
                if 'DB_PATH' in sync_config:
                    main_config = get_config()
                    main_db_path = str(main_config.get_db_path())
                    sync_db_path = str(sync_config['DB_PATH'])
                    
                    if main_db_path != sync_db_path:
                        results['consistency_issues'].append(
                            f"DB path mismatch: main={main_db_path}, sync={sync_db_path}"
                        )
                        
        except Exception as e:
            results['consistency_issues'].append(f"Synchronization analysis error: {e}")
            
        return results
        
    def analyze_performance_reliability(self) -> Dict[str, Any]:
        """Analyze configuration system performance and reliability."""
        results = {
            'load_times': {},
            'memory_usage': {},
            'reliability_score': 0,
            'performance_issues': []
        }
        
        try:
            import tracemalloc
            import gc
            from autotasktracker.config import get_config
            
            # Test multiple config loading cycles for performance
            load_times = []
            for i in range(5):
                tracemalloc.start()
                start_time = time.time()
                
                config = get_config()
                _ = config.get_db_path()
                
                load_time = (time.time() - start_time) * 1000
                load_times.append(load_time)
                
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                if i == 0:  # First load
                    results['memory_usage']['first_load'] = {
                        'current_kb': current / 1024,
                        'peak_kb': peak / 1024
                    }
                    
                gc.collect()
                
            results['load_times'] = {
                'average_ms': sum(load_times) / len(load_times),
                'min_ms': min(load_times),
                'max_ms': max(load_times),
                'all_times': load_times
            }
            
            # Performance thresholds
            avg_time = results['load_times']['average_ms']
            if avg_time > 100:
                results['performance_issues'].append(f"Slow config loading: {avg_time:.1f}ms average")
            if max(load_times) > 500:
                results['performance_issues'].append(f"Inconsistent load times: max {max(load_times):.1f}ms")
                
            # Calculate reliability score
            time_variance = max(load_times) - min(load_times)
            if time_variance < 10:
                results['reliability_score'] = 100
            elif time_variance < 50:
                results['reliability_score'] = 80
            else:
                results['reliability_score'] = 60
                
        except Exception as e:
            results['performance_issues'].append(f"Performance analysis error: {e}")
            
        return results
        
    def analyze_config_integration(self) -> Dict[str, Any]:
        """Analyze configuration integration with other systems."""
        results = {
            'database_integration': False,
            'api_integration': False,
            'service_integration': False,
            'integration_issues': []
        }
        
        try:
            from autotasktracker.config import get_config
            from autotasktracker.core.database import DatabaseManager
            
            config = get_config()
            
            # Test database integration
            try:
                db_manager = DatabaseManager()
                db_path = config.get_db_path()
                
                if db_path and Path(db_path).exists():
                    results['database_integration'] = True
                else:
                    results['integration_issues'].append(f"Database path not accessible: {db_path}")
                    
            except Exception as e:
                results['integration_issues'].append(f"Database integration error: {e}")
                
            # Test API integration
            try:
                from autotasktracker.pensieve.api_client import get_pensieve_client
                
                client = get_pensieve_client()
                if hasattr(client, 'base_url'):
                    results['api_integration'] = True
                    
            except Exception as e:
                results['integration_issues'].append(f"API integration error: {e}")
                
            # Test service integration
            try:
                from autotasktracker.pensieve.config_reader import get_pensieve_config_reader
                
                reader = get_pensieve_config_reader()
                status = reader.get_memos_status()
                
                if isinstance(status, dict) and 'running' in status:
                    results['service_integration'] = True
                    
            except Exception as e:
                results['integration_issues'].append(f"Service integration error: {e}")
                
        except Exception as e:
            results['integration_issues'].append(f"Integration analysis error: {e}")
            
        return results
        
    def analyze_security_hardening(self) -> Dict[str, Any]:
        """Analyze configuration security hardening."""
        results = {
            'security_score': 0,
            'hardcoded_values': [],
            'insecure_patterns': [],
            'recommendations': []
        }
        
        try:
            # Scan for hardcoded configuration values
            config_files = [
                self.package_dir / "config.py",
                self.package_dir / "pensieve" / "config_reader.py"
            ]
            
            insecure_patterns = [
                (r'password\s*=\s*["\'][^"\']*["\']', 'hardcoded password'),
                (r'secret\s*=\s*["\'][^"\']*["\']', 'hardcoded secret'),
                (r'key\s*=\s*["\'][^"\']*["\']', 'hardcoded key'),
                (r'token\s*=\s*["\'][^"\']*["\']', 'hardcoded token'),
                (r'localhost', 'localhost reference'),
                (r'127\.0\.0\.1', 'hardcoded localhost IP'),
                (r':\d{4,5}', 'hardcoded port')
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    content = config_file.read_text()
                    
                    for pattern, description in insecure_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            results['insecure_patterns'].append({
                                'file': str(config_file.relative_to(self.project_root)),
                                'pattern': description,
                                'matches': len(matches)
                            })
                            
            # Calculate security score
            total_issues = len(results['insecure_patterns'])
            if total_issues == 0:
                results['security_score'] = 100
            elif total_issues <= 2:
                results['security_score'] = 80
            elif total_issues <= 5:
                results['security_score'] = 60
            else:
                results['security_score'] = 40
                
            # Generate recommendations
            if results['insecure_patterns']:
                results['recommendations'].append("Move hardcoded values to environment variables")
                results['recommendations'].append("Use configuration validation")
                results['recommendations'].append("Implement secrets management")
                
        except Exception as e:
            results['insecure_patterns'].append({'error': f"Security analysis error: {e}"})
            
        return results