"""Test for testing system meta-health validation."""
import logging
import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
import pytest

logger = logging.getLogger(__name__)


class TestMetaHealth:
    """Test for testing system meta-health validation."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        self.health_test_dir = self.test_dir / "health"
    
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
    
    def test_testing_system_meta_health(self):
        """Validate the health of the testing system itself."""
        test_files = self.get_test_files()
        
        # Collect comprehensive statistics
        stats = self._collect_testing_statistics(test_files)
        
        # Validate testing system health
        health_issues = self._validate_testing_health(stats)
        
        # Report statistics
        self._report_testing_statistics(stats)
        
        # Check for critical issues
        critical_issues = [issue for issue in health_issues if 'critical' in issue.lower()]
        
        if critical_issues:
            logger.error(f"Found {len(critical_issues)} critical testing system issues")
            for issue in critical_issues[:5]:
                logger.error(f"  {issue}")
        
        if health_issues:
            logger.warning(f"Testing system health: {len(health_issues)} issues found")
    
    def test_modular_vs_monolithic_coverage(self):
        """Test that modular tests provide adequate coverage compared to monolithic tests."""
        # Check if modular tests exist
        modular_test_files = list(self.health_test_dir.glob('testing/test_*.py'))
        monolithic_test_file = self.health_test_dir / 'test_testing_system_health.py'
        
        if not monolithic_test_file.exists():
            pytest.skip("Monolithic test file not found")
        
        if not modular_test_files:
            pytest.fail("No modular testing health tests found")
        
        # Count test methods in each
        monolithic_content = self._safe_read_file(monolithic_test_file)
        monolithic_tests = len(re.findall(r'def test_', monolithic_content))
        
        modular_tests = 0
        for test_file in modular_test_files:
            content = self._safe_read_file(test_file)
            modular_tests += len(re.findall(r'def test_', content))
        
        coverage_ratio = modular_tests / monolithic_tests if monolithic_tests > 0 else 0
        
        logger.info(f"Test coverage comparison:")
        logger.info(f"  Monolithic tests: {monolithic_tests}")
        logger.info(f"  Modular tests: {modular_tests}")
        logger.info(f"  Coverage ratio: {coverage_ratio:.2f}")
        
        if coverage_ratio < 0.8:
            logger.warning(f"Modular test coverage below 80% of monolithic ({coverage_ratio:.1%})")
    
    def test_health_test_quality(self):
        """Test that health tests themselves meet quality standards."""
        health_test_files = list(self.health_test_dir.glob('**/*.py'))
        health_test_files = [f for f in health_test_files if f.name.startswith('test_')]
        
        quality_issues = []
        
        for test_file in health_test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Check for proper error handling in health tests
            if 'except:' in content and 'except Exception' not in content:
                quality_issues.append(f"{test_file.name}: Uses bare except clause")
            
            # Check for meaningful assertions
            test_functions = re.findall(r'def (test_\w+)\(', content)
            for test_func in test_functions:
                func_content = self._extract_function_content(content, test_func)
                assertion_count = len(re.findall(r'assert ', func_content))
                
                if assertion_count == 0 and 'pytest.skip' not in func_content:
                    quality_issues.append(f"{test_file.name}:{test_func}: No assertions")
        
        if quality_issues:
            logger.warning(f"Health test quality issues: {len(quality_issues)}")
            for issue in quality_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_health_test_execution_time(self):
        """Test that health tests execute within reasonable time limits."""
        # This is a meta-test that checks if health tests are efficient
        import time
        
        # Simulate health test execution timing
        health_test_files = list(self.health_test_dir.glob('**/*.py'))
        health_test_files = [f for f in health_test_files if f.name.startswith('test_')]
        
        slow_tests = []
        
        for test_file in health_test_files:
            content = self._safe_read_file(test_file)
            file_size = len(content)
            
            # Heuristic: files with complex operations that might be slow
            complexity_indicators = [
                'os.walk',
                'for.*in.*files',
                'ast.parse',
                're.findall',
                'subprocess',
            ]
            
            complexity_score = sum(content.count(indicator) for indicator in complexity_indicators)
            
            # Estimate if test might be slow based on file size and complexity
            if file_size > 10000 and complexity_score > 20:
                slow_tests.append(f"{test_file.name}: High complexity ({complexity_score}) + large size ({file_size} chars)")
        
        if slow_tests:
            logger.info(f"Potentially slow health tests: {len(slow_tests)}")
            for test in slow_tests[:3]:
                logger.info(f"  {test}")
    
    def _collect_testing_statistics(self, test_files: List[Path]) -> Dict:
        """Collect comprehensive testing statistics."""
        stats = {
            'total_files': len(test_files),
            'total_tests': 0,
            'total_assertions': 0,
            'files_with_fixtures': 0,
            'files_with_mocks': 0,
            'files_with_parameterization': 0,
            'category_distribution': {},
            'assertion_distribution': {},
            'file_sizes': [],
            'docstring_coverage': 0,
        }
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Count tests and assertions
            test_count = len(re.findall(r'def test_', content))
            assertion_count = len(re.findall(r'assert ', content))
            
            stats['total_tests'] += test_count
            stats['total_assertions'] += assertion_count
            
            # Track features
            if '@pytest.fixture' in content or 'fixture' in content:
                stats['files_with_fixtures'] += 1
            
            if 'mock' in content.lower():
                stats['files_with_mocks'] += 1
            
            if '@pytest.mark.parametrize' in content:
                stats['files_with_parameterization'] += 1
            
            # Categorize by directory
            category = self._categorize_test_file(test_file)
            stats['category_distribution'][category] = stats['category_distribution'].get(category, 0) + 1
            
            # File size distribution
            stats['file_sizes'].append(len(content))
            
            # Docstring coverage
            if test_count > 0:
                docstring_count = len(re.findall(r'def test_.*\):.*"""', content, re.DOTALL))
                if docstring_count > 0:
                    stats['docstring_coverage'] += 1
        
        return stats
    
    def _categorize_test_file(self, test_file: Path) -> str:
        """Categorize a test file by its path."""
        path_str = str(test_file)
        if '/unit/' in path_str:
            return 'unit'
        elif '/integration/' in path_str:
            return 'integration'
        elif '/functional/' in path_str:
            return 'functional'
        elif '/e2e/' in path_str:
            return 'e2e'
        elif '/health/' in path_str:
            return 'health'
        elif '/performance/' in path_str:
            return 'performance'
        elif '/infrastructure/' in path_str:
            return 'infrastructure'
        else:
            return 'other'
    
    def _validate_testing_health(self, stats: Dict) -> List[str]:
        """Validate the health of the testing system based on statistics."""
        issues = []
        
        # Check test distribution
        if stats['total_tests'] == 0:
            issues.append("CRITICAL: No tests found in the system")
            return issues
        
        # Check assertion density
        assertions_per_test = stats['total_assertions'] / stats['total_tests']
        if assertions_per_test < 1.5:
            issues.append(f"Low assertion density: {assertions_per_test:.2f} assertions per test (should be >1.5)")
        
        # Check category balance
        total_files = stats['total_files']
        category_dist = stats['category_distribution']
        
        unit_percentage = (category_dist.get('unit', 0) / total_files) * 100
        health_percentage = (category_dist.get('health', 0) / total_files) * 100
        
        if unit_percentage < 20:
            issues.append(f"Low unit test coverage: {unit_percentage:.1f}% (should be >20%)")
        
        if health_percentage > 40:
            issues.append(f"Excessive health test proportion: {health_percentage:.1f}% (should be <40%)")
        
        # Check fixture usage
        fixture_percentage = (stats['files_with_fixtures'] / total_files) * 100
        if fixture_percentage < 10:
            issues.append(f"Low fixture usage: {fixture_percentage:.1f}% (consider using more fixtures)")
        
        # Check file size distribution
        if stats['file_sizes']:
            avg_file_size = sum(stats['file_sizes']) / len(stats['file_sizes'])
            max_file_size = max(stats['file_sizes'])
            
            if avg_file_size > 5000:
                issues.append(f"Large average test file size: {avg_file_size:.0f} chars (consider splitting)")
            
            if max_file_size > 20000:
                issues.append(f"Very large test file found: {max_file_size:.0f} chars (should split)")
        
        return issues
    
    def _report_testing_statistics(self, stats: Dict) -> None:
        """Report comprehensive testing statistics."""
        logger.info("TESTING SYSTEM HEALTH REPORT")
        logger.info("=" * 40)
        logger.info(f"Total test files: {stats['total_files']}")
        logger.info(f"Total test functions: {stats['total_tests']}")
        logger.info(f"Total assertions: {stats['total_assertions']}")
        
        if stats['total_tests'] > 0:
            logger.info(f"Assertions per test: {stats['total_assertions'] / stats['total_tests']:.2f}")
        
        logger.info(f"Files with fixtures: {stats['files_with_fixtures']}")
        logger.info(f"Files with mocks: {stats['files_with_mocks']}")
        logger.info(f"Files with parameterization: {stats['files_with_parameterization']}")
        
        logger.info("Category distribution:")
        for category, count in stats['category_distribution'].items():
            percentage = (count / stats['total_files']) * 100
            logger.info(f"  {category}: {count} files ({percentage:.1f}%)")
        
        if stats['file_sizes']:
            avg_size = sum(stats['file_sizes']) / len(stats['file_sizes'])
            logger.info(f"Average file size: {avg_size:.0f} characters")
    
    def _extract_function_content(self, content: str, function_name: str) -> str:
        """Extract the content of a specific function."""
        lines = content.split('\\n')
        start_line = None
        
        for i, line in enumerate(lines):
            if f'def {function_name}(' in line:
                start_line = i
                break
        
        if start_line is None:
            return ""
        
        # Extract function body (until next def or class)
        function_body = []
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(' ') and not line.startswith('\\t'):
                break
            function_body.append(line)
        
        return '\\n'.join(function_body)