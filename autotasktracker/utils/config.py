"""
Configuration management for AutoTaskTracker.
Handles environment variables, config files, and default settings.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import logging


logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration with defaults and environment variable support."""
    
    # Database settings
    DB_PATH: str = field(default_factory=lambda: os.path.expanduser("~/.memos/database.db"))
    SCREENSHOTS_DIR: str = field(default_factory=lambda: os.path.expanduser("~/.memos/screenshots"))
    LOGS_DIR: str = field(default_factory=lambda: os.path.expanduser("~/.memos/logs"))
    
    # Server ports
    MEMOS_PORT: int = 8839
    TASK_BOARD_PORT: int = 8502
    ANALYTICS_PORT: int = 8503
    TIMETRACKER_PORT: int = 8504
    NOTIFICATIONS_PORT: int = 8505
    
    # Application settings
    AUTO_REFRESH_SECONDS: int = 30
    CACHE_TTL_SECONDS: int = 60
    DEFAULT_TASK_LIMIT: int = 100
    GROUP_INTERVAL_MINUTES: int = 5
    SCREENSHOT_INTERVAL_SECONDS: int = 4  # Default from memos config
    
    # Time tracking settings
    MIN_SESSION_DURATION_SECONDS: int = 30
    MAX_SESSION_GAP_SECONDS: int = 600  # 10 minutes
    IDLE_THRESHOLD_SECONDS: int = 300   # 5 minutes
    
    # Feature flags
    SHOW_SCREENSHOTS: bool = True
    ENABLE_NOTIFICATIONS: bool = True
    ENABLE_ANALYTICS: bool = True
    
    # Performance settings
    MAX_SCREENSHOT_SIZE: int = 300  # pixels for thumbnails
    CONNECTION_POOL_SIZE: int = 5
    QUERY_TIMEOUT_SECONDS: int = 30
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Create config instance from environment variables.
        
        Environment variables should be prefixed with AUTOTASK_
        Example: AUTOTASK_DB_PATH, AUTOTASK_TASK_BOARD_PORT
        """
        config_dict = {}
        prefix = "AUTOTASK_"
        
        # Get all class fields
        for field_name, field_def in cls.__dataclass_fields__.items():
            env_var = f"{prefix}{field_name}"
            if env_var in os.environ:
                value = os.environ[env_var]
                # Type conversion based on field type
                if field_def.type == int:
                    config_dict[field_name] = int(value)
                elif field_def.type == bool:
                    config_dict[field_name] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    config_dict[field_name] = value
        
        return cls(**config_dict)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to JSON config file
            
        Returns:
            Config instance
        """
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            return cls(**config_dict)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return cls()
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config_path: Path to save JSON config
        """
        try:
            config_dir = os.path.dirname(config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
        except IOError as e:
            logger.error(f"Error saving config to {config_path}: {e}")
    
    def get_service_url(self, service: str) -> str:
        """
        Get the URL for a service.
        
        Args:
            service: Service name (e.g., 'memos', 'task_board')
            
        Returns:
            Service URL
        """
        port_map = {
            'memos': self.MEMOS_PORT,
            'task_board': self.TASK_BOARD_PORT,
            'analytics': self.ANALYTICS_PORT,
            'timetracker': self.TIMETRACKER_PORT,
            'notifications': self.NOTIFICATIONS_PORT
        }
        
        port = port_map.get(service)
        if port:
            return f"http://localhost:{port}"
        return ""
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if valid, False otherwise
        """
        # Check if paths exist
        if not os.path.exists(os.path.dirname(self.DB_PATH)):
            logger.warning(f"Database directory does not exist: {os.path.dirname(self.DB_PATH)}")
            return False
        
        # Check port ranges
        ports = [self.MEMOS_PORT, self.TASK_BOARD_PORT, self.ANALYTICS_PORT, 
                self.TIMETRACKER_PORT, self.NOTIFICATIONS_PORT]
        for port in ports:
            if not (1024 <= port <= 65535):
                logger.error(f"Invalid port number: {port}")
                return False
        
        # Check for port conflicts
        if len(set(ports)) != len(ports):
            logger.error("Port conflict detected - multiple services using same port")
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    @property
    def memos_dir(self) -> Path:
        """Get the memos directory path."""
        return Path(self.DB_PATH).parent
    
    def get_ollama_url(self) -> str:
        """Get Ollama API URL from environment or default."""
        return os.getenv('OLLAMA_URL', 'http://localhost:11434')


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Loads from environment variables first, then falls back to defaults.
    """
    global _config
    if _config is None:
        # Try to load from standard config file location
        config_file = os.path.expanduser("~/.autotasktracker/config.json")
        if os.path.exists(config_file):
            _config = Config.from_file(config_file)
        else:
            # Load from environment variables or use defaults
            _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to defaults."""
    global _config
    _config = None