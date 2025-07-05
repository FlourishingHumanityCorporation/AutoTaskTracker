"""Pensieve configuration synchronization for AutoTaskTracker."""

import os
import yaml
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import json

from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class PensieveConfig:
    """Pensieve configuration data."""
    database_path: str
    screenshots_dir: str
    record_interval: int
    ocr_enabled: bool
    api_port: int
    web_port: int
    max_workers: int
    
    # Processing settings
    idle_processing: bool = True
    sampling_strategy: str = "adaptive"
    sparsity_factor: float = 1.0
    rate_window_seconds: int = 300
    
    # Storage settings
    max_storage_gb: float = 10.0
    cleanup_days: int = 30
    
    # Advanced features
    postgresql_enabled: bool = False
    vector_search_enabled: bool = False
    plugin_dir: Optional[str] = None


class PensieveConfigReader:
    """Reader for Pensieve/memos configuration."""
    
    def __init__(self):
        """Initialize config reader."""
        config = get_config()
        self.memos_dir = config.memos_dir_property
        self.config_file = self.memos_dir / "config.yaml"
        self._cached_config: Optional[PensieveConfig] = None
        self._cache_timestamp: float = 0
    
    def get_memos_status(self) -> Dict[str, Any]:
        """Get current memos service status."""
        try:
            # Use memos command directly (it should be in PATH)
            result = subprocess.run(
                ["memos", "ps"],
                capture_output=True,
                    text=True,
                    timeout=10
                )
            
            if result.returncode == 0:
                return {
                    "running": True,
                    "output": result.stdout.strip(),
                    "process_info": self._parse_process_info(result.stdout)
                }
            else:
                return {
                    "running": False,
                    "error": result.stderr.strip(),
                    "output": result.stdout.strip()
                }
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Failed to get memos status: {e}")
            return {
                "running": False,
                "error": str(e),
                "output": ""
            }
    
    def _parse_process_info(self, output: str) -> Dict[str, Any]:
        """Parse process information from memos ps output."""
        info = {
            "services": [],
            "ports": {},
            "status": "unknown"
        }
        
        try:
            lines = output.strip().split('\n')
            for line in lines:
                if "API" in line and ":" in line:
                    # Extract API port
                    parts = line.split(":")
                    if len(parts) > 1:
                        port_part = parts[-1].strip()
                        if port_part.isdigit():
                            info["ports"]["api"] = int(port_part)
                
                if "Web" in line and ":" in line:
                    # Extract Web port
                    parts = line.split(":")
                    if len(parts) > 1:
                        port_part = parts[-1].strip()
                        if port_part.isdigit():
                            info["ports"]["web"] = int(port_part)
                
                if "running" in line.lower():
                    info["status"] = "running"
                elif "stopped" in line.lower():
                    info["status"] = "stopped"
                    
        except Exception as e:
            logger.debug(f"Failed to parse process info: {e}")
        
        return info
    
    def read_pensieve_config(self, force_refresh: bool = False) -> PensieveConfig:
        """Read Pensieve configuration from memos config files.
        
        Args:
            force_refresh: Force refresh from disk
            
        Returns:
            PensieveConfig object with current settings
        """
        # Check cache
        current_time = os.path.getmtime(self.config_file) if self.config_file.exists() else 0
        
        if not force_refresh and self._cached_config and current_time <= self._cache_timestamp:
            return self._cached_config
        
        config_data = self._load_config_from_files()
        pensieve_config = self._build_pensieve_config(config_data)
        
        # Update cache
        self._cached_config = pensieve_config
        self._cache_timestamp = current_time
        
        return pensieve_config
    
    def _load_config_from_files(self) -> Dict[str, Any]:
        """Load configuration from various memos config sources."""
        config_data = {}
        
        # Default values
        app_config = get_config()
        config_data.update({
            "database_path": app_config.get_db_path(),
            "screenshots_dir": app_config.get_screenshots_path(),
            "record_interval": app_config.SCREENSHOT_INTERVAL_SECONDS,
            "ocr_enabled": True,
            "api_port": app_config.MEMOS_PORT,
            "web_port": app_config.MEMOS_WEB_PORT,
            "max_workers": 4,
            "idle_processing": True,
            "sampling_strategy": "adaptive",
            "sparsity_factor": 1.0,
            "rate_window_seconds": 300,
            "max_storage_gb": 10.0,
            "cleanup_days": 30,
            "postgresql_enabled": False,
            "vector_search_enabled": False,
            "plugin_dir": None
        })
        
        # Load from YAML config file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    yaml_config = yaml.safe_load(f) or {}
                
                # Ensure database_path is expanded to full path if it's relative
                if 'database_path' in yaml_config:
                    db_path = yaml_config['database_path']
                    if not os.path.isabs(db_path):
                        # If relative path, make it relative to memos directory
                        yaml_config['database_path'] = str(self.memos_dir / db_path)
                
                config_data.update(yaml_config)
                logger.debug(f"Loaded config from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load YAML config: {e}")
        
        # Load from environment variables
        env_mappings = {
            "MEMOS_DB_PATH": "database_path",
            "MEMOS_SCREENSHOTS_DIR": "screenshots_dir", 
            "MEMOS_RECORD_INTERVAL": "record_interval",
            "MEMOS_API_PORT": "api_port",
            "MEMOS_WEB_PORT": "web_port",
            "MEMOS_MAX_WORKERS": "max_workers",
            "MEMOS_OCR_ENABLED": "ocr_enabled",
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Type conversion
                if config_key in ["record_interval", "api_port", "web_port", "max_workers"]:
                    try:
                        config_data[config_key] = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {env_value}")
                elif config_key in ["ocr_enabled"]:
                    config_data[config_key] = env_value.lower() in ["true", "1", "yes", "on"]
                else:
                    config_data[config_key] = env_value
        
        # Load from memos service status (ports, etc.)
        status = self.get_memos_status()
        if status["running"] and "process_info" in status:
            process_info = status["process_info"]
            if "ports" in process_info:
                if "api" in process_info["ports"]:
                    config_data["api_port"] = process_info["ports"]["api"]
                if "web" in process_info["ports"]:
                    config_data["web_port"] = process_info["ports"]["web"]
        
        return config_data
    
    def _build_pensieve_config(self, config_data: Dict[str, Any]) -> PensieveConfig:
        """Build PensieveConfig object from raw config data."""
        return PensieveConfig(
            database_path=config_data["database_path"],
            screenshots_dir=config_data["screenshots_dir"],
            record_interval=config_data["record_interval"],
            ocr_enabled=config_data["ocr_enabled"],
            api_port=config_data["api_port"],
            web_port=config_data["web_port"],
            max_workers=config_data["max_workers"],
            idle_processing=config_data["idle_processing"],
            sampling_strategy=config_data["sampling_strategy"],
            sparsity_factor=config_data["sparsity_factor"],
            rate_window_seconds=config_data["rate_window_seconds"],
            max_storage_gb=config_data["max_storage_gb"],
            cleanup_days=config_data["cleanup_days"],
            postgresql_enabled=config_data["postgresql_enabled"],
            vector_search_enabled=config_data["vector_search_enabled"],
            plugin_dir=config_data["plugin_dir"]
        )
    
    def sync_autotasktracker_config(self) -> Dict[str, Any]:
        """Synchronize AutoTaskTracker config with Pensieve settings.
        
        Returns:
            Dictionary of synchronized config values for AutoTaskTracker
        """
        pensieve_config = self.read_pensieve_config()
        
        return {
            # Database settings
            "DB_PATH": pensieve_config.database_path,
            "SCREENSHOTS_DIR": pensieve_config.screenshots_dir,
            
            # Timing settings  
            "SCREENSHOT_INTERVAL_SECONDS": pensieve_config.record_interval,
            
            # Service ports
            "MEMOS_PORT": pensieve_config.api_port,
            "MEMOS_WEB_PORT": pensieve_config.web_port,
            
            # Processing settings
            "MAX_WORKERS": pensieve_config.max_workers,
            "OCR_ENABLED": pensieve_config.ocr_enabled,
            "IDLE_PROCESSING": pensieve_config.idle_processing,
            
            # Storage settings
            "MAX_STORAGE_GB": pensieve_config.max_storage_gb,
            "CLEANUP_DAYS": pensieve_config.cleanup_days,
            
            # Feature flags
            "POSTGRESQL_ENABLED": pensieve_config.postgresql_enabled,
            "VECTOR_SEARCH_ENABLED": pensieve_config.vector_search_enabled,
            
            # API settings
            "PENSIEVE_API_URL": f"http://{get_config().SERVER_HOST}:{pensieve_config.api_port}",
            "PENSIEVE_WEB_URL": f"http://{get_config().SERVER_HOST}:{pensieve_config.web_port}",
        }
    
    def write_autotasktracker_config(self, output_path: Optional[Union[str, Path]] = None) -> bool:
        """Write synchronized config to AutoTaskTracker config file.
        
        Args:
            output_path: Path to write config file, defaults to project config
            
        Returns:
            True if successful, False otherwise
        """
        if output_path is None:
            # Default to AutoTaskTracker config directory
            project_root = Path(__file__).parent.parent.parent
            output_path = project_root / "config" / "pensieve_sync.json"
            output_path.parent.mkdir(exist_ok=True)
        
        try:
            sync_config = self.sync_autotasktracker_config()
            
            with open(output_path, 'w') as f:
                json.dump(sync_config, f, indent=2)
            
            logger.info(f"Wrote synchronized config to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write synchronized config: {e}")
            return False
    
    def validate_pensieve_setup(self) -> Dict[str, Any]:
        """Validate Pensieve setup and configuration.
        
        Returns:
            Validation results with status and issues
        """
        validation = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "config": None,
            "status": None
        }
        
        try:
            # Check memos service status
            status = self.get_memos_status()
            validation["status"] = status
            
            if not status["running"]:
                validation["valid"] = False
                validation["issues"].append("Memos service is not running")
            
            # Check config file
            if not self.config_file.exists():
                validation["warnings"].append(f"No config file found at {self.config_file}")
            
            # Check database path
            config = self.read_pensieve_config()
            validation["config"] = config
            
            db_path = Path(config.database_path)
            if not db_path.exists():
                validation["issues"].append(f"Database file not found: {config.database_path}")
                validation["valid"] = False
            
            # Check screenshots directory
            screenshots_dir = Path(config.screenshots_dir)
            if not screenshots_dir.exists():
                validation["warnings"].append(f"Screenshots directory not found: {config.screenshots_dir}")
            
            # Check ports
            if config.api_port < 1024 or config.api_port > 65535:
                validation["warnings"].append(f"API port out of range: {config.api_port}")
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Configuration validation failed: {e}")
        
        return validation


# Singleton instance
_config_reader: Optional[PensieveConfigReader] = None


def get_pensieve_config_reader() -> PensieveConfigReader:
    """Get singleton Pensieve config reader."""
    global _config_reader
    if _config_reader is None:
        _config_reader = PensieveConfigReader()
    return _config_reader


def get_pensieve_config() -> PensieveConfig:
    """Get current Pensieve configuration."""
    return get_pensieve_config_reader().read_pensieve_config()


def sync_config() -> Dict[str, Any]:
    """Synchronize AutoTaskTracker with Pensieve configuration."""
    return get_pensieve_config_reader().sync_autotasktracker_config()