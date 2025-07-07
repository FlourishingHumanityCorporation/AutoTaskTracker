#!/usr/bin/env python
"""Verify that screenshots are now properly grouped by window title."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository

# Get task groups from the last hour
end_date = datetime.now()
start_date = end_date - timedelta(hours=1)

print(f"=== SCREENSHOT GROUPING VERIFICATION ===")
print(f"Time range: {start_date.strftime('%H:%M')} - {end_date.strftime('%H:%M')}\n")

task_repo = TaskRepository()
task_groups = task_repo.get_task_groups(
    start_date=start_date,
    end_date=end_date,
    min_duration_minutes=1
)

print(f"Found {len(task_groups)} task groups (min 1 minute duration)\n")

# Show each group
for i, group in enumerate(task_groups[:10]):  # Show first 10
    print(f"Group {i+1}: {group.window_title}")
    print(f"  Category: {group.category}")
    print(f"  Duration: {group.duration_minutes:.1f} minutes")
    print(f"  Tasks: {len(group.tasks)}")
    print(f"  Time: {group.start_time.strftime('%H:%M')} - {group.end_time.strftime('%H:%M')}")
    
    if group.tasks and group.tasks[-1].screenshot_path:
        filename = os.path.basename(group.tasks[-1].screenshot_path)
        print(f"  Latest screenshot: {filename}")
    print()

# Count by window type
window_counts = {}
for group in task_groups:
    window = group.window_title
    if window not in window_counts:
        window_counts[window] = 0
    window_counts[window] += 1

print("\nWindow title distribution:")
for window, count in sorted(window_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {window}: {count} groups")

# Check for "Unknown Activity" groups
unknown_count = sum(1 for g in task_groups if "Unknown" in g.window_title)
print(f"\nGroups with 'Unknown' in title: {unknown_count}/{len(task_groups)}")