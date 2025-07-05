"""
Shared fixtures for health tests to prevent redundant file scanning.

This module provides cached fixtures that are shared across all health tests,
significantly improving performance by avoiding repeated file system operations.
"""

import os
import pytest
from pathlib import Path
from typing import List, Dict
import logging
from functools import lru_cache

from tests.health.shared_file_selection import get_health_test_files, categorize_files
from tests.health.analyzers.utils import FileAnalysisCache

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get project root directory (cached for session)."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def file_cache() -> FileAnalysisCache:
    """Get shared file analysis cache."""
    return FileAnalysisCache()


@pytest.fixture(scope="session")
def all_python_files(project_root: Path) -> List[Path]:
    """Get all Python files for analysis (cached for entire session)."""
    import time
    start_time = time.time()
    
    files = get_health_test_files(project_root)
    
    elapsed = time.time() - start_time
    logger.info(f"Loaded {len(files)} Python files for health testing in {elapsed:.2f}s")
    
    # Warn if file loading is slow
    if elapsed > 5.0:
        logger.warning(f"File discovery took {elapsed:.2f}s - consider reducing PENSIEVE_MAX_FILES")
    
    return files


@pytest.fixture(scope="session")
def categorized_files(all_python_files: List[Path]) -> Dict[str, List[Path]]:
    """Get categorized files (cached for entire session)."""
    categories = categorize_files(all_python_files)
    logger.info(f"Categorized files: {', '.join(f'{k}={len(v)}' for k, v in categories.items())}")
    return categories


@pytest.fixture(scope="session")
def production_files(categorized_files: Dict[str, List[Path]]) -> List[Path]:
    """Get production files only."""
    return categorized_files['production_files']


@pytest.fixture(scope="session")
def script_files(categorized_files: Dict[str, List[Path]]) -> List[Path]:
    """Get script files only."""
    return categorized_files['script_files']


@pytest.fixture(scope="session")
def test_files(categorized_files: Dict[str, List[Path]]) -> List[Path]:
    """Get test files only."""
    return categorized_files['test_files']


@pytest.fixture(scope="session")
def dashboard_files(categorized_files: Dict[str, List[Path]]) -> List[Path]:
    """Get dashboard files only."""
    return categorized_files['dashboard_files']


@pytest.fixture(scope="session")
def docs_dir(project_root: Path) -> Path:
    """Get documentation directory."""
    return project_root / "docs"


@pytest.fixture(scope="session")
def test_dir(project_root: Path) -> Path:
    """Get test directory."""
    return project_root / "tests"


# Performance optimization fixtures
@pytest.fixture(scope="session")
def max_files_per_test() -> int:
    """Maximum files to analyze per test for performance."""
    return int(os.getenv('PENSIEVE_MAX_FILES_PER_TEST', '50'))


@pytest.fixture(scope="function")
def test_timeout():
    """Apply a timeout to individual tests to prevent hanging (opt-in)."""
    timeout_seconds = int(os.getenv('PENSIEVE_TEST_TIMEOUT', '30'))
    
    import signal
    import sys
    
    # Only use SIGALRM on Unix-like systems
    if sys.platform != 'win32' and hasattr(signal, 'SIGALRM'):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test exceeded {timeout_seconds}s timeout")
        
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        yield
        
        # Clean up
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    else:
        # No timeout on Windows or systems without SIGALRM
        yield


# Shared analyzer instances (created once per session)
@pytest.fixture(scope="session")
def database_analyzer(project_root: Path):
    """Get shared database analyzer instance."""
    from tests.health.analyzers.database_analyzer import DatabaseAccessAnalyzer
    return DatabaseAccessAnalyzer(project_root)


@pytest.fixture(scope="session")
def error_analyzer(project_root: Path):
    """Get shared error analyzer instance."""
    from tests.health.analyzers.error_analyzer import ErrorHandlingAnalyzer
    return ErrorHandlingAnalyzer(project_root)


@pytest.fixture(scope="session")
def config_analyzer(project_root: Path):
    """Get shared config analyzer instance."""
    from tests.health.analyzers.config_analyzer import ConfigurationAnalyzer
    return ConfigurationAnalyzer(project_root)


