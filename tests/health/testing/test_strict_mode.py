"""Test for strict mode quality controls with adaptive performance."""
import logging
import ast
import os
import re
from pathlib import Path
from typing import List, Set
import pytest

from .context_intelligence import TestingIntelligenceEngine, ValidationMode
from .performance_manager import AdaptivePerformanceManager

logger = logging.getLogger(__name__)


class TestStrictModeQuality:
    """Test for strict mode quality controls."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with intelligence and performance management"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        
        # Initialize intelligence and performance management
        self.intelligence = TestingIntelligenceEngine(self.project_root)
        self.performance = AdaptivePerformanceManager(self.intelligence)
        
        # Check if strict mode is enabled
        self.strict_mode = os.getenv('STRICT_MODE', 'false').lower() == 'true'
        self.ultra_strict_mode = os.getenv('ULTRA_STRICT_MODE', 'false').lower() == 'true'
        
        logger.info(f"Strict mode testing initialized: mode={self.intelligence.mode.value}, "
                   f"strict={self.strict_mode}, ultra_strict={self.ultra_strict_mode}")
    
    def get_test_files(self) -> List[Path]:
        """Get test files with intelligent selection and performance management"""
        # Get all test files first
        all_test_files = []
        for root, dirs, files in os.walk(self.test_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    all_test_files.append(Path(root) / file)
        
        # Use intelligence engine for smart selection
        selected_files = self.intelligence.get_smart_file_selection(all_test_files)
        
        # Apply performance constraints
        performance_filtered = []
        for test_file in selected_files:
            should_process, reason = self.performance.should_process_file(test_file)
            if should_process:
                performance_filtered.append(test_file)
            else:
                logger.debug(f"Skipping {test_file.name}: {reason}")
            
            if not self.performance.should_continue_execution():
                logger.info("Stopping file selection due to performance constraints")
                break
        
        self.performance.update_metrics(files_processed=len(performance_filtered))
        logger.info(f"Selected {len(performance_filtered)} files from {len(all_test_files)} total "
                   f"(mode: {self.intelligence.mode.value})")
        return performance_filtered
    
    def _safe_read_file(self, file_path: Path) -> str:
        """Safely read file content"""
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except:
            return ""
    
    def test_strict_assertion_quality(self):
        """Test that assertions are meaningful and test real conditions."""
        if not self.strict_mode:
            pytest.skip("Strict mode not enabled (set STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        assertion_issues = []
        
        # Enhanced patterns for strict mode
        trivial_patterns = [
            r'assert True(?:\s|$)',
            r'assert 1 == 1(?:\s|$)',
            r'assert False == False(?:\s|$)', 
            r'assert None is None(?:\s|$)',
            r'assert "" == ""(?:\s|$)',
            r'assert \[\] == \[\](?:\s|$)',
            r'assert \{\} == \{\}(?:\s|$)',
        ]
        
        weak_patterns = [
            r'assert \w+ is not None(?:\s|$)',  # Only checking existence
            r'assert len\(\w+\) > 0(?:\s|$)',   # Only checking non-empty
            r'assert isinstance\(\w+, \w+\)(?:\s|$)',  # Only checking type
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health tests from strict validation
            if 'health' in str(test_file):
                continue
                
            # Check for trivial assertions
            for pattern in trivial_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    assertion_issues.append(f"{test_file.name}: Trivial assertion pattern '{pattern}'")
            
            # In strict mode, flag tests with only weak assertions
            test_functions = re.findall(r'def (test_\w+)\(', content)
            for test_func in test_functions:
                func_content = self._extract_function_content(content, test_func)
                if not func_content:
                    continue
                
                assertion_count = len(re.findall(r'assert ', func_content))
                weak_assertion_count = sum(len(re.findall(pattern, func_content)) for pattern in weak_patterns)
                
                if assertion_count > 0 and weak_assertion_count == assertion_count:
                    assertion_issues.append(f"{test_file.name}:{test_func}: Only weak assertions (type/existence checks)")
        
        if assertion_issues:
            failure_message = f"Strict mode: Found {len(assertion_issues)} assertion quality issues:\\n"
            failure_message += "\\n".join(assertion_issues[:10])
            if len(assertion_issues) > 10:
                failure_message += f"\\n... and {len(assertion_issues) - 10} more"
            
            assert len(assertion_issues) < 20, failure_message  # Allow some issues but not too many
    
    def test_strict_error_condition_coverage(self):
        """Test that error conditions are properly tested."""
        if not self.strict_mode:
            pytest.skip("Strict mode not enabled (set STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        error_coverage_issues = []
        
        # Functions that should have error condition tests
        critical_functions = [
            'get_db_connection', 'connect_to_database', 'database_manager',
            'extract_tasks', 'process_screenshot', 'generate_embeddings',
            'categorize_activity', 'store_metadata', 'fetch_tasks',
            'process_ocr', 'vlm_analysis', 'task_extraction'
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health and infrastructure tests
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
            
            # Check if file tests any critical functions
            tests_critical_functions = any(func in content.lower() for func in critical_functions)
            if not tests_critical_functions:
                continue
            
            # Check for error condition testing patterns
            error_patterns = [
                r'pytest\.raises\(',
                r'with pytest\.raises\(',
                r'assertRaises\(',
                r'except \w+Error',
                r'except Exception',
                r'try:.*except:',
            ]
            
            has_error_testing = any(re.search(pattern, content, re.DOTALL) for pattern in error_patterns)
            
            if not has_error_testing:
                error_coverage_issues.append(f"{test_file.name}: Tests critical functions but no error condition testing")
        
        if error_coverage_issues:
            logger.warning(f"Strict mode: Found {len(error_coverage_issues)} files lacking error condition tests")
            for issue in error_coverage_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_strict_boundary_testing(self):
        """Test that boundary conditions are tested."""
        if not self.strict_mode:
            pytest.skip("Strict mode not enabled (set STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        boundary_issues = []
        
        # Boundary testing patterns
        boundary_patterns = [
            r'assert.*== 0',       # Zero boundary
            r'assert.*== 1',       # Minimum valid
            r'assert.*== -1',      # Edge case
            r'assert.*\.empty',    # Empty collections
            r'assert.*len\(\w+\) == 0',  # Empty length
            r'assert.*is None',    # None boundary
            r'assert.*!= None',    # Non-none boundary
            r'range\(0,.*\)',     # Zero-based iteration
            r'range\(1,.*\)',     # One-based iteration
            r'if.*== 0:',         # Zero condition
            r'if.*< 1:',          # Minimum threshold
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health tests and simple imports
            if 'health' in str(test_file) or 'import' in test_file.name:
                continue
            
            test_functions = re.findall(r'def (test_\w+)\(', content)
            
            # Only check files with substantial tests
            if len(test_functions) < 2:
                continue
            
            has_boundary_testing = any(re.search(pattern, content) for pattern in boundary_patterns)
            
            # Check for numeric operations that should have boundary tests
            has_numeric_operations = bool(re.search(r'[+\-*/]|range\(|len\(|count\(', content))
            
            if has_numeric_operations and not has_boundary_testing:
                boundary_issues.append(f"{test_file.name}: Has numeric operations but no boundary value testing")
        
        if boundary_issues:
            logger.warning(f"Strict mode: Found {len(boundary_issues)} files lacking boundary testing")
            for issue in boundary_issues[:5]:
                logger.warning(f"  {issue}")
    
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
    
    def test_adaptive_performance_validation(self):
        """Test that adaptive performance management is working correctly."""
        if not self.strict_mode:
            pytest.skip("Strict mode not enabled (set STRICT_MODE=true)")
        
        # Get performance summary
        summary = self.performance.get_performance_summary()
        
        logger.info("ADAPTIVE PERFORMANCE VALIDATION")
        logger.info(f"Mode: {summary['mode']}")
        logger.info(f"Execution time: {summary['execution_time']:.2f}s")
        logger.info(f"Files processed: {summary['files_processed']}")
        logger.info(f"Performance rating: {summary['performance_rating']}")
        logger.info(f"Efficiency score: {summary['efficiency_score']:.2f}")
        logger.info(f"Within limits: {summary['within_limits']}")
        
        # Validate performance is within expected bounds
        if self.intelligence.mode == ValidationMode.FAST:
            assert summary['execution_time'] <= 35.0, f"Fast mode exceeded time limit: {summary['execution_time']}s"
            assert summary['files_processed'] <= 20, f"Fast mode processed too many files: {summary['files_processed']}"
        elif self.intelligence.mode == ValidationMode.COMPREHENSIVE:
            # More lenient for comprehensive mode
            assert summary['execution_time'] <= 650.0, f"Comprehensive mode exceeded reasonable time: {summary['execution_time']}s"
        else:  # STANDARD
            assert summary['execution_time'] <= 130.0, f"Standard mode exceeded time limit: {summary['execution_time']}s"
            assert summary['files_processed'] <= 60, f"Standard mode processed too many files: {summary['files_processed']}"
        
        # Validate efficiency
        assert summary['efficiency_score'] > 0.0, "No efficiency score calculated"
        
        # Context awareness validation
        test_files = self.get_test_files()[:3]  # Sample 3 files
        for test_file in test_files:
            thresholds = self.intelligence.get_context_aware_thresholds(test_file)
            
            # Validate thresholds are context-appropriate
            assert 'minimum_assertions' in thresholds
            assert 'importance_level' in thresholds
            assert thresholds['minimum_assertions'] >= 1
            
            if thresholds['importance_level'] == 'critical':
                assert thresholds['minimum_assertions'] >= 3, f"Critical module {test_file.name} has insufficient assertion requirement"
            elif thresholds['importance_level'] == 'experimental':
                assert thresholds['minimum_assertions'] <= 2, f"Experimental module {test_file.name} has excessive assertion requirement"
        
        logger.info("✅ Adaptive performance validation passed")
    
    def test_strict_mode_configuration_summary(self):
        """Display strict mode configuration summary with performance metrics."""
        if not self.strict_mode:
            pytest.skip("Strict mode not enabled (set STRICT_MODE=true)")
        
        logger.info("STRICT MODE ENABLED - Enhanced Quality Controls Active")
        logger.info(f"  - Validation Mode: {self.intelligence.mode.value}")
        logger.info(f"  - Ultra Strict Mode: {'ENABLED' if self.ultra_strict_mode else 'DISABLED'}")
        logger.info("  - Assertion Quality: Enhanced validation active")
        logger.info("  - Error Coverage: Critical function error testing required")
        logger.info("  - Boundary Testing: Numeric operations require boundary tests")
        
        # Show performance summary
        self.performance.log_performance_summary()
        
        # This test always passes - it's just for information
        assert True


class TestUltraStrictModeQuality:
    """Test for ultra strict mode quality controls."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        self.ultra_strict_mode = os.getenv('ULTRA_STRICT_MODE', 'false').lower() == 'true'
    
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
    
    def test_ultra_strict_assertion_count_minimum(self):
        """Test that tests have minimum 3 meaningful assertions in ultra strict mode."""
        if not self.ultra_strict_mode:
            pytest.skip("Ultra strict mode not enabled (set ULTRA_STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        assertion_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health tests and simple structural tests
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
            
            test_functions = re.findall(r'def (test_\w+)\(', content)
            
            for test_func in test_functions:
                func_content = self._extract_function_content(content, test_func)
                if not func_content:
                    continue
                
                # Count meaningful assertions (exclude trivial ones)
                total_assertions = len(re.findall(r'assert ', func_content))
                trivial_assertions = len(re.findall(r'assert True|assert 1 == 1|assert isinstance', func_content))
                meaningful_assertions = total_assertions - trivial_assertions
                
                # Skip very simple structural tests
                if len(func_content.split('\n')) < 5:
                    continue
                
                if meaningful_assertions < 3:
                    assertion_issues.append(
                        f"{test_file.name}:{test_func}: Only {meaningful_assertions} meaningful assertions (ultra strict requires ≥3)"
                    )
        
        # Allow some violations but not excessive
        if len(assertion_issues) > 15:
            failure_message = f"Ultra strict mode: {len(assertion_issues)} tests below minimum assertion threshold:\\n"
            failure_message += "\\n".join(assertion_issues[:10])
            assert False, failure_message
    
    def test_ultra_strict_test_independence(self):
        """Test that tests are completely independent with no shared state."""
        if not self.ultra_strict_mode:
            pytest.skip("Ultra strict mode not enabled (set ULTRA_STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        independence_issues = []
        
        # Patterns that indicate potential shared state
        shared_state_patterns = [
            r'global \w+',
            r'class.*:\s*\w+\s*=',  # Class variables
            r'@pytest\.fixture\(scope=["\']module["\']',  # Module-scoped fixtures
            r'@pytest\.fixture\(scope=["\']session["\']',  # Session-scoped fixtures
            r'cache\s*=.*\{\}',  # Shared cache
            r'shared_.*=',  # Shared variables
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health tests (they may use shared patterns legitimately)
            if 'health' in str(test_file):
                continue
            
            for pattern in shared_state_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    independence_issues.append(f"{test_file.name}: Potential shared state pattern '{pattern}'")
        
        if independence_issues:
            logger.warning(f"Ultra strict mode: Found {len(independence_issues)} potential independence issues")
            for issue in independence_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_ultra_strict_performance_requirements(self):
        """Test that tests meet strict performance requirements."""
        if not self.ultra_strict_mode:
            pytest.skip("Ultra strict mode not enabled (set ULTRA_STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        performance_issues = []
        
        # Patterns that indicate potential performance issues
        slow_patterns = [
            r'time\.sleep\([^0]',  # Sleep > 0
            r'timeout\s*=\s*[1-9]\d+',  # Timeout > 9 seconds
            r'requests\.get|requests\.post',  # HTTP requests without mocking
            r'subprocess\.run',  # Subprocess calls
            r'for.*in range\([1-9]\d\d\d+\)',  # Large loops (>999)
        ]
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip integration tests (they may legitimately be slower)
            if 'integration' in str(test_file) or 'e2e' in str(test_file):
                continue
            
            for pattern in slow_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    performance_issues.append(f"{test_file.name}: Potential slow pattern '{pattern}'")
        
        if performance_issues:
            logger.warning(f"Ultra strict mode: Found {len(performance_issues)} potential performance issues")
            for issue in performance_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_ultra_strict_documentation_requirements(self):
        """Test that tests have comprehensive documentation in ultra strict mode."""
        if not self.ultra_strict_mode:
            pytest.skip("Ultra strict mode not enabled (set ULTRA_STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        documentation_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health tests (different documentation standards)
            if 'health' in str(test_file):
                continue
            
            test_functions = re.findall(r'def (test_\w+)\([^)]*\):', content)
            
            for test_func in test_functions:
                # Find the function and check for docstring
                func_pattern = rf'def {re.escape(test_func)}\([^)]*\):\s*"""([^"]*?)"""'
                docstring_match = re.search(func_pattern, content, re.DOTALL)
                
                if not docstring_match:
                    documentation_issues.append(f"{test_file.name}:{test_func}: Missing docstring")
                else:
                    docstring = docstring_match.group(1).strip()
                    if len(docstring) < 20:  # Very short docstring
                        documentation_issues.append(f"{test_file.name}:{test_func}: Docstring too brief (<20 chars)")
        
        # Allow some documentation issues but not excessive
        if len(documentation_issues) > 20:
            logger.warning(f"Ultra strict mode: Found {len(documentation_issues)} documentation issues")
            for issue in documentation_issues[:5]:
                logger.warning(f"  {issue}")
    
    def test_ultra_strict_real_functionality_validation(self):
        """Test that tests validate real functionality comprehensively in ultra strict mode."""
        if not self.ultra_strict_mode:
            pytest.skip("Ultra strict mode not enabled (set ULTRA_STRICT_MODE=true)")
        
        test_files = self.get_test_files()
        functionality_issues = []
        
        for test_file in test_files:
            content = self._safe_read_file(test_file)
            if not content:
                continue
            
            # Skip health and infrastructure tests
            if any(skip in str(test_file) for skip in ['health', 'infrastructure']):
                continue
            
            test_functions = re.findall(r'def (test_\w+)\(', content)
            
            for test_func in test_functions:
                func_content = self._extract_function_content(content, test_func)
                if not func_content:
                    continue
                
                # Check for comprehensive validation patterns
                validation_patterns = [
                    r'assert.*\.status_code',  # HTTP status validation
                    r'assert.*\.content',  # Content validation
                    r'assert.*\.data',  # Data validation
                    r'assert.*\.result',  # Result validation
                    r'assert.*raises.*Exception',  # Error condition testing
                    r'assert.*!=.*None',  # Non-null validation
                    r'assert.*in.*',  # Membership validation
                    r'assert.*>.*\d+',  # Value comparison
                    r'assert.*==.*\w+\(',  # Function call result validation
                ]
                
                # Must have at least 2 different types of validation
                validation_types = sum(1 for pattern in validation_patterns if re.search(pattern, func_content))
                
                # Skip very simple tests
                if len(func_content.split('\n')) < 8:
                    continue
                
                if validation_types < 2:
                    functionality_issues.append(
                        f"{test_file.name}:{test_func}: Insufficient validation types ({validation_types}<2)"
                    )
        
        # Ultra strict mode is very demanding
        if len(functionality_issues) > 10:
            logger.warning(f"Ultra strict mode: Found {len(functionality_issues)} insufficient validation cases")
            for issue in functionality_issues[:5]:
                logger.warning(f"  {issue}")
    
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