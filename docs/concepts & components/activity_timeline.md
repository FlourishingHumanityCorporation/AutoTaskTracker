# Activity Timeline Component

## 1. Overview

### 1.1 Conceptual Definition
The Activity Timeline is a visual representation of user activities and system events displayed in chronological order, providing a comprehensive view of work patterns, task progress, and system interactions over time. It serves as both an analytical tool and an audit trail.

### 1.2 Purpose
- Visualize the sequence and duration of work activities
- Identify patterns in work habits and productivity
- Provide context for task completion and system interactions
- Support time tracking and analysis
- Enable retrospective reviews and process improvement

## 2. Technical Specifications

### 2.1 Component Architecture
```
┌───────────────────────────────────────────────────────────────┐
│                    Activity Timeline                         │
├───────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ┌─────┐ 09:00  Started work                         │  │
│  │  │  🔵  │───────────────────────────────────────┐    │  │
│  │  └─────┘                                       │    │  │
│  │  ┌─────┐ 09:15  Task: Update Documentation     │    │  │
│  │  │  🟢  │─────────────────────────────────┐    │    │  │
│  │  └─────┘                                 │    │    │  │
│  │  ┌─────┐ 09:30  Screenshot captured      │    │    │  │
│  │  │  📷  │───────────────────────────┐    │    │    │  │
│  │  └─────┘                           │    │    │    │  │
│  │  ┌─────┐ 10:00  Meeting: Standup   │    │    │    │  │
│  │  │  🟣  │─────────────────────────┼────┐    │    │  │
│  │  └─────┘                         │    │    │    │  │
│  │  ┌─────┐ 10:30  Break            │    │    │    │  │
│  │  │  ⏸️  │────────────────────┐    │    │    │    │  │
│  │  └─────┘                    │    │    │    │    │  │
│  │  ┌─────┐ 10:45  Resumed work │    │    │    │    │  │
│  │  │  🔵  │────────────────────┼────┼────┘    │    │  │
│  │  └─────┘                    │    │         │    │  │
│  └────────────────────────────┼────┼─────────┼────┘  │
│  [Zoom +] [Today] [Custom Range ▼] [Export]          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Model

#### 2.2.1 Timeline Event Types
- **Work Sessions**: Active work periods
- **Task Activities**: Task creation, updates, completions
- **System Events**: Screenshots, OCR processing
- **Meetings & Breaks**: Calendar events and downtime
- **Context Switches**: Changes between different tasks/applications

#### 2.2.2 Data Structure
```python
class TimelineEvent:
    id: UUID
    type: TimelineEventType
    start_time: datetime
    end_time: Optional[datetime]
    duration: timedelta
    
    # Entity reference
    entity_type: str  # 'task', 'screenshot', 'meeting', etc.
    entity_id: Optional[UUID]
    
    # Display properties
    title: str
    description: Optional[str]
    color: str
    icon: str
    
    # Metadata
    metadata: Dict[str, Any]
    tags: List[str]
    
    # Relationships
    parent_event_id: Optional[UUID]  # For nested events
    related_events: List[UUID]       # For linked events
```

## 3. Component Details

### 3.1 Timeline Visualization

#### 3.1.1 Time Scale Modes
```python
class TimeScale(Enum):
    MINUTES_15 = "15min"  # 15-minute intervals
    HOURLY = "hourly"     # 1-hour intervals
    DAILY = "daily"       # 1-day intervals
    WEEKLY = "weekly"     # 1-week intervals
    CUSTOM = "custom"     # User-defined scale
```

#### 3.1.2 Event Rendering
- **Duration Bars**: Horizontal bars showing event duration
- **Collapsible Groups**: Group related events (e.g., all tasks in a project)
- **Event Density**: Adjustable visualization for high-activity periods
- **Current Time Indicator**: Vertical line showing the current time

### 3.2 Interactive Features

#### 3.2.1 Navigation
- **Zoom**: In/out on time scale
- **Pan**: Move left/right through time
- **Jump to**: Specific date/time
- **Today Button**: Quickly return to current time

#### 3.2.2 Event Interaction
- **Hover**: Show tooltip with details
- **Click**: Open detailed view
- **Drag**: Reschedule events (if applicable)
- **Select**: Multiple event selection

## 4. Implementation

### 4.1 Backend Processing

#### 4.1.1 Event Aggregation
```python
async def get_timeline_events(
    user_id: UUID,
    start_time: datetime,
    end_time: datetime,
    filters: Optional[Dict] = None
) -> List[TimelineEvent]:
    """Fetch and process timeline events for the given time range."""
    # Get raw events from various sources
    task_events = await get_task_events(user_id, start_time, end_time)
    screenshot_events = await get_screenshot_events(user_id, start_time, end_time)
    calendar_events = await get_calendar_events(user_id, start_time, end_time)
    
    # Combine and sort all events
    all_events = task_events + screenshot_events + calendar_events
    all_events.sort(key=lambda e: e.start_time)
    
    # Apply filters if provided
    if filters:
        all_events = [e for e in all_events if matches_filters(e, filters)]
    
    # Process events to calculate durations and relationships
    return process_event_relationships(all_events)
