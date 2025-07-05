"""Test configuration management patterns."""
import logging
from pathlib import Path
import pytest

from tests.health.analyzers.config_analyzer import ConfigurationAnalyzer
from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestConfigurationManagement:
    """Test for configuration management best practices."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.analyzer = ConfigurationAnalyzer(cls.project_root)
        
        # Use shared file selection
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files
        categories = categorize_files(cls.python_files)
        cls.production_files = categories['production_files']
        cls.dashboard_files = categories['dashboard_files']
    
    def test_config_centralization(self):
        """Test that configuration is centralized and not scattered."""
        config_locations = []
        
        # Look for files that define configuration
        for file_path in self.python_files:
            try:
                content = file_path.read_text()
                
                # Check for config-like patterns
                if any(pattern in content for pattern in [
                    'CONFIG =', 'SETTINGS =', 'config = {',
                    'settings = {', 'PORT =', 'DATABASE_URL =',
                    'API_KEY =', 'SECRET_KEY ='
                ]):
                    # Skip if it's importing from central config
                    if 'from autotasktracker.config' not in content:
                        config_locations.append(file_path)
            except Exception:
                continue
        
        # Filter out test files and the main config files
        scattered_configs = [
            f for f in config_locations
            if 'test' not in str(f) and 
            'config.py' not in f.name and
            'config_manager.py' not in f.name
        ]
        
        if scattered_configs:
            error_msg = f"""
SCATTERED CONFIGURATION DETECTED

Found {len(scattered_configs)} files with configuration outside of core config module:

{chr(10).join(f'  {f.relative_to(self.project_root)}' for f in scattered_configs[:10])}
{f'  ... and {len(scattered_configs) - 10} more' if len(scattered_configs) > 10 else ''}

All configuration should be centralized in:
  - autotasktracker/config.py
  - autotasktracker/core/config_manager.py

Other files should import from these modules.
"""
            raise AssertionError(error_msg)
    
    def test_config_security(self):
        """Test that sensitive configuration is handled securely."""
        security_issues = []
        
        sensitive_patterns = [
            ('password', r'password\s*=\s*["\'][^"\']+["\']'),
            ('api_key', r'api_key\s*=\s*["\'][^"\']+["\']'),
            ('secret', r'secret\s*=\s*["\'][^"\']+["\']'),
            ('token', r'token\s*=\s*["\'][^"\']+["\']'),
            ('credential', r'credential\s*=\s*["\'][^"\']+["\']'),
        ]
        
        for file_path in self.production_files + self.dashboard_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                    
                    for name, pattern in sensitive_patterns:
                        import re
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if it's a placeholder
                            if any(placeholder in line for placeholder in [
                                'your-', 'example', 'dummy', 'test',
                                '<', 'xxx', '...', 'changeme'
                            ]):
                                continue
                            
                            security_issues.append({
                                'file': file_path,
                                'line': line_num,
                                'type': name,
                                'content': line.strip()[:50] + '...'
                            })
            except Exception:
                continue
        
        if security_issues:
            logger.warning(f"SECURITY: Found {len(security_issues)} potential sensitive values in code")
            for issue in security_issues[:5]:
                logger.warning(f"  {issue['file'].name}:{issue['line']} - {issue['type']}")
            logger.warning("Use environment variables or secure vaults for sensitive configuration!")
    
    def test_config_defaults(self):
        """Test that configuration has sensible defaults."""
        files_without_defaults = []
        
        config_files = [
            f for f in self.python_files 
            if 'config' in f.name and f.name.endswith('.py')
        ]
        
        for file_path in config_files:
            try:
                content = file_path.read_text()
                
                # Check for default value patterns
                has_defaults = any(pattern in content for pattern in [
                    'default=', 'defaults=', 'DEFAULT',
                    '.get(', 'or ', 'if None',
                    'fallback=', 'default_'
                ])
                
                if not has_defaults and 'test' not in str(file_path):
                    files_without_defaults.append(file_path)
            except Exception:
                continue
        
        if files_without_defaults:
            logger.info("Config files that may lack default values:")
            for f in files_without_defaults:
                logger.info(f"  {f.name}")
    
    def test_config_type_safety(self):
        """Test that configuration values are type-checked."""
        type_issues = []
        
        # Check ConfigManager for type checking
        config_manager = self.project_root / "autotasktracker" / "core" / "config_manager.py"
        
        if config_manager.exists():
            content = config_manager.read_text()
            
            # Look for type checking patterns
            type_checks = [
                'isinstance(', 'type(', 'int(', 'str(', 'bool(',
                'float(', 'Path(', 'typing', 'TypedDict',
                ': int', ': str', ': bool', ': float'
            ]
            
            has_type_checking = any(check in content for check in type_checks)
            
            if not has_type_checking:
                type_issues.append("ConfigManager lacks type checking")
        
        # Check for common type conversion issues
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                # Look for unsafe type conversions
                import re
                unsafe_patterns = [
                    (r'int\([^)]*\)', 'int() without try/except'),
                    (r'float\([^)]*\)', 'float() without try/except'),
                ]
                
                for pattern, desc in unsafe_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Check if it's in a try block
                        if 'try:' not in content.split(match)[0].split('\n')[-5:]:
                            type_issues.append(f"{file_path.name}: {desc}")
                            break
            except Exception:
                continue
        
        if type_issues:
            logger.info("Configuration type safety suggestions:")
            for issue in type_issues[:10]:
                logger.info(f"  {issue}")