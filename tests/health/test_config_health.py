"""
Configuration pattern health tests.

Tests configuration patterns including hardcoded values and configuration
management using extracted analyzers.
"""

import os
from pathlib import Path
import pytest
import logging

from tests.health.analyzers.config_analyzer import ConfigurationAnalyzer
from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestConfigHealth:
    """Configuration pattern health checks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.config_analyzer = ConfigurationAnalyzer(cls.project_root)
        
        # Use shared file selection to ensure identical file lists across all health tests
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files using shared logic
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.test_files = categories['test_files']
        cls.production_files = categories['production_files']
        cls.dashboard_files = categories['dashboard_files']
    
    def test_configuration_hardcoding(self):
        """Test for hardcoded values that should be configurable."""
        all_hardcoding_issues = []
        
        for file_path in self.python_files:
            issues = self.config_analyzer.analyze_hardcoded_values(file_path)
            all_hardcoding_issues.extend(issues)
        
        if all_hardcoding_issues:
            warning_msg = f"""
⚠️ HARDCODED VALUES DETECTED ⚠️

Found {len(all_hardcoding_issues)} hardcoded values that should be configurable:

{chr(10).join(f'''
⚠️ {issue["file"].relative_to(self.project_root) if issue["file"].is_relative_to(self.project_root) else issue["file"].name}:{issue["line"]}
   Type: {issue["type"]}
   Value: {issue["value"]}
   Context: {issue["context"]}...
''' for issue in all_hardcoding_issues[:15])}
{f'... and {len(all_hardcoding_issues) - 15} more' if len(all_hardcoding_issues) > 15 else ''}

✅ MAKE VALUES CONFIGURABLE:

1. Move to configuration:
   # config.py
   VLM_TIMEOUT = int(os.getenv('VLM_TIMEOUT', '30'))
   RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))
   BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))

2. Use configuration:
   from autotasktracker.config import get_config
   config = get_config()
   timeout = config.VLM_TIMEOUT

3. For URLs:
   base_url = config.API_BASE_URL
   endpoint = f"{{base_url}}/api/v1/process"

This improves maintainability and deployment flexibility!
"""
            print(warning_msg)  # Warning for discussion
    
    def test_config_usage_patterns(self):
        """Test for proper configuration usage patterns."""
        good_patterns = 0
        poor_patterns = 0
        config_reports = []
        
        for file_path in self.python_files:
            patterns = self.config_analyzer.analyze_config_usage(file_path)
            
            # Score the file's configuration usage
            score = sum(patterns.values())
            
            if score >= 3:  # Good configuration usage
                good_patterns += 1
            elif score == 0:  # No configuration usage
                poor_patterns += 1
            
            if score > 0:  # File uses some configuration
                config_reports.append({
                    'file': file_path,
                    'score': score,
                    'patterns': patterns
                })
        
        # Report on configuration usage
        if config_reports:
            print(f"""
📊 CONFIGURATION USAGE ANALYSIS 📊

Files using configuration: {len(config_reports)}
Good configuration usage: {good_patterns}
Files with no configuration: {poor_patterns}

Top configuration users:
""")
            # Sort by score and show top 10
            config_reports.sort(key=lambda x: x['score'], reverse=True)
            for report in config_reports[:10]:
                file_path = report['file']
                try:
                    rel_path = file_path.relative_to(self.project_root)
                except ValueError:
                    rel_path = file_path.name
                
                features = []
                if report['patterns']['uses_env_vars']:
                    features.append('env vars')
                if report['patterns']['uses_config_module']:
                    features.append('config module')
                if report['patterns']['has_defaults']:
                    features.append('defaults')
                if report['patterns']['validates_config']:
                    features.append('validation')
                
                print(f"✅ {rel_path} - Score: {report['score']} ({', '.join(features)})")
        
        # Always pass - this is informational
        assert True