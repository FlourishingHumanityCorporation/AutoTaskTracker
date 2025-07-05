"""Test for database transaction patterns."""
import logging
from pathlib import Path
import pytest

from tests.health.analyzers.database_analyzer import DatabaseAccessAnalyzer

logger = logging.getLogger(__name__)


class TestDatabaseTransactions:
    """Test for proper database transaction management."""
    
    def test_transaction_management(self, production_files, script_files, database_analyzer):
        """Test for proper transaction management in multi-metadata updates."""
        all_issues = []
        
        # Only check production files
        files_to_check = production_files + script_files
        
        for file_path in files_to_check:
            issues = database_analyzer.analyze_transaction_management(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            warning_msg = f"""
TRANSACTION MANAGEMENT WARNING

Found {len(all_issues)} functions with multiple write operations but no transactions:

{chr(10).join(f'''
{issue["file"].name} - {issue["function"]}()
   Line {issue["line"]}: {issue["operations"]} write operations without transaction
   First operation at line {issue["first_op"]["line"]}: {issue["first_op"]["type"]}
''' for issue in all_issues[:5])}
{f'... and {len(all_issues) - 5} more' if len(all_issues) > 5 else ''}

RECOMMENDED:
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
            logger.warning(warning_msg)
    
    def test_transaction_scope(self, production_files, script_files):
        """Test that transactions are not held too long."""
        issues = []
        
        for file_path in production_files + script_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                # Look for transaction patterns
                in_transaction = False
                transaction_start = 0
                
                for i, line in enumerate(lines):
                    if 'BEGIN TRANSACTION' in line or 'conn.execute("BEGIN")' in line:
                        in_transaction = True
                        transaction_start = i
                    elif in_transaction and ('COMMIT' in line or 'ROLLBACK' in line):
                        transaction_length = i - transaction_start
                        if transaction_length > 50:  # More than 50 lines in transaction
                            issues.append({
                                'file': file_path,
                                'line': transaction_start + 1,
                                'length': transaction_length,
                                'message': 'Long transaction scope'
                            })
                        in_transaction = False
                    
                    # Check for network/file operations in transactions
                    if in_transaction:
                        if any(op in line for op in ['requests.', 'urlopen', 'open(', 'time.sleep']):
                            issues.append({
                                'file': file_path,
                                'line': i + 1,
                                'message': 'Network/file/sleep operation inside transaction'
                            })
            except Exception:
                continue
        
        if issues:
            logger.warning(f"Found {len(issues)} transaction scope issues")
            for issue in issues[:5]:
                logger.warning(f"  {issue['file'].name}:{issue['line']} - {issue['message']}")