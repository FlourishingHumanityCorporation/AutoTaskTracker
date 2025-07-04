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
1. **NEVER create `*_improved.py`, `*_enhanced.py`, `*_v2.py`** - ALWAYS edit the original file
2. **NEVER create files in root directory** - Use proper subdirectories
3. **NEVER use bare except clauses** - Always specify exception types
4. **NEVER use `sys.path.append()`** - Use proper package imports
5. **NEVER use `sqlite3.connect()` directly** - Use `DatabaseManager`
6. **NEVER use `print()` in production** - Use `logging.getLogger(__name__)`
7. **NEVER create announcement-style docs** - No "We're excited to announce!"

### ALWAYS DO THESE:
1. **ALWAYS run tests before committing**: `pytest tests/test_codebase_health.py`
2. **ALWAYS check existing code first**: Don't create duplicate functionality
3. **ALWAYS use specific imports**: `from module import SpecificClass`
4. **ALWAYS update CLAUDE.md**: Document significant changes here
5. **ALWAYS follow file organization**: See [File Organization](#file-organization)

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
│   ├── dashboards/           # Streamlit UIs
│   │   ├── task_board.py     # Main dashboard
│   │   ├── analytics.py      # Analytics dashboard
│   │   └── legacy/           # Old versions (don't modify)
│   ├── comparison/           # AI pipeline comparison tools
│   └── utils/                # Shared utilities
├── scripts/                  # Standalone scripts
├── tests/                    # All tests
├── docs/                     # Documentation (organized!)
└── CLAUDE.md                 # THIS FILE - AI instructions
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

# All dashboards
python autotasktracker.py start
```

### AI Features
```bash
# Check AI status
python scripts/ai_cli.py status

# Generate embeddings
python scripts/ai_cli.py embeddings --limit 50

# Enable VLM (optional, needs Ollama)
python scripts/ai_cli.py enable-vlm

# VLM Management
python scripts/vlm_manager.py status        # Check VLM coverage
python scripts/vlm_manager.py start         # Start processing service
python scripts/vlm_manager.py optimize      # Run high-performance batch
python scripts/vlm_manager.py benchmark     # Test VLM speed
```

---

## 🧪 TESTING REQUIREMENTS

### MANDATORY Before ANY Commit:
```bash
# 1. Code quality check
pytest tests/test_codebase_health.py -v

# 2. Documentation check
pytest tests/test_documentation_health.py -v

# 3. Critical functionality
pytest tests/test_critical.py -v

# Quick check for common issues
python -c "
import glob
for f in glob.glob('autotasktracker/**/*.py', recursive=True):
    with open(f) as file:
        content = file.read()
        if 'except:' in content:
            print(f'🚨 BARE EXCEPT in {f}')
        if 'sys.path' in content:
            print(f'🚨 SYS.PATH HACK in {f}')
"
```

### What Tests Check:
- ✅ No bare except clauses
- ✅ No sys.path hacks
- ✅ No root directory clutter
- ✅ Proper database usage
- ✅ Documentation quality
- ✅ No duplicate/improved files

---

## 📚 DOCUMENTATION STANDARDS

### Documentation Structure
```
docs/
├── architecture/     # Technical design (1-2 files max)
├── features/        # Feature docs
├── guides/          # How-to guides
├── design/          # UI/UX specs
├── planning/        # Future plans only
└── archive/         # Old docs (minimize)
```

### Writing Rules:
- ❌ NO: "We're excited to announce..."
- ❌ NO: "Successfully implemented!"
- ❌ NO: "As of December 2024..."
- ❌ NO: Code blocks > 20 lines
- ✅ YES: Professional, timeless language
- ✅ YES: Link to source files
- ✅ YES: Focus on "what" and "how"

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

### AI Features Not Working
1. Run `python scripts/ai_cli.py status`
2. Install sentence-transformers: `pip install sentence-transformers`
3. For VLM: Install Ollama and pull minicpm-v model

### Import Errors
- Scripts need parent directory in sys.path
- Dashboards gracefully degrade if AI modules missing
- Check virtual environment is activated

---

## 📝 CHANGE LOG
Document significant changes here with date and description.

2025-07-04: Major Dashboard Architecture Refactoring - COMPLETE
- **🏗️ Built comprehensive new dashboard architecture with 40% code reduction**
- Created `BaseDashboard` class with common functionality (connection, caching, error handling)
- Built 15+ reusable UI components: filters, metrics, visualizations, data display
- Implemented 3-layer data architecture: UI → Repository → Database
- Added unified caching system with TTL and smart invalidation
- **📊 Completed refactored dashboards:**
  - `task_board_refactored.py` (650→250 lines, 61% reduction)
  - `analytics_refactored.py` (580→280 lines, 52% reduction) 
  - `achievement_board_refactored.py` (570→280 lines, 51% reduction)
- **✅ 100% test coverage** for core functionality (`tests/test_dashboard_core.py`)
- Added `launcher_refactored.py` for managing new dashboard system
- **📚 Complete documentation:** `REFACTORING_COMPLETE.md`, `MIGRATION_GUIDE.md`, `REFACTORING_RESULTS.md`
- **🚀 Ready for production:** All refactored dashboards tested and validated

2025-07-04: Enhanced Time Tracking System
- Added `autotasktracker/core/time_tracker.py` with screenshot-aware session detection
- Implemented confidence scoring for time estimates (🟢🟡🔴 indicators)
- Added active vs total time metrics to distinguish work from idle time
- Auto-detects screenshot intervals from memos config (4 seconds default)
- Category-aware gap thresholds (Development: 10min, Reading: 15min, etc.)
- Updated timetracker.py dashboard with enhanced metrics and explanations
- See `docs/features/TIME_TRACKING_ENHANCED.md` for technical details

2025-01-04: VLM Processing Optimization
- Implemented async batch processing with 5x speedup
- Added image resizing and caching to reduce overhead
- Created perceptual hash deduplication system
- Added task-specific prompts for better context
- New commands: `vlm_manager.py optimize` for high-performance processing
- Fixed VLM bottlenecks: serial → concurrent, large images → resized
- Created `vlm_batch_optimizer.py` with async/await architecture

---

END OF INSTRUCTIONS - Now you can work on AutoTaskTracker!