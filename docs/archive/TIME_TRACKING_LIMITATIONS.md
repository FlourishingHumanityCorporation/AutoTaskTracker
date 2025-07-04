# ⚠️ Current Time Tracking Limitations & Solutions

## Current Issues

### 1. **Task Definition Problems**
- **Issue**: Tasks are defined by exact window title match
- **Example**: "Document.docx - Word" and "Document2.docx - Word" are treated as different tasks
- **Impact**: Overestimates task switching, fragments time

### 2. **Imprecise Start/End Times**
- **Issue**: 
  - Start time = first screenshot timestamp
  - End time = last screenshot timestamp
  - No consideration for work that happens between screenshots
- **Example**: If you work 10 minutes but only 2 screenshots captured, shows as 4 seconds
- **Impact**: Can underestimate actual time by up to 4 seconds per screenshot

### 3. **No Idle Detection**
- **Issue**: Can't distinguish between active work and leaving computer
- **Example**: 30-minute lunch break counted as "working" on last active window
- **Impact**: Overestimates time on tasks before breaks

### 4. **Poor Task Grouping**
- **Issue**: Every browser tab is a different "task"
- **Example**: Research across 10 websites = 10 different tasks
- **Impact**: Makes time reports fragmented and hard to use

## Proposed Solutions

### 1. **Smart Task Normalization**
```python
# Group similar activities
"README.md - Visual Studio Code" → "Coding: AutoTaskTracker"
"Gmail - Google Chrome" → "Email"
"AutoTaskTracker - Slack" → "Communication: Slack"
```

### 2. **Idle Detection Algorithm**
```python
# Detect breaks in screenshot pattern
if time_between_screenshots > 2 * normal_interval:
    mark_as_idle()
    end_previous_task_early()
```

### 3. **Activity Confidence Scoring**
- High confidence: Continuous screenshots (4-8 sec apart)
- Medium confidence: Some gaps (8-30 sec)
- Low confidence: Large gaps (>30 sec)

### 4. **Improved Duration Calculation**
```python
# Current (wrong)
duration = last_screenshot_time - first_screenshot_time

# Improved
duration = sum(active_periods) + (screenshot_count * avg_seconds_per_screenshot)
```

## Quick Fixes You Can Do Now

### 1. **Adjust Grouping Interval**
In the Task Board sidebar, increase "Group Similar Tasks" to 10-15 minutes

### 2. **Use Categories Instead of Individual Tasks**
Focus on the category summaries (Development, Communication, etc.) which are more accurate

### 3. **Manual Editing for Timesheets**
Export to CSV and manually merge similar tasks:
- All VS Code windows → "Development"
- All browser tabs for same project → "Research"

### 4. **Set Boundaries**
Take a screenshot of a "break" screen when stepping away to clearly mark work boundaries

## Future Improvements Needed

1. **Machine Learning Task Classification**
   - Learn your patterns over time
   - Automatically group related activities
   - Detect project contexts

2. **Keyboard/Mouse Activity Integration**
   - Use input activity to detect true idle time
   - More accurate active time calculation

3. **Manual Corrections Interface**
   - Allow marking "I was away" periods
   - Merge tasks after the fact
   - Add project tags

4. **Smarter Screenshot Intervals**
   - Increase frequency during active work
   - Decrease when idle detected
   - Adaptive based on activity patterns

## Current Workarounds

For now, the time tracking works best when you:
1. **Stay in one application** for extended periods
2. **Use the category summaries** rather than individual task times
3. **Export and post-process** the data for accurate timesheets
4. **Consider it directionally correct** rather than minute-perfect

The system gives you a good picture of where your time goes, but isn't yet precise enough for exact billing without manual review.