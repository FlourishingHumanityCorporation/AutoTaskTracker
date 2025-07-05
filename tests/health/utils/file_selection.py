"""
Shared file selection logic for health tests.
Ensures all health tests analyze the exact same set of files.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_health_test_files(project_root: Path) -> List[Path]:
    """Get the exact same file list that the original health tests use.
    
    This is a direct copy of the original TestPensieveIntegrationHealth.setup_class() logic
    to ensure 100% identical file selection.
    """
    
    # Check for incremental mode first
    try:
        from tests.health.analyzers.utils import IncrementalTestRunner
        
        if IncrementalTestRunner.should_run_incremental():
            changed_files = IncrementalTestRunner.get_changed_files(
                base_branch=os.getenv('GITHUB_BASE_REF')  # For PRs
            )
            if changed_files:
                logger.info(f"Running in incremental mode on {len(changed_files)} changed files")
                return changed_files
    except ImportError:
        # Fallback if utils not available
        pass
    
    # Full mode - analyze all files (with reasonable limit for performance)
    # EXACT COPY of original logic from test_pensieve_integration_health.py
    python_files = []
    max_files = int(os.getenv('PENSIEVE_MAX_FILES', '200'))  # Limit for performance
    
    # Prioritize production and script files
    priority_dirs = ['autotasktracker/', 'scripts/']
    other_files = []
    
    # Use the EXACT same iteration pattern as original (no sorting!)
    for pattern in ['**/*.py']:
        for file_path in project_root.glob(pattern):
            if any(skip in str(file_path) for skip in ['venv/', '__pycache__', '.git', 'build/', 'dist/', '.pytest_cache/']):
                continue
                
            # Prioritize production/script files
            if any(pdir in str(file_path) for pdir in priority_dirs):
                python_files.append(file_path)
            else:
                other_files.append(file_path)
            
            # Apply file limit
            if len(python_files) + len(other_files) >= max_files:
                break
        
        if len(python_files) + len(other_files) >= max_files:
            break
    
    # Add other files if we have room
    all_files = python_files + other_files[:max_files - len(python_files)]
    
    logger.debug(f"Selected {len(all_files)} files for health analysis (limit: {max_files})")
    return all_files


def categorize_files(python_files: List[Path]) -> Dict[str, List[Path]]:
    """Categorize files by type for targeted testing.
    
    This matches the original categorization logic exactly.
    """
    categories = {
        'script_files': [],
        'test_files': [],
        'production_files': [],
        'dashboard_files': []
    }
    
    for file_path in python_files:
        file_str = str(file_path)
        
        # Categorize using exact original logic
        if 'scripts/' in file_str:
            categories['script_files'].append(file_path)
        elif 'test_' in file_path.name or '/tests/' in file_str:
            categories['test_files'].append(file_path)
        elif 'dashboard' in file_str:
            categories['dashboard_files'].append(file_path)
        elif 'autotasktracker/' in file_str:
            categories['production_files'].append(file_path)
    
    return categories


def get_project_root() -> Path:
    """Get the project root directory."""
    # Start from this file and go up to find the project root
    current = Path(__file__).parent
    while current.parent != current:  # Until we reach filesystem root
        if (current / 'autotasktracker').exists() and (current / 'tests').exists():
            return current
        current = current.parent
    
    # Fallback - assume we're in tests/health/utils
    return Path(__file__).parent.parent.parent.parent