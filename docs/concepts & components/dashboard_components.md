# Dashboard Components

This directory contains detailed documentation for the various components that make up the AutoTaskTracker dashboards. Each component is documented in its own file for better organization and maintainability.

## Core Components

1. **[Tasks Today Counter](./tasks_today_counter.md)**
   - Real-time counter showing tasks created today
   - Displays current day's productivity at a glance

2. **[Task Metrics Summary](./task_metrics_summary.md)**
   - Consolidated view of task statistics
   - Shows distribution of tasks by status

3. **[Task List Component](./task_list_component.md)**
   - Interactive, filterable list of tasks
   - Displays task details and status

4. **[Task Filters](./task_filters.md)**
   - Interactive controls for customizing task views
   - Includes status, date range, and search filters

5. **[Unique Windows Tracking](./unique_windows.md)**
   - Tracks and analyzes application window usage
   - Provides insights into work patterns

## How to Use This Documentation

Each component's documentation includes:
- Conceptual definition
- Technical specifications
- Implementation details
- Related components
- Example usage

## Development Guidelines

When modifying or extending dashboard components:

1. **Create New Components**:
   - Add a new markdown file in this directory
   - Follow the existing documentation structure
   - Update this index file to include the new component

2. **Update Existing Components**:
   - Modify the relevant component file
   - Update any related documentation
   - Consider backward compatibility

3. **Testing**:
   - Test component interactions
   - Verify responsive behavior
   - Check for performance impacts

## Related Documentation

- [Architecture Overview](../architecture/ARCHITECTURE.md)
- [API Documentation](../api/README.md)
- [Development Guidelines](../CONTRIBUTING.md)
