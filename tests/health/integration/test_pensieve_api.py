"""Test Pensieve API integration patterns."""
import logging
import json
from pathlib import Path
import pytest

import re
from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestPensieveAPIIntegration:
    """Test for proper Pensieve API integration patterns."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        
        # Use shared file selection
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.test_files = categories['test_files']
        cls.production_files = categories['production_files']
        cls.dashboard_files = categories['dashboard_files']

    def analyze_rest_api_usage(self, file_path):
        """Context-aware analyzer for REST API usage."""
        issues = []
        try:
            content = file_path.read_text()
            
            # Check for requests usage
            if 'requests.get' in content or 'requests.post' in content:
                # Skip if it's calling external services (Ollama, etc.)
                external_services = ['ollama', 'localhost:11434', 'openai', 'anthropic']
                if any(service in content.lower() for service in external_services):
                    return issues  # Legitimate external API usage
                
                # Skip if it's already using an API client
                if 'api_client' in content.lower() or 'PensieveAPIClient' in content:
                    return issues
                    
                # Check if it's calling Pensieve endpoints without the client
                pensieve_patterns = [':8839', 'localhost:8839', '/api/screenshots', '/api/metadata']
                if any(pattern in content for pattern in pensieve_patterns):
                    issues.append(f"{file_path.name} - Direct Pensieve API calls without API client")
                    
        except Exception:
            pass
        return issues
    
    def test_rest_api_usage(self):
        """Test that REST API client is used properly for Pensieve communication."""
        all_issues = []
        
        for file_path in self.production_files + self.script_files:
            issues = self.analyze_rest_api_usage(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            # Group by issue type
            by_type = {}
            for issue in all_issues:
                issue_type = issue.split(' - ')[1] if ' - ' in issue else 'Other'
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(issue)
            
            error_msg = f"""
PENSIEVE REST API INTEGRATION ISSUES

Found {len(all_issues)} improper API usage patterns:

"""
            for issue_type, issues in by_type.items():
                error_msg += f"\n{issue_type} ({len(issues)} instances):\n"
                for issue in issues[:3]:
                    error_msg += f"  {issue}\n"
                if len(issues) > 3:
                    error_msg += f"  ... and {len(issues) - 3} more\n"
            
            error_msg += """
CORRECT USAGE:
  from autotasktracker.pensieve.api_client import PensieveAPIClient
  client = PensieveAPIClient()
  response = client.get_screenshots(limit=100)
  
INCORRECT USAGE:
  import requests
  response = requests.get("http://localhost:8839/api/screenshots")
  
Use the API client for proper error handling and fallback logic.
"""
            raise AssertionError(error_msg)
    
    def test_api_error_handling(self):
        """Test that API calls have proper error handling."""
        error_issues = []
        
        # Check files that use the API client
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                if 'PensieveAPIClient' in content or 'api_client' in content:
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines):
                        # Look for API calls without try/except
                        if any(method in line for method in [
                            '.get_screenshots(', '.get_health(', 
                            '.search(', '.get_metadata('
                        ]):
                            # Check if it's in a try block
                            context_start = max(0, i - 5)
                            context = lines[context_start:i]
                            
                            if not any('try:' in l for l in context):
                                error_issues.append({
                                    'file': file_path,
                                    'line': i + 1,
                                    'code': line.strip()
                                })
            except Exception:
                continue
        
        if error_issues:
            logger.warning(f"Found {len(error_issues)} API calls without error handling")
            for issue in error_issues[:5]:
                logger.warning(f"  {issue['file'].name}:{issue['line']} - {issue['code'][:50]}...")
    
    def test_api_client_reuse(self):
        """Test that API client instances are reused properly."""
        reuse_issues = []
        
        for file_path in self.production_files + self.dashboard_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                # Count API client instantiations
                instantiations = []
                for i, line in enumerate(lines):
                    if 'PensieveAPIClient()' in line:
                        instantiations.append(i + 1)
                
                # Check if multiple instantiations in same file
                if len(instantiations) > 1:
                    # Check if they're in different functions
                    function_count = content.count('def ')
                    if function_count > 0 and len(instantiations) > function_count / 2:
                        reuse_issues.append({
                            'file': file_path,
                            'count': len(instantiations),
                            'lines': instantiations[:3]
                        })
            except Exception:
                continue
        
        if reuse_issues:
            logger.info("API client reuse opportunities:")
            for issue in reuse_issues:
                logger.info(f"  {issue['file'].name}: {issue['count']} instantiations")
                logger.info(f"    Consider creating once and reusing")
    
    def test_api_fallback_implementation(self):
        """Test that API usage includes proper fallback to direct database."""
        fallback_issues = []
        
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                # Check files using API client
                if 'PensieveAPIClient' in content:
                    # Look for fallback patterns
                    has_fallback = any(pattern in content for pattern in [
                        'DatabaseManager', 'fallback', 'except',
                        'if not response', 'if response is None'
                    ])
                    
                    if not has_fallback:
                        fallback_issues.append(file_path)
            except Exception:
                continue
        
        if fallback_issues:
            logger.warning("Files using API without apparent fallback:")
            for f in fallback_issues[:5]:
                logger.warning(f"  {f.name}")
            logger.warning("Ensure graceful degradation when API is unavailable")