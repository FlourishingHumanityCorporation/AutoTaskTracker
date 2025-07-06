# Tasks Today Counter

## Conceptual Definition
The Tasks Today counter is a real-time metric that shows the number of tasks created or discovered on the current calendar day. It provides users with an immediate sense of daily productivity and task volume at a glance.

## Technical Definition
A Streamlit metric component that displays the count of database records in the `tasks` table with a `created_at` timestamp matching the current date (in the system's local timezone).

## Implementation Details

### Backend
- **Method**: `TaskRepository.count_tasks_today()`
- **Database Query**:
  ```sql
  SELECT COUNT(*) 
  FROM tasks 
  WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') = CURRENT_DATE
  ```
- **Timezone Handling**: Converts UTC timestamps to local time for accurate daily counts
- **Error Handling**: Returns "N/A" if there's a database error
- **Caching**: Results are cached for 60 seconds to improve performance

### Frontend
- **Component**: `st.metric()`
- **Update Frequency**: Refreshes with dashboard (default 60s)
- **Visual Indicator**: Calendar emoji (📅) for quick identification
- **Position**: Displayed in the top metrics row of the dashboard

## Data Flow
```
Database → TaskRepository → Dashboard View → Streamlit Metric
```

## Example Display
```
📊 Total Tasks: 42    ✅ Completed: 15    📅 Tasks Today: 7
```

## Related Components
- [Task Metrics Summary](./task_metrics_summary.md)
- [Task List Component](./task_list_component.md)
- [Task Repository](../architecture/ARCHITECTURE.md#task-repository)
