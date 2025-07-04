"""
Dashboard modules for AutoTaskTracker.
"""

# Export main dashboard functions
from .task_board import main as task_board_main
from .analytics import main as analytics_main
from .timetracker import main as timetracker_main

__all__ = [
    'task_board_main',
    'analytics_main', 
    'timetracker_main'
]