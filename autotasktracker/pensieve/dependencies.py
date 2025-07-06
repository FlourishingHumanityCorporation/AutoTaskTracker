"""
Centralized dependency management for Pensieve modules.
Provides lazy loading utilities to break circular import dependencies.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class PensieveDependencies:
    """Centralized dependency manager for Pensieve modules."""
    
    def __init__(self):
        self._database_manager = None
        self._cache_manager = None
        self._task_extractor = None
    
    def get_database_manager(self):
        """Get DatabaseManager instance with lazy loading."""
        if self._database_manager is None:
            try:
                from autotasktracker.core import DatabaseManager
                self._database_manager = DatabaseManager()
                logger.debug("Lazy loaded DatabaseManager")
            except ImportError as e:
                logger.error(f"Failed to import DatabaseManager: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize DatabaseManager: {e}")
                raise
        return self._database_manager
    
    def get_cache_manager(self):
        """Get cache manager instance with lazy loading."""
        if self._cache_manager is None:
            try:
                from autotasktracker.pensieve.cache_manager import get_cache_manager
                self._cache_manager = get_cache_manager()
                logger.debug("Lazy loaded cache manager")
            except ImportError as e:
                logger.debug(f"Cache manager not available: {e}")
                return None
            except Exception as e:
                logger.warning(f"Failed to initialize cache manager: {e}")
                return None
        return self._cache_manager
    
    def get_task_extractor(self):
        """Get task extractor instance with lazy loading."""
        if self._task_extractor is None:
            try:
                from autotasktracker.core import TaskExtractor
                self._task_extractor = TaskExtractor()
                logger.debug("Lazy loaded TaskExtractor")
            except ImportError as e:
                logger.error(f"Failed to import TaskExtractor: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize TaskExtractor: {e}")
                raise
        return self._task_extractor
    
    def set_database_manager(self, db_manager):
        """Inject a specific DatabaseManager instance."""
        self._database_manager = db_manager
        logger.debug("Injected DatabaseManager instance")
    
    def set_cache_manager(self, cache_manager):
        """Inject a specific cache manager instance."""
        self._cache_manager = cache_manager
        logger.debug("Injected cache manager instance")
    
    def set_task_extractor(self, task_extractor):
        """Inject a specific TaskExtractor instance."""
        self._task_extractor = task_extractor
        logger.debug("Injected TaskExtractor instance")
    
    def reset(self):
        """Reset all dependencies (useful for testing)."""
        self._database_manager = None
        self._cache_manager = None
        self._task_extractor = None
        logger.debug("Reset all dependencies")


# Global dependency registry
_dependencies = PensieveDependencies()


def get_dependencies() -> PensieveDependencies:
    """Get the global dependency registry."""
    return _dependencies


def reset_dependencies():
    """Reset the global dependency registry (useful for testing)."""
    global _dependencies
    _dependencies.reset()


# Convenience functions for common dependencies
def get_database_manager():
    """Get DatabaseManager instance (convenience function)."""
    return get_dependencies().get_database_manager()


def get_cache_manager():
    """Get cache manager instance (convenience function)."""
    return get_dependencies().get_cache_manager()


def get_task_extractor():
    """Get TaskExtractor instance (convenience function)."""
    return get_dependencies().get_task_extractor()