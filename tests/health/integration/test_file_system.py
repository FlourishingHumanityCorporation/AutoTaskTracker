"""Test file system integration patterns."""
import logging
from pathlib import Path
import pytest

from tests.health.analyzers.error_analyzer import ErrorHandlingAnalyzer
from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestFileSystemIntegration:
    """Test for proper file system integration patterns."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.error_analyzer = ErrorHandlingAnalyzer(cls.project_root)
        
        # Use shared file selection
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.production_files = categories['production_files']
    
    def test_screenshot_directory_usage(self):
        """Test that code uses Pensieve's screenshot directory structure properly."""
        directory_issues = []
        
        # Expected screenshot directory patterns
        expected_patterns = [
            '~/.memos/screenshots',
            'SCREENSHOT_DIR',
            'get_screenshot_dir()',
        ]
        
        for file_path in self.production_files + self.script_files:
            try:
                content = file_path.read_text()
                
                # Check if file deals with screenshots
                if 'screenshot' in content.lower():
                    # Check if it uses proper directory structure
                    uses_proper_dir = any(pattern in content for pattern in expected_patterns)
                    
                    # Look for hardcoded paths
                    import re
                    hardcoded_paths = re.findall(r'["\']([/\\].*screenshots?[/\\][^"\']+)["\']', content)
                    
                    if hardcoded_paths and not uses_proper_dir:
                        directory_issues.append({
                            'file': file_path,
                            'paths': hardcoded_paths[:3]
                        })
            except Exception:
                continue
        
        if directory_issues:
            error_msg = "SCREENSHOT DIRECTORY ISSUES\n\n"
            error_msg += f"Found {len(directory_issues)} files with hardcoded screenshot paths:\n\n"
            
            for issue in directory_issues:
                error_msg += f"{issue['file'].name}:\n"
                for path in issue['paths']:
                    error_msg += f"  {path}\n"
            
            error_msg += "\nUse Pensieve's screenshot directory configuration!"
            raise AssertionError(error_msg)
    
    def test_file_validation(self):
        """Test that file operations include proper validation."""
        all_issues = []
        
        # Only check production files
        for file_path in self.production_files + self.script_files:
            issues = self.error_analyzer.analyze_file_validation(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            # Group by validation type
            by_type = {}
            for issue in all_issues:
                issue_type = issue.split(' - ')[1] if ' - ' in issue else 'Other'
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(issue)
            
            logger.warning(f"FILE VALIDATION ISSUES: {len(all_issues)} total")
            for issue_type, issues in by_type.items():
                logger.warning(f"\n{issue_type} ({len(issues)} instances):")
                for issue in issues[:3]:
                    logger.warning(f"  {issue}")
    
    def test_path_handling(self):
        """Test that paths are handled properly (cross-platform, etc.)."""
        path_issues = []
        
        for file_path in self.python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    # Check for hardcoded path separators
                    if '\\\\' in line or ('"/' in line and 'http' not in line):
                        path_issues.append({
                            'file': file_path,
                            'line': i + 1,
                            'issue': 'Hardcoded path separator'
                        })
                    
                    # Check for string path concatenation instead of Path.joinpath
                    import re
                    if re.search(r'["\'][^"\']+["\']\s*\+\s*["\'][/\\]', line):
                        path_issues.append({
                            'file': file_path,
                            'line': i + 1,
                            'issue': 'String path concatenation'
                        })
            except Exception:
                continue
        
        if path_issues:
            logger.info(f"Path handling suggestions: {len(path_issues)} issues")
            for issue in path_issues[:5]:
                logger.info(f"  {issue['file'].name}:{issue['line']} - {issue['issue']}")
            logger.info("\nUse pathlib.Path for cross-platform compatibility!")
    
    def test_file_permissions(self):
        """Test that file operations check permissions properly."""
        permission_issues = []
        
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                # Check for file operations without permission checks
                file_ops = ['open(', 'Path(', '.write', '.read', '.mkdir', '.unlink']
                
                for op in file_ops:
                    if op in content:
                        # Check if there are permission checks nearby
                        if not any(check in content for check in [
                            'os.access', 'try:', 'except Permission',
                            'except OSError', '.exists()', '.is_file()'
                        ]):
                            permission_issues.append({
                                'file': file_path,
                                'operation': op
                            })
                            break
            except Exception:
                continue
        
        if permission_issues:
            logger.info("File permission check suggestions:")
            for issue in permission_issues[:5]:
                logger.info(f"  {issue['file'].name}: {issue['operation']} without permission check")
    
    def test_temp_file_handling(self):
        """Test that temporary files are handled properly."""
        temp_issues = []
        
        for file_path in self.python_files:
            try:
                content = file_path.read_text()
                
                # Check for temp file usage
                if any(term in content for term in ['tempfile', 'tmp/', '/tmp', 'temp_']):
                    # Check for proper cleanup
                    has_cleanup = any(pattern in content for pattern in [
                        'with tempfile.', 'finally:', '.cleanup()',
                        'atexit.register', 'contextmanager'
                    ])
                    
                    if not has_cleanup:
                        temp_issues.append(file_path)
            except Exception:
                continue
        
        if temp_issues:
            logger.info("Temporary file handling suggestions:")
            for f in temp_issues[:5]:
                logger.info(f"  {f.name}: Ensure temp files are cleaned up")
            logger.info("\nUse context managers or try/finally for cleanup!")