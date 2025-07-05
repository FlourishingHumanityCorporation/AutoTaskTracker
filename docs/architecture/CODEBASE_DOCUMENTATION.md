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
- **Database**: SQLite/PostgreSQL/pgvector via Pensieve integration
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
Main modules: core/ (business logic), ai/ (AI features), dashboards/ (Streamlit interfaces), and utils/ (utilities).

## Core Components

### 1. Database Manager (`autotasktracker/core/database.py`)

**Purpose**: Centralized database access and query management for Pensieve database (SQLite/PostgreSQL/pgvector).

**Key Features**:
- Connection pooling and context management
- Read-only connection support for safety
- Comprehensive query methods for tasks, activities, and metadata
- AI coverage statistics
- Time-based filtering and pagination

**Key Methods**: Connection management, task retrieval, AI coverage analysis, and search functionality. See `autotasktracker/core/database.py` for complete API.

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

**Application Patterns**: Supports 50+ applications including VS Code, Chrome, Slack, GitHub, and more. See `autotasktracker/core/task_extractor.py` for complete pattern definitions.

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

**Key Methods**: Semantic search, task grouping, context discovery, and similarity calculations. See `autotasktracker/ai/embeddings_search.py` for complete API.

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

**Enhanced Output**: Structured task data with confidence scores, AI feature indicators, and related task information. See `autotasktracker/ai/enhanced_task_extractor.py` for complete schema.

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

**Metrics Calculated**: Hours worked, activity counts, category distribution, focus sessions, and productivity trends. See `autotasktracker/dashboards/analytics.py` for complete metrics.

### 3. Additional Dashboards

- **Time Tracker**: Detailed time-based analysis and session tracking
- **Notifications**: Alert system for productivity insights
- **Achievement Board**: Gamification and progress tracking

## Database Layer

### Schema Overview
AutoTaskTracker integrates with Pensieve's SQLite database structure:

**Core Tables**: `entities` (screenshots) and `metadata_entries` (OCR, AI results). See Pensieve documentation for complete schema.

### Query Patterns
Standard queries join `entities` with `metadata_entries` to combine screenshot metadata with OCR and AI results. See `autotasktracker/core/database.py` for optimized query implementations.

## Configuration Management

### Config System (`autotasktracker/utils/config.py`)
Centralized configuration using dataclasses and environment variables:

**Configuration**: Database paths, dashboard ports, UI settings, and AI feature flags. See `autotasktracker/utils/config.py` for complete configuration options.

### Environment Variables
- `AUTOTASK_DB_PATH`: Override database path
- `AUTOTASK_SHOW_SCREENSHOTS`: Control screenshot display
- `AUTOTASK_AI_FEATURES`: Enable/disable AI features

## Testing Infrastructure

### Test Organization
Tests are organized into critical tests, smoke tests, and E2E tests in the `tests/` directory.

### Test Categories
1. **Critical Tests**: Database, task extraction, categorization
2. **Smoke Tests**: Basic functionality and imports
3. **E2E Tests**: Full user workflows with Playwright
4. **Codebase Health**: Import validation, file structure

### Running Tests
Use `pytest` to run all tests or specific test suites. See individual test files for detailed test scenarios.

## Development Workflow

### Entry Points
1. **Main CLI** (`autotasktracker.py`): Service management and dashboard launching
2. **AI CLI** (`ai_cli.py`): AI feature management
3. **Individual Dashboards**: Direct Streamlit execution

### Common Commands
Use `autotasktracker.py` for service management and `ai_cli.py` for AI features. See `--help` for complete command reference.

### Development Setup
Initialize Pensieve, setup AI features, and run tests. See `CLAUDE.md` for complete setup instructions.

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

#### Utility Functions
Convenience functions for configuration, database access, and task processing. See `autotasktracker/__init__.py` for complete utility API.

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