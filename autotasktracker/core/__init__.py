"""Core modules for AutoTaskTracker."""

from autotasktracker.core.categorizer import ActivityCategorizer, categorize_activity, extract_task_summary, extract_window_title
from autotasktracker.core.database import DatabaseManager, get_default_db_manager

__all__ = [
    'ActivityCategorizer',
    'categorize_activity',
    'extract_task_summary', 
    'extract_window_title',
    'DatabaseManager',
    'get_default_db_manager'
]