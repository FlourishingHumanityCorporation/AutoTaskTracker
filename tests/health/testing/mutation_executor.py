"""Mutation execution module - handles running tests with mutations.

This module is responsible for applying mutations and running tests.
"""

import logging
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

from .shared_utilities import temporary_file_mutation
from .config import EffectivenessConfig

logger = logging.getLogger(__name__)


@dataclass
class MutationResult:
    """Result of testing a single mutation."""
    mutation_type: str
    original_code: str
    mutated_code: str
    tests_failed: List[str]
    tests_passed: List[str]
    file_path: Path
    line_number: int
    effectiveness_score: float
    
    @property
    def was_caught(self) -> bool:
        """Check if the mutation was caught by any test."""
        return len(self.tests_failed) > 0


class MutationExecutor:
    """Executes mutations and runs tests to measure effectiveness."""
    
    def __init__(self, project_root: Path, config: Optional[EffectivenessConfig] = None):
        self.project_root = project_root
        self.config = config or EffectivenessConfig()
        
    def execute_mutation(self, test_file: Path, source_file: Path, mutation: Dict) -> Optional[MutationResult]:
        """Execute a single mutation and run tests.
        
        Args:
            test_file: Path to the test file to run
            source_file: Path to the source file to mutate
            mutation: Mutation dictionary with keys: type, line, original, mutated
            
        Returns:
            MutationResult if successful, None if failed
        """
        try:
            # Read original content
            original_content = source_file.read_text(encoding='utf-8')
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
            
            # Use the robust temporary_file_mutation context manager
            try:
                with temporary_file_mutation(source_file, mutated_content):
                    # Run the specific test file
                    result = self._run_test(test_file)
                    
                    if result is None:
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
            logger.error(f"Mutation execution failed: {e}", exc_info=True)
            return None
    
    def _run_test(self, test_file: Path) -> Optional[subprocess.CompletedProcess]:
        """Run pytest on a specific test file.
        
        Args:
            test_file: Path to the test file
            
        Returns:
            CompletedProcess result or None if failed
        """
        try:
            timeout = self.config.mutation.timeout_seconds
            logger.info(f"Running pytest on {test_file}")
            
            result = subprocess.run([
                'python', '-m', 'pytest', str(test_file), '-v', '--tb=no', '-q'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=timeout)
            
            logger.info(f"Test result: return code={result.returncode}")
            return result
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Test execution timeout ({timeout}s) for {test_file}")
            return None
        except FileNotFoundError:
            logger.warning("pytest not found - cannot run mutation tests")
            return None
        except OSError as e:
            logger.error(f"Failed to run test: {e}")
            return None
    
    def _parse_test_failures(self, output: str) -> List[str]:
        """Parse test failure information from pytest output."""
        failed_tests = []
        
        # Look for FAILED test names in pytest output
        lines = output.split('\n')
        for line in lines:
            # Pattern: FAILED tests/test_file.py::TestClass::test_method
            if 'FAILED' in line:
                match = re.search(r'FAILED.*::(test_\w+)', line)
                if match:
                    failed_tests.append(match.group(1))
        
        return failed_tests
    
    def _parse_test_names(self, test_file: Path) -> List[str]:
        """Extract all test function names from a test file."""
        try:
            content = test_file.read_text(encoding='utf-8')
            return re.findall(r'def (test_\w+)\(', content)
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Could not read test file {test_file}: {e}")
            return []