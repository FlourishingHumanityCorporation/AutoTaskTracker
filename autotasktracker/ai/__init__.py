"""
AI enhancement modules for AutoTaskTracker.
Provides VLM integration, embeddings search, and OCR enhancement.
"""

from .vlm_integration import VLMTaskExtractor, extract_vlm_enhanced_task
from .ocr_enhancement import OCREnhancer, create_ocr_enhancer
from .embeddings_search import EmbeddingsSearchEngine, EmbeddingStats
from .ai_task_extractor import AIEnhancedTaskExtractor

__all__ = [
    'VLMTaskExtractor',
    'extract_vlm_enhanced_task',
    'OCREnhancer',
    'create_ocr_enhancer',
    'EmbeddingsSearchEngine',
    'EmbeddingStats',
    'AIEnhancedTaskExtractor'
]