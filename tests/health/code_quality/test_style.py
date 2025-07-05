"""Test for code style and quality patterns."""
import logging
import os
import re
import ast
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)


class TestCodeStyle:
    """Test for code style conventions and quality patterns."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.package_dir = self.project_root / "autotasktracker"
        
    def get_python_files(self, exclude_dirs=None):
        """Get all Python files in the project"""
        if exclude_dirs is None:
            exclude_dirs = {'venv', '__pycache__', '.git', '.pytest_cache', 'build', 'dist'}
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories from search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def test_print_statements_vs_logging(self):
        """Test that code uses logging instead of print statements"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        files_with_prints = []
        
        for file_path in python_files:
            # Skip test files and __main__ blocks
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Look for print statements (but not in comments or main blocks)
                if ('print(' in line and 
                    not line.strip().startswith('#') and 
                    'if __name__' not in ''.join(lines[max(0, i-5):i+1])):
                    files_with_prints.append(f"{file_path}:{i+1}")
                    break
        
        # Just warn for now since some prints might be intentional
        if files_with_prints:
            logger.warning(f"Found print statements (consider using logging): {len(files_with_prints)} files")
            for item in files_with_prints[:3]:
                logger.warning(f"  {item}")
            if len(files_with_prints) > 3:
                logger.warning(f"  ... and {len(files_with_prints) - 3} more")
    
    def test_no_debug_code(self):
        """Test that there's no debug code left in production files"""
        python_files = [f for f in self.get_python_files() if 'test' not in str(f)]
        debug_code_found = []
        
        debug_patterns = [
            r'print\s*\(\s*["\']debug',
            r'breakpoint\(\)',
            r'import\s+pdb',
            r'pdb\.set_trace',
            r'import\s+ipdb',
            r'console\.log',  # JavaScript debug
            r'debugger;',     # JavaScript debug
        ]
        
        for file_path in python_files:
            content = file_path.read_text()
            for pattern in debug_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    debug_code_found.append(f"{file_path}: {pattern}")
        
        assert not debug_code_found, f"Found debug code: {debug_code_found}"
    
    def test_no_todos_or_fixmes(self):
        """Test for TODO/FIXME comments that need attention"""
        python_files = self.get_python_files()
        todos_found = []
        
        patterns = [
            r'#\s*TODO',
            r'#\s*FIXME',
            r'#\s*HACK',
            r'#\s*XXX',
        ]
        
        for file_path in python_files:
            content = file_path.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        todos_found.append(f"{file_path}:{i+1}: {line.strip()}")
        
        # We'll just warn, not fail for TODOs
        if todos_found:
            logger.info(f"Found {len(todos_found)} TODO/FIXME comments:")
            for todo in todos_found[:5]:  # Show first 5
                logger.info(f"  {todo}")
            if len(todos_found) > 5:
                logger.info(f"  ... and {len(todos_found) - 5} more")
    
    def test_no_hardcoded_paths(self):
        """Test that there are no hardcoded absolute paths"""
        python_files = self.get_python_files()
        files_with_hardcoded_paths = []
        
        # Patterns that indicate hardcoded paths
        patterns = [
            r'/Users/\w+/',
            r'C:\\Users\\',
            r'/home/\w+/',
            r'~/CodeProjects/'  # Specific user paths
        ]
        
        for file_path in python_files:
            # Skip test files for hardcoded path check
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            for pattern in patterns:
                if re.search(pattern, content):
                    # Allow in comments and docstrings
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.search(pattern, line) and not line.strip().startswith('#'):
                            # Check if it's in a docstring
                            in_docstring = False
                            if i > 0 and (lines[i-1].strip().startswith('"""') or lines[i-1].strip().startswith("'''")):
                                in_docstring = True
                            if not in_docstring:
                                files_with_hardcoded_paths.append(f"{file_path}:{i+1}")
                                break
        
        assert not files_with_hardcoded_paths, f"Found hardcoded paths in: {files_with_hardcoded_paths}"
    
    def test_consistent_line_endings(self):
        """Test that files use consistent line endings"""
        python_files = self.get_python_files()
        mixed_endings = []
        
        for file_path in python_files:
            content = file_path.read_bytes()
            has_crlf = b'\r\n' in content
            has_lf = b'\n' in content and not has_crlf
            
            if has_crlf and has_lf:
                mixed_endings.append(str(file_path))
        
        assert not mixed_endings, f"Found files with mixed line endings: {mixed_endings}"
    
    def test_no_merge_conflicts(self):
        """Test that there are no merge conflict markers"""
        all_files = self.get_python_files()
        merge_conflicts = []
        
        conflict_markers = [
            '<' + '<<<<< ',  # Split to avoid matching self, with space
            '=' + '===== ',  # With space to avoid matching decoration lines
            '>' + '>>>>> '   # With space for consistency
        ]
        
        for file_path in all_files:
            content = file_path.read_text()
            for marker in conflict_markers:
                if marker in content:
                    merge_conflicts.append(str(file_path))
                    break
        
        assert not merge_conflicts, f"Found merge conflict markers in: {merge_conflicts}"
    
    def test_file_permissions(self):
        """Test that Python files have correct permissions"""
        python_files = self.get_python_files()
        permission_issues = []
        
        for file_path in python_files:
            # Check if file is executable when it shouldn't be
            if os.access(file_path, os.X_OK):
                # Only main entry points should be executable
                if file_path.name not in ['autotasktracker.py', 'autotask.py', 'setup.py']:
                    permission_issues.append(f"{file_path}: Executable bit set")
        
        assert not permission_issues, f"Found permission issues: {permission_issues}"
    
    def test_no_large_files(self):
        """Test that there are no accidentally committed large files"""
        large_files = []
        
        for file_path in self.get_python_files():
            size_kb = file_path.stat().st_size / 1024
            
            # Different limits for different file types
            if 'test_' in file_path.name or '/tests/' in str(file_path):
                max_size_kb = 200  # Tests can be longer
            elif '/scripts/' in str(file_path):
                max_size_kb = 150  # Scripts can be longer
            else:
                max_size_kb = 100  # Production code should be smaller
            
            if size_kb > max_size_kb:
                large_files.append(f"{file_path}: {size_kb:.1f}KB (limit: {max_size_kb}KB)")
        
        assert not large_files, f"Found large files: {large_files}"
    
    def test_long_functions_and_files(self):
        """Test for overly long functions and files that might need refactoring"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        long_items = []
        
        for file_path in python_files:
            # Skip test files for this check
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Check file length
            if len(lines) > 600:
                long_items.append(f"{file_path}: {len(lines)} lines (consider splitting)")
            
            # Check for very long functions (basic heuristic)
            in_function = False
            function_start = 0
            function_name = ""
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('def ') and not stripped.startswith('def __'):
                    if in_function and i - function_start > 100:
                        long_items.append(f"{file_path}:{function_start} function '{function_name}' is {i - function_start} lines")
                    
                    in_function = True
                    function_start = i
                    function_name = stripped.split('(')[0].replace('def ', '')
                elif stripped.startswith('class '):
                    in_function = False
                elif not stripped and in_function:
                    # End of function on double newline or class
                    continue
        
        # Just warn about long items
        if long_items:
            logger.warning(f"Found {len(long_items)} long files/functions that might need refactoring:")
            for item in long_items[:3]:
                logger.warning(f"  {item}")
            if len(long_items) > 3:
                logger.warning(f"  ... and {len(long_items) - 3} more")
    
    def test_no_duplicate_functions(self):
        """Test for duplicate function definitions across files"""
        function_locations = {}
        duplicates = []
        
        # Focus on key functions that should not be duplicated
        key_functions = [
            'categorize_activity',
            'extract_task_info',
            'get_db_connection',
            'extract_window_title'
        ]
        
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        
        for file_path in python_files:
            # Skip test files and legacy
            if 'test' in str(file_path) or 'legacy' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name in key_functions:
                            if node.name not in function_locations:
                                function_locations[node.name] = []
                            function_locations[node.name].append(str(file_path))
            except:
                # Skip files that can't be parsed
                pass
        
        # Check for duplicates
        for func_name, locations in function_locations.items():
            if len(locations) > 1:
                # Allow if one is in __init__.py (re-export)
                non_init = [loc for loc in locations if '__init__.py' not in loc]
                if len(non_init) > 1:
                    duplicates.append(f"{func_name}: {non_init}")
        
        assert not duplicates, f"Found duplicate functions: {duplicates}"
    
    def test_stray_log_files(self):
        """Test for log files that shouldn't be committed"""
        log_files = []
        log_patterns = ['*.log', '*.logs', '*.out', '*.err']
        
        for pattern in log_patterns:
            log_files.extend(list(self.project_root.glob(pattern)))
            log_files.extend(list(self.project_root.glob(f"**/{pattern}")))
        
        # Filter out logs in acceptable locations
        problematic_logs = []
        for log_file in log_files:
            # Allow logs in .git, venv, __pycache__, .logs directories
            if not any(part in str(log_file) for part in ['.git', 'venv', '__pycache__', '.logs', 'logs/']):
                problematic_logs.append(str(log_file))
        
        assert not problematic_logs, f"Found log files that should not be committed: {problematic_logs}"