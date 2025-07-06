# Dashboard Component Architecture

## Overview

AutoTaskTracker uses a component-based architecture for all dashboard implementations. This architecture promotes code reuse, maintainability, and consistent user experience across all dashboards.

## Architecture Principles

### 1. Component-Based UI
- **Reusable Components**: UI elements are extracted into standalone components
- **Stateless Design**: Most components are stateless for easier testing
- **Composition**: Complex UIs are built by composing simpler components

### 2. Repository Pattern
- **Data Access Layer**: All data access goes through repository classes
- **Caching Support**: Built-in caching for expensive queries
- **Database Agnostic**: Easy to switch between different backends

### 3. Base Dashboard Class
- **Common Functionality**: Shared features like connection handling, caching
- **Consistent Structure**: All dashboards follow the same pattern
- **Session State Management**: Centralized session state handling

## Component Structure

```
autotasktracker/dashboards/
├── base.py                    # BaseDashboard class
├── components/                # Reusable UI components
│   ├── base_component.py      # Component base classes
│   ├── filters.py             # Time and category filters
│   ├── metrics.py             # Metric displays
│   ├── data_display.py        # Data visualization components
│   ├── visualizations.py      # Charts and graphs
│   └── [dashboard]_components.py  # Dashboard-specific components
├── data/                      # Data access layer
│   ├── models.py              # Data models
│   ├── repositories.py        # Repository classes
│   └── core/                  # Business logic
└── [dashboard].py             # Individual dashboards
```

## Component Types

### Base Components

#### BaseComponent
Abstract base class for stateful components:
```python
class BaseComponent:
    def render(self, **kwargs) -> Any
    def get_cache_key(self, **kwargs) -> str
    def get_default_config(self) -> Dict[str, Any]
```

#### StatelessComponent
For simple, stateless components:
```python
class StatelessComponent:
    @staticmethod
    def render(**kwargs) -> Any
```

### Common Components

#### Filters
- `TimeFilterComponent`: Date/time range selection
- `CategoryFilterComponent`: Task category filtering

#### Metrics
- `MetricsCard`: Single metric display
- `MetricsRow`: Multiple metrics in a row

#### Data Display
- `TaskGroup`: Grouped task display
- `ActivityCard`: Individual activity cards
- `DataTable`: Enhanced data tables
- `NoDataMessage`: Empty state displays

#### Visualizations
- `CategoryPieChart`: Category distribution
- `TimelineChart`: Activity timeline
- `HourlyActivityChart`: Hourly patterns
- `TrendChart`: Trend analysis
- And more...

### Dashboard-Specific Components

Each dashboard can have its own specialized components:

#### Time Tracker Components
- `TimeTrackerTimeline`: Session timeline visualization
- `TimeTrackerMetrics`: Time tracking metrics
- `TimeTrackerTaskList`: Detailed task list

#### VLM Monitor Components
- `VLMCoverageGauge`: Coverage percentage gauge
- `VLMSystemStatus`: System health display
- `VLMProcessingTimeline`: Processing timeline

#### Real-time Components
- `RealtimeMetricsRow`: Live metrics display
- `LiveActivityFeed`: Real-time activity feed
- `SmartSearchInterface`: Advanced search UI

## Usage Examples

### Creating a Dashboard

```python
from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components import TimeFilterComponent, MetricsRow
from autotasktracker.dashboards.data.repositories import TaskRepository

class MyDashboard(BaseDashboard):
    def __init__(self):
        super().__init__(
            title="My Dashboard",
            icon="📊",
            port=8504
        )
        
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            time_filter = TimeFilterComponent.render()
            return time_filter
            
    def run(self):
        """Main dashboard execution."""
        if not self.ensure_connection():
            return
            
        # Get filters
        time_filter = self.render_sidebar()
        
        # Get data
        task_repo = TaskRepository(self.db_manager)
        tasks = task_repo.get_tasks(time_filter)
        
        # Display metrics
        MetricsRow.render({
            "Total Tasks": len(tasks),
            "Categories": len(set(t.category for t in tasks))
        })
```

### Creating a Component

```python
from autotasktracker.dashboards.components.base_component import StatelessComponent

class MyComponent(StatelessComponent):
    @staticmethod
    def render(data, title="My Component", **kwargs):
        """Render the component."""
        st.subheader(title)
        
        # Component logic here
        for item in data:
            st.write(item)
```

## Best Practices

### 1. Component Design
- Keep components focused on a single responsibility
- Use descriptive names that indicate the component's purpose
- Provide sensible defaults for all parameters
- Document component parameters and return values

### 2. Data Access
- Always use repository classes for data access
- Never access the database directly from components
- Use caching for expensive queries
- Handle errors gracefully

### 3. State Management
- Minimize stateful components
- Use Streamlit's session state appropriately
- Keep component state isolated

### 4. Performance
- Use the `@cached_data` decorator for expensive operations
- Implement pagination for large datasets
- Lazy load heavy components

### 5. Testing
- Write unit tests for components
- Test components in isolation
- Mock dependencies appropriately

## Migration Guide

To refactor an existing dashboard:

1. **Identify Reusable UI Elements**
   - Look for repeated UI patterns
   - Find inline rendering code
   - Identify data access patterns

2. **Extract Components**
   - Create component classes
   - Move rendering logic to components
   - Keep components focused

3. **Create Repositories**
   - Extract data access logic
   - Implement caching where beneficial
   - Handle database specifics

4. **Update Dashboard**
   - Extend `BaseDashboard`
   - Use components for rendering
   - Use repositories for data access

5. **Test Thoroughly**
   - Ensure functionality is preserved
   - Test edge cases
   - Verify performance

## Component Catalog

For a complete list of available components and their usage, see:
- `/autotasktracker/dashboards/components/__init__.py`
- Individual component files in the components directory

Each component includes docstrings with usage examples and parameter descriptions.