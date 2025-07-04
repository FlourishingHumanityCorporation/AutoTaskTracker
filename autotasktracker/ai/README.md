# 🤖 AI Enhancement Module Documentation

The AI module provides advanced processing capabilities that enhance the basic task extraction with machine learning and artificial intelligence features.

## 📁 Module Contents

```
autotasktracker/ai/
├── __init__.py                    # Module initialization  
├── enhanced_task_extractor.py     # 🎯 Main AI orchestration
├── ocr_enhancement.py            # 📝 OCR text analysis
├── vlm_integration.py            # 👁️ Visual language model
└── embeddings_search.py          # 🧠 Semantic similarity search
```

## 🔗 AI Processing Pipeline

```
Window Title (Basic)
        ↓
OCR Enhancement ──→ Enhanced Task + Confidence
        ↓
VLM Analysis ──────→ Visual Context + UI State  
        ↓
Semantic Search ───→ Similar Tasks + Patterns
        ↓
AI Orchestration ──→ Final Enhanced Result
```

## 🎯 enhanced_task_extractor.py

### **Purpose**
Main orchestrator that combines all AI enhancement features into a unified processing pipeline.

### **Key Class: AIEnhancedTaskExtractor**

#### **Initialization**
```python
from autotasktracker.ai import AIEnhancedTaskExtractor

# Initialize with database path
db_path = "/Users/username/.memos/database.db"
ai_extractor = AIEnhancedTaskExtractor(db_path)
```

#### **Main Method: extract_enhanced_task()**
```python
result = ai_extractor.extract_enhanced_task(
    window_title="Claude Code - VS Code",
    ocr_text='[["screenshot", "text", 0.95], ...]',  # JSON string
    vlm_description="A code editor showing Python file...",
    entity_id=12345
)

# Returns comprehensive result:
{
    'task': 'Claude Code Development',
    'category': '🧑‍💻 Coding', 
    'confidence': 0.85,
    'ai_features': {
        'ocr_enhancement': True,
        'vlm_analysis': True,
        'semantic_search': True
    },
    'similar_tasks': [
        {'task': 'Python Development', 'similarity': 0.92},
        {'task': 'VS Code Programming', 'similarity': 0.88}
    ]
}
```

#### **Processing Logic**
1. **Start with basic extraction** (core module)
2. **Apply OCR enhancement** (if OCR text available)
3. **Apply VLM enhancement** (if VLM description available)
4. **Search for similar tasks** (if embeddings available)
5. **Combine all insights** with confidence weighting
6. **Return comprehensive result**

#### **Confidence Calculation**
```python
# Base confidence from basic extraction
base_confidence = 0.5

# OCR enhancement (0.0 - 1.0)
ocr_boost = ocr_confidence * 0.3

# VLM enhancement (0.0 - 1.0)  
vlm_boost = vlm_confidence * 0.2

# Semantic similarity boost
similarity_boost = max_similarity * 0.2

# Final confidence (capped at 1.0)
final_confidence = min(1.0, base_confidence + ocr_boost + vlm_boost + similarity_boost)
```

---

## 📝 ocr_enhancement.py

### **Purpose**
Analyzes OCR text to improve task extraction accuracy and provide confidence scoring.

### **Key Class: OCREnhancer**

#### **Initialization**
```python
from autotasktracker.ai import OCREnhancer

ocr_enhancer = OCREnhancer()
```

#### **Main Method: enhance_task_with_ocr()**
```python
# OCR result from Memos (JSON string)
ocr_text = '[["screenshot", "Welcome", 0.95], ["login", "button", 0.88]]'
basic_task = "Chrome Browser"

enhancement = ocr_enhancer.enhance_task_with_ocr(ocr_text, basic_task)

# Returns detailed enhancement:
{
    'task': 'Login Portal Access',
    'confidence': 0.75,
    'ocr_quality': 'good',
    'text_regions': {
        'headers': ['Welcome'],
        'buttons': ['login', 'button'],
        'forms': [],
        'navigation': []
    },
    'layout_analysis': {
        'ui_elements_detected': 2,
        'text_confidence_avg': 0.915,
        'layout_complexity': 'simple'
    }
}
```

#### **OCR Analysis Features**

