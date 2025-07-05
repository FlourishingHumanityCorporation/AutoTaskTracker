# AutoTaskTracker Domain Knowledge

## Core Concepts & Terminology

### **Pensieve Integration**
- **Pensieve/memos**: Backend system that captures screenshots and performs OCR
- **DatabaseManager**: Abstraction layer that uses Pensieve's SQLite database at `~/.memos/database.db`
- **API-first architecture**: Prefer Pensieve APIs over direct database access when available
- **Graceful fallback**: System degrades gracefully when Pensieve API unavailable

### **Data Model**
- **entities**: Screenshots metadata (file paths, timestamps, window titles)
- **metadata_entries**: OCR text, AI analysis results, extracted tasks
- **entity_id**: Primary key linking screenshots to their processed data
- **frame_id**: Legacy terminology for entity_id (being phased out)

### **AI Processing Pipeline**
- **OCR Processing**: Text extraction from screenshots using Tesseract
- **VLM Processing**: Vision-Language Model analysis using Ollama
- **Task Extraction**: AI identification of actionable items from text
- **Embeddings**: Semantic search capabilities using sentence-transformers
- **Categorization**: Automatic classification of extracted tasks

### **Dashboard System**
- **Task Board** (port 8502): Main dashboard showing extracted tasks
- **Analytics** (port 8503): Data visualization and metrics
- **Time Tracker** (port 8505): Productivity monitoring
- **Integration Health** (port TBD): Real-time system monitoring

### **Processing Modes**
- **Realtime Processing**: Live screenshot capture and analysis
- **Batch Processing**: Bulk processing of historical screenshots  
- **Pipeline Comparison**: A/B testing different AI processing approaches
- **Health Monitoring**: System performance and integration status tracking

## File Organization Patterns

### **Core Modules**
- `autotasktracker/core/`: Essential system components (database, extraction, config)
- `autotasktracker/ai/`: AI processing (OCR, VLM, embeddings, task extraction)
- `autotasktracker/pensieve/`: Pensieve integration (API, events, search, webhooks)
- `autotasktracker/dashboards/`: Streamlit web interfaces

### **Scripts Organization**
- `scripts/ai/`: AI model management and processing tools
- `scripts/processing/`: Data processing and batch operations
- `scripts/analysis/`: Performance analysis and comparison tools

### **Navigation Markers**
Large files use HTML comment markers for navigation:
- `<!-- CLAUDE-MARKER: section-name -->` - Search for these to understand file structure
- `database.py`: `database-manager-class`, `pensieve-api-methods`, `main-query-methods`

## Integration Patterns

### **Pensieve API Usage**
```python
# ✅ Preferred: Use DatabaseManager
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    data = db.fetch_tasks(limit=100)

# ❌ Avoid: Direct database access
conn = sqlite3.connect("~/.memos/database.db")
```

### **Configuration Hierarchy**
1. **Pensieve config**: Read from `memos config` when available
2. **Environment variables**: Override specific settings
3. **Default fallbacks**: Ensure system always works

### **Error Handling Patterns**
- **Graceful degradation**: Features work even if dependencies unavailable
- **Specific exceptions**: Never use bare `except:` clauses
- **Logging over print**: Use `logging.getLogger(__name__)`

## Common Workflows

### **Adding New AI Processing**
1. Check if Pensieve already provides the capability
2. Implement in `autotasktracker/ai/` with graceful fallbacks
3. Add integration tests in `tests/integration/`
4. Update health monitoring in `tests/health/`

### **Dashboard Development**  
1. Create in `autotasktracker/dashboards/`
2. Use components from `dashboards/components/`
3. Follow port conventions (8502, 8503, 8505, etc.)
4. Add to launcher system

### **Pensieve Integration**
1. Check Pensieve capabilities first (`memos --help`)
2. Implement API integration with fallback to direct database
3. Add health monitoring for the integration
4. Document integration percentage and limitations

## Performance Considerations

### **Database Optimization**
- Use connection pooling through DatabaseManager
- Prefer API methods when available for caching benefits
- Monitor query performance with built-in metrics

### **Memory Management**
- Screenshots can be large - process in batches
- Use streaming for large dataset operations
- Clear context frequently in long-running operations

### **AI Model Loading**
- Models are loaded on-demand to save memory
- Implement graceful fallbacks when models unavailable
- Cache embeddings to avoid recomputation

## Environment Dependencies

### **Critical Path**
- **Python virtual environment**: `venv/` (NOT anaconda3)
- **Pensieve installation**: Must be in same venv as AutoTaskTracker
- **Database location**: `~/.memos/database.db` (Pensieve managed)

### **Optional Dependencies**
- **sentence-transformers**: For semantic search (graceful fallback)
- **Ollama**: For VLM processing (graceful fallback)
- **pytest-xdist**: For parallel test execution