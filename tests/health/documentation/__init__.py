"""Utilities for documentation health tests."""

import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def safe_read_text(file_path: Union[str, Path]) -> str:
    """Safely read text from a file with proper encoding handling.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File contents as string, or empty string if file cannot be read
        
    Example:
        >>> content = safe_read_text("docs/README.md")
        >>> if content:
        ...     print("File read successfully")
    """
    try:
        path = Path(file_path)
        return path.read_text(encoding='utf-8', errors='ignore')
    except (UnicodeDecodeError, OSError) as e:
        logger.warning(f"Could not read file {file_path}: {e}")
        return ""