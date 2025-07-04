
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

# CRITICAL: Test specific issues (will show DETAILED error messages):
python -m pytest tests/test_codebase_health.py::TestCodebaseHealth::test_root_directory_clutter -v -s  # 🚨 ROOT ORGANIZATION
python -m pytest tests/test_codebase_health.py::TestCodebaseHealth::test_bare_except_clauses -v -s     # 🚨 ERROR HANDLING
python -m pytest tests/test_codebase_health.py::TestCodebaseHealth::test_no_sys_path_hacks -v -s       # 🚨 IMPORTS
python -m pytest tests/test_codebase_health.py::TestCodebaseHealth::test_database_connection_patterns -v -s  # 🚨 DATABASE

# MANDATORY: Run critical tests
python -m pytest tests/test_critical.py -v

# QUICK: Check for immediate code issues
python -c "
import ast
import glob
for f in glob.glob('autotasktracker/**/*.py', recursive=True):
    try:
        with open(f) as file:
            content = file.read()
            if 'except:' in content and 'except Exception:' not in content:
                print(f'🚨 BARE EXCEPT in {f}')
            if 'sys.path' in content and 'autotasktracker' in f:
                print(f'🚨 SYS.PATH HACK in {f}')
    except: pass
"

# ORGANIZATION: Check root directory cleanliness
ls -la | grep -E '\.(py|md|json|csv)$' | grep -v -E '(README|CLAUDE|QUICKSTART|requirements|autotasktracker\.py)'
```

## Improved Error Messages
The codebase health tests now provide DETAILED, actionable error messages with:
- 🚨 Clear categorization of issues (DOCUMENTATION CLUTTER, DEBUG FILES, etc.)
- ✅ Specific allowed files listed
- 🔧 Exact commands to fix issues
- 📊 Visual indicators (emojis) for immediate recognition

When tests fail, you'll see EXACTLY what needs to be fixed and how to fix it!

## ORIGINAL INSTRUCTIONS
- IMPROVE THE CURRENT FILE RATHER THAN CREATING A NEW FILE THAT'S CALLED FILE_IMPROVED!!!
- NEVER CREATE FILES IN ROOT DIRECTORY - ALWAYS FIND THE RIGHT DIRECTORY TO PUT THE FILE IN BEFORE CREATING IT
- LABEL EACH FILE AS DESCRIPTIVE AS POSSIBLE AND CLEARLY DOCUMENT THE PURPOSE OF THE FILE
- DOCUMENT ALL CHANGES IN THE CLAUDE.md FILE

# AutoTaskTracker - Mission Critical Context

## Project Overview
AutoTaskTracker is an AI-powered application that passively discovers and organizes daily tasks from screenshots. It runs continuously in the background, capturing screen activity and using AI to infer completed tasks without manual logging.

## Core Requirements
- **Passive Operation**: Must run unobtrusively in the background without impacting system performance
- **AI-Powered Analysis**: Uses OCR, object detection, and LLMs to understand screen content
- **Engaging Interface**: Custom task board showing discovered tasks and productivity insights
- **Automated Discovery**: Automatically identifies and categorizes tasks from screen activity

## Technical Architecture

### Backend (Python/Pensieve)
- **Pensieve** (memos): Open-source Python package for screenshot capture and AI analysis
- Three core services:
  - `memos record`: Captures screenshots at regular intervals
  - `memos watch`: Queues screenshots for AI processing
  - `memos serve`: Provides REST API and web interface
- Data stored in `~/.memos/` directory (config, SQLite DB, screenshots)
- AI Pipeline: Screenshot → OCR → Embeddings → Task Classification

### Frontend (Streamlit)
- Custom dashboard at `task_board.py`
- Connects directly to Pensieve SQLite database
- Displays tasks with screenshots, timestamps, and AI-generated summaries
- Real-time updates as new tasks are discovered

### AI Components
- **OCR**: Tesseract or EasyOCR for text extraction
- **Embeddings**: jinaai/jina-embeddings-v2-base-en for semantic search
- **Optional LLM**: Ollama with minicpm-v model for advanced task summarization
- **UI Detection**: YOLOv8n for identifying buttons, forms, etc.

## Critical Commands
```bash
# Setup
python3 -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install memos streamlit pandas plotly

# Initialize and start Pensieve
memos init
memos enable
memos start

# Check status
memos ps

# View logs
ls ~/.memos/logs/

# AI FEATURES - NEW
# One-command AI setup (installs dependencies, generates embeddings)
python ai_cli.py setup

# Check AI feature status
python ai_cli.py status

# Generate embeddings for semantic search
python ai_cli.py embeddings

# Enable VLM for visual context (requires Ollama + minicpm-v model)
python ai_cli.py enable-vlm

# Run AI-enhanced dashboard (NEW - with AI insights)
./venv/bin/streamlit run autotasktracker/dashboards/task_board.py

# Run analytics dashboard
./venv/bin/streamlit run autotasktracker/dashboards/analytics.py --server.port 8503

# Alternative: Run via main CLI
python autotasktracker.py analytics

# Or run in background
./venv/bin/streamlit run autotasktracker/dashboards/task_board.py --server.headless true --server.port 8502 &
./venv/bin/streamlit run autotasktracker/dashboards/analytics.py --server.headless true --server.port 8503 &

# CLI shortcuts for all dashboards
python autotasktracker.py start         # Start all services
python autotasktracker.py dashboard     # Main task board (port 8502)
python autotasktracker.py analytics     # Analytics dashboard (port 8503)
python autotasktracker.py timetracker   # Time tracker (port 8504)
python autotasktracker.py status        # Check system status
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
3. **Port conflicts**: Memos uses 8839, Streamlit dashboards use 8502-8504
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