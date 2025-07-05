"""Configuration management for effectiveness-based test validation.

This module provides centralized configuration for mutation testing, analysis limits,
and validation thresholds to make the system more maintainable and customizable.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Import shared constants
try:
    from .shared_utilities import ValidationLimits
except ImportError:
    from shared_utilities import ValidationLimits

logger = logging.getLogger(__name__)


@dataclass
class MutationConfig:
    """Configuration for mutation testing."""
    max_mutations_per_file: int = field(default=ValidationLimits.MAX_MUTATIONS_PER_FILE)
    timeout_seconds: int = field(default=ValidationLimits.DEFAULT_TIMEOUT_SECONDS)
    max_file_size_kb: int = field(default=ValidationLimits.MAX_FILE_SIZE_KB)
    skip_patterns: List[str] = field(default_factory=lambda: [
        '__pycache__',
        '.git',
        'node_modules',
        '.pytest_cache'
    ])
    mutation_types: List[str] = field(default_factory=lambda: [
        'off_by_one',
        'boolean_flip', 
        'condition_flip',
        'boundary_shift'
    ])


@dataclass
class AnalysisConfig:
    """Configuration for effectiveness analysis."""
    max_files_per_test: int = 15  # Reasonable default, not in ValidationLimits
    max_analysis_time_seconds: int = field(default=ValidationLimits.MAX_ANALYSIS_TIME_SECONDS)
    min_effectiveness_threshold: float = field(default=ValidationLimits.MIN_EFFECTIVENESS_THRESHOLD)
    warning_effectiveness_threshold: float = field(default=ValidationLimits.WARNING_EFFECTIVENESS_THRESHOLD)
    max_function_lines: int = field(default=ValidationLimits.MAX_FUNCTION_LINES)
    max_hardcoded_items: int = field(default=ValidationLimits.MAX_HARDCODED_ITEMS)


@dataclass
class ValidationConfig:
    """Configuration for test validation thresholds."""
    mutation_weight: float = 0.6
    bug_pattern_weight: float = 0.3
    integration_weight: float = 0.1
    critical_threshold: float = field(default=ValidationLimits.MIN_EFFECTIVENESS_THRESHOLD)
    warning_threshold: float = field(default=ValidationLimits.WARNING_EFFECTIVENESS_THRESHOLD)
    max_overall_score: float = 100.0


@dataclass
class EffectivenessConfig:
    """Master configuration for effectiveness validation system."""
    mutation: MutationConfig = field(default_factory=MutationConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig) 
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # Performance settings
    enable_parallel_execution: bool = True
    max_worker_threads: int = 4
    
    # Logging settings
    log_level: str = "INFO"
    log_detailed_errors: bool = True
    
    # Output settings
    max_recommendations: int = 5
    include_examples: bool = True
    
    @classmethod
    def from_environment(cls) -> 'EffectivenessConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Mutation config from environment
        config.mutation.max_mutations_per_file = int(
            os.getenv('EFFECTIVENESS_MAX_MUTATIONS', '10')
        )
        config.mutation.timeout_seconds = int(
            os.getenv('EFFECTIVENESS_TIMEOUT', '30')
        )
        config.mutation.max_file_size_kb = int(
            os.getenv('EFFECTIVENESS_MAX_FILE_SIZE', '100')
        )
        
        # Analysis config from environment
        config.analysis.max_files_per_test = int(
            os.getenv('EFFECTIVENESS_MAX_FILES', '15')
        )
        config.analysis.max_analysis_time_seconds = int(
            os.getenv('EFFECTIVENESS_MAX_TIME', '300')
        )
        config.analysis.min_effectiveness_threshold = float(
            os.getenv('EFFECTIVENESS_MIN_THRESHOLD', '50.0')
        )
        
        # Performance settings
        config.enable_parallel_execution = (
            os.getenv('EFFECTIVENESS_PARALLEL', 'true').lower() == 'true'
        )
        config.max_worker_threads = int(
            os.getenv('EFFECTIVENESS_MAX_WORKERS', '4')
        )
        
        # Logging settings
        config.log_level = os.getenv('EFFECTIVENESS_LOG_LEVEL', 'INFO')
        config.log_detailed_errors = (
            os.getenv('EFFECTIVENESS_DETAILED_ERRORS', 'true').lower() == 'true'
        )
        
        return config
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for serialization."""
        return {
            'mutation': {
                'max_mutations_per_file': self.mutation.max_mutations_per_file,
                'timeout_seconds': self.mutation.timeout_seconds,
                'max_file_size_kb': self.mutation.max_file_size_kb,
                'skip_patterns': self.mutation.skip_patterns,
                'mutation_types': self.mutation.mutation_types
            },
            'analysis': {
                'max_files_per_test': self.analysis.max_files_per_test,
                'max_analysis_time_seconds': self.analysis.max_analysis_time_seconds,
                'min_effectiveness_threshold': self.analysis.min_effectiveness_threshold,
                'warning_effectiveness_threshold': self.analysis.warning_effectiveness_threshold,
                'max_function_lines': self.analysis.max_function_lines,
                'max_hardcoded_items': self.analysis.max_hardcoded_items
            },
            'validation': {
                'mutation_weight': self.validation.mutation_weight,
                'bug_pattern_weight': self.validation.bug_pattern_weight,
                'integration_weight': self.validation.integration_weight,
                'critical_threshold': self.validation.critical_threshold,
                'warning_threshold': self.validation.warning_threshold,
                'max_overall_score': self.validation.max_overall_score
            },
            'performance': {
                'enable_parallel_execution': self.enable_parallel_execution,
                'max_worker_threads': self.max_worker_threads
            },
            'logging': {
                'log_level': self.log_level,
                'log_detailed_errors': self.log_detailed_errors
            },
            'output': {
                'max_recommendations': self.max_recommendations,
                'include_examples': self.include_examples
            }
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return any issues."""
        issues = []
        
        # Validate mutation config
        if self.mutation.max_mutations_per_file < 1:
            issues.append("max_mutations_per_file must be at least 1")
        if self.mutation.timeout_seconds < 5:
            issues.append("timeout_seconds must be at least 5")
        if self.mutation.max_file_size_kb < 1:
            issues.append("max_file_size_kb must be at least 1")
            
        # Validate analysis config
        if self.analysis.max_files_per_test < 1:
            issues.append("max_files_per_test must be at least 1")
        if self.analysis.min_effectiveness_threshold < 0 or self.analysis.min_effectiveness_threshold > 100:
            issues.append("min_effectiveness_threshold must be between 0 and 100")
            
        # Validate validation config
        total_weight = (
            self.validation.mutation_weight + 
            self.validation.bug_pattern_weight + 
            self.validation.integration_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            issues.append(f"Validation weights must sum to 1.0, got {total_weight}")
            
        # Validate performance config
        if self.max_worker_threads < 1:
            issues.append("max_worker_threads must be at least 1")
            
        return issues
    
    def save_to_file(self, file_path: Path) -> None:
        """Save configuration to a file."""
        import json
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Configuration saved to {file_path}")
        except (OSError, PermissionError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save configuration to {file_path}: {type(e).__name__}: {e}")
            raise
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> 'EffectivenessConfig':
        """Load configuration from a file."""
        import json
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            config = cls()
            
            # Load mutation config
            if 'mutation' in data:
                m = data['mutation']
                config.mutation.max_mutations_per_file = m.get('max_mutations_per_file', 10)
                config.mutation.timeout_seconds = m.get('timeout_seconds', 30)
                config.mutation.max_file_size_kb = m.get('max_file_size_kb', 100)
                config.mutation.skip_patterns = m.get('skip_patterns', [])
                config.mutation.mutation_types = m.get('mutation_types', [])
            
            # Load analysis config
            if 'analysis' in data:
                a = data['analysis']
                config.analysis.max_files_per_test = a.get('max_files_per_test', 15)
                config.analysis.max_analysis_time_seconds = a.get('max_analysis_time_seconds', 300)
                config.analysis.min_effectiveness_threshold = a.get('min_effectiveness_threshold', 50.0)
                config.analysis.warning_effectiveness_threshold = a.get('warning_effectiveness_threshold', 70.0)
                config.analysis.max_function_lines = a.get('max_function_lines', 30)
                config.analysis.max_hardcoded_items = a.get('max_hardcoded_items', 3)
            
            # Load validation config
            if 'validation' in data:
                v = data['validation']
                config.validation.mutation_weight = v.get('mutation_weight', 0.6)
                config.validation.bug_pattern_weight = v.get('bug_pattern_weight', 0.3)
                config.validation.integration_weight = v.get('integration_weight', 0.1)
                config.validation.critical_threshold = v.get('critical_threshold', 50.0)
                config.validation.warning_threshold = v.get('warning_threshold', 70.0)
                config.validation.max_overall_score = v.get('max_overall_score', 100.0)
            
            # Load performance config
            if 'performance' in data:
                p = data['performance']
                config.enable_parallel_execution = p.get('enable_parallel_execution', True)
                config.max_worker_threads = p.get('max_worker_threads', 4)
            
            # Load logging config
            if 'logging' in data:
                l = data['logging']
                config.log_level = l.get('log_level', 'INFO')
                config.log_detailed_errors = l.get('log_detailed_errors', True)
            
            # Load output config
            if 'output' in data:
                o = data['output']
                config.max_recommendations = o.get('max_recommendations', 5)
                config.include_examples = o.get('include_examples', True)
            
            logger.info(f"Configuration loaded from {file_path}")
            return config
            
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load configuration from {file_path}: {type(e).__name__}: {e}")
            raise


class ConfigManager:
    """Manages configuration for effectiveness validation system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_file = project_root / "tests" / "health" / "testing" / "effectiveness_config.json"
        self._config: Optional[EffectivenessConfig] = None
    
    def get_config(self) -> EffectivenessConfig:
        """Get current configuration, loading from file or environment."""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> EffectivenessConfig:
        """Load configuration from file, environment, or defaults."""
        # Try to load from file first
        if self.config_file.exists():
            try:
                config = EffectivenessConfig.load_from_file(self.config_file)
                logger.info(f"Loaded configuration from {self.config_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
        
        # Fall back to environment variables
        try:
            config = EffectivenessConfig.from_environment()
            logger.info("Loaded configuration from environment variables")
            return config
        except Exception as e:
            logger.warning(f"Failed to load config from environment: {e}")
        
        # Fall back to defaults
        config = EffectivenessConfig()
        logger.info("Using default configuration")
        return config
    
    def save_config(self, config: EffectivenessConfig) -> None:
        """Save configuration to file."""
        # Validate configuration first
        issues = config.validate()
        if issues:
            raise ValueError(f"Configuration validation failed: {', '.join(issues)}")
        
        # Ensure directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        config.save_to_file(self.config_file)
        self._config = config
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = EffectivenessConfig()
        logger.info("Configuration reset to defaults")
    
    def get_environment_overrides(self) -> Dict[str, str]:
        """Get current environment variable overrides."""
        env_vars = {}
        
        effectiveness_vars = [
            'EFFECTIVENESS_MAX_MUTATIONS',
            'EFFECTIVENESS_TIMEOUT',
            'EFFECTIVENESS_MAX_FILE_SIZE',
            'EFFECTIVENESS_MAX_FILES',
            'EFFECTIVENESS_MAX_TIME',
            'EFFECTIVENESS_MIN_THRESHOLD',
            'EFFECTIVENESS_PARALLEL',
            'EFFECTIVENESS_MAX_WORKERS',
            'EFFECTIVENESS_LOG_LEVEL',
            'EFFECTIVENESS_DETAILED_ERRORS'
        ]
        
        for var in effectiveness_vars:
            value = os.getenv(var)
            if value is not None:
                env_vars[var] = value
        
        return env_vars