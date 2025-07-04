# 📦 AutoTaskTracker Package Structure

This package contains the core AutoTaskTracker application components organized into logical modules.

## 📁 Module Overview

```
autotasktracker/
├── core/          # 🏗️  Foundation components (always needed)
├── ai/            # 🤖  AI enhancement features (optional)
├── dashboards/    # 📊  User interface components
├── comparison/    # ⚖️  AI evaluation tools (development)
└── utils/         # 🛠️  Shared utilities and helpers
```

## 🏗️ Core Module (`autotasktracker/core/`)

**Purpose**: Essential components that form the foundation of AutoTaskTracker.

### Components:
- **`database.py`** → Database connection and management
- **`task_extractor.py`** → Basic task extraction from window titles
- **`categorizer.py`** → Activity categorization logic

### Dependencies:
- SQLite database (via Memos/Pensieve)
- No AI dependencies required

### Usage:
```python
from autotasktracker.core import DatabaseManager, TaskExtractor, ActivityCategorizer
```

### Relationships:
- **Used by**: All other modules depend on core
- **Uses**: Only standard libraries and database

---

## 🤖 AI Module (`autotasktracker/ai/`)

**Purpose**: Enhanced AI processing capabilities that build on core functionality.

### Components:
- **`enhanced_task_extractor.py`** → Orchestrates all AI enhancements
- **`ocr_enhancement.py`** → Text analysis and confidence scoring
- **`vlm_integration.py`** → Visual language model integration
- **`embeddings_search.py`** → Semantic similarity search

### Dependencies:
- `autotasktracker.core` (required)
- Sentence transformers, numpy (for embeddings)
- Ollama (for VLM, optional)

### Usage:
```python
from autotasktracker.ai import AIEnhancedTaskExtractor, OCREnhancer
```

### Relationships:
- **Used by**: Dashboards, comparison tools
- **Uses**: Core module + AI libraries
- **Enhances**: Basic task extraction with AI capabilities

---

## 📊 Dashboards Module (`autotasktracker/dashboards/`)

**Purpose**: User interface components for different use cases.

### Structure:
```
dashboards/
├── task_board.py              # 🎯 Main daily task interface  
├── analytics.py               # 📈 Productivity insights
├── achievement_board.py       # 🏆 Goals and achievements
├── legacy/                    # 📦 Older dashboard versions
│   └── comparison/            # ⚖️ Old comparison tools
└── development/               # 🔬 Experimental interfaces
```

### Component Purposes:
- **`task_board.py`** → Primary user interface (port 8502)
- **`analytics.py`** → Productivity analysis (port 8503)  
- **`achievement_board.py`** → Gamification features (port 8507)

### Dependencies:
- `autotasktracker.core` (required)
- `autotasktracker.ai` (optional, for enhanced features)
- Streamlit, pandas, plotly (for UI)

### Usage:
```bash
streamlit run autotasktracker/dashboards/task_board.py
```

### Relationships:
- **Used by**: End users via web browser
- **Uses**: Core and AI modules for data processing
- **Displays**: Processed task data and insights

---

## ⚖️ Comparison Module (`autotasktracker/comparison/`)

**Purpose**: Tools for evaluating and comparing different AI processing approaches.

### Structure:
```
comparison/
├── pipelines/                 # 🔧 Different processing approaches
│   ├── base.py               # Abstract pipeline interface
│   ├── basic.py              # Basic pattern matching
│   ├── ocr.py                # OCR-enhanced processing
│   └── ai_full.py            # Complete AI pipeline
├── analysis/                  # 📊 Performance evaluation
│   ├── performance_analyzer.py # Main analysis engine
│   └── metrics.py            # Comparison metrics
└── dashboards/                # 🖥️ Comparison interfaces
    └── pipeline_comparison.py # Interactive comparison tool
```

### Component Purposes:
- **`pipelines/`** → Different AI processing implementations
- **`analysis/`** → Tools for measuring and comparing performance
- **`dashboards/`** → Interactive comparison interface

### Dependencies:
- `autotasktracker.core` (required)
- `autotasktracker.ai` (required)
- Scientific libraries (numpy, pandas)

### Usage:
```python
from autotasktracker.comparison import BasicPipeline, PerformanceAnalyzer
```

### Relationships:
- **Used by**: Developers and researchers
- **Uses**: All pipeline implementations for comparison
- **Purpose**: Optimize AI processing approaches

---

## 🛠️ Utils Module (`autotasktracker/utils/`)

**Purpose**: Shared utilities and helper functions used across modules.

### Components:
- **`config.py`** → Configuration management
- **`streamlit_helpers.py`** → Common Streamlit utilities

### Dependencies:
- Minimal (mostly standard library)

### Usage:
```python
from autotasktracker.utils import config, streamlit_helpers
```

### Relationships:
- **Used by**: All other modules
- **Uses**: Standard libraries
- **Provides**: Common functionality and utilities

---

## 🔗 Module Dependency Graph

```
                    Utils
                      ↑
                      │
Core  ←──────────────┼──────────────→  AI
 ↑                   │                   ↑
 │                   │                   │
 │              Dashboards         Comparison
 │                   ↑                   ↑
 └───────────────────┼───────────────────┘
                     │
               User Interfaces
```

## 📋 Import Patterns

### **Production Code** (Core functionality):
```python
from autotasktracker.core import DatabaseManager, TaskExtractor
from autotasktracker.ai import AIEnhancedTaskExtractor  # Optional
```

### **Dashboard Code** (User interfaces):
```python
from autotasktracker.core import DatabaseManager
from autotasktracker.ai import OCREnhancer  # When AI features needed
```

### **Development Code** (AI evaluation):
```python
from autotasktracker.comparison import BasicPipeline, PerformanceAnalyzer
from autotasktracker.comparison.analysis import ComparisonMetrics
```

## 🎯 Module Selection Guide

### **Need basic task tracking?**
→ Use `core` module only

### **Want AI enhancements?** 
→ Add `ai` module

### **Building user interfaces?**
→ Use `dashboards` with `core` + optional `ai`

### **Evaluating AI performance?**
→ Use `comparison` module (includes everything)

### **Need shared utilities?**
→ Use `utils` module

This structure enables clear separation of concerns while maintaining logical relationships between components.