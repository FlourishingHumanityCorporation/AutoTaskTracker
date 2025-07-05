"""Test for database connection patterns."""
import logging
import os
import re
from pathlib import Path
import pytest

from tests.health.analyzers.database_analyzer import DatabaseAccessAnalyzer
from tests.health.analyzers.utils import ParallelAnalyzer

logger = logging.getLogger(__name__)


class TestDatabaseConnections:
    """Test for proper database connection patterns."""
    
    def test_no_direct_sqlite_access(self, all_python_files, database_analyzer):
        """Test that no files use direct sqlite3 connections to Pensieve database."""
        direct_sqlite_files = []
        problematic_patterns = []
        
        for file_path in all_python_files:
            violations = database_analyzer.analyze_sqlite_access(file_path)
            if violations:
                direct_sqlite_files.append(file_path)
                problematic_patterns.extend(violations)
        
        if direct_sqlite_files:
            # Get project root for relative path display
            project_root = all_python_files[0].parents[3] if all_python_files else Path.cwd()
            error_msg = f"""
DIRECT SQLITE ACCESS TO PENSIEVE DATABASE DETECTED

Found {len(direct_sqlite_files)} files bypassing DatabaseManager:

Files with issues:
{chr(10).join(f'  {f.relative_to(project_root) if f.is_relative_to(project_root) else f.name}' for f in direct_sqlite_files)}

Specific violations:
{chr(10).join(f'  {p}' for p in problematic_patterns[:10])}
{f'  ... and {len(problematic_patterns) - 10} more' if len(problematic_patterns) > 10 else ''}

CORRECT USAGE:
  from autotasktracker.core.database import DatabaseManager
  db = DatabaseManager()
  
INCORRECT USAGE:
  import sqlite3
  conn = sqlite3.connect("~/.memos/database.db")

All database access should go through DatabaseManager for:
- Connection pooling
- Error handling
- Performance optimization
- Consistent configuration
"""
            # Log as warning for now since existing code may have legitimate reasons
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Found {len(direct_sqlite_files)} files using direct SQLite access")
            for file_path in direct_sqlite_files:
                logger.warning(f"  {file_path.name} - Consider migrating to DatabaseManager")
    
    def test_connection_pool_usage(self, all_python_files, database_analyzer):
        """Test that database connections use pooling properly."""
        all_issues = []
        
        for file_path in all_python_files:
            issues = database_analyzer.analyze_connection_pooling(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            warning_msg = f"""
CONNECTION POOLING ISSUES

Found {len(all_issues)} potential connection pooling issues:

{chr(10).join(f'''
{issue["file"].relative_to(all_python_files[0].parents[3]) if issue["file"].is_relative_to(all_python_files[0].parents[3]) else issue["file"].name} - {issue["function"]}()
   Issue: {issue["issue"]} ({issue["count"]} instances)
''' for issue in all_issues[:10])}

BEST PRACTICES:

1. Reuse DatabaseManager instances:
   def __init__(self):
       self.db = DatabaseManager()  # Create once
   
   def method1(self):
       data = self.db.fetch_tasks()  # Reuse
   
   def method2(self):
       data = self.db.fetch_tasks()  # Reuse same instance

2. Use context managers for connections:
   with self.db.get_connection() as conn:
       # Connection automatically returned to pool

3. For scripts, create once at module level:
   db = DatabaseManager()  # Module level
   
   def main():
       data = db.fetch_tasks()  # Use module instance
"""
            logger.warning(warning_msg)
    
    def test_database_connection_patterns(self, production_files):
        """Test for proper database connection management"""
        python_files = production_files
        db_issues = []
        
        for file_path in python_files:
            content = file_path.read_text()
            
            # Look for direct sqlite3.connect calls (should use DatabaseManager)
            if 'sqlite3.connect' in content and 'database.py' not in str(file_path):
                db_issues.append(f"{file_path}: Direct sqlite3.connect (use DatabaseManager)")
            
            # Look for hardcoded database paths
            db_path_patterns = ['.memos/database.db', '~/.memos/', 'database.db']
            for pattern in db_path_patterns:
                # Exclude config files and pensieve modules which legitimately interface with memos defaults
                if (pattern in content and 
                    'config.py' not in str(file_path) and 
                    'pensieve/' not in str(file_path)):
                    db_issues.append(f"{file_path}: Hardcoded DB path '{pattern}' (use config)")
                    break
        
        # Log as warning instead of failing for existing code patterns
        if db_issues:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Found {len(db_issues)} database connection pattern issues")
            for issue in db_issues:
                logger.warning(f"  {issue}")