# AutoTaskTracker Architecture Overview

## System Overview

AutoTaskTracker passively discovers and organizes tasks from screenshots using AI processing pipelines and multiple dashboard interfaces.

**Core Design Decision**: Built on Pensieve/memos for screenshot capture because:
- Handles privacy-first local processing (no cloud dependencies)
- Provides robust SQLite integration with proven OCR pipeline
- Enables continuous background operation without user intervention
- Offers extensible metadata architecture for AI enhancement

## Application Flow

1. **Capture**: Memos captures screenshots automatically (4-second intervals)
2. **Process**: Layered AI pipelines extract tasks and metadata  
3. **Store**: Results saved to SQLite database with metadata_entries pattern
4. **Display**: Multiple specialized dashboards show different analytical views
5. **Analyze**: Comparison tools evaluate AI pipeline performance

**Key Architectural Decision**: Multi-layered AI processing allows graceful degradation:
- Base layer: Pattern matching (always works)
- Enhanced layer: OCR + VLM analysis (when available)
- Advanced layer: Semantic search with embeddings (when trained)

## File Structure

```
AutoTaskTracker/
├── autotasktracker/           # Core application package
│   ├── core/                  # Foundation components
│   ├── ai/                    # AI enhancement features
│   ├── dashboards/            # User interfaces
│   ├── comparison/            # AI evaluation tools
│   └── utils/                 # Shared utilities
├── scripts/                   # Standalone scripts
├── tests/                     # Test suite
└── docs/                      # Documentation
```

## Core Concepts

### Unique Windows

AutoTaskTracker tracks and analyzes your application windows and browser tabs to provide insights into your work patterns. For a comprehensive guide, see the [Unique Windows documentation](../concepts/unique_windows.md).

Key aspects:
- Tracks distinct application windows and browser tabs
- Provides metrics on focus and context switching
- Helps optimize workflow and productivity

This metric is particularly useful for understanding your work habits and identifying opportunities to improve focus and efficiency.

## Component Relationships

### Data Flow Architecture
```
Screenshots → OCR/VLM → Task Extraction → Categorization → Database → Dashboards
     ↓           ↓           ↓              ↓            ↓         ↓
  Pensieve    AI Analysis  Pattern Match  Smart Rules  SQLite   Streamlit
```

**Critical Decision**: Database-centric architecture ensures:
- All processing results are persisted and auditable
- Multiple dashboards can share the same processed data
- AI enhancements can be developed/tested without affecting core functionality
- Historical analysis becomes possible as data accumulates

### Dependencies
```
Core Components (foundation) ← Database schema drives everything
    ↓
AI Enhancement Layer (builds on core) ← Optional, degrades gracefully
    ↓  
Comparison Tools (evaluates AI) ← Development-time validation
    ↓
Dashboards (presents everything) ← User-facing, performance critical
```

**Design Rationale**: Layered dependency structure allows:
- Core functionality works without AI dependencies
- AI features can be incrementally enabled
- Development tools don't impact production performance
- Clear separation enables independent testing and deployment

## Dashboard Ecosystem

**Architectural Decision**: Separate production and development dashboards because:
- Production dashboards prioritize performance and reliability
- Development dashboards need experimental features and detailed diagnostics
- Different user personas (end users vs AI researchers)
- Independent deployment and scaling requirements

### Production Dashboards
- **Task Board** (`task_board.py`) - Primary interface for task viewing
- **Analytics** (`analytics.py`) - Productivity insights and trends  
- **Achievement Board** (`achievement_board.py`) - Gamification and goals

**Design Choice**: Streamlit for production dashboards because:
- Rapid development with Python-native components
- Built-in caching and state management
- Easy integration with pandas/numpy data processing
- No need for separate frontend/backend complexity

### Development Dashboards
- **Pipeline Comparison** (`comparison/dashboards/`) - AI method evaluation

**Rationale**: Separate comparison tools enable:
- A/B testing of different AI approaches
- Performance benchmarking without affecting production
- Data-driven decision making for AI improvements
- Academic research and method validation

## AI Processing Pipeline

**Critical Design Decision**: Graduated AI enhancement pipeline ensures system reliability:
- Each stage builds on previous stages but can work independently
- Failures in advanced stages don't break basic functionality
- Users get value immediately, enhanced value as AI capabilities improve
- Clear performance/accuracy tradeoffs at each stage

### Processing Stages
1. **Basic** - Pattern matching on window titles (50+ app patterns)
2. **OCR Enhanced** - Text extraction and analysis (requires Tesseract)
3. **VLM Enhanced** - Visual understanding (requires Ollama + 8GB VRAM)
4. **Full AI** - Semantic similarity search (requires embeddings database)

**Why This Architecture**:
- **Reliability**: Basic patterns work even when AI services are down
- **Performance**: Each stage adds computational cost, users can choose tradeoff
- **Development**: New AI methods can be tested without breaking existing functionality
- **Privacy**: More advanced stages can be disabled for privacy-sensitive environments

