"""
Pensieve configuration synchronization system.
Automatically syncs configurations between Pensieve and AutoTaskTracker.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from autotasktracker.config import get_config
from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError

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
        
        # Configuration file for persistent settings
        self.config_file = Path.home() / ".memos" / "autotask_config.json"
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
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
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save config to file: {e}")
    
    def _load_config_from_file(self) -> SyncedConfiguration:
        """Load configuration from file."""
        try:
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
        Update Pensieve configuration (if supported by API).
        
        Args:
            updates: Configuration updates to apply
            
        Returns:
            True if successful
        """
        try:
            # Note: This depends on Pensieve API supporting config updates
            # For now, log the intended updates
            logger.info(f"Configuration updates requested: {updates}")
            logger.warning("Pensieve config updates not yet implemented - updates logged only")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update Pensieve config: {e}")
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