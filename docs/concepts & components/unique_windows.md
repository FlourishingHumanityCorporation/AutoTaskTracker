# Unique Windows in AutoTaskTracker

## Overview
In AutoTaskTracker, "unique windows" is a fundamental metric that tracks distinct application windows or browser tabs during your work sessions. This metric provides valuable insights into your work patterns and productivity.

## Definition
- Represents individual application windows or browser tabs being tracked
- Each unique window title/application combination is counted once
- Tracked over configurable time periods (daily, weekly, etc.)
- Examples:
  - VS Code (1 window) = 1 unique window
  - Chrome with 3 tabs = 3 unique windows (one per tab title)
  - Terminal (1 window) = 1 unique window
  - Total in this example: 5 unique windows

## Implementation Details

### Data Capture
- Captured automatically through the system's screenshot and window tracking
- Each window is identified by:
  - Application name (e.g., "Google Chrome", "Visual Studio Code")
  - Window title (e.g., "Documentation - AutoTaskTracker - VS Code")
  - Timestamp of observation

### Storage
- Stored in the database with associated metadata:
  - Application name
  - Window title
  - Timestamp
  - Screenshot reference (when available)
  - Duration of active use

### Processing
- Deduplication occurs based on window title and application
- Time-based aggregation for different reporting periods
- Integration with other metrics for comprehensive analysis

## Purpose and Benefits

### Productivity Insights
- Identifies context switching patterns
- Tracks focus and attention distribution
- Measures time spent in different applications

### Work Pattern Analysis
- Identifies most frequently used applications
- Tabs usage patterns
- Application switching frequency

### System Recommendations
- Suggests when too many windows might be causing context switching overhead
- Identifies opportunities for workflow optimization
- Tracks focus time and deep work sessions

## Example Scenarios

### High Context Switching
```
9:00-9:30: 12 unique windows
- VS Code (main project)
- Chrome (8 different documentation tabs)
- Terminal (2 different sessions)
- Slack
```
**Insight**: High number of windows may indicate frequent context switching.

### Focused Work
```
14:00-15:30: 3 unique windows
- VS Code (main project)
- Terminal (build process)
- Chrome (API documentation)
```
**Insight**: Lower window count suggests focused work session.

## Best Practices
- Aim for a balance between necessary context and focus
- Use the metric to identify when to close unused applications/tabs
- Schedule deep work sessions with minimal window switching
- Review patterns over time to understand your most productive workflows

## Related Metrics
- Window switch frequency
- Time per window
- Application usage distribution
- Task completion rate vs. window count

## Configuration
You can adjust how unique windows are tracked in the application settings, including:
- Window title cleaning rules
- Application grouping
- Minimum active time threshold
- Reporting period settings
