# 🗺️ AutoTaskTracker Feature Map

## 🎯 Feature-to-File Mapping

This guide shows exactly which files implement which features, making it easy to understand what each component does.

## 📊 Core Features

### **Screenshot Capture & Storage**
- **Implementation**: External (Memos/Pensieve backend)
- **Configuration**: `~/.memos/config.yaml`
- **Data Storage**: `~/.memos/database.db`
- **Files**: Screenshots stored in `~/.memos/screenshots/`

### **Database Management**
- **File**: `autotasktracker/core/database.py`
- **Class**: `DatabaseManager`
- **Purpose**: Connect to and query Memos SQLite database
- **Used by**: All modules that need data access

### **Basic Task Extraction**
- **File**: `autotasktracker/core/task_extractor.py`
- **Class**: `TaskExtractor`
- **Purpose**: Extract task names from window titles using pattern matching
- **Input**: Window title strings
- **Output**: Human-readable task names

### **Activity Categorization**
- **File**: `autotasktracker/core/categorizer.py`
- **Class**: `ActivityCategorizer`
- **Purpose**: Classify activities into categories with emojis
- **Input**: Window title + optional OCR text
- **Output**: Category with emoji (e.g., "🧑‍💻 Coding")

---

## 🤖 AI Enhancement Features

### **OCR Text Enhancement**
- **File**: `autotasktracker/ai/ocr_enhancement.py`
- **Class**: `OCREnhancer`
- **Purpose**: Improve task extraction using OCR text analysis
- **Features**:
  - Confidence scoring based on text quality
  - Layout analysis (headers, buttons, forms)
  - Text region classification
- **Input**: OCR results + basic task
- **Output**: Enhanced task with confidence score

### **Visual Language Model (VLM) Integration**
- **File**: `autotasktracker/ai/vlm_integration.py`
- **Class**: `VLMTaskExtractor`
- **Purpose**: Understand screenshots using visual AI
- **Features**:
  - Scene understanding
  - UI state detection
  - Visual context analysis
- **Requirements**: Ollama with minicpm-v model
- **Input**: VLM description + context
- **Output**: Enhanced task with visual insights

### **Semantic Similarity Search**
- **File**: `autotasktracker/ai/embeddings_search.py`
- **Class**: `EmbeddingsSearchEngine`
- **Purpose**: Find similar tasks using vector embeddings
- **Features**:
  - Vector similarity search
  - Historical pattern matching
  - Semantic task clustering
- **Requirements**: Sentence transformers, Jina embeddings
- **Input**: Text query or entity ID
- **Output**: Similar tasks with similarity scores

### **Complete AI Pipeline**
- **File**: `autotasktracker/ai/enhanced_task_extractor.py`
- **Class**: `AIEnhancedTaskExtractor`
- **Purpose**: Orchestrate all AI features together
- **Features**:
  - Combines OCR, VLM, and semantic search
  - Confidence aggregation
  - Fallback handling
- **Input**: Window title, OCR text, VLM description, entity ID
- **Output**: Best possible task extraction with confidence

---

## 📱 User Interface Features

### **Main Task Dashboard** (Daily Use)
- **File**: `autotasktracker/dashboards/task_board.py`
- **URL**: http://localhost:8502
- **Purpose**: Primary interface for viewing discovered tasks
- **Features**:
  - Today's task timeline
  - Screenshot gallery with detected tasks
  - Task filtering and search
  - Category-based organization
  - Real-time updates

### **Analytics Dashboard** (Insights)
- **File**: `autotasktracker/dashboards/analytics.py`
- **URL**: http://localhost:8503
- **Purpose**: Productivity analysis and trends
- **Features**:
  - Time spent per activity
  - Category distribution charts
  - Productivity trends over time
  - Weekly/monthly summaries
  - Export capabilities

### **Achievement Dashboard** (Gamification)
- **File**: `autotasktracker/dashboards/achievement_board.py`
- **URL**: http://localhost:8507
- **Purpose**: Goals, achievements, and motivation
- **Features**:
  - Productivity goals tracking
  - Achievement badges
  - Progress visualization
  - Streaks and milestones

### **Time Tracker Dashboard** (Detailed Time Tracking)
- **File**: `autotasktracker/dashboards/timetracker.py`
- **URL**: http://localhost:8505 (typical)
- **Purpose**: Comprehensive time tracking and session analysis
- **Features**:
  - Detailed time tracking by task
  - Timeline visualization
  - Time distribution charts
  - Session tracking and analysis
  - CSV export functionality
  - Intelligent task recognition
  - Application-based grouping

### **Desktop Notifications** (Productivity Insights)
- **File**: `autotasktracker/dashboards/notifications.py`
- **Purpose**: Periodic desktop notifications for productivity insights
- **Features**:
  - Hourly productivity updates
  - Focus time tracking
  - Activity summaries
  - Cross-platform notifications (via plyer)
- **Usage**: `python autotasktracker/dashboards/notifications.py`
- **Requirements**: `pip install plyer`

---

## ⚖️ AI Evaluation Features

### **Pipeline Comparison Dashboard**
- **File**: `autotasktracker/comparison/dashboards/pipeline_comparison.py`
- **URL**: http://localhost:8512
- **Purpose**: Compare different AI processing methods
- **Features**:
  - Side-by-side pipeline comparison
  - Same screenshot, different methods
  - Confidence score visualization
  - Feature usage breakdown
  - Real-time processing

