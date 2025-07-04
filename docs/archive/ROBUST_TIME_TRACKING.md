# 🧠 Robust Context-Aware Time Tracking

## Overview

I've created a **Smart Time Tracker** that understands task context and user behavior patterns. It solves the exact problem you described:

- **Tracks separate emails** to different people as different tasks
- **Groups supporting activities** (research, file lookups) with the main task
- **Detects task returns** when you go back to an email after research
- **Focuses on the main window** not every tab switch

## Access the Smart Tracker

```bash
# Direct URL
http://localhost:8505

# Or via launcher
./autotask.py
# Then select "Smart Time Tracker"
```

## How It Works

### 1. **Smart Task Detection**

The tracker identifies tasks by understanding context:

```
Email to Sarah → Research on LinkedIn → Back to Email to Sarah
= One task: "Email: Meeting with Sarah" (3 minutes total)

Email to Tom → Check Excel spreadsheet → Back to Email to Tom  
= One task: "Email: Budget Report for Tom" (2 minutes total)
```

### 2. **Context Understanding**

For each window, it extracts:
- **Task type**: Email, Coding, Document, Meeting, etc.
- **Subject/Person**: Who the email is to, what document, which project
- **Supporting apps**: Browser for research, Terminal for coding, etc.

### 3. **Task Boundaries**

Creates new tasks when:
- ✅ Different email recipient (Sarah → Tom)
- ✅ Different document (report.docx → proposal.docx)
- ✅ Different project (projectA/main.py → projectB/test.py)
- ✅ More than 5 minutes away from previous task

Continues same task when:
- ✅ Return to same email/document within 5 minutes
- ✅ Use supporting app (Chrome while writing email)
- ✅ Quick reference lookup (Excel while composing report)

### 4. **Real Example**

Your workflow:
```
10:00 - Gmail: Compose email to Client A about Project X
10:02 - Chrome: Research Project X details
10:03 - Gmail: Continue email to Client A
10:05 - Gmail: New email to Manager about Budget
10:06 - Excel: Check budget numbers
10:07 - Gmail: Continue email to Manager
```

Traditional tracker would show: 6 different tasks ❌

Smart tracker shows: 2 tasks ✅
1. "Email: Project X to Client A" (3 min, includes research)
2. "Email: Budget to Manager" (2 min, includes Excel lookup)

## Features

### 1. **Configurable Intelligence**
- **Context Switch Threshold**: How long before considering a new task (default: 30 seconds)
- **Task Return Window**: How long you can be away and still return to a task (default: 5 minutes)
- **Minimum Task Duration**: Filter out brief window switches (default: 1 minute)

### 2. **Task Grouping Rules**

**Email Tasks**:
- Groups by recipient or subject
- Includes web research, file lookups
- Tracks compose, reply, forward separately

**Coding Tasks**:
- Groups by project/file
- Includes terminal, documentation, Stack Overflow
- Maintains context across debugging

**Document Tasks**:
- Groups by document name
- Includes research, image searches
- Tracks revisions as one task

### 3. **Visual Timeline**
- Gantt chart showing task overlaps
- Color-coded by category
- Hover for full context (all windows used)

### 4. **Smart Exports**
- **Task-based CSV**: One row per logical task
- **Detailed JSON**: Includes all context windows
- **Time reports**: Human-readable summaries

## Comparison

### Before (Window-based tracking):
```
09:00-09:01  Gmail - Compose: Meeting invite     1 min
09:01-09:02  Google Calendar                     1 min  
09:02-09:03  Gmail - Compose: Meeting invite     1 min
09:03-09:04  Slack - #general                    1 min
09:04-09:05  Gmail - Compose: Meeting invite     1 min
Total: 5 tasks, fragmented view
```

### After (Context-aware tracking):
```
09:00-09:05  Email: Meeting invite               5 min
  └── Includes: Gmail, Calendar lookup, back to Gmail
  └── Interrupted by: Quick Slack check (ignored as noise)
Total: 1 cohesive task
```

## Configuration Tips

1. **For Email Heavy Work**:
   - Set return window to 10 minutes
   - Lower context switch threshold to 20 seconds

2. **For Development**:
   - Set return window to 15 minutes (for longer research)
   - Include terminal/browser as supporting apps

3. **For Document Writing**:
   - Higher context switch threshold (60 seconds)
   - Group all research under main document

## Technical Implementation

The `context_aware_tracker.py` implements:
- Pattern matching for task extraction
- State machine for task boundaries  
- Stack-based task history for returns
- Configurable thresholds
- Smart app categorization

## Try It Now

1. Open http://localhost:8505
2. Select today's date
3. See your tasks grouped intelligently
4. Adjust thresholds to match your workflow
5. Export clean time logs

This gives you the robust, context-aware time tracking you wanted - where switching windows for research doesn't create new tasks, but switching to a different email recipient does!