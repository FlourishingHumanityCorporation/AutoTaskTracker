"""Effectiveness-based test validation system.

This module provides tools for validating test quality based on actual bug-catching
effectiveness rather than structural metrics.
"""

from .mutation_effectiveness import (
    EffectivenessValidator,
    SimpleMutationTester,  # Deprecated - use RefactoredMutationTester
    MutationType,
    MutationResult,
    TestEffectivenessReport
)

# New refactored components (preferred)
from .mutation_tester_refactored import RefactoredMutationTester
from .mutation_generator import MutationGenerator
from .mutation_executor import MutationExecutor
from .mutation_analyzer import MutationAnalyzer

from .simple_intelligence import (
    FocusedTestValidator,
    SimpleTestAnalyzer,
    ActionableInsight,
    TestPurpose
)

from .config import (
    ConfigManager,
    EffectivenessConfig,
    MutationConfig,
    AnalysisConfig,
    ValidationConfig
)

try:
    from .performance_optimizer import (
        PerformanceOptimizer,
        AnalysisCache,
        ParallelAnalyzer,
        SmartScheduler,
        PerformanceMetrics
    )
    _PERFORMANCE_AVAILABLE = True
except ImportError:
    _PERFORMANCE_AVAILABLE = False

__all__ = [
    'EffectivenessValidator',
    'SimpleMutationTester',  # Deprecated
    'MutationType',
    'MutationResult',
    'TestEffectivenessReport',
    # New refactored components (preferred)
    'RefactoredMutationTester',
    'MutationGenerator',
    'MutationExecutor', 
    'MutationAnalyzer',
    'FocusedTestValidator',
    'SimpleTestAnalyzer',
    'ActionableInsight',
    'TestPurpose',
    'ConfigManager',
    'EffectivenessConfig',
    'MutationConfig',
    'AnalysisConfig',
    'ValidationConfig'
]

if _PERFORMANCE_AVAILABLE:
    __all__.extend([
        'PerformanceOptimizer',
        'AnalysisCache',
        'ParallelAnalyzer',
        'SmartScheduler',
        'PerformanceMetrics'
    ])