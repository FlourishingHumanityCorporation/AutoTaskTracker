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
8. **NEVER implement poor workarounds** - Fix the root causes of issues. Ask at least Why Something Happened three times. 
9. **NEVER bypass Pensieve capabilities** - Check Pensieve features before implementing custom solutions

### ALWAYS DO THESE:
1. **ALWAYS run ALL health tests before committing**
2. **ALWAYS check existing code first**: Don't create duplicate functionality
3. **ALWAYS use specific imports**: `from module import SpecificClass`
4. **ALWAYS update CLAUDE.md**: Document significant changes here
5. **ALWAYS follow file organization**: See [File Organization](#file-organization)
6. **ALWAYS delete completion docs immediately**: Never create status/summary/complete files
7. **ALWAYS use measured, technical language**: Avoid superlatives like "perfect", "flawless", "best","amazing", "excellent" in technical contexts
8. **ALWAYS leverage Pensieve first**: Check Pensieve capabilities before implementing custom solutions

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

## 🔗 PENSIEVE ARCHITECTURE IMPERATIVE

### 🎯 PENSIEVE-FIRST DEVELOPMENT PRINCIPLE

**Before implementing ANY feature, developers MUST:**

1. **Check Pensieve Documentation**: Review available APIs, plugins, and services
2. **Audit Current Utilization**: Understand what Pensieve already provides
3. **Design Integration-First**: Prefer Pensieve APIs over direct implementation
4. **Document Decision**: If custom implementation needed, document why Pensieve can't be used

- Vector Search: 60% ⚠️ (Implementation exists, limited by API availability)

### 📋 MANDATORY PENSIEVE INTEGRATION CHECKLIST

**For Any New Feature:**
- [ ] Checked `memos --help` for relevant commands
- [ ] Reviewed Pensieve REST API documentation
- [ ] Evaluated plugin system capabilities  
- [ ] Considered event-driven architecture
- [ ] Assessed configuration management needs

**For Data Processing:**
- [ ] Use Pensieve's built-in OCR processing (builtin_ocr plugin)
- [ ] Leverage built-in VLM processing (builtin_vlm plugin) 
- [ ] Utilize metadata_entries table for results storage
- [ ] Use DatabaseManager instead of direct sqlite3.connect()

**For File Operations:**
- [ ] Use Pensieve's screenshot directory structure
- [ ] Implement file validation and error handling
- [ ] Use service commands (scan, reindex) when appropriate
- [ ] Read configuration from Pensieve when possible

### 🛠️ PENSIEVE INTEGRATION PATTERNS

**✅ PREFERRED: DatabaseManager Approach**
```python
# Use DatabaseManager for consistent database access
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    screenshots = db.fetch_tasks(limit=100)
```

**✅ ACCEPTABLE: Service Commands**
```bash
# Use Pensieve commands for maintenance
memos scan           # Scan for new screenshots
memos ps            # Check service status  
memos start/stop    # Service management
memos config        # Read configuration
```

**❌ DISCOURAGED: Direct SQLite Access**
```python
# Avoid direct database connections
# Use DatabaseManager instead
conn = sqlite3.connect("~/.memos/database.db")  # DON'T DO THIS
```

### 📊 UTILIZATION MONITORING

**Required Metrics Tracking:**
- DatabaseManager usage vs. direct sqlite3.connect()
- Pensieve plugin usage (builtin_ocr, builtin_vlm) vs. custom processing
- Service command utilization (scan, config, reindex)
- Metadata schema compliance and efficiency

**Regular Reviews:**
- Audit scripts for direct database access violations
- Check OCR/VLM processing efficiency
- Monitor file system integration patterns
- Assess configuration management improvements


### ⚖️ ARCHITECTURAL DECISION FRAMEWORK

**When to Use Pensieve:**
- ✅ Feature exists in Pensieve (database, OCR, VLM plugins)
- ✅ Performance is acceptable (SQLite for <1M records)
- ✅ Maintains data consistency and schema compliance
- ✅ Simplifies maintenance and reduces code duplication

**When Custom Implementation is Justified:**
- ⚠️ Pensieve lacks specific functionality (advanced task extraction)
- ⚠️ Performance requirements exceed Pensieve capabilities
- ⚠️ AutoTaskTracker-specific UI/UX requirements
- ⚠️ AI processing that extends beyond Pensieve's scope

**Documentation Required for Custom Implementation:**
1. **Pensieve Capability Assessment**: What Pensieve provides and limitations
2. **Performance Justification**: Why Pensieve's approach is insufficient
3. **Integration Plan**: How custom solution uses Pensieve infrastructure
4. **Maintenance Plan**: Ongoing compatibility with Pensieve updates

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
- ✅ YES: Matter-of-fact summaries focused on next steps (not overconfident progress claims)

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

**2025-07-06: Dashboard Component Refactoring - COMPLETE**
- **Timeline Visualization Component** (`autotasktracker/dashboards/components/timeline_visualization.py`):
  - Activity timeline with gap visualization and hover details
  - Task timeline with horizontal bars and duration-based coloring
  - Gantt chart support with progress indicators and grouping
  - Timeline summary with metrics, gap analysis, and pattern detection
  - Quick timeline API with automatic type detection
  - Graceful fallback when Plotly unavailable
- **Session Controls Component** (`autotasktracker/dashboards/components/session_controls.py`):
  - Centralized cache management (clear cache, view stats)
  - Debug mode toggle with enhanced error display
  - Real-time mode controls with refresh rate settings
  - Session information display with duration tracking
  - Custom control hooks for dashboard-specific actions
  - Compact and expanded display modes
- **Smart Defaults Component** (`autotasktracker/dashboards/components/smart_defaults.py`):
  - Intelligent time period selection based on data availability and quality
  - Category recommendations from activity patterns
  - Comprehensive reasoning generation for user transparency
  - Data summary statistics integration
  - Enhanced logic extraction from TimeFilterComponent
- **Dashboard Integration Updates**:
  - Updated 5 dashboards (task_board.py, analytics.py, timetracker.py, advanced_analytics.py, vlm_monitor.py)
  - Replaced all `render_cache_controls()` calls with SessionControlsComponent
  - Updated TimeFilterComponent to use new smart defaults logic
- **Testing**: All 66 unit tests passing for new components (26 + 20 + 20)
- **Technical Debt Cleanup**: Completed comprehensive cleanup of refactoring artifacts
- **Completion**: Dashboard component refactoring **100% COMPLETE** with 11/11 components extracted and integrated

**Technical Debt Resolution:**
- **Import Cleanup**: Removed unused imports and fixed duplicate imports across 32+ files
  - Fixed duplicate `streamlit` import in `filters.py`
  - Removed unused `threading` import in `task_board.py`  
  - Consolidated duplicate `SmartDefaultsComponent` imports in `task_board.py`
- **Component Consolidation**: Addressed duplicate functionality patterns
  - Refactored `RawDataViewer` to use `ExportComponent` instead of inline CSV export
  - Marked `TimelineChart` as deprecated, delegates to `TimelineVisualizationComponent`
  - Identified 9 areas of duplicate functionality for future consolidation
- **Error Handling Consistency**: Standardized exception handling patterns
  - Fixed inconsistent exception logging in `SmartDefaultsComponent`
  - Ensured all exceptions include proper logging messages
  - Validated no bare except clauses exist
- **Type Hints**: Added missing return type annotations to improve code clarity
  - Fixed `_clear_cache()`, `render_minimal()`, `_calculate_diversity_factor()`, `_add_gap_visualization()`
- **Dashboard Migration**: Updated 8 dashboards to use SessionControlsComponent instead of `render_cache_controls()`
- **Code Quality**: All components pass import validation and follow consistent patterns

---

END OF INSTRUCTIONS - Now you can work on AutoTaskTracker!