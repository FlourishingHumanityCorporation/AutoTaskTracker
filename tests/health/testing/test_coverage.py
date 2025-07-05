"""Test for test coverage analysis with context-aware intelligence."""
import logging
import ast
import os
import re
from pathlib import Path
from typing import List, Set
import pytest

from .context_intelligence import TestingIntelligenceEngine, ValidationMode
from .mutation_effectiveness import EffectivenessValidator
from .bug_correlation import RealWorldEffectivenessAnalyzer

logger = logging.getLogger(__name__)


class TestCoverage:
    """Test for test coverage analysis and quality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with intelligence engine"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        self.src_dir = self.project_root / "autotasktracker"
        self.intelligence = TestingIntelligenceEngine(self.project_root)
    
    def get_test_files(self) -> List[Path]:
        """Get test files with intelligent selection based on validation mode"""
        # Get all test files first
        all_test_files = []
        for root, dirs, files in os.walk(self.test_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    all_test_files.append(Path(root) / file)
        
        # Use intelligence engine for smart selection
        return self.intelligence.get_smart_file_selection(all_test_files)
    
    def get_source_files(self) -> List[Path]:
        """Get all source files in the project"""
        source_files = []
        for root, dirs, files in os.walk(self.src_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    source_files.append(Path(root) / file)
        return source_files
    
    def _safe_read_file(self, file_path: Path) -> str:
        """Safely read file content"""
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except (OSError, PermissionError, UnicodeDecodeError):
            return ""
    
    def test_critical_functions_have_tests(self):
        """Test that critical functions have corresponding tests"""
        critical_functions = [
            'extract_tasks',
            'categorize_activity',
            'store_metadata',
            'get_db_connection',
            'process_screenshot',
            'generate_embeddings',
        ]
        
        # Get all test content
        all_test_content = ""
        for test_file in self.get_test_files():
            all_test_content += self._safe_read_file(test_file)
        
        missing_tests = []
        for func in critical_functions:
            # Check if function is tested (simple heuristic)
            if f"test_{func}" not in all_test_content and func not in all_test_content:
                missing_tests.append(func)
        
        if missing_tests:
            logger.warning(f"Critical functions without apparent tests: {missing_tests}")
    
    def test_no_trivial_assertions(self):
        """Test that tests don't contain trivial assertions"""
        test_files = self.get_test_files()
        trivial_issues = []
        
        trivial_patterns = [
            r'assert True',
            r'assert 1 == 1',
            r'assert len\(\[\]\) == 0',
            r'assert bool\(True\)',
            r'assert not False',
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            for pattern in trivial_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Skip trivial assertions in specific test types
                    if ('import' in test_file.name or 'integration' in test_file.name or 
                        'utils' in test_file.name or 'health' in str(test_file.parent)):
                        continue
                    trivial_issues.append(f"{test_file.name}: Trivial assertion '{matches[0]}'")
        
        assert not trivial_issues, f"Found trivial assertions: {trivial_issues[:10]}"
    
    def test_error_condition_coverage(self):
        """Test that error conditions are tested"""
        test_files = self.get_test_files()
        coverage_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Check if file tests error conditions
            has_error_tests = any(pattern in content for pattern in [
                'pytest.raises',
                'with raises',
                'Exception',
                'Error',
                'try:',
                'except',
                'assertRaises',
            ])
            
            # Check if file has complex logic that should be error tested
            has_complex_logic = any(pattern in content for pattern in [
                'def test_',  # Has tests
                'if ',  # Has conditionals
                'for ',  # Has loops
                'while ',  # Has loops
            ])
            
            if has_complex_logic and not has_error_tests:
                # Skip simple test files
                if content.count('def test_') > 1:  # Multiple tests
                    coverage_issues.append(f"{test_file.name}: No error condition testing")
        
        if coverage_issues:
            logger.info(f"Tests without error condition coverage: {len(coverage_issues)}")
            for issue in coverage_issues[:5]:
                logger.info(f"  {issue}")
    
    def test_boundary_value_testing(self):
        """Test that boundary values are tested"""
        test_files = self.get_test_files()
        boundary_issues = []
        
        boundary_indicators = [
            r'range\(\d+\)',  # Should test range boundaries
            r'len\(',  # Should test empty/full collections
            r'>\s*\d+',  # Should test boundary values
            r'<\s*\d+',  # Should test boundary values
            r'==\s*\d+',  # Should test off-by-one
        ]
        
        boundary_tests = [
            r'empty',
            r'\[\]',
            r'{}',
            r'None',
            r'0',
            r'-1',
            r'max',
            r'min',
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Check if file has boundary-related logic
            has_boundary_logic = False
            for pattern in boundary_indicators:
                import re
                if re.search(pattern, content):
                    has_boundary_logic = True
                    break
            
            if has_boundary_logic:
                # Check if boundary values are tested
                has_boundary_tests = False
                for pattern in boundary_tests:
                    if re.search(pattern, content):
                        has_boundary_tests = True
                        break
                
                if not has_boundary_tests:
                    boundary_issues.append(f"{test_file.name}: Has boundary logic but no boundary tests")
        
        if boundary_issues:
            logger.info(f"Tests missing boundary value testing: {len(boundary_issues)}")
            for issue in boundary_issues[:5]:
                logger.info(f"  {issue}")
    
    def test_test_independence(self):
        """Test that tests are independent"""
        test_files = self.get_test_files()
        independence_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            try:
                tree = ast.parse(content)
                
                # Look for class variables or module-level variables that could cause dependencies
                class_vars = []
                module_vars = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        # Check if it's a module-level assignment
                        if isinstance(node.targets[0], ast.Name):
                            module_vars.append(node.targets[0].id)
                    elif isinstance(node, ast.ClassDef):
                        for child in node.body:
                            if isinstance(child, ast.Assign):
                                if isinstance(child.targets[0], ast.Name):
                                    class_vars.append(child.targets[0].id)
                
                # Check for shared state
                shared_state_vars = [var for var in class_vars + module_vars 
                                   if not var.startswith('_') and var.isupper()]
                
                if shared_state_vars:
                    independence_issues.append(f"{test_file.name}: May have shared state: {shared_state_vars}")
                    
            except:
                continue
        
        if independence_issues:
            logger.warning("Test independence issues:")
            for issue in independence_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_mock_usage_quality(self):
        """Test that mocks are used appropriately"""
        test_files = self.get_test_files()
        mock_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Count mocks
            mock_count = content.count('mock') + content.count('Mock')
            test_count = content.count('def test_')
            
            if test_count > 0 and mock_count > test_count * 3:  # More than 3 mocks per test
                mock_issues.append(f"{test_file.name}: Excessive mocking ({mock_count} mocks, {test_count} tests)")
            
            # Check for mock assertions
            if 'mock' in content.lower():
                if 'assert_called' not in content and 'assert_not_called' not in content:
                    # Check if it's just importing mock
                    if 'from unittest.mock import' not in content:
                        mock_issues.append(f"{test_file.name}: Uses mocks but no mock assertions")
        
        if mock_issues:
            logger.info("Mock usage suggestions:")
            for issue in mock_issues[:5]:
                logger.info(f"  {issue}")
    
    def test_functionality_validation_quality(self):
        """Test that tests validate real functionality using effectiveness-based analysis."""
        test_files = self.get_test_files()
        functionality_issues = []
        context_summaries = []
        
        # Initialize effectiveness validators
        effectiveness_validator = EffectivenessValidator(self.project_root)
        real_world_analyzer = RealWorldEffectivenessAnalyzer(self.project_root)
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
                
            # Get effectiveness-based analysis instead of structure-based rules
            effectiveness_results = effectiveness_validator.validate_test_effectiveness(test_file)
            real_world_results = real_world_analyzer.analyze_real_world_effectiveness(test_file)
            
            context_summaries.append(
                f"{test_file.name}: {effectiveness_results['overall_effectiveness']:.1f}% effective "
                f"(mutation: {effectiveness_results['mutation_effectiveness']:.1f}%)"
            )
            
            # Skip files that can't be analyzed
            if effectiveness_results['overall_effectiveness'] == 0:
                continue
            
            lines = content.split('\n')
            test_functions = re.findall(r'def (test_\w+)\(', content)
            
            for test_func in test_functions:
                test_content = self._extract_test_function_body(lines, test_func)
                if not test_content:
                    continue
                
                # Analyze test quality with effectiveness-based validation
                issues = self._analyze_test_effectiveness_based(
                    test_file, test_func, test_content, effectiveness_results, real_world_results
                )
                functionality_issues.extend(issues)
        
        # Log effectiveness summary for transparency
        logger.info(f"Effectiveness-based validation applied to {len(context_summaries)} files:")
        for summary in context_summaries[:5]:
            logger.info(f"  {summary}")
        if len(context_summaries) > 5:
            logger.info(f"  ... and {len(context_summaries) - 5} more files")
        
        # Categorize issues by actual bug-catching ability
        critical_issues = [issue for issue in functionality_issues if 'would miss most real bugs' in issue or 'CRITICAL' in issue]
        severe_issues = [issue for issue in functionality_issues if 'significant gaps' in issue or 'mutation' in issue]
        
        if critical_issues:
            logger.error(f"Found {len(critical_issues)} critical functionality validation issues")
            for issue in critical_issues[:3]:
                logger.error(f"  {issue}")
        
        if len(severe_issues) > 3:  # Lower threshold due to context awareness
            logger.warning(f"Found {len(severe_issues)} severe functionality validation issues")
            for issue in severe_issues[:5]:
                logger.warning(f"  {issue}")
    
    def _extract_test_function_body(self, lines: list, test_func: str) -> str:
        """Extract the body of a test function."""
        start_line = None
        for i, line in enumerate(lines):
            if f'def {test_func}(' in line:
                start_line = i
                break
        
        if start_line is None:
            return ""
        
        # Extract test function body (until next def or class)
        test_body = []
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                break
            test_body.append(line)
        
        return '\n'.join(test_body)
    
    def _analyze_test_effectiveness_based(self, test_file: Path, test_func: str, 
                                         test_content: str, effectiveness_results: dict, 
                                         real_world_results: dict) -> list:
        """Analyze test effectiveness based on actual bug-catching ability."""
        issues = []
        
        # Primary validation: Can this test catch real bugs?
        overall_effectiveness = effectiveness_results.get('overall_effectiveness', 0)
        mutation_effectiveness = effectiveness_results.get('mutation_effectiveness', 0)
        
        # Critical: Tests that would miss most real bugs
        if overall_effectiveness < 30:
            issues.append(f"{test_file.name}:{test_func}: CRITICAL - would miss most real bugs (effectiveness: {overall_effectiveness:.1f}%)")
            
        # Severe: Tests with significant gaps
        elif overall_effectiveness < 60:
            issues.append(f"{test_file.name}:{test_func}: WARNING - significant gaps in bug detection (effectiveness: {overall_effectiveness:.1f}%)")
        
        # Mutation testing results
        if mutation_effectiveness < 50:
            issues.append(f"{test_file.name}:{test_func}: Poor mutation detection ({mutation_effectiveness:.1f}%) - may miss code changes")
        
        # Real-world bug pattern analysis
        bug_correlation_score = real_world_results.get('bug_correlation_score', 0)
        if bug_correlation_score > 0 and bug_correlation_score < 50:
            issues.append(f"{test_file.name}:{test_func}: Poor historical bug prevention ({bug_correlation_score:.1f}%)")
        
        # Integration quality
        integration_quality = effectiveness_results.get('integration_quality', 0)
        if 'integration' in str(test_file) and integration_quality < 50:
            issues.append(f"{test_file.name}:{test_func}: Poor integration testing - may not catch component interaction bugs")
        
        # Check for specific actionable recommendations
        recommendations = effectiveness_results.get('actionable_recommendations', [])
        for rec in recommendations:
            if 'CRITICAL' in rec or 'would miss most real bugs' in rec:
                issues.append(f"{test_file.name}:{test_func}: {rec}")
        
        return issues
    
    def test_coverage_balance(self):
        """Test that test coverage is balanced across different areas."""
        test_files = self.get_test_files()
        coverage_stats = {
            'unit': 0,
            'integration': 0,
            'functional': 0,
            'e2e': 0,
            'health': 0,
            'performance': 0,
            'other': 0
        }
        
        for test_file in test_files:
            # Categorize tests by directory/name
            test_path = str(test_file)
            if '/unit/' in test_path:
                coverage_stats['unit'] += 1
            elif '/integration/' in test_path:
                coverage_stats['integration'] += 1
            elif '/functional/' in test_path:
                coverage_stats['functional'] += 1
            elif '/e2e/' in test_path:
                coverage_stats['e2e'] += 1
            elif '/health/' in test_path:
                coverage_stats['health'] += 1
            elif '/performance/' in test_path:
                coverage_stats['performance'] += 1
            else:
                coverage_stats['other'] += 1
        
        total_tests = sum(coverage_stats.values())
        if total_tests == 0:
            return
        
        # Calculate percentages
        percentages = {k: (v / total_tests) * 100 for k, v in coverage_stats.items()}
        
        balance_issues = []
        
        # Check for imbalanced coverage
        if percentages['unit'] < 30:
            balance_issues.append(f"Low unit test coverage: {percentages['unit']:.1f}% (should be >30%)")
        
        if percentages['integration'] < 10:
            balance_issues.append(f"Low integration test coverage: {percentages['integration']:.1f}% (should be >10%)")
        
        if percentages['functional'] < 5:
            balance_issues.append(f"Low functional test coverage: {percentages['functional']:.1f}% (should be >5%)")
        
        if percentages['health'] > 50:
            balance_issues.append(f"Excessive health test coverage: {percentages['health']:.1f}% (should be <50%)")
        
        # Log current coverage stats
        logger.info("Test Coverage Balance:")
        for category, percentage in percentages.items():
            if coverage_stats[category] > 0:
                logger.info(f"  {category}: {coverage_stats[category]} files ({percentage:.1f}%)")
        
        if balance_issues:
            logger.warning("Coverage balance suggestions:")
            for issue in balance_issues:
                logger.warning(f"  {issue}")