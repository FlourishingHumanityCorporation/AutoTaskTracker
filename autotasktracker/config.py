"""
Centralized configuration module for AutoTaskTracker.
Manages all configuration settings, paths, and environment variables.

This module uses the unified Pydantic-based configuration system with advanced
features including hot-reloading, change monitoring, and Pensieve integration.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Use Pydantic configuration system
from autotasktracker.config_pydantic import AutoTaskSettings, get_pydantic_config
UNIFIED_AVAILABLE = False  # Unified system not implemented
UnifiedAutoTaskSettings = AutoTaskSettings  # Alias for compatibility
logger.info("📋 Using Pydantic configuration system")


def get_config():
    """Get the configuration instance.
    
    This is the main configuration function used throughout the application.
    Returns a type-safe, validated configuration with environment variable support.
    
    Returns:
        AutoTaskSettings: Validated Pydantic configuration instance
        
    Raises:
        ValidationError: If configuration validation fails
    """
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
            },
            'vlm_config': {
                'model': config.vlm.model,
                'port': config.vlm.port,
                'cache_dir': config.vlm.cache_dir
            },
            'embedding_config': {
                'model': config.embedding.model,
                'dimension': config.embedding.dimension
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


def get_typed_config() -> UnifiedAutoTaskSettings:
    """Get the unified configuration instance.
    
    Alias for get_config() for backward compatibility.
    
    Returns:
        UnifiedAutoTaskSettings: Validated unified configuration instance
    """
    return get_config()


def reload_config():
    """Reload configuration from environment variables and sources.
    
    This function forces a fresh reload of the configuration system.
    
    Returns:
        AutoTaskSettings: Configuration instance after reload
    """
    from autotasktracker.config_pydantic import reset_pydantic_config
    reset_pydantic_config()
    return get_config()


def reset_config() -> None:
    """Reset configuration to force reload on next access.
    
    This function resets the configuration singleton to force
    a fresh reload from environment variables and configuration files.
    """
    from autotasktracker.config_pydantic import reset_pydantic_config
    reset_pydantic_config()


def start_config_monitoring(check_interval: int = 60) -> bool:
    """Start configuration monitoring for hot-reloading.
    
    Args:
        check_interval: How often to check for changes in seconds (default: 60)
        
    Returns:
        bool: True if monitoring started, False if not available
    """
    if UNIFIED_AVAILABLE:
        try:
            config_manager = get_config_manager()
            config_manager.start_monitoring(check_interval)
            logger.info(f"🔥 Configuration hot-reloading started (interval: {check_interval}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to start configuration monitoring: {e}")
            return False
    else:
        logger.warning("Configuration monitoring not available - unified system required")
        return False


def stop_config_monitoring() -> bool:
    """Stop configuration monitoring.
    
    Returns:
        bool: True if monitoring stopped, False if not available
    """
    if UNIFIED_AVAILABLE:
        try:
            config_manager = get_config_manager()
            config_manager.stop_monitoring()
            logger.info("Configuration monitoring stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop configuration monitoring: {e}")
            return False
    else:
        return False


def add_config_change_listener(listener_func) -> bool:
    """Add a listener for configuration changes.
    
    Args:
        listener_func: Function to call when configuration changes
        
    Returns:
        bool: True if listener added, False if not available
    """
    if UNIFIED_AVAILABLE:
        try:
            config_manager = get_config_manager()
            config_manager.add_change_listener(listener_func)
            logger.info("Configuration change listener added")
            return True
        except Exception as e:
            logger.error(f"Failed to add configuration change listener: {e}")
            return False
    else:
        logger.warning("Configuration change listeners not available - unified system required")
        return False


def initialize_pensieve_integration() -> bool:
    """Initialize advanced Pensieve integration features.
    
    Returns:
        bool: True if integration successful, False otherwise
    """
    try:
        from autotasktracker.pensieve.config_integration import initialize_pensieve_integration
        return initialize_pensieve_integration()
    except ImportError:
        logger.warning("Pensieve integration module not available")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Pensieve integration: {e}")
        return False


def get_pensieve_features() -> dict:
    """Get detected Pensieve features and their status.
    
    Returns:
        dict: Features and their availability status
    """
    try:
        from autotasktracker.pensieve.config_integration import get_pensieve_integrator
        integrator = get_pensieve_integrator()
        return integrator.get_integration_status()
    except ImportError:
        logger.warning("Pensieve integration module not available")
        return {}
    except Exception as e:
        logger.error(f"Failed to get Pensieve features: {e}")
        return {}


def optimize_for_pensieve() -> dict:
    """Optimize AutoTaskTracker configuration for detected Pensieve features.
    
    Returns:
        dict: Applied optimizations
    """
    try:
        from autotasktracker.pensieve.config_integration import get_pensieve_integrator
        integrator = get_pensieve_integrator()
        return integrator.optimize_autotask_for_pensieve()
    except ImportError:
        logger.warning("Pensieve integration module not available")
        return {}
    except Exception as e:
        logger.error(f"Failed to optimize for Pensieve: {e}")
        return {}


def start_config_event_system() -> bool:
    """Start the configuration event system for real-time updates.
    
    Returns:
        bool: True if started successfully, False otherwise
    """
    try:
        from autotasktracker.core.config_events import start_config_event_system
        start_config_event_system()
        logger.info("🔄 Configuration event system started")
        return True
    except ImportError:
        logger.warning("Configuration event system not available")
        return False
    except Exception as e:
        logger.error(f"Failed to start configuration event system: {e}")
        return False


def stop_config_event_system() -> bool:
    """Stop the configuration event system.
    
    Returns:
        bool: True if stopped successfully, False otherwise
    """
    try:
        from autotasktracker.core.config_events import stop_config_event_system
        stop_config_event_system()
        logger.info("Configuration event system stopped")
        return True
    except ImportError:
        return False
    except Exception as e:
        logger.error(f"Failed to stop configuration event system: {e}")
        return False


def emit_config_change_event(key: str, old_value: Any, new_value: Any, source: str = "system") -> bool:
    """Emit a configuration change event.
    
    Args:
        key: Configuration key that changed
        old_value: Previous value
        new_value: New value
        source: Source of the change
        
    Returns:
        bool: True if event emitted successfully
    """
    try:
        from autotasktracker.core.config_events import emit_config_event
        emit_config_event("config_changed", key, old_value, new_value, source)
        return True
    except ImportError:
        return False
    except Exception as e:
        logger.error(f"Failed to emit configuration event: {e}")
        return False


def register_config_event_handler(handler) -> bool:
    """Register a custom configuration event handler.
    
    Args:
        handler: Event handler instance or function
        
    Returns:
        bool: True if registered successfully
    """
    try:
        from autotasktracker.core.config_events import get_config_event_bus
        bus = get_config_event_bus()
        
        if hasattr(handler, 'handle_event'):
            bus.register_handler(handler)
        else:
            bus.register_async_handler(handler)
        
        logger.info("Configuration event handler registered")
        return True
    except ImportError:
        logger.warning("Configuration event system not available")
        return False
    except Exception as e:
        logger.error(f"Failed to register event handler: {e}")
        return False


def run_config_health_check() -> dict:
    """Run comprehensive configuration health check.
    
    Returns:
        dict: Health report with metrics and status
    """
    try:
        from autotasktracker.core.config_health import run_config_health_check
        report = run_config_health_check()
        return report.to_dict()
    except ImportError:
        logger.warning("Configuration health monitoring not available")
        return {"status": "unknown", "message": "Health monitoring not available"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": f"Health check failed: {e}"}


def get_config_health_status() -> dict:
    """Get current configuration health status.
    
    Returns:
        dict: Current health status and metrics
    """
    try:
        from autotasktracker.core.config_health import get_config_health_status
        return get_config_health_status()
    except ImportError:
        logger.warning("Configuration health monitoring not available")
        return {"status": "unknown", "message": "Health monitoring not available"}
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        return {"status": "error", "message": f"Failed to get health status: {e}"}


def get_config_metrics() -> dict:
    """Get configuration performance and health metrics.
    
    Returns:
        dict: Configuration metrics for monitoring
    """
    try:
        from autotasktracker.core.config_health import get_config_health_monitor
        monitor = get_config_health_monitor()
        return monitor.export_health_metrics()
    except ImportError:
        logger.warning("Configuration health monitoring not available")
        return {}
    except Exception as e:
        logger.error(f"Failed to get config metrics: {e}")
        return {}


def get_comprehensive_config_status() -> dict:
    """Get comprehensive configuration status including all systems.
    
    Returns:
        dict: Complete configuration system status
    """
    status = {
        'timestamp': datetime.now().isoformat(),
        'configuration': {},
        'health': {},
        'pensieve': {},
        'monitoring': {},
        'events': {}
    }
    
    try:
        # Basic configuration status
        config = get_config()
        status['configuration'] = {
            'type': type(config).__name__,
            'unified_available': UNIFIED_AVAILABLE,
            'validation': validate_current_config()
        }
        
        # Health status
        status['health'] = get_config_health_status()
        
        # Pensieve features
        status['pensieve'] = get_pensieve_features()
        
        # Monitoring status
        status['monitoring'] = {
            'hot_reload_available': UNIFIED_AVAILABLE,
            'event_system_available': True,
            'metrics_available': True
        }
        
        # Events status
        try:
            from autotasktracker.core.config_events import get_config_event_bus
            bus = get_config_event_bus()
            status['events'] = {
                'handlers_registered': len(bus._handlers) if hasattr(bus, '_handlers') else 0,
                'processing_active': getattr(bus, '_running', False)
            }
        except Exception:
            status['events'] = {'available': False}
        
        logger.info("Comprehensive configuration status retrieved")
        return status
        
    except Exception as e:
        logger.error(f"Failed to get comprehensive status: {e}")
        status['error'] = str(e)
        return status


# Legacy alias for backwards compatibility
# This allows existing code to continue working without changes
config = get_config()


# Export key functions and classes for easy importing
__all__ = [
    'get_config',
    'validate_current_config', 
    'get_typed_config',
    'reload_config',
    'reset_config',
    'start_config_monitoring',
    'stop_config_monitoring', 
    'add_config_change_listener',
    'initialize_pensieve_integration',
    'get_pensieve_features',
    'optimize_for_pensieve',
    'start_config_event_system',
    'stop_config_event_system',
    'emit_config_change_event',
    'register_config_event_handler',
    'run_config_health_check',
    'get_config_health_status',
    'get_config_metrics',
    'get_comprehensive_config_status',
    'UnifiedAutoTaskSettings',
    'AutoTaskSettings',
    'config'  # Legacy alias
]