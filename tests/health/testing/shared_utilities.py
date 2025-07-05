"""Shared utilities for effectiveness validation system.

This module provides common utilities to reduce code duplication and
establish consistent patterns across the effectiveness validation system.
"""

import logging
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Generator, List, Dict, Any, Union
import tempfile
import time

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for performance
class CompiledPatterns:
    """Pre-compiled regex patterns to avoid recompilation in loops."""
    
    OFF_BY_ONE = re.compile(r'>\s*\d+|<\s*\d+|>=\s*\d+|<=\s*\d+')
    BOOLEAN_LOGIC = re.compile(r'\s+and\s+|\s+or\s+')
    BOUNDARY_NUMS = re.compile(r'\b0\b|\b1\b|\b-1\b')
    TEST_PATTERNS = re.compile(r'assert.*==.*[^)]')
    MOCK_PATTERNS = re.compile(r'\.assert_called|\.call_count|Mock\(\)')
    
    # Real-world bug patterns
    NULL_HANDLING = re.compile(r'assert.*== 0|assert.*len.*== 0|assert.*is None|assert.*== None', re.IGNORECASE)
    ERROR_TESTING = re.compile(r'except.*Exception|pytest\.raises', re.IGNORECASE)
    STATE_VALIDATION = re.compile(r'assert.*!=.*before|assert.*changed', re.IGNORECASE)
    BOUNDARY_TESTING = re.compile(r'assert.*>.*0|assert.*<.*len|assert.*startswith|assert.*endswith', re.IGNORECASE)


class ValidationLimits:
    """Configuration limits to replace hardcoded magic numbers."""
    
    # Function complexity limits
    MAX_FUNCTION_LINES = 30
    MAX_HARDCODED_ITEMS = 3
    
    # File processing limits  
    MAX_FILE_SIZE_KB = 100
    LARGE_FILE_THRESHOLD_KB = 50
    MAX_MUTATIONS_PER_FILE = 20
    
    # Performance limits
    DEFAULT_TIMEOUT_SECONDS = 30
    MAX_ANALYSIS_TIME_SECONDS = 300
    MAX_CACHE_ENTRIES = 1000
    
    # Quality thresholds
    MIN_EFFECTIVENESS_THRESHOLD = 50.0
    WARNING_EFFECTIVENESS_THRESHOLD = 70.0
    HIGH_EFFECTIVENESS_THRESHOLD = 90.0