```

#### 4.1.2 Gap Detection
```python
def detect_work_sessions(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """Identify continuous work sessions from discrete events."""
    if not events:
        return []
        
    # Sort by start time
    sorted_events = sorted(events, key=lambda e: e.start_time)
    
    sessions = []
    current_session = None
    
    for event in sorted_events:
        if current_session is None:
            # Start new session
            current_session = TimelineEvent(
                type=TimelineEventType.WORK_SESSION,
                start_time=event.start_time,
                end_time=event.end_time or event.start_time,
                title="Work Session"
            )
        else:
            # Check if this event continues the current session
            gap = (event.start_time - current_session.end_time).total_seconds()
            
            if gap <= WORK_SESSION_GAP_THRESHOLD:  # e.g., 15 minutes
                # Extend current session
                current_session.end_time = max(
                    current_session.end_time,
                    event.end_time or event.start_time
                )
            else:
                # Finalize current session and start new one
                sessions.append(current_session)
                current_session = TimelineEvent(
                    type=TimelineEventType.WORK_SESSION,
                    start_time=event.start_time,
                    end_time=event.end_time or event.start_time,
                    title="Work Session"
                )
    
    # Add the last session if it exists
    if current_session:
        sessions.append(current_session)
    
    return sessions
```

### 4.2 Frontend Implementation

#### 4.2.1 Timeline Rendering (React Example)
```jsx
function Timeline({ events, startTime, endTime, scale }) {
  const timeScale = useTimeScale({ startTime, endTime, scale });
  const [selectedEvent, setSelectedEvent] = useState(null);
  
  // Group events by time periods based on scale
  const timeSlots = useMemo(() => {
    return groupEventsByTime(events, scale, startTime, endTime);
  }, [events, scale, startTime, endTime]);

  return (
    <div className="timeline">
      <TimelineHeader 
        startTime={startTime}
        endTime={endTime}
        scale={scale}
        onScaleChange={handleScaleChange}
      />
      
      <div className="timeline-content">
        {timeSlots.map(({ time, events }) => (
          <TimelineSlot 
            key={time.toString()}
            time={time}
            events={events}
            timeScale={timeScale}
            onEventClick={setSelectedEvent}
          />
        ))}
      </div>
      
      {selectedEvent && (
        <EventDetailsModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}
```

## 5. Performance Considerations

### 5.1 Data Loading
- **Time-based Chunking**: Load data in chunks based on visible time range
- **Progressive Loading**: Load more data as user scrolls
- **Server-side Aggregation**: Pre-aggregate data for faster rendering

### 5.2 Rendering Optimization
- **Virtualization**: Only render visible timeline segments
- **Canvas Rendering**: Use canvas for large datasets
- **Level-of-Detail**: Simplify rendering for small/zoomed-out views

## 6. Related Components

### 6.1 Integration Points
- **Activity Stream**: Raw event data source
- **Task Management**: Task-related events
- **Calendar Integration**: Scheduled events and meetings
- **Analytics Dashboard**: Time tracking metrics

### 6.2 Dependencies
- Date/Time handling library (e.g., date-fns, moment)
- Visualization library (e.g., D3, vis-timeline)
- State management (e.g., Redux, Zustand)

## 7. Future Enhancements

### 7.1 Planned Features
- **Collaborative Timeline**: View team members' activities
- **Automatic Tagging**: AI-powered event categorization
- **Time Blocking**: Plan future time allocation
- **Integration with External Tools**: Import/export timeline data

### 7.2 Research Areas
- Anomaly detection in work patterns
- Predictive time allocation
- Automated time tracking suggestions
- Privacy-preserving team analytics
