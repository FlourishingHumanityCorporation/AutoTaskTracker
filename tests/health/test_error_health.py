"""
Error handling pattern health tests.

Tests error handling patterns including bare except clauses, print statements,
and retry logic using extracted analyzers.
"""

import os
from pathlib import Path
from collections import defaultdict
import pytest
import logging

from tests.health.analyzers.error_analyzer import ErrorHandlingAnalyzer, analyze_file_for_error_handling
from tests.health.analyzers.auto_fixer import PensieveHealthAutoFixer
from tests.health.analyzers.utils import ParallelAnalyzer
from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestErrorHealth:
    """Error handling pattern health checks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.error_analyzer = ErrorHandlingAnalyzer(cls.project_root)
        cls.auto_fixer = PensieveHealthAutoFixer(dry_run=not os.getenv('PENSIEVE_AUTO_FIX'))
        cls.analyzer = ParallelAnalyzer()
        
        # Use shared file selection to ensure identical file lists across all health tests
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files using shared logic
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.test_files = categories['test_files']
        cls.production_files = categories['production_files']
        cls.dashboard_files = categories['dashboard_files']
    
    def test_error_handling_patterns(self):
        """Test error handling patterns using parallel processing with auto-fix."""
        # Skip in incremental mode to avoid hanging
        from tests.health.analyzers.utils import IncrementalTestRunner
        if IncrementalTestRunner.should_run_incremental():
            print("⏩ Skipping expensive error handling analysis in incremental mode")
            return
            
        # Limit files based on environment
        max_slow_test_files = int(os.getenv('PENSIEVE_MAX_FILES', '50'))
        
        # Limit files for performance - focus on production code
        files_to_check = self.production_files + self.script_files
        if len(files_to_check) > max_slow_test_files:
            files_to_check = files_to_check[:max_slow_test_files]
            print(f"ℹ️  Analyzing {max_slow_test_files} files for error patterns (set PENSIEVE_MAX_FILES to analyze more)")
            
        results = self.analyzer.analyze_files_parallel(
            files_to_check,
            analyze_file_for_error_handling,
            'error_handling',
            timeout_per_file=1
        )
        
        # Group issues by file
        issues_by_file = defaultdict(list)
        for file_path, issues in results:
            if issues:
                issues_by_file[file_path] = issues
        
        # Auto-fix if enabled
        if os.getenv('PENSIEVE_AUTO_FIX') and issues_by_file:
            print("\n🔧 AUTO-FIX MODE ENABLED 🔧\n")
            for file_path, issues in issues_by_file.items():
                if self.auto_fixer.add_error_logging(file_path, issues):
                    print(f"✅ Fixed error logging in {file_path}")
        
        # Report findings
        if issues_by_file:
            total_issues = sum(len(issues) for issues in issues_by_file.values())
            error_msg = f"""
🚨 POOR ERROR HANDLING IN PENSIEVE INTEGRATION 🚨

Found {total_issues} error handling issues in {len(issues_by_file)} files:

"""
            for file_path, issues in list(issues_by_file.items())[:5]:
                try:
                    rel_path = file_path.relative_to(self.project_root)
                except ValueError:
                    rel_path = file_path.name
                error_msg += f"❌ {rel_path}\n"
                for line_num, issue_type, code in issues[:3]:
                    error_msg += f"   Line {line_num}: {issue_type.replace('_', ' ').title()}\n"
                    error_msg += f"   Code: {code[:60]}...\n"
                if len(issues) > 3:
                    error_msg += f"   ... and {len(issues) - 3} more issues\n"
                error_msg += "\n"
            
            if len(issues_by_file) > 5:
                error_msg += f"... and {len(issues_by_file) - 5} more files\n"
            
            error_msg += """
✅ GOOD ERROR HANDLING:
  try:
      result = db.fetch_tasks()
  except sqlite3.DatabaseError as e:
      logger.error(f"Database error: {{e}}")
      # Specific recovery action
  except Exception as e:
      logger.exception("Unexpected error")
      # Graceful degradation

❌ AVOID:
  - Bare except clauses
  - Printing errors instead of logging
  - Silently passing exceptions
  - Not handling specific error types
"""
            
            if not os.getenv('PENSIEVE_AUTO_FIX'):
                error_msg += "\n💡 TIP: Set PENSIEVE_AUTO_FIX=1 to automatically fix some issues\n"
            
            raise AssertionError(error_msg)
    
    def test_retry_logic_implementation(self):
        """Test for proper retry logic with exponential backoff."""
        all_retry_issues = []
        
        for file_path in self.python_files:
            issues = self.error_analyzer.analyze_retry_logic(file_path)
            all_retry_issues.extend(issues)
        
        if all_retry_issues:
            warning_msg = f"""
⚠️ MISSING RETRY LOGIC WARNING ⚠️

Found {len(all_retry_issues)} files with network operations but no retry logic:

{chr(10).join(f'''
⚠️ {issue["file"].relative_to(self.project_root) if issue["file"].is_relative_to(self.project_root) else issue["file"].name}
   Reason: {issue["reason"]} without retry logic
''' for issue in all_retry_issues[:10])}
{f'... and {len(all_retry_issues) - 10} more' if len(all_retry_issues) > 10 else ''}

✅ IMPLEMENT RETRY LOGIC:
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def api_call_with_retry():
    response = requests.get(url)
    response.raise_for_status()
    return response

Or manual implementation:
for attempt in range(max_retries):
    try:
        result = api_call()
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(2 ** attempt)  # Exponential backoff
"""
            print(warning_msg)  # Warning, not error
    
    def test_file_operation_validation(self):
        """Test that file operations include proper validation."""
        all_validation_issues = []
        
        # Limit files for performance
        max_slow_test_files = int(os.getenv('PENSIEVE_MAX_FILES', '50'))
        
        # Only check production files
        files_to_check = (self.production_files + self.script_files)[:max_slow_test_files]
        
        for file_path in files_to_check:
            issues = self.error_analyzer.analyze_file_operations(file_path)
            all_validation_issues.extend(issues)
        
        if all_validation_issues:
            error_msg = f"""
🚨 FILE OPERATION VALIDATION MISSING 🚨

Found {len(all_validation_issues)} file operations without validation:
""" + chr(10).join(f'''
❌ {issue["file"].relative_to(self.project_root) if issue["file"].is_relative_to(self.project_root) else issue["file"].name}:{issue["line"]}
   Function: {issue["function"]}()
   Operation: {issue["operation"]}
   Code: {issue["code"]}
''' for issue in all_validation_issues[:10]) + (f'\n... and {len(all_validation_issues) - 10} more' if len(all_validation_issues) > 10 else '') + """

✅ ALWAYS VALIDATE FILE OPERATIONS:

# Before reading:
if not os.path.exists(filepath):
    logger.error(f"File not found: {{filepath}}")
    return None

# Check permissions:
if not os.access(filepath, os.R_OK):
    raise PermissionError(f"Cannot read file: {{filepath}}")

# Use Path for better validation:
from pathlib import Path
file_path = Path(filepath)
if not file_path.is_file():
    raise FileNotFoundError(f"Not a file: {{filepath}}")

# Always use try/except:
try:
    with open(filepath, 'r') as f:
        content = f.read()
except IOError as e:
    logger.error(f"Failed to read file: {{e}}")
    raise
"""
            raise AssertionError(error_msg)