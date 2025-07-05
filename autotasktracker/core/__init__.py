"""Core modules for AutoTaskTracker.

Barrel exports for commonly used core classes and functions.
This reduces import overhead during refactoring.

Usage:
    from autotasktracker.core import DatabaseManager, TaskExtractor, TimeTracker
"""

# Database management
from autotasktracker.core.database import DatabaseManager, get_default_db_manager

# Task processing
from autotasktracker.core.categorizer import ActivityCategorizer, categorize_activity, extract_task_summary, extract_window_title
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.core.time_tracker import TimeTracker
from autotasktracker.core.error_handler import VLMErrorHandler

# Configuration
from autotasktracker.core.config_manager import ConfigManager

# Pensieve integration
from autotasktracker.core.pensieve_adapter import PensieveSchemaAdapter

__all__ = [
    # Database
    'DatabaseManager',
    'get_default_db_manager',
    
    # Task processing
    'ActivityCategorizer',
    'categorize_activity',
    'extract_task_summary', 
    'extract_window_title',
    'TaskExtractor',
    'TimeTracker',
    'VLMErrorHandler',
    
    # Configuration
    'ConfigManager',
    
    # Pensieve
    'PensieveSchemaAdapter',
]