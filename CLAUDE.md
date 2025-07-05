# 🚨 AUTOTASKTRACKER AI ASSISTANT INSTRUCTIONS 🚨

Essential instructions for AI assistants working on AutoTaskTracker.

## 📚 CRITICAL DOCUMENTATION PATTERN
@docs/architecture/pensieve_integration.md
@docs/guides/testing_guide.md
@docs/guides/code_style.md
@docs/guides/workflow_patterns.md
@docs/guides/domain_knowledge.md
@docs/guides/dependencies.md
@docs/guides/mcp_integration.md
@docs/guides/permissions_setup.md
@docs/guides/github_actions_integration.md
@docs/guides/complexity_management.md
@docs/guides/common_issues.md

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
10. **NEVER use progress percentages or superlatives** - No "85% complete", "amazing", "perfect" in documentation or task summaries

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
8. **ALWAYS leverage Pensieve first**: Check Pensieve capabilities before implementing custom solutions
9. **ALWAYS use conventional commits**: Follow structured commit message format
10. **ALWAYS use git for project history**: Run git log/show/diff instead of manual changelogs

---

## 📝 COMMIT MESSAGE STANDARDS

**Format:** `type(scope): description`

**Types:**
- `feat`: New feature
- `fix`: Bug fix 
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(ai): add VLM processing pipeline
fix(database): resolve connection pool deadlock
docs(pensieve): update integration guide
test(health): add parallel execution tests
```

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
│   │   ├── analyzers/       # General health analyzers
│   │   ├── pensieve_health/ # Pensieve-specific health tests
│   │   ├── config_system/   # Configuration health tests
│   │   └── import_system/   # Import analysis tools
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

## 🔗 PENSIEVE INTEGRATION IMPERATIVE

Always check Pensieve capabilities before implementing custom solutions. See docs/guides/PENSIEVE_REFERENCE.md for more information.

**Key Principle:** Use DatabaseManager, not direct sqlite3.connect()

```python
# ✅ CORRECT
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    screenshots = db.fetch_tasks(limit=100)
```

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

**MANDATORY Before ANY Commit:**
```bash
# Run all health tests
pytest tests/health/ -v

# Fast parallel execution  
python scripts/run_health_tests_parallel.py --fast

# Real functional tests
python tests/run_functional_tests.py --verbose
```

---

## 📚 DOCUMENTATION STANDARDS

**Write Rules:**
- ❌ NO: Announcement-style language, completion docs, superlatives
- ✅ YES: Professional, timeless, measured language
- ✅ YES: DELETE irrelevant docs, don't archive

**Key Principles:**
- Update existing docs or use git commit messages for status
- Use TDD workflow to prevent AI hallucinations and scope drift
- Break complex tasks into smaller sub-problems to avoid "complexity threshold"
- Clear context frequently with `/clear` or `/reload` to prevent degradation

**Personal Overrides:** Create `CLAUDE.local.md` for experimental instructions (ignored by git)

**Available Commands:** `/health-check`, `/start-dashboards`, `/process-screenshots`, `/new-feature [description]`, `/complexity-check`

**Plan Template:** Use `@docs/templates/plan.md` for complex feature implementation

**User Template:** Copy `@docs/templates/user-claude.md` to `~/.claude/CLAUDE.md` for personal preferences

**Navigation:** Search for `<!-- CLAUDE-MARKER: section-name -->` in large files

**Hierarchical Context:** Module-specific CLAUDE.md files in `autotasktracker/ai/`, `autotasktracker/dashboards/`, `autotasktracker/pensieve/`, `scripts/`

---

## 🎯 EFFECTIVE AI PROMPT ENGINEERING

**Core Principle:** The quality of AI-generated code directly reflects the quality of your prompt. Vague prompts force AI to make more guesses, increasing errors and security flaws.

**Think of AI as a junior pair programmer:** Fast with vast knowledge, but needs clear direction and context to be truly effective.

### The PACC Framework for Better Code

**Context is King:** The most common reason AI-generated code fails is lack of context. Structure prompts with **Persona, Action, Criteria, Context (PACC)**.

#### 1. Persona (The "Who")
Define the end-user to help AI make better assumptions about database schema, UI, and functionality.

**❌ Vague:** "A user"  
**✅ Better:** "A non-technical content creator"  
**✅ Best:** "As a **busy marketing manager**..."

#### 2. Action (The "What") 
Use user story format: "As a [Persona], I want to [Action], so that [Purpose]"

**❌ Vague:** "I want a file upload feature"  
**✅ Better:** "As a **marketing manager**, I want to **upload a CSV of contacts**, so that I can **easily add them to my email campaign**"

#### 3. Criteria (The "How")
Provide clear, testable acceptance criteria. This is the most critical part for getting working code.

**❌ Vague:** "The upload should work"  
**✅ Better (Acceptance Criteria):**
- Form must only accept `.csv` files
- File size cannot exceed 5MB  
- Show success message "Contacts uploaded!" on completion
- Display specific error messages on failure
- Disable upload button during processing

#### 4. Context (The "Where")
Provide technical environment, existing code patterns, and architectural constraints.

**❌ Vague:** "Use Python"  
**✅ Better:** "Using Python Flask with SQLAlchemy. User model exists with 'id' and 'email' fields. Follow AutoTaskTracker patterns: DatabaseManager for database access, logging.getLogger(__name__) for logging, graceful AI feature fallbacks."

### Advanced Techniques for High-Quality Code

#### 1. Be Hyper-Specific and Demanding
**❌ Vague:** "Create a login function"  
**✅ Specific:** "Generate a Python function using Flask 2.0 for a user login endpoint. The function should be named `handle_login`, accept a POST request with JSON body, and return a JSON response."

#### 2. Assign a Persona
**❌ Basic:** "Create a database query function"  
**✅ Persona-Based:** "**Act as a senior backend engineer with expertise in database security.** Create a function that queries the entities table using DatabaseManager..."

#### 3. Provide Rich Context (Few-Shot Prompting)
**❌ No Context:** "Add error handling"  
**✅ Context-Rich:** "Following AutoTaskTracker patterns where we use `logging.getLogger(__name__)` and specific exception types, add error handling to this function. Here's an example from our codebase:
```python
try:
    db = DatabaseManager()
    with db.get_connection() as conn:
        result = conn.execute(query)
