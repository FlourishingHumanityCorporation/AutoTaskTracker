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

### Key Techniques for High-Quality Code

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

## 🧬 AGILE AI DEVELOPMENT FRAMEWORK

AutoTaskTracker is an AI-powered system requiring specialized development approaches that blend agile methodology with data science experimentation.

### AI Development Principles

**Hypothesis-Driven Development:** Frame AI work as experiments, not feature deliverables:
```
We believe that <implementing VLM task extraction>
Will result in <20% improvement in task detection accuracy>
We will know we've succeeded when <F1-score > 0.85 on validation set>
```

**Probabilistic Acceptance Criteria:** Define "done" for AI features using statistical thresholds:
- **Quantitative:** "Model achieves precision > 0.80 and recall > 0.85"
- **Performance:** "Response time < 200ms for 95% of requests"
- **Qualitative:** "Task explanations rated as 'clear and helpful' by 4/5 users"

### AI Story Formats

**AI-Adapted User Stories:**
```
As a fraud analyst reviewing transactions,
I want to see a prioritized list of transactions with >75% fraud probability,
so that I can focus investigation time on highest-risk cases.
```

**Data Stories (for infrastructure work):**
```
As a data scientist training task extraction models,
I need access to the last 6 months of cleaned OCR text with validated labels,
so that I can begin model training with sufficient data quality.
```

**Hypothesis Stories (for experimental work):**
```
We believe that adding semantic embeddings to task classification
Will result in improved task categorization accuracy
We will know we've succeeded when category prediction F1-score > 0.90
```

### AI Development Workflow

1. **Research Phase:** Use hypothesis stories to frame experiments
2. **Data Phase:** Write data stories for infrastructure needs
3. **Model Phase:** Define probabilistic acceptance criteria
4. **Integration Phase:** Use AI-adapted user stories for application features
5. **Validation Phase:** Measure against both technical and user experience metrics

### AI-Specific Quality Gates

**Technical Validation:**
- Model performance meets statistical thresholds
- Inference latency within acceptable bounds
- Resource utilization within budget

**User Experience Validation:**
- AI explanations are understandable to target users
- Graceful degradation when AI is unavailable
- Error handling provides meaningful feedback

**Ethical Validation:**
- No discriminatory bias in model predictions
- User consent and data privacy compliance
- Transparency in automated decision-making

### Anti-Patterns to Avoid

**"Solutioneering":** Don't assume AI is the solution - validate the problem first
**"Model-Centric Development":** Focus on user outcomes, not model metrics
**"Perfectionism Trap":** Accept probabilistic outcomes, don't chase 100% accuracy
**"AI-First Fallacy":** Use simple rules where they work better than complex models

### Integration with AutoTaskTracker

**Pensieve-AI Integration:** Always check if Pensieve provides AI capabilities before custom implementation
**Graceful Degradation:** All AI features must work with fallback mechanisms
**Performance Monitoring:** Track both model performance and user experience metrics
**Continuous Learning:** Use production data to improve models over time

---

## 📝 RECENT CHANGES

**2025-07-05: Added Agile AI Development Framework**
- Integrated comprehensive agile AI methodology from best practices guide
- Added hypothesis-driven development approach for AI experiments
- Defined probabilistic acceptance criteria for AI features
- Included ethical requirements and validation gates
- Added AI-adapted user stories, data stories, and hypothesis stories
- Established 5-phase AI development workflow
- Defined anti-patterns to avoid in AI development
- Connected framework to AutoTaskTracker's Pensieve integration

**2025-07-05: Added AI prompt engineering guidelines**
- Added "Effective AI Prompt Engineering" section with 5 key techniques
- Included AutoTaskTracker-specific prompting example
- Emphasized security requirements and context-rich prompts
- Added Chain-of-Thought and Recursive Criticism techniques
- **CRITICAL**: Added mandatory "Prompt Improvement Protocol" requiring Claude to start responses with improved prompts

**2025-07-05: Documentation optimization and modular structure**
- Implemented modular CLAUDE.md structure using @ imports
- Created `docs/architecture/pensieve_integration.md` for detailed integration patterns
- Added `docs/guides/code_style.md` with specific formatting requirements
- Added `/changes` and `/reload` context management commands in `.claude/commands/`
- Reduced main CLAUDE.md from 547 to 294 lines

**2025-07-05: Advanced best practices implementation**
- Implemented hierarchical CLAUDE.md structure for module-specific context
- Added MCP (Multi-Claude Protocol) integration documentation and custom servers
- Created team-shared permissions configuration (`.claude/settings.json`)
- Added GitHub Actions integration for automated workflows (@claude commands)
- Implemented complexity budgeting system with `/complexity-check` command
- Created navigational markers for large files (database.py)
- Added user-level CLAUDE.md template for personal preferences

**2025-07-05: Pensieve integration modules**
- Added webhook client (`autotasktracker/pensieve/webhook_client.py`)
- Added endpoint discovery (`autotasktracker/pensieve/endpoint_discovery.py`) 
- Added migration automation (`autotasktracker/pensieve/migration_automation.py`)
- Added search coordinator (`autotasktracker/pensieve/search_coordinator.py`)
- Added integration health dashboard (`autotasktracker/dashboards/integration_health.py`)
- Added performance optimizer (`autotasktracker/pensieve/performance_optimizer.py`)

**2025-07-05: Meta-testing security implementation**
- Implemented AI-specific Semgrep rules (`.semgrep.yml`) targeting AI-generated code vulnerabilities
- Added package legitimacy validator (`scripts/security/package_validator.py`) for slopsquatting protection
- Configured Bandit (`.bandit`) and Safety (`.safety-policy.json`) with AI-focused security scanning
- Implemented basic DAST capabilities (`scripts/security/dashboard_security_tester.py`) for Streamlit dashboards
- Enhanced CI workflow with comprehensive security tool integration
- Added meta-testing compliance health checks (`tests/health/test_metatesting_security.py`)
- Security tools now include: semgrep, bandit, safety, pip-audit with AI-specific configurations

---

END OF INSTRUCTIONS - Now you can work on AutoTaskTracker!