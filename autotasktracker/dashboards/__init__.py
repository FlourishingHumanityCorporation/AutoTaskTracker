"""Dashboard modules for AutoTaskTracker.

Barrel exports for dashboard components and utilities.
Reduces import overhead during refactoring.

Usage:
    from autotasktracker.dashboards import DashboardManager, TaskBoard, Analytics
"""

# Main dashboard functions (imported locally to avoid circular imports)
# Importing these at the module level causes circular imports
# They are imported inside functions when needed instead

# Core components (imported directly from their modules when needed)
# from .base import BaseDashboard  # Imported locally to prevent circular imports
# from .cache import DashboardCache  # Imported locally to prevent circular imports
# from .notifications import TaskNotifier  # Imported locally to prevent circular imports

# Lazy imports for dashboard main functions
def get_task_board():
    from .task_board import main as task_board_main
    return task_board_main

def get_analytics():
    from .analytics import main as analytics_main
    return analytics_main

def get_timetracker():
    from .timetracker import main as timetracker_main
    return timetracker_main

def get_launcher():
    from .launcher import main as launcher_main
    return launcher_main

# Utilities
from .utils import format_datetime, safe_divide, get_color_palette
from .templates import DashboardTemplate

# Data components
from .data.repositories import TaskRepository, MetricsRepository
from .data.models import Task

__all__ = [
    # Main functions
    'task_board_main',
    'analytics_main', 
    'timetracker_main',
    'launcher_main',
    
    # Dashboard components
    'BaseDashboard',
    'DashboardCache',
    'TaskNotifier',
    
    # Utilities
    'format_datetime',
    'safe_divide', 
    'get_color_palette',
    'DashboardTemplate',
    
    # Data components
    'TaskRepository',
    'MetricsRepository', 
    'Task',
]