"""AutoTaskTracker - AI-powered task discovery from screenshots.

Main barrel export providing easy access to core functionality.
This reduces import paths and simplifies refactoring.

Usage:
    from autotasktracker import DatabaseManager, TaskExtractor, VLMProcessor
    from autotasktracker.factories import create_database_manager
    from autotasktracker.interfaces import AbstractDatabaseManager
"""

__version__ = "0.1.0"

# Core functionality - most commonly used
from autotasktracker.core import (
    DatabaseManager, 
    get_default_db_manager,
    ActivityCategorizer, 
    categorize_activity, 
    extract_task_summary, 
    extract_window_title,
    TaskExtractor,
    TimeTracker
)

# Configuration
from autotasktracker.config import AutoTaskSettings, get_config

# AI capabilities - import directly to avoid circular imports
from autotasktracker.ai.vlm_processor import SmartVLMProcessor as VLMProcessor
from autotasktracker.ai import EmbeddingsSearchEngine as EmbeddingsSearch
from autotasktracker.ai import VLMTaskExtractor

# Factory pattern for easy object creation
from autotasktracker.factories import (
    create_database_manager,
    create_activity_categorizer,
    create_task_extractor,
    create_vlm_processor
)

# Interfaces for dependency injection - import directly to avoid issues
from autotasktracker.interfaces import AbstractDatabaseManager, AbstractTaskExtractor

__all__ = [
    # Core functionality
    'DatabaseManager',
    'get_default_db_manager',
    'ActivityCategorizer',
    'categorize_activity', 
    'extract_task_summary',
    'extract_window_title',
    'TaskExtractor',
    'TimeTracker',
    
    # Configuration
    'AutoTaskSettings',
    'get_config',
    
    # AI capabilities
    'VLMProcessor',
    'EmbeddingsSearch', 
    'VLMTaskExtractor',
    
    # Factory functions
    'create_database_manager',
    'create_activity_categorizer',
    'create_task_extractor',
    'create_vlm_processor',
    
    # Interfaces
    'AbstractDatabaseManager',
    'AbstractTaskExtractor',
]