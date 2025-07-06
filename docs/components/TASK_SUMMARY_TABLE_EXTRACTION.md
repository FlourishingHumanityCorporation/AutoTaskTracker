# Task Summary Table Component Extraction

## Overview

The Task Summary Table is implemented in the Time Tracker dashboard as part of the `TimeTrackerTaskList` component. This component provides an enhanced task list with detailed metrics, confidence indicators, and export functionality.

## Implementation Details

### Location
- **Component**: `autotasktracker/dashboards/components/timetracker_components.py`
- **Class**: `TimeTrackerTaskList` (lines 129-213)
- **Usage**: `autotasktracker/dashboards/timetracker.py` (line 224)

### Key Features

1. **Enhanced Task Metrics**
   - Total time (including gaps)
   - Active time (excluding idle gaps)
   - Session count
   - Confidence scoring with visual indicators
   - Category classification
   - First/last seen timestamps

2. **Visual Confidence Indicators**
   - 🟢 High confidence (0.8+): Dense screenshots, few gaps
   - 🟡 Medium confidence (0.5-0.8): Some gaps detected
   - 🔴 Low confidence (<0.5): Many gaps or sparse data

3. **Smart Time Tracking**
   - Accounts for 4-second screenshot intervals
   - Excludes idle gaps longer than 5 minutes
   - Category-aware gap thresholds
   - Intelligent session detection

4. **Data Export**
   - CSV export functionality
   - Filename includes selected date
   - All metrics included in export

### Component Architecture

```python
class TimeTrackerTaskList(StatelessComponent):
    """Enhanced task list for time tracker."""
    
    @staticmethod
    def render(task_groups: Dict[str, Dict[str, Any]], selected_date: datetime):
        """Render time tracker task list.
        
        Args:
            task_groups: Task groups from TimeTracker.group_by_task()
            selected_date: Date for the export filename
        """
```

### Data Structure

The component expects `task_groups` dictionary with this structure:
```python
{
    "task_name": {
        "total_minutes": float,
        "active_minutes": float,
        "session_count": int,
        "average_confidence": float,
        "category": str,
        "first_seen": datetime,
        "last_seen": datetime
    }
}
```

### Table Configuration

The table uses Streamlit's enhanced dataframe with custom column configuration:
- **Number columns**: Formatted with appropriate decimal places
- **Text columns**: Truncated at 50 characters for task names
- **Help tooltips**: Explain each metric
- **Sorting**: By total time (descending)

### Usage Example

```python
# In timetracker.py dashboard
if settings['show_detailed_list']:
    st.header("📋 Detailed Task List")
    TimeTrackerTaskList.render(task_groups, settings['selected_date'])
```

### Integration with Time Tracking System

The component works with:
1. **TimeTracker** class (`autotasktracker/core/time_tracker.py`)
   - Provides `group_by_task()` method
   - Calculates confidence scores
   - Handles session detection

2. **TaskSession** dataclass
   - Tracks individual work sessions
   - Calculates active vs total time
   - Manages gap tracking

### Reusability

This component can be extracted and reused in other dashboards:
1. Import the component
2. Provide task groups data in the expected format
3. Pass a date for export filename
4. The component handles all rendering and export logic

### Dependencies

- `streamlit`: For UI rendering
- `pandas`: For dataframe creation
- `datetime`: For timestamp handling
- Base component architecture from `autotasktracker.dashboards.components`

## Extraction for Reuse

To use this component in another context:

1. **Copy the component class** from `timetracker_components.py`
2. **Ensure data format** matches the expected structure
3. **Import required dependencies**
4. **Call the render method** with appropriate data

The component is self-contained and stateless, making it easy to integrate into any Streamlit-based dashboard that needs to display task summaries with time tracking metrics.