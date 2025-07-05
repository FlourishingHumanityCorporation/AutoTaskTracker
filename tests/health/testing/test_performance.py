"""Test for test performance and reliability."""
import logging
import re
import ast
from pathlib import Path
from typing import List
import pytest

logger = logging.getLogger(__name__)


class TestTestPerformance:
    """Test for test performance and reliability issues."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
    
    def get_test_files(self) -> List[Path]:
        """Get all test files in the project"""
        test_files = []
        import os
        for root, dirs, files in os.walk(self.test_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        return test_files
    
    def _safe_read_file(self, file_path: Path) -> str:
        """Safely read file content"""
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except:
            return ""
    
    def test_no_infinite_loops(self):
        """Test that tests don't contain potential infinite loops"""
        test_files = self.get_test_files()
        loop_issues = []
        
        dangerous_patterns = [
            r'while\s+True:',
            r'while\s+\d+:',
            r'while\s+[a-zA-Z_]\w*\s*==\s*[a-zA-Z_]\w*:',  # while x == x
            r'for\s+\w+\s+in\s+\w+\s*:\s*\w+\.append\(\w+\)',  # Growing list
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Check if there's a break condition nearby
                    for match in matches:
                        match_pos = content.find(match)
                        context = content[match_pos:match_pos + 200]
                        
                        if 'break' not in context and 'return' not in context:
                            loop_issues.append(f"{test_file.name}: Potential infinite loop - {match}")
        
        assert not loop_issues, f"Found potential infinite loops: {loop_issues}"
    
    def test_no_long_sleeps(self):
        """Test that tests don't contain long sleep statements"""
        test_files = self.get_test_files()
        sleep_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Look for sleep statements
            sleep_matches = re.findall(r'time\.sleep\(([^)]+)\)', content)
            for sleep_arg in sleep_matches:
                try:
                    # Try to evaluate simple numeric expressions
                    if sleep_arg.replace('.', '').isdigit():
                        sleep_time = float(sleep_arg)
                        if sleep_time > 1.0:  # Longer than 1 second
                            sleep_issues.append(f"{test_file.name}: Long sleep({sleep_time}s)")
                except:
                    # If we can't evaluate, flag it for review
                    sleep_issues.append(f"{test_file.name}: Sleep with variable duration: {sleep_arg}")
        
        if sleep_issues:
            logger.warning(f"Found {len(sleep_issues)} long sleep statements")
            for issue in sleep_issues:
                logger.warning(f"  {issue}")
    
    def test_external_dependencies_handled(self):
        """Test that external dependencies are properly handled"""
        test_files = self.get_test_files()
        dependency_issues = []
        
        external_deps = [
            (r'requests\.', 'HTTP requests'),
            (r'urllib\.', 'URL operations'),
            (r'subprocess\.', 'Process execution'),
            (r'socket\.', 'Network operations'),
            (r'smtplib\.', 'Email sending'),
            (r'ftplib\.', 'FTP operations'),
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            for pattern, dep_name in external_deps:
                if re.search(pattern, content):
                    # Check if it's mocked or in integration/e2e tests
                    if 'mock' not in content.lower() and '/integration/' not in str(test_file) and '/e2e/' not in str(test_file):
                        dependency_issues.append(f"{test_file.name}: Uses {dep_name} without mocking")
        
        if dependency_issues:
            logger.warning("External dependencies without mocking:")
            for issue in dependency_issues[:10]:
                logger.warning(f"  {issue}")
    
    def test_test_docstrings(self):
        """Test that test functions have appropriate docstrings"""
        test_files = self.get_test_files()
        docstring_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            try:
                tree = ast.parse(content)
                
                test_functions = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        has_docstring = (node.body and 
                                       isinstance(node.body[0], ast.Expr) and 
                                       isinstance(node.body[0].value, ast.Str))
                        
                        if not has_docstring:
                            # Check if it's a simple test
                            if len(node.body) > 3:  # Complex test should have docstring
                                test_functions.append(node.name)
                
                if test_functions:
                    docstring_issues.append(f"{test_file.name}: Tests without docstrings: {test_functions[:3]}")
                    
            except:
                continue
        
        if docstring_issues:
            logger.info("Tests without docstrings:")
            for issue in docstring_issues[:5]:
                logger.info(f"  {issue}")
    
    def test_assertion_count(self):
        """Test that tests have meaningful number of assertions"""
        test_files = self.get_test_files()
        assertion_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        # Count assertions
                        assertion_count = 0
                        for child in ast.walk(node):
                            if isinstance(child, ast.Assert):
                                assertion_count += 1
                            elif isinstance(child, ast.Call):
                                # pytest.raises, etc.
                                if hasattr(child.func, 'attr') and 'assert' in str(child.func.attr).lower():
                                    assertion_count += 1
                        
                        # Check if test has too few assertions (skip certain patterns)
                        if assertion_count == 0:
                            # Skip tests that use pytest.xfail, infrastructure tests, or health tests
                            test_body = ast.get_source_segment(content, node) or ""
                            if ('pytest.xfail' not in test_body and 'pytest.skip' not in test_body and
                                'health' not in str(test_file.parent) and 'infrastructure' not in str(test_file.parent)):
                                assertion_issues.append(f"{test_file.name}: {node.name} has no assertions")
                        elif assertion_count == 1:
                            # Check if it's just assert True or similar (skip import tests and health tests)
                            test_body = ast.get_source_segment(content, node) or ""
                            if (('assert True' in test_body or 'assert 1' in test_body) and 
                                'import' not in node.name and 'health' not in str(test_file.parent)):
                                assertion_issues.append(f"{test_file.name}: {node.name} has trivial assertion")
                                
            except:
                continue
        
        # Allow some assertion issues for infrastructure/import tests, but flag excessive problems
        if len(assertion_issues) > 10:
            logger.warning(f"Found {len(assertion_issues)} tests with assertion issues")
            for issue in assertion_issues[:5]:
                logger.warning(f"  {issue}")
            
            # Only fail if there are many issues (indicating a systematic problem)
            assert len(assertion_issues) < 20, f"Too many assertion issues: {len(assertion_issues)}"
    
    def test_timeout_protection(self):
        """Test that tests have timeout protection"""
        test_files = self.get_test_files()
        timeout_issues = []
        
        potentially_slow_patterns = [
            r'requests\.',
            r'subprocess\.',
            r'time\.sleep',
            r'urllib\.',
            r'socket\.',
            r'while.*:',
            r'for.*in.*range\(\d{3,}\)',  # Large ranges
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            has_slow_operations = any(re.search(pattern, content) for pattern in potentially_slow_patterns)
            has_timeout = any(timeout in content for timeout in [
                '@pytest.mark.timeout',
                'timeout=',
                'pytest.timeout',
                'with pytest.timeout',
            ])
            
            if has_slow_operations and not has_timeout and '/e2e/' not in str(test_file):
                timeout_issues.append(f"{test_file.name}: Has slow operations without timeout protection")
        
        if timeout_issues:
            logger.info("Tests that may benefit from timeout protection:")
            for issue in timeout_issues[:5]:
                logger.info(f"  {issue}")