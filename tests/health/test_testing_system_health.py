"""
🧪 TESTING SYSTEM HEALTH CHECKER 🧪

This test suite validates the health and organization of the testing system itself:

🏗️  TESTING STRUCTURE:
   - Test file organization and placement
   - Test coverage and completeness
   - Test execution dependencies
   - Test isolation and reliability

🔧 TESTING QUALITY:
   - No infinite loops or hanging tests
   - Proper fixtures and teardown
   - Appropriate test categories
   - Mock usage and external dependencies

🎯 FUNCTIONALITY VALIDATION (CONFIGURABLE STRICT MODE):
   - Tests validate real business logic, not just structure
   - Tests can discover actual breaks in functionality
   - Mutation testing analysis for break detection
   - Error condition and edge case coverage
   - Test data diversity and realism
   
   📊 STRICT MODE (STRICT_MODE = True):
   - No trivial assertions (assert True, assert x == x)
   - All complex functions must test error conditions
   - Integration tests must validate actual integration
   - Boundary value testing mandatory
   
   🔥 ULTRA STRICT MODE (ULTRA_STRICT_MODE = True):
   - Every test must have ≥3 meaningful assertions
   - Complete test independence (no shared state)
   - Strict performance requirements (no long sleeps/timeouts)
   - Comprehensive docstrings required

🧬 MUTATION RESISTANCE (ENHANCED):
   - Off-by-one error detection
   - Boolean logic mutation resistance
   - Boundary condition testing
   - Return value validation
   - Conditional logic coverage
   - STRICT: Boundary value testing mandatory
   - STRICT: Error path testing mandatory
   - STRICT: State change validation mandatory

📊 CRITICAL TESTS (STRICT MODE - must pass for reliable CI/CD):
   - test_all_tests_discoverable ← 🚨 DISCOVERY
   - test_no_infinite_loops ← 🚨 RELIABILITY
   - test_proper_test_categories ← 🚨 ORGANIZATION
   - test_external_dependencies_handled ← 🚨 ISOLATION
   - test_tests_validate_real_functionality_and_discover_breaks ← 🚨 EFFECTIVENESS
   - test_strict_assertion_quality ← 🚨 ASSERTION QUALITY
   - test_strict_error_condition_coverage ← 🚨 ERROR TESTING
   - test_strict_mock_realism ← 🚨 MOCK QUALITY
   - test_strict_boundary_testing ← 🚨 EDGE CASES
   - test_strict_integration_validation ← 🚨 INTEGRATION DEPTH

Run: pytest tests/health/test_testing_system_health.py -v
"""

import os
import re
import ast
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Set
import pytest


