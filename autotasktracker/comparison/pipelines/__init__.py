"""
Pipeline implementations for AI comparison.
"""

from autotasktracker.comparison.pipelines.base import BasePipeline
from autotasktracker.comparison.pipelines.basic import BasicPipeline
from autotasktracker.comparison.pipelines.ocr import OCRPipeline
from autotasktracker.comparison.pipelines.ai_full import AIFullPipeline

__all__ = ['BasePipeline', 'BasicPipeline', 'OCRPipeline', 'AIFullPipeline']