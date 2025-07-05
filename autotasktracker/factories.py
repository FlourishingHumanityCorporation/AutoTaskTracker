"""Factory functions for AutoTaskTracker.

Centralized object creation to reduce import coupling and enable easier refactoring.
Usage example:
    from autotasktracker.factories import create_database_manager
    db = create_database_manager()
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def create_database_manager(**kwargs) -> 'DatabaseManager':
    """Create DatabaseManager instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for DatabaseManager
        
    Returns:
        Configured DatabaseManager instance
    """
    from autotasktracker.core import DatabaseManager
    return DatabaseManager(**kwargs)


def create_activity_categorizer(**kwargs) -> 'ActivityCategorizer':
    """Create ActivityCategorizer instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for ActivityCategorizer
        
    Returns:
        Configured ActivityCategorizer instance
    """
    from autotasktracker.core import ActivityCategorizer
    return ActivityCategorizer(**kwargs)


def create_task_extractor(**kwargs) -> 'TaskExtractor':
    """Create TaskExtractor instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for TaskExtractor
        
    Returns:
        Configured TaskExtractor instance
    """
    from autotasktracker.core import TaskExtractor
    return TaskExtractor(**kwargs)


def create_time_tracker(**kwargs) -> 'TimeTracker':
    """Create TimeTracker instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for TimeTracker
        
    Returns:
        Configured TimeTracker instance
    """
    from autotasktracker.core import TimeTracker
    return TimeTracker(**kwargs)


def create_embeddings_search(**kwargs) -> 'EmbeddingsSearch':
    """Create EmbeddingsSearch instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for EmbeddingsSearch
        
    Returns:
        Configured EmbeddingsSearch instance
    """
    from autotasktracker.ai.embeddings_search import EmbeddingsSearch
    return EmbeddingsSearch(**kwargs)


def create_vlm_processor(**kwargs) -> 'VLMProcessor':
    """Create VLMProcessor instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for VLMProcessor
        
    Returns:
        Configured VLMProcessor instance
    """
    from autotasktracker.ai import VLMProcessor
    return VLMProcessor(**kwargs)


def create_performance_analyzer(**kwargs) -> 'PerformanceAnalyzer':
    """Create PerformanceAnalyzer instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for PerformanceAnalyzer
        
    Returns:
        Configured PerformanceAnalyzer instance
    """
    from autotasktracker.comparison.analysis.performance_analyzer import PerformanceAnalyzer
    return PerformanceAnalyzer(**kwargs)


def create_pensieve_api_client(**kwargs) -> 'PensieveAPIClient':
    """Create PensieveAPIClient instance with optional configuration.
    
    Args:
        **kwargs: Configuration options for PensieveAPIClient
        
    Returns:
        Configured PensieveAPIClient instance
    """
    from autotasktracker.pensieve.api_client import PensieveAPIClient
    return PensieveAPIClient(**kwargs)


# Factory registry for dynamic creation
FACTORY_REGISTRY = {
    'DatabaseManager': create_database_manager,
    'ActivityCategorizer': create_activity_categorizer,
    'TaskExtractor': create_task_extractor,
    'TimeTracker': create_time_tracker,
    'EmbeddingsSearch': create_embeddings_search,
    'VLMProcessor': create_vlm_processor,
    'PerformanceAnalyzer': create_performance_analyzer,
    'PensieveAPIClient': create_pensieve_api_client,
}


def create_service(service_name: str, **kwargs) -> Any:
    """Create service instance by name.
    
    Args:
        service_name: Name of service to create
        **kwargs: Configuration options
        
    Returns:
        Configured service instance
        
    Raises:
        ValueError: If service_name not found in registry
    """
    if service_name not in FACTORY_REGISTRY:
        available = ', '.join(FACTORY_REGISTRY.keys())
        raise ValueError(f"Unknown service '{service_name}'. Available: {available}")
    
    factory = FACTORY_REGISTRY[service_name]
    return factory(**kwargs)


def register_factory(service_name: str, factory_func) -> None:
    """Register custom factory function.
    
    Args:
        service_name: Name to register factory under
        factory_func: Factory function that returns service instance
    """
    FACTORY_REGISTRY[service_name] = factory_func
    logger.info(f"Registered factory for {service_name}")


def list_available_services() -> list:
    """Get list of available service names.
    
    Returns:
        List of available service names
    """
    return list(FACTORY_REGISTRY.keys())