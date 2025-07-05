"""Performance management for adaptive testing execution modes.

Provides intelligent execution strategies based on validation mode:
- FAST: <30 seconds, essential checks only
- STANDARD: <2 minutes, comprehensive analysis  
- COMPREHENSIVE: <10 minutes, deep analysis with full coverage
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .context_intelligence import ValidationMode, TestingIntelligenceEngine

logger = logging.getLogger(__name__)


@dataclass
class ExecutionLimits:
    """Execution limits for different validation modes."""
    max_files: int
    max_tests_per_file: int
    max_execution_time: float  # seconds
    enable_parallel: bool
    skip_large_files: bool
    file_size_limit: int  # bytes
    enable_caching: bool


@dataclass
class PerformanceMetrics:
    """Performance metrics for execution monitoring."""
    files_processed: int
    tests_executed: int
    execution_time: float
    files_skipped: int
    cache_hits: int
    cache_misses: int
    mode: ValidationMode


class AdaptivePerformanceManager:
    """Manages adaptive performance based on validation mode and system constraints."""
    
    def __init__(self, intelligence_engine: TestingIntelligenceEngine):
        self.intelligence = intelligence_engine
        self.start_time = time.time()
        self.metrics = PerformanceMetrics(0, 0, 0.0, 0, 0, 0, intelligence_engine.mode)
        # Use bounded cache with size limits
        from .shared_utilities import BoundedDict, ValidationLimits
        self._file_cache = BoundedDict(max_size=ValidationLimits.MAX_CACHE_ENTRIES)
        self._execution_limits = self._create_execution_limits()
        
        logger.info(f"Performance manager initialized for {self.intelligence.mode.value} mode")
        logger.info(f"Limits: {self._execution_limits.max_files} files, "
                   f"{self._execution_limits.max_execution_time}s timeout")
    
    def _create_execution_limits(self) -> ExecutionLimits:
        """Create execution limits based on validation mode."""
        mode = self.intelligence.mode
        
        # Get user-specified overrides from environment
        max_files_override = os.getenv('VALIDATION_MAX_FILES')
        max_time_override = os.getenv('VALIDATION_MAX_TIME')
        
        if mode == ValidationMode.FAST:
            limits = ExecutionLimits(
                max_files=15,
                max_tests_per_file=10,
                max_execution_time=30.0,
                enable_parallel=True,
                skip_large_files=True,
                file_size_limit=50 * 1024,  # 50KB
                enable_caching=True
            )
        elif mode == ValidationMode.COMPREHENSIVE:
            limits = ExecutionLimits(
                max_files=200,
                max_tests_per_file=100,
                max_execution_time=600.0,  # 10 minutes
                enable_parallel=True,
                skip_large_files=False,
                file_size_limit=5 * 1024 * 1024,  # 5MB
                enable_caching=True
            )
        else:  # STANDARD
            limits = ExecutionLimits(
                max_files=50,
                max_tests_per_file=25,
                max_execution_time=120.0,  # 2 minutes
                enable_parallel=True,
                skip_large_files=True,
                file_size_limit=200 * 1024,  # 200KB
                enable_caching=True
            )
        
        # Apply user overrides
        if max_files_override:
            try:
                limits.max_files = int(max_files_override)
                logger.info(f"Override max_files: {limits.max_files}")
            except ValueError:
                logger.warning(f"Invalid VALIDATION_MAX_FILES: {max_files_override}")
        
        if max_time_override:
            try:
                limits.max_execution_time = float(max_time_override)
                logger.info(f"Override max_time: {limits.max_execution_time}s")
            except ValueError:
                logger.warning(f"Invalid VALIDATION_MAX_TIME: {max_time_override}")
        
        return limits
    
    def should_process_file(self, test_file: Path) -> Tuple[bool, str]:
        """Determine if a file should be processed based on performance constraints."""
        # Check execution time limit
        elapsed = time.time() - self.start_time
        if elapsed > self._execution_limits.max_execution_time:
            return False, f"Time limit exceeded ({elapsed:.1f}s > {self._execution_limits.max_execution_time}s)"
        
        # Check file count limit
        if self.metrics.files_processed >= self._execution_limits.max_files:
            return False, f"File limit reached ({self.metrics.files_processed} >= {self._execution_limits.max_files})"
        
        # Check file size if skip_large_files is enabled
        if self._execution_limits.skip_large_files:
            try:
                file_size = test_file.stat().st_size
                if file_size > self._execution_limits.file_size_limit:
                    self.metrics.files_skipped += 1
                    return False, f"File too large ({file_size} > {self._execution_limits.file_size_limit} bytes)"
            except OSError:
                return False, "Cannot access file"
        
        # Check if file exists in cache
        file_key = str(test_file)
        if self._execution_limits.enable_caching and file_key in self._file_cache:
            self.metrics.cache_hits += 1
            # Still process but can use cached analysis
        else:
            self.metrics.cache_misses += 1
        
        return True, "OK"
    
    def get_test_limit_for_file(self, test_file: Path) -> int:
        """Get the maximum number of tests to analyze for a specific file."""
        context = self.intelligence.analyze_module_context(test_file)
        
        # Critical files get more tests analyzed even in fast mode
        if context.is_critical_path:
            return min(self._execution_limits.max_tests_per_file * 2, 50)
        elif context.importance.value == 'critical':
            return min(self._execution_limits.max_tests_per_file * 1.5, 30)
        else:
            return self._execution_limits.max_tests_per_file
    
    def should_run_deep_analysis(self, test_file: Path) -> bool:
        """Determine if deep analysis should be run on a file."""
        if self.intelligence.mode == ValidationMode.FAST:
            # Only run deep analysis on critical path files in fast mode
            context = self.intelligence.analyze_module_context(test_file)
            return context.is_critical_path or context.importance.value == 'critical'
        elif self.intelligence.mode == ValidationMode.COMPREHENSIVE:
            # Run deep analysis on all files in comprehensive mode
            return True
        else:
            # Standard mode: run on important+ files
            context = self.intelligence.analyze_module_context(test_file)
            return context.importance.value in ['critical', 'important']
    
    def get_analysis_scope(self, test_file: Path) -> Set[str]:
        """Get the set of analyses to run for a file based on mode and context."""
        context = self.intelligence.analyze_module_context(test_file)
        scope = set()
        
        # Always run basic analyses
        scope.add('naming_conventions')
        scope.add('basic_structure')
        
        if self.intelligence.mode == ValidationMode.FAST:
            # Fast mode: only essential checks
            if context.is_critical_path or context.importance.value == 'critical':
                scope.update(['assertions', 'error_handling'])
        
        elif self.intelligence.mode == ValidationMode.COMPREHENSIVE:
            # Comprehensive mode: all analyses
            scope.update([
                'assertions', 'error_handling', 'boundary_testing',
                'mock_quality', 'performance', 'documentation',
                'mutation_resistance', 'business_logic'
            ])
        
        else:  # STANDARD mode
            # Standard mode: context-aware selection
            scope.update(['assertions', 'error_handling'])
            
            if context.importance.value in ['critical', 'important']:
                scope.update(['boundary_testing', 'mock_quality'])
            
            if context.risk_level > 0.7:
                scope.add('mutation_resistance')
            
            if context.complexity_score > 0.6:
                scope.add('business_logic')
        
        return scope
    
    def cache_file_analysis(self, test_file: Path, analysis_results: dict) -> None:
        """Cache analysis results for a file."""
        if not self._execution_limits.enable_caching:
            return
        
        file_key = str(test_file)
        try:
            # Include file modification time in cache key for invalidation
            mod_time = test_file.stat().st_mtime
            self._file_cache[file_key] = {
                'results': analysis_results,
                'mod_time': mod_time,
                'cached_at': time.time()
            }
        except OSError:
            pass  # Cannot cache if file is inaccessible
    
    def get_cached_analysis(self, test_file: Path) -> Optional[dict]:
        """Get cached analysis results for a file if still valid."""
        if not self._execution_limits.enable_caching:
            return None
        
        file_key = str(test_file)
        if file_key not in self._file_cache:
            return None
        
        cached = self._file_cache[file_key]
        
        try:
            # Check if file has been modified since caching
            current_mod_time = test_file.stat().st_mtime
            if current_mod_time != cached['mod_time']:
                # File modified, invalidate cache
                del self._file_cache[file_key]
                return None
        except OSError:
            # File no longer accessible, invalidate cache
            del self._file_cache[file_key]
            return None
        
        # Check cache age (expire after 1 hour)
        cache_age = time.time() - cached['cached_at']
        if cache_age > 3600:  # 1 hour
            del self._file_cache[file_key]
            return None
        
        return cached['results']
    
    def update_metrics(self, files_processed: int = 0, tests_executed: int = 0) -> None:
        """Update performance metrics."""
        self.metrics.files_processed += files_processed
        self.metrics.tests_executed += tests_executed
        self.metrics.execution_time = time.time() - self.start_time
    
    def should_continue_execution(self) -> bool:
        """Check if execution should continue based on time and resource constraints."""
        elapsed = time.time() - self.start_time
        
        # Hard time limit
        if elapsed > self._execution_limits.max_execution_time:
            logger.warning(f"Time limit exceeded: {elapsed:.1f}s > {self._execution_limits.max_execution_time}s")
            return False
        
        # Soft file limit with warning
        if self.metrics.files_processed >= self._execution_limits.max_files:
            logger.info(f"File limit reached: {self.metrics.files_processed} files processed")
            return False
        
        # Warning at 80% of time limit
        if elapsed > self._execution_limits.max_execution_time * 0.8:
            remaining = self._execution_limits.max_execution_time - elapsed
            logger.warning(f"Approaching time limit: {remaining:.1f}s remaining")
        
        return True
    
    def get_performance_summary(self) -> dict:
        """Get comprehensive performance summary."""
        elapsed = time.time() - self.start_time
        
        cache_hit_rate = 0.0
        if self.metrics.cache_hits + self.metrics.cache_misses > 0:
            cache_hit_rate = self.metrics.cache_hits / (self.metrics.cache_hits + self.metrics.cache_misses)
        
        return {
            'mode': self.intelligence.mode.value,
            'execution_time': elapsed,
            'files_processed': self.metrics.files_processed,
            'files_skipped': self.metrics.files_skipped,
            'tests_executed': self.metrics.tests_executed,
            'cache_hit_rate': cache_hit_rate,
            'performance_rating': self._calculate_performance_rating(elapsed),
            'efficiency_score': self._calculate_efficiency_score(),
            'within_limits': elapsed <= self._execution_limits.max_execution_time,
            'limits': {
                'max_files': self._execution_limits.max_files,
                'max_time': self._execution_limits.max_execution_time,
                'file_size_limit': self._execution_limits.file_size_limit
            }
        }
    
    def _calculate_performance_rating(self, elapsed_time: float) -> str:
        """Calculate performance rating based on execution time."""
        time_ratio = elapsed_time / self._execution_limits.max_execution_time
        
        if time_ratio <= 0.5:
            return "Excellent"
        elif time_ratio <= 0.75:
            return "Good"
        elif time_ratio <= 1.0:
            return "Acceptable"
        else:
            return "Poor"
    
    def _calculate_efficiency_score(self) -> float:
        """Calculate efficiency score (0.0 to 1.0) based on throughput."""
        if self.metrics.execution_time == 0:
            return 1.0
        
        # Files per second as efficiency metric
        files_per_second = self.metrics.files_processed / self.metrics.execution_time
        
        # Expected throughput based on mode
        expected_throughput = {
            ValidationMode.FAST: 2.0,        # 2 files/second
            ValidationMode.STANDARD: 0.8,    # 0.8 files/second  
            ValidationMode.COMPREHENSIVE: 0.3 # 0.3 files/second
        }[self.intelligence.mode]
        
        efficiency = min(files_per_second / expected_throughput, 1.0)
        return efficiency
    
    def log_performance_summary(self) -> None:
        """Log detailed performance summary."""
        summary = self.get_performance_summary()
        
        logger.info("="*60)
        logger.info("PERFORMANCE SUMMARY")
        logger.info("="*60)
        logger.info(f"Mode: {summary['mode']}")
        logger.info(f"Execution time: {summary['execution_time']:.2f}s")
        logger.info(f"Files processed: {summary['files_processed']}")
        logger.info(f"Files skipped: {summary['files_skipped']}")
        logger.info(f"Tests executed: {summary['tests_executed']}")
        logger.info(f"Cache hit rate: {summary['cache_hit_rate']:.1%}")
        logger.info(f"Performance rating: {summary['performance_rating']}")
        logger.info(f"Efficiency score: {summary['efficiency_score']:.2f}")
        logger.info(f"Within limits: {summary['within_limits']}")
        logger.info("="*60)
        
        # Performance recommendations
        if summary['efficiency_score'] < 0.5:
            logger.warning("Low efficiency detected. Consider:")
            logger.warning("  - Using FAST mode for quicker feedback")
            logger.warning("  - Reducing file size limits")
            logger.warning("  - Enabling caching if disabled")
        
        if summary['files_skipped'] > summary['files_processed'] * 0.3:
            logger.info(f"High skip rate ({summary['files_skipped']} files). Consider:")
            logger.info("  - Increasing file size limits")
            logger.info("  - Using COMPREHENSIVE mode for full coverage")
    
    def clear_file_cache(self) -> None:
        """Clear file analysis cache to free memory."""
        cache_size = len(self._file_cache)
        self._file_cache.clear()
        logger.info(f"Cleared file cache ({cache_size} entries)")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Return cache usage statistics for monitoring."""
        return {
            'cache_size': len(self._file_cache),
            'cache_limit': getattr(self._file_cache, 'max_size', 1000),
            'memory_estimate_kb': len(self._file_cache) * 10,  # Rough estimate: 10KB per entry
            'utilization_percent': int((len(self._file_cache) / 1000) * 100)
        }
    
    def cleanup_expired_cache_entries(self) -> None:
        """Remove expired cache entries based on timestamp."""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._file_cache.items()
            if current_time - data.get('timestamp', 0) > 3600  # 1 hour expiration
        ]
        
        for key in expired_keys:
            del self._file_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def cleanup_cache_if_needed(self) -> None:
        """Cleanup cache if memory utilization is high."""
        stats = self.get_cache_stats()
        
        # First clean expired entries
        self.cleanup_expired_cache_entries()
        
        # Check if we're still over capacity
        updated_stats = self.get_cache_stats()
        if updated_stats['utilization_percent'] > 90:
            logger.warning(f"Cache utilization still high ({updated_stats['utilization_percent']}%) after expiration cleanup")
            # BoundedDict will handle LRU eviction automatically