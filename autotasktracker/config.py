"""
Centralized configuration module for AutoTaskTracker.
Manages all configuration settings, paths, and environment variables.

This module now uses Pydantic-based configuration exclusively for type safety,
validation, and modern environment variable support.
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import Pydantic config
try:
    from autotasktracker.config_pydantic import AutoTaskSettings, get_pydantic_config
    PYDANTIC_AVAILABLE = True
    logger.debug("Pydantic configuration loaded successfully")
except ImportError as e:
    PYDANTIC_AVAILABLE = False
    logger.error(f"Pydantic configuration not available: {e}")
    raise ImportError("Pydantic configuration is required but not available") from e


def get_config() -> AutoTaskSettings:
    """Get the Pydantic configuration instance.
    
    This is the main configuration function used throughout the application.
    Returns a type-safe, validated configuration with environment variable support.
    
    Returns:
        AutoTaskSettings: Validated Pydantic configuration instance
        
    Raises:
        ImportError: If Pydantic configuration is not available
        ValidationError: If configuration validation fails
    """
    if not PYDANTIC_AVAILABLE:
        raise ImportError("Pydantic configuration is required but not available")
    
    return get_pydantic_config()


def validate_current_config() -> Dict[str, Any]:
    """Validate the current configuration and return detailed results.
    
    Returns:
        Dict containing validation results and configuration details
    """
    try:
        config = get_config()
        
        return {
            'validation_passed': True,
            'config_type': type(config).__name__,
            'database_path': config.database.path,
            'ports': {
                'memos': config.server.memos_port,
                'task_board': config.server.task_board_port,
                'analytics': config.server.analytics_port,
                'timetracker': config.server.timetracker_port,
                'notifications': config.server.notifications_port,
                'daily_summary': config.server.daily_summary_port,
            },
            'vlm_config': {
                'model': config.vlm.model,
                'port': config.vlm.port,
                'cache_dir': config.vlm.cache_dir
            },
            'debug_mode': config.debug,
            'pensieve_integration': config.use_pensieve_api
        }
        
    except Exception as e:
        return {
            'validation_passed': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


def get_typed_config() -> AutoTaskSettings:
    """Get the Pydantic-typed configuration.
    
    Alias for get_config() for backward compatibility.
    
    Returns:
        AutoTaskSettings: Validated Pydantic configuration instance
    """
    return get_config()


def reset_config() -> None:
    """Reset configuration to force reload on next access.
    
    This function resets the Pydantic configuration singleton to force
    a fresh reload from environment variables and configuration files.
    """
    from autotasktracker.config_pydantic import reset_pydantic_config
    reset_pydantic_config()


# Legacy alias for backwards compatibility
# This allows existing code to continue working without changes
config = get_config()


# Export key functions and classes for easy importing
__all__ = [
    'get_config',
    'validate_current_config', 
    'get_typed_config',
    'reset_config',
    'AutoTaskSettings',
    'config'  # Legacy alias
]