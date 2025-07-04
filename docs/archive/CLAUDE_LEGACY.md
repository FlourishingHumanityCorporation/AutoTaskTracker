
# CRITICAL CODING RULES - STRICTLY ENFORCE

## Code Quality Standards (MANDATORY)
- **NO BARE EXCEPT CLAUSES**: Always specify exception types `except (ValueError, TypeError):` instead of `except:`
- **NO SYS.PATH HACKS**: Use proper package imports instead of `sys.path.append()` or `sys.path.insert()`
- **USE DATABASE MANAGER**: Import from `autotasktracker.core.database.DatabaseManager` instead of direct `sqlite3.connect()`
- **NO DUPLICATE FILES**: Never create `*_improved.py`, `*_enhanced.py`, `*_v2.py` - edit the original file
- **PROPER LOGGING**: Use `logging.getLogger(__name__)` instead of `print()` statements in production code
- **SPECIFIC IMPORTS**: Import exact functions/classes needed, avoid `import *`

## File Organization Rules (MANDATORY)
- **NO ROOT CLUTTER**: Never create files in project root - use proper directories:
  - Scripts → `scripts/`
  - Tests → `tests/`
  - Dashboards → `autotasktracker/dashboards/`
  - AI components → `autotasktracker/ai/`
  - Core utilities → `autotasktracker/core/`
- **LEGACY ISOLATION**: Put deprecated code in `legacy/` subfolder, never in main directories
- **NO DEBUG FILES**: Remove temporary files like `debug_*.py`, `test_*.json`, `temp_*.py`

## Exception Handling Rules (MANDATORY)
```python
# ❌ WRONG - Bare except
try:
    risky_operation()
except:
    pass

# ✅ CORRECT - Specific exceptions
try:
    risky_operation()
except (ValueError, TypeError, ConnectionError) as e:
    logger.warning(f"Operation failed: {e}")
```

## Import Rules (MANDATORY)
```python
# ❌ WRONG - sys.path hack
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# ✅ CORRECT - Package import
from autotasktracker.core.database import DatabaseManager

# ❌ WRONG - Direct database connection
import sqlite3
conn = sqlite3.connect(db_path)

# ✅ CORRECT - Use DatabaseManager
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    # use connection
```

## Testing Commands (RUN BEFORE COMMITTING)
```bash
# MANDATORY: Run codebase health check before any commit
python -m pytest tests/test_codebase_health.py -v

    # ... (truncated - see source files)
```python

## Improved Error Messages
The codebase health tests now provide DETAILED, actionable error messages with:
    # ... (truncated - see source files for full implementation)
```
docs/
├── architecture/     # Technical design docs (max 1-2 core files)
├── features/        # Feature-specific documentation
├── guides/          # How-to guides and tutorials  
├── design/          # UI/UX specifications
├── planning/        # Future plans ONLY (not past achievements)
└── archive/         # Historical docs (minimize this)
```

### ✍️ **Writing Documentation**
```markdown
# ❌ WRONG - Announcement style
# 🚀 AutoTaskTracker is Now Live! 
We're thrilled to announce that AutoTaskTracker is complete! With 1000+ screenshots processed...

# ✅ CORRECT - Reference style  
# AutoTaskTracker Technical Reference
This document describes the AutoTaskTracker architecture and implementation.
```

### 🔗 **Code References**
```markdown
# ❌ WRONG - Large embedded code block
```python
def fetch_tasks(self, start_date=None, end_date=None, limit=100):
    # 50+ lines of code...
```

# ✅ CORRECT - Link to source
See `autotasktracker/core/database.py:fetch_tasks()` for implementation.

Key parameters:
- `start_date`: Filter by start date
- `limit`: Maximum results (default: 100)
```

### 📏 **Size Guidelines**
- **Architecture docs**: Max 800 lines (can be comprehensive)
- **Feature docs**: Max 500 lines (focused on one feature)
- **Guides**: Max 500 lines (task-oriented)
- **Planning docs**: Max 1000 lines (can explore ideas)

### 🚫 **Never Create These Documents**
- `PROJECT_UPDATE.md` - Status belongs in git commits
- `IMPLEMENTATION_COMPLETE.md` - Victory lap document
- `*_v2.md`, `*_improved.md` - Use git for versioning
- `DATA_STATUS.md` - Statistics become stale immediately

### ✅ **Always Create/Update These**
- `architecture/CODEBASE_DOCUMENTATION.md` - Primary technical reference
- `guides/FEATURE_MAP.md` - Feature-to-file mapping
- `guides/README_AI.md` - User guides for features

