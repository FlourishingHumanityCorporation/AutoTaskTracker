"""Mutation testing integration to measure actual bug-catching effectiveness.

This module implements real effectiveness validation by introducing controlled
mutations and measuring which tests catch them. This answers the critical question:
"Would this test catch the bug that will happen next week?"
"""

import ast
import logging
import os
import tempfile
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Union, Any, Protocol
from dataclasses import dataclass
from enum import Enum
import importlib.util

# Type definitions for better code clarity
class ConfigManagerProtocol(Protocol):
    """Protocol for config manager dependency injection."""
    def get_config(self) -> Any: ...

class PerformanceOptimizerProtocol(Protocol):
    """Protocol for performance optimizer dependency injection."""
    def optimize_analysis(self, func, files, **kwargs) -> List[Tuple[Path, Dict]]: ...
    def get_performance_report(self) -> Dict: ...
    def clear_cache(self) -> None: ...

try:
    from .config import ConfigManager, EffectivenessConfig
    from .shared_utilities import (
        temporary_file_mutation,
        ValidationLimits,
        CompiledPatterns,
        validate_file_for_analysis,
        standardize_error_message
    )
except ImportError:
    # Fallback for direct execution
    try:
        from config import ConfigManager, EffectivenessConfig
        from shared_utilities import (
            temporary_file_mutation,
            ValidationLimits,
            CompiledPatterns,
            validate_file_for_analysis,
            standardize_error_message
        )
    except ImportError:
        # Create minimal fallback if modules not available
        from contextlib import contextmanager
        
        class EffectivenessConfig:
            def __init__(self):
                self.mutation = type('obj', (object,), {
                    'max_mutations_per_file': 10,
                    'timeout_seconds': 30,
                    'max_file_size_kb': 100
                })()
        
        class ConfigManager:
            def __init__(self, project_root):
                pass
            def get_config(self):
                return EffectivenessConfig()
        
        class ValidationLimits:
            MAX_MUTATIONS_PER_FILE = 20
        
        class CompiledPatterns:
            OFF_BY_ONE = re.compile(r'>\s*\d+|<\s*\d+|>=\s*\d+|<=\s*\d+')
            BOOLEAN_LOGIC = re.compile(r'\s+and\s+|\s+or\s+')
            BOUNDARY_NUMS = re.compile(r'\b0\b|\b1\b|\b-1\b')
        
        @contextmanager
        def temporary_file_mutation(source_file, mutated_content):
            original_content = source_file.read_text()
            try:
                source_file.write_text(mutated_content)
                yield
            finally:
                source_file.write_text(original_content)
        
        def validate_file_for_analysis(file_path, max_size_kb=100):
            return file_path.exists() and file_path.is_file()
        
        def standardize_error_message(error, context=""):
            return f"{context}: {type(error).__name__}: {str(error)}"

logger = logging.getLogger(__name__)


class MutationType(Enum):
    """Types of mutations that represent common bugs."""
    OFF_BY_ONE = "off_by_one"          # >, < become >=, <=
    BOOLEAN_FLIP = "boolean_flip"       # True/False flip
    OPERATOR_CHANGE = "operator_change" # +, -, *, / changes
    CONDITION_FLIP = "condition_flip"   # and/or flip
    BOUNDARY_SHIFT = "boundary_shift"   # 0 becomes 1, -1
    RETURN_CHANGE = "return_change"     # None, empty list, etc.
    # AutoTaskTracker-specific patterns
    DATABASE_ERROR = "database_error"   # Database connection/query issues
    API_FAILURE = "api_failure"        # API timeout/connection failures
    EXCEPTION_HANDLING = "exception_handling"  # except: -> specific exceptions


@dataclass
class MutationResult:
    """Result of applying a mutation and running tests."""
    mutation_type: MutationType
    original_code: str
    mutated_code: str
    tests_failed: List[str]  # Tests that caught this mutation
    tests_passed: List[str]  # Tests that missed this mutation
    file_path: Path
    line_number: int
    effectiveness_score: float  # 0.0 to 1.0


@dataclass
class TestEffectivenessReport:
    """Comprehensive effectiveness report for a test file."""
    test_file: Path
    source_file: Path
    mutations_caught: int
    mutations_missed: int
    effectiveness_percentage: float
    weak_areas: List[str]  # Code areas not protected by tests
    strong_areas: List[str]  # Well-protected code areas
    recommendations: List[str]


