# Tasks Today Counter Component

## Overview
The Tasks Today Counter is a dashboard component that displays the number of tasks discovered or completed today, providing users with immediate feedback on their daily productivity.

## Purpose
- Provide at-a-glance daily task metrics
- Motivate users with real-time progress tracking
- Enable quick daily productivity assessment
- Support goal tracking and achievement

## Design Specifications

### Visual Design
```
┌─────────────────────────┐
│    📋 Tasks Today       │
│         42              │
│    ↑ 15% from yesterday │
└─────────────────────────┘
```

### Component Structure
```python
class TasksTodayCounter:
    """Display count of tasks discovered/completed today."""
    
    @staticmethod
    def render(
        task_count: int,
        comparison: Optional[Dict[str, Any]] = None,
        variant: str = "default",
        show_trend: bool = True
    ) -> None:
        """Render the tasks today counter."""
        pass
```

## Features

### Core Functionality
1. **Real-time Count**: Updates as new tasks are discovered
2. **Daily Reset**: Automatically resets at midnight (user timezone)
3. **Comparison Metrics**: Shows change from previous day
4. **Visual Indicators**: Color-coded trends (green/red/neutral)

### Configuration Options
- **Variant Types**:
  - `default`: Standard counter display
  - `compact`: Minimal space usage
  - `detailed`: Includes breakdown by category
  - `motivational`: Adds encouraging messages

- **Display Options**:
  - Show/hide trend indicator
  - Custom time period (today/this week/custom)
  - Task type filtering (all/completed/pending)
  - Animation on count change

### Data Sources
The component pulls data from:
1. Task extraction results (metadata_entries)
2. AI classification results
3. User confirmation status
4. Time-based filtering

## Implementation Details

### API Design
```python
# Basic usage
TasksTodayCounter.render(task_count=42)

# With comparison
TasksTodayCounter.render(
    task_count=42,
    comparison={
        'yesterday': 36,
        'trend': 'up',
        'percentage': 16.7
    }
)

# Detailed variant with categories
TasksTodayCounter.render(
    task_count=42,
    variant='detailed',
    breakdown={
        'meetings': 5,
        'todos': 12,
        'emails': 8,
        'code_reviews': 17
    }
)
```

### State Management
- Caches count for performance
- Updates on:
  - New screenshot processed
  - Task status change
  - Manual refresh
  - Time period change

### Performance Considerations
- Efficient database queries with proper indexing
- Client-side caching with TTL
- Debounced updates to prevent flicker
- Lazy loading for detailed views

## Integration Points

### Dashboard Integration
```python
# In task_board.py
col1, col2, col3 = st.columns(3)
with col1:
    TasksTodayCounter.render(
        task_count=metrics['today_count'],
        comparison=metrics['comparison']
    )
```

### Event Handling
- Subscribes to task discovery events
- Emits count change events for other components
- Supports click actions (drill-down to task list)

## Visual States

### Loading State
- Skeleton loader animation
- Maintains last known count

### Error State
- Graceful degradation
- Shows last cached value
- Error indicator with retry

### Empty State
- Encouraging message for new users
- Quick start tips
- Historical comparison if available

## Accessibility
- ARIA labels for screen readers
- Keyboard navigation support
- High contrast mode support
- Configurable font sizes

## Testing Requirements
1. **Unit Tests**:
   - Count calculation accuracy
   - Time zone handling
   - Comparison logic

2. **Integration Tests**:
   - Dashboard integration
   - Real-time updates
   - Cache behavior

3. **Visual Tests**:
   - All variant displays
   - Responsive behavior
   - Animation smoothness

## Future Enhancements
1. **Goal Setting**: Allow users to set daily targets
2. **Notifications**: Alert when goals reached
3. **Historical Chart**: Mini sparkline of past week
4. **Gamification**: Streaks and achievements
5. **Export**: Daily summaries for reporting

## Usage Examples

### Basic Counter
```python
# Simple task count
TasksTodayCounter.render(task_count=25)
```

### With Yesterday Comparison
```python
# Show trend from yesterday
today_count = db.get_task_count(date=today)
yesterday_count = db.get_task_count(date=yesterday)

TasksTodayCounter.render(
    task_count=today_count,
    comparison={
        'yesterday': yesterday_count,
        'trend': 'up' if today_count > yesterday_count else 'down',
        'percentage': abs((today_count - yesterday_count) / yesterday_count * 100)
    }
)
```

### Motivational Variant
```python
# Encouraging messages based on progress
TasksTodayCounter.render(
    task_count=42,
    variant='motivational',
    messages={
        'milestone': "Great job! You've hit 40+ tasks!",
        'streak': "3 day streak! Keep it going!"
    }
)
```

## Related Components
- Period Statistics: For longer time ranges
- Task Summary Table: Detailed task breakdown
- Analytics Charts: Historical trends
- Goal Tracker: Target achievement