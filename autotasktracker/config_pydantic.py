"""
Pydantic-based configuration management for AutoTaskTracker.
Modern, type-safe configuration with automatic validation.
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    """Database configuration with validation."""
    
    path: str = Field(
        default_factory=lambda: os.path.expanduser("~/.memos/database.db"),
        description="Path to SQLite database file"
    )
    connection_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Database connection pool size"
    )
    query_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Database query timeout in seconds"
    )
    
    @field_validator('path')
    @classmethod
    def validate_database_path(cls, v):
        """Validate database path security and format."""
        if not v:
            raise ValueError("Database path cannot be empty")
        
        # Expand user path
        expanded = os.path.expanduser(v)
        
        # Security validation - prevent dangerous paths
        dangerous_patterns = ['/etc/', '/bin/', '/usr/bin/', '/sbin/', '/var/log/']
        for pattern in dangerous_patterns:
            if pattern in expanded.lower():
                raise ValueError(f"Database path not allowed in system directory: {pattern}")
        
        # Ensure .db extension for SQLite
        if not expanded.endswith('.db'):
            expanded += '.db'
            
        return expanded

    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_DATABASE_",
        env_nested_delimiter="__"
    )

class ServerSettings(BaseSettings):
    """Server and port configuration with validation."""
    
    host: str = Field(
        default="localhost",
        description="Server hostname"
    )
    memos_port: int = Field(
        default=8839,
        ge=1024,
        le=65535,
        description="Pensieve/memos API port"
    )
    memos_web_port: int = Field(
        default=8840,
        ge=1024,
        le=65535,
        description="Pensieve/memos web interface port"
    )
    task_board_port: int = Field(
        default=8502,
        ge=1024,
        le=65535,
        description="Task board dashboard port"
    )
    analytics_port: int = Field(
        default=8503,
        ge=1024,
        le=65535,
        description="Analytics dashboard port"
    )
    timetracker_port: int = Field(
        default=8505,
        ge=1024,
        le=65535,
        description="Time tracker dashboard port"
    )
    notifications_port: int = Field(
        default=8506,
        ge=1024,
        le=65535,
        description="Notifications service port"
    )
    advanced_analytics_port: int = Field(
        default=8507,
        ge=1024,
        le=65535,
        description="Advanced analytics dashboard port"
    )
    overview_port: int = Field(
        default=8508,
        ge=1024,
        le=65535,
        description="Overview dashboard port"
    )
    focus_tracker_port: int = Field(
        default=8509,
        ge=1024,
        le=65535,
        description="Focus tracker dashboard port"
    )
    daily_summary_port: int = Field(
        default=8510,
        ge=1024,
        le=65535,
        description="Daily summary dashboard port"
    )
    
    @field_validator('memos_port', 'memos_web_port', 'task_board_port', 'analytics_port', 'timetracker_port', 'notifications_port', 'advanced_analytics_port', 'overview_port', 'focus_tracker_port', 'daily_summary_port')
    @classmethod
    def validate_ports_unique(cls, v, info):
        """Ensure all ports are unique to prevent conflicts."""
        if not info.data:
            return v
        
        # Get all port values that have been validated so far
        port_fields = ['memos_port', 'memos_web_port', 'task_board_port', 'analytics_port', 'timetracker_port', 'notifications_port', 'advanced_analytics_port', 'overview_port', 'focus_tracker_port', 'daily_summary_port']
        existing_ports = []
        
        for field_name in port_fields:
            if field_name in info.data and field_name != info.field_name:
                port_value = info.data[field_name]
                if port_value is not None:  # Handle None values gracefully
                    existing_ports.append(port_value)
        
        # Validate port is not None and is in valid range
        if v is None:
            raise ValueError("Port cannot be None")
        
        if v in existing_ports:
            field_names = [name for name in port_fields if name in info.data and info.data[name] == v and name != info.field_name]
            raise ValueError(f"Port {v} conflicts with port(s) used by: {', '.join(field_names)}")
        
        return v

    def model_post_init(self, __context) -> None:
        """Additional validation after model initialization."""
        # Collect all port values for comprehensive uniqueness check
        port_fields = ['memos_port', 'memos_web_port', 'task_board_port', 'analytics_port', 
                      'timetracker_port', 'notifications_port', 'advanced_analytics_port', 
                      'overview_port', 'focus_tracker_port', 'daily_summary_port']
        
        port_values = {}
        for field_name in port_fields:
            port_value = getattr(self, field_name)
            if port_value in port_values:
                raise ValueError(f"Port {port_value} is used by both {port_values[port_value]} and {field_name}")
            port_values[port_value] = field_name

    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_SERVER_",
        env_nested_delimiter="__"
    )

class VLMSettings(BaseSettings):
    """VLM (Visual Language Model) configuration."""
    
    model: str = Field(
        default="minicpm-v",
        description="VLM model name"
    )
    port: int = Field(
        default=11434,
        ge=1024,
        le=65535,
        description="VLM service port (Ollama)"
    )
    cache_dir: str = Field(
        default_factory=lambda: os.path.expanduser("~/.memos/vlm_cache"),
        description="VLM cache directory"
    )
    
    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v):
        """Validate VLM model name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("VLM model name cannot be empty")
        
        # Basic sanitization
        sanitized = v.strip().lower()
        if len(sanitized) > 100:
            raise ValueError("VLM model name too long (max 100 characters)")
        
        return sanitized

    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_VLM_",
        env_nested_delimiter="__"
    )