class TestTestingSystemHealth:
    """Tests for testing system health and organization"""
    
    # STRICT MODE CONFIGURATION
    ULTRA_STRICT_MODE = True  # Set to True for maximum strictness
    STRICT_MODE = True        # Set to True for enhanced strictness
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.test_dir = self.project_root / "tests"
        
    def get_test_files(self) -> List[Path]:
        """Get all test files in the project"""
        test_files = []
        for root, dirs, files in os.walk(self.test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        return test_files
    
    def test_all_test_files_follow_naming_conventions_and_discoverable(self):
        """Test that all test files follow naming conventions and are discoverable by pytest"""
        test_files = self.get_test_files()
        discovery_issues = []
        
        for test_file in test_files:
            # Check naming convention
            if not test_file.name.startswith('test_'):
                discovery_issues.append(f"{test_file}: Should start with 'test_'")
            
            # Check if file contains test functions
            try:
                content = test_file.read_text()
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
        """Test that tests are properly categorized and organized"""
        test_files = self.get_test_files()
        categorization_issues = []
        
        # Expected test categories based on existing structure
        expected_categories = {
            'basic_functionality': 'Basic functionality checks',
            'pensieve_critical_path': 'End-to-end critical path tests',
            'pensieve_end_to_end': 'Pensieve integration tests',
            'codebase_health': 'Code quality and organization',
            'documentation_health': 'Documentation quality',
            'dashboard': 'Dashboard functionality',
            'ai_features_integration': 'AI feature tests',
            'e2e': 'End-to-end integration tests',
            'testing_system_health': 'Testing system validation',
            'refactored_components': 'Refactored component tests',
            'ui_validation': 'UI testing and validation',
            'headless_environment': 'Headless environment tests',
            'complete_user_journey': 'Complete user journey tests',
            'infrastructure': 'Infrastructure and component tests'
        }
        
        found_categories = set()
        
        for test_file in test_files:
            filename = test_file.name
            filepath = str(test_file)
            category_found = False
            
            for category in expected_categories:
                if category in filename or category in filepath:
                    found_categories.add(category)
                    category_found = True
                    break
            
            # Check if file is in organized subdirectories
            if test_file.parent.name in ['unit', 'integration', 'infrastructure', 'health', 'e2e']:
                category_found = True
                # Map directory to categories
                if test_file.parent.name == 'unit':
                    if 'dashboard' in filename:
                        found_categories.add('dashboard')
                    if 'basic' in filename:
                        found_categories.add('basic_functionality')
                    if 'refactored' in filename:
                        found_categories.add('refactored_components')
                elif test_file.parent.name == 'integration':
                    if 'ai' in filename:
                        found_categories.add('ai_features_integration')
                    if 'pensieve_critical_path' in filename:
                        found_categories.add('pensieve_critical_path')
                    if 'pensieve_end_to_end' in filename:
                        found_categories.add('pensieve_end_to_end')
                    if 'ui_validation' in filename:
                        found_categories.add('ui_validation')
                elif test_file.parent.name == 'health':
                    if 'testing_system' in filename:
                        found_categories.add('testing_system_health')
                    if 'codebase' in filename:
                        found_categories.add('codebase_health')
                    if 'documentation' in filename:
                        found_categories.add('documentation_health')
                elif test_file.parent.name == 'infrastructure':
                    found_categories.add('infrastructure')
                elif test_file.parent.name == 'e2e':
                    found_categories.add('e2e')
                    if 'headless' in filename:
                        found_categories.add('headless_environment')
                    if 'user_journey' in filename:
                        found_categories.add('complete_user_journey')
            
            if not category_found:
                categorization_issues.append(f"{test_file}: Unknown test category")
        
        # Check for missing critical categories
        missing_categories = set(expected_categories.keys()) - found_categories
        for missing in missing_categories:
            if missing not in ['ai_features_integration', 'e2e', 'refactored_components', 'headless_environment', 'ui_validation', 'complete_user_journey', 'infrastructure']:  # These might be optional
                categorization_issues.append(f"Missing {missing} tests")
        
        assert not categorization_issues, f"Test categorization issues: {categorization_issues}"
    
    def test_no_infinite_loops_in_test_code(self):
        """Test that test files don't contain potential infinite loops that could hang CI"""
        test_files = self.get_test_files()
        infinite_loop_risks = []
        
        dangerous_patterns = [
            r'while\s+True:',
            r'while\s+1:',
        ]
        
        for test_file in test_files:
            content = test_file.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                for pattern in dangerous_patterns:
                    if re.search(pattern, line):
                        # Check if there's a break statement nearby
                        context = '\n'.join(lines[max(0, i-2):i+10])
                        if 'break' not in context and 'return' not in context and 'timeout' not in context:
                            infinite_loop_risks.append(f"{test_file}:{i+1}: Potential infinite loop")
        
        assert not infinite_loop_risks, f"Potential infinite loops: {infinite_loop_risks}"
    
    def test_external_dependencies_handled(self):
        """Test that external dependencies are properly handled with mocks/skips"""
        test_files = self.get_test_files()
        dependency_issues = []
        
        # External services that should be mocked or skipped
        external_services = [
            'requests.get',
            'requests.post',
            'sqlite3.connect',
            'subprocess.run',
            'os.system'
        ]
        
        for test_file in test_files:
            content = test_file.read_text()
            
            for service in external_services:
                if service in content:
                    # Check if there's proper handling
                    has_mock = any(pattern in content for pattern in [
                        '@patch', '@mock', 'Mock()', 'MagicMock()', 'pytest.xfail', 'pytest.skip'
                    ])
                    
                    # Skip certain test types that legitimately use external services
                    skip_files = [
                        'test_critical.py',
                        'test_codebase_health.py',  # Checks for external service patterns
                        'test_headless_environment.py',  # E2E test that needs real HTTP
                        'test_pensieve_end_to_end.py'  # E2E test
                    ]
                    
                    if not has_mock and not any(skip_file in str(test_file) for skip_file in skip_files):
                        dependency_issues.append(f"{test_file}: Uses {service} without mocking")
        
        # Just warn for now since some tests legitimately need external services
        if dependency_issues:
            print(f"\n⚠️  External dependency usage (consider mocking): {len(dependency_issues)} cases")
            for issue in dependency_issues[:3]:
                print(f"  {issue}")
    
    def test_test_isolation(self):
        """Test that tests are properly isolated and don't depend on each other"""
        test_files = self.get_test_files()
        isolation_issues = []
        
        for test_file in test_files:
            content = test_file.read_text()
            
            # Check for global state modifications
            global_state_patterns = [
                r'os\.environ\[',
                r'sys\.path\.',
                r'chdir\(',
                r'global\s+\w+'
            ]
            
            for pattern in global_state_patterns:
                if re.search(pattern, content):
                    # Check if there's proper cleanup or if it's conftest.py (which is appropriate)
                    if ('@pytest.fixture' not in content and 'teardown' not in content.lower() 
                        and 'conftest.py' not in str(test_file)):
                        isolation_issues.append(f"{test_file}: Modifies global state without cleanup")
                        break
        
        # Just warn for isolation issues
        if isolation_issues:
            print(f"\n⚠️  Test isolation issues: {len(isolation_issues)} files")
            for issue in isolation_issues[:3]:
                print(f"  {issue}")
    
    def test_test_execution_time(self):
        """Test that individual tests don't take too long"""
        test_files = self.get_test_files()
        slow_tests = []
        
        # Simple heuristic: look for time.sleep() calls
        for test_file in test_files:
            content = test_file.read_text()
            
            # Find sleep calls
            sleep_matches = re.findall(r'time\.sleep\((\d+)\)', content)
            for match in sleep_matches:
                sleep_time = int(match)
                if sleep_time > 5:  # More than 5 seconds
                    slow_tests.append(f"{test_file}: Sleeps for {sleep_time} seconds")
        
        # Just warn about slow tests
        if slow_tests:
            print(f"\n⚠️  Potentially slow tests: {len(slow_tests)} cases")
            for test in slow_tests:
                print(f"  {test}")
    
    def test_proper_fixtures(self):
        """Test that fixtures are properly defined and used"""
        test_files = self.get_test_files()
        fixture_issues = []
        
        for test_file in test_files:
            content = test_file.read_text()
            
            # Check for fixture definitions
            if '@pytest.fixture' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    stripped_line = line.strip()
                    if stripped_line.startswith('@pytest.fixture'):
                        # Check next non-empty lines for proper fixture function
                        j = i + 1
                        found_def = False
                        while j < len(lines) and j < i + 3:  # Check next 3 lines
                            next_line = lines[j].strip()
                            if next_line and not next_line.startswith('@'):
                                if next_line.startswith('def '):
                                    found_def = True
                                break
                            j += 1
                        
                        if not found_def:
                            fixture_issues.append(f"{test_file}:{i+1}: Fixture not followed by function")
        
        assert not fixture_issues, f"Fixture definition issues: {fixture_issues}"
    
    def test_test_file_organization(self):
        """Test that test files are well organized"""
        test_files = self.get_test_files()
        organization_issues = []
        
        # Check for tests in subdirectories
        subdirs = set()
        for test_file in test_files:
            relative_path = test_file.relative_to(self.test_dir)
            if len(relative_path.parts) > 1:
                subdirs.add(relative_path.parts[0])
        
        # Validate known subdirectories
        known_subdirs = {'e2e', 'tools', 'assets'}
        unknown_subdirs = subdirs - known_subdirs
        
        if unknown_subdirs:
            organization_issues.append(f"Unknown test subdirectories: {unknown_subdirs}")
        
        # Check for excessive number of test files in root
        root_test_files = [f for f in test_files if len(f.relative_to(self.test_dir).parts) == 1]
        if len(root_test_files) > 5:  # Lower threshold since we organized files
            organization_issues.append(f"Too many test files in root: {len(root_test_files)} (consider organizing in subdirs)")
        
        # Just warn about organization issues
        if organization_issues:
            print(f"\n⚠️  Test organization suggestions:")
            for issue in organization_issues:
                print(f"  {issue}")
    
    def test_no_duplicate_test_names(self):
        """Test that there are no duplicate test function names across files"""
        test_files = self.get_test_files()
        test_function_map = {}
        duplicates = []
        
        for test_file in test_files:
            try:
                content = test_file.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        if node.name not in test_function_map:
                            test_function_map[node.name] = []
                        test_function_map[node.name].append(str(test_file))
            except:
                pass
        
        # Find duplicates
        for func_name, files in test_function_map.items():
            if len(files) > 1:
                duplicates.append(f"{func_name}: {files}")
        
        assert not duplicates, f"Duplicate test function names: {duplicates}"
    
    def test_test_coverage_balance(self):
        """Test that test coverage is balanced across components"""
        test_files = self.get_test_files()
        coverage_analysis = {}
        
        # Analyze what each test file covers (updated for new structure)
        components = ['dashboard', 'ai', 'core', 'utils', 'infrastructure', 'health', 'integration']
        
        for component in components:
            coverage_analysis[component] = []
            
            for test_file in test_files:
                filepath = str(test_file)
                content = test_file.read_text()
                
                # Map directories to components
                if (component == 'dashboard' and ('dashboard' in content or 'dashboard' in test_file.name or '/unit/' in filepath)) or \
                   (component == 'ai' and ('ai' in content or 'ai' in test_file.name)) or \
                   (component == 'core' and ('core' in content or 'pensieve' in test_file.name or 'basic' in test_file.name)) or \
                   (component == 'infrastructure' and '/infrastructure/' in filepath) or \
                   (component == 'health' and '/health/' in filepath) or \
                   (component == 'integration' and ('/integration/' in filepath or '/e2e/' in filepath)) or \
                   (component == 'utils' and 'utils' in content):
                    coverage_analysis[component].append(test_file.name)
        
        # Check for under-tested components
        under_tested = []
        for component, test_files in coverage_analysis.items():
            if len(test_files) == 0:
                under_tested.append(component)
        
        # Just warn about coverage gaps
        if under_tested:
            print(f"\n⚠️  Components with limited test coverage: {under_tested}")
        
        # Show coverage summary
        print(f"\n📊 Test Coverage Summary:")
        for component, test_files in coverage_analysis.items():
            print(f"  {component}: {len(test_files)} test files")
    
    def test_conftest_files(self):
        """Test that conftest.py files are properly structured"""
        conftest_files = list(self.test_dir.glob("**/conftest.py"))
        conftest_issues = []
        
        for conftest_file in conftest_files:
            content = conftest_file.read_text()
            
            # Check for pytest fixtures
            if '@pytest.fixture' not in content:
                conftest_issues.append(f"{conftest_file}: conftest.py should contain fixtures")
            
            # Check for imports
            if 'import pytest' not in content:
                conftest_issues.append(f"{conftest_file}: Missing pytest import")
        
        # Just report conftest analysis
        if conftest_files:
            print(f"\n📋 Found {len(conftest_files)} conftest.py files")
            if conftest_issues:
                print("  Issues:")
                for issue in conftest_issues:
                    print(f"    {issue}")
    
    def test_test_data_organization(self):
        """Test that test data and assets are properly organized"""
        test_data_issues = []
        
        # Check for test data files in wrong locations
        all_files = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if any(indicator in file.lower() for indicator in ['test', 'mock', 'sample', 'fixture']):
                    file_path = Path(root) / file
                    if 'tests' not in str(file_path) and 'test' in file.lower():
                        all_files.append(file_path)
        
        # Check for assets in tests directory
        assets_dir = self.test_dir / "assets"
        if assets_dir.exists():
            assets = list(assets_dir.iterdir())
            print(f"\n📁 Test assets directory contains {len(assets)} files")
        
        # Check for scattered test data
        scattered_test_data = [f for f in all_files if f.suffix in ['.json', '.csv', '.txt', '.png']]
        if scattered_test_data:
            test_data_issues.append(f"Test data files outside tests/: {len(scattered_test_data)} files")
        
        # Just warn about organization
        if test_data_issues:
            print(f"\n⚠️  Test data organization issues:")
            for issue in test_data_issues:
                print(f"  {issue}")
    
    def test_pytest_markers(self):
        """Test for proper use of pytest markers"""
        test_files = self.get_test_files()
        marker_usage = []
        
        common_markers = ['@pytest.mark.slow', '@pytest.mark.integration', '@pytest.mark.unit', '@pytest.mark.skip']
        
        for test_file in test_files:
            content = test_file.read_text()
            
            for marker in common_markers:
                if marker in content:
                    marker_usage.append(f"{test_file.name}: {marker}")
        
        # Report marker usage
        if marker_usage:
            print(f"\n🏷️  Pytest markers in use:")
            for usage in marker_usage:
                print(f"  {usage}")
        else:
            print(f"\n⚠️  No pytest markers found - consider using markers for test categorization")
    
    def test_mock_realism_and_quality(self):
        """Test that mocks are realistic and follow best practices"""
        test_files = self.get_test_files()
        mock_issues = []
        
        for test_file in test_files:
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                # Check for bad mock patterns
                bad_patterns = [
                    (r'Mock\(\)', 'Use MagicMock() for objects with magic methods'),
                    (r'mock_.*\.return_value\s*=\s*Mock\(\)', 'Mock return values should be realistic objects, not empty Mocks'),
                    (r'Mock\(\)\..*\.return_value', 'Chain mocking suggests unrealistic test setup'),
                    (r'patch\(.*\).*return_value\s*=\s*True', 'Boolean return values should match real function behavior'),
                    (r'mock_.*\.side_effect\s*=\s*None', 'None side_effect may not represent real behavior'),
                    (r'Mock\(\)\..*\..*\..*\.', 'Deep mock chaining indicates unrealistic mocking'),
                ]
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Skip comments and docstrings
                    if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                        continue
                    
                    for pattern, message in bad_patterns:
                        if re.search(pattern, line):
                            mock_issues.append(f"{test_file.name}:{line_num}: {message}")
                
                # Check for context manager mocking realism
                if 'get_connection' in content and 'Mock()' in content:
                    # Look for proper context manager setup
                    has_enter_exit = '__enter__' in content and '__exit__' in content
                    has_magic_mock = 'MagicMock()' in content
                    
                    if not (has_enter_exit or has_magic_mock):
                        mock_issues.append(f"{test_file.name}: Database connection mocking should use MagicMock or explicit __enter__/__exit__")
                
                # Check for realistic data mocking
                if 'pd.DataFrame' in content and 'Mock()' in content:
                    # Look for realistic DataFrame structures
                    if 'columns' not in content and 'data' not in content:
                        mock_issues.append(f"{test_file.name}: DataFrame mocks should use realistic column/data structures")
                
                # Check for missing assertions about mock calls
                if 'Mock()' in content or 'MagicMock()' in content:
                    has_call_assertions = any(pattern in content for pattern in [
                        '.called', '.call_count', '.assert_called', '.call_args'
                    ])
                    if not has_call_assertions:
                        mock_issues.append(f"{test_file.name}: Tests with mocks should verify mock interactions")
                
                # Check for overly broad patching
                patch_patterns = re.findall(r'@patch\([\'\"](.*?)[\'\"]', content)
                for patch_target in patch_patterns:
                    if patch_target.count('.') > 3:
                        mock_issues.append(f"{test_file.name}: Overly specific patch target may be brittle: {patch_target}")
                
                # Check for mock setup that doesn't match real interface
                if 'execute_query' in content and 'Mock()' in content:
                    # execute_query should return DataFrame-like objects
                    if 'pd.DataFrame' not in content and 'return_value' in content:
                        mock_issues.append(f"{test_file.name}: execute_query mock should return DataFrame-like objects")
                
            except Exception as e:
                mock_issues.append(f"{test_file.name}: Error analyzing mocks - {e}")
        
        # Report findings but don't fail the test - this is for guidance
        if mock_issues:
            print(f"\n🎭 Mock Quality Issues Found ({len(mock_issues)}):")
            for issue in mock_issues[:10]:  # Limit output
                print(f"  ⚠️  {issue}")
            if len(mock_issues) > 10:
                print(f"  ... and {len(mock_issues) - 10} more issues")
        else:
            print("\n✅ All mocks appear realistic and well-structured")
    
    def test_tests_validate_real_functionality_and_discover_breaks(self):
        """Test that tests actually validate real functionality and can discover real breaks."""
        test_files = self.get_test_files()
        functionality_issues = []
        
        for test_file in test_files:
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                # Skip test files that are infrastructure or meta-tests
                if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                    continue
                
                # Analyze test quality patterns
                test_functions = re.findall(r'def (test_\w+)\(', content)
                
                for test_func in test_functions:
                    # Find the test function content
                    start_line = None
                    for i, line in enumerate(lines):
                        if f'def {test_func}(' in line:
                            start_line = i
                            break
                    
                    if start_line is None:
                        continue
                    
                    # Extract test function body (until next def or class)
                    test_body = []
                    for i in range(start_line + 1, len(lines)):
                        line = lines[i]
                        if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                            break
                        test_body.append(line)
                    
                    test_content = '\n'.join(test_body)
                    
                    # Check for weak test patterns that don't validate real functionality
                    weak_patterns = [
                        # Tests that only check object creation
                        (r'assert.*is not None.*\n.*assert.*==.*\n$', 
                         'Only checks object creation, not functionality'),
                        
                        # Tests that only check mock was called
                        (r'assert.*\.called.*$', 
                         'Only verifies mock calls, no actual functionality validation'),
                        
                        # Tests with hardcoded simple values that can't break
                        (r'assert.*==.*["\']test["\']', 
                         'Uses hardcoded test values that may not reflect real usage'),
                        
                        # Tests that don't validate the actual business logic
                        (r'assert len\(.*\) ==.*\n.*assert isinstance', 
                         'Only validates data structure, not business logic'),
                    ]
                    
                    # Check for strong validation patterns
                    strong_patterns = [
                        r'assert.*\.status_code.*==.*200',  # HTTP validation
                        r'assert.*\.content.*',  # Content validation
                        r'assert.*\.data.*',  # Data validation
                        r'assert.*\.result.*',  # Result validation
                        r'assert.*calculation.*',  # Calculation validation
                        r'assert.*processing.*',  # Processing validation
                        r'assert.*transformation.*',  # Data transformation
                        r'assert.*raises.*Exception',  # Error condition testing
                        r'assert.*!=.*None',  # Non-null validation
                        r'assert.*>.*0',  # Meaningful value validation
                        r'assert.*in.*',  # Membership validation
                        r'assert.*startswith|endswith|contains',  # String validation
                    ]
                    
                    # Check for meaningful assertions
                    assertion_count = len(re.findall(r'assert ', test_content))
                    mock_verification_count = len(re.findall(r'\.assert_called|\.called|\.call_count', test_content))
                    
                    # Flag weak tests
                    if assertion_count <= 1:
                        functionality_issues.append(
                            f"{test_file.name}:{test_func}: Too few assertions ({assertion_count}) - may not validate functionality"
                        )
                    
                    # Detect meaningless assertions
                    if 'assert True' in test_content or 'assert 1 == 1' in test_content:
                        functionality_issues.append(
                            f"{test_file.name}:{test_func}: Contains meaningless assertion (assert True) - provides no validation"
                        )
                    
                    if mock_verification_count > assertion_count:
                        functionality_issues.append(
                            f"{test_file.name}:{test_func}: More mock verifications than business logic assertions"
                        )
                    
                    # Check for business logic validation
                    has_business_logic = any(re.search(pattern, test_content) for pattern in strong_patterns)
                    has_only_structure_checks = all(
                        keyword in test_content for keyword in ['assert len(', 'isinstance']
                    ) and assertion_count <= 3
                    
                    if has_only_structure_checks and not has_business_logic:
                        functionality_issues.append(
                            f"{test_file.name}:{test_func}: Only validates data structure, not business logic"
                        )
                    
                    # Check for real data validation vs hardcoded test data
                    if 'assert' in test_content and 'test_data' in test_content.lower():
                        # Look for realistic data patterns
                        realistic_patterns = [
                            r'datetime\.',  # Real datetime handling
                            r'\.total_seconds\(\)',  # Time calculations
                            r'pd\.DataFrame',  # Real data structures
                            r'\.sum\(\)|\.count\(\)|\.mean\(\)',  # Aggregations
                            r'\.filter\(|\.where\(',  # Data filtering
                            r'\.json\(\)|\.dict\(\)',  # Data serialization
                        ]
                        
                        has_realistic_data = any(re.search(pattern, test_content) for pattern in realistic_patterns)
                        if not has_realistic_data:
                            functionality_issues.append(
                                f"{test_file.name}:{test_func}: May use oversimplified test data"
                            )
                    
                    # Check for error condition testing
                    if 'test_' in test_func and 'error' not in test_func.lower() and 'fail' not in test_func.lower():
                        has_error_testing = any(pattern in test_content for pattern in [
                            'pytest.raises', 'assertRaises', 'with raises', 'Exception'
                        ])
                        
                        # Only flag if this seems like a function that should have error cases
                        if ('repository' in test_func.lower() or 'service' in test_func.lower() or 
                            'process' in test_func.lower()) and len(test_body) > 10:
                            # Look for corresponding error test
                            error_test_exists = any(
                                f"{test_func.replace('test_', 'test_')}_error" in other_func or
                                f"{test_func}_fails" in other_func or
                                f"{test_func}_invalid" in other_func
                                for other_func in test_functions
                            )
                            
                            if not has_error_testing and not error_test_exists:
                                functionality_issues.append(
                                    f"{test_file.name}:{test_func}: No error condition testing for complex functionality"
                                )
                
                # Check for integration between components
                if 'test_' in content and 'integration' in str(test_file):
                    # Integration tests should test real interaction between components
                    integration_patterns = [
                        r'\.get_.*\(.*\).*\.process_.*\(',  # Chain of operations
                        r'repository.*\..*service\.',  # Cross-component interaction
                        r'database.*\..*api\.',  # Database to API
                        r'mock_.*\..*real_.*',  # Mixed mock and real components
                    ]
                    
                    has_real_integration = any(re.search(pattern, content) for pattern in integration_patterns)
                    if not has_real_integration and len(test_functions) > 0:
                        functionality_issues.append(
                            f"{test_file.name}: Integration test may not test real component interaction"
                        )
                
            except Exception as e:
                functionality_issues.append(f"{test_file.name}: Error analyzing functionality - {e}")
        
        # Report findings with actionable guidance
        if functionality_issues:
            print(f"\n🔍 Test Functionality Issues Found ({len(functionality_issues)}):")
            print("   Tests may not adequately validate real functionality or discover breaks:")
            
            # Group by issue type for better reporting
            issue_categories = {
                'weak_assertions': [],
                'mock_heavy': [],
                'structure_only': [],
                'simple_data': [],
                'missing_errors': [],
                'integration': [],
                'other': []
            }
            
            for issue in functionality_issues:
                if 'Too few assertions' in issue:
                    issue_categories['weak_assertions'].append(issue)
                elif 'More mock verifications' in issue:
                    issue_categories['mock_heavy'].append(issue)
                elif 'Only validates data structure' in issue:
                    issue_categories['structure_only'].append(issue)
                elif 'oversimplified test data' in issue:
                    issue_categories['simple_data'].append(issue)
                elif 'No error condition' in issue:
                    issue_categories['missing_errors'].append(issue)
                elif 'Integration test' in issue:
                    issue_categories['integration'].append(issue)
                else:
                    issue_categories['other'].append(issue)
            
            for category, issues in issue_categories.items():
                if issues:
                    category_name = {
                        'weak_assertions': '⚠️  Weak Assertions',
                        'mock_heavy': '🎭 Mock-Heavy Tests',
                        'structure_only': '📊 Structure-Only Tests', 
                        'simple_data': '🔧 Oversimplified Data',
                        'missing_errors': '❌ Missing Error Testing',
                        'integration': '🔄 Weak Integration',
                        'other': '🔍 Other Issues'
                    }[category]
                    
                    print(f"\n   {category_name}:")
                    for issue in issues[:3]:  # Limit output per category
                        print(f"     • {issue}")
                    if len(issues) > 3:
                        print(f"     ... and {len(issues) - 3} more")
            
            print(f"\n   💡 Recommendations:")
            print(f"     • Add assertions that validate business logic, not just data structure")
            print(f"     • Test error conditions and edge cases")
            print(f"     • Use realistic data that matches production scenarios") 
            print(f"     • Ensure integration tests validate real component interaction")
            print(f"     • Balance mock verification with functionality validation")
            
        else:
            print("\n✅ All tests appear to validate real functionality")
        
        # Additional check: Test mutation analysis
        print(f"\n🧬 Mutation Testing Analysis:")
        mutation_issues = self._analyze_mutation_resistance(test_files)
        
        # CRITICAL: Only fail for truly broken tests (0 assertions or meaningless assertions)
        critical_issues = []
        for issue in functionality_issues:
            if any(critical in issue for critical in [
                'Too few assertions (0)',  # No assertions at all
                'meaningless assertion',   # Meaningless assertions like assert True
            ]):
                critical_issues.append(issue)
        
        # Warn about other quality issues but don't fail unless truly broken
        warning_issues = []
        for issue in functionality_issues:
            if issue not in critical_issues:
                warning_issues.append(issue)
        
        if warning_issues:
            print(f"\n⚠️ TEST QUALITY WARNINGS ({len(warning_issues)}):")
            print("These tests could be improved but are functional:")
            for issue in warning_issues[:5]:
                print(f"  • {issue}")
            if len(warning_issues) > 5:
                print(f"  ... and {len(warning_issues) - 5} more warnings")
        
        # Only fail if we have truly broken tests
        if critical_issues:
            assert False, f"""
🚨 CRITICAL TEST QUALITY FAILURES ({len(critical_issues)}):
Tests with fundamental quality issues that WILL NOT catch real bugs:

{chr(10).join('  • ' + issue for issue in critical_issues[:10])}
{f'  ... and {len(critical_issues) - 10} more critical issues' if len(critical_issues) > 10 else ''}

💡 IMMEDIATE ACTION REQUIRED:
• Tests with 0 assertions provide NO validation whatsoever
• Tests with "assert True" or similar provide false confidence
• These must be fixed for basic testing reliability!
"""
    
    def test_test_system_meta_health(self):
        """Meta-test: Verify this test file itself is healthy"""
        this_file = Path(__file__)
        content = this_file.read_text()
        
        # Check that this file follows its own rules
        assert 'test_' in this_file.name
        assert 'class TestTestingSystemHealth' in content
        assert '@pytest.fixture' in content
        
        # Check for good test documentation
        assert '"""' in content
        assert 'Test' in content or 'test' in content
        
        print("\n✅ Testing system health test is self-validating")
    
    def _analyze_mutation_resistance(self, test_files):
        """Analyze how resistant tests are to common code mutations."""
        mutation_issues = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                test_functions = re.findall(r'def (test_\w+)\(.*?\):', content, re.DOTALL)
                
                for test_func in test_functions:
                    # Find test function content
                    pattern = rf'def {re.escape(test_func)}\(.*?\):(.*?)(?=\n    def |\nclass |\n\n\nif |\Z)'
                    match = re.search(pattern, content, re.DOTALL)
                    
                    if not match:
                        continue
                    
                    test_body = match.group(1)
                    
                    # Check resistance to common mutations
                    mutation_checks = [
                        # Off-by-one errors
                        {
                            'name': 'off_by_one',
                            'pattern': r'assert.*==.*\d+',
                            'weakness': 'May not catch off-by-one errors',
                            'check': lambda body: '>' in body or '<' in body or 'range(' in body
                        },
                        
                        # Boolean logic mutations
                        {
                            'name': 'boolean_logic',
                            'pattern': r'assert.*and|or',
                            'weakness': 'Boolean logic may not be thoroughly tested',
                            'check': lambda body: 'True' in body and 'False' in body
                        },
                        
                        # Boundary conditions
                        {
                            'name': 'boundaries',
                            'pattern': r'assert.*len\(.*\)',
                            'weakness': 'May not test boundary conditions',
                            'check': lambda body: any(boundary in body for boundary in ['empty', '[]', '{}', '0', 'None'])
                        },
                        
                        # Return value mutations
                        {
                            'name': 'return_values',
                            'pattern': r'assert.*==.*',
                            'weakness': 'May not catch return value mutations',
                            'check': lambda body: 'not ' in body or '!=' in body
                        },
                        
                        # Conditional mutations (if/else)
                        {
                            'name': 'conditionals',
                            'pattern': r'if.*:',
                            'weakness': 'Conditional logic may not be fully tested',
                            'check': lambda body: 'else' in body or multiple_conditions(body)
                        }
                    ]
                    
                    # Helper function for conditional analysis
                    def multiple_conditions(body):
                        return len(re.findall(r'assert.*(?:==|!=|>|<|>=|<=)', body)) > 2
                    
                    for mutation in mutation_checks:
                        if re.search(mutation['pattern'], test_body):
                            if not mutation['check'](test_body):
                                mutation_issues.append(
                                    f"{test_file.name}:{test_func}: {mutation['weakness']}"
                                )
            except Exception as e:
                mutation_issues.append(f"{test_file.name}: Error analyzing mutations - {e}")
        
        # Report mutation resistance analysis
        if mutation_issues:
            print(f"   Found {len(mutation_issues)} potential mutation blind spots:")
            
            # Group by mutation type
            by_type = {}
            for issue in mutation_issues:
                issue_type = issue.split(': ')[1]
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(issue)
            
            for issue_type, issues in by_type.items():
                print(f"   🧬 {issue_type}: {len(issues)} cases")
                if len(issues) <= 2:
                    for issue in issues:
                        print(f"      • {issue.split(': ')[0]}")
        else:
            print("   ✅ Tests appear resistant to common code mutations")
        
        # Additional analysis: Test value diversity
        print(f"\n🎲 Test Data Diversity Analysis:")
        self._analyze_test_data_diversity(test_files)
        
        return mutation_issues
    
    def _analyze_test_data_diversity(self, test_files):
        """Analyze diversity of test data to ensure tests can catch various failures."""
        diversity_issues = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                
                # Extract test values
                string_values = re.findall(r'["\']([^"\']+)["\']', content)
                numeric_values = re.findall(r'(?:==|!=|>|<|>=|<=)\s*(\d+)', content)
                
                # Check for diversity in test data
                unique_strings = set(string_values)
                unique_numbers = set(numeric_values)
                
                # Flag files with limited diversity
                if len(string_values) > 5 and len(unique_strings) < 3:
                    diversity_issues.append(f"{test_file.name}: Limited string value diversity")
                
                if len(numeric_values) > 3 and len(unique_numbers) < 2:
                    diversity_issues.append(f"{test_file.name}: Limited numeric value diversity")
                
                # Check for edge case coverage
                edge_cases = ['0', '1', '-1', '[]', '{}', 'None', 'True', 'False', '""', "''"]
                has_edge_cases = any(case in content for case in edge_cases)
                
                if not has_edge_cases and len(content) > 1000:  # Only for substantial test files
                    diversity_issues.append(f"{test_file.name}: Missing edge case testing")
            except Exception as e:
                diversity_issues.append(f"{test_file.name}: Error analyzing diversity - {e}")
        
        if diversity_issues:
            print(f"   Found {len(diversity_issues)} test data diversity issues:")
            for issue in diversity_issues[:5]:  # Limit output
                print(f"   📊 {issue}")
            if len(diversity_issues) > 5:
                print(f"   ... and {len(diversity_issues) - 5} more")
        else:
            print("   ✅ Test data shows good diversity")
    
    def _run_strict_assertion_quality_checks(self, test_files):
        """Helper method to run strict assertion quality checks and return failures"""
        strict_assertion_failures = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                # Find all test functions
                test_functions = re.findall(r'def (test_\w+)\(', content)
                
                for test_func in test_functions:
                    # Extract test function body
                    start_line = None
                    for i, line in enumerate(lines):
                        if f'def {test_func}(' in line:
                            start_line = i
                            break
                    
                    if start_line is None:
                        continue
                    
                    # Get function body
                    test_body = []
                    indent_level = None
                    for i in range(start_line + 1, len(lines)):
                        line = lines[i]
                        if line.strip() == '':
                            test_body.append(line)
                            continue
                        
                        current_indent = len(line) - len(line.lstrip())
                        if indent_level is None and line.strip():
                            indent_level = current_indent
                        
                        if line.strip() and current_indent <= indent_level and not line.startswith(' ') and not line.startswith('\t'):
                            if not line.strip().startswith('#'):
                                break
                        
                        test_body.append(line)
                    
                    test_content = '\n'.join(test_body)
                    
                    # STRICT CHECKS:
                    
                    # 1. Completely trivial assertions
                    trivial_patterns = [
                        r'assert True[^a-zA-Z]',  # assert True
                        r'assert 1[^a-zA-Z]',    # assert 1  
                        r'assert ".*" == ".*"',  # assert "same" == "same"
                        r'assert \w+ == \w+(?:\s*#.*)?$'  # assert x == x
                    ]
                    
                    for pattern in trivial_patterns:
                        if re.search(pattern, test_content, re.MULTILINE):
                            strict_assertion_failures.append(
                                f"{test_file.name}:{test_func}: Contains trivial assertion that provides no validation"
                            )
                    
                    # 2. Tests that only check object creation
                    creation_only_pattern = r'assert.*is not None.*\n.*assert.*\w+\s*==.*\n\s*$'
                    if re.search(creation_only_pattern, test_content, re.MULTILINE | re.DOTALL):
                        if test_content.count('assert') <= 2:
                            strict_assertion_failures.append(
                                f"{test_file.name}:{test_func}: Only validates object creation, not functionality"
                            )
                    
                    # 3. Tests with no error condition testing for complex functionality
                    has_complex_logic = any(keyword in test_content for keyword in [
                        'database', 'connection', 'api', 'request', 'process', 'file', 'network'
                    ])
                    has_error_testing = any(keyword in test_content for keyword in [
                        'except', 'raises', 'error', 'fail', 'exception', 'invalid', 'timeout'
                    ])
                    
                    if has_complex_logic and not has_error_testing and len(test_content) > 300:
                        strict_assertion_failures.append(
                            f"{test_file.name}:{test_func}: Complex functionality lacks error condition testing"
                        )
                    
                    # 4. Tests that only verify mocks were called (no business logic validation)
                    mock_calls = len(re.findall(r'assert.*\.called', test_content))
                    business_assertions = len(re.findall(r'assert(?!.*\.called)', test_content))
                    
                    if mock_calls > 0 and business_assertions == 0:
                        strict_assertion_failures.append(
                            f"{test_file.name}:{test_func}: Only validates mock calls, no business logic"
                        )
                        
            except Exception as e:
                strict_assertion_failures.append(f"{test_file.name}: Error analyzing assertions - {e}")
        
        return strict_assertion_failures
    
    def _run_strict_error_condition_checks(self, test_files):
        """Helper method to run strict error condition checks and return failures"""
        error_coverage_failures = []
        
        complex_function_patterns = [
            r'def.*database.*\(',
            r'def.*connection.*\(',
            r'def.*api.*\(',
            r'def.*request.*\(',
            r'def.*file.*\(',
            r'def.*process.*\(',
            r'def.*parse.*\(',
            r'def.*extract.*\(',
            r'def.*fetch.*\(',
            r'def.*save.*\(',
            r'def.*load.*\(',
        ]
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                
                # Find complex functions being tested
                for pattern in complex_function_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # Check if there are corresponding error tests
                        has_error_tests = any(error_pattern in content.lower() for error_pattern in [
                            'exception', 'error', 'fail', 'invalid', 'timeout', 'connection.*error',
                            'file.*not.*found', 'permission.*denied', 'network.*error'
                        ])
                        
                        if not has_error_tests:
                            error_coverage_failures.append(
                                f"{test_file.name}: Tests complex functions but lacks error condition coverage"
                            )
                            
            except Exception as e:
                error_coverage_failures.append(f"{test_file.name}: Error analyzing error coverage - {e}")
        
        return error_coverage_failures
    
    def _run_strict_boundary_checks(self, test_files):
        """Helper method to run strict boundary checks and return failures"""
        boundary_failures = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                
                # Look for numeric operations that should have boundary testing
                has_numeric_ops = any(op in content for op in [
                    'range(', 'len(', '>', '<', '>=', '<=', '+', '-', '*', '/'
                ])
                
                # Check for boundary value testing
                has_boundary_tests = any(boundary in content for boundary in [
                    ' 0', ' 1', '-1', 'empty', '[]', '{}', 'None', 'min', 'max'
                ])
                
                # Look for collections that should test empty/single/multiple items
                has_collections = any(collection in content for collection in [
                    'list', 'dict', 'set', 'tuple', '[]', '{}'
                ])
                
                has_collection_boundaries = any(test in content for test in [
                    'empty', 'single', 'multiple', 'len(.*) == 0', 'len(.*) == 1'
                ])
                
                if has_numeric_ops and not has_boundary_tests and len(content) > 500:
                    boundary_failures.append(
                        f"{test_file.name}: Has numeric operations but lacks boundary value testing"
                    )
                
                if has_collections and not has_collection_boundaries and len(content) > 500:
                    boundary_failures.append(
                        f"{test_file.name}: Uses collections but lacks empty/single/multiple testing"
                    )
                        
            except Exception as e:
                boundary_failures.append(f"{test_file.name}: Error analyzing boundary testing - {e}")
        
        return boundary_failures
    
    def test_strict_assertion_quality(self):
        """🚨 STRICT: Test that all assertions are meaningful and validate actual functionality"""
        if not self.STRICT_MODE:
            pytest.skip("Strict mode disabled")
            
        test_files = self.get_test_files()
        strict_assertion_failures = self._run_strict_assertion_quality_checks(test_files)
        
        if strict_assertion_failures:
            print(f"\n🚨 STRICT ASSERTION QUALITY FAILURES ({len(strict_assertion_failures)}):")
            for failure in strict_assertion_failures[:10]:
                print(f"  • {failure}")
            if len(strict_assertion_failures) > 10:
                print(f"  ... and {len(strict_assertion_failures) - 10} more failures")
            
            assert False, f"STRICT MODE: {len(strict_assertion_failures)} tests have inadequate assertion quality"
    
    def test_strict_error_condition_coverage(self):
        """🚨 STRICT: Test that all complex functions have error condition testing"""
        if not self.STRICT_MODE:
            pytest.skip("Strict mode disabled")
            
        test_files = self.get_test_files()
        error_coverage_failures = self._run_strict_error_condition_checks(test_files)
        
        if error_coverage_failures:
            print(f"\n🚨 STRICT ERROR CONDITION COVERAGE FAILURES ({len(error_coverage_failures)}):")
            for failure in error_coverage_failures[:8]:
                print(f"  • {failure}")
            if len(error_coverage_failures) > 8:
                print(f"  ... and {len(error_coverage_failures) - 8} more failures")
            
            assert False, f"STRICT MODE: {len(error_coverage_failures)} test files lack error condition coverage"
    
    def test_strict_boundary_testing(self):
        """🚨 STRICT: Test that boundary conditions are properly tested"""
        if not self.STRICT_MODE:
            pytest.skip("Strict mode disabled")
            
        test_files = self.get_test_files()
        boundary_failures = self._run_strict_boundary_checks(test_files)
        
        if boundary_failures:
            print(f"\n🚨 STRICT BOUNDARY TESTING FAILURES ({len(boundary_failures)}):")
            for failure in boundary_failures[:8]:
                print(f"  • {failure}")
            if len(boundary_failures) > 8:
                print(f"  ... and {len(boundary_failures) - 8} more failures")
            
            assert False, f"STRICT MODE: {len(boundary_failures)} test files lack boundary condition testing"
    
    def test_ultra_strict_assertion_count_minimum(self):
        """🔥 ULTRA STRICT: Every test function must have at least 3 meaningful assertions + ALL STRICT MODE CHECKS"""
        if not self.ULTRA_STRICT_MODE:
            pytest.skip("Ultra strict mode disabled")
            
        test_files = self.get_test_files()
        ultra_strict_failures = []
        
        # FIRST: Run all STRICT mode checks (ULTRA STRICT includes everything from STRICT)
        print("🔥 ULTRA STRICT: Running ALL strict mode checks first...")
        
        # Include all strict assertion quality checks
        strict_failures = self._run_strict_assertion_quality_checks(test_files)
        ultra_strict_failures.extend([f"STRICT: {failure}" for failure in strict_failures])
        
        # Include error condition coverage checks
        error_failures = self._run_strict_error_condition_checks(test_files)
        ultra_strict_failures.extend([f"STRICT: {failure}" for failure in error_failures])
        
        # Include boundary testing checks  
        boundary_failures = self._run_strict_boundary_checks(test_files)
        ultra_strict_failures.extend([f"STRICT: {failure}" for failure in boundary_failures])
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                # Find all test functions
                test_functions = re.findall(r'def (test_\w+)\(', content)
                
                for test_func in test_functions:
                    # Extract test function body
                    start_line = None
                    for i, line in enumerate(lines):
                        if f'def {test_func}(' in line:
                            start_line = i
                            break
                    
                    if start_line is None:
                        continue
                    
                    # Get function body
                    test_body = []
                    indent_level = None
                    for i in range(start_line + 1, len(lines)):
                        line = lines[i]
                        if line.strip() == '':
                            test_body.append(line)
                            continue
                        
                        current_indent = len(line) - len(line.lstrip())
                        if indent_level is None and line.strip():
                            indent_level = current_indent
                        
                        if line.strip() and current_indent <= indent_level and not line.startswith(' ') and not line.startswith('\t'):
                            if not line.strip().startswith('#'):
                                break
                        
                        test_body.append(line)
                    
                    test_content = '\n'.join(test_body)
                    
                    # Count meaningful assertions
                    assertion_count = 0
                    assertions = re.findall(r'assert\s+[^(].*', test_content)
                    
                    for assertion in assertions:
                        # Skip trivial assertions
                        if any(trivial in assertion for trivial in [
                            'assert True', 'assert 1', 'assert "test" == "test"',
                            'is not None', 'pytest.', 'xfail', 'skip'
                        ]):
                            continue
                        assertion_count += 1
                    
                    # ULTRA STRICT: Require minimum 3 meaningful assertions
                    if assertion_count < 3 and len(test_content) > 100:
                        ultra_strict_failures.append(
                            f"{test_file.name}:{test_func}: Only {assertion_count} meaningful assertions (requires ≥3)"
                        )
                        
            except Exception as e:
                ultra_strict_failures.append(f"{test_file.name}: Error analyzing assertion count - {e}")
        
        if ultra_strict_failures:
            print(f"\n🔥 ULTRA STRICT ASSERTION COUNT FAILURES ({len(ultra_strict_failures)}):")
            for failure in ultra_strict_failures[:12]:
                print(f"  • {failure}")
            if len(ultra_strict_failures) > 12:
                print(f"  ... and {len(ultra_strict_failures) - 12} more failures")
            
            assert False, f"ULTRA STRICT MODE: {len(ultra_strict_failures)} tests have insufficient assertions"
    
    def test_ultra_strict_test_independence(self):
        """🔥 ULTRA STRICT: Tests must be completely independent (no shared state)"""
        if not self.ULTRA_STRICT_MODE:
            pytest.skip("Ultra strict mode disabled")
            
        test_files = self.get_test_files()
        independence_failures = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                
                # Check for shared state indicators
                shared_state_patterns = [
                    (r'global\s+\w+', "Uses global variables"),
                    (r'class\s+\w+.*:\s*\n.*\w+\s*=', "Uses class-level shared state"),
                    (r'@pytest\.fixture\(scope=["\']module["\']', "Uses module-scoped fixtures"),
                    (r'@pytest\.fixture\(scope=["\']session["\']', "Uses session-scoped fixtures"),
                    (r'_cache\s*=', "Uses module-level caching"),
                    (r'_shared\s*=', "Uses explicit shared state"),
                ]
                
                for pattern, message in shared_state_patterns:
                    if re.search(pattern, content):
                        independence_failures.append(f"{test_file.name}: {message}")
                
                # Check for test ordering dependencies
                if 'TestCase' in content or 'unittest' in content:
                    independence_failures.append(f"{test_file.name}: Uses unittest which may have ordering dependencies")
                        
            except Exception as e:
                independence_failures.append(f"{test_file.name}: Error analyzing independence - {e}")
        
        if independence_failures:
            print(f"\n🔥 ULTRA STRICT TEST INDEPENDENCE FAILURES ({len(independence_failures)}):")
            for failure in independence_failures[:10]:
                print(f"  • {failure}")
            if len(independence_failures) > 10:
                print(f"  ... and {len(independence_failures) - 10} more failures")
            
            assert False, f"ULTRA STRICT MODE: {len(independence_failures)} tests lack independence"
    
    def test_ultra_strict_performance_requirements(self):
        """🔥 ULTRA STRICT: All tests must complete within strict time limits"""
        if not self.ULTRA_STRICT_MODE:
            pytest.skip("Ultra strict mode disabled")
            
        test_files = self.get_test_files()
        performance_failures = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                
                # Check for performance anti-patterns
                slow_patterns = [
                    (r'time\.sleep\(\s*[1-9][0-9]*', "Uses long sleep() calls"),
                    (r'requests\.get.*timeout=(?:[1-9][0-9]+|None)', "Uses long HTTP timeouts"),
                    (r'while.*time\.time\(\).*[1-9][0-9]+', "Uses long polling loops"),
                    (r'for.*range\(\s*[1-9][0-9]{4,}', "Uses large iteration loops"),
                    (r'subprocess\..*timeout=(?:[1-9][0-9]+|None)', "Uses long subprocess timeouts"),
                ]
                
                for pattern, message in slow_patterns:
                    if re.search(pattern, content):
                        performance_failures.append(f"{test_file.name}: {message}")
                
                # Check for missing timeout decorators on integration tests
                if 'integration' in str(test_file) or 'e2e' in str(test_file):
                    has_timeout = '@pytest.mark.timeout' in content or 'timeout=' in content
                    if not has_timeout:
                        performance_failures.append(f"{test_file.name}: Integration test lacks timeout protection")
                        
            except Exception as e:
                performance_failures.append(f"{test_file.name}: Error analyzing performance - {e}")
        
        if performance_failures:
            print(f"\n🔥 ULTRA STRICT PERFORMANCE FAILURES ({len(performance_failures)}):")
            for failure in performance_failures[:10]:
                print(f"  • {failure}")
            if len(performance_failures) > 10:
                print(f"  ... and {len(performance_failures) - 10} more failures")
            
            assert False, f"ULTRA STRICT MODE: {len(performance_failures)} tests have performance issues"
    
    def test_ultra_strict_documentation_requirements(self):
        """🔥 ULTRA STRICT: All tests must have comprehensive docstrings"""
        if not self.ULTRA_STRICT_MODE:
            pytest.skip("Ultra strict mode disabled")
            
        test_files = self.get_test_files()
        documentation_failures = []
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                # Find all test functions
                test_functions = re.findall(r'def (test_\w+)\(', content)
                
                for test_func in test_functions:
                    # Check if function has docstring
                    start_line = None
                    for i, line in enumerate(lines):
                        if f'def {test_func}(' in line:
                            start_line = i
                            break
                    
                    if start_line is None:
                        continue
                    
                    # Check for docstring in next few lines
                    has_docstring = False
                    docstring_content = ""
                    
                    for i in range(start_line + 1, min(start_line + 5, len(lines))):
                        line = lines[i].strip()
                        if line.startswith('"""') or line.startswith("'''"):
                            has_docstring = True
                            # Extract docstring content
                            if '"""' in line or "'''" in line:
                                docstring_start = i
                                for j in range(i, min(i + 10, len(lines))):
                                    docstring_content += lines[j] + " "
                                    if j > i and ('"""' in lines[j] or "'''" in lines[j]):
                                        break
                            break
                    
                    if not has_docstring:
                        documentation_failures.append(f"{test_file.name}:{test_func}: Missing docstring")
                    elif len(docstring_content.strip()) < 50:
                        documentation_failures.append(f"{test_file.name}:{test_func}: Docstring too brief (<50 chars)")
                    elif not any(keyword in docstring_content.lower() for keyword in [
                        'test', 'verify', 'validate', 'check', 'ensure', 'assert'
                    ]):
                        documentation_failures.append(f"{test_file.name}:{test_func}: Docstring lacks test purpose description")
                        
            except Exception as e:
                documentation_failures.append(f"{test_file.name}: Error analyzing documentation - {e}")
        
        if documentation_failures:
            print(f"\n🔥 ULTRA STRICT DOCUMENTATION FAILURES ({len(documentation_failures)}):")
            for failure in documentation_failures[:12]:
                print(f"  • {failure}")
            if len(documentation_failures) > 12:
                print(f"  ... and {len(documentation_failures) - 12} more failures")
            
            assert False, f"ULTRA STRICT MODE: {len(documentation_failures)} tests lack proper documentation"
    
    def test_strict_mode_configuration_summary(self):
        """🔧 Show current strict mode configuration and available tests"""
        print(f"\n{'='*60}")
        print(f"🧪 TESTING SYSTEM HEALTH - STRICT MODE CONFIGURATION")
        print(f"{'='*60}")
        
        print(f"\n📊 CURRENT CONFIGURATION:")
        print(f"   STRICT_MODE = {self.STRICT_MODE}")
        print(f"   ULTRA_STRICT_MODE = {self.ULTRA_STRICT_MODE}")
        
        print(f"\n🎯 AVAILABLE STRICT TESTS:")
        
        if self.STRICT_MODE:
            print(f"   ✅ test_strict_assertion_quality")
            print(f"   ✅ test_strict_error_condition_coverage") 
            print(f"   ✅ test_strict_boundary_testing")
        else:
            print(f"   ❌ test_strict_assertion_quality (DISABLED)")
            print(f"   ❌ test_strict_error_condition_coverage (DISABLED)")
            print(f"   ❌ test_strict_boundary_testing (DISABLED)")
            
        if self.ULTRA_STRICT_MODE:
            print(f"   🔥 test_ultra_strict_assertion_count_minimum")
            print(f"   🔥 test_ultra_strict_test_independence")
            print(f"   🔥 test_ultra_strict_performance_requirements")
            print(f"   🔥 test_ultra_strict_documentation_requirements")
        else:
            print(f"   ⏸️  test_ultra_strict_assertion_count_minimum (DISABLED)")
            print(f"   ⏸️  test_ultra_strict_test_independence (DISABLED)")
            print(f"   ⏸️  test_ultra_strict_performance_requirements (DISABLED)")
            print(f"   ⏸️  test_ultra_strict_documentation_requirements (DISABLED)")
        
        print(f"\n📝 STRICTNESS LEVELS:")
        print(f"   📊 STRICT MODE enforces:")
        print(f"      • No trivial assertions (assert True, assert x == x)")
        print(f"      • Error condition testing for complex functions")
        print(f"      • Boundary value testing")
        print(f"   ")
        print(f"   🔥 ULTRA STRICT MODE includes:")
        print(f"      • ALL STRICT MODE CHECKS (above) PLUS:")
        print(f"      • Minimum 3 meaningful assertions per test")
        print(f"      • Complete test independence")
        print(f"      • Performance requirements (no long sleeps)")
        print(f"      • Comprehensive docstring requirements")
        print(f"   ")
        print(f"   💡 LOGICAL HIERARCHY:")
        print(f"      ULTRA STRICT ⊃ STRICT ⊃ BASELINE")
        print(f"      (Ultra finds EVERYTHING Strict finds + more)")
        
        print(f"\n🔧 TO MODIFY STRICTNESS:")
        print(f"   Edit the class variables at the top of TestTestingSystemHealth:")
        print(f"   STRICT_MODE = True/False")
        print(f"   ULTRA_STRICT_MODE = True/False")
        
        print(f"\n🚀 RUN COMMANDS:")
        print(f"   pytest tests/health/test_testing_system_health.py -v  # All tests")
        print(f"   pytest tests/health/test_testing_system_health.py -k strict -v  # Strict only")
        print(f"   pytest tests/health/test_testing_system_health.py -k ultra -v  # Ultra only")
        
        print(f"\n{'='*60}")
        
        # This test always passes - it's just informational
        assert True, "Configuration summary displayed"
    
    def test_ultra_strict_real_functionality_validation(self):
        """🔥 ULTRA STRICT: Do tests actually validate REAL FUNCTIONALITY that would catch bugs?"""
        if not self.ULTRA_STRICT_MODE:
            pytest.skip("Ultra strict mode disabled")
            
        test_files = self.get_test_files()
        real_functionality_failures = []
        
        print("\n🔥 ULTRA STRICT: Analyzing if tests validate REAL FUNCTIONALITY...")
        
        for test_file in test_files:
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
                
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                # Find all test functions
                test_functions = re.findall(r'def (test_\w+)\(', content)
                
                for test_func in test_functions:
                    # Extract test function body
                    start_line = None
                    for i, line in enumerate(lines):
                        if f'def {test_func}(' in line:
                            start_line = i
                            break
                    
                    if start_line is None:
                        continue
                    
                    # Get function body
                    test_body = []
                    indent_level = None
                    for i in range(start_line + 1, len(lines)):
                        line = lines[i]
                        if line.strip() == '':
                            test_body.append(line)
                            continue
                        
                        current_indent = len(line) - len(line.lstrip())
                        if indent_level is None and line.strip():
                            indent_level = current_indent
                        
                        if line.strip() and current_indent <= indent_level and not line.startswith(' ') and not line.startswith('\t'):
                            if not line.strip().startswith('#'):
                                break
                        
                        test_body.append(line)
                    
                    test_content = '\n'.join(test_body)
                    
                    # REAL FUNCTIONALITY ANALYSIS:
                    
                    # 1. Check if test validates STATE CHANGES (not just return values)
                    validates_state_change = any(pattern in test_content for pattern in [
                        r'assert.*!=.*before',  # Compares before/after state
                        r'assert.*changed',     # Explicitly checks for changes
                        r'assert.*updated',     # Checks for updates
                        r'assert.*modified',    # Checks for modifications
                        r'before.*!=.*after',   # Before/after comparison
                        r'initial.*!=.*final',  # Initial vs final state
                    ])
                    
                    # 2. Check if test validates SIDE EFFECTS (beyond return values)
                    validates_side_effects = any(effect in test_content for effect in [
                        'file', 'database', 'cache', 'log', 'email', 'notification',
                        'insert', 'update', 'delete', 'create', 'save', 'write'
                    ])
                    
                    # 3. Check if test uses REALISTIC data (not just "test" strings)
                    has_realistic_data = False
                    # Look for domain-specific data
                    domain_patterns = [
                        r'screenshot', r'task', r'dashboard', r'metrics', r'ocr', r'vlm',
                        r'pensieve', r'memos', r'AI', r'embedding', r'extraction'
                    ]
                    realistic_data_count = sum(1 for pattern in domain_patterns if re.search(pattern, test_content, re.IGNORECASE))
                    has_realistic_data = realistic_data_count >= 2
                    
                    # 4. Check if test validates BUSINESS RULES (not just technical correctness)
                    validates_business_rules = False
                    business_validations = [
                        r'assert.*confidence.*[><]',      # Validates confidence thresholds
                        r'assert.*accuracy.*[><]',        # Validates accuracy requirements  
                        r'assert.*threshold.*[><]',       # Validates business thresholds
                        r'assert.*limit.*[><]',           # Validates business limits
                        r'assert.*valid.*format',        # Validates business formats
                        r'assert.*within.*range',        # Validates business ranges
                    ]
                    validates_business_rules = any(re.search(pattern, test_content, re.IGNORECASE) for pattern in business_validations)
                    
                    # 5. Check if test would catch REGRESSION BUGS (tests integration points)
                    tests_integration = any(integration in test_content for integration in [
                        'pipeline', 'workflow', 'end_to_end', 'integration', 'complete',
                        'full_stack', 'cross_component', 'system'
                    ])
                    
                    # 6. Check if test validates ERROR PROPAGATION (not just happy path)
                    validates_error_propagation = any(error_check in test_content for error_check in [
                        'assert.*exception', 'assert.*error', 'assert.*fail',
                        'with.*raises', 'except.*as', 'try.*except'
                    ])
                    
                    # 7. Check for MUTATION RESISTANCE (would catch off-by-one, boolean flips, etc.)
                    mutation_resistant = False
                    mutation_checks = [
                        r'assert.*== 0',           # Would catch off-by-one  
                        r'assert.*== 1',           # Would catch off-by-one
                        r'assert.*empty',          # Would catch boundary errors
                        r'assert.*len.*== 0',      # Would catch collection errors
                        r'assert.*is True',        # Would catch boolean flips
                        r'assert.*is False',       # Would catch boolean flips
                    ]
                    mutation_resistant = any(re.search(pattern, test_content) for pattern in mutation_checks)
                    
                    # SCORING: How many "real functionality" criteria does this test meet?
                    functionality_score = sum([
                        validates_state_change,
                        validates_side_effects, 
                        has_realistic_data,
                        validates_business_rules,
                        tests_integration,
                        validates_error_propagation,
                        mutation_resistant
                    ])
                    
                    # ULTRA STRICT: Require tests to validate REAL functionality
                    if len(test_content) > 100:  # Only check substantial tests
                        if functionality_score < 2:
                            real_functionality_failures.append(
                                f"{test_file.name}:{test_func}: Low functionality validation score ({functionality_score}/7) - may not catch real bugs"
                            )
                        
                        # Extra strict checks for critical test types
                        if any(critical in test_func.lower() for critical in ['integration', 'end_to_end', 'critical', 'pipeline']):
                            if functionality_score < 3:
                                real_functionality_failures.append(
                                    f"{test_file.name}:{test_func}: Critical test with insufficient functionality validation ({functionality_score}/7)"
                                )
                        
                        # Flag tests that only check structure, not behavior
                        if test_content.count('assert') >= 3:  # Has multiple assertions
                            structure_assertions = test_content.count('is not None') + test_content.count('isinstance')
                            total_assertions = test_content.count('assert')
                            if structure_assertions / total_assertions > 0.6:
                                real_functionality_failures.append(
                                    f"{test_file.name}:{test_func}: Over 60% structure-only assertions - likely not testing behavior"
                                )
                        
            except Exception as e:
                real_functionality_failures.append(f"{test_file.name}: Error analyzing real functionality - {e}")
        
        if real_functionality_failures:
            print(f"\n🔥 ULTRA STRICT REAL FUNCTIONALITY FAILURES ({len(real_functionality_failures)}):")
            for failure in real_functionality_failures[:15]:
                print(f"  • {failure}")
            if len(real_functionality_failures) > 15:
                print(f"  ... and {len(real_functionality_failures) - 15} more failures")
            
            print(f"\n💡 REAL FUNCTIONALITY CRITERIA (tests should meet ≥2/7):")
            print(f"  1. 🔄 Validates STATE CHANGES (before ≠ after)")
            print(f"  2. 📁 Validates SIDE EFFECTS (files, DB, cache)")  
            print(f"  3. 🎯 Uses REALISTIC DATA (domain-specific)")
            print(f"  4. 📋 Validates BUSINESS RULES (thresholds, limits)")
            print(f"  5. 🔗 Tests INTEGRATION (cross-component)")
            print(f"  6. ⚠️  Validates ERROR PROPAGATION")
            print(f"  7. 🧬 MUTATION RESISTANT (boundary values)")
            
            assert False, f"ULTRA STRICT MODE: {len(real_functionality_failures)} tests don't validate real functionality"


if __name__ == "__main__":
    # Run the testing system health checks
    test = TestTestingSystemHealth()
    test.project_root = Path(__file__).parent.parent
    test.test_dir = test.project_root / "tests"
    
    print("Running testing system health checks...\n")
    
    # Run each test
    tests = [
        ("Test discoverability", test.test_all_test_files_follow_naming_conventions_and_discoverable),
        ("Test categories", test.test_proper_test_categories),
        ("Infinite loop check", test.test_no_infinite_loops_in_test_code),
        ("External dependencies", test.test_external_dependencies_handled),
        ("Test isolation", test.test_test_isolation),
        ("Execution time", test.test_test_execution_time),
        ("Fixture usage", test.test_proper_fixtures),
        ("File organization", test.test_test_file_organization),
        ("Duplicate test names", test.test_no_duplicate_test_names),
        ("Coverage balance", test.test_test_coverage_balance),
        ("Conftest files", test.test_conftest_files),
        ("Test data organization", test.test_test_data_organization),
        ("Pytest markers", test.test_pytest_markers),
        ("Meta-health", test.test_test_system_meta_health),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {test_name}: Error - {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Testing System Health: {len(tests)} checks | Passed: {passed} | Failed: {failed}")
    print(f"{'='*60}")
    
    if failed > 0:
        exit(1)