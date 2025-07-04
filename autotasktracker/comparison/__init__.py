"""
AI Pipeline Comparison Module for AutoTaskTracker.

This module provides tools for comparing different AI processing pipelines
to evaluate their performance on screenshot task extraction.

Components:
- pipelines: Different AI processing pipeline implementations
- dashboards: Interactive comparison interfaces  
- analysis: Performance analysis and reporting tools
"""

from .pipelines.base import BasePipeline
from .pipelines.basic import BasicPipeline
from .pipelines.ocr import OCRPipeline
from .pipelines.ai_full import AIFullPipeline

from .analysis.performance_analyzer import PerformanceAnalyzer
from .analysis.metrics import ComparisonMetrics

__all__ = [
    'BasePipeline',
    'BasicPipeline', 
    'OCRPipeline',
    'AIFullPipeline',
    'PerformanceAnalyzer',
    'ComparisonMetrics'
]