# Live Activity Stream

## 1. Overview

### 1.1 Conceptual Definition
The Live Activity Stream is a real-time, chronologically ordered feed that captures and displays system-wide activities, user actions, and task-related events. It provides immediate visibility into what's happening across the AutoTaskTracker system, enabling users to stay informed about relevant updates without manual refreshing.

### 1.2 Purpose
- Provide real-time visibility into system activities
- Enhance collaboration through transparent task updates
- Enable quick response to important events
- Maintain a searchable history of all activities
- Support audit and compliance requirements

## 2. Technical Specifications

### 2.1 Component Architecture
```
┌───────────────────────────────────────────────────────────────┐
│                    Live Activity Stream                       │
├───────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🔵 John Doe created task "Update Documentation"      │  │
│  │  ⏱️ 2 minutes ago • #TASK-42                          │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  🟢 System captured new screenshot (window: VS Code)  │  │
│  │  ⏱️ 5 minutes ago • #SCREEN-8912                      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  🟣 Alice completed "Fix Login Bug"                   │  │
│  │  ⏱️ 1 hour ago • #TASK-41                            │  │
│  └───────────────────────────────────────────────────────┘  │
│  [Load More Activities]                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Model

#### 2.2.1 Event Types
- **Task Events**: Created, updated, completed, assigned
- **System Events**: Screenshot captured, OCR completed
- **User Actions**: Status changes, comments, mentions
- **Integration Events**: External system updates

#### 2.2.2 Data Structure
```python
class ActivityEvent:
    id: UUID
    event_type: str
    actor_id: UUID
    timestamp: datetime
    entity_type: str  # 'task', 'screenshot', 'user', etc.
    entity_id: UUID
    metadata: Dict[str, Any]
    
    # Computed fields
    actor_name: str
    entity_name: str
    message: str
    icon: str
    color: str
    is_important: bool
```

## 3. Component Details

### 3.1 Event Processing Pipeline

#### 3.1.1 Event Collection
```python
async def capture_event(event_type: str, actor: User, entity: Any, **metadata):
    """Capture and process an activity event."""
    event = ActivityEvent(
        id=uuid4(),
        event_type=event_type,
        actor_id=actor.id,
        timestamp=datetime.utcnow(),
        entity_type=entity.__class__.__name__,
        entity_id=entity.id,
        metadata=metadata
    )
    
    # Enrich with additional context
    await event.enrich()
    
    # Store in database
    await db.save_event(event)
    
    # Publish to real-time subscribers
    await event_bus.publish('activity', event)
    
    return event
```

#### 3.1.2 Real-time Updates
- WebSocket connection for instant updates
- Server-Sent Events (SSE) for browser clients
- Efficient delta updates to minimize bandwidth

### 3.2 User Interface

#### 3.2.1 Activity Item
```html
<div class="activity-item" data-importance="{{event.is_important}}">
  <div class="activity-icon" style="color: {{event.color}}">
    {{event.icon}}
  </div>
  <div class="activity-content">
    <div class="activity-message">{{event.message}}</div>
    <div class="activity-meta">
      <time datetime="{{event.timestamp}}">{{event.timestamp|relative_time}}</time>
      {% if event.entity_url %}
        • <a href="{{event.entity_url}}">{{event.entity_reference}}</a>
      {% endif %}
    </div>
  </div>
</div>
```

#### 3.2.2 Filtering and Search
- Filter by event type
- Filter by user
- Filter by date range
- Full-text search across activity messages

## 4. Implementation

### 4.1 Backend Services

#### 4.1.1 Event Storage
```python
class ActivityRepository:
    async def save_event(self, event: ActivityEvent) -> None:
        """Save event to the database with JSONB storage for metadata."""
        query = """
        INSERT INTO activity_events (
            id, event_type, actor_id, timestamp,
            entity_type, entity_id, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await db.execute(query, (
            str(event.id),
            event.event_type,
            str(event.actor_id),
            event.timestamp,
            event.entity_type,
            str(event.entity_id),
            json.dumps(event.metadata)
        ))

    async def get_recent_activities(
        self,
        limit: int = 50,
        before: Optional[datetime] = None,
        filters: Optional[Dict] = None
    ) -> List[ActivityEvent]:
        """Retrieve recent activities with optional filtering."""
        query = """
        SELECT * FROM activity_events
        WHERE 1=1
        """
        params = []
        
        if before:
            query += " AND timestamp < ${}"
            params.append(before)
            
        if filters:
            if 'event_types' in filters:
                query += f" AND event_type = ANY(${len(params) + 1}::text[])"
                params.append(filters['event_types'])
                
            if 'user_id' in filters:
                query += f" AND actor_id = ${len(params) + 1}"
                params.append(str(filters['user_id']))
        
        query += " ORDER BY timestamp DESC LIMIT ${}"
        params.append(limit)
        
        rows = await db.fetch(query, *params)
        return [self._row_to_event(row) for row in rows]
```

### 4.2 Frontend Implementation

#### 4.2.1 Real-time Subscription
```javascript
class ActivityStream {
  constructor() {
    this.events = [];
    this.subscribers = new Set();
    this.connection = null;
  }

  async connect() {
    this.connection = new WebSocket(ACTIVITY_WS_URL);
    
    this.connection.onmessage = (event) => {
      const activity = JSON.parse(event.data);
      this.events.unshift(activity);
      this.notifySubscribers();
    };
    
    this.connection.onclose = () => {
      setTimeout(() => this.connect(), 5000); // Reconnect after delay
    };
    
    // Load initial batch
    await this.loadMore();
  }
  
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }
  
  notifySubscribers() {
    for (const callback of this.subscribers) {
      callback([...this.events]);
    }
  }
  
  async loadMore(before) {
    const params = new URLSearchParams();
    if (before) params.set('before', before.toISOString());
    
    const response = await fetch(`/api/activities?${params}`);
    const newEvents = await response.json();
    
    this.events = [...this.events, ...newEvents];
    this.notifySubscribers();
  }
}
```

## 5. Performance Considerations

### 5.1 Scaling Strategies
- **Pagination**: Load activities in chunks (e.g., 50 at a time)
- **Lazy Loading**: Load older activities on demand
- **WebSocket Optimization**: Only send deltas for real-time updates
- **Database Indexing**: Optimize for common query patterns

### 5.2 Caching
- **In-Memory Cache**: Cache recent activities
- **Materialized Views**: Pre-compute common aggregations
- **CDN Caching**: Cache public activity feeds

## 6. Related Components

### 6.1 Integration Points
- **Task Management**: Task creation/updates
- **User Notifications**: Important activity alerts
- **Search Indexing**: Make activities searchable
- **Analytics**: Usage patterns and trends

### 6.2 Dependencies
- Message Broker (e.g., Redis, Kafka)
- Real-time Transport (WebSockets, SSE)
- Database with JSON support
- Caching layer

## 7. Future Enhancements

### 7.1 Planned Features
- **Rich Media Support**: Embed images/videos in activities
- **Reactions**: Like/emoji reactions to activities
- **Threaded Comments**: Discussions on activity items
- **Custom Event Types**: User-defined activity types

### 7.2 Research Areas
- Activity scoring and prioritization
- Automated activity summarization
- Predictive activity suggestions
- Integration with external activity sources
