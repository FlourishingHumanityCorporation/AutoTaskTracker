"""Centralized constants and configuration values for testing framework.

This module consolidates all hardcoded values, magic numbers, and thresholds
into a single, configurable location to improve maintainability.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class EffectivenessThresholds:
    """Thresholds for determining test effectiveness ratings."""
    
    # Mutation testing effectiveness thresholds (percentages)
    EXCELLENT: float = 90.0    # >= 90% mutations caught
    GOOD: float = 70.0         # >= 70% mutations caught  
    MODERATE: float = 50.0     # >= 50% mutations caught
    POOR: float = 30.0         # >= 30% mutations caught
    # Below 30% is considered "very poor"
    
    # Integration quality thresholds  
    HIGH_INTEGRATION: float = 80.0     # >= 80% real integration
    MEDIUM_INTEGRATION: float = 60.0   # >= 60% real integration
    LOW_INTEGRATION: float = 40.0      # >= 40% real integration


@dataclass  
class MutationTestingLimits:
    """Limits and constraints for mutation testing operations."""
    
    # Mutation generation limits
    MAX_MUTATIONS_PER_FILE: int = 10
    DEFAULT_TIMEOUT_SECONDS: int = 30
    MAX_FILE_SIZE_KB: int = 100
    
    # Parallel execution limits
    MAX_WORKERS: int = 8
    BATCH_SIZE: int = 5


@dataclass
class CacheConfiguration:
    """Configuration for caching behavior."""
    
    # Cache size limits
    DEFAULT_MAX_SIZE_MB: int = 100
    MAX_CACHE_ENTRIES: int = 1000
    
    # Cache timing
    DEFAULT_TTL_SECONDS: int = 3600  # 1 hour
    DEFAULT_CLEANUP_INTERVAL_HOURS: int = 24  # Daily cleanup
    
    # Cache utilization thresholds
    CLEANUP_THRESHOLD_PERCENT: float = 80.0  # Start cleanup at 80% full
    TARGET_UTILIZATION_PERCENT: float = 60.0  # Clean down to 60%


@dataclass
class PerformanceLimits:
    """Performance-related limits and timeouts."""
    
    # Git operation timeouts
    GIT_COMMAND_TIMEOUT: int = 15
    GIT_HISTORY_TIMEOUT: int = 10
    GIT_STATUS_TIMEOUT: int = 5
    
    # File operation limits
    MAX_FILE_READ_SIZE_MB: int = 50
    FILE_OPERATION_TIMEOUT: int = 10
    
    # Analysis limits
    MAX_ANALYSIS_TIME_SECONDS: int = 300  # 5 minutes
    MAX_FILES_PER_BATCH: int = 15


@dataclass
class TestComplexityLimits:
    """Limits for test complexity analysis."""
    
    # Function complexity
    MAX_FUNCTION_LINES: int = 30
    MAX_CYCLOMATIC_COMPLEXITY: int = 10
    MAX_NESTING_DEPTH: int = 4
    
    # Test quality thresholds
    MAX_HARDCODED_ITEMS: int = 3
    MIN_ASSERTION_COUNT: int = 1
    
    # Documentation thresholds
    REQUIRE_DOCSTRING_LINES: int = 10  # Functions > 10 lines need docstrings


@dataclass
class RetryConfiguration:
    """Configuration for retry behavior with exponential backoff."""
    
    # Default retry settings
    DEFAULT_MAX_ATTEMPTS: int = 3
    DEFAULT_BASE_DELAY: float = 1.0
    DEFAULT_MAX_DELAY: float = 60.0
    DEFAULT_BACKOFF_FACTOR: float = 2.0
    
    # Git-specific retry settings
    GIT_MAX_ATTEMPTS: int = 3
    GIT_BASE_DELAY: float = 0.5
    GIT_MAX_DELAY: float = 10.0
    
    # File operation retry settings
    FILE_MAX_ATTEMPTS: int = 3
    FILE_BASE_DELAY: float = 0.1
    FILE_MAX_DELAY: float = 5.0


@dataclass
class BugCorrelationConstants:
    """Constants for bug correlation analysis."""
    
    # Historical analysis periods
    DEFAULT_HISTORY_DAYS: int = 90
    RECENT_CHANGES_DAYS: int = 30
    CRITICAL_PERIOD_DAYS: int = 7
    
    # Risk scoring thresholds
    HIGH_RISK_SCORE: int = 80
    MEDIUM_RISK_SCORE: int = 60
    LOW_RISK_SCORE: int = 40
    
    # Pattern detection limits
    MIN_PATTERN_OCCURRENCES: int = 3
    MAX_PATTERNS_TO_TRACK: int = 50


@dataclass
class AnalysisPriorities:
    """Priority values for different types of analysis."""
    
    # File type priorities
    CRITICAL_FILE_PRIORITY: int = 30
    CORE_FILE_PRIORITY: int = 20
    UTILITY_FILE_PRIORITY: int = 10
    TEST_FILE_PRIORITY: int = 15
    
    # Analysis type priorities
    SECURITY_ANALYSIS_PRIORITY: int = 25
    PERFORMANCE_ANALYSIS_PRIORITY: int = 20
    QUALITY_ANALYSIS_PRIORITY: int = 15
    DOCUMENTATION_ANALYSIS_PRIORITY: int = 10


@dataclass
class SystemConstants:
    """System-wide constants and defaults."""
    
    # File patterns
    CRITICAL_FILE_PATTERNS: List[str] = None
    EXPERIMENTAL_FILE_PATTERNS: List[str] = None
    
    # Encoding fallbacks
    ENCODING_FALLBACKS: List[str] = None
    
    def __post_init__(self):
        if self.CRITICAL_FILE_PATTERNS is None:
            self.CRITICAL_FILE_PATTERNS = ['critical', 'core', 'main', 'base']
        
        if self.EXPERIMENTAL_FILE_PATTERNS is None:
            self.EXPERIMENTAL_FILE_PATTERNS = ['experimental', 'draft', 'temp', 'test']
        
        if self.ENCODING_FALLBACKS is None:
            self.ENCODING_FALLBACKS = ['utf-8', 'latin-1', 'cp1252', 'utf-16']


# Global configuration instance
class TestingFrameworkConstants:
    """Centralized access to all testing framework constants."""
    
    EFFECTIVENESS = EffectivenessThresholds()
    MUTATION_TESTING = MutationTestingLimits()
    CACHE = CacheConfiguration()
    PERFORMANCE = PerformanceLimits()
    COMPLEXITY = TestComplexityLimits()
    RETRY = RetryConfiguration()
    BUG_CORRELATION = BugCorrelationConstants()
    PRIORITIES = AnalysisPriorities()
    SYSTEM = SystemConstants()
    
    @classmethod
    def get_effectiveness_threshold(cls, level: str) -> float:
        """Get effectiveness threshold by level name."""
        thresholds = {
            'excellent': cls.EFFECTIVENESS.EXCELLENT,
            'good': cls.EFFECTIVENESS.GOOD,
            'moderate': cls.EFFECTIVENESS.MODERATE,
            'poor': cls.EFFECTIVENESS.POOR
        }
        return thresholds.get(level.lower(), cls.EFFECTIVENESS.MODERATE)
    
    @classmethod
    def get_cache_config(cls, **overrides) -> Dict:
        """Get cache configuration with optional overrides."""
        config = {
            'max_size_mb': cls.CACHE.DEFAULT_MAX_SIZE_MB,
            'max_entries': cls.CACHE.MAX_CACHE_ENTRIES,
            'ttl_seconds': cls.CACHE.DEFAULT_TTL_SECONDS,
            'cleanup_interval_hours': cls.CACHE.DEFAULT_CLEANUP_INTERVAL_HOURS
        }
        config.update(overrides)
        return config
    
    @classmethod
    def get_retry_config(cls, operation_type: str = 'default') -> Dict:
        """Get retry configuration for specific operation type."""
        if operation_type == 'git':
            return {
                'max_attempts': cls.RETRY.GIT_MAX_ATTEMPTS,
                'base_delay': cls.RETRY.GIT_BASE_DELAY,
                'max_delay': cls.RETRY.GIT_MAX_DELAY,
                'backoff_factor': cls.RETRY.DEFAULT_BACKOFF_FACTOR
            }
        elif operation_type == 'file':
            return {
                'max_attempts': cls.RETRY.FILE_MAX_ATTEMPTS,
                'base_delay': cls.RETRY.FILE_BASE_DELAY,
                'max_delay': cls.RETRY.FILE_MAX_DELAY,
                'backoff_factor': cls.RETRY.DEFAULT_BACKOFF_FACTOR
            }
        else:
            return {
                'max_attempts': cls.RETRY.DEFAULT_MAX_ATTEMPTS,
                'base_delay': cls.RETRY.DEFAULT_BASE_DELAY,
                'max_delay': cls.RETRY.DEFAULT_MAX_DELAY,
                'backoff_factor': cls.RETRY.DEFAULT_BACKOFF_FACTOR
            }


# Convenience aliases for backward compatibility
CONSTANTS = TestingFrameworkConstants()
EFFECTIVENESS_THRESHOLDS = CONSTANTS.EFFECTIVENESS
MUTATION_LIMITS = CONSTANTS.MUTATION_TESTING
CACHE_CONFIG = CONSTANTS.CACHE
PERFORMANCE_LIMITS = CONSTANTS.PERFORMANCE