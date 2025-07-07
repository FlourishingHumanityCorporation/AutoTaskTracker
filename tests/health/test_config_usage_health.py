"""
Configuration usage health tests.

Tests that production files properly use configuration instead of 
hardcoded values, validates config compliance across the codebase.
"""

import os
import ast
import re
from pathlib import Path
import pytest
import logging

logger = logging.getLogger(__name__)


class TestConfigUsageHealth:
    """Configuration usage and compliance health checks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        
        # Get all production Python files (exclude tests)
        cls.production_files = []
        for pattern in ['autotasktracker/**/*.py', 'scripts/**/*.py']:
            cls.production_files.extend(cls.project_root.glob(pattern))
        
        # Exclude test files and __pycache__
        cls.production_files = [
            f for f in cls.production_files 
            if not any(exclude in str(f) for exclude in [
                'test_', '__pycache__', '.pyc', '/tests/', 
                '/config.py'  # Config file itself defines defaults
            ])
        ]
        
    def test_production_files_use_config_no_hardcoded_values(self):
        """Scan ALL production files for hardcoded values that should use config."""
        hardcoded_violations = []
        config_import_violations = []
        
        # Patterns that should use config
        hardcoded_patterns = {
            'ports': {
                'pattern': r'\b(8502|8503|8504|8505|8506|8841|11434)\b',
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
                'pattern': r'["\']http://localhost:(8841|11434)[^"\']*["\']',
                'should_use': 'config.get_service_url("memos") or config.get_ollama_url()'
            }
        }
        
        for file_path in self.production_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = file_path.relative_to(self.project_root)
                
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
                
        if hardcoded_violations:
            error_msg = f"""
🚨 HARDCODED CONFIGURATION VALUES DETECTED 🚨

Found {len(hardcoded_violations)} hardcoded values in production files:

"""
            # Group violations by file
            violations_by_file = {}
            for violation in hardcoded_violations:
                file_path = violation['file']
                if file_path not in violations_by_file:
                    violations_by_file[file_path] = []
                violations_by_file[file_path].append(violation)
                
            for file_path, violations in list(violations_by_file.items())[:10]:  # Show first 10 files
                error_msg += f"\n❌ {file_path}:\n"
                for violation in violations[:3]:  # Show first 3 violations per file
                    error_msg += f"   • {violation['pattern']}: {violation['value']} → {violation['should_use']}\n"
                if len(violations) > 3:
                    error_msg += f"   ... and {len(violations) - 3} more\n"
                    
            if len(violations_by_file) > 10:
                error_msg += f"\n... and {len(violations_by_file) - 10} more files\n"
                
            error_msg += """
✅ CONFIGURATION REQUIREMENTS:
  - Use config.get_db_path() instead of hardcoded database paths
  - Use config.TASK_BOARD_PORT instead of hardcoded ports  
  - Use config.get_service_url() instead of hardcoded URLs
  - Import configuration in files that need it

🔧 FIXES:
  1. Import config: from autotasktracker.config import get_config
  2. Replace hardcoded values with config methods
  3. Use environment variables for overrides
  4. Centralize all configuration in config.py
"""
            raise AssertionError(error_msg)
            
        if config_import_violations:
            error_msg = f"""
🚨 MISSING CONFIG IMPORTS 🚨

{len(config_import_violations)} files use hardcoded values but don't import config:

{chr(10).join(f'  ❌ {file_path}' for file_path in config_import_violations[:10])}

✅ Add proper config imports to these files
"""
            raise AssertionError(error_msg)
            
    def test_dashboard_files_use_config_ports_exclusively(self):
        """Test that dashboard files use config for port management."""
        dashboard_files = [
            f for f in self.production_files 
            if 'dashboard' in str(f) and f.name.endswith('.py')
        ]
        
        port_violations = []
        
        for file_path in dashboard_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = file_path.relative_to(self.project_root)
                
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
                
        if port_violations:
            error_msg = f"""
🚨 DASHBOARD PORT CONFIGURATION VIOLATIONS 🚨

{len(port_violations)} dashboard files use hardcoded ports:

{chr(10).join(f"  ❌ {v['file']}: ports {v['ports']}" for v in port_violations)}

✅ DASHBOARD PORT REQUIREMENTS:
  - Use config.TASK_BOARD_PORT instead of 8502
  - Use config.ANALYTICS_PORT instead of 8503  
  - Use config.TIMETRACKER_PORT instead of 8505
  - Import and use configuration properly

🔧 EXAMPLE FIX:
  from autotasktracker.config import get_config
  config = get_config()
  port = config.TASK_BOARD_PORT
"""
            raise AssertionError(error_msg)
            
    def test_api_client_files_use_config_urls_exclusively(self):
        """Test that API client files use config for URL management."""
        api_files = [
            f for f in self.production_files 
            if any(api_indicator in str(f).lower() for api_indicator in [
                'api_client', 'client', 'pensieve'
            ])
        ]
        
        url_violations = []
        
        for file_path in api_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = file_path.relative_to(self.project_root)
                
                # Check for hardcoded URLs
                url_patterns = [
                    r'["\']http://localhost:8841[^"\']*["\']',
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
                
        if url_violations:
            error_msg = f"""
🚨 API CLIENT URL CONFIGURATION VIOLATIONS 🚨

{len(url_violations)} API client files use hardcoded URLs:

"""
            for violation in url_violations:
                error_msg += f"  ❌ {violation['file']}:\n"
                for url in violation['urls'][:3]:  # Show first 3 URLs
                    error_msg += f"     • {url}\n"
                if len(violation['urls']) > 3:
                    error_msg += f"     ... and {len(violation['urls']) - 3} more\n"
                    
            error_msg += """
✅ API URL REQUIREMENTS:
  - Use config.get_service_url("memos") instead of hardcoded memos URLs
  - Use config.get_ollama_url() instead of hardcoded Ollama URLs
  - Use config.PENSIEVE_API_URL for Pensieve API access
  - Make URLs configurable via environment variables

🔧 EXAMPLE FIX:
  from autotasktracker.config import get_config
  config = get_config()
  memos_url = config.get_service_url("memos")
  ollama_url = config.get_ollama_url()
"""
            raise AssertionError(error_msg)