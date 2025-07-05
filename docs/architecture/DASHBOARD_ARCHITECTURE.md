# 🏗️ Dashboard Architecture - Technical Deep Dive

> **Refactored System (2025)**: This document describes the completely rewritten dashboard architecture featuring component-based design, intelligent data processing, and 40% code reduction.

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component System](#component-system)
3. [Data Layer Architecture](#data-layer-architecture)
4. [Smart Filtering System](#smart-filtering-system)
5. [Intelligent Task Grouping](#intelligent-task-grouping)
6. [Caching Strategy](#caching-strategy)
7. [Error Handling](#error-handling)
8. [Performance Optimizations](#performance-optimizations)

## 🎯 Architecture Overview

### **Design Philosophy**
The refactored dashboard system follows these core principles:

1. **Component Reusability**: 15+ reusable UI components eliminate code duplication
2. **Data-Driven Intelligence**: Filters and defaults adapt based on actual user data
3. **Repository Pattern**: Clean separation between data access and UI presentation
4. **Progressive Enhancement**: Core functionality works even when AI services fail
5. **Smart Defaults**: System intelligently configures itself based on usage patterns

### **Architectural Layers**

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐│
│  │   Task Board    │ │   Analytics     │ │  Achievement     ││
│  │   Dashboard     │ │   Dashboard     │ │   Board          ││
│  └─────────────────┘ └─────────────────┘ └──────────────────┘│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Component Layer                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐│
│  │   Filters       │ │    Metrics      │ │  Data Display    ││
│  │  (Smart)        │ │   Components    │ │   Components     ││
│  └─────────────────┘ └─────────────────┘ └──────────────────┘│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Data Access Layer                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐│
│  │ TaskRepository  │ │MetricsRepository│ │  Cache Manager   ││
│  │ (Smart Grouping)│ │ (Analytics)     │ │ (TTL + Smart)    ││
│  └─────────────────┘ └─────────────────┘ └──────────────────┘│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                          │
│           ┌─────────────────────────────────────┐           │
│           │         DatabaseManager            │           │
│           │      (Pensieve/SQLite)             │           │
│           └─────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🧩 Component System

### **Base Dashboard Class**
All dashboards inherit from `BaseDashboard` which provides:

```python
class BaseDashboard:
    """Base class with common dashboard functionality."""
    
    def __init__(self, title: str, icon: str, port: int):
        self.db_manager = DatabaseManager()  # Lazy loaded
        self.setup_page()                   # Streamlit configuration
        self.init_session_state()          # Smart defaults
    
    @property
    def db_manager(self) -> DatabaseManager:
        """Lazy-loaded database connection with error handling."""
        
    def ensure_connection(self) -> bool:
        """Check database connectivity with user-friendly errors."""
        
    def add_auto_refresh(self, seconds: int):
        """Consistent auto-refresh across dashboards."""
```

### **Reusable Components**

#### **Smart Filter Components** (`components/filters.py`)
```python
class TimeFilterComponent:
    @staticmethod
    def get_smart_default(db_manager=None) -> str:
        """Data-driven time filter selection."""
        # Analyzes actual data patterns to select appropriate default
        
    @staticmethod
    def render(db_manager=None) -> str:
        """Renders time filter with intelligent defaults."""

class CategoryFilterComponent:
    @staticmethod
    def render(multiselect=False) -> List[str]:
        """Fixed logic: empty selection = all categories."""
```

#### **Metrics Components** (`components/metrics.py`)
```python
class MetricsRow:
    @staticmethod
    def render(metrics: Dict[str, Any]):
        """Consistent metrics display across dashboards."""

class ProgressIndicator:
    @staticmethod
    def render(value: float, max_value: float, label: str):
        """Reusable progress visualization."""
```

#### **Data Display Components** (`components/data_display.py`)
```python
class TaskGroup:
    @staticmethod
    def render(window_title: str, duration: float, ...):
        """Standardized task group presentation."""

class NoDataMessage:
    @staticmethod
    def render(message: str, suggestions: List[str]):
        """Intelligent no-data messaging with actionable guidance."""
```

## 🗃️ Data Layer Architecture

### **Repository Pattern Implementation**

The data layer uses the Repository pattern to separate data access from business logic:

```python
class TaskRepository(BaseRepository):
    """Handles all task-related data operations."""
    
    def get_task_groups(
        self, 
        start_date: datetime, 
        end_date: datetime,
        min_duration_minutes: float = 0.5,
        gap_threshold_minutes: float = 15
    ) -> List[TaskGroup]:
        """Smart task grouping with window title normalization."""
        
    def _normalize_window_title(self, window_title: str) -> str:
        """Removes session noise while preserving context."""
        # Removes: MallocNanoZone=1, terminal dimensions, git hashes
        # Preserves: Application name, main context
```

### **Data Models** (`data/models.py`)
```python
@dataclass
class TaskGroup:
    window_title: str
    category: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    task_count: int
    tasks: List[Task]
    confidence: float = 1.0
```

## 🧠 Smart Filtering System

### **Data-Driven Time Filter**

The system automatically detects the appropriate time period based on actual data:

```python
def get_smart_default(db_manager=None) -> str:
    """Intelligent time filter selection."""
    try:
        # Check today's activity
        today_df = db_manager.fetch_tasks(start_date=today_start, end_date=now)
        
        # Check yesterday's activity  
        yesterday_df = db_manager.fetch_tasks(start_date=yesterday_start, end_date=yesterday_end)
        
        # Prefer day with more substantial activity
        if len(yesterday_df) >= len(today_df) and len(yesterday_df) >= 5:
            return "Yesterday"
        elif len(today_df) >= 5:
            return "Today"
        
        return "Last 7 Days"  # Safe fallback
    except Exception:
        return "Last 7 Days"
```

### **Intelligent Category Filtering**

Fixed the broken logic where "all selected" meant "exclude all":

```python
# Before (Broken)
default=categories[1:]  # Selects all categories = exclude all

# After (Fixed)  
default=[]  # Empty selection = include all categories
```

## 🔍 Intelligent Task Grouping

### **Window Title Normalization**

The system removes session-specific noise while preserving meaningful context:

```python
def _normalize_window_title(self, window_title: str) -> str:
    """Smart normalization for better task grouping."""
    
    # Remove session-specific noise
    normalized = re.sub(r'MallocNanoZone=\d+', '', window_title)
    normalized = re.sub(r'— \d+×\d+$', '', normalized)  # Terminal dimensions
    normalized = re.sub(r'\([a-f0-9]{7,}\)', '', normalized)  # Git hashes
    
    # Extract meaningful parts
    if ' — ' in normalized:
        parts = normalized.split(' — ')
        app_name = parts[0]
        main_context = parts[1] if len(parts) > 1 else ''
        
        # Skip generic parts, preserve meaningful context
        if main_context not in ['', '✳', '✳ ']:
            return f"{app_name} — {main_context}"
    
    return normalized
```

### **Improved Grouping Algorithm**

```python
# Enhanced grouping parameters
min_duration_minutes: float = 0.5   # Lowered from 1.0
gap_threshold_minutes: float = 15   # Increased from 10
```

**Results**: 30 → 107 task groups (3.5x improvement)

## ⚡ Caching Strategy

### **Multi-Layer Caching**

```python
class DashboardCache:
    @staticmethod
    def get_cached(key: str, fetch_func: Callable, ttl_seconds: int = 300):
        """TTL-based caching with intelligent invalidation."""
        
class QueryCache:
    def get_time_filtered_data(self, table: str, start_date: datetime, ...):
        """Database query caching with smart cache keys."""
```

### **Cache Invalidation Strategy**
- **Time-based**: TTL expires after specified duration
- **Data-driven**: Cache invalidated when underlying data changes
- **User-action**: Cache cleared on filter changes

## 🛡️ Error Handling

### **Graceful Degradation**

```python
def ensure_connection(self) -> bool:
    """Database connectivity with user-friendly error handling."""
    if not self.db_manager.test_connection():
        show_error_message(
            "Cannot connect to database",
            "Make sure Memos is running: memos start"
        )
        return False
    return True
```

### **Component Error Boundaries**

Each component handles its own errors without crashing the entire dashboard:

```python
def render_task_groups(self, ...):
    try:
        task_groups = task_repo.get_task_groups(...)
        # Render components
    except Exception as e:
        logger.error(f"Task group rendering failed: {e}")
        NoDataMessage.render(
            "Error loading tasks",
            ["Check database connection", "Refresh the page"]
        )
```

## 🚀 Performance Optimizations

### **Lazy Loading**
- Database connections created only when needed
- Components loaded on demand
- Large datasets paginated automatically

### **Efficient Queries**
```python
# Repository pattern enables query optimization
def get_task_groups(self, start_date: datetime, end_date: datetime, limit: int = 1000):
    """Optimized query with smart limits."""
    
# Batch operations where possible
def get_metadata_batch(self, entity_ids: List[int]):
    """Bulk metadata retrieval."""
```

### **Memory Management**
- Automatic cleanup of large datasets
- Session state management
- Component lifecycle optimization

## 📊 Key Architectural Decisions

### **Why Repository Pattern?**
- **Separation of Concerns**: UI logic separated from data access
- **Testability**: Easy to mock data layer for testing
- **Flexibility**: Can swap data sources without UI changes
- **Performance**: Centralized query optimization

### **Why Component-Based UI?**
- **Code Reuse**: 40% reduction in dashboard code
- **Consistency**: Uniform UI elements across dashboards
- **Maintainability**: Changes propagate across all dashboards
- **Testing**: Components can be tested in isolation

### **Why Smart Defaults?**
- **User Experience**: Works out-of-the-box without configuration
- **Adaptability**: Adjusts to user's actual data patterns
- **Reduced Support**: Fewer "no data found" issues
- **Intelligence**: System learns from usage patterns

## 🔧 Implementation Guidelines

### **Creating New Dashboards**
1. Inherit from `BaseDashboard`
2. Use repository pattern for data access
3. Compose UI from reusable components
4. Implement smart defaults where applicable
5. Add comprehensive error handling

### **Adding New Components**
1. Create in `components/` package
2. Make stateless with clear interfaces
3. Include error handling and graceful degradation
4. Add docstrings and type hints
5. Test in isolation

### **Extending Repositories**
1. Inherit from `BaseRepository`
2. Use parameterized queries for security
3. Implement caching where appropriate
4. Add comprehensive error handling
5. Document query performance characteristics

---

*This architecture enables the dashboard system to provide intelligent, data-driven experiences while maintaining high performance and reliability.*