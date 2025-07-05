"""Test for Pensieve-specific database patterns."""
import logging
from pathlib import Path
import pytest

from tests.health.analyzers.database_analyzer import DatabaseAccessAnalyzer

logger = logging.getLogger(__name__)


class TestPensieveDatabase:
    """Test for Pensieve-specific database integration patterns."""
    
    def test_pensieve_schema_compliance(self, production_files, script_files):
        """Test that code follows Pensieve database schema conventions."""
        schema_issues = []
        
        # Expected table and column names
        expected_tables = ['entities', 'metadata_entries']
        expected_columns = {
            'entities': ['id', 'file_path', 'created_at', 'type'],
            'metadata_entries': ['id', 'entity_id', 'key', 'value', 'created_at']
        }
        
        for file_path in production_files + script_files:
            try:
                content = file_path.read_text()
                
                # Check for non-standard table references
                for line_num, line in enumerate(content.split('\n'), 1):
                    # Look for SQL queries
                    if 'FROM' in line or 'INSERT INTO' in line or 'UPDATE' in line:
                        # Check if using correct table names
                        for table in expected_tables:
                            if table in line:
                                # Good - using expected table
                                break
                        else:
                            # Check if it's a custom table reference
                            if any(keyword in line for keyword in ['FROM', 'INTO', 'UPDATE']):
                                if not any(t in line for t in ['sqlite_', 'pragma']):
                                    schema_issues.append({
                                        'file': file_path,
                                        'line': line_num,
                                        'issue': 'Non-standard table reference',
                                        'code': line.strip()
                                    })
            except Exception:
                continue
        
        if schema_issues:
            logger.warning(f"Found {len(schema_issues)} potential schema compliance issues")
            for issue in schema_issues[:5]:
                logger.warning(f"  {issue['file'].name}:{issue['line']} - {issue['issue']}")
    
    def test_metadata_key_conventions(self):
        """Test that metadata keys follow consistent naming conventions."""
        key_issues = []
        
        # Common metadata keys that should be used consistently
        standard_keys = {
            'ocr_text', 'window_title', 'tasks', 'category',
            'vlm_analysis', 'embeddings', 'processed'
        }
        
        for file_path in self.production_files + self.script_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    # Look for metadata key usage
                    if 'store_metadata' in line or 'fetch_metadata' in line:
                        # Try to extract the key
                        import re
                        key_matches = re.findall(r'["\']([^"\']+)["\']', line)
                        for key in key_matches:
                            # Check if it looks like a metadata key
                            if key.lower() == key and '_' in key:
                                # Check if it's a variation of a standard key
                                for std_key in standard_keys:
                                    if (key != std_key and 
                                        (std_key in key or key in std_key)):
                                        key_issues.append({
                                            'file': file_path,
                                            'line': i + 1,
                                            'key': key,
                                            'suggestion': std_key
                                        })
            except Exception:
                continue
        
        if key_issues:
            logger.info(f"Found {len(key_issues)} metadata key convention issues")
            for issue in key_issues[:5]:
                logger.info(f"  {issue['file'].name}:{issue['line']} - '{issue['key']}' (consider '{issue['suggestion']}')")
    
    def test_pensieve_api_usage(self):
        """Test that code properly uses Pensieve APIs when available."""
        api_issues = []
        
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                # Check for direct database access that could use Pensieve API
                if 'autotasktracker/pensieve' not in str(file_path):
                    # Look for patterns that suggest bypassing Pensieve
                    if ('entities' in content and 'metadata_entries' in content and
                        'DatabaseManager' in content):
                        
                        # Check if they're importing Pensieve modules
                        if 'from autotasktracker.pensieve' not in content:
                            api_issues.append({
                                'file': file_path,
                                'issue': 'Direct database access without Pensieve API consideration'
                            })
            except Exception:
                continue
        
        if api_issues:
            logger.info("Consider using Pensieve API modules:")
            for issue in api_issues[:5]:
                logger.info(f"  {issue['file'].name} - {issue['issue']}")
            logger.info("\nAvailable Pensieve modules:")
            logger.info("  - autotasktracker.pensieve.api_client")
            logger.info("  - autotasktracker.pensieve.health_monitor")
            logger.info("  - autotasktracker.pensieve.postgresql_adapter")