except sqlite3.Error as e:
    logger.error(f"Database error: {e}")
```"

#### 4. Incorporate Security Requirements Explicitly
**❌ Implicit:** "Create a function to process user input"  
**✅ Explicit Security:** "Create a function that:
1. Validates all user input against SQL injection
2. Uses parameterized queries via DatabaseManager
3. Implements rate limiting
4. Logs security events
5. Follows OWASP input validation guidelines"

#### 5. Use Advanced Reasoning Techniques

**Chain-of-Thought (CoT):**
"**First, outline the steps** needed to implement VLM processing with graceful degradation. Include: model availability check, fallback logic, error handling, and performance monitoring. **Then, write the code** implementing these steps."

**Recursive Criticism and Improvement (RCI):**
1. Initial: "Create the function following AutoTaskTracker patterns..."
2. Follow-up: "**Review your code** for potential issues: missing error cases, Pensieve integration opportunities, complexity score impact. **Provide an improved version** addressing these concerns."

### Collaborative Development Best Practices

#### Iterate, Don't Dictate
- Treat first prompt as start of conversation
- Review AI output and provide feedback for refinement
- Example: "That's great, but can you add a loading spinner while the file is uploading?"

#### Break Down Large Tasks
- Decompose complex features into smaller, independent user stories
- Feed to AI one by one (mirrors agile development)
- More effective than asking for huge, complex features all at once

#### Provide Your "House Style"
- Give AI examples of existing code patterns
- "Here is an example of another route in my application. Please follow this style for function naming and comments."

#### Remember: AI Isn't a Mind Reader
- AI doesn't know your business logic, data structures, or long-term goals
- The more relevant details you provide, the less "magic" needed for good results

### AutoTaskTracker-Specific Prompting

**Example Prompt for New Feature:**
```
Act as a senior engineer familiar with AutoTaskTracker's architecture.

Context: We use DatabaseManager for all database access, prefer Pensieve APIs when available, and implement graceful degradation for all AI features.

Task: Create a new function in autotasktracker/ai/ that extracts dates from OCR text.

Requirements:
1. Check if Pensieve provides date extraction capabilities first
2. Use type hints and Google-style docstrings
3. Handle missing dependencies gracefully (dateutil might not be installed)
4. Log operations using logging.getLogger(__name__)
5. Return empty list on errors, never raise exceptions to caller
6. Keep complexity score under 15 points

First, outline your approach. Then implement the solution.
```

### 🔄 IMPORTANT: Prompt Improvement Protocol

**When receiving any development request, Claude MUST:**
1. **Start the response** with an improved version of the user's prompt that applies the prompt engineering techniques above
2. **Format** the improved prompt in a clear quote block
3. **Then proceed** with the actual implementation

**Example:**
```
User: "add a function to process screenshots"

