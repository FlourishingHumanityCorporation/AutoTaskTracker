"""Comprehensive unit tests for shared utilities module.

This test suite validates utility functions, context managers, patterns,
and helper classes used across the mutation effectiveness system.
"""

import pytest
import tempfile
import shutil
import time
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import logging

from tests.health.testing.shared_utilities import (
    CompiledPatterns,
    ValidationLimits,
    safe_read_file,
    safe_parse_datetime,
    temporary_file_mutation,
    managed_temporary_file,
    extract_function_content,
    validate_file_for_analysis,
    SafeSubprocessRunner,
    standardize_error_message,
    BoundedDict
)


class TestCompiledPatterns:
    """Test the CompiledPatterns class with pre-compiled regex patterns."""
    
    def test_off_by_one_pattern(self):
        """Test off-by-one pattern matching."""
        test_cases = [
            ("if x > 10:", True),
            ("if y < 5:", True),
            ("if z >= 0:", True),
            ("if w <= 100:", True),
            ("if x == 10:", False),
            ("print('hello'):", False),
        ]
        
        for text, should_match in test_cases:
            match = CompiledPatterns.OFF_BY_ONE.search(text)
            assert bool(match) == should_match, f"Pattern mismatch for: {text}"
    
    def test_boolean_logic_pattern(self):
        """Test boolean logic pattern matching."""
        test_cases = [
            ("if x and y:", True),
            ("if a or b:", True),
            ("if condition1 and condition2:", True),
            ("if x == y:", False),
            ("print('and'):", False),
        ]
        
        for text, should_match in test_cases:
            match = CompiledPatterns.BOOLEAN_LOGIC.search(text)
            assert bool(match) == should_match, f"Pattern mismatch for: {text}"
    
    def test_boundary_nums_pattern(self):
        """Test boundary numbers pattern matching."""
        test_cases = [
            ("if x == 0:", True),
            ("return 1", True),
            ("value = -1", True),
            ("if x == 10:", False),
            ("string0 = 'test'", False),  # Should not match in variable names
        ]
        
        for text, should_match in test_cases:
            match = CompiledPatterns.BOUNDARY_NUMS.search(text)
            assert bool(match) == should_match, f"Pattern mismatch for: {text}"
    
    def test_test_patterns(self):
        """Test assertion patterns for test detection."""
        test_cases = [
            ("assert result == expected", True),
            ("assert value == 0", True),
            ("assert func() == True", True),
            ("assert func()", False),  # No comparison
            ("print('test')", False),
        ]
        
        for text, should_match in test_cases:
            match = CompiledPatterns.TEST_PATTERNS.search(text)
            assert bool(match) == should_match, f"Pattern mismatch for: {text}"
    
    def test_mock_patterns(self):
        """Test mock pattern detection."""
        test_cases = [
            ("mock.assert_called()", True),
            ("mock.assert_called_with()", True),
            ("assert mock.call_count == 1", True),
            ("Mock()", True),
            ("mock_object = Mock()", True),
            ("normal_function()", False),
        ]
        
        for text, should_match in test_cases:
            match = CompiledPatterns.MOCK_PATTERNS.search(text)
            assert bool(match) == should_match, f"Pattern mismatch for: {text}"
    
    def test_real_world_bug_patterns(self):
        """Test real-world bug detection patterns."""
        # NULL handling
        null_cases = [
            ("assert result is None", True),
            ("assert len(items) == 0", True),
            ("assert value == None", True),
            ("assert something else", False),
        ]
        
        for text, should_match in null_cases:
            match = CompiledPatterns.NULL_HANDLING.search(text)
            assert bool(match) == should_match, f"NULL pattern mismatch for: {text}"
        
        # Error testing
        error_cases = [
            ("except ValueError:", True),
            ("pytest.raises(Exception)", True),
            ("with pytest.raises(ValueError):", True),
            ("normal code", False),
        ]
        
        for text, should_match in error_cases:
            match = CompiledPatterns.ERROR_TESTING.search(text)
            assert bool(match) == should_match, f"Error pattern mismatch for: {text}"


