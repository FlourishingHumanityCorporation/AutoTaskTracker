"""Data repositories for dashboard data access.

This module now imports from the refactored modular structure while maintaining
backward compatibility. The original monolithic implementation has been split
into focused modules:

- core/: Base infrastructure (BaseRepository, CacheCoordinator, CircuitBreaker, QueryRouter)
- task/: Task-related data access (TaskRepository)  
- activity/: Activity/screenshot data access (ActivityRepository)
- metrics/: Analytics and metrics data access (MetricsRepository)
"""

import logging

# Import from new modular structure
from autotasktracker.dashboards.data.core.base_repository import BaseRepository
from autotasktracker.dashboards.data.task.task_repository import TaskRepository
from autotasktracker.dashboards.data.activity.activity_repository import ActivityRepository
from autotasktracker.dashboards.data.metrics.metrics_repository import MetricsRepository

logger = logging.getLogger(__name__)

# Legacy compatibility - re-export all classes
__all__ = [
    'BaseRepository',
    'TaskRepository',
    'ActivityRepository', 
    'MetricsRepository'
]

logger.info("Repository modules loaded from refactored modular structure")