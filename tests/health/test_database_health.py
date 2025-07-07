"""
Database access health tests.

Tests database usage patterns including SQLite access, transaction management,
and connection pooling using extracted analyzers.
"""

import os
from pathlib import Path
from collections import defaultdict
import pytest
import logging

from tests.health.analyzers.database_analyzer import (
    DatabaseAccessAnalyzer, 
    analyze_file_for_n_plus_one,
    analyze_bulk_operations,
    analyze_index_usage
)
from tests.health.analyzers.utils import ParallelAnalyzer
from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestDatabaseHealth:
    """Database access pattern health checks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.analyzer = ParallelAnalyzer()
        cls.db_analyzer = DatabaseAccessAnalyzer(cls.project_root)
        
        # Use shared file selection to ensure identical file lists across all health tests
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files using shared logic
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.test_files = categories['test_files']
        cls.production_files = categories['production_files']
        cls.dashboard_files = categories['dashboard_files']
    
    def test_no_direct_sqlite_access(self):
        """Test that no files use direct sqlite3 connections to Pensieve database."""
        direct_sqlite_files = []
        problematic_patterns = []
        
        for file_path in self.python_files:
            violations = self.db_analyzer.analyze_sqlite_access(file_path)
            if violations:
                direct_sqlite_files.append(file_path)
                problematic_patterns.extend(violations)
        
        if direct_sqlite_files:
            error_msg = f"""
🚨 DIRECT SQLITE ACCESS TO PENSIEVE DATABASE DETECTED 🚨

Found {len(direct_sqlite_files)} files bypassing DatabaseManager:

Files with issues:
{chr(10).join(f'  ❌ {f.relative_to(self.project_root) if f.is_relative_to(self.project_root) else f.name}' for f in direct_sqlite_files)}

Specific violations:
{chr(10).join(f'  📍 {p}' for p in problematic_patterns[:10])}
{f'  ... and {len(problematic_patterns) - 10} more' if len(problematic_patterns) > 10 else ''}

✅ CORRECT USAGE:
  from autotasktracker.core.database import DatabaseManager
  db = DatabaseManager()
  
❌ INCORRECT USAGE:
  import sqlite3
  conn = sqlite3.connect("/Users/paulrohde/AutoTaskTracker.memos/database.db")

All database access should go through DatabaseManager for:
- Connection pooling
- Error handling
- Performance optimization
- Consistent configuration
"""
            raise AssertionError(error_msg)
    
    def test_transaction_management(self):
        """Test for proper transaction management in multi-metadata updates."""
        all_issues = []
        
        # Only check production files
        files_to_check = self.production_files + self.script_files
        
        for file_path in files_to_check:
            issues = self.db_analyzer.analyze_transaction_management(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            warning_msg = f"""
⚠️ TRANSACTION MANAGEMENT WARNING ⚠️

Found {len(all_issues)} functions with multiple write operations but no transactions:

{chr(10).join(f'''
⚠️ {issue["file"].relative_to(self.project_root) if issue["file"].is_relative_to(self.project_root) else issue["file"].name} - {issue["function"]}()
   Line {issue["line"]}: {issue["operations"]} write operations without transaction
   First operation at line {issue["first_op"]["line"]}: {issue["first_op"]["type"]}
''' for issue in all_issues[:5])}
{f'... and {len(all_issues) - 5} more' if len(all_issues) > 5 else ''}

✅ RECOMMENDED:
  with db.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("BEGIN TRANSACTION")
      try:
          # Multiple operations
          db.store_metadata(entity_id, "tasks", task_data, conn=conn)
          db.store_metadata(entity_id, "category", category, conn=conn)
          cursor.execute("COMMIT")
      except:
          cursor.execute("ROLLBACK")
          raise

This ensures atomicity and better performance.
"""
            print(warning_msg)  # Warning, not error
    
    def test_connection_pool_usage(self):
        """Test that database connections use pooling properly."""
        all_issues = []
        
        for file_path in self.python_files:
            issues = self.db_analyzer.analyze_connection_pooling(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            warning_msg = f"""
⚠️ CONNECTION POOLING ISSUES ⚠️

Found {len(all_issues)} potential connection pooling issues:

{chr(10).join(f'''
⚠️ {issue["file"].relative_to(self.project_root) if issue["file"].is_relative_to(self.project_root) else issue["file"].name} - {issue["function"]}()
   Issue: {issue["issue"]} ({issue["count"]} instances)
''' for issue in all_issues[:10])}

