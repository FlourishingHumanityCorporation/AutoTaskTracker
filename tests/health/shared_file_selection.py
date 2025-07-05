"""
Shared file selection logic for health tests.
Ensures all health tests analyze the exact same set of files.
"""

import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def get_health_test_files(project_root: Path) -> List[Path]:
    """Get the exact same file list that the original health tests use.
    
    This is a direct copy of the original TestPensieveIntegrationHealth.setup_class() logic
    to ensure 100% identical file selection.
    """
    
    # Check for incremental mode first
    from tests.health.analyzers.utils import IncrementalTestRunner
    
    if IncrementalTestRunner.should_run_incremental():
        changed_files = IncrementalTestRunner.get_changed_files(
            base_branch=os.getenv('GITHUB_BASE_REF')  # For PRs
        )
        if changed_files:
            logger.info(f"Running in incremental mode on {len(changed_files)} changed files")
            return changed_files
    
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
            
            # Stop if we hit the limit with priority files
            if len(python_files) >= max_files:
                logger.info(f"Limited analysis to {max_files} priority files for performance")
                break
    
    # Add other files if we have room
    remaining_slots = max_files - len(python_files)
    if remaining_slots > 0 and other_files:
        python_files.extend(other_files[:remaining_slots])
    
    logger.info(f"Selected {len(python_files)} files for health test analysis")
    return python_files


def categorize_files(files: List[Path]) -> dict:
    """Categorize files for targeted analysis (same logic as original)."""
    script_files = []
    test_files = []
    production_files = []
    dashboard_files = []
    
    for file_path in files:
        path_str = str(file_path)
        # Only consider files in tests/ directory as test files
        if 'tests/' in path_str:
            test_files.append(file_path)
        elif 'scripts/' in path_str:
            script_files.append(file_path)
        elif 'dashboards/' in path_str:
            dashboard_files.append(file_path)
            production_files.append(file_path)
        elif 'autotasktracker/' in path_str:
            production_files.append(file_path)
    
    return {
        'script_files': script_files,
        'test_files': test_files,
        'production_files': production_files,
        'dashboard_files': dashboard_files
    }