class SimpleMutationTester:
    """Lightweight mutation testing focused on common real-world bugs."""
    
    def __init__(self, project_root: Path, config: Optional[EffectivenessConfig] = None):
        self.project_root = project_root
        self.src_dir = project_root / "autotasktracker"
        self.test_dir = project_root / "tests"
        
        # Initialize configuration
        if config is None:
            config_manager = ConfigManager(project_root)
            self.config = config_manager.get_config()
        else:
            self.config = config
        
    def analyze_test_effectiveness(self, test_file: Path) -> TestEffectivenessReport:
        """Analyze how effectively a test file catches real bugs."""
        # Find the corresponding source file
        source_file = self._find_source_file(test_file)
        if not source_file:
            return self._create_empty_report(test_file, "No corresponding source file found")
            
        # Generate targeted mutations based on the source code
        mutations = self._generate_smart_mutations(source_file)
        if not mutations:
            return self._create_empty_report(test_file, "No meaningful mutations possible")
            
        # Test each mutation with configurable limit
        results = []
        max_mutations = self.config.mutation.max_mutations_per_file
        mutations_to_test = mutations[:max_mutations]
        
        # Use parallel execution if enabled and worthwhile
        if (getattr(self.config, 'enable_parallel_execution', False) and 
            len(mutations_to_test) > 2):
            logger.info(f"Using parallel execution for {len(mutations_to_test)} mutations with {getattr(self.config, 'max_worker_threads', 4)} workers")
            results = self._test_mutations_parallel(test_file, source_file, mutations_to_test)
        else:
            # Sequential execution for small mutation sets
            logger.info(f"Using sequential execution for {len(mutations_to_test)} mutations")
            for mutation in mutations_to_test:
                result = self._test_mutation(test_file, source_file, mutation)
                if result:
                    results.append(result)
        
        # Analyze results
        return self._analyze_mutation_results(test_file, source_file, results)
    
    def _find_source_file(self, test_file: Path) -> Optional[Path]:
        """Find the source file that corresponds to this test file."""
        # Extract module name from test file
        test_name = test_file.name
        
        # Common patterns for test file naming
        patterns = [
            test_name.replace('test_', '').replace('.py', '.py'),  # test_foo.py -> foo.py
            test_name.replace('test_', '').replace('_test.py', '.py'),  # foo_test.py -> foo.py
        ]
        
        # Search in source directory
        for pattern in patterns:
            for src_file in self.src_dir.rglob(pattern):
                if src_file.is_file() and src_file.suffix == '.py':
                    return src_file
                    
        # If exact match not found, look for related files
        base_name = test_name.replace('test_', '').replace('.py', '')
        for src_file in self.src_dir.rglob('*.py'):
            if base_name in src_file.name or src_file.stem in test_name:
                return src_file
                
        return None
    
    def _generate_smart_mutations(self, source_file: Path) -> List[Dict]:
        """Generate mutations targeting common bug patterns."""
        try:
            content = source_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Could not parse {source_file}: {e}")
            return []
        except (OSError, IOError) as e:
            logger.warning(f"Could not read {source_file}: {e}")
            return []
        except UnicodeDecodeError as e:
            logger.warning(f"Encoding error in {source_file}: {e}")
            return []
            
        mutations = []
        lines = content.split('\n')
        
        # Off-by-one errors (most common real bug) - use pre-compiled pattern
        for i, line in enumerate(lines):
            if CompiledPatterns.OFF_BY_ONE.search(line):
                original = line.strip()
                # Flip comparison operators
                mutated = original
                mutated = re.sub(r'>\s*(\d+)', r'>= \1', mutated)
                mutated = re.sub(r'<\s*(\d+)', r'<= \1', mutated)
                mutated = re.sub(r'>=\s*(\d+)', r'> \1', mutated) 
                mutated = re.sub(r'<=\s*(\d+)', r'< \1', mutated)
                
                if mutated != original:
                    mutations.append({
                        'type': MutationType.OFF_BY_ONE,
                        'line': i,
                        'original': original,
                        'mutated': mutated
                    })
        
        # Boolean logic errors - use pre-compiled pattern
        for i, line in enumerate(lines):
            if CompiledPatterns.BOOLEAN_LOGIC.search(line):
                original = line.strip()
                mutated = original.replace(' and ', ' or ').replace(' or ', ' and ')
                if mutated != original:
                    mutations.append({
                        'type': MutationType.CONDITION_FLIP,
                        'line': i,
                        'original': original,
                        'mutated': mutated
                    })
        
        # Boundary value errors - use pre-compiled pattern
        for i, line in enumerate(lines):
            if CompiledPatterns.BOUNDARY_NUMS.search(line):
                original = line.strip()
                mutated = original
                mutated = re.sub(r'\b0\b', '1', mutated)
                mutated = re.sub(r'\b1\b', '0', mutated) 
                mutated = re.sub(r'\b-1\b', '0', mutated)
                
                if mutated != original and 'assert' not in mutated:  # Don't mutate test assertions
                    mutations.append({
                        'type': MutationType.BOUNDARY_SHIFT,
                        'line': i,
                        'original': original,
                        'mutated': mutated
                    })
        
        # AutoTaskTracker-specific: Database connection patterns
        for i, line in enumerate(lines):
            if 'sqlite3.connect' in line or 'DatabaseManager()' in line:
                original = line.strip()
                # Simulate database connection failure
                mutated = original.replace('sqlite3.connect', 'raise sqlite3.Error("Connection failed") #')
                mutated = mutated.replace('DatabaseManager()', 'raise ConnectionError("DB unavailable") #')
                if mutated != original:
                    mutations.append({
                        'type': MutationType.DATABASE_ERROR,
                        'line': i,
                        'original': original,
                        'mutated': mutated
                    })
        
        # AutoTaskTracker-specific: Exception handling patterns
        for i, line in enumerate(lines):
            if re.search(r'except\s*:', line):
                original = line.strip()
                # Change bare except to specific exception
                mutated = re.sub(r'except\s*:', 'except ValueError:', original)
                if mutated != original:
                    mutations.append({
                        'type': MutationType.EXCEPTION_HANDLING,
                        'line': i,
                        'original': original,
                        'mutated': mutated
                    })
        
        # Limit mutations based on configuration
        max_mutations = getattr(self.config.mutation, 'max_mutations_per_file', ValidationLimits.MAX_MUTATIONS_PER_FILE)
        return mutations[:max_mutations]
    
    def _test_mutations_parallel(self, test_file: Path, source_file: Path, mutations: List[Dict]) -> List[MutationResult]:
        """Test multiple mutations in parallel for better performance.
        
        Args:
            test_file: Path to test file
            source_file: Path to source file to mutate
            mutations: List of mutations to test
            
        Returns:
            List of mutation results
        """
        import concurrent.futures
        import multiprocessing
        
        # Determine optimal number of workers
        max_workers = min(
            len(mutations),
            getattr(self.config, 'max_worker_threads', 4),
            multiprocessing.cpu_count()
        )
        
        results = []
        
        # Use ProcessPoolExecutor for true parallelism (avoids GIL)
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all mutations for parallel processing
            future_to_mutation = {
                executor.submit(
                    self._test_mutation_isolated, 
                    test_file, 
                    source_file, 
                    mutation,
                    self.config
                ): mutation 
                for mutation in mutations
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_mutation):
                try:
                    result = future.result(timeout=self.config.mutation.timeout_seconds * 2)
                    if result:
                        results.append(result)
                except concurrent.futures.TimeoutError:
                    mutation = future_to_mutation[future]
                    logger.warning(f"Parallel mutation test timeout for {mutation['type']} at line {mutation['line']}")
                except Exception as e:
                    mutation = future_to_mutation[future]
                    logger.error(f"Parallel mutation test failed: {e}")
        
        return results
    
    @staticmethod
    def _test_mutation_isolated(test_file: Path, source_file: Path, mutation: Dict, config) -> Optional[MutationResult]:
        """Static method for parallel execution to avoid pickling issues.
        
        This method recreates necessary state for isolated execution.
        """
        # Create a minimal tester instance for this mutation
        from pathlib import Path
        project_root = test_file.parent.parent.parent  # Approximate project root
        
        tester = SimpleMutationTester(project_root, config)
        return tester._test_mutation(test_file, source_file, mutation)
    
    def _test_mutation(self, test_file: Path, source_file: Path, mutation: Dict) -> Optional[MutationResult]:
        """Apply a mutation and run tests to see if they catch it."""
        backup_content = None
        temp_path = None
        
        try:
            # Validate inputs
            if not test_file.exists():
                logger.warning(f"Test file not found: {test_file}")
                return None
                
            if not source_file.exists():
                logger.warning(f"Source file not found: {source_file}")
                return None
            
            # Read original source with better error handling
            try:
                original_content = source_file.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                logger.warning(f"Cannot decode {source_file} as UTF-8")
                return None
            except PermissionError:
                logger.warning(f"Permission denied reading {source_file}")
                return None
                
            lines = original_content.split('\n')
            
            # Apply mutation with validation
            line_idx = mutation['line']
            if line_idx >= len(lines):
                logger.warning(f"Line index {line_idx} out of range for {source_file}")
                return None
            
            original_line = lines[line_idx]
            if mutation['original'].strip() not in original_line:
                logger.warning(f"Mutation pattern not found in line {line_idx}: {mutation['original']}")
                return None
                
            lines[line_idx] = lines[line_idx].replace(
                mutation['original'].strip(),
                mutation['mutated'].strip()
            )
            mutated_content = '\n'.join(lines)
            
            # Validate mutated content is different
            if mutated_content == original_content:
                logger.warning(f"Mutation did not change content: {mutation}")
                return None
            
            # Write mutated source to temporary file
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                    temp_file.write(mutated_content)
                    temp_path = Path(temp_file.name)
            except OSError as e:
                logger.warning(f"Cannot create temp file: {e}")
                return None
            
            # Use the robust temporary_file_mutation context manager
            try:
                with temporary_file_mutation(source_file, mutated_content):
                    # Run the specific test file with enhanced error handling
                    try:
                        timeout = self.config.mutation.timeout_seconds
                        logger.info(f"Running pytest on {test_file} with mutation at line {line_idx}")
                        result = subprocess.run([
                            'python', '-m', 'pytest', str(test_file), '-v', '--tb=no', '-q'
                        ], capture_output=True, text=True, cwd=self.project_root, timeout=timeout)
                        logger.info(f"Test result: return code={result.returncode}, stdout={len(result.stdout)} chars, stderr={len(result.stderr)} chars")
                    except subprocess.TimeoutExpired:
                        timeout = self.config.mutation.timeout_seconds
                        logger.warning(f"Test execution timeout ({timeout}s) for {test_file}")
                        return None
                    except FileNotFoundError:
                        logger.warning("pytest not found - cannot run mutation tests")
                        return None
                    
                    # Analyze test results
                    tests_failed = []
                    tests_passed = []
                    
                    if result.returncode != 0:
                        # Some tests failed - good! They caught the mutation
                        tests_failed = self._parse_test_failures(result.stdout + result.stderr)
                    else:
                        # Tests passed - bad! They missed the mutation
                        tests_passed = self._parse_test_names(test_file)
                    
                    # Calculate effectiveness with safety check
                    total_tests = len(tests_failed) + len(tests_passed)
                    effectiveness = len(tests_failed) / max(total_tests, 1) if total_tests > 0 else 0.0
                    
                    return MutationResult(
                        mutation_type=mutation['type'],
                        original_code=mutation['original'],
                        mutated_code=mutation['mutated'],
                        tests_failed=tests_failed,
                        tests_passed=tests_passed,
                        file_path=source_file,
                        line_number=line_idx + 1,
                        effectiveness_score=effectiveness
                    )
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error(f"File mutation failed for {source_file}: {e}")
                return None
                
        except (TypeError, ValueError, AttributeError) as e:
            logger.error(f"Mutation testing failed for {test_file}: {e}", exc_info=True)
            return None
            
        finally:
            # Cleanup temp file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except (OSError, IOError) as cleanup_error:
                    logger.warning(f"Could not cleanup temp file {temp_path}: {cleanup_error}")
    
    def _parse_test_failures(self, output: str) -> List[str]:
        """Parse test names from pytest failure output."""
        failed_tests = []
        for line in output.split('\n'):
            if 'FAILED' in line or 'ERROR' in line:
                # Extract test name from pytest output
                match = re.search(r'(test_\w+)', line)
                if match:
                    failed_tests.append(match.group(1))
        return failed_tests
    
    def _parse_test_names(self, test_file: Path) -> List[str]:
        """Extract all test function names from a test file."""
        try:
            content = test_file.read_text(encoding='utf-8')
            return re.findall(r'def (test_\w+)\(', content)
        except Exception:
            return []
    
    def _analyze_mutation_results(self, test_file: Path, source_file: Path, 
                                results: List[MutationResult]) -> TestEffectivenessReport:
        """Analyze mutation testing results to create effectiveness report."""
        if not results:
            return self._create_empty_report(test_file, "No mutation results")
            
        mutations_caught = sum(1 for r in results if r.tests_failed)
        mutations_missed = sum(1 for r in results if not r.tests_failed)
        
        effectiveness = (mutations_caught / len(results)) * 100 if results else 0
        
        # Identify weak areas (mutations that weren't caught)
        weak_areas = []
        strong_areas = []
        
        for result in results:
            if not result.tests_failed:
                weak_areas.append(f"Line {result.line_number}: {result.mutation_type.value}")
            else:
                strong_areas.append(f"Line {result.line_number}: Caught by {len(result.tests_failed)} tests")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, effectiveness)
        
        return TestEffectivenessReport(
            test_file=test_file,
            source_file=source_file,
            mutations_caught=mutations_caught,
            mutations_missed=mutations_missed,
            effectiveness_percentage=effectiveness,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, results: List[MutationResult], effectiveness: float) -> List[str]:
        """Generate actionable recommendations based on mutation results."""
        recommendations = []
        
        if effectiveness < 50:
            recommendations.append("🚨 CRITICAL: Less than 50% of mutations caught - major gaps in test coverage")
        elif effectiveness < 70:
            recommendations.append("⚠️  WARNING: Less than 70% of mutations caught - some important bugs may slip through")
        elif effectiveness < 90:
            recommendations.append("✓ GOOD: Most mutations caught, but room for improvement")
        else:
            recommendations.append("🎯 EXCELLENT: High mutation detection rate")
            
        # Specific recommendations based on missed mutation types
        missed_types = [r.mutation_type for r in results if not r.tests_failed]
        
        if MutationType.OFF_BY_ONE in missed_types:
            recommendations.append("Add boundary value testing (test with 0, 1, -1, max values)")
            
        if MutationType.BOOLEAN_FLIP in missed_types:
            recommendations.append("Add tests for both true and false conditions in conditional logic")
            
        if MutationType.CONDITION_FLIP in missed_types:
            recommendations.append("Test both AND and OR branches of complex conditions")
            
        if MutationType.BOUNDARY_SHIFT in missed_types:
            recommendations.append("Add edge case testing for numeric boundaries and empty collections")
            
        return recommendations
    
    def _create_empty_report(self, test_file: Path, reason: str) -> TestEffectivenessReport:
        """Create an empty report when mutation testing isn't possible."""
        return TestEffectivenessReport(
            test_file=test_file,
            source_file=Path("unknown"),
            mutations_caught=0,
            mutations_missed=0,
            effectiveness_percentage=0.0,
            weak_areas=[],
            strong_areas=[],
            recommendations=[f"Cannot analyze: {reason}"]
        )


