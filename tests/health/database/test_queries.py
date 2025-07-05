"""Test for database query patterns and performance."""
import logging
import os
from pathlib import Path
import pytest

from tests.health.analyzers.database_analyzer import (
    analyze_file_for_n_plus_one,
    analyze_bulk_operations,
    analyze_index_usage
)
from tests.health.analyzers.utils import ParallelAnalyzer, IncrementalTestRunner

logger = logging.getLogger(__name__)


class TestDatabaseQueries:
    """Test for database query patterns and performance issues."""
    
    def __init__(self):
        self.analyzer = ParallelAnalyzer()
    
    def test_n_plus_one_query_patterns(self, production_files, script_files):
        """Test for N+1 query patterns using parallel processing."""
        # Skip in incremental mode to avoid hanging  
        if IncrementalTestRunner.should_run_incremental():
            logger.info("Skipping expensive N+1 query analysis in incremental mode")
            return
            
        # Limit files based on environment
        max_slow_test_files = int(os.getenv('PENSIEVE_MAX_FILES_PER_TEST', '30'))
        
        # Only analyze production and script files (limited for performance)
        files_to_analyze = production_files + script_files
        if len(files_to_analyze) > max_slow_test_files:
            files_to_analyze = files_to_analyze[:max_slow_test_files]
            logger.info(f"Analyzing {max_slow_test_files} files for N+1 patterns (set PENSIEVE_MAX_FILES_PER_TEST to analyze more)")
        
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
            logger.warning(f"POTENTIAL N+1 QUERY PATTERNS DETECTED")
            logger.warning(f"Found {len(n_plus_one_issues)} potential N+1 patterns in production code:")
            
            for issue in n_plus_one_issues[:10]:
                file_path = Path(issue['file']) if isinstance(issue['file'], str) else issue['file']
                try:
                    # Get project root from file path
                    project_root = file_path.parents[3] if len(file_path.parents) > 3 else Path.cwd()
                    rel_path = file_path.relative_to(project_root)
                except ValueError:
                    rel_path = file_path.name
                logger.warning(f"{rel_path}:{issue['line']}")
                logger.warning(f"   Loop at line {issue['loop_line']} contains database query")
                logger.warning(f"   Code: {issue['code'][:80]}...")
            
            if len(n_plus_one_issues) > 10:
                logger.warning(f"... and {len(n_plus_one_issues) - 10} more")
            
            logger.info("Consider using batch operations or JOIN queries for better performance")
    
    def test_bulk_operation_opportunities(self, production_files, script_files):
        """Test for opportunities to use bulk operations instead of loops."""
        bulk_opportunities = []
        
        # Limit files for performance
        max_slow_test_files = int(os.getenv('PENSIEVE_MAX_FILES_PER_TEST', '30'))
        files_to_check = (production_files + script_files)[:max_slow_test_files]
        
        for file_path in files_to_check:
            opportunities = analyze_bulk_operations(file_path)
            bulk_opportunities.extend(opportunities)
        
        if bulk_opportunities:
            logger.info("BULK OPERATION OPPORTUNITIES")
            logger.info(f"Found {len(bulk_opportunities)} files with potential bulk operation improvements:")
            
            for f in bulk_opportunities[:10]:
                file_path = Path(f)
                try:
                    project_root = file_path.parents[3] if len(file_path.parents) > 3 else Path.cwd()
                    rel_path = file_path.relative_to(project_root)
                except ValueError:
                    rel_path = file_path.name
                logger.info(f"  {rel_path}")
            
            if len(bulk_opportunities) > 10:
                logger.info(f"  ... and {len(bulk_opportunities) - 10} more")
            
            logger.info("\nConsider using bulk operations for better performance:")
            logger.info("Instead of:")
            logger.info("  for item in items:")
            logger.info("      db.store_metadata(entity_id, key, item)")
            logger.info("\nUse:")
            logger.info("  db.store_metadata_batch([(entity_id, key, item) for item in items])")
    
    def test_missing_index_usage(self, all_python_files):
        """Test for queries that might benefit from indexes."""
        all_issues = []
        
        for file_path in all_python_files:
            issues = analyze_index_usage(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            logger.info("DATABASE INDEX OPTIMIZATION OPPORTUNITIES")
            logger.info(f"Found {len(all_issues)} queries that might benefit from indexes:")
            
            for issue in all_issues[:10]:
                file_path = issue['file']
                try:
                    project_root = file_path.parents[3] if len(file_path.parents) > 3 else Path.cwd()
                    rel_path = file_path.relative_to(project_root)
                except ValueError:
                    rel_path = file_path.name
                logger.info(f"{rel_path}:{issue['line']}")
                logger.info(f"   Issue: {issue['issue']}")
                logger.info(f"   Query: {issue['query']}...")
            
            if len(all_issues) > 10:
                logger.info(f"... and {len(all_issues) - 10} more")
            
            logger.info("\nCONSIDER ADDING INDEXES:")
            logger.info("1. For frequent WHERE clauses:")
            logger.info("   CREATE INDEX idx_metadata_key ON metadata_entries(key);")
            logger.info("   CREATE INDEX idx_entities_created ON entities(created_at);")
            logger.info("\n2. For JOIN operations:")
            logger.info("   CREATE INDEX idx_metadata_entity ON metadata_entries(entity_id, key);")
            logger.info("\n3. For sorting:")
            logger.info("   CREATE INDEX idx_entities_created_desc ON entities(created_at DESC);")
            logger.info("\nNote: Indexes improve read performance but can slow writes.")
            logger.info("Analyze your workload before adding indexes!")