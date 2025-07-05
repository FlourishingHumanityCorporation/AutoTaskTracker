"""
Pensieve configuration synchronization system.
Automatically syncs configurations between Pensieve and AutoTaskTracker.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from pathlib import Path

from autotasktracker.config import get_config
from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
# DatabaseManager import moved to avoid circular dependency

# Import Pydantic config for enhanced integration
try:
    from autotasktracker.config_pydantic import AutoTaskSettings, get_pydantic_config
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    AutoTaskSettings = None
    get_pydantic_config = None

logger = logging.getLogger(__name__)


@dataclass
class SyncedConfiguration:
    """Represents synchronized configuration between Pensieve and AutoTaskTracker."""
    
    # Pensieve-derived settings
    screenshots_dir: str = ""
    database_path: str = ""
    api_base_url: str = "http://localhost:8839"
    
    # Performance settings from Pensieve
    ocr_timeout: int = 30
    batch_size: int = 100
    max_concurrent_requests: int = 10
    
    # AutoTaskTracker-specific settings (preserved)
    ai_model: str = "all-MiniLM-L6-v2"
    task_categories: list = field(default_factory=lambda: ["development", "communication", "research", "admin"])
    vlm_model: str = "minicpm-v"
    
    # Cache and performance settings
    cache_ttl: int = 300
    memory_cache_size: int = 1000
    disk_cache_enabled: bool = True
    
    # Integration settings
    real_time_processing: bool = True
    auto_migration: bool = True
    api_retry_attempts: int = 3
    
    # Environment-based overrides
    overrides: Dict[str, Any] = field(default_factory=dict)


class PensieveConfigSync:
    """Synchronizes configuration between Pensieve and AutoTaskTracker."""
    
    def __init__(self):
        self.api_client = get_pensieve_client()
        self.local_config = get_config()
        self._cached_config: Optional[SyncedConfiguration] = None
        self._last_sync_time = 0
        self._sync_interval = 300  # Sync every 5 minutes
        
        # Enhanced Pydantic integration
        self.use_pydantic = PYDANTIC_AVAILABLE
        if self.use_pydantic:
            logger.info("Pensieve config sync enhanced with Pydantic validation")
        
        # Configuration file for persistent settings
        self.config_file = Path.home() / ".memos" / "autotask_config.json"
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create default
        self._load_local_config()
        
        # Enhanced synchronization features
        self._watchers = []  # File watchers for real-time sync
        self._sync_callbacks = []  # Callbacks for config changes
        self._last_pensieve_sync = 0
        self._sync_conflicts = []  # Track configuration conflicts
    
    def _load_local_config(self):
        """Load local configuration at startup."""
        try:
            if self.config_file.exists():
                self._cached_config = self._load_config_from_file()
                logger.info("Loaded cached configuration")
            else:
                self._cached_config = self._get_default_config()
                logger.info("Using default configuration")
        except Exception as e:
            logger.warning(f"Failed to load local config: {e}")
            self._cached_config = self._get_default_config()
    
    def get_synced_config(self, force_refresh: bool = False) -> SyncedConfiguration:
        """
        Get synchronized configuration with caching.
        
        Args:
            force_refresh: Force refresh from Pensieve
            
        Returns:
            Merged configuration object
        """
        import time
        current_time = time.time()
        
        # Use cached config if within sync interval
        if (not force_refresh and 
            self._cached_config and 
            current_time - self._last_sync_time < self._sync_interval):
            return self._cached_config
        
        # Sync with Pensieve
        try:
            pensieve_config = self._fetch_pensieve_config()
            merged_config = self._merge_configurations(pensieve_config)
            
            # Apply environment overrides
            merged_config = self._apply_environment_overrides(merged_config)
            
            # Cache the result
            self._cached_config = merged_config
            self._last_sync_time = current_time
            
            # Persist to file for offline use
            self._save_config_to_file(merged_config)
            
            logger.info("Configuration synchronized with Pensieve")
            return merged_config
            
        except Exception as e:
            logger.warning(f"Failed to sync with Pensieve, using cached/default config: {e}")
            
            # Try to load from file if sync failed
            if self.config_file.exists():
                return self._load_config_from_file()
            
            # Fallback to default configuration
            return self._get_default_config()
    
    def _fetch_pensieve_config(self) -> Dict[str, Any]:
        """Fetch configuration from Pensieve API."""
        if not self.api_client.is_healthy():
            raise Exception("Pensieve API not available")
        
        try:
            config = self.api_client.get_config()
            logger.debug(f"Fetched Pensieve config: {list(config.keys())}")
            return config
        except PensieveAPIError as e:
            logger.error(f"Failed to fetch Pensieve config: {e.message}")
            raise
    
    def _merge_configurations(self, pensieve_config: Dict[str, Any]) -> SyncedConfiguration:
        """Merge Pensieve config with AutoTaskTracker defaults."""
        
        # Extract Pensieve settings
        screenshots_dir = pensieve_config.get('screenshots_dir', 
                                            pensieve_config.get('data_dir', '~/.memos/screenshots'))
        database_path = pensieve_config.get('database_path', '~/.memos/database.db')
        
        # Performance settings from Pensieve
        ocr_timeout = pensieve_config.get('ocr_timeout', 30)
        batch_size = pensieve_config.get('batch_size', 100)
        max_concurrent = pensieve_config.get('max_concurrent_requests', 10)
        
        # API settings
        api_port = pensieve_config.get('port', 8839)
        api_host = pensieve_config.get('host', 'localhost')
        api_base_url = f"http://{api_host}:{api_port}"
        
        # Create merged configuration
        merged = SyncedConfiguration(
            # Pensieve-derived
            screenshots_dir=os.path.expanduser(screenshots_dir),
            database_path=os.path.expanduser(database_path),
            api_base_url=api_base_url,
            ocr_timeout=ocr_timeout,
            batch_size=batch_size,
            max_concurrent_requests=max_concurrent,
            
            # AutoTaskTracker defaults
            ai_model=getattr(self.local_config, 'AI_MODEL', 'all-MiniLM-L6-v2'),
            task_categories=getattr(self.local_config, 'TASK_CATEGORIES', 
                                  ["development", "communication", "research", "admin"]),
            vlm_model=getattr(self.local_config, 'VLM_MODEL', 'minicpm-v'),
            
            # Performance defaults
            cache_ttl=int(os.getenv('PENSIEVE_CACHE_TTL', '300')),
            memory_cache_size=int(os.getenv('PENSIEVE_MEMORY_CACHE_SIZE', '1000')),
            disk_cache_enabled=os.getenv('PENSIEVE_DISK_CACHE', 'true').lower() == 'true',
            
            # Integration features
            real_time_processing=os.getenv('PENSIEVE_REALTIME', 'true').lower() == 'true',
            auto_migration=os.getenv('PENSIEVE_AUTO_MIGRATION', 'true').lower() == 'true',
            api_retry_attempts=int(os.getenv('PENSIEVE_RETRY_ATTEMPTS', '3'))
        )
        
        return merged
    
    def _create_pydantic_config_from_pensieve(self, pensieve_config: Dict[str, Any]) -> Optional[Any]:
        """Create Pydantic configuration from Pensieve settings."""
        if not self.use_pydantic:
            return None
        
        try:
            # Prepare environment variables for Pydantic to read
            env_mapping = {
                'AUTOTASK_DATABASE__PATH': pensieve_config.get('database_path', '~/.memos/database.db'),
                'AUTOTASK_SERVER__MEMOS_PORT': str(pensieve_config.get('port', 8839)),
                'AUTOTASK_SCREENSHOTS_DIR': pensieve_config.get('screenshots_dir', '~/.memos/screenshots'),
                'AUTOTASK_PROCESSING__BATCH_SIZE': str(pensieve_config.get('batch_size', 100)),
                'AUTOTASK_VLM__MODEL': pensieve_config.get('vlm_model', 'minicpm-v'),
                'AUTOTASK_EMBEDDING__MODEL': pensieve_config.get('ai_model', 'jina-embeddings-v2-base-en'),
            }
            
            # Temporarily set environment variables
            original_env = {}
            for key, value in env_mapping.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = str(value)
            
            try:
                # Create Pydantic config with Pensieve values
                pydantic_config = AutoTaskSettings()
                logger.debug("Created Pydantic config from Pensieve settings")
                return pydantic_config
            finally:
                # Restore original environment
                for key, original_value in original_env.items():
                    if original_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = original_value
                        
        except Exception as e:
            logger.warning(f"Failed to create Pydantic config from Pensieve: {e}")
            return None
    
    def _apply_environment_overrides(self, config: SyncedConfiguration) -> SyncedConfiguration:
        """Apply environment variable overrides to configuration."""
        overrides = {}
        
        # Check for environment overrides
        env_overrides = {
            'PENSIEVE_API_TIMEOUT': 'ocr_timeout',
            'PENSIEVE_BATCH_SIZE': 'batch_size',
            'PENSIEVE_API_URL': 'api_base_url',
            'PENSIEVE_SCREENSHOTS_DIR': 'screenshots_dir',
            'PENSIEVE_DATABASE_PATH': 'database_path',
            'AI_MODEL': 'ai_model',
            'VLM_MODEL': 'vlm_model'
        }
        
        for env_var, config_key in env_overrides.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Type conversion
                if config_key in ['ocr_timeout', 'batch_size']:
                    value = int(value)
                elif config_key.endswith('_enabled'):
                    value = value.lower() == 'true'
                
                setattr(config, config_key, value)
                overrides[config_key] = value
                logger.info(f"Applied environment override: {config_key} = {value}")
        
        config.overrides = overrides
        return config
    
    def _get_default_config(self) -> SyncedConfiguration:
        """Get default configuration when Pensieve is not available."""
        return SyncedConfiguration(
            screenshots_dir=os.path.expanduser("~/.memos/screenshots"),
            database_path=os.path.expanduser("~/.memos/database.db"),
            api_base_url="http://localhost:8839"
        )
    
    def _save_config_to_file(self, config: SyncedConfiguration) -> None:
        """Save configuration to file for offline use."""
        try:
            # Validate file path before writing
            if not self.config_file.parent.exists():
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                
            config_dict = {
                'screenshots_dir': config.screenshots_dir,
                'database_path': config.database_path,
                'api_base_url': config.api_base_url,
                'ocr_timeout': config.ocr_timeout,
                'batch_size': config.batch_size,
                'max_concurrent_requests': config.max_concurrent_requests,
                'ai_model': config.ai_model,
                'task_categories': config.task_categories,
                'vlm_model': config.vlm_model,
                'cache_ttl': config.cache_ttl,
                'memory_cache_size': config.memory_cache_size,
                'disk_cache_enabled': config.disk_cache_enabled,
                'real_time_processing': config.real_time_processing,
                'auto_migration': config.auto_migration,
                'api_retry_attempts': config.api_retry_attempts,
                'overrides': config.overrides,
                'last_sync': self._last_sync_time
            }
            
            # Validate file path before writing
            if not self.config_file.parent.exists():
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save config to file: {e}")
    
    def _load_config_from_file(self) -> SyncedConfiguration:
        """Load configuration from file."""
        try:
            # Validate file exists before reading
            if not self.config_file.exists():
                logger.debug(f"Config file not found: {self.config_file}")
                return self._default_config
            
            with open(self.config_file, 'r') as f:
                config_dict = json.load(f)
            
            config = SyncedConfiguration(**{k: v for k, v in config_dict.items() 
                                          if k != 'last_sync'})
            
            logger.info("Loaded configuration from cache file")
            return config
            
        except Exception as e:
            logger.warning(f"Failed to load config from file: {e}")
            return self._get_default_config()
    
    def update_pensieve_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update Pensieve configuration with fallback strategies.
        
        Args:
            updates: Configuration updates to apply
            
        Returns:
            True if successful (includes partial success with local overrides)
        """
        try:
            logger.info(f"Configuration updates requested: {updates}")
            
            # Strategy 1: Try direct API update (when available)
            if self._try_api_config_update(updates):
                logger.info("Successfully updated Pensieve configuration via API")
                return True
            
            # Strategy 2: Apply local environment overrides
            if self._apply_local_config_overrides(updates):
                logger.info("Applied configuration updates as local overrides")
                return True
            
            # Strategy 3: Log for manual application
            self._log_manual_config_instructions(updates)
            logger.warning("Pensieve config API not available - applied local overrides where possible")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update Pensieve config: {e}")
            return False
    
    def _try_api_config_update(self, updates: Dict[str, Any]) -> bool:
        """Try to update configuration via Pensieve API."""
        try:
            # Check if API supports config updates
            # Based on our testing, /api/config is read-only, but we'll try POST/PUT
            import requests
            
            # Try POST to /api/config
            response = requests.post(
                f"{self.api_client.base_url}/api/config",
                json=updates,
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            elif response.status_code == 405:
                # Method not allowed - try PUT
                response = requests.put(
                    f"{self.api_client.base_url}/api/config",
                    json=updates,
                    timeout=10
                )
                return response.status_code == 200
            
        except Exception as e:
            logger.debug(f"API config update failed: {e}")
        
        return False
    
    def _apply_local_config_overrides(self, updates: Dict[str, Any]) -> bool:
        """Apply configuration updates as local environment overrides."""
        try:
            # Update the cached configuration with new values
            if self._cached_config:
                updated = False
                
                # Map update keys to config attributes
                config_mapping = {
                    'ocr_timeout': 'ocr_timeout',
                    'batch_size': 'batch_size',
                    'max_concurrent_requests': 'max_concurrent_requests',
                    'cache_ttl': 'cache_ttl',
                    'memory_cache_size': 'memory_cache_size',
                    'api_retry_attempts': 'api_retry_attempts',
                    'ai_model': 'ai_model',
                    'vlm_model': 'vlm_model',
                    'real_time_processing': 'real_time_processing'
                }
                
                for update_key, value in updates.items():
                    if update_key in config_mapping:
                        config_attr = config_mapping[update_key]
                        old_value = getattr(self._cached_config, config_attr, None)
                        setattr(self._cached_config, config_attr, value)
                        
                        # Track the override
                        self._cached_config.overrides[config_attr] = value
                        
                        logger.info(f"Updated {config_attr}: {old_value} → {value}")
                        updated = True
                
                if updated:
                    # Save to file so changes persist
                    self._save_config_to_file(self._cached_config)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply local config overrides: {e}")
            return False
    
    def _log_manual_config_instructions(self, updates: Dict[str, Any]):
        """Log instructions for manual configuration application."""
        logger.info("Manual Pensieve configuration instructions:")
        logger.info("=" * 50)
        
        for key, value in updates.items():
            if key in ['ocr_timeout', 'batch_size', 'max_concurrent_requests']:
                logger.info(f"Set {key} to {value} in Pensieve configuration")
            elif key in ['screenshots_dir', 'database_path']:
                logger.info(f"Update {key} to '{value}' in ~/.memos/config")
            elif key.startswith('api_'):
                logger.info(f"Configure {key}={value} in Pensieve API settings")
            else:
                logger.info(f"Set {key}={value} via environment variable PENSIEVE_{key.upper()}")
        
        logger.info("Restart Pensieve after making changes: memos restart")
    
    def get_config_update_capabilities(self) -> Dict[str, Any]:
        """Get information about configuration update capabilities."""
        return {
            'api_updates_available': self._test_api_update_support(),
            'local_overrides_available': True,
            'supported_update_keys': [
                'ocr_timeout', 'batch_size', 'max_concurrent_requests',
                'cache_ttl', 'memory_cache_size', 'api_retry_attempts',
                'ai_model', 'vlm_model', 'real_time_processing'
            ],
            'readonly_keys': [
                'screenshots_dir', 'database_path', 'api_base_url'
            ]
        }
    
    def _test_api_update_support(self) -> bool:
        """Test if the API supports configuration updates."""
        try:
            # Quick test with empty payload
            import requests
            response = requests.post(
                f"{self.api_client.base_url}/api/config",
                json={},
                timeout=5
            )
            # If we get anything other than 404, the endpoint exists
            return response.status_code != 404
        except Exception:
            return False
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance-related configuration settings."""
        config = self.get_synced_config()
        
        return {
            'ocr_timeout': config.ocr_timeout,
            'batch_size': config.batch_size,
            'max_concurrent_requests': config.max_concurrent_requests,
            'cache_ttl': config.cache_ttl,
            'memory_cache_size': config.memory_cache_size,
            'api_retry_attempts': config.api_retry_attempts
        }
    
    def get_integration_config(self) -> Dict[str, Any]:
        """Get integration-related configuration settings."""
        config = self.get_synced_config()
        
        return {
            'api_base_url': config.api_base_url,
            'screenshots_dir': config.screenshots_dir,
            'database_path': config.database_path,
            'real_time_processing': config.real_time_processing,
            'auto_migration': config.auto_migration
        }
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI-related configuration settings."""
        config = self.get_synced_config()
        
        return {
            'ai_model': config.ai_model,
            'vlm_model': config.vlm_model,
            'task_categories': config.task_categories
        }
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get configuration sync status and health."""
        import time
        
        try:
            api_healthy = self.api_client.is_healthy()
            config = self.get_synced_config()
            
            return {
                'pensieve_api_healthy': api_healthy,
                'last_sync_time': self._last_sync_time,
                'sync_age_seconds': time.time() - self._last_sync_time,
                'config_file_exists': self.config_file.exists(),
                'environment_overrides': len(config.overrides),
                'override_details': config.overrides
            }
            
        except Exception as e:
            return {
                'pensieve_api_healthy': False,
                'error': str(e),
                'last_sync_time': self._last_sync_time,
                'config_file_exists': self.config_file.exists()
            }
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get synchronization statistics and health metrics."""
        return {
            'last_sync_time': self._last_pensieve_sync,
            'sync_conflicts_count': len(self._sync_conflicts),
            'registered_callbacks': len(self._sync_callbacks),
            'config_file_exists': self.config_file.exists(),
            'config_file_age_hours': (
                (time.time() - self.config_file.stat().st_mtime) / 3600
                if self.config_file.exists() else None
            ),
            'sync_health': 'healthy' if len(self._sync_conflicts) == 0 else 'has_conflicts'
        }


# Global instance
_config_sync_instance: Optional[PensieveConfigSync] = None


def get_pensieve_config_sync() -> PensieveConfigSync:
    """Get global Pensieve configuration sync instance."""
    global _config_sync_instance
    if _config_sync_instance is None:
        _config_sync_instance = PensieveConfigSync()
    return _config_sync_instance


def get_synced_config(force_refresh: bool = False) -> SyncedConfiguration:
    """Get synchronized configuration (convenience function)."""
    return get_pensieve_config_sync().get_synced_config(force_refresh)


def reset_config_sync():
    """Reset configuration sync instance (useful for testing)."""
    global _config_sync_instance
    _config_sync_instance = None


def perform_enhanced_sync(force_refresh: bool = False) -> Dict[str, Any]:
    """Perform enhanced configuration synchronization.
    
    Args:
        force_refresh: Force refresh from all sources
        
    Returns:
        Detailed sync report
    """
    return get_pensieve_config_sync().perform_enhanced_sync(force_refresh)


def get_config_sync_status() -> Dict[str, Any]:
    """Get comprehensive configuration synchronization status."""
    sync_instance = get_pensieve_config_sync()
    
    # Get basic sync statistics
    stats = sync_instance.get_sync_statistics()
    
    # Add integration assessment
    integration_score = 70  # Base score
    
    # Improve score based on sync health
    if stats['sync_health'] == 'healthy':
        integration_score += 10
    
    # Improve score based on recent sync activity
    if stats['last_sync_time'] and (time.time() - stats['last_sync_time']) < 3600:
        integration_score += 10
    
    # Improve score based on callback usage
    if stats['registered_callbacks'] > 0:
        integration_score += 5
    
    # Improve score based on config file management
    if stats['config_file_exists']:
        integration_score += 5
    
    return {
        'integration_level': min(integration_score, 100),
        'statistics': stats,
        'recommendations': _generate_sync_recommendations(stats),
        'next_actions': _get_sync_next_actions(stats)
    }


def _generate_sync_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate synchronization improvement recommendations."""
    recommendations = []
    
    if stats['sync_health'] != 'healthy':
        recommendations.append("Resolve configuration conflicts for better sync reliability")
    
    if not stats['last_sync_time'] or (time.time() - stats['last_sync_time']) > 7200:
        recommendations.append("Perform configuration sync to ensure settings are current")
    
    if stats['registered_callbacks'] == 0:
        recommendations.append("Consider registering callbacks for real-time config updates")
    
    if not stats['config_file_exists']:
        recommendations.append("Initialize local configuration file for persistence")
    
    if not recommendations:
        recommendations.append("Configuration synchronization is optimal")
    
    return recommendations


def _get_sync_next_actions(stats: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get next actions for configuration synchronization."""
    actions = []
    
    if stats['sync_conflicts_count'] > 0:
        actions.append({
            'action': 'resolve_conflicts',
            'description': 'Resolve configuration conflicts',
            'priority': 'high'
        })
    
    if not stats['last_sync_time']:
        actions.append({
            'action': 'initial_sync',
            'description': 'Perform initial configuration synchronization',
            'priority': 'medium'
        })
    
    if stats['config_file_age_hours'] and stats['config_file_age_hours'] > 24:
        actions.append({
            'action': 'refresh_config',
            'description': 'Refresh configuration from Pensieve',
            'priority': 'low'
        })
    
    return actions