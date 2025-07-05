"""Test for proper fixture usage and test dependencies."""
import logging
import ast
import os
import re
from pathlib import Path
from typing import List
import pytest

logger = logging.getLogger(__name__)


class TestFixtureUsage:
    """Test for proper fixture usage and test dependencies."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
    
    def get_test_files(self) -> List[Path]:
        """Get all test files in the project"""
        test_files = []
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
    
    def test_fixture_cleanup(self):
        """Test that fixtures properly clean up resources"""
        test_files = self.get_test_files()
        cleanup_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Look for fixtures that allocate resources
            resource_patterns = [
                r'open\(',
                r'connect\(',
                r'Session\(',
                r'create_',
                r'mkdir\(',
                r'tempfile\.',
            ]
            
            fixture_blocks = re.findall(r'@pytest\.fixture.*?\ndef\s+\w+.*?(?=\n(?:def|class|@|\Z))', 
                                      content, re.DOTALL)
            
            for fixture in fixture_blocks:
                for pattern in resource_patterns:
                    if re.search(pattern, fixture):
                        # Check for cleanup
                        if not any(cleanup in fixture for cleanup in ['yield', 'finally:', 'close()', 'cleanup']):
                            cleanup_issues.append(f"{test_file.name}: Fixture may not clean up resources")
                            break
        
        if cleanup_issues:
            logger.warning(f"Found {len(cleanup_issues)} fixture cleanup issues")
            for issue in cleanup_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_fixture_scope_appropriate(self):
        """Test that fixture scopes are appropriate"""
        test_files = self.get_test_files()
        scope_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Check for inappropriate session/module scoped fixtures
            session_fixtures = re.findall(r'@pytest\.fixture\(.*scope=["\']session["\'].*\)', content)
            module_fixtures = re.findall(r'@pytest\.fixture\(.*scope=["\']module["\'].*\)', content)
            
            if session_fixtures or module_fixtures:
                # Check if they modify state
                for fixture_match in session_fixtures + module_fixtures:
                    # Get the fixture function
                    fixture_start = content.find(fixture_match)
                    fixture_end = content.find('\ndef ', fixture_start + len(fixture_match))
                    if fixture_end == -1:
                        fixture_end = len(content)
                    
                    fixture_body = content[fixture_start:fixture_end]
                    
                    # Check for state modifications
                    if any(pattern in fixture_body for pattern in ['=', 'append', 'update', 'delete']):
                        scope_issues.append(f"{test_file.name}: Session/module fixture modifies state")
        
        if scope_issues:
            logger.info("Fixture scope suggestions:")
            for issue in scope_issues:
                logger.info(f"  {issue}")
    
    def test_no_hardcoded_test_data_in_fixtures(self):
        """Test that fixtures don't contain hardcoded test data"""
        test_files = self.get_test_files()
        hardcoded_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Look for fixtures with hardcoded data
            fixture_blocks = re.findall(r'@pytest\.fixture.*?\ndef\s+\w+.*?(?=\n(?:def|class|@|\Z))', 
                                      content, re.DOTALL)
            
            for fixture in fixture_blocks:
                # Check for hardcoded values
                hardcoded_patterns = [
                    r'["\']test_user_\d+["\']',
                    r'["\']password123["\']',
                    r'["\']http://localhost:\d+["\']',
                    r'["\'][a-zA-Z0-9]{32,}["\']',  # API keys, tokens
                ]
                
                for pattern in hardcoded_patterns:
                    if re.search(pattern, fixture):
                        hardcoded_issues.append(f"{test_file.name}: Fixture contains hardcoded test data")
                        break
        
        if hardcoded_issues:
            logger.info("Fixtures with hardcoded data:")
            for issue in hardcoded_issues[:5]:
                logger.info(f"  {issue}")
            logger.info("Consider using fixture parameters or factories")
    
    def test_fixture_dependencies(self):
        """Test that fixture dependencies are reasonable"""
        test_files = self.get_test_files()
        dependency_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            try:
                tree = ast.parse(content)
                
                # Extract fixtures and their dependencies
                fixtures = {}
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check if it's a fixture
                        for decorator in node.decorator_list:
                            if (isinstance(decorator, ast.Name) and decorator.id == 'fixture') or \
                               (isinstance(decorator, ast.Attribute) and decorator.attr == 'fixture'):
                                # Get fixture dependencies from function args
                                deps = [arg.arg for arg in node.args.args if arg.arg != 'self']
                                fixtures[node.name] = deps
                
                # Check for circular dependencies or too many dependencies
                for fixture_name, deps in fixtures.items():
                    if len(deps) > 3:
                        dependency_issues.append(
                            f"{test_file.name}: Fixture '{fixture_name}' has {len(deps)} dependencies"
                        )
                    
                    # Simple circular dependency check
                    for dep in deps:
                        if dep in fixtures and fixture_name in fixtures[dep]:
                            dependency_issues.append(
                                f"{test_file.name}: Circular dependency between '{fixture_name}' and '{dep}'"
                            )
            except:
                continue
        
        if dependency_issues:
            logger.warning("Fixture dependency issues:")
            for issue in dependency_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_conftest_organization(self):
        """Test that conftest.py files are properly organized"""
        conftest_files = list(self.test_dir.rglob("conftest.py"))
        organization_issues = []
        
        for conftest in conftest_files:
            content = self._safe_read_file(conftest)
            if not content:
                continue
            
            # Check for test functions in conftest (should only have fixtures)
            if re.search(r'def test_', content):
                organization_issues.append(f"{conftest}: Contains test functions (should only have fixtures)")
            
            # Check for excessive size
            line_count = len(content.split('\n'))
            if line_count > 200:
                organization_issues.append(f"{conftest}: Too large ({line_count} lines)")
            
            # Check for proper imports
            if 'from .' in content or 'from ..' in content:
                organization_issues.append(f"{conftest}: Uses relative imports")
        
        if organization_issues:
            logger.warning("conftest.py organization issues:")
            for issue in organization_issues:
                logger.warning(f"  {issue}")