### **Performance Analysis CLI**
- **File**: `comparison_cli.py`
- **Purpose**: Batch analysis of AI pipeline performance
- **Features**:
  - Process multiple screenshots
  - Generate comparison reports
  - Export detailed results to CSV/JSON
  - Statistical analysis
- **Usage**: `python comparison_cli.py --limit 50 --export results.csv`

### **Individual Pipeline Implementations**
- **Basic**: `autotasktracker/comparison/pipelines/basic.py`
  - Pattern matching only
  - Fast, simple processing
  - 50% fixed confidence
  
- **OCR Enhanced**: `autotasktracker/comparison/pipelines/ocr.py`
  - Adds OCR text analysis
  - Dynamic confidence scoring
  - Layout understanding
  
- **AI Full**: `autotasktracker/comparison/pipelines/ai_full.py`
  - Complete AI pipeline
  - All features combined
  - Highest accuracy potential

### **Analysis Engine**
- **File**: `autotasktracker/comparison/analysis/performance_analyzer.py`
- **Class**: `PerformanceAnalyzer`
- **Purpose**: Analyze and compare pipeline performance
- **Features**:
  - Batch screenshot processing
  - Statistical analysis
  - Confidence comparison
  - Task diversity metrics

---

## 🛠️ Utility Features

### **Main Entry Point CLI**
- **File**: `autotasktracker.py`
- **Purpose**: Unified command-line interface for managing AutoTaskTracker
- **Usage**: 
  ```bash
  python autotasktracker.py start            # Start all services
  python autotasktracker.py dashboard        # Launch task board
  python autotasktracker.py analytics        # Launch analytics dashboard
  python autotasktracker.py timetracker      # Launch time tracker
  python autotasktracker.py notifications    # Start notification service
  python autotasktracker.py stop            # Stop all services
  python autotasktracker.py status          # Check service status
  ```
- **Features**:
  - Service management (start/stop)
  - Dashboard launching
  - Headless mode support (`--headless`)
  - Status checking

### **Embedding Generation**
- **File**: `scripts/generate_embeddings.py`
- **Purpose**: Generate embeddings for existing screenshots
- **Usage**: `python scripts/generate_embeddings.py --limit 100`
- **Output**: Vector embeddings stored in database

### **AI Feature Management**
- **File**: `scripts/ai_cli.py`
- **Purpose**: Manage AI features (enable/disable VLM, etc.)
- **Usage**: `python scripts/ai_cli.py enable-vlm`
- **Features**:
  - Check AI status
  - Enable/disable VLM
  - Setup AI dependencies

### **Database Debugging**
- **File**: `scripts/test_data.py`
- **Purpose**: Debug and inspect database contents
- **Usage**: `python scripts/test_data.py`
- **Features**:
  - View recent screenshots
  - Check database connectivity
  - Inspect metadata entries

### **Configuration Management**
- **File**: `autotasktracker/utils/config.py`
- **Purpose**: Handle application configuration
- **Features**:
  - Load settings from files
  - Environment variable support
  - Default value handling

---

## 🔄 Feature Interaction Map

```
Screenshot Capture (Memos)
         ↓
Database Storage (database.py)
         ↓
Basic Processing (task_extractor.py + categorizer.py)
         ↓
AI Enhancement (ai/*.py) [OPTIONAL]
         ↓
Dashboard Display (dashboards/*.py)
         ↓
User Interaction
```

### **AI Enhancement Chain**:
```
Basic Task → OCR Enhancement → VLM Enhancement → Semantic Search → Final Result
```

### **Dashboard Data Flow**:
```
Database → Data Loading → Processing → Visualization → User Interface
```

## 📋 Feature Status

### **✅ Fully Implemented**
- Screenshot capture and storage
- Basic task extraction
- Activity categorization
- Main task dashboard
- Analytics dashboard
- OCR enhancement
- Pipeline comparison tools
- Performance analysis

### **🔄 Partially Implemented**
- VLM integration (requires model download)
- Semantic similarity search (requires embeddings)
- Achievement system (basic implementation)

### **🎯 Enhancement Opportunities**
- Automated task pattern learning
- Custom category definitions
- Advanced time tracking
- Integration with external task managers
- Mobile interface

## 🎯 Quick Feature Lookup

| **Want to...** | **Use this file...** | **Run this...** |
|----------------|----------------------|-----------------|
| View daily tasks | `dashboards/task_board.py` | `streamlit run autotasktracker/dashboards/task_board.py` |
| Analyze productivity | `dashboards/analytics.py` | `streamlit run autotasktracker/dashboards/analytics.py` |
| Compare AI methods | `comparison/dashboards/pipeline_comparison.py` | `streamlit run autotasktracker/comparison/dashboards/pipeline_comparison.py` |
| Extract basic tasks | `core/task_extractor.py` | `TaskExtractor().extract_task(window_title)` |
| Enhance with AI | `ai/enhanced_task_extractor.py` | `AIEnhancedTaskExtractor().extract_enhanced_task(...)` |
| Generate embeddings | `scripts/generate_embeddings.py` | `python scripts/generate_embeddings.py` |
| Manage AI features | `scripts/ai_cli.py` | `python scripts/ai_cli.py status` |
| Batch analysis | `comparison_cli.py` | `python comparison_cli.py --limit 50` |

This feature map provides a clear understanding of what each file does and how features relate to each other in the AutoTaskTracker ecosystem.