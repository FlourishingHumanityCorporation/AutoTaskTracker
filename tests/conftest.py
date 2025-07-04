"""
Pytest configuration and shared fixtures for AutoTaskTracker tests.

This file provides shared setup and teardown for tests to ensure:
- Proper import path configuration
- Test isolation and cleanup
- Shared fixtures for common test needs
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def test_isolation():
    """Ensure tests are isolated and don't affect each other."""
    # Store original state
    original_cwd = os.getcwd()
    original_path = sys.path.copy()
    original_env = os.environ.copy()
    
    yield
    
    # Restore original state after test
    os.chdir(original_cwd)
    sys.path[:] = original_path
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def project_root_path():
    """Provide project root path for tests."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir():
    """Provide test data directory path."""
    return Path(__file__).parent / "assets"


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    temp_file = tmp_path / "test_file.txt"
    temp_file.write_text("test content")
    return temp_file


# Mark slow tests
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )