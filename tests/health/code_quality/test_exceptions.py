"""Test for exception handling patterns and code quality."""
import logging
import os
import re
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)


class TestExceptionHandling:
    """Test for proper exception handling patterns."""
    
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
    
    def test_bare_except_clauses(self):
        """Test for dangerous bare except clauses"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        bare_except_files = []
        
        for file_path in python_files:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Look for bare except: clauses
                if stripped == 'except:' or stripped.startswith('except:'):
                    bare_except_files.append(f"{file_path}:{i+1}")
        
        assert not bare_except_files, f"Found dangerous bare except clauses: {bare_except_files}"
    
    def test_specific_exception_handling(self):
        """Test that exceptions are handled with specific types"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        generic_except_files = []
        
        for file_path in python_files:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Look for overly broad exception handling
                if re.match(r'except\s+Exception\s*:', stripped):
                    # Check if there's a more specific handler nearby
                    context_start = max(0, i - 10)
                    context_end = min(len(lines), i + 10)
                    context = lines[context_start:context_end]
                    
                    # If this is the only except clause, flag it
                    except_count = sum(1 for l in context if 'except' in l)
                    if except_count == 1:
                        generic_except_files.append(f"{file_path}:{i+1} - Consider more specific exception")
        
        # Just warn about generic exceptions
        if generic_except_files:
            logger.warning(f"Found generic exception handlers: {len(generic_except_files)} instances")
            for item in generic_except_files[:3]:
                logger.warning(f"  {item}")
    
    def test_error_messages(self):
        """Test that exceptions include helpful error messages"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        issues = []
        
        for file_path in python_files:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Look for raise statements without messages
                if re.match(r'^\s*raise\s+\w+Exception\(\s*\)', line):
                    issues.append(f"{file_path}:{i+1} - Exception raised without message")
                # Look for re-raising without context
                elif re.match(r'^\s*raise\s+\w+Exception\s*$', line):
                    # Check if it's a simple re-raise (which is fine)
                    if not re.match(r'^\s*raise\s*$', line):
                        issues.append(f"{file_path}:{i+1} - Consider adding error context")
        
        # Just warn about error message issues
        if issues:
            logger.info(f"Exception message suggestions: {len(issues)} instances")
            for issue in issues[:3]:
                logger.info(f"  {issue}")
    
    def test_exception_logging(self):
        """Test that exceptions are properly logged"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        issues = []
        
        for file_path in python_files:
            # Skip test files
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Check if file imports logging
            has_logging = 'import logging' in content or 'from logging import' in content
            
            for i, line in enumerate(lines):
                if 'except' in line and ':' in line:
                    # Look at the except block
                    block_start = i + 1
                    block_lines = []
                    
                    # Collect lines in the except block
                    for j in range(block_start, min(block_start + 10, len(lines))):
                        if j < len(lines) and lines[j].strip():
                            if not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                                break
                            block_lines.append(lines[j])
                    
                    block_content = '\n'.join(block_lines)
                    
                    # Check if exception is logged
                    if has_logging and block_content:
                        if not any(log_term in block_content for log_term in 
                                 ['logger.', 'logging.', 'log.', 'print(']):
                            if 'pass' not in block_content and 'raise' not in block_content:
                                issues.append(f"{file_path}:{i+1} - Exception not logged")
        
        # Just warn about logging issues
        if issues:
            logger.info(f"Exception logging suggestions: {len(issues)} instances")
            for issue in issues[:5]:
                logger.info(f"  {issue}")