### AI Components
- `enhanced_task_extractor.py` - Orchestrates all AI features
- `ocr_enhancement.py` - Text analysis and confidence scoring
- `vlm_integration.py` - Visual language model integration
- `embeddings_search.py` - Semantic similarity search

**Component Design Rationale**:
- **Single Orchestrator**: `enhanced_task_extractor.py` provides unified interface
- **Specialized Modules**: Each AI capability in separate file for maintainability
- **Confidence Scoring**: All AI outputs include confidence for user decision-making
- **Fallback Strategy**: Each component has graceful degradation behavior

### Data Dependencies
```
Window Title (always available) ← Core requirement, minimal processing
    ↓
OCR Text (when available) → OCR Enhancement ← Pensieve integration
    ↓
VLM Description (when available) → VLM Enhancement ← External Ollama service
    ↓
Historical Data (when available) → Semantic Search ← Requires training time
```

**Data Flow Decision**: Each stage adds value independently because:
- Window titles provide immediate basic functionality
- OCR text enables content-aware task extraction
- VLM descriptions add visual context understanding
- Historical embeddings enable pattern recognition and workflow optimization

## Database Schema

**Schema Design Decision**: Inherited Pensieve schema with metadata_entries pattern because:
- **Extensibility**: New AI features can add metadata without schema changes
- **Flexibility**: Different AI outputs (text, JSON, binary) stored uniformly
- **Performance**: Single join operation retrieves all AI results for an entity
- **Compatibility**: Works with existing Pensieve ecosystem and tools

### Core Tables
- **entities** - Screenshot files and metadata (Pensieve core)
- **metadata_entries** - AI processing results linked to entities (Pensieve extensible)
- **Key relationship**: `entities.id` ↔ `metadata_entries.entity_id`

**Why This Pattern Works**:
- Pensieve handles screenshot capture, storage, and basic OCR
- AutoTaskTracker adds AI enhancement as metadata without breaking Pensieve
- Multiple AI processing results can coexist for same screenshot
- Historical analysis works across different AI model versions

### Metadata Types
- `ocr_result` - Text extraction results (Pensieve native)
- `vlm_result` - Visual analysis results (AutoTaskTracker extension)
- `active_window` - Window title information (Pensieve native)
- `embedding` - Vector embeddings for similarity search (AutoTaskTracker extension)
- `tasks` - Extracted task descriptions (AutoTaskTracker core)
- `category` - Activity categorization (AutoTaskTracker core)

**Metadata Strategy**: Key-value storage enables:
- Different AI models can store different result formats
- Experimentation with new AI approaches without database migrations
- Version compatibility as AI models improve
- Audit trail of different processing attempts

## Service Architecture

**Port Strategy Decision**: Fixed port allocation prevents conflicts and enables:
- Consistent bookmarks and documentation
- Process management and monitoring scripts
- Development/production environment isolation
- Load balancer configuration for multi-instance deployments

### Production Services
```
memos serve    (port 8839) - Backend API (Pensieve)
task_board.py  (port 8502) - Main dashboard (primary UI)
analytics.py   (port 8503) - Analytics dashboard (insights)
```

**Production Design Rationale**:
- **Pensieve Backend**: Handles all data capture and storage concerns
- **Specialized Dashboards**: Each dashboard optimized for specific use cases
- **Stateless Frontend**: Streamlit dashboards can be restarted without data loss
- **Independent Scaling**: Different dashboards can be scaled based on usage patterns

### Development Tools
```
comparison_cli.py              - CLI analysis tool (scripting)
pipeline_comparison.py (8512)  - Interactive comparison (research)
achievement_board.py (8507)    - Goals tracking (experimental)
```

**Development Tools Philosophy**:
- **CLI First**: Enables automation and batch processing for research
- **Interactive Validation**: Web interface for detailed AI pipeline analysis
- **Experimental Features**: Isolated environment for testing new concepts
- **Research Support**: Tools designed for AI method development and validation

## Component Interaction Patterns

### Data Processing Flow
```
Memos Capture → Database Storage → Core Processing → AI Enhancement → Dashboard Display
```

### User Interaction Flow  
```
User Views Dashboard → Selects Screenshot → Triggers Processing → Shows Results
```

### Development Flow
```
Run Comparison → Analyze Results → Tune Parameters → Re-evaluate → Deploy Changes
```

## Quick Reference

- **Daily tasks**: http://localhost:8502 (Task Board)
- **Analytics**: http://localhost:8503 (Analytics Dashboard)
- **AI evaluation**: `python comparison_cli.py` or http://localhost:8512
- **AI management**: `python scripts/ai_cli.py`
- **Code exploration**: Start with `autotasktracker/core/` then `autotasktracker/ai/`

This architecture enables clear separation of concerns while maintaining flexibility for AI experimentation and improvement.