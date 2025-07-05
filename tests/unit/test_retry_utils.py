"""Unit tests for retry utilities."""

import pytest
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, call

from tests.health.testing.retry_utils import (
    RetryConfig,
    with_retry,
    GitOperations,
    FileOperations,
    retry_git_operation,
    retry_file_operation
)


class TestRetryConfig:
    """Test retry configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            backoff_factor=1.5,
            jitter=False
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.backoff_factor == 1.5
        assert config.jitter is False


class TestWithRetryDecorator:
    """Test the with_retry decorator."""
    
    def test_successful_operation(self):
        """Test that successful operations work normally."""
        @with_retry()
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_retry_on_exception(self):
        """Test that operations are retried on specified exceptions."""
        attempt_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01), exceptions=(ValueError,))
        def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert attempt_count == 3
    
    def test_max_attempts_exceeded(self):
        """Test that exceptions are re-raised after max attempts."""
        @with_retry(RetryConfig(max_attempts=2, base_delay=0.01), exceptions=(ValueError,))
        def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            always_fails()
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        attempt_count = 0
        
        @with_retry(RetryConfig(max_attempts=3), exceptions=(ValueError,))
        def raises_type_error():
            nonlocal attempt_count
            attempt_count += 1
            raise TypeError("Not retryable")
        
        with pytest.raises(TypeError, match="Not retryable"):
            raises_type_error()
        assert attempt_count == 1  # Should not retry
    
    @patch('time.sleep')
    def test_backoff_timing(self, mock_sleep):
        """Test exponential backoff timing."""
        attempt_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=1.0, backoff_factor=2.0, jitter=False))
        def fails_twice():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise OSError("Temporary failure")
            return "success"
        
        result = fails_twice()
        assert result == "success"
        
        # Check sleep was called with exponential backoff
        assert mock_sleep.call_count == 2
        call_args = [call[0][0] for call in mock_sleep.call_args_list]
        assert call_args[0] == 1.0  # First retry: base_delay
        assert call_args[1] == 2.0  # Second retry: base_delay * backoff_factor


class TestGitOperations:
    """Test Git operations with retry logic."""
    
    @pytest.fixture
    def git_ops(self, tmp_path):
        """Create GitOperations instance with temporary directory."""
        return GitOperations(tmp_path)
    
    @patch('subprocess.run')
    def test_get_commit_info_success(self, mock_run, git_ops):
        """Test successful commit info retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="abc123|John Doe|john@example.com|2023-01-01|Test commit"
        )
        
        info = git_ops.get_commit_info()
        
        assert info['hash'] == 'abc123'
        assert info['author_name'] == 'John Doe'
        assert info['author_email'] == 'john@example.com'
        assert info['message'] == 'Test commit'
    
    @patch('subprocess.run')
    def test_get_commit_info_retry(self, mock_run, git_ops):
        """Test commit info retrieval with retry on failure."""
        # First call fails, second succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stderr="temporary error"),
            Mock(returncode=0, stdout="abc123|John Doe|john@example.com|2023-01-01|Test commit")
        ]
        
        info = git_ops.get_commit_info()
        
        assert info['hash'] == 'abc123'
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_check_repo_status_success(self, mock_run, git_ops):
        """Test successful repository status check."""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="true"),  # is-inside-work-tree
            Mock(returncode=0, stdout=" M file1.py\nA  file2.py\n?? file3.py")  # status
        ]
        
        status = git_ops.check_repo_status()
        
        assert status['is_git_repo'] is True
        assert status['is_clean'] is False
        assert status['modified_count'] == 1
        assert status['added_count'] == 1
        assert status['untracked_count'] == 1
    
    @patch('subprocess.run')
    def test_check_repo_status_not_git(self, mock_run, git_ops):
        """Test repository status when not in a git repo."""
        mock_run.return_value = Mock(returncode=1, stderr="not a git repository")
        
        status = git_ops.check_repo_status()
        
        assert status['is_git_repo'] is False
        assert 'error' in status


class TestFileOperations:
    """Test file operations with retry logic."""
    
    @pytest.fixture
    def file_ops(self):
        """Create FileOperations instance."""
        return FileOperations()
    
    def test_read_file_safe_success(self, file_ops, tmp_path):
        """Test successful file reading."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding='utf-8')
        
        content = file_ops.read_file_safe(test_file)
        assert content == "Hello, World!"
    
    def test_read_file_safe_encoding_fallback(self, file_ops, tmp_path):
        """Test reading file with encoding fallback."""
        test_file = tmp_path / "test.txt"
        
        # Write with latin-1 encoding
        with open(test_file, 'w', encoding='latin-1') as f:
            f.write("Hello, café!")
        
        # Should succeed with fallback encoding
        content = file_ops.read_file_safe(test_file)
        assert "café" in content
    
    def test_write_file_safe_success(self, file_ops, tmp_path):
        """Test successful file writing."""
        test_file = tmp_path / "test.txt"
        
        file_ops.write_file_safe(test_file, "Hello, World!")
        
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"
    
    def test_ensure_directory_success(self, file_ops, tmp_path):
        """Test directory creation."""
        new_dir = tmp_path / "new" / "nested" / "directory"
        
        file_ops.ensure_directory(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()


class TestConvenienceFunctions:
    """Test convenience functions for retry operations."""
    
    @patch('subprocess.run')
    def test_retry_git_operation(self, mock_run):
        """Test convenience function for git operations."""
        mock_run.return_value = Mock(returncode=0, stdout="success")
        
        result = retry_git_operation(subprocess.run, ['git', 'status'])
        
        assert result.stdout == "success"
    
    def test_retry_file_operation(self, tmp_path):
        """Test convenience function for file operations."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")
        
        result = retry_file_operation(Path.read_text, test_file)
        
        assert result == "original"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])