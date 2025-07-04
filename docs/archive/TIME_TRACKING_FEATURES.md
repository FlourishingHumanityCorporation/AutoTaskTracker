# ⏱️ Time Tracking Features in AutoTaskTracker

## Yes! We have comprehensive time tracking:

### 1. **Automatic Time Calculation**
- Tracks time spent on each task/application
- Groups continuous work into sessions
- Handles interruptions intelligently (5-minute gap threshold)

### 2. **Three Dashboards for Different Views**

#### 📋 Task Board (http://localhost:8502)
- Real-time view of current activities
- Shows duration for each task group
- Live updates every 30 seconds

#### 📊 Analytics Dashboard (http://localhost:8503)
- Hourly productivity patterns
- Focus session analysis
- Category-based time distribution
- Weekly/monthly trends

#### ⏱️ Time Tracker (http://localhost:8504)
- **Detailed time logs for every task**
- **Exact start/end times**
- **Total hours per task/app**
- **Timeline visualization**
- **Export to CSV for timesheets**

### 3. **Time Tracking Features**

- **Task-Level Tracking**: See time spent on each window/document
- **Application Tracking**: Time per application (VS Code, Chrome, etc.)
- **Category Summaries**: Development, Communication, Meetings, etc.
- **Session Detection**: Identifies continuous work periods
- **Daily/Weekly Views**: Track patterns over time

### 4. **Export Options**

The Time Tracker dashboard provides:
- **CSV Export**: Detailed sessions with timestamps
  ```csv
  task,application,category,start,end,duration_minutes
  "AutoTaskTracker.py","VS Code","Development",2025-01-03 14:30:00,2025-01-03 15:45:00,75.0
  ```
- **JSON Summary**: High-level statistics
- **Time Reports**: For client billing or productivity analysis

### 5. **How Time is Calculated**

1. **Screenshot Intervals**: Every 4 seconds by default
2. **Session Grouping**: Same task + <5 min gap = one session
3. **Duration Calculation**: End time - Start time of session
4. **Minimum Duration**: At least 0.1 min per screenshot

### 6. **Quick Access**

```bash
# View time tracking directly
open http://localhost:8504

# Or through the launcher
./autotask.py
# Then: open time
```

### 7. **Example Use Cases**

- **Freelancers**: Export time logs for client invoices
- **Employees**: Track time on different projects
- **Students**: See how much time spent studying vs browsing
- **Anyone**: Understand where your time really goes

The time tracking is automatic and passive - just let AutoTaskTracker run and it will build a complete picture of how you spend your time!