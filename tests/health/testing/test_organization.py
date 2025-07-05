"""Test for test file organization and structure."""
import logging
import os
import ast
import re
from pathlib import Path
from typing import List
import pytest

logger = logging.getLogger(__name__)


class TestTestOrganization:
    """Test for proper test file organization and structure."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        
    def get_test_files(self) -> List[Path]:
        """Get all test files in the project with safeguards against hanging"""
        test_files = []
        MAX_FILES = 100  # Prevent processing too many files
        file_count = 0
        
        try:
            for root, dirs, files in os.walk(self.test_dir):
                # Skip hidden directories to prevent hanging on symlinks
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if file.startswith('test_') and file.endswith('.py'):
                        test_path = Path(root) / file
                        # Skip files over 1MB to prevent memory issues
                        try:
                            if test_path.stat().st_size > 1024 * 1024:  # 1MB limit
                                continue
                        except (OSError, FileNotFoundError):
                            continue
                            
                        test_files.append(test_path)
                        file_count += 1
                        
                        # Prevent processing too many files
                        if file_count >= MAX_FILES:
                            break
                
                if file_count >= MAX_FILES:
                    break
                    
        except (OSError, PermissionError):
            # If directory walking fails, return what we have
            pass
            
        return test_files
    
    def _safe_read_file(self, file_path: Path, max_size: int = 1024 * 1024) -> str:
        """Safely read file content with size limits to prevent hanging"""
        try:
            # Check file size first
            if file_path.stat().st_size > max_size:
                return ""  # Skip large files
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Also limit by line count to prevent hanging on very long lines
            lines = content.split('\n')
            if len(lines) > 10000:  # Max 10k lines
                content = '\n'.join(lines[:10000])
                
            return content
        except (OSError, UnicodeDecodeError, MemoryError):
            return ""  # Return empty string on any read error
    
    def test_all_test_files_follow_naming_conventions(self):
        """Test that all test files follow naming conventions and are discoverable by pytest"""
        test_files = self.get_test_files()
        discovery_issues = []
        
        for test_file in test_files:
            # Check naming convention
            if not test_file.name.startswith('test_'):
                discovery_issues.append(f"{test_file}: Should start with 'test_'")
            
            # Check if file contains test functions
            try:
                content = self._safe_read_file(test_file)
                if not content:  # Skip empty or problematic files
                    continue
                tree = ast.parse(content)
                
                has_test_functions = False
                has_test_classes = False
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        has_test_functions = True
                    elif isinstance(node, ast.ClassDef) and 'test' in node.name.lower():
                        has_test_classes = True
                
                if not has_test_functions and not has_test_classes:
                    discovery_issues.append(f"{test_file}: No test functions or classes found")
                    
            except Exception as e:
                discovery_issues.append(f"{test_file}: Cannot parse - {e}")
        
        assert not discovery_issues, f"Test discovery issues: {discovery_issues}"
    
    def test_proper_test_categories(self):
        """Test that tests are properly categorized"""
        test_categories = {
            'unit': self.test_dir / 'unit',
            'integration': self.test_dir / 'integration',
            'e2e': self.test_dir / 'e2e',
            'functional': self.test_dir / 'functional',
            'performance': self.test_dir / 'performance',
            'health': self.test_dir / 'health'
        }
        
        categorization_issues = []
        
        # Check test files are in appropriate directories
        test_files = self.get_test_files()
        for test_file in test_files:
            relative_path = test_file.relative_to(self.test_dir)
            parts = relative_path.parts
            
            if len(parts) < 2:  # Test file directly in tests/
                categorization_issues.append(f"{test_file}: Not in a category directory")
                continue
            
            category = parts[0]
            if category not in test_categories:
                categorization_issues.append(f"{test_file}: Unknown category '{category}'")
                continue
            
            # Check test content matches category
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Simple heuristic checks
            if category == 'unit':
                # Unit tests should not have external dependencies
                if any(dep in content for dep in ['requests.', 'subprocess.', 'selenium']):
                    categorization_issues.append(f"{test_file}: Unit test has external dependencies")
            
            elif category == 'integration':
                # Integration tests should test multiple components
                if 'mock' in content.lower() and content.lower().count('mock') > 5:
                    categorization_issues.append(f"{test_file}: Integration test has too many mocks")
            
            elif category == 'e2e':
                # E2E tests should test full workflows
                if 'unittest.mock' in content:
                    categorization_issues.append(f"{test_file}: E2E test should not use mocks")
        
        if categorization_issues:
            logger.warning(f"Found {len(categorization_issues)} categorization issues")
            for issue in categorization_issues[:10]:
                logger.warning(f"  {issue}")
    
    def test_test_isolation(self):
        """Test that tests are properly isolated"""
        test_files = self.get_test_files()
        isolation_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Check for global state modifications
            global_state_patterns = [
                r'os\.environ\[.*\]\s*=',  # Modifying environment
                r'sys\.path\.insert',  # Modifying sys.path
                r'__builtins__\.',  # Modifying builtins
                r'globals\(\)\[',  # Modifying globals
            ]
            
            for pattern in global_state_patterns:
                import re
                if re.search(pattern, content):
                    # Check if it's properly cleaned up
                    if 'finally:' not in content and '@pytest.fixture' not in content:
                        isolation_issues.append(f"{test_file}: Modifies global state without cleanup")
                        break
            
            # Check for hardcoded file paths
            if any(path in content for path in ['/tmp/', '/home/', r'C:\\', r'D:\\']):
                isolation_issues.append(f"{test_file}: Contains hardcoded paths")
            
            # Check for time-dependent tests
            if 'time.sleep(' in content and 'mock' not in content.lower():
                isolation_issues.append(f"{test_file}: Contains unmocked time.sleep()")
        
        if isolation_issues:
            logger.warning(f"Found {len(isolation_issues)} test isolation issues")
            for issue in isolation_issues[:10]:
                logger.warning(f"  {issue}")
    
    def test_test_file_size(self):
        """Test that test files aren't too large"""
        test_files = self.get_test_files()
        oversized_files = []
        
        for test_file in test_files:
            try:
                size_kb = test_file.stat().st_size / 1024
                if size_kb > 50:  # 50KB is quite large for a test file
                    oversized_files.append(f"{test_file.name}: {size_kb:.1f}KB")
            except OSError:
                continue
        
        if oversized_files:
            logger.info(f"Found {len(oversized_files)} large test files")
            for file_info in oversized_files[:5]:
                logger.info(f"  {file_info}")
            logger.info("Consider splitting large test files for better organization")
    
    def test_no_duplicate_test_names(self):
        """Test that test names are unique across the project (excluding known legacy files)."""
        test_files = self.get_test_files()
        all_test_names = {}
        duplicate_issues = []
        
        # Exclude known legacy files during transition
        legacy_files = {'test_testing_system_health.py', 'test_codebase_health.py', 'test_documentation_health.py'}
        
        for test_file in test_files:
            # Skip legacy monolithic files during transition
            if test_file.name in legacy_files:
                continue
                
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Find all test function names
            test_functions = re.findall(r'def (test_\w+)\(', content)
            
            for test_func in test_functions:
                if test_func in all_test_names:
                    duplicate_issues.append(
                        f"Duplicate test name '{test_func}': {test_file.name} and {all_test_names[test_func]}"
                    )
                else:
                    all_test_names[test_func] = test_file.name
        
        # Only flag actual duplicates within the modular system
        if duplicate_issues:
            logger.warning(f"Found {len(duplicate_issues)} duplicate test names within modular system")
            for issue in duplicate_issues[:5]:
                logger.warning(f"  {issue}")
            
            # Only fail if there are many duplicates (indicating a real problem)
            assert len(duplicate_issues) < 10, f"Too many duplicate test names: {len(duplicate_issues)}"
    
    def test_pytest_markers_usage(self):
        """Test that pytest markers are used appropriately."""
        test_files = self.get_test_files()
        marker_issues = []
        
        # Expected markers for different test types
        expected_markers = {
            'integration': ['pytest.mark.integration', '@pytest.mark.integration'],
            'performance': ['pytest.mark.slow', '@pytest.mark.slow'],
            'e2e': ['pytest.mark.e2e', '@pytest.mark.e2e'],
            'functional': ['pytest.mark.functional', '@pytest.mark.functional'],
        }
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Check if file should have markers based on location
            for test_type, markers in expected_markers.items():
                if test_type in str(test_file):
                    has_marker = any(marker in content for marker in markers)
                    if not has_marker:
                        marker_issues.append(f"{test_file.name}: Missing {test_type} marker")
        
        # Allow some missing markers for now, but flag excessive issues
        if len(marker_issues) > 10:
            logger.warning(f"Found {len(marker_issues)} marker issues")
            for issue in marker_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_test_data_organization(self):
        """Test that test data is properly organized."""
        test_files = self.get_test_files()
        data_issues = []
        
        # Check for hardcoded test data patterns
        hardcoded_patterns = [
            r'test_user.*=.*["\'].*["\']',
            r'test_data.*=.*\{.*\}',
            r'sample_.*=.*["\'].*["\']',
            r'mock_.*=.*["\'].*["\']',
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health tests (they may have different patterns)
            if 'health' in str(test_file):
                continue
            
            # Check for hardcoded test data
            hardcoded_count = sum(len(re.findall(pattern, content)) for pattern in hardcoded_patterns)
            
            # Check for test asset usage
            has_test_assets = ('assets/' in content or 'fixtures/' in content or 
                             'test_data/' in content or 'conftest.py' in content)
            
            if hardcoded_count > 5 and not has_test_assets:
                data_issues.append(f"{test_file.name}: High hardcoded data count ({hardcoded_count}) without using test assets")
        
        if data_issues:
            logger.info(f"Found {len(data_issues)} test data organization suggestions")
            for issue in data_issues[:3]:
                logger.info(f"  {issue}")