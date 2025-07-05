"""AI enhancement modules for AutoTaskTracker.

Provides VLM integration, embeddings search, and OCR enhancement.
Barrel exports for commonly used AI classes and functions.

Usage:
    from autotasktracker.ai import VLMProcessor, EmbeddingsSearch, VLMTaskExtractor
"""

# VLM processing
from autotasktracker.ai.vlm_integration import VLMTaskExtractor, extract_vlm_enhanced_task
from autotasktracker.ai.vlm_processor import SmartVLMProcessor as VLMProcessor

# OCR enhancement
from autotasktracker.ai.ocr_enhancement import OCREnhancer, create_ocr_enhancer

# Embeddings and search
from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine, EmbeddingStats

# Task extraction
from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor

# Content filtering
from autotasktracker.ai.sensitive_filter import SensitiveDataFilter

__all__ = [
    # VLM processing
    'VLMTaskExtractor',
    'extract_vlm_enhanced_task',
    'VLMProcessor',
    
    # OCR enhancement
    'OCREnhancer',
    'create_ocr_enhancer',
    
    # Embeddings and search
    'EmbeddingsSearchEngine',
    'EmbeddingStats',
    
    # Task extraction
    'AIEnhancedTaskExtractor',
    
    # Content filtering
    'SensitiveDataFilter',
]