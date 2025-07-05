"""Dashboard modules for AutoTaskTracker.

Barrel exports for dashboard components and utilities.
Reduces import overhead during refactoring.

Usage:
    from autotasktracker.dashboards import DashboardManager, TaskBoard, Analytics
"""

# Main dashboard functions  
from autotasktracker.dashboards.task_board import main as task_board_main
from autotasktracker.dashboards.analytics import main as analytics_main
from autotasktracker.dashboards.timetracker import main as timetracker_main
from autotasktracker.dashboards.launcher import main as launcher_main

# Dashboard components
from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.cache import DashboardCache
from autotasktracker.dashboards.notifications import TaskNotifier

# Utilities
from autotasktracker.dashboards.utils import format_datetime, safe_divide, get_color_palette
from autotasktracker.dashboards.templates import DashboardTemplate

# Data components
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository
from autotasktracker.dashboards.data.models import Task
# DatabaseManager import removed - not used in this module

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