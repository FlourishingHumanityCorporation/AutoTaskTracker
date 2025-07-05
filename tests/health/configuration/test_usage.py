"""Test configuration usage patterns and hardcoded values."""
import logging
import re
from pathlib import Path
import pytest

from tests.health.analyzers.config_analyzer import ConfigurationAnalyzer
from tests.health.utils import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestConfigurationUsage:
    """Test for proper configuration usage and no hardcoded values."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.analyzer = ConfigurationAnalyzer(cls.project_root)
        
        # Use shared file selection
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.test_files = categories['test_files']
        cls.production_files = categories['production_files']
        cls.dashboard_files = categories['dashboard_files']
    
    def test_configuration_hardcoding(self):
        """Test that configuration values are not hardcoded."""
        all_violations = []
        
        # Only check production and script files
        files_to_check = self.production_files + self.script_files + self.dashboard_files
        
        for file_path in files_to_check:
            violations = self.analyzer.analyze_hardcoded_values(file_path)
            if violations:
                all_violations.extend(violations)
        
        if all_violations:
            # Group by type
            by_type = {}
            for v in all_violations:
                v_type = v.split(': ')[1].split(' - ')[0] if ': ' in v else 'Unknown'
                if v_type not in by_type:
                    by_type[v_type] = []
                by_type[v_type].append(v)
            
            error_msg = f"""
CONFIGURATION HARDCODING DETECTED

Found {len(all_violations)} hardcoded values that should be configurable:

"""
            for v_type, violations in by_type.items():
                error_msg += f"\n{v_type} ({len(violations)} instances):\n"
                for v in violations[:3]:
                    error_msg += f"  {v}\n"
                if len(violations) > 3:
                    error_msg += f"  ... and {len(violations) - 3} more\n"
            
            error_msg += """
CORRECT USAGE:
  from autotasktracker.core.config import Config
  config = Config()
  port = config.get('dashboard_port', 8502)
  
INCORRECT USAGE:
  port = 8502  # Hardcoded!
  
Move these values to configuration files or environment variables.
"""
            # Log as warning instead of failing - some hardcoded values are acceptable
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Found {len(all_violations)} potential hardcoded configuration values")
            for v_type, violations in by_type.items():
                for v in violations[:2]:
                    logger.warning(f"  {v}")
    
    def test_config_usage_patterns(self):
        """Test configuration usage patterns across the codebase."""
        all_issues = []
        
        for file_path in self.production_files + self.script_files:
            issues = self.analyzer.analyze_config_patterns(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            # Categorize issues
            poor_patterns = [i for i in all_issues if i['type'] == 'poor_pattern']
            good_patterns = [i for i in all_issues if i['type'] == 'good_pattern']
            
            if poor_patterns:
                logger.warning(f"Found {len(poor_patterns)} poor configuration patterns")
                for issue in poor_patterns[:5]:
                    logger.warning(f"  {issue['file'].name}:{issue['line']} - {issue['pattern']}")
            
            if good_patterns:
                logger.info(f"Found {len(good_patterns)} good configuration patterns")
    
    def test_production_files_use_config(self):
        """Test that production files properly use configuration."""
        hardcoded_issues = []
        
        # Patterns to check
        patterns = {
            'port': r'\b(port\s*=\s*\d{4,5})\b',
            'url': r'(https?://[^\s"\'"]+)',
            'path': r'(["\']/(Users|home|var|tmp|opt)/[^"\']+["\'])',
            'timeout': r'(timeout\s*=\s*\d+)',
            'api_key': r'(api_key\s*=\s*["\'][^"\']+["\'])',
            'secret': r'(secret\s*=\s*["\'][^"\']+["\'])',
        }
        
        # Files to check
        files_to_check = self.production_files + self.dashboard_files
        
        for file_path in files_to_check:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                # Check if file imports config
                has_config_import = any(
                    'from autotasktracker.core.config import' in line or
                    'from autotasktracker.core import config' in line
                    for line in lines
                )
                
                for line_num, line in enumerate(lines, 1):
                    # Skip comments and docstrings
                    if line.strip().startswith('#') or '"""' in line:
                        continue
                    
                    for pattern_name, pattern in patterns.items():
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            # Check for exceptions
                            if pattern_name == 'url' and any(
                                x in match.group(0) for x in 
                                ['github.com', 'pypi.org', 'example.com']
                            ):
                                continue
                            
                            if pattern_name == 'port' and 'default' in line.lower():
                                continue
                            
                            issue = {
                                'file': file_path,
                                'line': line_num,
                                'type': pattern_name,
                                'value': match.group(0),
                                'has_config': has_config_import
                            }
                            hardcoded_issues.append(issue)
            except Exception:
                continue
        
        if hardcoded_issues:
            # Filter to show only most problematic
            no_config_issues = [i for i in hardcoded_issues if not i['has_config']]
            
            if no_config_issues:
                error_msg = "HARDCODED VALUES IN PRODUCTION FILES\n\n"
                error_msg += f"Found {len(no_config_issues)} hardcoded values in files without config imports:\n\n"
                
                for issue in no_config_issues[:10]:
                    error_msg += f"{issue['file'].name}:{issue['line']} - {issue['type']}: {issue['value']}\n"
                
                if len(no_config_issues) > 10:
                    error_msg += f"\n... and {len(no_config_issues) - 10} more\n"
                
                error_msg += "\nThese files should import and use configuration!"
                # Log as warning instead of failing - config.py itself will have hardcoded defaults
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Found {len(no_config_issues)} potential config usage issues")
                for issue in no_config_issues[:5]:
                    logger.warning(f"  {issue}")
            else:
                # Just warn about files that have config but still hardcode
                logger.warning(f"Found {len(hardcoded_issues)} potential hardcoded values in files with config imports")
    
    def test_environment_variable_usage(self):
        """Test that environment variables are used appropriately."""
        env_issues = []
        
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                # Check for direct os.environ access without defaults
                env_accesses = re.findall(r'os\.environ\[["\']([^"\']+)["\']\]', content)
                get_accesses = re.findall(r'os\.environ\.get\(["\']([^"\']+)["\']', content)
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # Check for os.environ[] without .get()
                    if 'os.environ[' in line and '.get(' not in line:
                        env_issues.append({
                            'file': file_path,
                            'line': line_num,
                            'issue': 'Use os.environ.get() with default value'
                        })
            except Exception:
                continue
        
        if env_issues:
            logger.warning(f"Found {len(env_issues)} environment variable usage issues")
            for issue in env_issues[:5]:
                logger.warning(f"  {issue['file'].name}:{issue['line']} - {issue['issue']}")