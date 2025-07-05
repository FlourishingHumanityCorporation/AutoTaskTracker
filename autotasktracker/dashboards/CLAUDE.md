# Dashboards Module Context

**Focus**: Streamlit web interfaces and data visualization

## Module-Specific Rules

- **Port conventions**: Use assigned ports (8502, 8503, 8505) consistently
- **Graceful degradation**: Dashboards work even if AI features unavailable
- **Component reuse**: Use shared components from `components/` directory
- **Data isolation**: Use repository pattern for data access
- **Performance**: Implement caching for expensive operations

## Dashboard Architecture

**Main Dashboards:**
- `task_board.py` (port 8502) - Primary task management interface
- `analytics.py` (port 8503) - Data visualization and metrics
- `timetracker.py` (port 8505) - Productivity and time tracking
- `integration_health.py` - System monitoring dashboard

**Shared Components:**
- `components/data_display.py` - Data tables and lists
- `components/visualizations.py` - Charts and graphs
- `components/filters.py` - Search and filter widgets
- `components/metrics.py` - KPI and summary metrics

## Streamlit Patterns

```python
# ✅ Correct: Dashboard structure
import streamlit as st
from autotasktracker.dashboards.components import metrics, filters
from autotasktracker.dashboards.data.repositories import TaskRepository

def main():
    st.set_page_config(page_title="AutoTaskTracker", layout="wide")
    
    # Use repository pattern
    repo = TaskRepository()
    
    # Use shared components
    with st.sidebar:
        filters.render_time_filter()
    
    # Main content with error handling
    try:
        data = repo.get_tasks()
        metrics.render_task_metrics(data)
    except Exception as e:
        st.error(f"Data loading failed: {e}")
        st.info("Check system health with `/health-check`")
```

## State Management

- Use `st.session_state` for dashboard state
- Cache expensive data operations with `@st.cache_data`
- Implement real-time updates where appropriate
- Handle concurrent user sessions gracefully

## Data Access Patterns

- **Repository pattern**: Use `data/repositories.py` for data access
- **Database integration**: Always use DatabaseManager, never direct sqlite3
- **Error boundaries**: Wrap data operations in try/catch with user-friendly messages
- **Performance**: Implement pagination for large datasets

## UI/UX Guidelines

- **Responsive layout**: Use Streamlit's column system effectively
- **Loading states**: Show spinners for long operations
- **Error messages**: Provide actionable error information
- **Accessibility**: Use semantic HTML and proper contrast
- **Mobile friendly**: Test on different screen sizes

## Dashboard Testing

- Test dashboard loading without crashing
- Verify data displays correctly with sample data
- Test error handling when database unavailable
- Validate performance with large datasets