"""Unit tests for centralized constants configuration."""

import pytest
from tests.health.testing.constants import (
    TestingFrameworkConstants,
    CONSTANTS,
    EffectivenessThresholds,
    MutationTestingLimits,
    CacheConfiguration,
    RetryConfiguration
)


class TestEffectivenessThresholds:
    """Test effectiveness threshold constants."""
    
    def test_threshold_ordering(self):
        """Test that thresholds are in correct order."""
        thresholds = EffectivenessThresholds()
        
        assert thresholds.EXCELLENT > thresholds.GOOD
        assert thresholds.GOOD > thresholds.MODERATE  
        assert thresholds.MODERATE > thresholds.POOR
        assert thresholds.POOR > 0
    
    def test_threshold_values(self):
        """Test specific threshold values."""
        thresholds = EffectivenessThresholds()
        
        assert thresholds.EXCELLENT == 90.0
        assert thresholds.GOOD == 70.0
        assert thresholds.MODERATE == 50.0
        assert thresholds.POOR == 30.0


class TestMutationTestingLimits:
    """Test mutation testing limit constants."""
    
    def test_reasonable_limits(self):
        """Test that limits are reasonable."""
        limits = MutationTestingLimits()
        
        assert limits.MAX_MUTATIONS_PER_FILE > 0
        assert limits.MAX_MUTATIONS_PER_FILE <= 50  # Not too high
        assert limits.DEFAULT_TIMEOUT_SECONDS > 0
        assert limits.MAX_FILE_SIZE_KB > 0
        assert limits.MAX_WORKERS > 0


class TestCacheConfiguration:
    """Test cache configuration constants."""
    
    def test_cache_sizes(self):
        """Test cache size configurations."""
        cache = CacheConfiguration()
        
        assert cache.DEFAULT_MAX_SIZE_MB > 0
        assert cache.MAX_CACHE_ENTRIES > 0
        assert cache.DEFAULT_TTL_SECONDS > 0
        assert cache.DEFAULT_CLEANUP_INTERVAL_HOURS > 0
    
    def test_utilization_thresholds(self):
        """Test cache utilization thresholds."""
        cache = CacheConfiguration()
        
        assert 0 < cache.CLEANUP_THRESHOLD_PERCENT < 100
        assert 0 < cache.TARGET_UTILIZATION_PERCENT < cache.CLEANUP_THRESHOLD_PERCENT


class TestRetryConfiguration:
    """Test retry configuration constants."""
    
    def test_retry_values(self):
        """Test retry configuration values."""
        retry = RetryConfiguration()
        
        assert retry.DEFAULT_MAX_ATTEMPTS > 0
        assert retry.DEFAULT_BASE_DELAY > 0
        assert retry.DEFAULT_MAX_DELAY > retry.DEFAULT_BASE_DELAY
        assert retry.DEFAULT_BACKOFF_FACTOR > 1.0
    
    def test_operation_specific_configs(self):
        """Test operation-specific retry configurations."""
        retry = RetryConfiguration()
        
        # Git operations should be faster
        assert retry.GIT_BASE_DELAY <= retry.DEFAULT_BASE_DELAY
        assert retry.GIT_MAX_DELAY <= retry.DEFAULT_MAX_DELAY
        
        # File operations should be even faster
        assert retry.FILE_BASE_DELAY <= retry.GIT_BASE_DELAY


class TestTestingFrameworkConstants:
    """Test the main constants class."""
    
    def test_constant_access(self):
        """Test accessing constants through main interface."""
        assert hasattr(CONSTANTS, 'EFFECTIVENESS')
        assert hasattr(CONSTANTS, 'MUTATION_TESTING')
        assert hasattr(CONSTANTS, 'CACHE')
        assert hasattr(CONSTANTS, 'RETRY')
    
    def test_get_effectiveness_threshold(self):
        """Test getting effectiveness thresholds by name."""
        assert CONSTANTS.get_effectiveness_threshold('excellent') == 90.0
        assert CONSTANTS.get_effectiveness_threshold('good') == 70.0
        assert CONSTANTS.get_effectiveness_threshold('moderate') == 50.0
        assert CONSTANTS.get_effectiveness_threshold('poor') == 30.0
        
        # Test default for unknown level
        assert CONSTANTS.get_effectiveness_threshold('unknown') == 50.0
    
    def test_get_cache_config(self):
        """Test getting cache configuration."""
        config = CONSTANTS.get_cache_config()
        
        assert 'max_size_mb' in config
        assert 'max_entries' in config
        assert 'ttl_seconds' in config
        assert 'cleanup_interval_hours' in config
        
        # Test with overrides
        custom_config = CONSTANTS.get_cache_config(max_size_mb=200)
        assert custom_config['max_size_mb'] == 200
        assert custom_config['ttl_seconds'] == config['ttl_seconds']  # Unchanged
    
    def test_get_retry_config(self):
        """Test getting retry configurations for different operations."""
        # Default config
        default_config = CONSTANTS.get_retry_config()
        assert 'max_attempts' in default_config
        assert 'base_delay' in default_config
        
        # Git config
        git_config = CONSTANTS.get_retry_config('git')
        assert git_config['max_attempts'] == CONSTANTS.RETRY.GIT_MAX_ATTEMPTS
        assert git_config['base_delay'] == CONSTANTS.RETRY.GIT_BASE_DELAY
        
        # File config  
        file_config = CONSTANTS.get_retry_config('file')
        assert file_config['max_attempts'] == CONSTANTS.RETRY.FILE_MAX_ATTEMPTS
        assert file_config['base_delay'] == CONSTANTS.RETRY.FILE_BASE_DELAY


class TestConstantsIntegration:
    """Test integration between different constant groups."""
    
    def test_performance_consistency(self):
        """Test that performance-related constants are consistent."""
        # Cache cleanup should happen less frequently than mutations timeout
        assert CONSTANTS.CACHE.DEFAULT_CLEANUP_INTERVAL_HOURS * 3600 > CONSTANTS.MUTATION_TESTING.DEFAULT_TIMEOUT_SECONDS
        
        # Max workers should be reasonable
        assert CONSTANTS.MUTATION_TESTING.MAX_WORKERS <= 16  # Not too high
    
    def test_threshold_consistency(self):
        """Test that different threshold systems are consistent."""
        # All effectiveness thresholds should be between 0 and 100
        for threshold in [CONSTANTS.EFFECTIVENESS.EXCELLENT, 
                         CONSTANTS.EFFECTIVENESS.GOOD,
                         CONSTANTS.EFFECTIVENESS.MODERATE,
                         CONSTANTS.EFFECTIVENESS.POOR]:
            assert 0 <= threshold <= 100
    
    def test_backward_compatibility_aliases(self):
        """Test that backward compatibility aliases work."""
        from tests.health.testing.constants import (
            EFFECTIVENESS_THRESHOLDS,
            MUTATION_LIMITS,
            CACHE_CONFIG,
            PERFORMANCE_LIMITS
        )
        
        assert EFFECTIVENESS_THRESHOLDS == CONSTANTS.EFFECTIVENESS
        assert MUTATION_LIMITS == CONSTANTS.MUTATION_TESTING
        assert CACHE_CONFIG == CONSTANTS.CACHE
        assert PERFORMANCE_LIMITS == CONSTANTS.PERFORMANCE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])