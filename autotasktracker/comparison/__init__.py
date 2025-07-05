"""
AI Pipeline Comparison Module for AutoTaskTracker.

This module provides tools for comparing different AI processing pipelines
to evaluate their performance on screenshot task extraction.

Components:
- pipelines: Different AI processing pipeline implementations
- dashboards: Interactive comparison interfaces  
- analysis: Performance analysis and reporting tools
"""

from autotasktracker.comparison.pipelines.base import BasePipeline
from autotasktracker.comparison.pipelines.basic import BasicPipeline
from autotasktracker.comparison.pipelines.ocr import OCRPipeline
from autotasktracker.comparison.pipelines.ai_full import AIFullPipeline

from autotasktracker.comparison.analysis.performance_analyzer import PerformanceAnalyzer
from autotasktracker.comparison.analysis.metrics import ComparisonMetrics

__all__ = [
    'BasePipeline',
    'BasicPipeline', 
    'OCRPipeline',
    'AIFullPipeline',
    'PerformanceAnalyzer',
    'ComparisonMetrics'
]