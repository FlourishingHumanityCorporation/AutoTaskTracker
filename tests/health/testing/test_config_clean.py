"""Comprehensive test coverage for the effectiveness validation configuration system."""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Import with fallback for different execution contexts
try:
    from .config import (
        ConfigManager, 
        EffectivenessConfig, 
        MutationConfig, 
        AnalysisConfig, 
        ValidationConfig
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from config import (
        ConfigManager, 
        EffectivenessConfig, 
        MutationConfig, 
        AnalysisConfig, 
        ValidationConfig
    )


class TestMutationConfig:
    """Test mutation configuration component."""
    
    def test_mutation_config_clean_default_values(self):
        """Test default configuration values."""
        config = MutationConfig()
        
        assert config.max_mutations_per_file == 10
        assert config.timeout_seconds == 30
        assert config.max_file_size_kb == 100
        assert isinstance(config.skip_patterns, list)
        assert '__pycache__' in config.skip_patterns


class TestEffectivenessConfig:
    """Test the main effectiveness configuration."""
    
    def test_default_initialization(self):
        """Test default initialization creates all sub-configs."""
        config = EffectivenessConfig()
        
        assert isinstance(config.mutation, MutationConfig)
        assert isinstance(config.analysis, AnalysisConfig)
        assert isinstance(config.validation, ValidationConfig)
        assert config.enable_parallel_execution is True
    
    def test_environment_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            'EFFECTIVENESS_MAX_MUTATIONS': '5',
            'EFFECTIVENESS_TIMEOUT': '20',
            'EFFECTIVENESS_PARALLEL': 'false'
        }):
            config = EffectivenessConfig.from_environment()
            
            assert config.mutation.max_mutations_per_file == 5
            assert config.mutation.timeout_seconds == 20
            assert config.enable_parallel_execution is False
    
    def test_validation_success(self):
        """Test successful configuration validation."""
        config = EffectivenessConfig()
        issues = config.validate()
        
        assert isinstance(issues, list)
        assert len(issues) == 0  # No issues with default config
    
    def test_validation_failures(self):
        """Test configuration validation with invalid values."""
        config = EffectivenessConfig()
        
        # Create invalid configuration
        config.mutation.max_mutations_per_file = 0
        config.max_worker_threads = 0
        
        issues = config.validate()
        
        assert len(issues) > 0
        assert any('max_mutations_per_file' in issue for issue in issues)
        assert any('max_worker_threads' in issue for issue in issues)


class TestConfigManager:
    """Test the configuration manager."""
    
    def test_initialization(self):
        """Test config manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            manager = ConfigManager(project_root)
            
            assert manager.project_root == project_root
    
    def test_get_config_defaults(self):
        """Test getting configuration with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            manager = ConfigManager(project_root)
            
            config = manager.get_config()
            
            assert isinstance(config, EffectivenessConfig)
            assert config.mutation.max_mutations_per_file == 10  # Default value


def test_configuration_integration():
    """Basic integration test."""
    config = EffectivenessConfig()
    assert config.mutation.max_mutations_per_file > 0
    assert config.validation.mutation_weight > 0