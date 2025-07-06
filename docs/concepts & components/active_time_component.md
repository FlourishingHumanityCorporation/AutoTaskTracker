# Active Time Component

## 1. Overview

### 1.1 Conceptual Definition
The Active Time component is a sophisticated tracking and visualization system that measures and displays user engagement and productivity by monitoring active work sessions, application usage, and task-focused time. It provides insights into how time is spent across different tasks and applications.

### 1.2 Purpose
- Track and quantify productive work time
- Identify patterns in work habits and focus periods
- Provide data for productivity analysis
- Support time management and work optimization
- Offer visual feedback on daily/weekly productivity trends

## 2. Technical Specifications

### 2.1 Component Architecture
```
┌───────────────────────────────────────────────────────────────┐
│                     Active Time Dashboard                     │
├───────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐     ┌─────────────────────────┐  │
│  │   Daily Active Time     │     │   Weekly Trend Graph    │  │
│  │   ┌─────────────────┐   │     │   ┌─────────────────┐   │  │
│  │   │  05:23 / 08:00  │   │     │   │  █▄▄▄▄▄▄▄▄▄▄▄   │   │  │
│  │   └─────────────────┘   │     │   │  █████████████   │   │  │
│  └─────────────────────────┘     │   │  █████████████   │   │  │
│                                  └─────────────────────────┘  │
├───────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐     ┌─────────────────────────┐  │
│  │  Application Breakdown  │     │  Focus Sessions Today   │  │
│  │  ┌─────────────────┐   │     │  ┌─────────────────┐   │  │
│  │  │  VS Code  45%   │   │     │  │  ░░░░░░░░░░░░░  │   │  │
│  │  │  Browser  30%   │   │     │  │  ▓▓▓▓▓▓▓▓▓▓▓▓  │   │  │
│  │  │  Terminal 15%   │   │     │  └─────────────────┘   │  │
│  │  └─────────────────┘   │     └─────────────────────────┘  │
│  └─────────────────────────┘                                 │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 Data Model

#### 2.2.1 Data Sources
- **Window Activity Logs**: Tracks active application windows and titles
- **User Input Events**: Monitors keyboard and mouse activity
- **System Idle Detection**: Identifies periods of inactivity
- **Task Associations**: Links activity to specific tasks when possible

#### 2.2.2 Data Structure
```python
class ActiveTimeSession:
    session_id: UUID
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    application: str
    window_title: str
    task_id: Optional[UUID]
    activity_level: float  # 0.0 to 1.0
    metadata: Dict[str, Any]

class DailyActiveTime:
    date: date
    total_active_seconds: int
    productive_seconds: int
    sessions: List[ActiveTimeSession]
    application_breakdown: Dict[str, int]  # app_name: seconds
```

## 3. Component Details

### 3.1 Core Metrics

#### 3.1.1 Active Time
- **Definition**: Time spent actively engaged with the computer
- **Measurement**: Based on user input events and application focus
- **Thresholds**: 
  - **Active**: User input within last 30 seconds
  - **Idle**: No input for >30 seconds
  - **Away**: No input for >5 minutes

#### 3.1.2 Focus Sessions
- **Definition**: Continuous periods of focused work
- **Requirements**:
  - Minimum 15 minutes duration
  - High activity level (>70%)
  - Limited application switching

#### 3.1.3 Productivity Score
- **Calculation**:
  ```
  Productivity Score = (Focused Time × 1.0 + 
                       Semi-Focused Time × 0.5 + 
                       Passive Time × 0.2) / Total Time
  ```
- **Range**: 0.0 (completely unproductive) to 1.0 (highly productive)

### 3.2 Visual Components

#### 3.2.1 Daily Summary
- **Active Time Clock**: Shows hours:minutes of active time
- **Progress Bar**: Visualizes progress toward daily goal
- **Comparison**: Today vs. daily average

#### 3.2.2 Activity Timeline
- **X-axis**: 24-hour period
- **Y-axis**: Activity level
- **Color Coding**:
  - Green: Focused work
  - Blue: General activity
  - Gray: Idle/away

#### 3.2.3 Application Breakdown
- **Donut Chart**: Shows time spent per application
- **Top Applications**: List of most used apps with percentages
- **Time per App**: Bar chart of time distribution

## 4. Implementation

### 4.1 Data Collection

#### 4.1.1 Activity Monitoring
```python
def track_activity():
    while True:
        current_window = get_active_window()
        input_events = get_input_events()
        
        if is_productive_activity(current_window, input_events):
            record_activity(
                window=current_window,
                activity_level=calculate_activity_level(input_events),
                timestamp=datetime.now()
            )
        time.sleep(1)  # Sample every second
```

#### 4.1.2 Focus Detection
```python
def detect_focus_sessions(activity_data: List[ActivityEvent]) -> List[FocusSession]:
    sessions = []
    current_session = None
    
    for event in activity_data:
        if is_high_activity(event) and not current_session:
            current_session = FocusSession(start_time=event.timestamp)
        elif not is_high_activity(event) and current_session:
            current_session.end(event.timestamp)
            if current_session.duration_seconds >= 900:  # 15 minutes
                sessions.append(current_session)
            current_session = None
            
    return sessions
```

### 4.2 Data Storage

#### 4.2.1 Database Schema
```sql
CREATE TABLE activity_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    application VARCHAR(255),
    window_title TEXT,
    task_id UUID,
    activity_level FLOAT,
    metadata JSONB
);

CREATE INDEX idx_activity_user_time ON activity_sessions(user_id, start_time);
CREATE INDEX idx_activity_application ON activity_sessions(application);
```

## 5. Performance Considerations

### 5.1 Data Aggregation
- **Real-time Processing**: Process events in memory, batch write to DB
- **Daily Rollups**: Generate daily summaries during off-peak hours
- **Caching**: Cache frequent queries (e.g., today's activity)

### 5.2 Optimization
- **Sampling**: Reduce resolution for historical data (e.g., 1-second to 1-minute)
- **Partitioning**: Partition tables by date for faster queries
- **Materialized Views**: Pre-calculate common aggregations

## 6. Related Components

### 6.1 Integration Points
- **Task Manager**: Link activity to specific tasks
- **Calendar**: Compare scheduled vs. actual work time
- **Productivity Analytics**: Generate insights from activity data

### 6.2 Dependencies
- System monitoring libraries
- Window management APIs
- Input event monitoring

## 7. Privacy and Security

### 7.1 Data Collection
- **Anonymization**: Store only application names, not content
- **Opt-in**: Allow users to disable monitoring
- **Local Processing**: Process sensitive data locally when possible

### 7.2 User Control
- **Granular Permissions**: Control what data is collected
- **Data Export**: Allow users to export their activity data
- **Clear Data**: Provide option to delete activity history

## 8. Future Enhancements

### 8.1 Planned Features
- **Smart Notifications**: Suggest breaks based on activity patterns
- **Focus Mode**: Temporarily block distracting applications
- **Team Analytics**: Compare productivity across teams (aggregated/anonymous)

### 8.2 Research Areas
- Machine learning for better activity classification
- Integration with wearables for health metrics
- Automated time tracking suggestions