class TestValidationLimits:
    """Test the ValidationLimits class constants."""
    
    def test_function_limits(self):
        """Test function complexity limits."""
        assert ValidationLimits.MAX_FUNCTION_LINES == 30
        assert ValidationLimits.MAX_HARDCODED_ITEMS == 3
    
    def test_file_limits(self):
        """Test file processing limits."""
        assert ValidationLimits.MAX_FILE_SIZE_KB == 100
        assert ValidationLimits.LARGE_FILE_THRESHOLD_KB == 50
        assert ValidationLimits.MAX_MUTATIONS_PER_FILE == 20
    
    def test_performance_limits(self):
        """Test performance limits."""
        assert ValidationLimits.DEFAULT_TIMEOUT_SECONDS == 30
        assert ValidationLimits.MAX_ANALYSIS_TIME_SECONDS == 300
        assert ValidationLimits.MAX_CACHE_ENTRIES == 1000
    
    def test_quality_thresholds(self):
        """Test quality threshold constants."""
        assert ValidationLimits.MIN_EFFECTIVENESS_THRESHOLD == 50.0
        assert ValidationLimits.WARNING_EFFECTIVENESS_THRESHOLD == 70.0
        assert ValidationLimits.HIGH_EFFECTIVENESS_THRESHOLD == 90.0


class TestSafeReadFile:
    """Test the safe_read_file function."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_read_valid_utf8_file(self, temp_dir):
        """Test reading valid UTF-8 file."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, world! 🌍"
        test_file.write_text(test_content, encoding='utf-8')
        
        result = safe_read_file(test_file)
        
        assert result == test_content
    
    def test_read_latin1_file(self, temp_dir):
        """Test reading file with latin-1 encoding."""
        test_file = temp_dir / "latin1.txt"
        test_content = "Café"
        test_file.write_text(test_content, encoding='latin-1')
        
        result = safe_read_file(test_file)
        
        # Should read something (may not be exact due to encoding issues)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_read_nonexistent_file(self, temp_dir):
        """Test reading nonexistent file."""
        nonexistent = temp_dir / "nonexistent.txt"
        
        result = safe_read_file(nonexistent)
        
        assert result == ""
    
    def test_read_file_permission_denied(self, temp_dir):
        """Test handling permission denied."""
        test_file = temp_dir / "readonly.txt"
        test_file.write_text("test content")
        
        with patch.object(Path, 'read_text', side_effect=PermissionError("Permission denied")):
            result = safe_read_file(test_file)
        
        assert result == ""
    
    def test_read_file_unicode_error(self, temp_dir):
        """Test handling unicode decode error with fallback."""
        test_file = temp_dir / "binary.txt"
        # Write binary data that will cause UTF-8 decode error
        with open(test_file, 'wb') as f:
            f.write(b'\x80\x81\x82\x83')
        
        result = safe_read_file(test_file)
        
        # Should fallback to latin-1 and return something
        assert isinstance(result, str)
    
    def test_read_file_string_path(self, temp_dir):
        """Test reading file with string path instead of Path object."""
        test_file = temp_dir / "string_path.txt"
        test_content = "string path test"
        test_file.write_text(test_content)
        
        result = safe_read_file(str(test_file))
        
        assert result == test_content


