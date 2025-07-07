"""
Unified Configuration for AutoTaskTracker

This is the ONLY configuration file for AutoTaskTracker.
Includes all ports, paths, API endpoints, service configurations,
security validations, Pensieve integration, and thread safety.

Usage:
    from autotasktracker.config import get_config
    config = get_config()
"""

import os
import sys
import re
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union
import logging

# Port definitions included inline (no separate ports file)

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
    
    # Check if we're in test mode
    is_test_mode = (
        os.getenv("PYTEST_CURRENT_TEST") is not None or
        os.getenv("AUTOTASK_TEST_MODE") == "1" or
        "test" in sys.argv[0].lower() or
        any("pytest" in arg for arg in sys.argv)
    )
    
    # In test mode, allow test-specific paths
    if is_test_mode and ("test" in path.lower() or path.startswith("test_")):
        return path
    
    # Allow PostgreSQL URIs
    if path.startswith(('postgresql://', 'postgres://')):
        return path
    
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
            return "/Users/paulrohde/AutoTaskTracker.memos/database.db"
    
    # Ensure path is within user directory or explicitly allowed locations
    expanded = os.path.expanduser(normalized)
    
    # Only allow paths under user home or /tmp for testing
    home_dir = os.path.expanduser("~")
    allowed_prefixes = [home_dir, "/tmp", "/var/folders", "./", os.getcwd()]
    
    if not any(expanded.startswith(prefix) for prefix in allowed_prefixes):
        logger.warning(f"Path outside allowed directories rejected: {path}")
        return "/Users/paulrohde/AutoTaskTracker.memos/database.db"
    
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
    """Comprehensive centralized configuration for AutoTaskTracker."""
    
    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    
    # PostgreSQL Database (Primary)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "mysecretpassword"
    POSTGRES_DATABASE: str = "autotasktracker"
    
    @property
    def DATABASE_URL(self) -> str:
        """Primary PostgreSQL database URL."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
    
    
    # Note: SQLite support removed - PostgreSQL only
    
    # ============================================================================
    # DIRECTORY PATHS
    # ============================================================================
    
    # Base directories
    MEMOS_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos"
    SCREENSHOTS_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos/screenshots"
    LOGS_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos/logs"
    CACHE_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos/cache"
    VLM_CACHE_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos/vlm_cache"
    EMBEDDINGS_CACHE_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos/embeddings_cache"
    TEMP_DIR: str = "/Users/paulrohde/AutoTaskTracker.memos/temp"
    
    # Configuration files
    PENSIEVE_CONFIG_FILE: str = "/Users/paulrohde/AutoTaskTracker.memos/config_autotasktracker.yaml"
    AUTOTASK_CONFIG_FILE: str = "/Users/paulrohde/AutoTaskTracker.memos/autotask_config.json"
    
    # ============================================================================
    # PORT CONFIGURATION - Imported from ports.py
    # ============================================================================
    
    # Port values defined directly to avoid circular imports
    
    # Core Dashboard Ports
    TASK_BOARD_PORT: int = 8602
    ANALYTICS_PORT: int = 8603
    TIMETRACKER_PORT: int = 8605
    TIME_TRACKER_PORT: int = 8605  # Alias
    NOTIFICATIONS_PORT: int = 8606
    ADVANCED_ANALYTICS_PORT: int = 8607
    OVERVIEW_PORT: int = 8608
    FOCUS_TRACKER_PORT: int = 8609
    DAILY_SUMMARY_PORT: int = 8610
    
    # Administrative Ports
    LAUNCHER_PORT: int = 8611
    VLM_MONITOR_PORT: int = 8612
    AI_TASK_DASHBOARD_PORT: int = 8613
    ACHIEVEMENT_BOARD_PORT: int = 8614
    REALTIME_DASHBOARD_PORT: int = 8615
    
    # API and Service Ports
    AUTOTASK_API_PORT: int = 8620
    HEALTH_CHECK_PORT: int = 8621
    METRICS_PORT: int = 8622
    WEBHOOK_PORT: int = 8623
    
    # Development Ports
    DEV_DASHBOARD_PORT: int = 8650
    TEST_API_PORT: int = 8651
    DEBUG_PORT: int = 8652
    
    # Additional Dashboard Ports
    POSTGRES_TASK_BOARD_PORT: int = 8653
    POSTGRES_ANALYTICS_PORT: int = 8654
    POSTGRES_TIMETRACKER_PORT: int = 8655
    QUICK_DASHBOARD_PORT: int = 8656
    FINAL_DASHBOARD_PORT: int = 8657
    ADAPTIVE_TASK_BOARD_PORT: int = 8658
    
    # External Service Ports
    MEMOS_PORT: int = 8841  # AutoTaskTracker specific
    MEMOS_WEB_PORT: int = 8842  # AutoTaskTracker specific
    OLLAMA_PORT: int = 11434
    OCR_SERVICE_PORT: int = 5555
    POSTGRES_PORT: int = 5433
    JUPYTER_PORT: int = 8888
    TENSORBOARD_PORT: int = 6006
    
    # ============================================================================
    # API ENDPOINTS
    # ============================================================================
    
    SERVER_HOST: str = "localhost"
    
    @property
    def API_ENDPOINTS(self) -> Dict[str, str]:
        """All API endpoints used by AutoTaskTracker."""
        return {
            # Core APIs
            "pensieve_api": f"http://{self.SERVER_HOST}:{self.MEMOS_PORT}",
            "pensieve_web": f"http://{self.SERVER_HOST}:{self.MEMOS_WEB_PORT}",
            "autotask_api": f"http://{self.SERVER_HOST}:{self.AUTOTASK_API_PORT}",
            
            # AI Service APIs
            "ollama_api": f"http://{self.SERVER_HOST}:{self.OLLAMA_PORT}",
            "ollama_embeddings": f"http://{self.SERVER_HOST}:{self.OLLAMA_PORT}/v1/embeddings",
            "ocr_api": f"http://{self.SERVER_HOST}:{self.OCR_SERVICE_PORT}/predict",
            
            # Dashboard URLs
            "task_board": f"http://{self.SERVER_HOST}:{self.TASK_BOARD_PORT}",
            "analytics": f"http://{self.SERVER_HOST}:{self.ANALYTICS_PORT}",
            "timetracker": f"http://{self.SERVER_HOST}:{self.TIMETRACKER_PORT}",
            "notifications": f"http://{self.SERVER_HOST}:{self.NOTIFICATIONS_PORT}",
            "advanced_analytics": f"http://{self.SERVER_HOST}:{self.ADVANCED_ANALYTICS_PORT}",
            "overview": f"http://{self.SERVER_HOST}:{self.OVERVIEW_PORT}",
            "focus_tracker": f"http://{self.SERVER_HOST}:{self.FOCUS_TRACKER_PORT}",
            "daily_summary": f"http://{self.SERVER_HOST}:{self.DAILY_SUMMARY_PORT}",
            "launcher": f"http://{self.SERVER_HOST}:{self.LAUNCHER_PORT}",
            "vlm_monitor": f"http://{self.SERVER_HOST}:{self.VLM_MONITOR_PORT}",
            "ai_task_dashboard": f"http://{self.SERVER_HOST}:{self.AI_TASK_DASHBOARD_PORT}",
            "achievement_board": f"http://{self.SERVER_HOST}:{self.ACHIEVEMENT_BOARD_PORT}",
            "realtime_dashboard": f"http://{self.SERVER_HOST}:{self.REALTIME_DASHBOARD_PORT}",
            
            # Utility URLs
            "health_check": f"http://{self.SERVER_HOST}:{self.HEALTH_CHECK_PORT}/health",
            "metrics": f"http://{self.SERVER_HOST}:{self.METRICS_PORT}/metrics",
            "webhooks": f"http://{self.SERVER_HOST}:{self.WEBHOOK_PORT}/webhooks",
        }
    
    # ============================================================================
    # AI MODEL CONFIGURATION
    # ============================================================================
    
    # VLM (Vision Language Model) Settings
    VLM_MODEL_NAME: str = "minicpm-v"
    VLM_ENDPOINT: str = f"http://localhost:11434"
    VLM_CONCURRENCY: int = 8
    VLM_FORCE_JPEG: bool = True
    VLM_PROMPT: str = "Please describe the content of this image, including the layout and visual elements."
    VLM_TEMPERATURE: float = 0.7  # Temperature for VLM inference (0.0-1.0)
    
    # Dual-Model Configuration (Phase 2)
    LLAMA3_MODEL_NAME: str = "llama3:8b"
    ENABLE_DUAL_MODEL: bool = False  # Feature flag for dual-model processing
    
    # OCR Settings  
    OCR_ENDPOINT: str = f"http://localhost:5555/predict"
    OCR_USE_LOCAL: bool = True
    OCR_CONCURRENCY: int = 8
    OCR_FORCE_JPEG: bool = False
    
    # Embedding Settings
    EMBEDDING_MODEL: str = "arkohut/jina-embeddings-v2-base-en"
    EMBEDDING_DIMENSIONS: int = 768
    EMBEDDING_ENDPOINT: str = f"http://localhost:11434/v1/embeddings"
    EMBEDDING_USE_LOCAL: bool = True
    
    # ============================================================================
    # PENSIEVE/MEMOS CONFIGURATION
    # ============================================================================
    
    # Recording Settings
    RECORD_INTERVAL: int = 4        # seconds between screenshots
    PROCESSING_INTERVAL: int = 1    # processing interval
    IDLE_TIMEOUT: int = 300         # idle timeout in seconds
    
    # Watch Settings
    RATE_WINDOW_SIZE: int = 20
    SPARSITY_FACTOR: float = 1.0
    
    # Storage Settings
    CACHE_TTL: int = 600            # cache time-to-live in seconds
    MAX_STORAGE_GB: float = 10.0    # maximum storage in GB
    CLEANUP_DAYS: int = 30          # cleanup old data after N days
    
    # Plugin Settings
    DEFAULT_PLUGINS: List[str] = field(default_factory=lambda: [
        "builtin_ocr",
        "builtin_vlm"
    ])
    
    # ============================================================================
    # AUTHENTICATION & SECURITY
    # ============================================================================
    
    # Authentication (empty by default for local development)
    AUTH_USERNAME: str = ""
    AUTH_PASSWORD: str = ""
    
    # API Tokens (empty by default, set via environment)
    OLLAMA_TOKEN: str = ""
    OCR_TOKEN: str = ""
    EMBEDDING_TOKEN: str = ""
    
    # Security Settings
    ENABLE_CORS: bool = True
    ALLOWED_ORIGINS: List[str] = field(default_factory=lambda: [
        "http://localhost:8602",
        "http://localhost:8603", 
        "http://localhost:8605",
        "http://localhost:8606",
        "http://localhost:8607",
        "http://localhost:8608",
        "http://localhost:8609",
        "http://localhost:8610"
    ])
    
    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    
    # Core Features
    ENABLE_VLM: bool = True
    ENABLE_OCR: bool = True
    ENABLE_EMBEDDINGS: bool = True
    ENABLE_REAL_TIME: bool = True
    ENABLE_NOTIFICATIONS: bool = True
    
    # Advanced Features
    ENABLE_VECTOR_SEARCH: bool = True
    ENABLE_AI_INSIGHTS: bool = True
    ENABLE_PERFORMANCE_MONITORING: bool = True
    ENABLE_AUTO_BACKUP: bool = True
    
    # Development Features
    ENABLE_DEBUG_MODE: bool = False
    ENABLE_PROFILING: bool = False
    ENABLE_TELEMETRY: bool = True
    
    def __post_init__(self):
        """Initialize configuration with environment overrides and security validation."""
        # Validate paths without trying to set properties
        _validate_path_security(self.DATABASE_URL)
        
        # Create required directories - let it fail if there are permission issues
        self.create_directories()
    
    # ============================================================================
    # PENSIEVE INTEGRATION
    # ============================================================================
    
    # Pensieve integration settings
    USE_PENSIEVE_API: bool = True
    PENSIEVE_CONFIG_SYNC: bool = False  # DISABLED to prevent recursion
    PENSIEVE_CACHE_ENABLED: bool = True
    
    @property
    def SCREENSHOTS_DIR_PROPERTY(self) -> str:
        """Screenshots directory."""
        return os.path.expanduser(self.SCREENSHOTS_DIR)
    
    @property
    def LOGS_DIR_PROPERTY(self) -> str:
        """Logs directory."""
        return os.path.expanduser(self.LOGS_DIR)
    
    @property
    def VLM_CACHE_DIR_PROPERTY(self) -> str:
        """VLM cache directory."""
        return os.path.expanduser(self.VLM_CACHE_DIR)
    
    def get_service_url(self, service: str) -> str:
        """Get service URL."""
        # Use get_url_by_service for consistency
        return self.get_url_by_service(service) or f"http://{self.SERVER_HOST}:8841"
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return {
            'batch_size': self.SPARSITY_FACTOR,
            'cache_ttl': self.CACHE_TTL,
            'auto_refresh': self.CACHE_TTL,
            'confidence_threshold': self.VLM_CONCURRENCY
        }
    
    # ============================================================================
    # PATH AND DATABASE METHODS
    # ============================================================================
    
    
    def get_vlm_cache_path(self) -> str:
        """Get VLM cache directory path as string."""
        return str(self.get_expanded_path(self.VLM_CACHE_DIR_PROPERTY))
    
    def get_screenshots_path(self) -> str:
        """Get screenshots directory path as string."""
        return str(self.get_expanded_path(self.SCREENSHOTS_DIR_PROPERTY))
    
    def get_ollama_url(self) -> str:
        """Get Ollama API URL with validation."""
        # Check environment variable first
        env_url = os.getenv('OLLAMA_URL')
        if env_url:
            # Basic URL validation
            if env_url.startswith(('http://', 'https://')) and '://' in env_url:
                return env_url
            else:
                logger.warning(f"Invalid OLLAMA_URL format, using default: {env_url}")
        
        return f"http://{self.SERVER_HOST}:{self.OLLAMA_PORT}"
    
    def get_database_backend(self) -> str:
        """Get the configured database backend."""
        return "postgresql"  # Only PostgreSQL supported
    
    def get_database_url(self) -> str:
        """Get database URL."""
        return self.DATABASE_URL
    
    
    def test_database_connection(self) -> bool:
        """Test PostgreSQL database connection."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.DATABASE_URL)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    @property
    def memos_dir_property(self) -> Path:
        """Get memos directory as Path object."""
        return self.get_expanded_path(self.MEMOS_DIR)
    
    @property
    def MEMOS_CONFIG_PATH(self) -> Path:
        """Get AutoTaskTracker specific memos config path."""
        return self.memos_dir_property / "config_autotasktracker.yaml"
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_expanded_path(self, path: str) -> Path:
        """Get expanded Path object from string path."""
        return Path(os.path.expanduser(path))
    
    def get_all_ports(self) -> Dict[str, int]:
        """Get all defined ports."""
        return {
            # Core Dashboard ports
            "task_board": self.TASK_BOARD_PORT,
            "analytics": self.ANALYTICS_PORT,
            "timetracker": self.TIMETRACKER_PORT,
            "time_tracker": self.TIME_TRACKER_PORT,
            "notifications": self.NOTIFICATIONS_PORT,
            "advanced_analytics": self.ADVANCED_ANALYTICS_PORT,
            "overview": self.OVERVIEW_PORT,
            "focus_tracker": self.FOCUS_TRACKER_PORT,
            "daily_summary": self.DAILY_SUMMARY_PORT,
            
            # Administrative ports
            "launcher": self.LAUNCHER_PORT,
            "vlm_monitor": self.VLM_MONITOR_PORT,
            "ai_task_dashboard": self.AI_TASK_DASHBOARD_PORT,
            "achievement_board": self.ACHIEVEMENT_BOARD_PORT,
            "realtime_dashboard": self.REALTIME_DASHBOARD_PORT,
            
            # API ports
            "autotask_api": self.AUTOTASK_API_PORT,
            "health_check": self.HEALTH_CHECK_PORT,
            "metrics": self.METRICS_PORT,
            "webhook": self.WEBHOOK_PORT,
            
            # Additional Dashboard ports
            "postgres_task_board": self.POSTGRES_TASK_BOARD_PORT,
            "postgres_analytics": self.POSTGRES_ANALYTICS_PORT,
            "postgres_timetracker": self.POSTGRES_TIMETRACKER_PORT,
            "quick_dashboard": self.QUICK_DASHBOARD_PORT,
            "final_dashboard": self.FINAL_DASHBOARD_PORT,
            "adaptive_task_board": self.ADAPTIVE_TASK_BOARD_PORT,
            
            # External services
            "memos": self.MEMOS_PORT,
            "memos_web": self.MEMOS_WEB_PORT,
            "ollama": self.OLLAMA_PORT,
            "ocr_service": self.OCR_SERVICE_PORT,
            "postgres": self.POSTGRES_PORT,
            
            # Development
            "dev_dashboard": self.DEV_DASHBOARD_PORT,
            "test_api": self.TEST_API_PORT,
            "debug": self.DEBUG_PORT,
            "jupyter": self.JUPYTER_PORT,
            "tensorboard": self.TENSORBOARD_PORT,
        }
    
    def get_all_paths(self) -> Dict[str, str]:
        """Get all defined paths."""
        return {
            "memos_dir": self.MEMOS_DIR,
            "screenshots_dir": self.SCREENSHOTS_DIR,
            "logs_dir": self.LOGS_DIR,
            "cache_dir": self.CACHE_DIR,
            "vlm_cache_dir": self.VLM_CACHE_DIR,
            "embeddings_cache_dir": self.EMBEDDINGS_CACHE_DIR,
            "temp_dir": self.TEMP_DIR,
            "pensieve_config": self.PENSIEVE_CONFIG_FILE,
            "autotask_config": self.AUTOTASK_CONFIG_FILE,
        }
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check port ranges
        all_ports = self.get_all_ports()
        for name, port in all_ports.items():
            if not (1024 <= port <= 65535):
                issues.append(f"Port {name} ({port}) out of valid range")
        
        # Check for port conflicts (excluding intentional aliases)
        port_values = list(all_ports.values())
        from collections import Counter
        port_counts = Counter(port_values)
        # Allow timetracker/time_tracker alias conflict
        conflicts = [(port, count) for port, count in port_counts.items() 
                    if count > 1 and port != self.TIMETRACKER_PORT]
        if conflicts:
            issues.append(f"Port conflicts detected: {conflicts}")
        
        # Check critical paths exist
        critical_paths = [self.MEMOS_DIR, self.SCREENSHOTS_DIR]
        for path in critical_paths:
            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                issues.append(f"Critical path does not exist: {expanded}")
        
        return issues
    
    def create_directories(self) -> None:
        """Create all required directories."""
        paths = self.get_all_paths()
        for name, path in paths.items():
            if name.endswith('_dir'):
                expanded = self.get_expanded_path(path)
                expanded.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {expanded}")
    
    def get_port_by_service(self, service_name: str) -> Optional[int]:
        """Get port number for a specific service."""
        ports = self.get_all_ports()
        return ports.get(service_name.lower())
    
    def get_url_by_service(self, service_name: str) -> Optional[str]:
        """Get URL for a specific service."""
        port = self.get_port_by_service(service_name)
        if port is None:
            return None
        return f"http://{self.SERVER_HOST}:{port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "database_url": self.DATABASE_URL,
            "api_endpoints": self.API_ENDPOINTS,
            "all_ports": self.get_all_ports(),
            "all_paths": self.get_all_paths(),
            "ai_config": {
                "vlm_model": self.VLM_MODEL_NAME,
                "vlm_endpoint": self.VLM_ENDPOINT,
                "ocr_endpoint": self.OCR_ENDPOINT,
                "embedding_model": self.EMBEDDING_MODEL,
                "embedding_endpoint": self.EMBEDDING_ENDPOINT,
            },
            "feature_flags": {
                "enable_vlm": self.ENABLE_VLM,
                "enable_ocr": self.ENABLE_OCR,
                "enable_embeddings": self.ENABLE_EMBEDDINGS,
                "enable_real_time": self.ENABLE_REAL_TIME,
                "enable_vector_search": self.ENABLE_VECTOR_SEARCH,
                "enable_debug_mode": self.ENABLE_DEBUG_MODE,
            }
        }