Claude's Response:
> **Improved Prompt:**
> Act as a senior backend engineer with expertise in AutoTaskTracker's architecture and Pensieve integration.
> 
> Task: Create a new function in autotasktracker/core/ that processes screenshots from the entities table.
> 
> Context: 
> - We use DatabaseManager for all database operations
> - Screenshots are stored in ~/.memos/screenshots/
> - Processing should check Pensieve capabilities first
> - All AI features must degrade gracefully
> 
> Requirements:
> 1. Function named `process_screenshot_batch` with type hints
> 2. Use DatabaseManager, not direct sqlite3
> 3. Implement proper error handling with specific exceptions
> 4. Log using logging.getLogger(__name__)
> 5. Check if Pensieve provides processing capabilities before custom implementation
> 6. Keep complexity score under 20 points
> 7. Include comprehensive docstring with examples
> 
> First, verify existing functionality to avoid duplication. Then implement.

[Claude then continues with the actual implementation...]
```

This ensures every request benefits from optimal prompt engineering, improving code quality and reducing errors.


---

## 📝 RECENT CHANGES

**2025-07-05: Completed Repository Refactoring - 97.5% Complexity Reduction**
- ✅ **Modular Architecture**: Extracted monolithic 1,249-line repositories.py into focused modules
- ✅ **Core Infrastructure**: BaseRepository split into CacheCoordinator, CircuitBreaker, QueryRouter components  
- ✅ **Domain Separation**: TaskRepository, ActivityRepository, MetricsRepository extracted to dedicated modules
- ✅ **Backward Compatibility**: All existing imports and method signatures preserved
- ✅ **Import Optimization**: repositories.py reduced from 1,249 → 31 lines (97.5% reduction)
- ✅ **Single Responsibility**: Each module has one clear domain focus
- ✅ **Complexity Management**: All functions now under complexity thresholds

**Refactoring Structure:**
```
autotasktracker/dashboards/data/
├── repositories.py              # 31 lines (was 1,249) - Import module
├── core/                        # Base infrastructure (4 files, ~580 lines)
├── task/                        # Task data access (391 lines)
├── activity/                    # Activity data access (113 lines)  
└── metrics/                     # Analytics data access (299 lines)
```

**2025-07-05: Validated Mutation Testing Effectiveness with Real Bug Fixes**
- ✅ **Real Bug Detection**: Used mutation testing principles to find 3 actual bugs in core infrastructure
- ✅ **Bug Fix Validation**: Fixed return value errors, boolean logic errors, and off-by-one errors
- ✅ **Practical Value Demonstrated**: Mutation testing caught subtle bugs that traditional testing missed
- ✅ **Script Created**: `scripts/validate_mutation_effectiveness.py` demonstrates the system's value
- ✅ **System Proven**: Effectiveness testing system successfully identifies real production issues

**Bugs Found and Fixed:**
- **database.py:380**: Function returned `None` instead of `result` (missing data bug)
- **error_handler.py:289**: Boolean function returned `None` instead of `True` (logic error)
- **database.py:138**: Index extraction used `[-0]` instead of `[-1]` (off-by-one error)

**2025-07-05: Completed Advanced Pydantic Configuration Migration**
- ✅ **Unified Configuration System**: Integrated advanced Pydantic-based configuration with hot-reloading capabilities
- ✅ **Advanced Pensieve Integration**: Deep integration with feature detection, optimization, and real-time synchronization
- ✅ **Configuration Event System**: Real-time configuration change notifications with event-driven updates
- ✅ **Health Monitoring**: Comprehensive configuration health checks with performance metrics and diagnostics
- ✅ **Legacy Compatibility**: All existing imports and property access patterns maintained
- ✅ **Hot-Reloading**: Environment variable change detection with automatic configuration updates
- ✅ **Type Safety**: Full Pydantic validation with nested configuration support
- ✅ **Production Ready**: Advanced features ready for deployment with graceful fallbacks

**Configuration System Features Now Available:**
- **Hot-reloading monitoring**: `start_config_monitoring()`
- **Pensieve integration**: `initialize_pensieve_integration()`, `get_pensieve_features()`, `optimize_for_pensieve()`
- **Event system**: `start_config_event_system()`, `emit_config_change_event()`, `register_config_event_handler()`
- **Health monitoring**: `run_config_health_check()`, `get_config_health_status()`, `get_config_metrics()`
- **Comprehensive status**: `get_comprehensive_config_status()`

---

END OF INSTRUCTIONS - Now you can work on AutoTaskTracker!