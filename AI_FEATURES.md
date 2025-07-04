# AI Features Implementation Guide

## Overview
AutoTaskTracker now includes advanced AI capabilities that leverage Pensieve's built-in AI features for enhanced task detection and analysis.

## Implemented AI Features

### 1. **VLM (Vision Language Model) Integration**
- **Status**: Ready (requires model installation)
- **Module**: `autotasktracker/ai/vlm_integration.py`
- **Features**:
  - Understands visual context beyond text
  - Detects UI states (debugging, multi-tasking, etc.)
  - Identifies visual activities (design work, video editing)
  - Provides confidence scores for task detection

### 2. **Embeddings-Based Semantic Search**
- **Status**: Implemented (requires Pensieve to generate embeddings)
- **Module**: `autotasktracker/ai/embeddings_search.py`
- **Features**:
  - Find similar tasks using cosine similarity
  - Group related activities automatically
  - Semantic task search across time periods
  - Task context analysis

### 3. **OCR Enhancement**
- **Status**: Fully functional
- **Module**: `autotasktracker/ai/ocr_enhancement.py`
- **Features**:
  - OCR confidence scoring
  - Layout analysis (titles, code, UI elements)
  - Quality assessment (excellent/good/fair/poor)
  - Task-relevant text extraction

### 4. **AI-Enhanced Task Extraction**
- **Status**: Operational
- **Module**: `autotasktracker/ai/enhanced_task_extractor.py`
- **Features**:
  - Combines all AI features for superior task detection
  - Confidence-based task selection
  - Multi-source task enhancement
  - Intelligent fallback mechanisms

## Setup Instructions

### Enable VLM (Optional but Recommended)
```bash
# 1. Install Ollama (if not installed)
# Visit: https://ollama.ai

# 2. Pull the minicpm-v model
ollama pull minicpm-v

# 3. Enable VLM in Pensieve config
# Edit ~/.memos/config.yaml and uncomment:
# - builtin_vlm

# 4. Restart memos
memos restart
```

### View AI-Enhanced Dashboard
```bash
# Activate virtual environment
source venv/bin/activate

# Run the AI-enhanced dashboard
streamlit run autotasktracker/dashboards/ai_enhanced_task_board.py
```

## AI Coverage Statistics

The system tracks AI feature usage:
- **OCR Coverage**: Percentage of screenshots with text extraction
- **VLM Coverage**: Percentage with visual descriptions (0% until enabled)
- **Embedding Coverage**: Percentage with semantic vectors (0% initially)

## Performance Considerations

1. **OCR**: Already running, minimal overhead
2. **VLM**: Requires ~4GB for model, adds 2-3s per screenshot
3. **Embeddings**: Fast generation, ~768 dimensions per screenshot
4. **Storage**: Minimal increase (~1KB per screenshot for AI data)

## Testing

Run the comprehensive test suite:
```bash
python test_ai_enhancements.py
```

## Benefits

1. **Better Task Detection**: VLM understands visual context
2. **Smarter Grouping**: Embeddings find truly similar tasks
3. **Higher Accuracy**: OCR confidence filtering reduces noise
4. **Richer Insights**: UI states, visual context, and subtasks

## Future Enhancements

1. **YOLO Integration**: Detect UI elements (buttons, forms)
2. **LLM Summaries**: Generate daily activity summaries
3. **Pattern Learning**: Identify recurring task patterns
4. **API Integration**: Export to external task managers