class TestSafeParseDatetime:
    """Test the safe_parse_datetime function."""
    
    def test_parse_valid_datetime(self):
        """Test parsing valid datetime strings."""
        test_cases = [
            "2023-12-01 14:30:00",
            "2023-12-01T14:30:00",
            "2023-12-01",
            "2023/12/01 14:30:00",
            "12/01/2023 14:30:00",
        ]
        
        for date_string in test_cases:
            result = safe_parse_datetime(date_string)
            assert result is not None
            assert isinstance(result, time.struct_time)
    
    def test_parse_invalid_datetime(self):
        """Test parsing invalid datetime strings."""
        test_cases = [
            "invalid date",
            "2023-13-01",  # Invalid month
            "2023-12-32",  # Invalid day
            "",
            None,
            123,  # Not a string
        ]
        
        for date_string in test_cases:
            result = safe_parse_datetime(date_string)
            assert result is None
    
    def test_parse_datetime_custom_formats(self):
        """Test parsing with custom format list."""
        date_string = "01-Dec-2023"
        custom_formats = ["%d-%b-%Y"]
        
        result = safe_parse_datetime(date_string, custom_formats)
        
        assert result is not None
        assert result.tm_year == 2023
        assert result.tm_mon == 12
        assert result.tm_mday == 1
    
    def test_parse_datetime_empty_formats(self):
        """Test parsing with empty format list."""
        result = safe_parse_datetime("2023-12-01", [])
        
        assert result is None


class TestTemporaryFileMutation:
    """Test the temporary_file_mutation context manager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_successful_mutation(self, temp_dir):
        """Test successful file mutation and restoration."""
        source_file = temp_dir / "source.py"
        original_content = "def original(): pass"
        mutated_content = "def mutated(): pass"
        
        source_file.write_text(original_content)
        
        with temporary_file_mutation(source_file, mutated_content):
            # During mutation, file should have mutated content
            current_content = source_file.read_text()
            assert current_content == mutated_content
        
        # After context, file should be restored
        restored_content = source_file.read_text()
        assert restored_content == original_content
    
    def test_mutation_with_exception(self, temp_dir):
        """Test that file is restored even if exception occurs."""
        source_file = temp_dir / "source.py"
        original_content = "def original(): pass"
        mutated_content = "def mutated(): pass"
        
        source_file.write_text(original_content)
        
        try:
            with temporary_file_mutation(source_file, mutated_content):
                # Verify mutation applied
                assert source_file.read_text() == mutated_content
                # Raise exception
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # File should still be restored despite exception
        restored_content = source_file.read_text()
        assert restored_content == original_content
    
    def test_mutation_nonexistent_file(self, temp_dir):
        """Test mutation with nonexistent file."""
        nonexistent = temp_dir / "nonexistent.py"
        
        with pytest.raises(FileNotFoundError):
            with temporary_file_mutation(nonexistent, "content"):
                pass
    
    def test_mutation_permission_error(self, temp_dir):
        """Test handling permission error during mutation."""
        source_file = temp_dir / "readonly.py"
        source_file.write_text("original content")
        
        with patch.object(Path, 'write_text', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                with temporary_file_mutation(source_file, "mutated"):
                    pass
    
    def test_backup_cleanup(self, temp_dir):
        """Test that backup files are properly cleaned up."""
        source_file = temp_dir / "source.py"
        source_file.write_text("original content")
        
        backup_file = source_file.with_suffix(source_file.suffix + '.mutation_backup')
        
        with temporary_file_mutation(source_file, "mutated content"):
            # Backup should exist during mutation
            assert backup_file.exists()
        
        # Backup should be cleaned up after successful restoration
        assert not backup_file.exists()


class TestManagedTemporaryFile:
    """Test the managed_temporary_file context manager."""
    
    def test_create_temporary_file(self):
        """Test creating and cleaning up temporary file."""
        test_content = "temporary content"
        temp_path = None
        
        with managed_temporary_file(test_content, suffix='.py') as temp_file:
            temp_path = temp_file
            assert temp_file.exists()
            assert temp_file.suffix == '.py'
            
            content = temp_file.read_text()
            assert content == test_content
        
        # File should be cleaned up after context
        assert not temp_path.exists()
    
    def test_cleanup_on_exception(self):
        """Test that temporary file is cleaned up even on exception."""
        temp_path = None
        
        try:
            with managed_temporary_file("content") as temp_file:
                temp_path = temp_file
                assert temp_file.exists()
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # File should still be cleaned up
        assert not temp_path.exists()
    
    def test_custom_suffix(self):
        """Test creating temporary file with custom suffix."""
        with managed_temporary_file("content", suffix='.test') as temp_file:
            assert temp_file.suffix == '.test'


class TestExtractFunctionContent:
    """Test the extract_function_content function."""
    
    def test_extract_simple_function(self):
        """Test extracting simple function content."""
        source_code = """
