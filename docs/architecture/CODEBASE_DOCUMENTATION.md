# AutoTaskTracker - Comprehensive Codebase Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [AI Features](#ai-features)
5. [Dashboard Components](#dashboard-components)
6. [Database Layer](#database-layer)
7. [Configuration Management](#configuration-management)
8. [Testing Infrastructure](#testing-infrastructure)
9. [Development Workflow](#development-workflow)
10. [API Reference](#api-reference)

## Overview

AutoTaskTracker is an AI-powered application that passively discovers and organizes daily tasks from screenshots. It runs continuously in the background, capturing screen activity and using AI to infer completed tasks without manual logging.

### Key Features
- **Passive Operation**: Runs unobtrusively using the Pensieve backend
- **AI-Powered Analysis**: OCR, embeddings, and optional VLM for task understanding
- **Real-time Dashboards**: Multiple Streamlit interfaces for different use cases
- **Semantic Search**: Find similar tasks using embedding vectors
- **Task Categorization**: Automatic classification of activities
- **Export Capabilities**: CSV, JSON, and text report generation

### Technology Stack
- **Backend**: Python + Pensieve (memos) for screenshot capture and processing
- **Frontend**: Streamlit for web dashboards
- **Database**: SQLite via Pensieve integration
- **AI/ML**: Sentence Transformers, Optional Ollama/VLM integration
- **Image Processing**: PIL, OpenCV for screenshot handling
- **Data Processing**: Pandas, NumPy for analytics

## Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Screenshots   │───▶│    Pensieve     │───▶│ AutoTaskTracker │
│   (Continuous)  │    │   (Processing)  │    │   (Analysis)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  SQLite + OCR   │    │    Streamlit    │
                       │   + Metadata    │    │   Dashboards    │
                       └─────────────────┘    └─────────────────┘
```

### Component Architecture
```
autotasktracker/
├── core/                    # Core business logic
│   ├── database.py         # Database management
│   ├── task_extractor.py   # Task extraction logic
│   ├── categorizer.py      # Activity categorization
│   └── vlm_integration.py  # VLM processing
├── ai/                     # AI enhancement features
│   ├── embeddings_search.py     # Semantic search
│   ├── enhanced_task_extractor.py # AI-powered extraction
│   ├── ocr_enhancement.py       # OCR quality analysis
│   └── vlm_integration.py       # VLM task analysis
├── dashboards/             # Streamlit interfaces
│   ├── task_board.py       # Main task dashboard
│   ├── analytics.py        # Analytics dashboard
│   ├── timetracker.py      # Time tracking
│   └── notifications.py    # Notification system
└── utils/                  # Utility functions
    └── config.py           # Configuration management
```

## Core Components

### 1. Database Manager (`autotasktracker/core/database.py`)

**Purpose**: Centralized database access and query management for Pensieve SQLite database.

**Key Features**:
- Connection pooling and context management
- Read-only connection support for safety
- Comprehensive query methods for tasks, activities, and metadata
- AI coverage statistics
- Time-based filtering and pagination

**Key Methods**:
```python
class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None)
    def get_connection(self, readonly: bool = True) -> sqlite3.Connection
    def fetch_tasks(self, start_date, end_date, limit, offset) -> pd.DataFrame
    def fetch_tasks_by_time_filter(self, time_filter: str) -> pd.DataFrame
    def get_screenshot_count(self, date: datetime) -> int
    def get_ai_coverage_stats(self) -> Dict[str, Any]
    def search_activities(self, search_term: str) -> pd.DataFrame
```

**Database Schema Integration**:
- `entities` table: Screenshot files and metadata
- `metadata_entries` table: OCR results, window data, AI outputs
- Joins data from multiple tables for comprehensive task views

### 2. Task Extractor (`autotasktracker/core/task_extractor.py`)

**Purpose**: Advanced task extraction with application-specific patterns and intelligent parsing.

**Key Features**:
- Application-specific extraction patterns for 50+ applications
- File extension recognition and programming language detection
- Terminal command parsing and Git operation detection
- Website and localhost development recognition
- Subtask extraction from OCR data

**Application Patterns**:
```python
# Examples of supported applications
'vscode': {'pattern': r'(.*?)\s*[—–\-]\s*(.*?)\s*[—–\-]\s*Visual Studio Code'},
'chrome': {'pattern': r'(.*?)\s*[—–-]\s*(?:Google\s*)?Chrome'},
'slack': {'pattern': r'(.*?)\s*[—–-]\s*(.*?)\s*[—–-]\s*Slack'},
'github': Custom GitHub activity detection (PRs, issues, commits)
```

**Advanced Features**:
- Project name cleaning and file extension handling
- Terminal command categorization (git, npm, pip, etc.)
- Localhost port mapping for development environments
- OCR-based subtask extraction with confidence scoring

### 3. Activity Categorizer (`autotasktracker/core/categorizer.py`)

**Purpose**: Intelligent categorization of activities based on window titles and content.

**Categories**:
- 🧑‍💻 Coding (IDEs, terminals, localhost, code files)
- 💬 Communication (Slack, email, messaging)
- 🔍 Research/Browsing (browsers, documentation)
- 📝 Documentation (text editors, wikis)
- 🎥 Meetings (Zoom, Teams, video calls)
- 🎨 Design (Figma, Photoshop, design tools)
- 📊 Data Analysis (Excel, Tableau, Jupyter)
- 🎮 Entertainment (YouTube, gaming, streaming)
- 🤖 AI Tools (ChatGPT, Claude, Copilot)

**Smart Categorization**:
- Priority-based classification (coding patterns override general patterns)
- Context-aware AI tool categorization
- File extension recognition for precise coding classification

## AI Features

### 1. Embeddings Search Engine (`autotasktracker/ai/embeddings_search.py`)

**Purpose**: Semantic search and task similarity using Jina embeddings.

**Features**:
- Cosine similarity calculation for task relationships
- Semantic search with configurable thresholds
- Task grouping based on embedding similarity
- Context discovery for related work sessions

**Key Methods**:
```python
class EmbeddingsSearchEngine:
    def semantic_search(self, query_entity_id, limit, similarity_threshold) -> List[Dict]
    def find_similar_task_groups(self, min_group_size, similarity_threshold) -> List[List[Dict]]
    def get_task_context(self, entity_id, context_size) -> List[Dict]
    def cosine_similarity(self, embedding1, embedding2) -> float
```

**Technical Details**:
- Uses 768-dimensional Jina embeddings from Pensieve
- Configurable similarity thresholds (default 0.7)
- Time-window filtering for relevant context
- Numpy-based efficient similarity calculations

### 2. AI Enhanced Task Extractor (`autotasktracker/ai/enhanced_task_extractor.py`)

**Purpose**: Combines all AI features for superior task detection and analysis.

**Integration Points**:
- Base task extraction + OCR enhancement + VLM analysis
- Embedding-based similarity detection
- Confidence scoring across multiple AI systems
- Task insights and context discovery

**Enhanced Output**:
```python
{
    'task': 'Enhanced task description',
    'category': '🧑‍💻 Coding',
    'confidence': 0.85,
    'ai_features': {
        'ocr_quality': 'excellent',
        'vlm_available': True,
        'embeddings_available': True
    },
    'similar_tasks': [...],
    'ui_state': {...},
    'visual_context': {...}
}
```

### 3. AI CLI (`ai_cli.py`)

**Purpose**: Command-line interface for AI feature management.

**Commands**:
- `status`: Check AI feature availability and coverage
- `setup`: One-command AI setup with dependency installation
- `embeddings`: Generate embeddings for screenshots
- `enable-vlm`/`disable-vlm`: VLM configuration management

**Features**:
- Dependency checking (Sentence Transformers, Ollama)
- Model availability verification (minicpm-v)
- Configuration file management
- Progress reporting and error handling

## Dashboard Components

### 1. Task Board (`autotasktracker/dashboards/task_board.py`)

**Purpose**: Main dashboard for task visualization and management.

**Features**:
- Real-time task display with time filtering
- Screenshot thumbnails with zoom capability
- Intelligent task grouping by time and context
- AI-enhanced task extraction and similarity display
- Export functionality (CSV, JSON, text reports)
- Category filtering and search

**Smart Grouping Algorithm**:
- Groups tasks within configurable time intervals
- Considers category similarity and project context
- Uses shared keywords for intelligent grouping
- Maintains chronological order within groups

### 2. Analytics Dashboard (`autotasktracker/dashboards/analytics.py`)

**Purpose**: Productivity metrics and insights visualization.

**Analytics Features**:
- Activity distribution by hour/day/category
- Focus session detection (continuous work > 30 min)
- Application usage patterns
- Productivity trends and streaks
- Interactive charts with Plotly

**Metrics Calculated**:
```python
{
    'total_hours': float,
    'total_activities': int,
    'avg_activities_per_hour': float,
    'category_distribution': dict,
    'focus_sessions': int,
    'avg_focus_duration': float,
    'longest_focus': float
}
```

### 3. Additional Dashboards

- **Time Tracker**: Detailed time-based analysis and session tracking
- **Notifications**: Alert system for productivity insights
- **Achievement Board**: Gamification and progress tracking

## Database Layer

### Schema Overview
AutoTaskTracker integrates with Pensieve's SQLite database structure:

```sql
-- Core entities (screenshots)
entities (
    id INTEGER PRIMARY KEY,
    filepath TEXT,
    filename TEXT,
    created_at TIMESTAMP,
    file_type_group TEXT -- 'image' for screenshots
)

-- Metadata and AI results
metadata_entries (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    key TEXT, -- 'ocr_result', 'active_window', 'vlm_result', 'embedding'
    value TEXT -- JSON or text data
)
```

### Query Patterns
```sql
-- Typical task fetch with metadata
SELECT 
    e.id, e.filepath, e.created_at,
    me_ocr.value as ocr_text,
    me_window.value as active_window,
    me_vlm.value as vlm_description
FROM entities e
LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr.key = 'ocr_result'
LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id AND me_window.key = 'active_window'
LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm.key = 'vlm_result'
WHERE e.file_type_group = 'image'
ORDER BY e.created_at DESC
```

## Configuration Management

### Config System (`autotasktracker/utils/config.py`)
Centralized configuration using dataclasses and environment variables:

```python
@dataclass
class Config:
    # Database
    DB_PATH: str = "~/.memos/database.db"
    
    # Dashboard ports
    TASK_BOARD_PORT: int = 8502
    ANALYTICS_PORT: int = 8503
    TIMETRACKER_PORT: int = 8504
    
    # UI settings
    SHOW_SCREENSHOTS: bool = True
    GROUP_INTERVAL_MINUTES: int = 5
    
    # AI features
    ENABLE_AI_FEATURES: bool = True
    EMBEDDING_MODEL: str = "jinaai/jina-embeddings-v2-base-en"
```

### Environment Variables
- `AUTOTASK_DB_PATH`: Override database path
- `AUTOTASK_SHOW_SCREENSHOTS`: Control screenshot display
- `AUTOTASK_AI_FEATURES`: Enable/disable AI features

## Testing Infrastructure

### Test Organization
```
tests/
├── test_critical.py      # Core functionality tests
├── test_smoke.py         # Quick smoke tests
├── test_codebase_health.py # Code quality checks
├── e2e/
│   ├── test_full_journey.py # End-to-end workflows
│   └── test_headless_integration.py # Headless testing
└── assets/
    └── sample_screenshot.png # Test data
```

### Test Categories
1. **Critical Tests**: Database, task extraction, categorization
2. **Smoke Tests**: Basic functionality and imports
3. **E2E Tests**: Full user workflows with Playwright
4. **Codebase Health**: Import validation, file structure

### Running Tests
```bash
# All tests
python -m pytest tests/

# Specific test suites
python -m pytest tests/test_critical.py
python -m pytest tests/e2e/
```

## Development Workflow

### Entry Points
1. **Main CLI** (`autotasktracker.py`): Service management and dashboard launching
2. **AI CLI** (`ai_cli.py`): AI feature management
3. **Individual Dashboards**: Direct Streamlit execution

### Common Commands
```bash
# Start all services
python autotasktracker.py start

# Launch specific dashboards
python autotasktracker.py dashboard
python autotasktracker.py analytics

# AI management
python ai_cli.py status
python ai_cli.py setup
python ai_cli.py embeddings

# Check status
python autotasktracker.py status
```

### Development Setup
```bash
# Initialize Pensieve
memos init
memos enable
memos start

# Setup AI features
python ai_cli.py setup

# Run tests
python -m pytest tests/
```

## API Reference

### Core Classes

#### DatabaseManager
- **Purpose**: Database operations and query management
- **Location**: `autotasktracker.core.database`
- **Key Methods**: `fetch_tasks()`, `get_ai_coverage_stats()`, `search_activities()`

#### TaskExtractor  
- **Purpose**: Task description extraction from window data
- **Location**: `autotasktracker.core.task_extractor`
- **Key Methods**: `extract_task()`, `extract_subtasks_from_ocr()`

#### ActivityCategorizer
- **Purpose**: Activity classification and categorization
- **Location**: `autotasktracker.core.categorizer`
- **Key Methods**: `categorize()`, `get_all_categories()`

#### EmbeddingsSearchEngine
- **Purpose**: Semantic search and task similarity
- **Location**: `autotasktracker.ai.embeddings_search`
- **Key Methods**: `semantic_search()`, `find_similar_task_groups()`

#### AIEnhancedTaskExtractor
- **Purpose**: Combined AI-powered task analysis
- **Location**: `autotasktracker.ai.enhanced_task_extractor`
- **Key Methods**: `extract_enhanced_task()`, `get_task_insights()`

### Utility Functions

#### Configuration
```python
from autotasktracker import get_config
config = get_config()  # Returns Config instance
```

#### Database Access
```python
from autotasktracker import get_default_db_manager
db = get_default_db_manager()  # Returns DatabaseManager instance
```

#### Task Processing
```python
from autotasktracker import extract_task_summary, categorize_activity
task = extract_task_summary(ocr_text, window_data)
category = categorize_activity(window_title, ocr_text)
```

## Performance Considerations

### Optimization Features
- **Database Connection Pooling**: Reuses connections for efficiency
- **Caching**: Streamlit `@st.cache_data` for expensive operations
- **Pagination**: Limits query results to prevent memory issues
- **Lazy Loading**: AI features loaded only when needed

### Resource Management
- **Screenshot Storage**: ~400MB/day, configurable retention
- **Memory Usage**: Pandas DataFrames cached with TTL
- **CPU Usage**: OCR and embeddings are CPU-intensive
- **GPU Requirements**: VLM features require 8GB+ VRAM

### Scalability
- **Database**: SQLite suitable for single-user, consider PostgreSQL for multi-user
- **Processing**: Batch processing for embedding generation
- **Storage**: Configurable cleanup policies for old screenshots

---

This documentation covers the complete AutoTaskTracker codebase architecture, from core components to AI features and dashboard interfaces. The system is designed for extensibility and maintainability, with clear separation of concerns and comprehensive testing coverage.