# AutoTaskTracker Metrics Explained

## Dashboard Metrics Definitions

### 📊 Total Activities
- **What it measures**: Total number of screenshots captured in the selected time period
- **Data source**: Count of entries in the `entities` table
- **Example**: "2,425" means 2,425 screenshots were taken

### 📅 Active Days  
- **What it measures**: Number of unique calendar days that have at least one screenshot
- **Why it shows "1" for today**: Because you're viewing "Today" filter - there's only one unique date (today)
- **Calculation**: `COUNT(DISTINCT DATE(timestamp))` from screenshots
- **Example**: If viewing a week with activity on Mon, Wed, Fri → Active Days = 3

### 🪟 Unique Windows
- **What it measures**: Number of different application windows captured
- **Data source**: Distinct `active_window` values from metadata
- **Example**: "227" means you used 227 different app windows/tabs

### 🏷️ Categories
- **What it measures**: Number of distinct activity categories detected by AI
- **Common categories**: Development, Communication, Research, etc.
- **Example**: "6" means activities were classified into 6 different categories

### 📈 Daily Average
- **What it measures**: Average screenshots per active day
- **Calculation**: Total Activities ÷ Active Days
- **Example**: 2,425 activities ÷ 1 day = 2,425 daily average

### 🔴 Events (Real-time Status)
- **What it measures**: Number of real-time processing events (NOT total screenshots)
- **Includes**: New screenshot notifications, metadata updates, AI processing events
- **Why it's different**: This is a streaming event counter, not a database count
- **Example**: "20" might mean 20 real-time events processed in current session

## Understanding the Numbers

### Why "Active Days = 1" for Today
When you select "Today" as the time filter:
- Start: 2025-07-06 00:00:00
- End: 2025-07-06 23:59:59
- Unique dates in range: Just one (2025-07-06)
- Therefore: Active Days = 1

### Screenshot Frequency
- Default capture: Every 30 seconds when active
- 2,425 screenshots ÷ 24 hours = ~101 per hour
- This suggests active computer use for ~10-12 hours

### Events vs Activities
- **Activities/Screenshots**: Stored data in database (permanent record)
- **Events**: Real-time processing notifications (temporary, session-based)
- Events reset when dashboard restarts, activities persist in database