#!/usr/bin/env python
"""Debug the current screenshot being shown in the dashboard."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository

# Get very recent data - last 10 minutes
end_date = datetime.now()
start_date = end_date - timedelta(minutes=10)

print(f"=== CURRENT SCREENSHOT DEBUG ===")
print(f"Looking at last 10 minutes: {start_date.strftime('%H:%M')} - {end_date.strftime('%H:%M')}\n")

task_repo = TaskRepository()

# Get individual tasks first
tasks = task_repo.get_tasks_for_period(start_date, end_date)
print(f"Found {len(tasks)} individual tasks in the last 10 minutes")

if tasks:
    print("\nMost recent 5 tasks:")
    for i, task in enumerate(tasks[-5:]):
        time_str = task.timestamp.strftime('%H:%M:%S')
        filename = os.path.basename(task.screenshot_path) if task.screenshot_path else "None"
        window = task.window_title or "Unknown"
        print(f"  {time_str}: {window[:50]}")
        print(f"            Screenshot: {filename}")
        
# Now check task groups
task_groups = task_repo.get_task_groups(
    start_date=start_date,
    end_date=end_date,
    min_duration_minutes=0  # Show all groups
)

print(f"\nFound {len(task_groups)} task groups")

if task_groups:
    print("\nMost recent group:")
    group = task_groups[-1]  # Last group
    print(f"  Window: {group.window_title}")
    print(f"  Time: {group.start_time.strftime('%H:%M')} - {group.end_time.strftime('%H:%M')}")
    print(f"  Tasks in group: {len(group.tasks)}")
    
    if group.tasks:
        print(f"\n  First task: {group.tasks[0].timestamp.strftime('%H:%M:%S')}")
        print(f"              {os.path.basename(group.tasks[0].screenshot_path) if group.tasks[0].screenshot_path else 'None'}")
        print(f"  Last task:  {group.tasks[-1].timestamp.strftime('%H:%M:%S')}")
        print(f"              {os.path.basename(group.tasks[-1].screenshot_path) if group.tasks[-1].screenshot_path else 'None'}")
        
        # Check what the dashboard would show
        dashboard_screenshot = group.tasks[-1].screenshot_path if group.tasks else None
        print(f"\n  Dashboard will show: {os.path.basename(dashboard_screenshot) if dashboard_screenshot else 'None'}")
        
        # Show the actual path
        if dashboard_screenshot:
            print(f"  Full path: {dashboard_screenshot}")
            print(f"  File exists: {os.path.exists(dashboard_screenshot)}")

# Look for a specific window if you know what should be showing
print("\n\nLooking for specific windows...")
all_groups = task_repo.get_task_groups(
    start_date=end_date - timedelta(hours=2),
    end_date=end_date,
    min_duration_minutes=1
)

for group in all_groups:
    if "Chrome" in group.window_title or "Terminal" in group.window_title or "Code" in group.window_title:
        print(f"\nFound: {group.window_title}")
        print(f"  Time: {group.start_time.strftime('%H:%M')} - {group.end_time.strftime('%H:%M')}")
        print(f"  Duration: {group.duration_minutes:.1f} minutes")
        if group.tasks:
            print(f"  Would show: {os.path.basename(group.tasks[-1].screenshot_path) if group.tasks[-1].screenshot_path else 'None'}")