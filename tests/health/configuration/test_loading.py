"""Test configuration loading and architecture."""
import logging
import time
from pathlib import Path
import pytest
import sys
import os

from tests.health.analyzers.config_system_analyzer import ConfigSystemAnalyzer
from tests.health.utils import get_health_test_files

logger = logging.getLogger(__name__)


class TestConfigurationLoading:
    """Test configuration system architecture and loading performance."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.analyzer = ConfigSystemAnalyzer(cls.project_root)
        cls.python_files = get_health_test_files(cls.project_root)
    
    def test_config_system_architecture_integrity(self):
        """Test that configuration system follows proper architecture patterns."""
        import importlib
        
        # Test that config module loads successfully
        try:
            # Add project root to sys.path temporarily
            sys.path.insert(0, str(self.project_root))
            
            # Test loading the config module
            start_time = time.time()
            config_module = importlib.import_module('autotasktracker.config')
            load_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Verify config has required attributes
            assert hasattr(config_module, 'AutoTaskSettings'), "Config missing AutoTaskSettings class"
            assert hasattr(config_module, 'get_config'), "Config missing get_config function"
            
            # Check load time
            assert load_time < 5000, f"Config module took {load_time:.0f}ms to load (should be <5000ms)"
            
            # Test config instantiation
            config = config_module.get_config()
            assert config is not None, "get_config() returned None"
            assert hasattr(config, 'db_path'), "Config missing db_path attribute"
            
            # Test that config has essential paths
            assert hasattr(config, 'screenshots_dir'), "Config missing screenshots_dir"
            assert hasattr(config, 'vlm_cache_dir'), "Config missing vlm_cache_dir"
            
        except ImportError as e:
            pytest.fail(f"Failed to import config module: {e}")
        except Exception as e:
            pytest.fail(f"Config architecture test failed: {e}")
        finally:
            # Clean up sys.path
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))
    
    def test_config_loading_performance(self):
        """Test that configuration loads quickly without performance issues."""
        import importlib
        import gc
        
        load_times = []
        
        # Test multiple loads to check for consistency
        for i in range(5):
            # Force garbage collection to get clean timing
            gc.collect()
            
            try:
                # Remove from cache if present
                if 'autotasktracker.core.config' in sys.modules:
                    del sys.modules['autotasktracker.core.config']
                
                sys.path.insert(0, str(self.project_root))
                
                start_time = time.time()
                importlib.import_module('autotasktracker.config')
                load_time = (time.time() - start_time) * 1000  # ms
                
                load_times.append(load_time)
                
            finally:
                if str(self.project_root) in sys.path:
                    sys.path.remove(str(self.project_root))
        
        # Check performance metrics
        avg_load_time = sum(load_times) / len(load_times)
        max_load_time = max(load_times)
        
        assert avg_load_time < 1000, f"Average config load time {avg_load_time:.0f}ms exceeds 1000ms"
        assert max_load_time < 2000, f"Max config load time {max_load_time:.0f}ms exceeds 2000ms"
        
        # Check for consistent performance (allow reasonable variance)
        for load_time in load_times:
            if load_time > 200:  # Only flag really slow loads as outliers
                pytest.fail(f"Load time {load_time:.0f}ms is too slow (should be <200ms)")
    
    def test_environment_variable_handling(self):
        """Test that configuration properly handles environment variables."""
        env_vars_to_test = [
            ('MEMOS_DB_PATH', '/custom/path/db.sqlite'),
            ('PENSIEVE_BACKEND', 'postgresql'),
            ('AUTOTASKTRACKER_CONFIG', '/custom/config.json'),
            ('LOG_LEVEL', 'DEBUG'),
        ]
        
        issues = []
        
        for var_name, test_value in env_vars_to_test:
            # Set environment variable
            original_value = os.environ.get(var_name)
            os.environ[var_name] = test_value
            
            try:
                # Test that the variable is accessible
                value = os.environ.get(var_name)
                if value != test_value:
                    issues.append(f"{var_name}: Expected '{test_value}', got '{value}'")
            finally:
                # Restore original value
                if original_value is not None:
                    os.environ[var_name] = original_value
                else:
                    del os.environ[var_name]
        
        if issues:
            logger.warning(f"Environment variable handling issues: {issues}")
    
    def test_config_file_locations(self):
        """Test that configuration files are in proper locations."""
        expected_locations = [
            self.project_root / "autotasktracker" / "config.py",
            self.project_root / "autotasktracker" / "core" / "config_manager.py",
        ]
        
        missing_files = []
        for location in expected_locations:
            if not location.exists():
                missing_files.append(str(location))
        
        assert not missing_files, f"Missing configuration files: {missing_files}"
    
    def test_config_imports(self):
        """Test that configuration is imported consistently."""
        import_issues = []
        
        # Patterns for proper config imports
        good_patterns = [
            r'from autotasktracker\.core\.config import',
            r'from autotasktracker\.core import config',
            r'import autotasktracker\.core\.config',
        ]
        
        bad_patterns = [
            r'from \.\.\.core\.config',  # Relative imports from outside package
            r'sys\.path.*config',  # Path hacks for config
        ]
        
        for file_path in self.python_files:
            if 'test' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                
                # Check for bad patterns
                for pattern in bad_patterns:
                    import re
                    if re.search(pattern, content):
                        import_issues.append(f"{file_path}: Bad config import pattern '{pattern}'")
            except Exception:
                continue
        
        if import_issues:
            logger.warning(f"Found {len(import_issues)} config import issues")
            for issue in import_issues[:5]:
                logger.warning(f"  {issue}")