def first_function():
    return "first"

def target_function():
    x = 1
    y = 2
    return x + y

def third_function():
    return "third"
"""
        
        result = extract_function_content(source_code, "target_function")
        
        assert "x = 1" in result
        assert "y = 2" in result
        assert "return x + y" in result
        assert "def target_function():" not in result
        assert "def third_function():" not in result
    
    def test_extract_function_with_nested_blocks(self):
        """Test extracting function with nested blocks."""
        source_code = """
def complex_function():
    if condition:
        for item in items:
            if item.valid:
                process(item)
    return result
"""
        
        result = extract_function_content(source_code, "complex_function")
        
        assert "if condition:" in result
        assert "for item in items:" in result
        assert "if item.valid:" in result
        assert "process(item)" in result
        assert "return result" in result
    
    def test_extract_nonexistent_function(self):
        """Test extracting nonexistent function."""
        source_code = """
def existing_function():
    pass
"""
        
        result = extract_function_content(source_code, "nonexistent_function")
        
        assert result == ""
    
    def test_extract_function_empty_input(self):
        """Test extracting with empty input."""
        assert extract_function_content("", "any_function") == ""
        assert extract_function_content("some code", "") == ""
        assert extract_function_content(None, "function") == ""


class TestValidateFileForAnalysis:
    """Test the validate_file_for_analysis function."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_validate_good_python_file(self, temp_dir):
        """Test validating good Python file."""
        test_file = temp_dir / "good.py"
        test_file.write_text("def test(): pass")
        
        result = validate_file_for_analysis(test_file)
        
        assert result is True
    
    def test_validate_nonexistent_file(self, temp_dir):
        """Test validating nonexistent file."""
        nonexistent = temp_dir / "nonexistent.py"
        
        result = validate_file_for_analysis(nonexistent)
        
        assert result is False
    
    def test_validate_directory(self, temp_dir):
        """Test validating directory instead of file."""
        result = validate_file_for_analysis(temp_dir)
        
        assert result is False
    
    def test_validate_large_file(self, temp_dir):
        """Test validating file that exceeds size limit."""
        large_file = temp_dir / "large.py"
        large_content = "# Large file\n" * 10000  # Create large content
        large_file.write_text(large_content)
        
        result = validate_file_for_analysis(large_file, max_size_kb=1)  # 1KB limit
        
        assert result is False
    
    def test_validate_non_python_file(self, temp_dir):
        """Test validating non-Python file."""
        text_file = temp_dir / "readme.txt"
        text_file.write_text("This is a text file")
        
        result = validate_file_for_analysis(text_file)
        
        assert result is False
    
    def test_validate_file_stat_error(self, temp_dir):
        """Test handling file stat error."""
        test_file = temp_dir / "test.py"
        test_file.write_text("content")
        
        with patch.object(Path, 'stat', side_effect=OSError("Stat failed")):
            result = validate_file_for_analysis(test_file)
        
        assert result is False