1. **Text Quality Assessment**:
   ```python
   # Confidence scoring based on OCR accuracy
   high_quality = avg_confidence > 0.8    # "excellent"
   good_quality = avg_confidence > 0.6    # "good"  
   low_quality = avg_confidence < 0.4     # "poor"
   ```

2. **Layout Analysis**:
   ```python
   # UI element classification
   BUTTON_KEYWORDS = ["button", "click", "submit", "login", "save"]
   HEADER_KEYWORDS = ["title", "heading", "welcome", "dashboard"]
   FORM_KEYWORDS = ["input", "field", "form", "enter", "password"]
   NAVIGATION_KEYWORDS = ["menu", "nav", "home", "back", "next"]
   ```

3. **Task Enhancement Logic**:
   - **Button-heavy layout** → Interactive task (login, form submission)
   - **Header-rich content** → Reading/research task  
   - **Form elements** → Data entry task
   - **Navigation elements** → Browsing/exploration task

4. **Confidence Calculation**:
   ```python
   # Base confidence from OCR quality
   quality_confidence = average_ocr_confidence
   
   # Layout complexity bonus
   layout_bonus = min(0.2, detected_elements * 0.05)
   
   # Keyword relevance bonus
   relevance_bonus = relevant_keywords_count * 0.1
   
   final_confidence = min(1.0, quality_confidence + layout_bonus + relevance_bonus)
   ```

---

## 👁️ vlm_integration.py

### **Purpose**
Integrates with Visual Language Models (VLM) to understand screenshot content through visual analysis.

### **Key Class: VLMTaskExtractor**

#### **Initialization**
```python
from autotasktracker.ai import VLMTaskExtractor

vlm_extractor = VLMTaskExtractor()
```

#### **Main Method: extract_from_vlm_description()**
```python
vlm_description = "The screenshot shows a code editor with a Python file open..."
window_title = "VS Code"
ocr_text = "def main(): print('hello')"

vlm_task = vlm_extractor.extract_from_vlm_description(
    vlm_description, window_title, ocr_text
)

# Returns VLMTask object:
{
    'task_title': 'Python Development in VS Code',
    'category': '🧑‍💻 Coding',
    'confidence': 0.88,
    'ui_state': 'code_editing',
    'visual_context': 'programming_environment',
    'subtasks': ['file_editing', 'syntax_highlighting'],
    'details': 'User actively coding in Python development environment'
}
```

#### **VLM Analysis Features**

1. **Scene Understanding**:
   ```python
   SCENE_PATTERNS = {
       'code_editor': ['editor', 'syntax', 'programming', 'code'],
       'web_browser': ['browser', 'webpage', 'navigation', 'url'],
       'document_editing': ['document', 'text', 'writing', 'editing'],
       'communication': ['chat', 'message', 'conversation', 'meeting']
   }
   ```

2. **UI State Detection**:
   ```python
   UI_STATES = {
       'active_editing': ['typing', 'cursor', 'active', 'focus'],
       'reading_content': ['reading', 'scrolling', 'viewing'],
       'form_filling': ['form', 'input', 'filling', 'entering'],
       'navigation': ['clicking', 'browsing', 'searching']
   }
   ```

3. **Visual Context Analysis**:
   - **Layout recognition**: Identifies common UI patterns
   - **Activity detection**: Determines what user is doing
   - **Content analysis**: Understands purpose and context
   - **Workflow inference**: Predicts task progression

4. **Confidence Scoring**:
   ```python
   # VLM description quality
   description_quality = len(vlm_description) / 200  # Longer = better
   
   # Keyword relevance
   relevant_keywords = count_matching_keywords(vlm_description)
   keyword_score = min(0.4, relevant_keywords * 0.1)
   
   # Context consistency 
   consistency_score = check_context_alignment(window_title, vlm_description)
   
   final_confidence = min(1.0, description_quality + keyword_score + consistency_score)
   ```

---

## 🧠 embeddings_search.py

### **Purpose**
Provides semantic similarity search using vector embeddings to find related tasks and patterns.

### **Key Class: EmbeddingsSearchEngine**

#### **Initialization**
```python
from autotasktracker.ai import EmbeddingsSearchEngine

# Initialize with database manager or path
embeddings_engine = EmbeddingsSearchEngine(db_manager)
# or
embeddings_engine = EmbeddingsSearchEngine("/path/to/database.db")
```

