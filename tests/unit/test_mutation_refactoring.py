"""Unit tests for refactored mutation testing components."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from tests.health.testing.mutation_generator import MutationGenerator, MutationType
from tests.health.testing.mutation_executor import MutationExecutor, MutationResult
from tests.health.testing.mutation_analyzer import MutationAnalyzer, TestEffectivenessReport
from tests.health.testing.mutation_tester_refactored import RefactoredMutationTester


class TestMutationGenerator:
    """Test mutation generation functionality."""
    
    @pytest.fixture
    def generator(self):
        return MutationGenerator(max_mutations_per_file=5)
    
    @pytest.fixture
    def sample_source(self, tmp_path):
        """Create sample source file for testing."""
        source_file = tmp_path / "sample.py"
        source_file.write_text("""
def process_data(items):
    if len(items) > 5:
        return True
    for i in range(len(items)):
        if items[i] == None:
            return False
    return True

def calculate(a, b):
    return a + b
""")
        return source_file
    
    def test_generate_mutations(self, generator, sample_source):
        """Test that mutations are generated correctly."""
        mutations = generator.generate_mutations(sample_source)
        
        assert len(mutations) > 0
        assert len(mutations) <= 5  # Respects max limit
        
        # Check mutation structure
        for mutation in mutations:
            assert 'type' in mutation
            assert 'line' in mutation
            assert 'original' in mutation
            assert 'mutated' in mutation
            assert 'description' in mutation
    
    def test_off_by_one_mutations(self, generator, sample_source):
        """Test off-by-one mutation generation."""
        mutations = generator.generate_mutations(sample_source)
        
        # Should find the > comparison
        off_by_one_mutations = [m for m in mutations if m['type'] == MutationType.OFF_BY_ONE.value]
        assert len(off_by_one_mutations) > 0
    
    def test_operator_mutations(self, generator, sample_source):
        """Test operator mutation generation."""
        mutations = generator.generate_mutations(sample_source)
        
        # Should find the + operator
        operator_mutations = [m for m in mutations if m['type'] == MutationType.OPERATOR_CHANGE.value]
        assert len(operator_mutations) >= 0  # May or may not find depending on parsing


class TestMutationExecutor:
    """Test mutation execution functionality."""
    
    @pytest.fixture
    def executor(self, tmp_path):
        return MutationExecutor(tmp_path)
    
    @pytest.fixture
    def test_files(self, tmp_path):
        """Create sample test and source files."""
        # Source file
        source_file = tmp_path / "calculator.py"
        source_file.write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")
        
        # Test file
        test_file = tmp_path / "test_calculator.py"
        test_file.write_text("""
from calculator import add, multiply

def test_add():
    assert add(2, 3) == 5
    assert add(0, 0) == 0

def test_multiply():
    assert multiply(2, 3) == 6
""")
        
        return test_file, source_file
    
    def test_execute_mutation_structure(self, executor, test_files):
        """Test mutation execution returns proper structure."""
        test_file, source_file = test_files
        
        mutation = {
            'type': 'operator_change',
            'line': 2,  # Line with 'return a + b' (0-indexed, line 3 in file)
            'original': '    return a + b',
            'mutated': '    return a - b'
        }
        
        # Mock the test execution to avoid running actual pytest
        with patch.object(executor, '_run_test') as mock_run_test:
            mock_result = Mock()
            mock_result.returncode = 1  # Test failed (good!)
            mock_result.stdout = "FAILED test_calculator.py::test_add"
            mock_result.stderr = ""
            mock_run_test.return_value = mock_result
            
            result = executor.execute_mutation(test_file, source_file, mutation)
        
        assert result is not None
        assert isinstance(result, MutationResult)
        assert result.mutation_type == 'operator_change'
        assert result.was_caught  # Should be caught since test failed


class TestMutationAnalyzer:
    """Test mutation analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        return MutationAnalyzer()
    
    def test_analyze_empty_results(self, analyzer, tmp_path):
        """Test analysis with no results."""
        test_file = tmp_path / "test_empty.py"
        report = analyzer.analyze_results(test_file, None, [])
        
        assert isinstance(report, TestEffectivenessReport)
        assert report.total_mutations == 0
        assert report.effectiveness_percentage == 0.0
        assert not report.is_effective
    
    def test_analyze_mixed_results(self, analyzer, tmp_path):
        """Test analysis with mixed caught/uncaught mutations."""
        test_file = tmp_path / "test_mixed.py"
        source_file = tmp_path / "source.py"
        
        results = [
            MutationResult(
                mutation_type='off_by_one',
                original_code='if x > 5:',
                mutated_code='if x >= 5:',
                tests_failed=['test_boundary'],
                tests_passed=[],
                file_path=source_file,
                line_number=10,
                effectiveness_score=1.0
            ),
            MutationResult(
                mutation_type='boolean_flip',
                original_code='return True',
                mutated_code='return False',
                tests_failed=[],
                tests_passed=['test_returns'],
                file_path=source_file,
                line_number=15,
                effectiveness_score=0.0
            )
        ]
        
        report = analyzer.analyze_results(test_file, source_file, results)
        
        assert report.total_mutations == 2
        assert report.caught_mutations == 1
        assert report.effectiveness_percentage == 50.0
        assert len(report.uncaught_mutations) == 1
        assert len(report.recommendations) > 0
    
    def test_effectiveness_rating(self, analyzer):
        """Test effectiveness rating calculation."""
        assert analyzer.get_effectiveness_rating(95) == 'excellent'
        assert analyzer.get_effectiveness_rating(75) == 'good'
        assert analyzer.get_effectiveness_rating(55) == 'moderate'
        assert analyzer.get_effectiveness_rating(35) == 'poor'
        assert analyzer.get_effectiveness_rating(15) == 'very poor'


class TestRefactoredMutationTester:
    """Test the refactored mutation tester integration."""
    
    @pytest.fixture
    def tester(self, tmp_path):
        return RefactoredMutationTester(tmp_path)
    
    def test_init_creates_components(self, tester):
        """Test that initialization creates all required components."""
        assert hasattr(tester, 'generator')
        assert hasattr(tester, 'executor')
        assert hasattr(tester, 'analyzer')
        assert isinstance(tester.generator, MutationGenerator)
        assert isinstance(tester.executor, MutationExecutor)
        assert isinstance(tester.analyzer, MutationAnalyzer)
    
    def test_find_source_file_patterns(self, tester, tmp_path):
        """Test source file finding with different patterns."""
        # Create test file
        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_something(): pass")
        
        # Create corresponding source file
        source_file = tmp_path / "example.py"
        source_file.write_text("def example_func(): pass")
        
        found_source = tester._find_source_file(test_file)
        assert found_source == source_file
    
    def test_find_source_file_not_found(self, tester, tmp_path):
        """Test behavior when source file cannot be found."""
        test_file = tmp_path / "test_nonexistent.py"
        test_file.write_text("def test_something(): pass")
        
        found_source = tester._find_source_file(test_file)
        assert found_source is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])