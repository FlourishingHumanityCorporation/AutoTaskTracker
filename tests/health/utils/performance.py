"""
Performance monitoring and optimization utilities for health tests.

Provides performance tracking, bottleneck identification, and optimization
recommendations for the health test suite.
"""

import time
import functools
import logging
from typing import Dict, List, Callable, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class HealthTestPerformanceMonitor:
    """Monitor and optimize health test performance."""
    
    def __init__(self):
        self.test_timings: Dict[str, float] = {}
        self.module_timings: Dict[str, List[float]] = {}
        self.bottlenecks: List[Dict[str, Any]] = []
        
    def time_test(self, test_name: str):
        """Decorator to time individual tests."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.test_timings[test_name] = duration
                    
                    # Track module timings
                    module = test_name.split('::')[0] if '::' in test_name else 'unknown'
                    if module not in self.module_timings:
                        self.module_timings[module] = []
                    self.module_timings[module].append(duration)
                    
                    # Flag slow tests
                    if duration > 5.0:  # 5 second threshold
                        self.bottlenecks.append({
                            'test': test_name,
                            'duration': duration,
                            'type': 'slow_test'
                        })
                        logger.warning(f"Slow test detected: {test_name} took {duration:.2f}s")
                        
            return wrapper
        return decorator
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance patterns and suggest optimizations."""
        analysis = {
            'total_tests': len(self.test_timings),
            'total_time': sum(self.test_timings.values()),
            'avg_test_time': sum(self.test_timings.values()) / len(self.test_timings) if self.test_timings else 0,
            'slowest_tests': sorted(self.test_timings.items(), key=lambda x: x[1], reverse=True)[:10],
            'module_performance': {},
            'bottlenecks': self.bottlenecks,
            'recommendations': []
        }
        
        # Analyze module performance
        for module, timings in self.module_timings.items():
            analysis['module_performance'][module] = {
                'test_count': len(timings),
                'total_time': sum(timings),
                'avg_time': sum(timings) / len(timings),
                'max_time': max(timings),
                'min_time': min(timings)
            }
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check for slow modules
        for module, stats in analysis['module_performance'].items():
            if stats['avg_time'] > 3.0:
                recommendations.append(
                    f"Optimize {module}: Average test time {stats['avg_time']:.2f}s is high. "
                    f"Consider reducing file scan scope or adding caching."
                )
        
        # Check for file scanning bottlenecks
        slow_tests = [name for name, duration in analysis['slowest_tests'] if duration > 10.0]
        if slow_tests:
            recommendations.append(
                f"File scanning bottleneck: {len(slow_tests)} tests > 10s. "
                f"Consider using PENSIEVE_MAX_FILES_PER_TEST environment variable."
            )
        
        # Check for fixture efficiency
        if analysis['total_time'] > 120:  # 2 minutes total
            recommendations.append(
                "Consider parallelizing tests with pytest-xdist: "
                "pip install pytest-xdist && pytest -n auto"
            )
        
        return recommendations
    
    def save_report(self, filepath: Path) -> None:
        """Save performance analysis to file."""
        analysis = self.analyze_performance()
        
        with open(filepath, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Performance report saved to {filepath}")
    
    def print_summary(self) -> None:
        """Print performance summary to console."""
        analysis = self.analyze_performance()
        
        print("\n📊 Health Test Performance Summary")
        print("=" * 50)
        print(f"Total Tests: {analysis['total_tests']}")
        print(f"Total Time: {analysis['total_time']:.2f}s")
        print(f"Average per Test: {analysis['avg_test_time']:.2f}s")
        
        print("\n🐌 Slowest Tests:")
        for test, duration in analysis['slowest_tests'][:5]:
            print(f"  {test}: {duration:.2f}s")
        
        print("\n📁 Module Performance:")
        for module, stats in analysis['module_performance'].items():
            print(f"  {module}: {stats['test_count']} tests, {stats['total_time']:.2f}s total")
        
        if analysis['recommendations']:
            print("\n💡 Optimization Recommendations:")
            for rec in analysis['recommendations']:
                print(f"  • {rec}")
        
        print()


# Global performance monitor instance
performance_monitor = HealthTestPerformanceMonitor()


def optimize_test_environment():
    """Apply common performance optimizations to test environment."""
    import os
    
    # Set performance-friendly defaults
    optimizations = {
        'PENSIEVE_MAX_FILES_PER_TEST': '30',  # Reduce file scan scope
        'PENSIEVE_TEST_TIMEOUT': '20',        # Shorter timeout for faster feedback
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',  # Reduce plugin overhead
    }
    
    applied = []
    for key, value in optimizations.items():
        if key not in os.environ:
            os.environ[key] = value
            applied.append(f"{key}={value}")
    
    if applied:
        logger.info(f"Applied performance optimizations: {', '.join(applied)}")


class PerformanceOptimizedTest:
    """Base class for performance-optimized health tests."""
    
    @classmethod
    def setup_class(cls):
        """Setup with performance optimizations."""
        optimize_test_environment()
        cls.start_time = time.time()
        
    @classmethod
    def teardown_class(cls):
        """Track class execution time."""
        duration = time.time() - cls.start_time
        performance_monitor.module_timings[cls.__name__] = [duration]
        
        if duration > 30:  # 30 second threshold for class
            logger.warning(f"Slow test class: {cls.__name__} took {duration:.2f}s")