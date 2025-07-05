"""Comprehensive unit tests for mutation effectiveness configuration module.

This test suite validates the configuration management system for mutation testing,
including dataclasses, environment loading, file I/O, and validation.
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

from tests.health.testing.config import (
    MutationConfig,
    AnalysisConfig,
    ValidationConfig,
    EffectivenessConfig,
    ConfigManager
)
from tests.health.testing.shared_utilities import ValidationLimits


class TestMutationConfig:
    """Test the MutationConfig dataclass."""
    
    def test_mutation_config_default_values(self):
        """Test MutationConfig default values."""
        config = MutationConfig()
        
        assert config.max_mutations_per_file == ValidationLimits.MAX_MUTATIONS_PER_FILE
        assert config.timeout_seconds == ValidationLimits.DEFAULT_TIMEOUT_SECONDS
        assert config.max_file_size_kb == ValidationLimits.MAX_FILE_SIZE_KB
        assert config.skip_patterns == ['__pycache__', '.git', 'node_modules', '.pytest_cache']
        assert config.mutation_types == [
            'off_by_one',
            'boolean_flip',
            'condition_flip',
            'boundary_shift'
        ]
    
    def test_mutation_config_custom_values(self):
        """Test MutationConfig with custom values."""
        config = MutationConfig(
            max_mutations_per_file=50,
            timeout_seconds=60,
            max_file_size_kb=200,
            skip_patterns=['custom_skip'],
            mutation_types=['custom_type']
        )
        
        assert config.max_mutations_per_file == 50
        assert config.timeout_seconds == 60
        assert config.max_file_size_kb == 200
        assert config.skip_patterns == ['custom_skip']
        assert config.mutation_types == ['custom_type']


class TestAnalysisConfig:
    """Test the AnalysisConfig dataclass."""
    
    def test_analysis_config_default_values(self):
        """Test AnalysisConfig default values."""
        config = AnalysisConfig()
        
        assert config.max_files_per_test == 15
        assert config.max_analysis_time_seconds == ValidationLimits.MAX_ANALYSIS_TIME_SECONDS
        assert config.min_effectiveness_threshold == ValidationLimits.MIN_EFFECTIVENESS_THRESHOLD
        assert config.warning_effectiveness_threshold == ValidationLimits.WARNING_EFFECTIVENESS_THRESHOLD
        assert config.max_function_lines == ValidationLimits.MAX_FUNCTION_LINES
        assert config.max_hardcoded_items == ValidationLimits.MAX_HARDCODED_ITEMS
    
    def test_analysis_config_custom_values(self):
        """Test AnalysisConfig with custom values."""
        config = AnalysisConfig(
            max_files_per_test=25,
            max_analysis_time_seconds=600,
            min_effectiveness_threshold=60.0,
            warning_effectiveness_threshold=80.0,
            max_function_lines=50,
            max_hardcoded_items=5
        )
        
        assert config.max_files_per_test == 25
        assert config.max_analysis_time_seconds == 600
        assert config.min_effectiveness_threshold == 60.0
        assert config.warning_effectiveness_threshold == 80.0
        assert config.max_function_lines == 50
        assert config.max_hardcoded_items == 5


class TestValidationConfig:
    """Test the ValidationConfig dataclass."""
    
    def test_validation_config_default_values(self):
        """Test ValidationConfig default values."""
        config = ValidationConfig()
        
        assert config.mutation_weight == 0.6
        assert config.bug_pattern_weight == 0.3
        assert config.integration_weight == 0.1
        assert config.critical_threshold == ValidationLimits.MIN_EFFECTIVENESS_THRESHOLD
        assert config.warning_threshold == ValidationLimits.WARNING_EFFECTIVENESS_THRESHOLD
        assert config.max_overall_score == 100.0
    
    def test_validation_config_custom_values(self):
        """Test ValidationConfig with custom values."""
        config = ValidationConfig(
            mutation_weight=0.5,
            bug_pattern_weight=0.4,
            integration_weight=0.1,
            critical_threshold=40.0,
            warning_threshold=65.0,
            max_overall_score=100.0
        )
        
        assert config.mutation_weight == 0.5
        assert config.bug_pattern_weight == 0.4
        assert config.integration_weight == 0.1
        assert config.critical_threshold == 40.0
        assert config.warning_threshold == 65.0


class TestEffectivenessConfig:
    """Test the EffectivenessConfig dataclass."""
    
    def test_effectiveness_config_default_values(self):
        """Test EffectivenessConfig default values."""
        config = EffectivenessConfig()
        
        # Check nested configs
        assert isinstance(config.mutation, MutationConfig)
        assert isinstance(config.analysis, AnalysisConfig)
        assert isinstance(config.validation, ValidationConfig)
        
        # Check performance settings
        assert config.enable_parallel_execution is True
        assert config.max_worker_threads == 4
        
        # Check logging settings
        assert config.log_level == "INFO"
        assert config.log_detailed_errors is True
        
        # Check output settings
        assert config.max_recommendations == 5
        assert config.include_examples is True
    
    def test_from_environment_default(self):
        """Test loading config from environment with no env vars set."""
        config = EffectivenessConfig.from_environment()
        
        # Should use defaults when no env vars
        assert config.mutation.max_mutations_per_file == 10
        assert config.mutation.timeout_seconds == 30
        assert config.enable_parallel_execution is True
    
    def test_from_environment_with_vars(self):
        """Test loading config from environment variables."""
        env_vars = {
            'EFFECTIVENESS_MAX_MUTATIONS': '20',
            'EFFECTIVENESS_TIMEOUT': '45',
            'EFFECTIVENESS_MAX_FILE_SIZE': '150',
            'EFFECTIVENESS_MAX_FILES': '25',
            'EFFECTIVENESS_MAX_TIME': '400',
            'EFFECTIVENESS_MIN_THRESHOLD': '60.0',
            'EFFECTIVENESS_PARALLEL': 'false',
            'EFFECTIVENESS_MAX_WORKERS': '8',
            'EFFECTIVENESS_LOG_LEVEL': 'DEBUG',
            'EFFECTIVENESS_DETAILED_ERRORS': 'false'
        }
        
        with patch.dict(os.environ, env_vars):
            config = EffectivenessConfig.from_environment()
        
        assert config.mutation.max_mutations_per_file == 20
        assert config.mutation.timeout_seconds == 45
        assert config.mutation.max_file_size_kb == 150
        assert config.analysis.max_files_per_test == 25
        assert config.analysis.max_analysis_time_seconds == 400
        assert config.analysis.min_effectiveness_threshold == 60.0
        assert config.enable_parallel_execution is False
        assert config.max_worker_threads == 8
        assert config.log_level == 'DEBUG'
        assert config.log_detailed_errors is False
    
    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = EffectivenessConfig()
        config.mutation.max_mutations_per_file = 25
        config.enable_parallel_execution = False
        
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert 'mutation' in result
        assert 'analysis' in result
        assert 'validation' in result
        assert 'performance' in result
        assert 'logging' in result
        assert 'output' in result
        
        assert result['mutation']['max_mutations_per_file'] == 25
        assert result['performance']['enable_parallel_execution'] is False
    
    def test_validate_valid_config(self):
        """Test validating a valid configuration."""
        config = EffectivenessConfig()
        
        issues = config.validate()
        
        assert issues == []
    
    def test_validate_invalid_mutation_config(self):
        """Test validating invalid mutation configuration."""
        config = EffectivenessConfig()
        config.mutation.max_mutations_per_file = 0
        config.mutation.timeout_seconds = 3
        config.mutation.max_file_size_kb = 0
        
        issues = config.validate()
        
        assert "max_mutations_per_file must be at least 1" in issues
        assert "timeout_seconds must be at least 5" in issues
        assert "max_file_size_kb must be at least 1" in issues
    
    def test_validate_invalid_analysis_config(self):
        """Test validating invalid analysis configuration."""
        config = EffectivenessConfig()
        config.analysis.max_files_per_test = 0
        config.analysis.min_effectiveness_threshold = 150
        
        issues = config.validate()
        
        assert "max_files_per_test must be at least 1" in issues
        assert "min_effectiveness_threshold must be between 0 and 100" in issues
    
    def test_validate_invalid_validation_weights(self):
        """Test validating invalid validation weights."""
        config = EffectivenessConfig()
        config.validation.mutation_weight = 0.5
        config.validation.bug_pattern_weight = 0.3
        config.validation.integration_weight = 0.3  # Sum > 1.0
        
        issues = config.validate()
        
        assert any("weights must sum to 1.0" in issue for issue in issues)
    
    def test_validate_invalid_performance_config(self):
        """Test validating invalid performance configuration."""
        config = EffectivenessConfig()
        config.max_worker_threads = 0
        
        issues = config.validate()
        
        assert "max_worker_threads must be at least 1" in issues
    
    def test_save_to_file(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            config = EffectivenessConfig()
            config.mutation.max_mutations_per_file = 15
            
            config.save_to_file(config_file)
            
            assert config_file.exists()
            
            # Verify content
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            assert data['mutation']['max_mutations_per_file'] == 15
    
    def test_save_to_file_permission_error(self):
        """Test handling permission error when saving."""
        config = EffectivenessConfig()
        
        # Try to save to a read-only location
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")
            
            with pytest.raises((PermissionError, OSError)):
                config.save_to_file(Path("/readonly/config.json"))
    
    def test_load_from_file(self):
        """Test loading configuration from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Create test config data
            test_data = {
                'mutation': {
                    'max_mutations_per_file': 30,
                    'timeout_seconds': 60
                },
                'performance': {
                    'enable_parallel_execution': False,
                    'max_worker_threads': 2
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(test_data, f)
            
            config = EffectivenessConfig.load_from_file(config_file)
            
            assert config.mutation.max_mutations_per_file == 30
            assert config.mutation.timeout_seconds == 60
            assert config.enable_parallel_execution is False
            assert config.max_worker_threads == 2
    
    def test_load_from_file_missing_sections(self):
        """Test loading config file with missing sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "partial_config.json"
            
            # Create config with only some sections
            test_data = {
                'mutation': {
                    'max_mutations_per_file': 25
                }
                # Missing other sections
            }
            
            with open(config_file, 'w') as f:
                json.dump(test_data, f)
            
            config = EffectivenessConfig.load_from_file(config_file)
            
            # Should load partial config and use defaults for rest
            assert config.mutation.max_mutations_per_file == 25
            assert config.enable_parallel_execution is True  # Default
    
    def test_load_from_file_invalid_json(self):
        """Test handling invalid JSON when loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "invalid.json"
            config_file.write_text("{ invalid json")
            
            with pytest.raises(json.JSONDecodeError):
                EffectivenessConfig.load_from_file(config_file)
    
    def test_load_from_file_not_found(self):
        """Test handling file not found when loading."""
        config_file = Path("/nonexistent/config.json")
        
        with pytest.raises(OSError):
            EffectivenessConfig.load_from_file(config_file)


class TestConfigManager:
    """Test the ConfigManager class."""
    
    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project structure."""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir)
        
        # Create expected directory structure
        config_dir = project_root / "tests" / "health" / "testing"
        config_dir.mkdir(parents=True)
        
        yield project_root
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_config_manager_initialization(self, temp_project_root):
        """Test ConfigManager initialization."""
        manager = ConfigManager(temp_project_root)
        
        assert manager.project_root == temp_project_root
        assert manager.config_file == temp_project_root / "tests" / "health" / "testing" / "effectiveness_config.json"
        assert manager._config is None
    
    def test_get_config_default(self, temp_project_root):
        """Test getting config with defaults."""
        manager = ConfigManager(temp_project_root)
        
        config = manager.get_config()
        
        assert isinstance(config, EffectivenessConfig)
        assert config.mutation.max_mutations_per_file == 10  # Default
    
    def test_get_config_from_file(self, temp_project_root):
        """Test loading config from existing file."""
        manager = ConfigManager(temp_project_root)
        
        # Create config file
        config_data = {
            'mutation': {
                'max_mutations_per_file': 35
            }
        }
        
        with open(manager.config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = manager.get_config()
        
        assert config.mutation.max_mutations_per_file == 35
    
    def test_get_config_from_environment(self, temp_project_root):
        """Test loading config from environment when file doesn't exist."""
        manager = ConfigManager(temp_project_root)
        
        with patch.dict(os.environ, {'EFFECTIVENESS_MAX_MUTATIONS': '40'}):
            config = manager.get_config()
        
        assert config.mutation.max_mutations_per_file == 40
    
    def test_get_config_cached(self, temp_project_root):
        """Test that config is cached after first load."""
        manager = ConfigManager(temp_project_root)
        
        config1 = manager.get_config()
        config2 = manager.get_config()
        
        assert config1 is config2  # Same object
    
    def test_save_config(self, temp_project_root):
        """Test saving configuration."""
        manager = ConfigManager(temp_project_root)
        
        config = EffectivenessConfig()
        config.mutation.max_mutations_per_file = 45
        
        manager.save_config(config)
        
        assert manager.config_file.exists()
        assert manager._config == config
        
        # Verify saved content
        with open(manager.config_file, 'r') as f:
            data = json.load(f)
        
        assert data['mutation']['max_mutations_per_file'] == 45
    
    def test_save_config_invalid(self, temp_project_root):
        """Test saving invalid configuration."""
        manager = ConfigManager(temp_project_root)
        
        config = EffectivenessConfig()
        config.mutation.max_mutations_per_file = 0  # Invalid
        
        with pytest.raises(ValueError) as exc_info:
            manager.save_config(config)
        
        assert "max_mutations_per_file must be at least 1" in str(exc_info.value)
    
    def test_reset_to_defaults(self, temp_project_root):
        """Test resetting configuration to defaults."""
        manager = ConfigManager(temp_project_root)
        
        # Set custom config
        config = manager.get_config()
        original_max = config.mutation.max_mutations_per_file
        config.mutation.max_mutations_per_file = 50
        manager._config = config
        
        # Reset
        manager.reset_to_defaults()
        
        # Should be back to the default from ValidationLimits
        from tests.health.testing.shared_utilities import ValidationLimits
        assert manager._config.mutation.max_mutations_per_file == ValidationLimits.MAX_MUTATIONS_PER_FILE
    
    def test_get_environment_overrides(self, temp_project_root):
        """Test getting current environment overrides."""
        manager = ConfigManager(temp_project_root)
        
        env_vars = {
            'EFFECTIVENESS_MAX_MUTATIONS': '55',
            'EFFECTIVENESS_TIMEOUT': '90',
            'OTHER_VAR': 'ignore_this'
        }
        
        with patch.dict(os.environ, env_vars):
            overrides = manager.get_environment_overrides()
        
        assert overrides['EFFECTIVENESS_MAX_MUTATIONS'] == '55'
        assert overrides['EFFECTIVENESS_TIMEOUT'] == '90'
        assert 'OTHER_VAR' not in overrides
    
    def test_load_config_file_corrupted(self, temp_project_root):
        """Test fallback when config file is corrupted."""
        manager = ConfigManager(temp_project_root)
        
        # Create corrupted config file
        manager.config_file.write_text("corrupted data")
        
        # Should fall back to environment/defaults
        config = manager.get_config()
        
        assert isinstance(config, EffectivenessConfig)
        assert config.mutation.max_mutations_per_file == 10  # Default
    
    def test_config_directory_creation(self, temp_project_root):
        """Test that config directory is created if missing."""
        manager = ConfigManager(temp_project_root)
        
        # Remove the directory
        shutil.rmtree(manager.config_file.parent)
        
        config = EffectivenessConfig()
        manager.save_config(config)
        
        assert manager.config_file.parent.exists()
        assert manager.config_file.exists()


class TestConfigIntegration:
    """Test integration between config components."""
    
    def test_config_flow_end_to_end(self):
        """Test complete configuration flow from environment to validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "tests" / "health" / "testing").mkdir(parents=True)
            
            # Set environment variables
            env_vars = {
                'EFFECTIVENESS_MAX_MUTATIONS': '100',
                'EFFECTIVENESS_PARALLEL': 'false',
                'EFFECTIVENESS_MIN_THRESHOLD': '75.0'
            }
            
            with patch.dict(os.environ, env_vars):
                # Create manager and load config
                manager = ConfigManager(project_root)
                config = manager.get_config()
                
                # Verify environment values loaded
                assert config.mutation.max_mutations_per_file == 100
                assert config.enable_parallel_execution is False
                assert config.analysis.min_effectiveness_threshold == 75.0
                
                # Modify and save
                config.mutation.timeout_seconds = 120
                manager.save_config(config)
                
                # Create new manager and verify persistence
                manager2 = ConfigManager(project_root)
                config2 = manager2.get_config()
                
                assert config2.mutation.max_mutations_per_file == 100
                assert config2.mutation.timeout_seconds == 120
    
    def test_validation_weights_normalization(self):
        """Test that validation weights are properly used."""
        config = EffectivenessConfig()
        
        # Set custom weights that sum to 1.0
        config.validation.mutation_weight = 0.7
        config.validation.bug_pattern_weight = 0.2
        config.validation.integration_weight = 0.1
        
        issues = config.validate()
        assert issues == []
        
        # Test usage in calculation
        mutation_score = 80
        pattern_score = 60
        integration_score = 40
        
        overall = (
            mutation_score * config.validation.mutation_weight +
            pattern_score * config.validation.bug_pattern_weight +
            integration_score * config.validation.integration_weight
        )
        
        expected = 80 * 0.7 + 60 * 0.2 + 40 * 0.1
        assert overall == expected
        assert overall == 72.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])