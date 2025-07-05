"""Dashboard modules for AutoTaskTracker.

Barrel exports for dashboard components and utilities.
Reduces import overhead during refactoring.

Usage:
    from autotasktracker.dashboards import DashboardManager, TaskBoard, Analytics
"""

# Main dashboard functions  
from .task_board import main as task_board_main
from .analytics import main as analytics_main
from .timetracker import main as timetracker_main
from .launcher import main as launcher_main

# Dashboard components
from .base import BaseDashboard
from .cache import DashboardCache
from .notifications import TaskNotifier

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