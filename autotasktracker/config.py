"""
Centralized configuration module for AutoTaskTracker.
Manages all configuration settings, paths, and environment variables.
"""
import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


def _validate_path_security(path: str) -> str:
    """Validate and sanitize file paths for security.
    
    Args:
        path: Input path to validate
        
    Returns:
        Sanitized path
        
    Raises:
        ValueError: If path is potentially dangerous
    """
    if not path or not isinstance(path, str):
        raise ValueError("Path must be a non-empty string")
    
    # Normalize path to prevent traversal attacks
    normalized = os.path.normpath(path)
    
    # Check for dangerous patterns
    dangerous_patterns = [
        '/etc/', '/bin/', '/usr/bin/', '/sbin/', '/var/log/',
        'system32', 'windows', 'passwd', 'shadow', 'hosts',
        '..', '%', '$', '`', ';', '|', '&', '>', '<'
    ]
    
    path_lower = normalized.lower()
    for pattern in dangerous_patterns:
        if pattern in path_lower:
            logger.warning(f"Potentially dangerous path rejected: {path}")
            # Return safe default instead of raising to prevent DoS
            return os.path.expanduser("~/.memos/database.db")
    
    # Ensure path is within user directory or explicitly allowed locations
    expanded = os.path.expanduser(normalized)
    
    # Only allow paths under user home or /tmp for testing
    home_dir = os.path.expanduser("~")
    allowed_prefixes = [home_dir, "/tmp", "./", os.getcwd()]
    
    if not any(expanded.startswith(prefix) for prefix in allowed_prefixes):
        logger.warning(f"Path outside allowed directories rejected: {path}")
        return os.path.expanduser("~/.memos/database.db")
    
    return expanded


def _validate_port_security(port: Union[str, int]) -> int:
    """Validate port numbers for security.
    
    Args:
        port: Port number to validate
        
    Returns:
        Validated port number
        
    Raises:
        ValueError: If port is invalid or dangerous
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        raise ValueError(f"Port must be a valid integer: {port}")
    
    # Check for privileged ports (require root)
    if port_int < 1024:
        raise ValueError(f"Privileged port not allowed: {port_int}")
    
    # Check for valid port range
    if not (1024 <= port_int <= 65535):
        raise ValueError(f"Port out of valid range (1024-65535): {port_int}")
    
    # Check for commonly used system ports that should be avoided
    dangerous_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
    if port_int in dangerous_ports:
        raise ValueError(f"System port not allowed: {port_int}")
    
    return port_int


def _sanitize_string_input(value: str, max_length: int = 255) -> str:
    """Sanitize string inputs to prevent injection attacks.
    
    Args:
        value: String value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        raise ValueError("Value must be a string")
    
    if len(value) > max_length:
        raise ValueError(f"String too long (max {max_length}): {len(value)}")
    
    # Remove potential injection characters
    dangerous_chars = [';', '`', '$', '&', '|', '>', '<', '"', "'", '\\']
    sanitized = value
    
    for char in dangerous_chars:
        if char in sanitized:
            logger.warning(f"Dangerous character removed from input: {char}")
            sanitized = sanitized.replace(char, '')
    
    return sanitized.strip()


