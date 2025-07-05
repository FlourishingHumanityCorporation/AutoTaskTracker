# AI Module Context

**Focus**: AI processing pipeline (OCR, VLM, embeddings, task extraction)

## 🚨 CRITICAL PYDANTIC V2 MIGRATION IN PROGRESS 🚨

**NEVER use Pydantic v1 patterns** in the AI module. This module is being migrated to Pydantic v2.

### Pydantic v2 Requirements:
```python
# ✅ CORRECT - Pydantic v2 patterns
from pydantic import BaseModel, Field, field_validator, model_validator

class AITask(BaseModel):
    text: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        return v.strip()
    
    @model_validator(mode='after')
    def validate_model(self) -> 'AITask':
        # Model-level validation
        return self

# ❌ WRONG - Pydantic v1 patterns (DO NOT USE)
# from pydantic import validator
# @validator('text')  # This is v1 syntax
```

## Module-Specific Rules

- **Graceful fallbacks**: All AI features must work when models unavailable
- **On-demand loading**: Load models only when needed to conserve memory
- **Performance monitoring**: Track model loading times and processing speeds
- **Error isolation**: AI failures should not break the core system
- **Pydantic v2 compliance**: Use only v2 patterns for all data models

## Key Files & Their Purposes

- `ai_task_extractor.py` - Main task extraction pipeline
- `vlm_processor.py` - Vision-Language Model processing (requires Ollama)
- `embeddings_search.py` - Semantic search with sentence-transformers
- `ocr_enhancement.py` - OCR text processing and cleanup
- `sensitive_filter.py` - Content filtering and privacy protection

## Dependencies

**Required:**
- `pytesseract` - OCR text extraction
- `PIL/Pillow` - Image processing

**Optional (with graceful fallbacks):**
- `sentence-transformers` - For embeddings and semantic search
- `ollama` - For VLM processing
- `torch` - For advanced AI models

## AI Processing Patterns

```python
# ✅ Correct: Graceful fallback pattern
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.info("Embeddings unavailable - using text-based search fallback")

# ✅ Correct: On-demand model loading
def get_vlm_model():
    if not hasattr(get_vlm_model, '_model'):
        get_vlm_model._model = load_vlm_model()
    return get_vlm_model._model
```

## Performance Considerations

- **Batch processing**: Process screenshots in batches to optimize GPU usage
- **Memory management**: Clear model caches between large operations
- **Async processing**: Use async patterns for non-blocking AI operations
- **Progress tracking**: Provide progress indicators for long-running AI tasks

## Testing AI Components

- Use `tests/functional/test_*_extraction_on_real_screenshots.py` for real data testing
- Mock AI models for unit tests to avoid dependencies
- Test graceful fallbacks when models unavailable
- Validate AI output quality with known good examples