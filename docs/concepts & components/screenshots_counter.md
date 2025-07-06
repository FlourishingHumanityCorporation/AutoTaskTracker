# Screenshots Counter Component

## 1. Overview

### 1.1 Conceptual Definition
The Screenshots Counter is a monitoring component that tracks and displays statistics about the screenshots captured by the AutoTaskTracker system. It provides insights into the volume, timing, and processing status of screenshots, which are fundamental to the system's task discovery capabilities.

### 1.2 Purpose
- Monitor the health and activity of the screenshot capture system
- Provide visibility into screenshot processing pipeline
- Help identify potential issues with screenshot capture or storage
- Enable performance monitoring and capacity planning
- Support debugging and system maintenance

## 2. Technical Specifications

### 2.1 Component Architecture
```
┌───────────────────────────────────────────────────────────────┐
│                    Screenshots Dashboard                      │
├───────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐     ┌─────────────────────────┐  │
│  │   Today's Screenshots   │     │  Screenshot Statistics  │  │
│  │   ┌─────────────────┐   │     │  ┌───────────────────┐  │  │
│  │   │    1,247       │   │     │  │ Total:   25,812   │  │  │
│  │   │   Screenshots  │   │     │  │ Today:   1,247    │  │  │
│  │   └─────────────────┘   │     │  │ Avg/Day: 1,075    │  │  │
│  └─────────────────────────┘     │  │ Failed:  12       │  │  │
│                                  └───────────────────┘  │
├───────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Capture Timeline                     │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │  █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄  │   │  │
│  │  │  ████████████████████████████████████████████  │   │  │
│  │  └───────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 Data Model

#### 2.2.1 Data Sources
- **Screenshot Metadata Table**: Stores information about each captured screenshot
- **Processing Queue**: Tracks screenshots waiting for OCR/analysis
- **Storage System**: Local or cloud storage where screenshots are saved
- **Error Logs**: Records any failures in the screenshot capture process

#### 2.2.2 Data Structure
```python
class ScreenshotStats:
    total_count: int
    today_count: int
    daily_average: float
    failed_count: int
    last_capture: datetime
    storage_usage: str  # e.g., "4.2 GB"
    capture_rate: float  # screenshots per hour
    
class CaptureSession:
    session_id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    screenshots_taken: int
    errors: List[Dict[str, Any]]
    system_metrics: Dict[str, Any]
```

## 3. Component Details

### 3.1 Core Metrics

#### 3.1.1 Screenshot Volume
- **Total Captured**: Lifetime count of all screenshots
- **Today's Count**: Screenshots captured in the current calendar day
- **Capture Rate**: Screenshots per hour/minute based on configuration
- **Storage Usage**: Total disk space used by screenshots

#### 3.1.2 Quality Metrics
- **Success Rate**: Percentage of successful captures
- **Average Size**: Average file size of screenshots
- **Resolution Stats**: Most common screen resolutions captured
- **Retention Status**: Number of screenshots marked for deletion/archival

#### 3.1.3 Performance Metrics
- **Capture Latency**: Time taken to capture and save each screenshot
- **Processing Time**: Time from capture to processing completion
- **Queue Depth**: Number of screenshots waiting for processing

### 3.2 Visual Components

#### 3.2.1 Dashboard Widgets
- **Counter Display**: Large, prominent counter showing today's screenshot count
- **Trend Graph**: Historical view of screenshot volume
- **Status Indicators**: Visual cues for system health
- **Storage Usage Bar**: Visual representation of storage consumption

#### 3.2.2 Detailed Views
- **Timeline View**: Chronological display of screenshot captures
- **Error Log**: Detailed view of any capture failures
- **Storage Explorer**: Browse and manage stored screenshots

## 4. Implementation

### 4.1 Data Collection

#### 4.1.1 Capture Monitoring
```python
def track_screenshot_capture(screenshot_metadata: Dict[str, Any]) -> None:
    """Record a new screenshot capture event."""
    with DatabaseManager() as db:
        db.execute("""
            INSERT INTO screenshot_metrics (
                timestamp, 
                file_size, 
                resolution,
                capture_duration,
                status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.utcnow(),
            screenshot_metadata['size'],
            f"{screenshot_metadata['width']}x{screenshot_metadata['height']}",
            screenshot_metadata.get('capture_duration_ms'),
            'success'
        ))
        update_daily_stats()
```

#### 4.1.2 Statistics Aggregation
```python
def update_daily_stats() -> None:
    """Update aggregated daily statistics."""
    today = date.today()
    with DatabaseManager() as db:
        # Get today's count
        db.execute("""
            SELECT COUNT(*) 
            FROM screenshot_metrics 
            WHERE DATE(timestamp) = ?
        """, (today,))
        today_count = db.fetchone()[0]
        
        # Update daily stats
        db.execute("""
            INSERT OR REPLACE INTO daily_screenshot_stats (
                date, 
                count,
                last_updated
            ) VALUES (?, ?, ?)
        """, (today, today_count, datetime.utcnow()))
```

### 4.2 Storage Management

#### 4.2.1 Retention Policy
```python
def apply_retention_policy(max_age_days: int = 30) -> None:
    """Remove screenshots older than the specified number of days."""
    cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
    
    with DatabaseManager() as db:
        # Get list of files to delete
        db.execute("""
            SELECT file_path 
            FROM screenshot_metadata 
            WHERE timestamp < ? 
            AND status = 'processed'
        """, (cutoff_date,))
        
        for (file_path,) in db.fetchall():
            try:
                os.remove(file_path)
                db.execute("""
                    UPDATE screenshot_metadata 
                    SET status = 'deleted' 
                    WHERE file_path = ?
                """, (file_path,))
            except Exception as e:
                logging.error(f"Failed to delete {file_path}: {e}")
```

## 5. Performance Considerations

### 5.1 Database Optimization
- **Indexing**:
  ```sql
  CREATE INDEX idx_screenshot_timestamp ON screenshot_metrics(timestamp);
  CREATE INDEX idx_screenshot_status ON screenshot_metrics(status);
  ```
- **Partitioning**: Consider partitioning by date for large datasets
- **Materialized Views**: Pre-compute common aggregations

### 5.2 Storage Optimization
- **Compression**: Implement lossless compression for stored screenshots
- **Tiered Storage**: Move older screenshots to cheaper storage
- **Deduplication**: Identify and remove duplicate screenshots

## 6. Related Components

### 6.1 Integration Points
- **Screenshot Capture Service**: Primary source of screenshot data
- **Task Processor**: Consumes screenshots for task extraction
- **Storage Manager**: Handles physical storage of screenshot files
- **Alerting System**: Notifies of any issues with screenshot capture

### 6.2 Dependencies
- Database access layer
- File system utilities
- System monitoring tools

## 7. Monitoring and Alerts

### 7.1 Key Metrics to Monitor
- Capture failure rate
- Storage capacity
- Processing queue depth
- Capture latency

### 7.2 Alert Conditions
- Failed captures > 5% of total
- Storage > 90% capacity
- Queue depth > 100 items
- No new screenshots in last 15 minutes

## 8. Future Enhancements

### 8.1 Planned Features
- **Smart Compression**: Adaptive compression based on content
- **Automatic Cleanup**: More sophisticated retention policies
- **Quality Metrics**: Automated quality assessment of screenshots

### 8.2 Research Areas
- Machine learning for anomaly detection
- Predictive capacity planning
- Automated screenshot categorization
