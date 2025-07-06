# Task List Component

## Conceptual Definition
An interactive, filterable list that displays individual task records with their details and status, allowing users to browse and manage their tasks efficiently.

## Technical Definition
A Streamlit component that renders task data in an expandable list format, with each task displayed in a collapsible container showing its details, status, and related actions.

## Implementation Details

### Data Source
- **Primary Method**: `TaskRepository.get_tasks_for_period()`
- **Data Structure**: List of task dictionaries with consistent schema
- **Filtering**: Server-side filtering based on user selections

### Features

#### 1. Task Grouping
- Groups tasks by creation date (most recent first)
- Date headers with task counts
- Collapsible date sections

#### 2. Task Item Display
- **Expandable Details**:
  - Task title and description
  - Creation timestamp
  - Current status
  - Related metadata
- **Status Indicators**:
  - Color-coded badges
  - Status-specific icons

#### 3. Screenshot Preview
- Thumbnail of associated screenshot (if available)
- Click-to-expand functionality
- Fallback UI for missing images

#### 4. Interactive Elements
- Status update buttons
- Task selection for detailed view
- Context menu for actions (edit, delete, etc.)

### Performance Considerations
- Virtual scrolling for large task lists
- Lazy loading of images
- Server-side pagination

## Example Display
```
## Today (3)
▼ [✅] Complete project documentation
  Created: 10:30 AM
  Screenshot: [thumbnail]
  
▼ [🔄] Fix login bug
  Created: 11:15 AM
  Screenshot: [thumbnail]

## Yesterday (5)
...
```

## Related Components
- [Task Metrics Summary](./task_metrics_summary.md)
- [Task Filters](./task_filters.md)
- [Task Repository](../architecture/ARCHITECTURE.md#task-repository)