@dataclass
class Config:
    """Central configuration for AutoTaskTracker with environment variable support."""
    
    # Database settings
    DB_PATH: str = field(default_factory=lambda: os.path.expanduser("~/.memos/database.db"))
    SCREENSHOTS_DIR: str = field(default_factory=lambda: os.path.expanduser("~/.memos/screenshots"))
    LOGS_DIR: str = field(default_factory=lambda: os.path.expanduser("~/.memos/logs"))
    VLM_CACHE_DIR: str = field(default_factory=lambda: os.path.expanduser("~/.memos/vlm_cache"))
    
    # Server ports
    MEMOS_PORT: int = 8839
    TASK_BOARD_PORT: int = 8502
    ANALYTICS_PORT: int = 8503
    TIMETRACKER_PORT: int = 8504
    TIME_TRACKER_PORT: int = 8505  # Alias for compatibility
    NOTIFICATIONS_PORT: int = 8506
    
    # VLM configuration
    VLM_MODEL: str = "minicpm-v"
    VLM_PORT: int = 11434
    
    # Embedding configuration  
    EMBEDDING_MODEL: str = "jina-embeddings-v2-base-en"
    EMBEDDING_DIM: int = 768
    
    # Application settings
    AUTO_REFRESH_SECONDS: int = 30
    CACHE_TTL_SECONDS: int = 60
    TASK_LIMIT: int = 100
    GROUP_INTERVAL_MINUTES: int = 5
    SCREENSHOT_INTERVAL_SECONDS: int = 4
    
    # Processing configuration
    BATCH_SIZE: int = 50
    CONFIDENCE_THRESHOLD: float = 0.7
    
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
    
    def __post_init__(self):
        """Initialize configuration with environment overrides."""
        # Database path
        self.db_path = self._get_path(
            "AUTOTASK_DB_PATH",
            self.DB_PATH
        )
        
        # Directory paths  
        self.memos_dir = self._get_path(
            "AUTOTASK_MEMOS_DIR",
            os.path.expanduser("~/.memos")
        )
        
        self.vlm_cache_dir = self._get_path(
            "AUTOTASK_VLM_CACHE_DIR",
            self.VLM_CACHE_DIR
        )
        
        self.screenshots_dir = self._get_path(
            "AUTOTASK_SCREENSHOTS_DIR", 
            self.SCREENSHOTS_DIR
        )
        
        # VLM settings
        self.vlm_model = os.getenv("AUTOTASK_VLM_MODEL", self.VLM_MODEL)
        self.vlm_port = int(os.getenv("AUTOTASK_VLM_PORT", str(self.VLM_PORT)))
        
        # Embedding settings
        self.embedding_model = os.getenv("AUTOTASK_EMBEDDING_MODEL", self.EMBEDDING_MODEL)
        self.embedding_dim = int(os.getenv("AUTOTASK_EMBEDDING_DIM", str(self.EMBEDDING_DIM)))
        
        # Processing settings
        self.batch_size = int(os.getenv("AUTOTASK_BATCH_SIZE", str(self.BATCH_SIZE)))
        self.confidence_threshold = float(os.getenv("AUTOTASK_CONFIDENCE_THRESHOLD", str(self.CONFIDENCE_THRESHOLD)))
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _get_path(self, env_var: str, default: str) -> Path:
        """Get path from environment or use default."""
        path_str = os.getenv(env_var, default)
        return Path(os.path.expanduser(path_str))
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        dirs = [self.memos_dir, self.vlm_cache_dir, self.screenshots_dir]
        for dir_path in dirs:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {dir_path}")
                except OSError as e:
                    logger.error(f"Failed to create directory {dir_path}: {e}")
    
    def get_db_path(self) -> str:
        """Get database path as string."""
        return str(self.db_path)
    
    def get_vlm_cache_path(self) -> str:
        """Get VLM cache directory path as string."""
        return str(self.vlm_cache_dir)
    
    def get_screenshots_path(self) -> str:
        """Get screenshots directory path as string."""
        return str(self.screenshots_dir)
    
    def get_ollama_url(self) -> str:
        """Get Ollama API URL."""
        return f"http://localhost:{self.vlm_port}"
    
    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return {
            "db_path": str(self.db_path),
            "memos_dir": str(self.memos_dir),
            "vlm_cache_dir": str(self.vlm_cache_dir),
            "screenshots_dir": str(self.screenshots_dir),
            "vlm_model": self.vlm_model,
            "vlm_port": self.vlm_port,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "batch_size": self.batch_size,
            "confidence_threshold": self.confidence_threshold,
            "ports": {
                "task_board": self.TASK_BOARD_PORT,
                "analytics": self.ANALYTICS_PORT,
                "time_tracker": self.TIME_TRACKER_PORT,
                "memos": self.MEMOS_PORT
            }
        }


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config