#### **Main Methods**

##### **search_similar_tasks()**
```python
# Search by text query
similar_tasks = embeddings_engine.search_similar_tasks(
    query="Python programming VS Code",
    limit=5,
    min_similarity=0.7
)

# Returns list of similar tasks:
[
    {
        'entity_id': 123,
        'similarity': 0.92,
        'task': 'Python Development', 
        'window_title': 'VS Code - main.py',
        'created_at': '2025-07-03 14:30:00'
    },
    {
        'entity_id': 456,
        'similarity': 0.88,
        'task': 'Django Coding',
        'window_title': 'VS Code - views.py', 
        'created_at': '2025-07-03 13:15:00'
    }
]
```

##### **find_similar_by_entity_id()**
```python
# Find tasks similar to a specific screenshot
similar_tasks = embeddings_engine.find_similar_by_entity_id(
    entity_id=12345,
    limit=3,
    min_similarity=0.8
)
```

#### **Embedding Features**

1. **Vector Generation**:
   ```python
   # Uses Jina embeddings v2 (768 dimensions)
   MODEL_NAME = "jinaai/jina-embeddings-v2-base-en"
   
   # Combines multiple text sources
   text_to_embed = f"{window_title} {ocr_summary} {vlm_summary}"
   embedding_vector = model.encode(text_to_embed)
   ```

2. **Similarity Calculation**:
   ```python
   # Cosine similarity between vectors
   similarity = cosine_similarity(query_vector, stored_vector)
   
   # Filter by minimum threshold
   relevant_tasks = [task for task in results if task['similarity'] >= min_similarity]
   ```

3. **Historical Pattern Recognition**:
   - **Recurring tasks**: Identifies frequently repeated activities
   - **Work patterns**: Discovers daily/weekly routines
   - **Context switching**: Tracks task transitions
   - **Productivity insights**: Analyzes time allocation patterns

---

## 🔗 AI Module Integration

### **Typical Usage Pattern**
```python
from autotasktracker.ai import AIEnhancedTaskExtractor

# Initialize the complete AI pipeline
ai_extractor = AIEnhancedTaskExtractor("/path/to/database.db")

# Process a screenshot with all available data
result = ai_extractor.extract_enhanced_task(
    window_title="VS Code - main.py",
    ocr_text='[["def", "main", 0.95], ["print", "hello", 0.88]]',
    vlm_description="Code editor showing Python function definition",
    entity_id=12345
)

# Get comprehensive AI-enhanced result
print(f"Task: {result['task']}")
print(f"Confidence: {result['confidence']:.1%}")
print(f"Similar tasks: {len(result.get('similar_tasks', []))}")
```

### **Dependencies**

#### **Required**
- `autotasktracker.core` - Foundation modules
- `sentence-transformers` - For embeddings
- `numpy` - Vector operations
- `sqlite3` - Database access

#### **Optional**
- `ollama` - For VLM functionality (minicpm-v model)
- GPU with 8GB+ VRAM (for optimal VLM performance)

### **Performance Considerations**

1. **Embedding Generation**: ~100-500ms per screenshot
2. **OCR Enhancement**: ~50-100ms per screenshot  
3. **VLM Analysis**: ~1-5 seconds per screenshot (GPU dependent)
4. **Similarity Search**: ~10-50ms per query

### **Configuration**

```python
# Enable/disable specific AI features
AI_CONFIG = {
    'enable_ocr_enhancement': True,
    'enable_vlm_analysis': True,  # Requires Ollama + model
    'enable_semantic_search': True,  # Requires embeddings
    'min_similarity_threshold': 0.7,
    'max_similar_tasks': 5
}
```

## 🎯 Key Design Principles

1. **Modularity**: Each AI feature can work independently
2. **Graceful Fallbacks**: System degrades gracefully if AI features unavailable
3. **Confidence Tracking**: All enhancements include confidence scoring
4. **Performance Optimization**: Caching and efficient algorithms
5. **Extensibility**: Easy to add new AI capabilities

This AI module transforms basic task extraction into intelligent, context-aware activity recognition while maintaining reliability and performance.