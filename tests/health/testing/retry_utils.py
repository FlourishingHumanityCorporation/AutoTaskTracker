"""Retry utilities with exponential backoff for reliable operations.

This module provides decorators and utilities for adding retry logic to
operations that may fail transiently, such as Git operations and file I/O.
"""

import functools
import logging
import time
import random
import subprocess
from pathlib import Path
from typing import Callable, Optional, List, Type, Any, Union

from .constants import CONSTANTS

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(self,
                 max_attempts: Optional[int] = None,
                 base_delay: Optional[float] = None,
                 max_delay: Optional[float] = None,
                 backoff_factor: Optional[float] = None,
                 jitter: bool = True):
        self.max_attempts = max_attempts or CONSTANTS.RETRY.DEFAULT_MAX_ATTEMPTS
        self.base_delay = base_delay or CONSTANTS.RETRY.DEFAULT_BASE_DELAY
        self.max_delay = max_delay or CONSTANTS.RETRY.DEFAULT_MAX_DELAY
        self.backoff_factor = backoff_factor or CONSTANTS.RETRY.DEFAULT_BACKOFF_FACTOR
        self.jitter = jitter


def with_retry(config: Optional[RetryConfig] = None,
               exceptions: Optional[tuple] = None,
               on_retry: Optional[Callable[[Exception, int], None]] = None):
    """Decorator to add exponential backoff retry logic to functions.
    
    Args:
        config: RetryConfig instance, defaults to conservative settings
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry attempt
    
    Example:
        @with_retry(RetryConfig(max_attempts=5), exceptions=(OSError, subprocess.CalledProcessError))
        def flaky_operation():
            # This operation will be retried up to 5 times
            pass
    """
    if config is None:
        config = RetryConfig()
    
    if exceptions is None:
        exceptions = (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed, re-raise
                        logger.error(f"Function {func.__name__} failed after {config.max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {e}. "
                                 f"Retrying in {delay:.2f}s...")
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class GitOperations:
    """Reliable Git operations with retry logic."""
    
    def __init__(self, project_root: Path, retry_config: Optional[RetryConfig] = None):
        self.project_root = project_root
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=0.5,
            max_delay=10.0
        )
    
    @with_retry(RetryConfig(max_attempts=3), exceptions=(subprocess.CalledProcessError, OSError))
    def get_commit_info(self, commit_hash: str = "HEAD") -> dict:
        """Get commit information with retry logic.
        
        Args:
            commit_hash: Git commit hash, defaults to HEAD
            
        Returns:
            Dictionary with commit info
            
        Raises:
            subprocess.CalledProcessError: If git command fails after retries
        """
        try:
            result = subprocess.run([
                'git', 'show', '--format=%H|%an|%ae|%ad|%s', '--no-patch', commit_hash
            ], capture_output=True, text=True, cwd=self.project_root, timeout=10)
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, 'git show', result.stderr)
            
            # Parse output
            parts = result.stdout.strip().split('|', 4)
            if len(parts) != 5:
                raise ValueError(f"Unexpected git output format: {result.stdout}")
            
            return {
                'hash': parts[0],
                'author_name': parts[1],
                'author_email': parts[2],
                'date': parts[3],
                'message': parts[4]
            }
            
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Git command timeout: {e}")
            raise
    
    @with_retry(RetryConfig(max_attempts=3), exceptions=(subprocess.CalledProcessError, OSError))
    def get_file_history(self, file_path: Path, max_commits: int = 10) -> List[dict]:
        """Get file history with retry logic.
        
        Args:
            file_path: Path to the file
            max_commits: Maximum number of commits to retrieve
            
        Returns:
            List of commit dictionaries
        """
        try:
            result = subprocess.run([
                'git', 'log', '--format=%H|%an|%ad|%s', f'-{max_commits}', '--', str(file_path)
            ], capture_output=True, text=True, cwd=self.project_root, timeout=15)
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, 'git log', result.stderr)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'date': parts[2],
                        'message': parts[3]
                    })
            
            return commits
            
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Git history command timeout: {e}")
            raise
    
    @with_retry(RetryConfig(max_attempts=3), exceptions=(subprocess.CalledProcessError, OSError))
    def check_repo_status(self) -> dict:
        """Check repository status with retry logic.
        
        Returns:
            Dictionary with repository status information
        """
        try:
            # Check if we're in a git repository
            result = subprocess.run([
                'git', 'rev-parse', '--is-inside-work-tree'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=5)
            
            if result.returncode != 0:
                return {'is_git_repo': False, 'error': result.stderr.strip()}
            
            # Get status information
            status_result = subprocess.run([
                'git', 'status', '--porcelain'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=10)
            
            if status_result.returncode != 0:
                raise subprocess.CalledProcessError(status_result.returncode, 'git status', status_result.stderr)
            
            # Count changes
            lines = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
            modified_files = [line for line in lines if line.strip().startswith('M')]
            added_files = [line for line in lines if line.strip().startswith('A')]
            untracked_files = [line for line in lines if line.strip().startswith('??')]
            
            return {
                'is_git_repo': True,
                'is_clean': len(lines) == 0,
                'modified_count': len(modified_files),
                'added_count': len(added_files),
                'untracked_count': len(untracked_files),
                'total_changes': len(lines)
            }
            
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Git status command timeout: {e}")
            raise


class FileOperations:
    """Reliable file operations with retry logic."""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=5.0
        )
    
    @with_retry(RetryConfig(max_attempts=3), exceptions=(OSError, PermissionError, UnicodeDecodeError))
    def read_file_safe(self, file_path: Path, encoding: str = 'utf-8') -> str:
        """Read file with retry logic and encoding fallback.
        
        Args:
            file_path: Path to the file to read
            encoding: Primary encoding to try
            
        Returns:
            File contents as string
            
        Raises:
            OSError: If file cannot be read after retries
        """
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Try alternative encodings
            for fallback_encoding in ['latin-1', 'cp1252', 'utf-16']:
                try:
                    logger.debug(f"Trying fallback encoding {fallback_encoding} for {file_path}")
                    return file_path.read_text(encoding=fallback_encoding)
                except UnicodeDecodeError:
                    continue
            raise UnicodeDecodeError(f"Could not decode file {file_path} with any encoding")
    
    @with_retry(RetryConfig(max_attempts=3), exceptions=(OSError, PermissionError))
    def write_file_safe(self, file_path: Path, content: str, encoding: str = 'utf-8') -> None:
        """Write file with retry logic and atomic operations.
        
        Args:
            file_path: Path to the file to write
            content: Content to write
            encoding: Encoding to use
        """
        import tempfile
        import shutil
        
        # Write to temporary file first for atomic operation
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        try:
            temp_path.write_text(content, encoding=encoding)
            # Atomic rename
            shutil.move(str(temp_path), str(file_path))
        except OSError:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise
    
    @with_retry(RetryConfig(max_attempts=3), exceptions=(OSError,))
    def ensure_directory(self, dir_path: Path) -> None:
        """Ensure directory exists with retry logic.
        
        Args:
            dir_path: Path to the directory to create
        """
        dir_path.mkdir(parents=True, exist_ok=True)


# Convenience functions for common operations
def retry_git_operation(func: Callable, *args, **kwargs) -> Any:
    """Convenience function to retry a git operation."""
    config = RetryConfig(max_attempts=3, base_delay=0.5)
    
    @with_retry(config, exceptions=(subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired))
    def _wrapped():
        return func(*args, **kwargs)
    
    return _wrapped()


def retry_file_operation(func: Callable, *args, **kwargs) -> Any:
    """Convenience function to retry a file operation."""
    config = RetryConfig(max_attempts=3, base_delay=0.1)
    
    @with_retry(config, exceptions=(OSError, PermissionError, UnicodeDecodeError))
    def _wrapped():
        return func(*args, **kwargs)
    
    return _wrapped()