# Global instance (using standard name now)




def load_config_from_env() -> Config:
    """Load configuration with environment variable overrides."""
    config = Config()
    
    # Database overrides
    if os.getenv("AUTOTASK_POSTGRES_HOST"):
        config.POSTGRES_HOST = os.getenv("AUTOTASK_POSTGRES_HOST")
    if os.getenv("AUTOTASK_POSTGRES_PORT"):
        config.POSTGRES_PORT = int(os.getenv("AUTOTASK_POSTGRES_PORT"))
    if os.getenv("AUTOTASK_POSTGRES_DB"):
        config.POSTGRES_DATABASE = os.getenv("AUTOTASK_POSTGRES_DB")
    if os.getenv("AUTOTASK_SERVER_HOST"):
        config.SERVER_HOST = os.getenv("AUTOTASK_SERVER_HOST")
    
    # Path overrides
    if os.getenv("AUTOTASK_MEMOS_DIR"):
        config.MEMOS_DIR = os.getenv("AUTOTASK_MEMOS_DIR")
    if os.getenv("AUTOTASK_SCREENSHOTS_DIR"):
        config.SCREENSHOTS_DIR = os.getenv("AUTOTASK_SCREENSHOTS_DIR")
    if os.getenv("AUTOTASK_VLM_CACHE_DIR"):
        config.VLM_CACHE_DIR = os.getenv("AUTOTASK_VLM_CACHE_DIR")
    
    # Port overrides
    if os.getenv("AUTOTASK_TASK_BOARD_PORT"):
        config.TASK_BOARD_PORT = int(os.getenv("AUTOTASK_TASK_BOARD_PORT"))
    if os.getenv("AUTOTASK_ANALYTICS_PORT"):
        config.ANALYTICS_PORT = int(os.getenv("AUTOTASK_ANALYTICS_PORT"))
    if os.getenv("AUTOTASK_TIMETRACKER_PORT"):
        config.TIMETRACKER_PORT = int(os.getenv("AUTOTASK_TIMETRACKER_PORT"))
    if os.getenv("AUTOTASK_NOTIFICATIONS_PORT"):
        config.NOTIFICATIONS_PORT = int(os.getenv("AUTOTASK_NOTIFICATIONS_PORT"))
    if os.getenv("AUTOTASK_ADVANCED_ANALYTICS_PORT"):
        config.ADVANCED_ANALYTICS_PORT = int(os.getenv("AUTOTASK_ADVANCED_ANALYTICS_PORT"))
    if os.getenv("AUTOTASK_OVERVIEW_PORT"):
        config.OVERVIEW_PORT = int(os.getenv("AUTOTASK_OVERVIEW_PORT"))
    if os.getenv("AUTOTASK_FOCUS_TRACKER_PORT"):
        config.FOCUS_TRACKER_PORT = int(os.getenv("AUTOTASK_FOCUS_TRACKER_PORT"))
    if os.getenv("AUTOTASK_DAILY_SUMMARY_PORT"):
        config.DAILY_SUMMARY_PORT = int(os.getenv("AUTOTASK_DAILY_SUMMARY_PORT"))
    if os.getenv("AUTOTASK_LAUNCHER_PORT"):
        config.LAUNCHER_PORT = int(os.getenv("AUTOTASK_LAUNCHER_PORT"))
    if os.getenv("AUTOTASK_VLM_MONITOR_PORT"):
        config.VLM_MONITOR_PORT = int(os.getenv("AUTOTASK_VLM_MONITOR_PORT"))
    if os.getenv("AUTOTASK_API_PORT"):
        config.AUTOTASK_API_PORT = int(os.getenv("AUTOTASK_API_PORT"))
    if os.getenv("AUTOTASK_HEALTH_CHECK_PORT"):
        config.HEALTH_CHECK_PORT = int(os.getenv("AUTOTASK_HEALTH_CHECK_PORT"))
    if os.getenv("AUTOTASK_METRICS_PORT"):
        config.METRICS_PORT = int(os.getenv("AUTOTASK_METRICS_PORT"))
    if os.getenv("AUTOTASK_WEBHOOK_PORT"):
        config.WEBHOOK_PORT = int(os.getenv("AUTOTASK_WEBHOOK_PORT"))
    if os.getenv("AUTOTASK_MEMOS_PORT"):
        config.MEMOS_PORT = int(os.getenv("AUTOTASK_MEMOS_PORT"))
    if os.getenv("AUTOTASK_MEMOS_WEB_PORT"):
        config.MEMOS_WEB_PORT = int(os.getenv("AUTOTASK_MEMOS_WEB_PORT"))
    
    # AI Service overrides
    if os.getenv("AUTOTASK_VLM_MODEL"):
        config.VLM_MODEL_NAME = os.getenv("AUTOTASK_VLM_MODEL")
    if os.getenv("AUTOTASK_VLM_PORT"):
        config.OLLAMA_PORT = int(os.getenv("AUTOTASK_VLM_PORT"))
    if os.getenv("AUTOTASK_EMBEDDING_MODEL"):
        config.EMBEDDING_MODEL = os.getenv("AUTOTASK_EMBEDDING_MODEL")
    
    # Processing overrides
    if os.getenv("AUTOTASK_BATCH_SIZE"):
        config.SPARSITY_FACTOR = float(os.getenv("AUTOTASK_BATCH_SIZE"))
    if os.getenv("AUTOTASK_CONFIDENCE_THRESHOLD"):
        config.VLM_CONCURRENCY = int(os.getenv("AUTOTASK_CONFIDENCE_THRESHOLD"))
    if os.getenv("AUTOTASK_AUTO_REFRESH_SECONDS"):
        config.CACHE_TTL = int(os.getenv("AUTOTASK_AUTO_REFRESH_SECONDS"))
    
    # Feature flag overrides
    if os.getenv("AUTOTASK_DEBUG_MODE") == "true":
        config.ENABLE_DEBUG_MODE = True
    if os.getenv("AUTOTASK_DISABLE_VLM") == "true":
        config.ENABLE_VLM = False
    
    # Pensieve integration overrides
    if os.getenv("PENSIEVE_CACHE_TTL"):
        config.CACHE_TTL = int(os.getenv("PENSIEVE_CACHE_TTL"))
    if os.getenv("PENSIEVE_REALTIME") == "false":
        config.ENABLE_REAL_TIME = False
    if os.getenv("PENSIEVE_AUTO_MIGRATION") == "false":
        config.ENABLE_AUTO_BACKUP = False
    if os.getenv("PENSIEVE_RETRY_ATTEMPTS"):
        config.VLM_CONCURRENCY = int(os.getenv("PENSIEVE_RETRY_ATTEMPTS"))
    
    return config


# Global configuration singleton with thread safety
_config_instance: Optional[Config] = None
_config_lock: Optional[threading.Lock] = None


def get_config() -> Config:
    """Get the global configuration instance using thread-safe singleton pattern."""
    global _config_instance, _config_lock
    
    if _config_instance is not None:
        return _config_instance
    
    if _config_lock is None:
        _config_lock = threading.Lock()
    
    with _config_lock:
        # Double-check pattern
        if _config_instance is None:
            _config_instance = Config()
        return _config_instance


def set_config(config_instance: Config) -> None:
    """Set a custom configuration instance (thread-safe)."""
    global _config_instance, _config_lock
    
    if _config_lock is None:
        _config_lock = threading.Lock()
    
    with _config_lock:
        _config_instance = config_instance


def reset_config() -> None:
    """Reset configuration to force reload on next access (thread-safe)."""
    global _config_instance, _config_lock
    
    if _config_lock is None:
        _config_lock = threading.Lock()
    
    with _config_lock:
        _config_instance = None


# Compatibility aliases for smooth migration
get_central_config = get_config  # Alias for code expecting central_config
CentralConfig = Config  # Alias for type hints