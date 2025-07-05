# Critical Dependencies & Load Order

## Environment Requirements

### **Python Virtual Environment**
- **CRITICAL**: Must use `venv/` environment, NOT `anaconda3/`
- **Pensieve dependency conflict**: Pensieve cannot be installed in anaconda3
- **Verification**: `which python` should point to `venv/bin/python`

### **Pensieve Installation Order**
1. **Create venv**: `python3 -m venv venv && source venv/bin/activate`
2. **Install AutoTaskTracker**: `pip install -e .`
3. **Initialize Pensieve**: `memos init && memos enable && memos start`
4. **Verify setup**: `memos ps` (should show running status)

## Database Dependencies

### **SQLite Database Access**
- **Location**: `~/.memos/database.db` (Pensieve managed)
- **NEVER**: Use `sqlite3.connect()` directly
- **ALWAYS**: Use `DatabaseManager` for all database operations
- **Connection pooling**: DatabaseManager handles connection lifecycle

### **API vs Direct Access Hierarchy**
1. **First preference**: Pensieve API (when healthy)
2. **Fallback**: Direct SQLite access via DatabaseManager
3. **Never**: Direct sqlite3.connect() calls

```python
# ✅ Correct dependency usage
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()  # Handles API health checks and fallbacks
```

## AI Model Loading Order

### **Optional Dependencies with Graceful Fallback**
- **sentence-transformers**: For embeddings/semantic search
- **ollama**: For VLM processing  
- **pytesseract**: For OCR enhancement

### **Loading Pattern**
```python
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    # Implement fallback behavior
```

## Streamlit Dashboard Dependencies

### **Port Allocation (CRITICAL)**
- **Memos service**: 8839 (Pensieve)
- **Task Board**: 8502 (main dashboard)
- **Analytics**: 8503 
- **Time Tracker**: 8505
- **Integration Health**: TBD

### **Dashboard Launch Order**
1. Ensure Pensieve is running (`memos ps`)
2. Start dashboards in any order (they're independent)
3. Each dashboard checks dependencies on startup

## Configuration Loading Hierarchy

### **Config Priority Order**
1. **Pensieve config**: `memos config` output
2. **Environment variables**: `.env` files
3. **Default values**: Hardcoded fallbacks

### **Critical Config Dependencies**
```python
# Load order matters
pensieve_config = get_pensieve_config()  # First
app_config = get_config()               # Then app config
db = DatabaseManager()                  # Then database connection
```

## Script Dependencies

### **Processing Scripts Load Order**
1. **Auto processor setup**: Environment and config validation
2. **Database connection**: Via DatabaseManager
3. **AI model loading**: On-demand with graceful fallbacks
4. **Processing pipeline**: OCR → VLM → Task extraction → Storage

### **Health Check Dependencies**
- **Database health**: Must verify before other checks
- **API health**: Pensieve API availability
- **Model health**: AI model loading status
- **Integration health**: End-to-end pipeline validation

## Inter-File Dependencies

### **Core Module Dependencies**
- `config.py` → Must load before any other modules
- `database.py` → Depends on config and Pensieve client
- `task_extractor.py` → Depends on database and AI modules

### **AI Module Dependencies**
- `ai_task_extractor.py` → Can use VLM, OCR, embeddings (all optional)
- `vlm_processor.py` → Depends on Ollama service
- `embeddings_search.py` → Depends on sentence-transformers

### **Dashboard Dependencies**
- All dashboards → Depend on database.py
- Analytics → Depends on data repositories
- Task board → Depends on task extraction pipeline

## Performance Dependencies

### **Connection Pool Management**
- DatabaseManager maintains connection pools
- Pool size based on system resources
- Automatic cleanup on application shutdown

### **Memory Dependencies**
- **Screenshots**: Can be large, process in batches
- **AI models**: Loaded on-demand to conserve memory
- **Embeddings cache**: Persistent storage to avoid recomputation

## Critical Path Validation

### **Startup Validation Order**
1. **Python environment**: Verify correct venv
2. **Pensieve service**: `memos ps` shows healthy
3. **Database access**: DatabaseManager connects successfully
4. **Optional AI models**: Load with graceful fallbacks
5. **Dashboard ports**: No conflicts on required ports

### **Health Check Commands**
```bash
# Verify critical path
memos ps                                    # Pensieve service
python scripts/pensieve_health_check.py    # Integration health  
pytest tests/health/ -v                    # System health
```

## Troubleshooting Dependencies

### **Common Dependency Issues**
- **Wrong Python env**: `which python` points to anaconda3
- **Pensieve not running**: `memos start` required
- **Port conflicts**: Check if ports 8502/8503/8505 are in use
- **Permission issues**: Database file permissions

### **Dependency Recovery**
1. **Environment reset**: Recreate venv with correct dependencies
2. **Pensieve reset**: `memos stop && memos start`  
3. **Database reset**: Backup and reinitialize if corrupted
4. **Model cache clear**: Remove cached models if corrupted