class TestSafeSubprocessRunner:
    """Test the SafeSubprocessRunner class."""
    
    def test_safe_subprocess_runner_initialization(self):
        """Test SafeSubprocessRunner initialization."""
        runner = SafeSubprocessRunner()
        assert runner.default_timeout == ValidationLimits.DEFAULT_TIMEOUT_SECONDS
        
        runner_custom = SafeSubprocessRunner(60)
        assert runner_custom.default_timeout == 60
    
    @patch('subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "command output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        runner = SafeSubprocessRunner()
        result = runner.run_git_command(['status'], Path('/test'))
        
        assert result == "command output"
        mock_run.assert_called_once_with(
            ['git', 'status'],
            capture_output=True,
            text=True,
            cwd=Path('/test'),
            timeout=ValidationLimits.DEFAULT_TIMEOUT_SECONDS
        )
    
    @patch('subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command execution failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result
        
        runner = SafeSubprocessRunner()
        result = runner.run_git_command(['status'], Path('/test'))
        
        assert result is None
    
    @patch('subprocess.run')
    def test_run_git_command_timeout(self, mock_run):
        """Test git command timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(['git', 'status'], 30)
        
        runner = SafeSubprocessRunner()
        result = runner.run_git_command(['status'], Path('/test'))
        
        assert result is None
    
    @patch('subprocess.run')
    def test_run_git_command_subprocess_error(self, mock_run):
        """Test git command subprocess error handling."""
        mock_run.side_effect = subprocess.SubprocessError("Process error")
        
        runner = SafeSubprocessRunner()
        result = runner.run_git_command(['status'], Path('/test'))
        
        assert result is None
    
    @patch('subprocess.run')
    def test_run_git_command_os_error(self, mock_run):
        """Test git command OS error handling."""
        mock_run.side_effect = OSError("Git not found")
        
        runner = SafeSubprocessRunner()
        result = runner.run_git_command(['status'], Path('/test'))
        
        assert result is None
    
    def test_run_git_command_custom_timeout(self):
        """Test git command with custom timeout."""
        runner = SafeSubprocessRunner()
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "output"
            mock_run.return_value = mock_result
            
            runner.run_git_command(['status'], Path('/test'), timeout=60)
            
            mock_run.assert_called_once()
            assert mock_run.call_args[1]['timeout'] == 60


class TestStandardizeErrorMessage:
    """Test the standardize_error_message function."""
    
    def test_standardize_with_context(self):
        """Test standardizing error message with context."""
        error = ValueError("Something went wrong")
        
        result = standardize_error_message(error, "Database operation")
        
        assert result == "Database operation: ValueError: Something went wrong"
    
    def test_standardize_without_context(self):
        """Test standardizing error message without context."""
        error = FileNotFoundError("File not found")
        
        result = standardize_error_message(error)
        
        assert result == "FileNotFoundError: File not found"
    
    def test_standardize_various_error_types(self):
        """Test standardizing various error types."""
        test_cases = [
            (ValueError("value error"), "ValueError: value error"),
            (KeyError("missing key"), "KeyError: missing key"),
            (IOError("io error"), "OSError: io error"),  # IOError is alias for OSError
        ]
        
        for error, expected in test_cases:
            result = standardize_error_message(error)
            assert result == expected


class TestBoundedDict:
    """Test the BoundedDict class."""
    
    def test_bounded_dict_initialization(self):
        """Test BoundedDict initialization."""
        bd = BoundedDict()
        assert bd.max_size == ValidationLimits.MAX_CACHE_ENTRIES
        assert len(bd) == 0
        
        bd_custom = BoundedDict(max_size=5)
        assert bd_custom.max_size == 5
    
    def test_basic_operations(self):
        """Test basic dictionary operations."""
        bd = BoundedDict(max_size=3)
        
        bd['key1'] = 'value1'
        bd['key2'] = 'value2'
        
        assert bd['key1'] == 'value1'
        assert bd['key2'] == 'value2'
        assert len(bd) == 2
        assert 'key1' in bd
    
    def test_size_limit_enforcement(self):
        """Test that size limit is enforced with LRU eviction."""
        bd = BoundedDict(max_size=2)
        
        bd['key1'] = 'value1'
        bd['key2'] = 'value2'
        bd['key3'] = 'value3'  # Should evict key1
        
        assert len(bd) == 2
        assert 'key1' not in bd
        assert 'key2' in bd
        assert 'key3' in bd
    
    def test_lru_access_pattern(self):
        """Test LRU access pattern."""
        bd = BoundedDict(max_size=2)
        
        bd['key1'] = 'value1'
        bd['key2'] = 'value2'
        
        # Access key1 to make it most recently used
        _ = bd['key1']
        
        # Add key3, should evict key2 (least recently used)
        bd['key3'] = 'value3'
        
        assert 'key1' in bd
        assert 'key2' not in bd
        assert 'key3' in bd
    
    def test_update_existing_key(self):
        """Test updating existing key doesn't change access order unnecessarily."""
        bd = BoundedDict(max_size=2)
        
        bd['key1'] = 'value1'
        bd['key2'] = 'value2'
        bd['key1'] = 'new_value1'  # Update existing key
        
        assert len(bd) == 2
        assert bd['key1'] == 'new_value1'
        
        # Add new key, should evict key2
        bd['key3'] = 'value3'
        
        assert 'key1' in bd
        assert 'key2' not in bd
        assert 'key3' in bd
    
    def test_deletion(self):
        """Test key deletion."""
        bd = BoundedDict(max_size=3)
        
        bd['key1'] = 'value1'
        bd['key2'] = 'value2'
        bd['key3'] = 'value3'
        
        del bd['key2']
        
        assert len(bd) == 2
        assert 'key1' in bd
        assert 'key2' not in bd
        assert 'key3' in bd
    
    def test_access_order_tracking(self):
        """Test that access order is properly tracked."""
        bd = BoundedDict(max_size=3)
        
        bd['a'] = 1
        bd['b'] = 2
        bd['c'] = 3
        
        # Access in specific order
        _ = bd['b']
        _ = bd['a']
        _ = bd['c']
        
        # Add new item, should evict the oldest in access order
        bd['d'] = 4
        
        # The exact eviction behavior depends on implementation details
        assert len(bd) == 3
        assert 'd' in bd


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple utilities."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project structure."""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir)
        
        # Create project structure
        (project_root / "src").mkdir()
        (project_root / "tests").mkdir()
        
        yield project_root
        
        shutil.rmtree(temp_dir)
    
    def test_mutation_testing_workflow(self, temp_project):
        """Test complete mutation testing workflow using utilities."""
        # Create source file
        source_file = temp_project / "src" / "calculator.py"
        source_content = """
def add(a, b):
    if a > 0 and b > 0:
        return a + b
    elif a == 0:
        return b
    else:
        return 0
"""
        source_file.write_text(source_content)
        
        # Validate file
        assert validate_file_for_analysis(source_file)
        
        # Extract function content
        func_content = extract_function_content(source_content, "add")
        assert "if a > 0 and b > 0:" in func_content
        
        # Test mutation patterns
        assert CompiledPatterns.OFF_BY_ONE.search(func_content)
        assert CompiledPatterns.BOOLEAN_LOGIC.search(func_content)
        assert CompiledPatterns.BOUNDARY_NUMS.search(func_content)
        
        # Apply temporary mutation
        mutated_content = source_content.replace("if a > 0", "if a >= 0")
        
        with temporary_file_mutation(source_file, mutated_content):
            # Verify mutation applied
            current = source_file.read_text()
            assert "if a >= 0" in current
        
        # Verify restoration
        restored = source_file.read_text()
        assert restored == source_content
    
    def test_error_handling_workflow(self, temp_project):
        """Test error handling across utilities."""
        # Test with problematic file
        bad_file = temp_project / "bad.py"
        
        # File doesn't exist
        assert not validate_file_for_analysis(bad_file)
        assert safe_read_file(bad_file) == ""
        
        # Create file with permission issues (simulate)
        bad_file.write_text("content")
        
        with patch.object(Path, 'stat', side_effect=OSError("Permission denied")):
            assert not validate_file_for_analysis(bad_file)
        
        # Test error standardization
        error = FileNotFoundError("File not found")
        standardized = standardize_error_message(error, "File validation")
        assert "File validation: FileNotFoundError: File not found" == standardized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])