✅ BEST PRACTICES:

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
            print(warning_msg)
    
    def test_n_plus_one_query_patterns(self):
        """Test for N+1 query patterns using parallel processing."""
        # Skip in incremental mode to avoid hanging  
        from tests.health.analyzers.utils import IncrementalTestRunner
        if IncrementalTestRunner.should_run_incremental():
            print("⏩ Skipping expensive N+1 query analysis in incremental mode")
            return
            
        # Limit files based on environment
        max_slow_test_files = int(os.getenv('PENSIEVE_MAX_FILES', '50'))
        
        # Only analyze production and script files (limited for performance)
        files_to_analyze = self.production_files + self.script_files
        if len(files_to_analyze) > max_slow_test_files:
            files_to_analyze = files_to_analyze[:max_slow_test_files]
            print(f"ℹ️  Analyzing {max_slow_test_files} files for N+1 patterns (set PENSIEVE_MAX_FILES to analyze more)")
        
        # Run parallel analysis
        results = self.analyzer.analyze_files_parallel(
            files_to_analyze,
            analyze_file_for_n_plus_one,
            'n_plus_one',
            timeout_per_file=1
        )
        
        # Collect issues
        n_plus_one_issues = []
        for file_path, issues in results:
            if issues:
                for issue in issues:
                    n_plus_one_issues.append({
                        'file': file_path,
                        'line': issue['line'],
                        'loop_line': issue['loop_line'],
                        'code': issue['code']
                    })
        
        # Report findings (info only for most, warnings for production)
        if n_plus_one_issues:
            print(f"\n⚠️ POTENTIAL N+1 QUERY PATTERNS DETECTED ⚠️\n")
            print(f"Found {len(n_plus_one_issues)} potential N+1 patterns in production code:\n")
            
            for issue in n_plus_one_issues[:10]:
                file_path = Path(issue['file']) if isinstance(issue['file'], str) else issue['file']
                try:
                    rel_path = file_path.relative_to(self.project_root)
                except ValueError:
                    rel_path = file_path.name
                print(f"❌ {rel_path}:{issue['line']}")
                print(f"   Loop at line {issue['loop_line']} contains database query")
                print(f"   Code: {issue['code'][:80]}...")
                print()
            
            if len(n_plus_one_issues) > 10:
                print(f"... and {len(n_plus_one_issues) - 10} more\n")
            
            print("💡 Consider using batch operations or JOIN queries for better performance")
    
    def test_bulk_operation_opportunities(self):
        """Test for opportunities to use bulk operations instead of loops."""
        bulk_opportunities = []
        
        # Limit files for performance
        max_slow_test_files = int(os.getenv('PENSIEVE_MAX_FILES', '50'))
        files_to_check = (self.production_files + self.script_files)[:max_slow_test_files]
        
        for file_path in files_to_check:
            opportunities = analyze_bulk_operations(file_path)
            bulk_opportunities.extend(opportunities)
        
        if bulk_opportunities:
            info_msg = f"""
💡 BULK OPERATION OPPORTUNITIES 💡

Found {len(bulk_opportunities)} files with potential bulk operation improvements:

{chr(10).join(f'  💡 {Path(f).relative_to(self.project_root) if Path(f).is_relative_to(self.project_root) else Path(f).name}' for f in bulk_opportunities[:10])}
{f'  ... and {len(bulk_opportunities) - 10} more' if len(bulk_opportunities) > 10 else ''}

Consider using bulk operations for better performance:

Instead of:
  for item in items:
      db.store_metadata(entity_id, key, item)

Use:
  db.store_metadata_batch([(entity_id, key, item) for item in items])
"""
            print(info_msg)
    
    def test_missing_index_usage(self):
        """Test for queries that might benefit from indexes."""
        all_issues = []
        
        for file_path in self.python_files:
            issues = analyze_index_usage(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            info_msg = f"""
💡 DATABASE INDEX OPTIMIZATION OPPORTUNITIES 💡

Found {len(all_issues)} queries that might benefit from indexes:

{chr(10).join(f'''
💡 {issue["file"].relative_to(self.project_root) if issue["file"].is_relative_to(self.project_root) else issue["file"].name}:{issue["line"]}
   Issue: {issue["issue"]}
   Query: {issue["query"]}...
''' for issue in all_issues[:10])}
{f'... and {len(all_issues) - 10} more' if len(all_issues) > 10 else ''}

✅ CONSIDER ADDING INDEXES:

1. For frequent WHERE clauses:
   CREATE INDEX idx_metadata_key ON metadata_entries(key);
   CREATE INDEX idx_entities_created ON entities(created_at);

2. For JOIN operations:
   CREATE INDEX idx_metadata_entity ON metadata_entries(entity_id, key);

3. For sorting:
   CREATE INDEX idx_entities_created_desc ON entities(created_at DESC);

4. Analyze query performance:
   EXPLAIN QUERY PLAN SELECT ...

Note: Indexes improve read performance but can slow writes.
Analyze your workload before adding indexes!
"""
            print(info_msg)