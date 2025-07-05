"""
Advanced Configuration Management for AutoTaskTracker.

Provides hot-reloading, environment detection, and distributed configuration capabilities.
"""

import os
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from datetime import datetime
import hashlib
from dataclasses import asdict

from autotasktracker.config import get_config, reset_config, AutoTaskSettings
from autotasktracker.core import DatabaseManager

logger = logging.getLogger(__name__)

class ConfigChangeEvent:
    """Configuration change event."""
    
    def __init__(self, key: str, old_value: Any, new_value: Any, source: str = "unknown"):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source
        self.timestamp = datetime.now()

class ConfigManager:
    """Advanced configuration manager with hot-reloading and monitoring."""
    
    def __init__(self):
        self.config = get_config()
        self.change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        self.file_watchers: Dict[str, float] = {}  # file_path -> last_modified
        self.environment_hash = ""
        self.monitoring_enabled = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Initialize environment monitoring
        self._update_environment_hash()
    
    def _update_environment_hash(self) -> str:
        """Update the environment variables hash for change detection."""
        env_vars = {k: v for k, v in os.environ.items() if k.startswith('AUTOTASK_')}
        env_string = json.dumps(env_vars, sort_keys=True)
        self.environment_hash = hashlib.md5(env_string.encode(), usedforsecurity=False).hexdigest()
        return self.environment_hash
    
    def add_change_listener(self, callback: Callable[[ConfigChangeEvent], None]):
        """Add a configuration change listener."""
        with self._lock:
            self.change_listeners.append(callback)
    
    def remove_change_listener(self, callback: Callable[[ConfigChangeEvent], None]):
        """Remove a configuration change listener."""
        with self._lock:
            if callback in self.change_listeners:
                self.change_listeners.remove(callback)
    
    def _notify_listeners(self, event: ConfigChangeEvent):
        """Notify all listeners of configuration changes."""
        with self._lock:
            for listener in self.change_listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Error in config change listener: {e}")
    
    def check_environment_changes(self) -> List[ConfigChangeEvent]:
        """Check for environment variable changes."""
        new_hash = self._update_environment_hash()
        changes = []
        
        if new_hash != self.environment_hash:
            logger.info("Environment variables changed, reloading config")
            
            # Capture old config values
            old_config = asdict(self.config)
            
            # Reset and reload configuration
            reset_config()
            self.config = get_config()
            
            # Detect specific changes
            new_config = asdict(self.config)
            
            for key, new_value in new_config.items():
                old_value = old_config.get(key)
                if old_value != new_value:
                    event = ConfigChangeEvent(
                        key=key,
                        old_value=old_value,
                        new_value=new_value,
                        source="environment"
                    )
                    changes.append(event)
                    self._notify_listeners(event)
            
            self.environment_hash = new_hash
        
        return changes
    
    def watch_config_file(self, file_path: str):
        """Add a configuration file to watch for changes."""
        if os.path.exists(file_path):
            self.file_watchers[file_path] = os.path.getmtime(file_path)
        else:
            logger.warning(f"Config file not found: {file_path}")
    
    def check_file_changes(self) -> List[ConfigChangeEvent]:
        """Check for configuration file changes."""
        changes = []
        
        for file_path, last_modified in list(self.file_watchers.items()):
            if os.path.exists(file_path):
                current_modified = os.path.getmtime(file_path)
                if current_modified > last_modified:
                    logger.info(f"Config file changed: {file_path}")
                    
                    try:
                        # Load file and apply changes
                        with open(file_path, 'r') as f:
                            file_config = json.load(f)
                        
                        # Apply environment variables from file
                        old_env = dict(os.environ)
                        for key, value in file_config.items():
                            if key.startswith('AUTOTASK_'):
                                old_value = os.environ.get(key)
                                os.environ[key] = str(value)
                                
                                if old_value != str(value):
                                    event = ConfigChangeEvent(
                                        key=key,
                                        old_value=old_value,
                                        new_value=value,
                                        source=f"file:{file_path}"
                                    )
                                    changes.append(event)
                        
                        # Reload configuration
                        reset_config()
                        self.config = get_config()
                        
                        # Notify listeners
                        for event in changes:
                            self._notify_listeners(event)
                        
                        self.file_watchers[file_path] = current_modified
                        
                    except Exception as e:
                        logger.error(f"Error loading config file {file_path}: {e}")
            else:
                # File was deleted
                logger.warning(f"Config file removed: {file_path}")
                del self.file_watchers[file_path]
        
        return changes
    
    def start_monitoring(self, interval: float = 5.0):
        """Start monitoring configuration changes."""
        if self.monitoring_enabled:
            logger.warning("Config monitoring already started")
            return
        
        self.monitoring_enabled = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Started config monitoring with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop monitoring configuration changes."""
        self.monitoring_enabled = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
            self.monitor_thread = None
        logger.info("Stopped config monitoring")
    
    def _monitoring_loop(self, interval: float):
        """Main monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Check for environment changes
                env_changes = self.check_environment_changes()
                if env_changes:
                    logger.info(f"Detected {len(env_changes)} environment changes")
                
                # Check for file changes
                file_changes = self.check_file_changes()
                if file_changes:
                    logger.info(f"Detected {len(file_changes)} file changes")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in config monitoring loop: {e}")
                time.sleep(interval)
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get current environment information."""
        return {
            'environment_hash': self.environment_hash,
            'config_values': asdict(self.config),
            'watched_files': list(self.file_watchers.keys()),
            'monitoring_enabled': self.monitoring_enabled,
            'autotask_env_vars': {
                k: v for k, v in os.environ.items() 
                if k.startswith('AUTOTASK_')
            }
        }
    
    def save_config_snapshot(self, file_path: str) -> bool:
        """Save current configuration as a snapshot."""
        try:
            # Validate file path before writing
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'config': asdict(self.config),
                'environment': {
                    k: v for k, v in os.environ.items() 
                    if k.startswith('AUTOTASK_')
                },
                'version': 'autotasktracker-1.0'
            }
            
            # Ensure parent directory exists
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate we can write to the location
            if file_path.exists() and not os.access(file_path, os.W_OK):
                raise PermissionError(f"Cannot write to file: {file_path}")
            
            with open(file_path, 'w') as f:
                json.dump(snapshot, f, indent=2, default=str)
            
            logger.info(f"Config snapshot saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config snapshot: {e}")
            return False
    
    def load_config_snapshot(self, file_path: str) -> bool:
        """Load configuration from a snapshot."""
        try:
            with open(file_path, 'r') as f:
                snapshot = json.load(f)
            
            # Apply environment variables from snapshot
            env_vars = snapshot.get('environment', {})
            for key, value in env_vars.items():
                os.environ[key] = str(value)
            
            # Reset and reload configuration
            reset_config()
            self.config = get_config()
            
            logger.info(f"Config snapshot loaded from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading config snapshot: {e}")
            return False
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return status."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        try:
            # Test database path
            db_path = self.config.get_db_path()
            if not os.path.exists(os.path.dirname(db_path)):
                validation_results['errors'].append(f"Database directory does not exist: {os.path.dirname(db_path)}")
                validation_results['valid'] = False
            
            # Test port availability
            import socket
            critical_ports = [
                self.config.MEMOS_PORT,
                self.config.TASK_BOARD_PORT,
                self.config.ANALYTICS_PORT
            ]
            
            for port in critical_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind((self.config.SERVER_HOST, port))
                    validation_results['info'].append(f"Port {port} is available")
                except OSError:
                    validation_results['warnings'].append(f"Port {port} is already in use")
            
            # Validate VLM configuration
            if self.config.vlm_port < 1024:
                validation_results['errors'].append("VLM port is in privileged range")
                validation_results['valid'] = False
            
            # Check file permissions
            for dir_path in [self.config.screenshots_dir, self.config.vlm_cache_dir]:
                if not os.access(dir_path, os.W_OK):
                    validation_results['warnings'].append(f"Directory not writable: {dir_path}")
            
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {e}")
            validation_results['valid'] = False
        
        return validation_results

# Global config manager instance
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def setup_config_monitoring(enable_file_watching: bool = True, 
                          config_files: Optional[List[str]] = None) -> ConfigManager:
    """Set up configuration monitoring with sensible defaults."""
    manager = get_config_manager()
    
    if enable_file_watching and config_files:
        for config_file in config_files:
            manager.watch_config_file(config_file)
    
    # Add default change listener for logging
    def log_config_changes(event: ConfigChangeEvent):
        logger.info(f"Config changed: {event.key} = {event.new_value} (was {event.old_value}) from {event.source}")
    
    manager.add_change_listener(log_config_changes)
    
    return manager