def safe_read_file(file_path: Path, encoding: str = 'utf-8') -> str:
    """Safely read file with proper encoding handling and error recovery.
    
    Args:
        file_path: Path to the file to read
        encoding: Text encoding to use (default: utf-8)
        
    Returns:
        File contents as string, or empty string if reading fails
        
    Raises:
        None - errors are logged and empty string returned
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
        
    try:
        return file_path.read_text(encoding=encoding, errors='ignore')
    except OSError as e:
        logger.warning(f"Could not read file {file_path}: {e}")
        return ""
    except UnicodeDecodeError as e:
        logger.warning(f"Encoding error reading {file_path}: {e}")
        try:
            # Fallback to latin-1 which can decode any byte sequence
            return file_path.read_text(encoding='latin-1', errors='ignore')
        except OSError:
            return ""
    except Exception as e:
        logger.error(f"Unexpected error reading {file_path}: {e}")
        return ""


def safe_parse_datetime(date_string: str, formats: Optional[List[str]] = None) -> Optional[time.struct_time]:
    """Safely parse datetime string with multiple format attempts.
    
    Args:
        date_string: String to parse as datetime
        formats: List of datetime formats to try (optional)
        
    Returns:
        Parsed datetime or None if parsing fails
    """
    if not date_string or not isinstance(date_string, str):
        return None
        
    if formats is None:
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S'
        ]
    
    for fmt in formats:
        try:
            return time.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    
    logger.debug(f"Could not parse datetime: {date_string}")
    return None


@contextmanager
def temporary_file_mutation(source_file: Path, mutated_content: str) -> Generator[None, None, None]:
    """Context manager for safely applying temporary file mutations with atomic operations.
    
    This ensures that:
    1. Original file is backed up atomically before mutation
    2. Mutation is applied using atomic rename operation
    3. Original content is restored regardless of what happens
    4. Multiple restoration strategies ensure data safety
    
    Args:
        source_file: Path to the file to mutate
        mutated_content: Content to temporarily write to the file
        
    Yields:
        None - context for running code with mutated file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        PermissionError: If file cannot be modified
        OSError: For other file system errors
    """
    import shutil
    import os
    
    if not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    
    backup_path = source_file.with_suffix(source_file.suffix + '.mutation_backup')
    temp_path = source_file.with_suffix(source_file.suffix + '.tmp')
    original_content = None
    
    # Read original content first
    try:
        original_content = source_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            original_content = source_file.read_text(encoding='latin-1')
        except OSError as e:
            raise OSError(f"Cannot read source file {source_file}: {e}")
    except OSError as e:
        raise OSError(f"Cannot read source file {source_file}: {e}")
    
    # Create atomic backup
    try:
        shutil.copy2(source_file, backup_path)
        logger.debug(f"Created backup at {backup_path}")
    except OSError as e:
        raise OSError(f"Cannot create backup of {source_file}: {e}")
    
    # Apply mutation atomically
    try:
        # Write to temp file first
        temp_path.write_text(mutated_content, encoding='utf-8')
        
        # Atomic rename (on same filesystem)
        os.replace(str(temp_path), str(source_file))
        logger.debug(f"Applied mutation to {source_file}")
        
        # Yield control to caller
        yield
        
    except PermissionError as e:
        # Restore from backup before raising
        if backup_path.exists():
            try:
                shutil.copy2(backup_path, source_file)
            except OSError:
                pass
        raise PermissionError(f"Cannot write to source file {source_file}: {e}")
    except OSError as e:
        # Restore from backup before raising
        if backup_path.exists():
            try:
                shutil.copy2(backup_path, source_file)
            except OSError:
                pass
        raise OSError(f"File system error with {source_file}: {e}")
    finally:
        # Always restore original with multiple strategies
        restore_success = False
        
        # Strategy 1: Restore from backup file
        if backup_path.exists():
            try:
                shutil.copy2(backup_path, source_file)
                logger.debug(f"Restored from backup: {source_file}")
                restore_success = True
            except OSError as e:
                logger.error(f"Failed to restore from backup: {e}")
        
        # Strategy 2: Restore from memory if backup failed
        if not restore_success and original_content is not None:
            try:
                source_file.write_text(original_content, encoding='utf-8')
                logger.debug(f"Restored from memory: {source_file}")
                restore_success = True
            except OSError as e:
                logger.error(f"Failed to restore from memory: {e}")
        
        # Strategy 3: Keep backup if restore failed
        if not restore_success:
            logger.critical(f"CRITICAL: Could not restore {source_file}! Backup preserved at {backup_path}")
            # Don't delete backup in this case
        else:
            # Cleanup backup only if restore successful
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except OSError:
                    pass  # Non-critical
        
        # Cleanup temp file if it exists
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass  # Non-critical


@contextmanager  
def managed_temporary_file(content: str, suffix: str = '.tmp') -> Generator[Path, None, None]:
    """Context manager for creating and cleaning up temporary files.
    
    Args:
        content: Content to write to temporary file
        suffix: File suffix for the temporary file
        
    Yields:
        Path to the temporary file
        
    Raises:
        OSError: If temporary file cannot be created or written
    """
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_file = Path(f.name)
        
        yield temp_file
        
    except OSError as e:
        raise OSError(f"Cannot create temporary file: {e}")
    finally:
        # Clean up temporary file
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                logger.debug(f"Cleaned up temporary file: {temp_file}")
            except OSError as cleanup_error:
                logger.warning(f"Could not cleanup temporary file {temp_file}: {cleanup_error}")


def extract_function_content(source_code: str, function_name: str) -> str:
    """Extract the content of a specific function from source code.
    
    Args:
        source_code: Full source code text
        function_name: Name of function to extract
        
    Returns:
        Function body content, or empty string if not found
    """
    if not source_code or not function_name:
        return ""
    
    lines = source_code.split('\n')
    start_line = None
    
    # Find function definition
    for i, line in enumerate(lines):
        if f'def {function_name}(' in line:
            start_line = i
            break
    
    if start_line is None:
        return ""
    
    # Extract function body with proper indentation detection
    function_body = []
    indent_level = None
    
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        
        # Skip empty lines
        if line.strip() == '':
            function_body.append(line)
            continue
        
        # Determine base indentation from first non-empty line
        current_indent = len(line) - len(line.lstrip())
        if indent_level is None and line.strip():
            indent_level = current_indent
        
        # Stop when we reach the same or lower indentation (next function/class)
        if line.strip() and current_indent <= indent_level and not line.startswith('#'):
            break
            
        function_body.append(line)
    
    return '\n'.join(function_body)


def validate_file_for_analysis(file_path: Path, max_size_kb: int = ValidationLimits.MAX_FILE_SIZE_KB) -> bool:
    """Validate that a file is suitable for analysis.
    
    Args:
        file_path: Path to file to validate
        max_size_kb: Maximum file size in KB
        
    Returns:
        True if file is suitable for analysis, False otherwise
    """
    if not file_path.exists():
        logger.debug(f"File does not exist: {file_path}")
        return False
    
    if not file_path.is_file():
        logger.debug(f"Path is not a file: {file_path}")
        return False
    
    try:
        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb > max_size_kb:
            logger.debug(f"File too large ({file_size_kb:.1f}KB > {max_size_kb}KB): {file_path}")
            return False
    except OSError as e:
        logger.warning(f"Cannot stat file {file_path}: {e}")
        return False
    
    # Check if it's a Python file
    if file_path.suffix != '.py':
        logger.debug(f"Not a Python file: {file_path}")
        return False
    
    return True


class SafeSubprocessRunner:
    """Safe subprocess execution with timeout and error handling."""
    
    def __init__(self, default_timeout: int = ValidationLimits.DEFAULT_TIMEOUT_SECONDS):
        self.default_timeout = default_timeout
    
    def run_git_command(self, args: List[str], cwd: Path, timeout: Optional[int] = None) -> Optional[str]:
        """Run a git command safely with proper error handling.
        
        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory for the command
            timeout: Timeout in seconds (optional)
            
        Returns:
            Command output as string, or None if command failed
        """
        import subprocess
        
        if timeout is None:
            timeout = self.default_timeout
        
        cmd = ['git'] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.debug(f"Git command failed (exit {result.returncode}): {' '.join(cmd)}")
                if result.stderr:
                    logger.debug(f"Git stderr: {result.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Git command timed out after {timeout}s: {' '.join(cmd)}")
            return None
        except subprocess.SubprocessError as e:
            logger.warning(f"Git command failed: {e}")
            return None
        except OSError as e:
            logger.warning(f"Git command OS error: {e}")
            return None


def standardize_error_message(error: Exception, context: str = "") -> str:
    """Standardize error messages for consistent logging.
    
    Args:
        error: Exception that occurred
        context: Additional context for the error
        
    Returns:
        Standardized error message string
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    if context:
        return f"{context}: {error_type}: {error_msg}"
    else:
        return f"{error_type}: {error_msg}"


class BoundedDict(dict):
    """Dictionary with maximum size limit and LRU eviction."""
    
    def __init__(self, max_size: int = ValidationLimits.MAX_CACHE_ENTRIES):
        super().__init__()
        self.max_size = max_size
        self._access_order = []
    
    def __setitem__(self, key, value):
        # Remove if already exists
        if key in self:
            self._access_order.remove(key)
        
        # Add to end (most recently used)
        self._access_order.append(key)
        super().__setitem__(key, value)
        
        # Evict oldest if over limit
        while len(self) > self.max_size:
            oldest_key = self._access_order.pop(0)
            super().__delitem__(oldest_key)
    
    def __getitem__(self, key):
        # Move to end (most recently used)
        if key in self._access_order:
            self._access_order.remove(key)
            self._access_order.append(key)
        return super().__getitem__(key)
    
    def __delitem__(self, key):
        if key in self._access_order:
            self._access_order.remove(key)
        super().__delitem__(key)