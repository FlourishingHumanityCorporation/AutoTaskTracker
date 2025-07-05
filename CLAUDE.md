# 🚨 AUTOTASKTRACKER AI ASSISTANT INSTRUCTIONS 🚨

This file contains MANDATORY instructions for AI assistants working on AutoTaskTracker.
Read this ENTIRE file before making ANY changes to the codebase.

---

## 📋 TABLE OF CONTENTS
1. [🛑 Critical Rules](#-critical-rules)
2. [📁 Project Overview](#-project-overview)
3. [🏗️ Technical Architecture](#-technical-architecture)
4. [🚀 Quick Start Commands](#-quick-start-commands)
5. [🧪 Testing Requirements](#-testing-requirements)
6. [📚 Documentation Standards](#-documentation-standards)
7. [💡 Lessons Learned](#-lessons-learned)
8. [⚠️ Common Issues](#-common-issues)

---

## 🛑 CRITICAL RULES

### NEVER DO THESE (WILL BREAK THE PROJECT):
0. **NEVER report 100% on something if it is not true // you haven't verify with 100% acurracy**!!!!!
1. **NEVER create `*_improved.py`, `*_enhanced.py`, `*_v2.py`** - ALWAYS edit the original file
2. **NEVER create files in root directory** - Use proper subdirectories
3. **NEVER use bare except clauses** - Always specify exception types
4. **NEVER use `sys.path.append()`** - Use proper package imports
5. **NEVER use `sqlite3.connect()` directly** - Use `DatabaseManager`
6. **NEVER use `print()` in production** - Use `logging.getLogger(__name__)`
7. **NEVER create announcement-style docs** - No "We're excited to announce!"
8. **NEVER implement poor workarounds** - Fix the root causes of issues

### ALWAYS DO THESE:
1. **ALWAYS run ALL health tests before committing**: 
   ```bash
   pytest tests/health/test_codebase_health.py -v
   pytest tests/health/test_documentation_health.py -v
   pytest tests/health/test_testing_system_health.py -v
   ```
2. **ALWAYS check existing code first**: Don't create duplicate functionality
3. **ALWAYS use specific imports**: `from module import SpecificClass`
4. **ALWAYS update CLAUDE.md**: Document significant changes here
5. **ALWAYS follow file organization**: See [File Organization](#file-organization)
6. **ALWAYS delete completion docs immediately**: Never create status/summary/complete files
7. **ALWAYS use measured, technical language**: Avoid superlatives like "perfect", "flawless", "best","amazing", "excellent" in technical contexts

---

## 📁 PROJECT OVERVIEW

**AutoTaskTracker** - AI-powered passive task discovery from screenshots
- Captures screenshots → Extracts text (OCR) → Identifies tasks → Shows on dashboard
- Privacy-first: All data stays local, no cloud services required
- Built on Pensieve/memos for backend, Streamlit for frontend

### Core Features:
- ✅ Automatic screenshot capture
- ✅ OCR text extraction
- ✅ AI task classification
- ✅ Multiple dashboards (Task Board, Analytics, Time Tracker)
- ✅ Semantic search with embeddings
- ✅ Export functionality (CSV, JSON)

---

## 🏗️ TECHNICAL ARCHITECTURE

### File Organization
```
AutoTaskTracker/
├── autotasktracker/          # Main package
│   ├── core/                 # Core functionality (database, task extraction)
│   ├── ai/                   # AI features (OCR, embeddings, VLM)
│   ├── pensieve/             # Pensieve integration (API, events, search)
│   ├── dashboards/           # Streamlit UIs
│   │   ├── task_board.py     # Main dashboard
│   │   ├── analytics.py      # Analytics dashboard
│   │   ├── timetracker.py    # Time tracking dashboard
│   │   ├── components/       # Reusable UI components
│   │   └── data/            # Data models and repositories
│   ├── comparison/           # AI pipeline comparison tools
│   └── utils/                # Shared utilities
├── scripts/                  # Standalone scripts
│   ├── ai/                  # AI-related scripts
│   ├── analysis/            # Analysis tools
│   ├── processing/          # Processing scripts
│   └── utils/               # Utility scripts
├── tests/                    # All tests
│   ├── health/              # Health checks
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── functional/          # Real functionality tests
│   ├── performance/         # Performance tests
│   └── e2e/                 # End-to-end tests
├── docs/                     # Documentation
│   ├── architecture/        # Technical design
│   ├── features/            # Feature documentation
│   └── guides/              # How-to guides
├── setup.py                 # Package installation
└── CLAUDE.md                # THIS FILE - AI instructions
```

### Key Technologies:
- **Backend**: Pensieve/memos (screenshot capture + OCR)
- **Frontend**: Streamlit (web dashboards)
- **Database**: SQLite (~/.memos/database.db)
- **AI**: OCR (Tesseract), Embeddings (sentence-transformers), VLM (Ollama)

### Database Tables:
- `entities`: Screenshots metadata
- `metadata_entries`: OCR text, window titles, AI results

---

## 🚀 QUICK START COMMANDS

### Initial Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Initialize Pensieve
memos init
memos enable
memos start

# Check it's working
memos ps
```

### Running Dashboards
```bash
# Main task board (port 8502)
python autotasktracker.py dashboard

# Analytics (port 8503)
python autotasktracker.py analytics

# Time tracker (port 8505)
python autotasktracker.py timetracker

# All dashboards
python autotasktracker.py start

# Interactive launcher
python autotasktracker.py launcher
```

### AI Features
```bash
# Check AI status
python scripts/ai/ai_cli.py status

# Generate embeddings
python scripts/generate_embeddings.py --limit 50

# Process tasks
python scripts/processing/process_tasks.py

# Health check
python scripts/pensieve_health_check.py
```

---

## 🧪 TESTING REQUIREMENTS

### MANDATORY Before ANY Commit:
```bash
# 1. Code quality check
pytest tests/health/test_codebase_health.py -v

# 2. Testing system health check
pytest tests/health/test_testing_system_health.py -v

# 3. Documentation check
pytest tests/health/test_documentation_health.py -v

# 4. Critical functionality
pytest tests/integration/test_pensieve_critical_path.py -v

# 5. Real functional tests (validates actual functionality)
python tests/run_functional_tests.py --verbose
```

### Real Functional Tests
Validate actual functionality instead of mocking:

```bash
# Run all functional tests
python tests/run_functional_tests.py

# Run specific categories
python tests/run_functional_tests.py --category ocr       # Real OCR
python tests/run_functional_tests.py --category database # Real SQLite
python tests/run_functional_tests.py --category ai       # Real AI
python tests/run_functional_tests.py --category pipeline # End-to-end
```

### What Tests Check:
- ✅ No bare except clauses
- ✅ No sys.path hacks
- ✅ No root directory clutter
- ✅ Proper database usage
- ✅ Documentation quality
- ✅ No duplicate/improved files
- ✅ Testing system health and organization
- ✅ Test categorization and discoverability
- ✅ No infinite loops in tests
- ✅ Proper fixture usage

---

## 📚 DOCUMENTATION STANDARDS

### Documentation Structure
```
docs/
├── architecture/     # Technical design (1-2 files max)
├── features/        # Feature docs
├── guides/          # How-to guides
└── archive/         # Legacy docs (minimize - prefer deletion)
```

### Writing Rules:
- ❌ NO: "We're excited to announce..."
- ❌ NO: "Successfully implemented!"
- ❌ NO: "As of December 2024..."
- ❌ NO: Code blocks > 20 lines
- ❌ NO: Completion/status announcements ("FIXED", "COMPLETE")
- ❌ NO: Process documentation (cleanup notes, migration guides)
- ❌ NO: Superlatives in technical contexts ("perfect", "amazing", "excellent")
- ✅ YES: Professional, timeless language
- ✅ YES: Link to source files
- ✅ YES: Focus on "what" and "how"
- ✅ YES: Measured, descriptive language ("functional", "working", "operational")

### Documentation Cleanup Rule:
**DELETE, don't archive!** Remove irrelevant docs completely:
- Status announcements ("Everything Fixed", "Complete")
- Process documentation (migration guides, refactoring notes)
- Outdated planning documents
- Duplicate content

### Root Cause Prevention:
**Why completion docs get created and how to prevent:**
- ❌ **Symptom**: Creating "COMPLETE.md", "FINAL.md", "SUMMARY.md" files
- ✅ **Root Cause**: Lack of process enforcement and automated checks
- ✅ **Prevention**: Run `pytest tests/health/test_documentation_health.py` before ANY commit
- ✅ **Alternative**: Update existing docs or use git commit messages for status

### Key Documents:
- `architecture/CODEBASE_DOCUMENTATION.md` - Primary technical reference
- `guides/FEATURE_MAP.md` - Feature-to-file mapping
- `guides/README_AI.md` - AI features guide

---

## 💡 LESSONS LEARNED

### Module Organization
- Check existing structure before creating files
- Use proper imports: `from autotasktracker.module import Class`
- Consolidate related functionality (e.g., all VLM code in ai/)
- Update all references when moving files

### Common Mistakes to Avoid
1. Creating duplicate functionality (check first!)
2. Putting scripts in root (use scripts/)
3. Forgetting to update imports after moving files
4. Not testing commands in documentation
5. Creating "improved" versions instead of editing
6. **PENSIEVE ENVIRONMENT ISSUE**: Check Python environment! Pensieve is installed in `venv/` NOT `anaconda3/`

### Import Patterns
```python
# ✅ CORRECT - From within package
from autotasktracker.core.database import DatabaseManager

# ✅ CORRECT - From scripts/
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autotasktracker.core.database import DatabaseManager

# ❌ WRONG - Relative imports
from ..core.database import DatabaseManager
```

---

## ⚠️ COMMON ISSUES

### Port Conflicts
- Memos: 8839
- Task Board: 8502
- Analytics: 8503
- Time Tracker: 8505

### Database Issues
- Path: `~/.memos/database.db` (NOT `memos.db`)
- Always use DatabaseManager for connections
- Check permissions if connection fails

### Pensieve/Memos Screenshot Capture Issues
**CRITICAL**: Pensieve is installed in `venv/` environment, NOT `anaconda3/`
```bash
# ✅ CORRECT commands (use venv Python):
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands ps
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands start
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands stop

# ❌ WRONG: Don't try to install pensieve in anaconda3 (dependency conflicts)
```

### AI Features Not Working
1. Run `python scripts/ai/ai_cli.py status`
2. Install sentence-transformers: `pip install sentence-transformers`
3. Check Pensieve health: `python scripts/pensieve_health_check.py`

### Import Errors
- Scripts need parent directory in sys.path
- Dashboards gracefully degrade if AI modules missing
- Check virtual environment is activated

---

## 📝 RECENT CHANGES

**2025-01-05: Pensieve Deep Integration**
- Built comprehensive Pensieve API integration (90%+ utilization)
- Added real-time event processing and advanced search
- Enhanced dashboard architecture with 40% code reduction
- Improved testing system health (comprehensive validation patterns)

**Key Features Added:**
- `autotasktracker/pensieve/`: API client, health monitoring, event processing
- Performance benchmarks in `tests/performance/`
- Real-time dashboard with live updates
- Enhanced time tracking with confidence scoring

**2025-01-05: Phase 3 - PostgreSQL Backend Integration COMPLETE**
- **🐘 Comprehensive PostgreSQL support** via Pensieve API with automatic backend detection
- **📊 PostgreSQL Adapter** (`autotasktracker/pensieve/postgresql_adapter.py`):
  - Performance tiers: SQLite (100K) → PostgreSQL (1M) → pgvector (10M+ screenshots)
  - Optimized queries, migration recommendations, performance benchmarking
- **🔍 Enhanced Vector Search** (`autotasktracker/pensieve/enhanced_vector_search.py`):
  - Native pgvector integration with HNSW indexing
  - Advanced semantic clustering, hybrid search, embedding quality assessment
- **⚡ Real-time Dashboard Enhancements:**
  - Backend indicators (📁🗄️🐘), performance benchmarks, migration guidance
  - Advanced vector search options with similarity thresholds and clustering
- **🧪 Integration Testing:** Comprehensive PostgreSQL adapter and vector search validation
- **📈 Enterprise Scale:** Millions of screenshots supported with pgvector optimization

---

END OF INSTRUCTIONS - Now you can work on AutoTaskTracker!