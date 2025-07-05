"""
Configuration synchronization health tests.

Tests synchronization between different configuration systems,
runtime consistency, and environment variable overrides.
"""

import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
import logging

from tests.health.analyzers.config_system_analyzer import ConfigSystemAnalyzer

logger = logging.getLogger(__name__)


class TestConfigSyncHealth:
    """Configuration synchronization and consistency health checks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.analyzer = ConfigSystemAnalyzer(cls.project_root)
        
    def test_config_synchronization_integrity(self):
        """Test synchronization between different configuration systems."""
        results = self.analyzer.analyze_config_synchronization()
        
        sync_issues = results['consistency_issues']
        
        if not results['sync_status'] or sync_issues:
            error_msg = f"""
🚨 CONFIGURATION SYNCHRONIZATION ISSUES 🚨

Sync Status: {'✅' if results['sync_status'] else '❌'}

"""
            if sync_issues:
                error_msg += f"Synchronization issues found:\n"
                error_msg += chr(10).join(f'  ❌ {issue}' for issue in sync_issues)
                error_msg += "\n"
                
            error_msg += f"""
📊 PENSIEVE STATUS:
{chr(10).join(f'  • {k}: {v}' for k, v in results['pensieve_status'].items())}

🔄 SYNC CONFIGURATION:
  Expected keys: {len(results['expected_keys'])}
  Actual keys: {len(results['sync_config'])}
  
"""
            if results['sync_config']:
                error_msg += "  Synchronized values:\n"
                for key, value in results['sync_config'].items():
                    error_msg += f"    • {key}: {value}\n"
                    
            error_msg += """
✅ SYNCHRONIZATION REQUIREMENTS:
  - Pensieve service must be responsive
  - All expected config keys must be present
  - Database paths must be consistent
  - Configuration sync must complete successfully

🔧 TROUBLESHOOTING:
  - Check Pensieve service status: memos ps
  - Verify configuration file permissions
  - Ensure database paths are accessible
  - Check network connectivity for API calls
"""
            raise AssertionError(error_msg)
            
    def test_runtime_config_consistency(self):
        """Test that runtime configuration remains consistent across operations."""
        from autotasktracker.config import get_config, Config
        
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
            
        if consistency_issues:
            error_msg = f"""
🚨 RUNTIME CONFIGURATION CONSISTENCY ISSUES 🚨

Found {len(consistency_issues)} consistency issues:

{chr(10).join(f'  ❌ {issue}' for issue in consistency_issues)}

✅ CONSISTENCY REQUIREMENTS:
  - Config instances should use singleton pattern
  - Database paths must remain consistent
  - Critical attributes must not change during runtime
  - Configuration state must be thread-safe

🔧 FIXES:
  - Implement proper singleton pattern
  - Use immutable configuration objects
  - Add thread-safety mechanisms
  - Validate configuration state consistency
"""
            raise AssertionError(error_msg)
            
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
            
        if override_issues:
            error_msg = f"""
🚨 ENVIRONMENT VARIABLE OVERRIDE ISSUES 🚨

Found {len(override_issues)} override issues:

{chr(10).join(f'  ❌ {issue}' for issue in override_issues)}

✅ OVERRIDE REQUIREMENTS:
  - Environment variables must override config defaults
  - Changes must be reflected immediately after reload
  - All critical config values must be overrideable
  - Override mechanism must be reliable

🔧 ENVIRONMENT VARIABLES TO TEST:
  - AUTOTASK_DB_PATH: Database file path
  - AUTOTASK_SCREENSHOTS_DIR: Screenshots directory  
  - AUTOTASK_VLM_PORT: VLM service port
  - AUTOTASK_MEMOS_DIR: Memos data directory

💡 DEBUGGING:
  - Check environment variable parsing logic
  - Verify config loading order (env vars vs defaults)
  - Test with different data types (strings, integers, booleans)
  - Ensure proper cleanup after environment changes
"""
            raise AssertionError(error_msg)
            
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
            
            for indicator in production_indicators:
                if indicator in db_path.lower():
                    isolation_issues.append(f"Test config may be using production path: {db_path}")
                    break
                    
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
            
        if isolation_issues:
            error_msg = f"""
🚨 TEST ENVIRONMENT ISOLATION ISSUES 🚨

Found {len(isolation_issues)} isolation issues:

{chr(10).join(f'  ❌ {issue}' for issue in isolation_issues)}

✅ ISOLATION REQUIREMENTS:
  - Test configuration must not affect production
  - Temporary configurations must work correctly
  - Configuration cleanup must be complete
  - Test databases must be separate from production

🧪 TEST SAFETY:
  - Use temporary directories for test data
  - Mock environment variables properly
  - Clean up after each test
  - Verify configuration restoration

💡 BEST PRACTICES:
  - Use pytest fixtures for config isolation
  - Implement proper teardown mechanisms
  - Use separate test configuration files
  - Validate configuration state before/after tests
"""
            raise AssertionError(error_msg)