class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""
    
    model: str = Field(
        default="jina-embeddings-v2-base-en",
        description="Embedding model name"
    )
    dimension: int = Field(
        default=768,
        ge=1,
        le=10000,
        description="Embedding vector dimension"
    )
    
    @field_validator('model')
    @classmethod
    def validate_embedding_model(cls, v):
        """Validate embedding model name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Embedding model name cannot be empty")
        return v.strip()

    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_EMBEDDING_",
        env_nested_delimiter="__"
    )

class ProcessingSettings(BaseSettings):
    """Processing and performance configuration."""
    
    batch_size: int = Field(
        default=50,
        ge=1,
        le=10000,
        description="Processing batch size"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="AI confidence threshold"
    )
    auto_refresh_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="Auto refresh interval in seconds"
    )
    cache_ttl_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Cache TTL in seconds"
    )
    screenshot_interval_seconds: int = Field(
        default=4,
        ge=1,
        le=60,
        description="Screenshot capture interval"
    )

    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_PROCESSING_",
        env_nested_delimiter="__"
    )

class SecuritySettings(BaseSettings):
    """Security and secrets configuration."""
    
    # Example secret field (would be populated from environment)
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for external services"
    )
    
    # Path validation settings
    max_path_length: int = Field(
        default=255,
        ge=50,
        le=1000,
        description="Maximum allowed path length"
    )
    
    # Port validation settings
    privileged_port_threshold: int = Field(
        default=1024,
        ge=1,
        le=1024,
        description="Minimum port number for non-privileged ports"
    )

    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_SECURITY_",
        env_nested_delimiter="__"
    )

class AutoTaskSettings(BaseSettings):
    """Main AutoTaskTracker configuration using Pydantic-Settings."""
    
    # Nested configuration sections
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    vlm: VLMSettings = Field(default_factory=VLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    
    # Top-level settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    app_name: str = Field(
        default="AutoTaskTracker",
        description="Application name"
    )
    
    # Directory settings
    screenshots_dir: str = Field(
        default_factory=lambda: os.path.expanduser("~/.memos/screenshots"),
        description="Screenshots directory"
    )
    logs_dir: str = Field(
        default_factory=lambda: os.path.expanduser("~/.memos/logs"),
        description="Logs directory"
    )
    
    # Feature flags
    show_screenshots: bool = Field(
        default=True,
        description="Show screenshots in UI"
    )
    enable_notifications: bool = Field(
        default=True,
        description="Enable system notifications"
    )
    enable_analytics: bool = Field(
        default=True,
        description="Enable analytics tracking"
    )
    
    # Pensieve integration
    use_pensieve_api: bool = Field(
        default=True,
        description="Use Pensieve API integration"
    )
    pensieve_config_sync: bool = Field(
        default=True,
        description="Sync configuration with Pensieve"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="AUTOTASK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__"  # For nested settings like DATABASE__PATH
    )
    
    @field_validator('screenshots_dir', 'logs_dir')
    @classmethod
    def validate_directory_paths(cls, v):
        """Validate directory paths and create if needed."""
        if not v:
            raise ValueError("Directory path cannot be empty")
        
        expanded = os.path.expanduser(v)
        
        # Create directory if it doesn't exist
        try:
            Path(expanded).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Don't fail validation, just warn
            import logging
            logging.getLogger(__name__).warning(f"Could not create directory {expanded}: {e}")
        
        return expanded
    
    def get_db_path(self) -> str:
        """Get database path (compatibility method)."""
        return self.database.path
    
    def get_vlm_cache_path(self) -> str:
        """Get VLM cache directory path."""
        return self.vlm.cache_dir
    
    def get_screenshots_path(self) -> str:
        """Get screenshots directory path."""
        return self.screenshots_dir
    
    def get_ollama_url(self) -> str:
        """Get Ollama API URL with validation."""
        # Check environment variable first
        env_url = os.getenv('OLLAMA_URL')
        if env_url:
            # Basic URL validation
            if env_url.startswith(('http://', 'https://')) and '://' in env_url:
                return env_url
            else:
                import logging
                logging.getLogger(__name__).warning(f"Invalid OLLAMA_URL format, using default: {env_url}")
        
        return f"http://{self.server.host}:{self.vlm.port}"
    
    def model_post_init(self, __context) -> None:
        """Additional validation after model initialization."""
        # Cross-settings port validation
        all_ports = {
            'server.memos': self.server.memos_port,
            'server.memos_web': self.server.memos_web_port,
            'server.task_board': self.server.task_board_port,
            'server.analytics': self.server.analytics_port,
            'server.timetracker': self.server.timetracker_port,
            'server.notifications': self.server.notifications_port,
            'server.advanced_analytics': self.server.advanced_analytics_port,
            'server.overview': self.server.overview_port,
            'server.focus_tracker': self.server.focus_tracker_port,
            'server.daily_summary': self.server.daily_summary_port,
            'vlm': self.vlm.port
        }
        
        # Check for conflicts
        port_to_service = {}
        for service, port in all_ports.items():
            if port in port_to_service:
                raise ValueError(
                    f"Port conflict: {service} and {port_to_service[port]} "
                    f"both configured to use port {port}"
                )
            port_to_service[port] = service
    
    def get_service_url(self, service_name: str) -> str:
        """Get service URL for a given service name."""
        if not isinstance(service_name, str) or not service_name:
            return ""
        
        service_ports = {
            'memos': self.server.memos_port,
            'task_board': self.server.task_board_port,
            'analytics': self.server.analytics_port,
            'timetracker': self.server.timetracker_port,
        }
        
        port = service_ports.get(service_name.lower())
        if port is None:
            return ""
        
        return f"http://{self.server.host}:{port}"
    
    # Legacy compatibility properties and methods
    @property
    def db_path(self) -> str:
        """Legacy compatibility for database path."""
        return self.database.path
    
    @property
    def vlm_cache_dir(self) -> str:
        """Legacy compatibility for VLM cache directory."""
        return self.vlm.cache_dir
    
    @property
    def DB_PATH(self) -> str:
        """Legacy compatibility for database path."""
        return self.database.path
    
    @property
    def MEMOS_PORT(self) -> int:
        """Legacy compatibility for memos port."""
        return self.server.memos_port
    
    @property
    def TASK_BOARD_PORT(self) -> int:
        """Legacy compatibility for task board port."""
        return self.server.task_board_port
    
    @property
    def ANALYTICS_PORT(self) -> int:
        """Legacy compatibility for analytics port."""
        return self.server.analytics_port
    
    @property
    def TIME_TRACKER_PORT(self) -> int:
        """Legacy compatibility for time tracker port."""
        return self.server.timetracker_port
    
    @property
    def TIMETRACKER_PORT(self) -> int:
        """Legacy compatibility for timetracker port (without underscore).
        
        DEPRECATED: Use TIME_TRACKER_PORT or config.server.timetracker_port instead.
        This property will be removed in a future version.
        """
        return self.server.timetracker_port
    
    @property
    def MEMOS_WEB_PORT(self) -> int:
        """Legacy compatibility for memos web port."""
        return self.server.memos_web_port
    
    @property
    def NOTIFICATIONS_PORT(self) -> int:
        """Legacy compatibility for notifications port."""
        return self.server.notifications_port
    
    @property
    def ADVANCED_ANALYTICS_PORT(self) -> int:
        """Legacy compatibility for advanced analytics port."""
        return self.server.advanced_analytics_port
    
    @property
    def OVERVIEW_PORT(self) -> int:
        """Legacy compatibility for overview port."""
        return self.server.overview_port
    
    @property
    def FOCUS_TRACKER_PORT(self) -> int:
        """Legacy compatibility for focus tracker port."""
        return self.server.focus_tracker_port
    
    @property
    def DAILY_SUMMARY_PORT(self) -> int:
        """Legacy compatibility for daily summary port."""
        return self.server.daily_summary_port
    
    @property
    def memos_dir_property(self) -> Path:
        """Legacy compatibility for memos directory property."""
        return Path(self.database.path).parent
    
    @property
    def SCREENSHOTS_DIR(self) -> str:
        """Legacy compatibility for screenshots directory."""
        return self.screenshots_dir
    
    @property
    def LOGS_DIR(self) -> str:
        """Legacy compatibility for logs directory."""
        return self.logs_dir
    
    @property
    def VLM_CACHE_DIR(self) -> str:
        """Legacy compatibility for VLM cache directory."""
        return self.vlm.cache_dir
    
    @property
    def DEFAULT_TASK_LIMIT(self) -> int:
        """Legacy compatibility for default task limit."""
        return 100
    
    @property
    def GROUP_INTERVAL_MINUTES(self) -> int:
        """Legacy compatibility for group interval."""
        return 5
    
    @property
    def MIN_SESSION_DURATION_SECONDS(self) -> int:
        """Legacy compatibility for minimum session duration."""
        return 30
    
    @property
    def MAX_SESSION_GAP_SECONDS(self) -> int:
        """Legacy compatibility for maximum session gap."""
        return 600
    
    @property
    def IDLE_THRESHOLD_SECONDS(self) -> int:
        """Legacy compatibility for idle threshold."""
        return 300
    
    @property
    def MAX_SCREENSHOT_SIZE(self) -> int:
        """Legacy compatibility for max screenshot size."""
        return 300
    
    @property
    def CONNECTION_POOL_SIZE(self) -> int:
        """Legacy compatibility for connection pool size."""
        return self.database.connection_pool_size
    
    @property
    def QUERY_TIMEOUT_SECONDS(self) -> int:
        """Legacy compatibility for query timeout."""
        return self.database.query_timeout_seconds
    
    @property
    def VLM_MODEL(self) -> str:
        """Legacy compatibility for VLM model."""
        return self.vlm.model
    
    @property
    def VLM_PORT(self) -> int:
        """Legacy compatibility for VLM port."""
        return self.vlm.port
    
    @property
    def EMBEDDING_MODEL(self) -> str:
        """Legacy compatibility for embedding model."""
        return self.embedding.model
    
    @property
    def EMBEDDING_DIM(self) -> int:
        """Legacy compatibility for embedding dimension."""
        return self.embedding.dimension
    
    @property
    def BATCH_SIZE(self) -> int:
        """Legacy compatibility for batch size."""
        return self.processing.batch_size
    
    @property
    def CONFIDENCE_THRESHOLD(self) -> float:
        """Legacy compatibility for confidence threshold."""
        return self.processing.confidence_threshold
    
    @property
    def AUTO_REFRESH_SECONDS(self) -> int:
        """Legacy compatibility for auto refresh."""
        return self.processing.auto_refresh_seconds
    
    @property
    def CACHE_TTL_SECONDS(self) -> int:
        """Legacy compatibility for cache TTL."""
        return self.processing.cache_ttl_seconds
    
    @property
    def SCREENSHOT_INTERVAL_SECONDS(self) -> int:
        """Legacy compatibility for screenshot interval."""
        return self.processing.screenshot_interval_seconds
    
    @property
    def SHOW_SCREENSHOTS(self) -> bool:
        """Legacy compatibility for show screenshots flag."""
        return self.show_screenshots
    
    @property
    def ENABLE_NOTIFICATIONS(self) -> bool:
        """Legacy compatibility for notifications flag."""
        return self.enable_notifications
    
    @property
    def ENABLE_ANALYTICS(self) -> bool:
        """Legacy compatibility for analytics flag."""
        return self.enable_analytics
    
    @property
    def USE_PENSIEVE_API(self) -> bool:
        """Legacy compatibility for Pensieve API flag."""
        return self.use_pensieve_api
    
    @property
    def PENSIEVE_CONFIG_SYNC(self) -> bool:
        """Legacy compatibility for Pensieve config sync flag."""
        return self.pensieve_config_sync
    
    def validate(self) -> bool:
        """Legacy compatibility for validation method."""
        return self.validate_configuration()
    
    def to_dict(self) -> dict:
        """Legacy compatibility for dict conversion."""
        return {
            "db_path": self.database.path,
            "vlm_model": self.vlm.model,
            "vlm_port": self.vlm.port,
            "embedding_model": self.embedding.model,
            "embedding_dim": self.embedding.dimension,
            "batch_size": self.processing.batch_size,
            "confidence_threshold": self.processing.confidence_threshold,
            "ports": {
                "task_board": self.server.task_board_port,
                "analytics": self.server.analytics_port,
                "time_tracker": self.server.timetracker_port,
                "memos": self.server.memos_port
            }
        }
    
    def validate_configuration(self) -> bool:
        """Validate the complete configuration."""
        try:
            # Database directory validation
            db_dir = Path(self.database.path).parent
            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                except OSError:
                    return False
            
            # Port uniqueness validation (already handled by validators)
            # Cross-settings port validation
            port_assignments = {
                'memos': self.server.memos_port,
                'memos_web': self.server.memos_web_port,
                'task_board': self.server.task_board_port,
                'analytics': self.server.analytics_port,
                'timetracker': self.server.timetracker_port,
                'notifications': self.server.notifications_port,
                'advanced_analytics': self.server.advanced_analytics_port,
                'overview': self.server.overview_port,
                'focus_tracker': self.server.focus_tracker_port,
                'daily_summary': self.server.daily_summary_port,
                'vlm': self.vlm.port
            }
            
            # Check for port conflicts across all settings
            port_usage = {}
            for service, port in port_assignments.items():
                if port in port_usage:
                    logger.error(f"Port conflict: {service} and {port_usage[port]} both use port {port}")
                    return False
                port_usage[port] = service
            
            return True
            
        except Exception:
            return False

# Singleton instance management
_pydantic_config_instance: Optional[AutoTaskSettings] = None

def get_pydantic_config() -> AutoTaskSettings:
    """Get the global Pydantic configuration instance."""
    global _pydantic_config_instance
    
    if _pydantic_config_instance is None:
        _pydantic_config_instance = AutoTaskSettings()
    
    return _pydantic_config_instance

def reset_pydantic_config() -> None:
    """Reset Pydantic configuration to force reload."""
    global _pydantic_config_instance
    _pydantic_config_instance = None