class EffectivenessValidator:
    """Validates test effectiveness using mutation testing and real-world patterns."""
    
    def __init__(self, 
                 project_root: Path, 
                 config_manager: Optional[ConfigManagerProtocol] = None, 
                 performance_optimizer: Optional[PerformanceOptimizerProtocol] = None, 
                 mutation_tester: Optional['SimpleMutationTester'] = None) -> None:
        """Initialize effectiveness validator with dependency injection.
        
        Args:
            project_root: Root path of the project
            config_manager: Optional config manager (for dependency injection)
            performance_optimizer: Optional performance optimizer (for dependency injection) 
            mutation_tester: Optional mutation tester (for dependency injection)
        """
        self.project_root = project_root
        
        # Initialize configuration via dependency injection or default
        if config_manager is None:
            config_manager = ConfigManager(project_root)
        self.config = config_manager.get_config()
        
        # Initialize mutation tester via dependency injection or default
        if mutation_tester is None:
            self.mutation_tester = SimpleMutationTester(project_root, self.config)
        else:
            self.mutation_tester = mutation_tester
        
        # Initialize performance optimizer via dependency injection or lazy loading
        if performance_optimizer is not None:
            self.performance_optimizer = performance_optimizer
        elif getattr(self.config, 'enable_parallel_execution', False):
            self.performance_optimizer = self._create_performance_optimizer()
        else:
            self.performance_optimizer = None
    
    def _create_performance_optimizer(self) -> Optional[PerformanceOptimizerProtocol]:
        """Create performance optimizer with lazy loading to avoid circular imports."""
        try:
            # Import here to avoid circular imports
            from .performance_optimizer import PerformanceOptimizer
            optimizer = PerformanceOptimizer(
                self.project_root, 
                self.config.to_dict() if hasattr(self.config, 'to_dict') else {}
            )
            logger.info("Performance optimization enabled")
            return optimizer
        except ImportError as e:
            logger.warning(f"Performance optimizer not available: {e}")
            return None
        except Exception as e:
            logger.warning(f"Performance optimizer initialization failed: {e}")
            return None
        
    def validate_test_effectiveness(self, test_file: Path) -> Dict[str, any]:
        """Comprehensive effectiveness validation that answers: 'Would this catch real bugs?'"""
        results = {
            'test_file': test_file.name,
            'mutation_effectiveness': 0.0,
            'real_bug_patterns': [],
            'integration_quality': 0.0,
            'overall_effectiveness': 0.0,
            'actionable_recommendations': [],
            'analysis_errors': []
        }
        
        # Validate input
        if not test_file.exists():
            error_msg = f"Test file not found: {test_file}"
            logger.error(error_msg)
            results['analysis_errors'].append(error_msg)
            results['actionable_recommendations'] = ["Cannot analyze: test file not found"]
            return results
        
        try:
            # 1. Mutation testing (most important)
            try:
                mutation_report = self.mutation_tester.analyze_test_effectiveness(test_file)
                results['mutation_effectiveness'] = mutation_report.effectiveness_percentage
                results['actionable_recommendations'].extend(mutation_report.recommendations)
            except Exception as e:
                error_msg = f"Mutation testing failed: {e}"
                logger.warning(error_msg)
                results['analysis_errors'].append(error_msg)
                results['mutation_effectiveness'] = 0.0
            
            # 2. Real bug pattern analysis
            try:
                bug_patterns = self._analyze_real_bug_patterns(test_file)
                results['real_bug_patterns'] = bug_patterns
            except Exception as e:
                error_msg = f"Bug pattern analysis failed: {e}"
                logger.warning(error_msg)
                results['analysis_errors'].append(error_msg)
                results['real_bug_patterns'] = []
            
            # 3. Integration quality
            try:
                integration_score = self._analyze_integration_quality(test_file)
                results['integration_quality'] = integration_score
            except Exception as e:
                error_msg = f"Integration analysis failed: {e}"
                logger.warning(error_msg)
                results['analysis_errors'].append(error_msg)
                results['integration_quality'] = 0.0
            
            # 4. Calculate overall effectiveness with safety checks
            try:
                mutation_score = max(0, min(100, results['mutation_effectiveness']))
                pattern_score = max(0, min(100, len(results['real_bug_patterns']) * 10))
                integration_score = max(0, min(100, results['integration_quality']))
                
                results['overall_effectiveness'] = (
                    mutation_score * 0.6 +      # Mutation testing is most important
                    pattern_score * 0.3 +       # Real bug patterns
                    integration_score * 0.1     # Integration quality
                )
                
                # Cap at 100
                results['overall_effectiveness'] = min(100, results['overall_effectiveness'])
                
            except Exception as e:
                error_msg = f"Effectiveness calculation failed: {e}"
                logger.warning(error_msg)
                results['analysis_errors'].append(error_msg)
                results['overall_effectiveness'] = 0.0
            
            # 5. Generate final recommendations
            try:
                if results['overall_effectiveness'] < 50:
                    results['actionable_recommendations'].insert(0, 
                        "🚨 CRITICAL: This test would miss most real bugs - needs major improvement")
                elif results['overall_effectiveness'] < 70:
                    results['actionable_recommendations'].insert(0,
                        "⚠️  WARNING: This test has significant gaps - some bugs will slip through")
                else:
                    results['actionable_recommendations'].insert(0,
                        "✓ EFFECTIVE: This test would catch most real bugs")
                        
                # Add error summary if there were issues
                if results['analysis_errors']:
                    results['actionable_recommendations'].append(
                        f"ℹ️  Note: {len(results['analysis_errors'])} analysis components had errors"
                    )
            except Exception as e:
                logger.warning(f"Recommendation generation failed: {e}")
                results['actionable_recommendations'] = ["Analysis partially failed - review errors"]
                    
        except Exception as e:
            error_msg = f"Effectiveness validation failed for {test_file}: {e}"
            logger.error(error_msg, exc_info=True)
            results['analysis_errors'].append(error_msg)
            results['actionable_recommendations'] = [f"Analysis failed: {str(e)[:100]}..."]
            
        return results
    
    def _analyze_real_bug_patterns(self, test_file: Path) -> List[str]:
        """Analyze if tests check for common real-world bug patterns."""
        try:
            content = test_file.read_text(encoding='utf-8')
        except Exception:
            return []
            
        patterns_found = []
        
        # Check for common bug patterns that tests should catch
        real_world_patterns = [
            (r'assert.*== 0|assert.*len.*== 0', "Empty collection handling"),
            (r'assert.*is None|assert.*== None', "Null value handling"),
            (r'except.*Exception|pytest\.raises', "Error condition testing"),
            (r'assert.*!=.*before|assert.*changed', "State change validation"),
            (r'mock.*side_effect.*Exception', "Error simulation testing"),
            (r'assert.*startswith|assert.*endswith', "String boundary testing"),
            (r'assert.*>.*0|assert.*<.*len', "Numeric boundary testing"),
            (r'timeout|sleep.*mock', "Timeout/timing issue testing"),
        ]
        
        for pattern, description in real_world_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                patterns_found.append(description)
                
        return patterns_found
    
    def _analyze_integration_quality(self, test_file: Path) -> float:
        """Analyze how well tests validate real component integration."""
        try:
            content = test_file.read_text(encoding='utf-8')
        except Exception:
            return 0.0
            
        integration_indicators = 0
        total_possible = 6
        
        # Real integration patterns
        if re.search(r'database.*api|api.*database', content, re.IGNORECASE):
            integration_indicators += 1
            
        if re.search(r'with.*get_connection|with.*session', content):
            integration_indicators += 1
            
        if re.search(r'assert.*status_code.*200', content):
            integration_indicators += 1
            
        if re.search(r'requests\.|http|api', content, re.IGNORECASE):
            integration_indicators += 1
            
        if re.search(r'end_to_end|e2e|integration', str(test_file)):
            integration_indicators += 1
            
        if re.search(r'subprocess|external|service', content, re.IGNORECASE):
            integration_indicators += 1
            
        return (integration_indicators / total_possible) * 100
    
    def validate_multiple_files(self, test_files: List[Path]) -> List[Tuple[Path, Dict]]:
        """Validate effectiveness for multiple test files with performance optimization."""
        if not test_files:
            return []
        
        results = []
        
        # Use performance optimization if available
        if self.performance_optimizer:
            def analysis_func(file_path: Path, config: Dict) -> Dict:
                return self.validate_test_effectiveness(file_path)
            
            optimized_results = self.performance_optimizer.optimize_analysis(
                analysis_func,
                test_files,
                enable_parallel=True,
                enable_caching=True,
                enable_scheduling=True
            )
            return optimized_results
        else:
            # Sequential processing
            for test_file in test_files:
                try:
                    result = self.validate_test_effectiveness(test_file)
                    results.append((test_file, result))
                except Exception as e:
                    logger.error(f"Validation failed for {test_file}: {e}")
                    error_result = {
                        'test_file': test_file.name,
                        'analysis_errors': [str(e)],
                        'actionable_recommendations': [f"Analysis failed: {e}"]
                    }
                    results.append((test_file, error_result))
            
            return results
    
    def get_performance_report(self) -> Dict:
        """Get performance report from optimizer if available."""
        if self.performance_optimizer:
            return self.performance_optimizer.get_performance_report()
        else:
            return {"message": "Performance optimization not enabled"}
    
    def clear_cache(self) -> None:
        """Clear analysis cache if available."""
        if self.performance_optimizer:
            self.performance_optimizer.clear_cache()
            logger.info("Analysis cache cleared")
        else:
            logger.info("No cache to clear (performance optimization not enabled)")