### 🧪 **Test Documentation Quality**
```bash
# Run before committing any docs changes
python tests/test_documentation_health.py

# This checks for:
# - Duplicate content
# - Outdated terminology  
# - Announcement style
# - Large code blocks
# - Professional tone
# - Proper organization
```python

## Key Lessons Learned (CRITICAL)

    # ... (truncated - see source files for full implementation)
```bash
# Setup
python3 -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
    # ... (truncated - see source files)
```

## Key File Locations
- Config: `~/.memos/config.yaml`
- Database: `~/.memos/database.db`
- Screenshots: `~/.memos/screenshots/`
- Logs: `~/.memos/logs/`

## Database Schema (Key Tables)
- `entities`: Contains file info including screenshots (filepath, created_at, last_scan_at)
- `metadata_entries`: Contains OCR text and active window data linked to entities
- Query pattern: 
```sql
SELECT e.*, me.value as ocr_text 
FROM entities e 
LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
WHERE e.file_type_group = 'image'
```

## Performance Considerations
- Screenshots: ~400MB/day, ~8GB/month storage
- CPU-only OCR is acceptable, but LLM features require GPU (8GB+ VRAM)
- Use pagination and thumbnails in dashboard to handle large datasets
- Configure retention policy in config.yaml to manage disk usage

## Common Issues & Solutions
1. **High resource usage**: Disable LLM features, use CPU-only mode
2. **Disk space**: Set appropriate retention in config.yaml
3. **Port conflicts**: Memos uses 8839, Streamlit dashboards use:
   - Task Board: 8502
   - Analytics: 8503
   - Time Tracker: 8505
   - Achievement Board: 8507
   - Pipeline Comparison: 8512
4. **No screenshots appearing**: Check `memos ps`, verify screen capture permissions
5. **Database not found**: Memos uses `database.db` not `memos.db`
6. **AI features not working**: Run `python ai_cli.py status` to check dependencies
7. **Timezone issues**: Recent updates fixed UTC/localtime conversion bugs
8. **Import errors**: Dashboard gracefully degrades if AI modules unavailable

## Development Priorities
1. ✅ Core functionality with Pensieve backend (Complete)
2. ✅ Basic Streamlit dashboard for task visualization (Complete)
3. Performance optimization (quantization, caching)
4. Advanced LLM integration (optional, requires GPU)

## Testing & Validation
- Verify screenshot capture: Check `~/.memos/screenshots/` directory
- Test OCR accuracy: Use `memos` web UI at http://localhost:8839
- Monitor performance: Watch CPU/memory usage during operation
- Validate task detection: Review activities in Streamlit dashboard at http://localhost:8502

## Deployment Notes
- Screenshots may contain sensitive information
- Consider cloud sync for backup and multi-device access
- Monitor storage usage as screenshots accumulate
- Configure appropriate retention policies

## Current Project Status
- ✅ Memos/Pensieve backend installed and running
- ✅ Screenshot capture working (780+ screenshots captured)
- ✅ Database integration functional
- ✅ Streamlit dashboard created and operational
- ✅ Task Analytics Dashboard with productivity insights
- ✅ All tests passing (9/9) including Playwright e2e tests
- ✅ OCR processing fully functional (585+ results)
- ✅ Task categorization implemented
- ✅ Export functionality (CSV, JSON, TXT reports)
- ✅ **AI FEATURES IMPLEMENTED:**
  - ✅ Embeddings-based semantic search and task similarity
  - ✅ OCR confidence scoring and layout analysis
  - ✅ AI-enhanced task extraction with confidence indicators
  - ✅ VLM integration ready (requires model setup)
  - ✅ AI-enhanced main dashboard with insight displays
  - ✅ Simple CLI tools for AI management (`ai_cli.py`)

## AI Enhancement Features
- ✅ **Semantic Search**: Find similar tasks using embedding vectors
- ✅ **Smart Task Grouping**: Group related activities automatically
- ✅ **OCR Quality Assessment**: Filter low-quality text extraction
- ✅ **AI Confidence Scores**: Show reliability of task detection
- ✅ **Visual Context Ready**: VLM integration for image understanding
- ✅ **Similar Task Discovery**: Show related work patterns
- ✅ **Enhanced Categories**: AI-powered activity categorization

## Future Enhancements
- Multimodal LLMs for better task understanding (VLM ready)
- Automated task pattern recognition using embeddings
- Enhanced UI element detection with YOLO models
- Advanced search and filtering capabilities (semantic search ready)
- Custom task rules and automation
- API integration with external task boards (Trello, Asana)