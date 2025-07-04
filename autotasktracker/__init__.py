"""
AutoTaskTracker - AI-powered task discovery from screenshots.
"""

__version__ = "0.1.0"

# Make key components easily importable
from autotasktracker.core.categorizer import ActivityCategorizer, categorize_activity, extract_task_summary, extract_window_title
from autotasktracker.core.database import DatabaseManager, get_default_db_manager
from autotasktracker.utils.config import Config, get_config

__all__ = [
    'ActivityCategorizer',
    'categorize_activity', 
    'extract_task_summary',
    'extract_window_title',
    'DatabaseManager',
    'get_default_db_manager',
    'Config',
    'get_config'
]