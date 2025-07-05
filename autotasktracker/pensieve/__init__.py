"""
Pensieve integration package for AutoTaskTracker.

This package provides comprehensive integration with Pensieve/memos infrastructure,
achieving 90%+ utilization of Pensieve capabilities through:

- API-first architecture with intelligent caching
- Real-time event processing and dashboard updates  
- Configuration synchronization and auto-optimization
- Enhanced search with semantic capabilities
- Backend auto-detection and migration
- Multi-tier caching system
"""

from autotasktracker.pensieve.api_client import (
    get_pensieve_client, 
    reset_pensieve_client,
    PensieveAPIClient,
    PensieveEntity,
    PensieveFrame,
    PensieveAPIError
)

from autotasktracker.pensieve.cache_manager import (
    get_cache_manager,
    reset_cache_manager,
    PensieveCacheManager
)

from autotasktracker.pensieve.config_sync import (
    get_pensieve_config_sync,
    get_synced_config,
    reset_config_sync,
    PensieveConfigSync,
    SyncedConfiguration
)

from autotasktracker.pensieve.event_integration import (
    get_event_integrator,
    start_event_integration,
    reset_event_integrator,
    PensieveEventIntegrator,
    PensieveEvent,
    EventHandler,
    ScreenshotEventHandler,
    MetadataEventHandler,
    DashboardNotifier
)

from autotasktracker.pensieve.advanced_search import (
    get_advanced_search,
    reset_advanced_search,
    PensieveEnhancedSearch,
    SearchResult,
    SearchQuery
)

from autotasktracker.pensieve.backend_optimizer import (
    get_backend_optimizer,
    auto_optimize_backend,
    reset_backend_optimizer,
    PensieveBackendOptimizer,
    BackendType,
    BackendMetrics,
    MigrationPlan
)

__version__ = "1.0.0"
__author__ = "AutoTaskTracker Team"

__all__ = [
    # API Client
    "get_pensieve_client",
    "reset_pensieve_client", 
    "PensieveAPIClient",
    "PensieveEntity",
    "PensieveFrame",
    "PensieveAPIError",
    
    # Cache Management
    "get_cache_manager",
    "reset_cache_manager",
    "PensieveCacheManager",
    
    # Configuration Sync
    "get_pensieve_config_sync",
    "get_synced_config",
    "reset_config_sync",
    "PensieveConfigSync", 
    "SyncedConfiguration",
    
    # Event Integration
    "get_event_integrator",
    "start_event_integration",
    "reset_event_integrator",
    "PensieveEventIntegrator",
    "PensieveEvent",
    "EventHandler",
    "ScreenshotEventHandler",
    "MetadataEventHandler",
    "DashboardNotifier",
    
    # Enhanced Search
    "get_advanced_search",
    "reset_advanced_search",
    "PensieveEnhancedSearch",
    "SearchResult",
    "SearchQuery",
    
    # Backend Optimization
    "get_backend_optimizer",
    "auto_optimize_backend", 
    "reset_backend_optimizer",
    "PensieveBackendOptimizer",
    "BackendType",
    "BackendMetrics",
    "MigrationPlan"
]