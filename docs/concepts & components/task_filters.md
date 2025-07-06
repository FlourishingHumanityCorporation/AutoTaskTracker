# Task Filters

## Conceptual Definition
Interactive controls that allow users to customize which tasks are displayed based on various criteria, enabling focused task management and analysis.

## Technical Definition
A collection of Streamlit form widgets that modify the task query parameters and filter the displayed task list in real-time.

## Implementation Details

### Filter Types

#### 1. Status Filter
- **Type**: Dropdown Selector
- **Options**:
  - All Tasks (default)
  - Pending
  - In Progress
  - Completed
- **Implementation**:
  ```python
  status = st.selectbox(
      "Status",
      ['all', 'pending', 'in_progress', 'completed'],
      format_func=lambda x: x.replace('_', ' ').title()
  )
  ```

#### 2. Date Range Filter
- **Type**: Dropdown Selector
- **Options**:
  - Today
  - Last 7 Days (default)
  - Last 30 Days
  - Custom Range (future enhancement)
- **Implementation**:
  ```python
  date_range = st.selectbox(
      "Date Range",
      [1, 7, 14, 30],
      format_func=lambda x: f"Last {x} Days"
  )
  ```

#### 3. Search Filter
- **Type**: Text Input
- **Functionality**:
  - Full-text search across task titles and descriptions
  - Case-insensitive matching
  - Real-time filtering
- **Implementation**:
  ```python
  search_query = st.text_input("Search tasks", "")
  ```

### State Management
- **Storage**: Streamlit's session state
- **Persistence**: Maintains filter state across interactions
- **Update Behavior**: Triggers data refresh when filters change

### Performance Considerations
- Debounced search input
- Optimized database queries
- Client-side filtering when possible

## Example Usage
```python
# In the dashboard's _render_filters method
with st.sidebar:
    st.header("🔍 Filters")
    
    # Status filter
    status = st.selectbox(
        "Status",
        ['all', 'pending', 'in_progress', 'completed'],
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    # Date range filter
    date_range = st.selectbox(
        "Date Range",
        [1, 7, 14, 30],
        format_func=lambda x: f"Last {x} Days"
    )
    
    # Search box
    search_query = st.text_input("Search tasks", "")
```

## Related Components
- [Task List Component](./task_list_component.md)
- [Task Metrics Summary](./task_metrics_summary.md)
- [Streamlit Documentation](https://docs.streamlit.io/)
