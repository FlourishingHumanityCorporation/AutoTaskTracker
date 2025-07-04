# Dashboard Refactoring Guide

This document explains the new dashboard architecture and how to refactor existing dashboards.

## New Architecture Overview

### 1. Base Dashboard Class (`base.py`)
- Common functionality for all dashboards
- Database connection management
- Error handling
- Session state initialization
- Time filtering utilities

### 2. Reusable Components (`components/`)
- **filters.py**: Time and category filters
- **metrics.py**: Metric cards and rows
- **data_display.py**: Task groups, activity cards, data tables

### 3. Data Access Layer (`data/`)
- **models.py**: Data models (Task, Activity, TaskGroup, DailyMetrics)
- **repositories.py**: Data access repositories with business logic

## Benefits of Refactoring

1. **Reduced Code Duplication**: ~40% less code by reusing components
2. **Consistent UI/UX**: All dashboards use same components
3. **Easier Maintenance**: Changes in one place affect all dashboards
4. **Better Testing**: Can test components independently
5. **Performance**: Optimized queries and caching (coming soon)

## How to Refactor a Dashboard

### Step 1: Extend BaseDashboard
```python
from .base import BaseDashboard

class MyDashboard(BaseDashboard):
    def __init__(self):
        super().__init__(
            title="My Dashboard",
            icon="🎯",
            port=8504
        )
```

### Step 2: Use Reusable Components
```python
from .components import TimeFilterComponent, MetricsRow

# Instead of custom time filter code:
time_filter = TimeFilterComponent.render()
start_date, end_date = TimeFilterComponent.get_time_range(time_filter)

# Instead of custom metrics display:
MetricsRow.render({
    "Total Tasks": 42,
    "Duration": "3.5 hours"
})
```

### Step 3: Use Data Repositories
```python
from .data import TaskRepository

# Instead of raw SQL queries:
task_repo = TaskRepository(self.db_manager)
tasks = task_repo.get_tasks_for_period(start_date, end_date)
task_groups = task_repo.get_task_groups(start_date, end_date)
```

### Step 4: Implement run() Method
```python
def run(self):
    if not self.ensure_connection():
        return
        
    # Your dashboard logic here
    st.title("My Dashboard")
    # ... render components
```

## Example: Task Board Refactoring

See `task_board_refactored.py` for a complete example showing:
- How to structure the dashboard class
- Using components for filters and display
- Accessing data through repositories
- Cleaner code organization

### Before (task_board.py): ~650 lines
- Database queries mixed with UI
- Duplicate time filtering logic
- Custom metrics display
- Error handling scattered

### After (task_board_refactored.py): ~250 lines
- Clean separation of concerns
- Reusable components
- Consistent error handling
- Easier to understand and modify

## Migration Strategy

1. **Phase 1**: Create new architecture (✅ Complete)
   - Base class
   - Components
   - Data layer

2. **Phase 2**: Refactor one dashboard as example (✅ Complete)
   - task_board_refactored.py

3. **Phase 3**: Gradually refactor other dashboards
   - Keep original versions during transition
   - Test thoroughly
   - Update imports in main launcher

4. **Phase 4**: Remove old versions
   - Once all dashboards migrated
   - Update documentation
   - Clean up legacy code

## Next Steps

1. Add caching layer for better performance
2. Implement WebSocket for real-time updates
3. Add more visualization components
4. Create dashboard templates
5. Add comprehensive tests