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
7. [📐 Arrow-Chain Root-Cause Analysis](#-arrow-chain-root-cause-analysis)
8. [💡 Lessons Learned](#-lessons-learned)
9. [⚠️ Common Issues](#-common-issues)
10. [🌐 Browser Audit Workflow](#-browser-audit-workflow)

---

## 🛑 CRITICAL RULES

### NEVER DO THESE (WILL BREAK THE PROJECT):  ☐ Must all remain unchecked before commit
1. **NEVER create `*_improved.py`, `*_enhanced.py`, `*_v2.py`** - ALWAYS edit the original file
2. **NEVER create files in root directory** - Use proper subdirectories
3. **NEVER use bare except clauses** - Always specify exception types
4. **NEVER use `sys.path.append()`** - Use proper package imports
5. **NEVER use `sqlite3.connect()` directly** - Use `DatabaseManager`
6. **NEVER use `print()` in production** - Use `logging.getLogger(__name__)`
7. **NEVER create announcement-style docs** - No "We're excited to announce!"
8. **NEVER implement poor workarounds** - Fix the root causes of issues. Use Arrow-Chain RCA methodology (see [Root Cause Analysis](#-arrow-chain-root-cause-analysis))
9. **NEVER bypass Pensieve capabilities** - Check Pensieve features before implementing custom solutions
10. **NEVER report 100% on something if it is not true** - Verify with 100% accuracy

### ALWAYS DO THESE: ☐ All boxes must be ticked
1. **ALWAYS check existing code first**: Don't create duplicate functionality
2. **ALWAYS use specific imports**: `from module import SpecificClass`
3. **ALWAYS update CLAUDE.md**: Document significant changes here
4. **ALWAYS follow file organization**: See [File Organization](#file-organization)
5. **ALWAYS delete completion docs immediately**: Never create status/summary/complete files
6. **ALWAYS use measured, technical language**: Avoid superlatives like "perfect", "flawless", "best","amazing", "excellent" in technical contexts
7. **ALWAYS use Arrow-Chain RCA for debugging**: Follow S-T-A-H-V-P methodology for all bug fixes
8. **ALWAYS leverage Pensieve first**: Check Pensieve capabilities before implementing custom solutions
9. **ALWAYS run ALL health tests before committing**
10. **ALWAYS use DatabaseManager for database connections**

---

## 📁 PROJECT OVERVIEW

**AutoTaskTracker** - AI-powered passive task discovery from screenshots
- Captures screenshots → Extracts text (OCR) → Identifies tasks → Shows on dashboard
- Privacy-first: All data stays local, no cloud services required
- Built on Pensieve/memos for backend, Streamlit for frontend

### 🚨 CRITICAL PROJECT DISTINCTION
**AutoTaskTracker ≠ AITaskTracker**
- **AutoTaskTracker** (THIS PROJECT): Uses Pensieve/memos backend, Python/Streamlit frontend
- **AITaskTracker** (OTHER PROJECT): Different architecture, may also use Pensieve
- **DO NOT CONFUSE**: These are separate codebases with different patterns and requirements
- **WHEN IN DOUBT**: Check project root directory name and package structure

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
- **Database**: PostgreSQL (localhost:5433/autotasktracker)

### Port Allocation:
- Memos: 8839 (Pensieve default)
- Memos Web: 8840
- Task Board: 8602
- Analytics: 8603
- Time Tracker: 8605
- Notifications: 8606
- Advanced Analytics: 8607
- Overview: 8608
- Focus Tracker: 8609
- Daily Summary: 8610

### Database Architecture:
- `entities`: Screenshots metadata
- `metadata_entries`: OCR text, window titles, AI results

### Database Configuration:
- **Path**: PostgreSQL at localhost:5433/autotasktracker
- **Config**: `/Users/paulrohde/AutoTaskTracker.memos/autotask-config.yaml`
- **Screenshots**: `/Users/paulrohde/AutoTaskTracker.memos/screenshots/`
- **Environment**: `MEMOS_CONFIG_PATH=/Users/paulrohde/AutoTaskTracker.memos/autotask-config.yaml`

---

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
# Main task board (port 8602)
python autotasktracker.py dashboard

# Analytics (port 8603)
python autotasktracker.py analytics

# Time tracker (port 8605)
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
# Run all health tests
pytest tests/health/ -v

# Run specific test suites
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/functional/ -v
pytest tests/performance/ -v
pytest tests/e2e/ -v

# Check documentation health
pytest tests/health/test_documentation_health.py -v
```

### What Tests Check:
- **Health Tests**: Codebase structure, configuration, documentation
- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interactions, database connections
- **Functional Tests**: Real screenshot processing, AI features
- **Performance Tests**: Response times, memory usage
- **E2E Tests**: Complete user workflows

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
- **CLAUDE.md**: AI assistant instructions (this file)
- **README.md**: Project setup and overview
- **docs/architecture/CODEBASE_DOCUMENTATION.md**: Primary technical reference
- **docs/guides/FEATURE_MAP.md**: Feature-to-file mapping
- **docs/guides/README_AI.md**: AI features guide

---

## 📐 ARROW-CHAIN ROOT-CAUSE ANALYSIS

**MANDATORY for all bug fixes and debugging in AutoTaskTracker**

### Framework Overview

The Arrow-Chain RCA methodology ensures systematic problem-solving by tracing data flow from symptoms to root causes:

```
symptom₀
     ↓ (observation / log / metric)
checkpoint₁
     ↓ (data transformation, API, queue, …)
checkpoint₂
     ↓
⋯
checkpointₙ
     ↓ (fault)
root-cause
```

### S-T-A-H-V-P Methodology

**Mnemonic**: Symptom → Trace → Arrow chain → Hypothesis → Validate → Patch

| Phase | What to do | Typical artifacts |
|-------|-----------|------------------|
| 1. **S**ymptom | List every visible defect (UI glitch, wrong value, crash) | Bug ticket, screenshot, user log |
| 2. **T**race | Walk downstream (where consumed?) and upstream (where produced?) | Source map, call graph, API logs |
| 3. **A**rrow chain | Write one line per hop: A → B → C until first divergence | ASCII diagram in PR/comment |
| 4. **H**ypothesis | Articulate what should have happened vs. what did happen | One-sentence root-cause statement |
| 5. **V**alidate | Reproduce with controlled test; confirm fix resolves symptom | Unit/integration test, log snippet |
| 6. **P**atch | Implement fix, add regression tests, update docs/monitoring | PR diff, CI job, updated docs |

### AutoTaskTracker-Specific RCA Examples

#### Example 1: OCR Text Missing

**Symptom**: Task cards show "No content" despite screenshots containing visible text

**Arrow Chain**:
```
Screenshot captured with text
     ↓ (Pensieve scan)
Pensieve OCR plugin processes image
     ↓ (builtin_ocr plugin)
OCR text = null in metadata_entries        ← root cause: Tesseract timeout
     ↓ (DatabaseManager query)
fetch_tasks() returns empty content
     ↓ (Streamlit UI)
Task board shows "No content"
```

**Fix**: Increase OCR timeout in Pensieve config, add retry logic in OCR processor

#### Example 2: Dashboard Port Conflict

**Symptom**: "Port 8502 is already in use" error when starting task board

**Arrow Chain**:
```
python autotasktracker.py dashboard
     ↓ (Streamlit app.run)
st.run_app(port=8502)
     ↓ (OS port binding)
Port 8502 already bound to AITaskTracker        ← root cause: port conflict
     ↓ (Exception)
AddressAlreadyInUse error
```

**Fix**: Use AutoTaskTracker dedicated port range (8600s), update config

### Implementation Checklist

When debugging ANY issue:

- [ ] Document the visible symptom(s) with screenshots/logs
- [ ] Trace data flow through the system (use grep/search tools)
- [ ] Draw arrow chain showing each transformation point
- [ ] Identify the FIRST point where data diverges from expected
- [ ] Form hypothesis about root cause (not just proximate cause)
- [ ] Create minimal test case that reproduces the issue
- [ ] Implement fix at the root cause level
- [ ] Add regression test to prevent recurrence
- [ ] Update documentation if needed

### Common AutoTaskTracker Checkpoints

1. **Screenshot Pipeline**: 
   - Pensieve capture → `screenshots/` → OCR processing → `metadata_entries` table

2. **AI Processing**:
   - OCR text → Task extraction → Embeddings → Vector search → UI display

3. **Database Flow**:
   - DatabaseManager → PostgreSQL → Query results → Streamlit components

4. **Configuration Chain**:
   - `MEMOS_CONFIG_PATH` → `autotask-config.yaml` → Pensieve services → Database connection

### Root Cause Documentation Template

When fixing bugs, document in PR/commit message:

```markdown
## Root Cause Analysis

**Symptom**: [What user sees]
**Root Cause**: [First divergence point]
**Arrow Chain**:
```
[step by step data flow]
```
**Fix**: [What was changed and why]
**Test**: [How to verify fix works]
```

---

## 🎯 MANDATORY PROMPT IMPROVEMENT PROTOCOL

**🚨 CRITICAL: Claude MUST ALWAYS start responses by improving the user prompt using CRAFT framework. This is NON-NEGOTIABLE. 🚨**

### REQUIRED Response Format:
```
**Improved Prompt**: [Enhanced version using CRAFT framework]

**Implementation Plan**:
1. [Specific step]
2. [Specific step]
3. [Specific step]

[Then proceed with actual work]
```

### CRAFT Framework (MUST USE):
- **C**ontext & Constraints: Add missing technical context, deadlines, audience
- **R**ole & Audience: Define perspective ("You are a RoleName working on AutoTaskTracker...")  
- **A**sk: Break compound tasks into numbered steps, request step-by-step reasoning
- **F**ormat: Specify output format (Markdown, JSON, code blocks, bullet lists)
- **T**one & Temperature: Set voice (technical, concise) and length constraints

### Prompt Enhancement Rules (MANDATORY):
1. **Anchor in clarity**: Transform vague requests ("fix this") into specific goals
2. **Structure for reasoning**: Break multi-step tasks into numbered steps with explicit reasoning requests
3. **Add AutoTaskTracker context**: Include file paths, dependencies, coding standards
4. **Specify constraints**: Add technical context (Pensieve integration, DatabaseManager usage)
5. **Define success criteria**: What constitutes completion of the task

### Example Transformation:
```
❌ User: "Fix the database connection"
✅ Improved: "You are a RoleName working on AutoTaskTracker. Fix DatabaseManager connection errors in autotasktracker/core/database.py by:
1. Analyzing current connection code and error logs
2. Checking PostgreSQL configuration (localhost:5433/autotasktracker)
3. Testing connection with proper error handling
4. Ensuring compatibility with Pensieve integration
Output: Code changes in diff format + explanation of fixes"
```

### ENFORCEMENT CHECKLIST:
- [ ] Every response starts with "**Improved Prompt**:"
- [ ] CRAFT framework applied to user request
- [ ] AutoTaskTracker-specific context added
- [ ] Multi-step tasks broken down with TodoWrite
- [ ] Success criteria defined
- [ ] Technical constraints specified

**VIOLATION CONSEQUENCES**: Any response that doesn't start with prompt improvement will be considered non-compliant with project standards.

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

### 🚨 CONFIGURATION - NO CONFUSION RULE

**ENVIRONMENT-BASED SOLUTION IMPLEMENTED**: AutoTaskTracker uses dedicated config via MEMOS_CONFIG_PATH environment variable.

**Configuration Setup:**
- AutoTaskTracker config: `/Users/paulrohde/AutoTaskTracker.memos/autotask-config.yaml`
- Environment variable: `MEMOS_CONFIG_PATH` points to AutoTaskTracker config
- Complete independence from shared `~/.memos/config.yaml` file
- No conflicts with AITaskTracker configuration

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
**AutoTaskTracker Ports (8600-8699 range):**
- Memos: 8839 (Pensieve default)
- Memos Web: 8840 
- Task Board: 8602
- Analytics: 8603
- Time Tracker: 8605
- Notifications: 8606
- Advanced Analytics: 8607
- Overview: 8608
- Focus Tracker: 8609
- Daily Summary: 8610

### Database Issues
- **Path**: PostgreSQL at localhost:5433/autotasktracker
- **Always use DatabaseManager** for connections
- Check permissions if connection fails
- Verify `MEMOS_CONFIG_PATH` environment variable

### Pensieve/Memos Configuration
**Setup/Recovery Commands:**
```bash
# Initial setup or recovery
./scripts/setup_environment_config.sh

# Manual verification
echo $MEMOS_CONFIG_PATH
```

**Python environment:**
```bash
# ✅ CORRECT commands (use venv Python):
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands ps
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands start
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands stop
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

## 🌐 BROWSER AUDIT WORKFLOW

**When requested to "run frontend in browser and audit with screenshot":**

### Required Command Chain (Non-Blocking):

1. **Start Pensieve Backend (Non-Blocking)**:
```bash
# Start Pensieve in background
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands start > /dev/null 2>&1 &
sleep 3  # Allow server startup time
```

2. **Start Dashboard (Non-Blocking)**:
```bash
# Start task board dashboard in background
python autotasktracker.py dashboard > /dev/null 2>&1 &
sleep 5  # Allow Streamlit startup time
```

3. **Verify Services Running**:
```bash
# Check Pensieve backend
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands ps

# Check dashboard (should return HTML)
curl -s http://localhost:8602 | head -1 || echo "Dashboard not ready"
```

4. **Open Browser and Capture**:
```bash
# Open in new Chrome tab (non-blocking)
osascript -e 'tell application "Google Chrome" to open location "http://localhost:8602"'

# Wait for page load, then capture
sleep 3
screencapture -x /tmp/AutoTaskTracker_audit.png
```

### Troubleshooting Common Issues:

**Port Conflicts:**
```bash
# Kill existing processes
lsof -ti:8602 | xargs kill -9 2>/dev/null || true
lsof -ti:8839 | xargs kill -9 2>/dev/null || true
```

**Database Connection:**
```bash
# Check PostgreSQL connection
psql -h localhost -p 5433 -d autotasktracker -c "SELECT COUNT(*) FROM entities;"
```

### Screenshot Analysis Process:

1. **Capture Application Screenshot**: Use non-blocking screenshot commands
2. **Visual Audit Checklist**:
   - ✅ Streamlit interface renders correctly
   - ✅ Task cards display with OCR content
   - ✅ Navigation sidebar functional
   - ✅ Dashboard components load data
   - ✅ Time tracking controls work
   - ✅ Export functionality accessible
   - ✅ No error messages or loading states stuck

3. **Document Findings**: Record specific issues with file references (e.g., `autotasktracker/dashboards/task_board.py:45`)

### Critical Command Patterns:

**✅ CORRECT - Non-Blocking Background Processes:**
```bash
python command > /dev/null 2>&1 &    # Run in background
sleep N                              # Allow startup time
```

**❌ WRONG - Blocking Commands:**
```bash
python autotasktracker.py dashboard  # Blocks terminal indefinitely
streamlit run app.py                 # Blocks until killed
```

**✅ CORRECT - Process Management:**
```bash
# Start with cleanup
lsof -ti:8602 | xargs kill -9 2>/dev/null || true
python autotasktracker.py dashboard > /dev/null 2>&1 &
```

---

END OF INSTRUCTIONS - Now you can work on AutoTaskTracker!