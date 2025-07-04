"""
Centralized configuration module for AutoTaskTracker.
Manages all configuration settings, paths, and environment variables.
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Central configuration for AutoTaskTracker."""
    
    # Database configuration
    DEFAULT_DB_PATH = "~/.memos/database.db"
    
    # Directory paths
    DEFAULT_MEMOS_DIR = "~/.memos"
    DEFAULT_VLM_CACHE_DIR = "~/.memos/vlm_cache"
    DEFAULT_SCREENSHOTS_DIR = "~/.memos/screenshots"
    
    # VLM configuration
    DEFAULT_VLM_MODEL = "minicpm-v"
    DEFAULT_VLM_PORT = 11434
    
    # Embedding configuration  
    DEFAULT_EMBEDDING_MODEL = "jina-embeddings-v2-base-en"
    DEFAULT_EMBEDDING_DIM = 768
    
    # Application ports
    TASK_BOARD_PORT = 8502
    ANALYTICS_PORT = 8503
    TIME_TRACKER_PORT = 8505
    MEMOS_PORT = 8839
    
    # Processing configuration
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self):
        """Initialize configuration with environment overrides."""
        # Database path
        self.db_path = self._get_path(
            "AUTOTASK_DB_PATH",
            self.DEFAULT_DB_PATH
        )
        
        # Directory paths
        self.memos_dir = self._get_path(
            "AUTOTASK_MEMOS_DIR",
            self.DEFAULT_MEMOS_DIR
        )
        
        self.vlm_cache_dir = self._get_path(
            "AUTOTASK_VLM_CACHE_DIR",
            self.DEFAULT_VLM_CACHE_DIR
        )
        
        self.screenshots_dir = self._get_path(
            "AUTOTASK_SCREENSHOTS_DIR", 
            self.DEFAULT_SCREENSHOTS_DIR
        )
        
        # VLM settings
        self.vlm_model = os.getenv("AUTOTASK_VLM_MODEL", self.DEFAULT_VLM_MODEL)
        self.vlm_port = int(os.getenv("AUTOTASK_VLM_PORT", str(self.DEFAULT_VLM_PORT)))
        
        # Embedding settings
        self.embedding_model = os.getenv("AUTOTASK_EMBEDDING_MODEL", self.DEFAULT_EMBEDDING_MODEL)
        self.embedding_dim = int(os.getenv("AUTOTASK_EMBEDDING_DIM", str(self.DEFAULT_EMBEDDING_DIM)))
        
        # Processing settings
        self.batch_size = int(os.getenv("AUTOTASK_BATCH_SIZE", str(self.DEFAULT_BATCH_SIZE)))
        self.confidence_threshold = float(os.getenv("AUTOTASK_CONFIDENCE_THRESHOLD", str(self.DEFAULT_CONFIDENCE_THRESHOLD)))
        
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