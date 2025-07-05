"""Unit tests for simple intelligence validation system.

This module tests the SimpleTestAnalyzer and FocusedTestValidator to ensure
they properly identify test quality issues and provide actionable feedback.
"""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from tests.health.testing.simple_intelligence import (
    SimpleTestAnalyzer,
    FocusedTestValidator,
    TestPurpose,
    ActionableInsight
)


class TestSimpleTestAnalyzer:
    """Test suite for SimpleTestAnalyzer."""
    
    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with temporary directory."""
        return SimpleTestAnalyzer(tmp_path)
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create a temporary test file."""
        test_file = tmp_path / "tests" / "test_example.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        return test_file
    
    def test_init_creates_config(self, tmp_path):
        """Test that __init__ properly initializes config attribute."""
        analyzer = SimpleTestAnalyzer(tmp_path)
        assert hasattr(analyzer, 'config')
        assert hasattr(analyzer.config, 'analysis')
        assert analyzer.project_root == tmp_path
        assert analyzer.test_dir == tmp_path / "tests"
    
    def test_analyze_unreadable_file(self, analyzer, test_file):
        """Test handling of unreadable files."""
        # Create file with no read permissions
        test_file.touch(mode=0o000)
        
        insights = analyzer.analyze_test_file(test_file)
        
        assert len(insights) == 1
        assert insights[0].issue == "Cannot read test file"
        assert insights[0].impact == "high"
        assert insights[0].action == "Fix file encoding or permissions"
    
    def test_detect_trivial_assertions(self, analyzer, test_file):
        """Test detection of trivial assertions that can't fail."""
        test_file.write_text("""
def test_trivial():
    assert True
    assert 1 == 1
    assert "test" == "test"
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        trivial_insights = [i for i in insights if "Trivial assertions" in i.issue]
        assert len(trivial_insights) == 1
        assert trivial_insights[0].impact == "high"
        assert "test actual behavior" in trivial_insights[0].action
    
    def test_detect_missing_assertions(self, analyzer, test_file):
        """Test detection of tests without assertions."""
        test_file.write_text("""def test_no_assertion():
    result = some_function()
    # No assertion here
    
def test_with_assertion():
    result = some_function()
    assert result == expected
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        no_assert_insights = [i for i in insights if "no assertions" in i.issue]
        assert len(no_assert_insights) == 1
        assert "test_no_assertion" in no_assert_insights[0].issue
        assert no_assert_insights[0].impact == "high"
    
    def test_detect_long_test_functions(self, analyzer, test_file):
        """Test detection of overly long test functions."""
        long_function = "\n".join([f"    line{i} = {i}" for i in range(50)])
        test_file.write_text(f"""def test_too_long():
{long_function}
    assert True
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        long_insights = [i for i in insights if "too long" in i.issue]
        assert len(long_insights) == 1
        assert "test_too_long" in long_insights[0].issue
        assert long_insights[0].impact == "medium"
        assert "Split into smaller" in long_insights[0].action
    
    def test_detect_mock_only_testing(self, analyzer, test_file):
        """Test detection of tests that only validate mocks."""
        test_file.write_text("""
def test_mock_only():
    mock_service = Mock()
    process(mock_service)
    mock_service.assert_called_once()
    assert mock_service.call_count == 1
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        mock_insights = [i for i in insights if "only validate that mocks" in i.issue]
        assert len(mock_insights) == 1
        assert mock_insights[0].impact == "high"
        assert "actual business logic" in mock_insights[0].action
    
    def test_detect_missing_error_testing(self, analyzer, test_file):
        """Test detection of missing error condition testing."""
        test_file.write_text("""
def test_database_operation():
    db = get_database_connection()
    result = db.query("SELECT * FROM users")
    assert len(result) > 0
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        error_insights = [i for i in insights if "error conditions" in i.issue]
        assert len(error_insights) == 1
        assert error_insights[0].impact == "high"
        assert "pytest.raises" in error_insights[0].action
    
    def test_detect_missing_boundary_testing(self, analyzer, test_file):
        """Test detection of missing boundary value testing."""
        test_file.write_text("""
def test_numeric_operation():
    for i in range(10, 20):
        result = process(i)
        assert result > 5
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        boundary_insights = [i for i in insights if "boundary values" in i.issue]
        assert len(boundary_insights) == 1
        assert boundary_insights[0].impact == "medium"
        assert "0, 1, -1" in boundary_insights[0].action
    
    def test_detect_hardcoded_test_data(self, analyzer, test_file):
        """Test detection of excessive hardcoded test data."""
        test_file.write_text("""
def test_hardcoded():
    user1 = "test_user_123"
    user2 = "test_user_456"
    password = "password123"
    url = "http://localhost:8080"
    token = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        hardcoded_insights = [i for i in insights if "hardcoded test data" in i.issue]
        assert len(hardcoded_insights) == 1
        assert hardcoded_insights[0].impact == "medium"
        assert "fixtures or factories" in hardcoded_insights[0].action
    
    def test_detect_test_interdependencies(self, analyzer, test_file):
        """Test detection of potential test interdependencies."""
        test_file.write_text("""
global_state = {}

class TestSuite:
    shared_data = None
    
    def test_modifies_state(self):
        global global_state
        global_state['key'] = 'value'
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        dependency_insights = [i for i in insights if "share state" in i.issue]
        assert len(dependency_insights) == 1
        assert dependency_insights[0].impact == "medium"
        assert "fixtures" in dependency_insights[0].action
    
    def test_detect_missing_docstrings(self, analyzer, test_file):
        """Test detection of missing docstrings on complex tests."""
        complex_function = "\n".join([f"    step{i}()" for i in range(15)])
        test_file.write_text(f"""
def test_complex_workflow():
{complex_function}
    assert result == expected
""")
        
        insights = analyzer.analyze_test_file(test_file)
        
        doc_insights = [i for i in insights if "lacks documentation" in i.issue]
        assert len(doc_insights) == 1
        assert doc_insights[0].impact == "low"
        assert "Add docstring" in doc_insights[0].action
    
    def test_extract_function_content(self, analyzer):
        """Test function content extraction."""
        content = """def test_example():
    # This is the function body
    x = 1
    y = 2
    assert x + y == 3

def test_another():
    pass
"""
        
        func_content = analyzer._extract_function_content(content, "test_example")
        
        assert "# This is the function body" in func_content
        assert "x = 1" in func_content
        assert "assert x + y == 3" in func_content
        assert "def test_another" not in func_content
    
    def test_get_file_purpose(self, analyzer, tmp_path):
        """Test file purpose detection based on path."""
        # Unit test
        unit_file = tmp_path / "tests" / "test_module.py"
        assert analyzer.get_file_purpose(unit_file) == TestPurpose.UNIT
        
        # Integration test
        integration_file = tmp_path / "tests" / "integration" / "test_api.py"
        assert analyzer.get_file_purpose(integration_file) == TestPurpose.INTEGRATION
        
        # E2E test
        e2e_file = tmp_path / "tests" / "e2e" / "test_workflow.py"
        assert analyzer.get_file_purpose(e2e_file) == TestPurpose.E2E
        
        # Infrastructure test
        health_file = tmp_path / "tests" / "health" / "test_system.py"
        assert analyzer.get_file_purpose(health_file) == TestPurpose.INFRASTRUCTURE
    
    def test_get_priority_insights(self, analyzer):
        """Test insight prioritization."""
        insights = [
            ActionableInsight("Low priority", "low", "Do this later"),
            ActionableInsight("High priority 1", "high", "Fix immediately"),
            ActionableInsight("Medium priority", "medium", "Fix soon"),
            ActionableInsight("High priority 2", "high", "Fix right now with detailed steps"),
        ]
        
        prioritized = analyzer.get_priority_insights(insights)
        
        assert prioritized[0].impact == "high"
        assert prioritized[1].impact == "high"
        assert prioritized[2].impact == "medium"
        assert prioritized[3].impact == "low"
        # Among high priority, shorter action comes first (more specific)
        assert len(prioritized[0].action) < len(prioritized[1].action)


class TestFocusedTestValidator:
    """Test suite for FocusedTestValidator."""
    
    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        return FocusedTestValidator(tmp_path)
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create a temporary test file."""
        test_file = tmp_path / "tests" / "test_example.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        return test_file
    
    def test_validate_good_test_file(self, validator, test_file):
        """Test validation of a well-written test file."""
        test_file.write_text("""
def test_user_creation():
    \"\"\"Test that users can be created with valid data.\"\"\"
    user = create_user("testuser", "test@example.com")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    
    with pytest.raises(ValueError):
        create_user("", "invalid-email")
""")
        
        result = validator.validate_test_file(test_file)
        
        assert result['effectiveness'] == "good"
        assert result['total_issues'] == 0
        assert len(result['high_priority_actions']) == 0
        assert result['next_steps'][0].startswith("✓")
    
    def test_validate_poor_test_file(self, validator, test_file):
        """Test validation of a poorly written test file."""
        test_file.write_text("""def test_bad():
    assert True
    
def test_worse():
    x = 1
    # No assertion
    
def test_terrible():
    assert 1 == 1
    assert "test" == "test"
""")
        
        result = validator.validate_test_file(test_file)
        
        # Should have high impact issues from trivial assertions and missing assertion
        assert result['effectiveness'] in ["poor", "moderate"]
        assert result['total_issues'] >= 2
        assert len(result['high_priority_actions']) >= 2
        assert not result['next_steps'][0].startswith("✓")
    
    def test_validate_moderate_test_file(self, validator, test_file):
        """Test validation of a moderately good test file."""
        test_file.write_text("""
def test_process():
    result = process_data([1, 2, 3])
    assert result == 6
    
def test_empty():
    assert True  # TODO: implement this test
""")
        
        result = validator.validate_test_file(test_file)
        
        assert result['effectiveness'] == "moderate"
        assert result['total_issues'] >= 1
        assert len(result['high_priority_actions']) >= 1
    
    def test_generate_next_steps(self, validator, test_file):
        """Test next steps generation."""
        # Create file with multiple issues
        test_file.write_text("""
def test_multiple_issues():
    assert True
    mock = Mock()
    mock.assert_called()
""")
        
        result = validator.validate_test_file(test_file)
        
        assert len(result['next_steps']) > 0
        assert all(isinstance(step, str) for step in result['next_steps'])
        # Steps should be numbered
        assert result['next_steps'][0].startswith("1.")
    
    def test_detailed_insights_format(self, validator, test_file):
        """Test format of detailed insights."""
        test_file.write_text("""
def test_with_issues():
    assert True
""")
        
        result = validator.validate_test_file(test_file)
        
        assert 'detailed_insights' in result
        for insight in result['detailed_insights']:
            assert 'issue' in insight
            assert 'impact' in insight
            assert 'action' in insight
            assert 'example' in insight  # May be None


class TestEffectivenessConfig:
    """Test configuration handling."""
    
    def test_config_fallback(self):
        """Test that config fallback works when import fails."""
        # This is already tested by successful import above
        from tests.health.testing.simple_intelligence import EffectivenessConfig
        
        config = EffectivenessConfig()
        assert hasattr(config, 'analysis')
        assert config.analysis.max_function_lines == 30
        assert config.analysis.max_hardcoded_items == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])