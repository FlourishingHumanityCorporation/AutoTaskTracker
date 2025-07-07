#!/usr/bin/env python
"""Debug why window titles aren't showing in UI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository

print("=== UI DISPLAY DEBUG ===\n")

# Get task groups like the dashboard does
task_repo = TaskRepository()
end_date = datetime.now()
start_date = end_date - timedelta(hours=2)  # Last 2 hours only

print(f"Dashboard query range: {start_date} to {end_date}")

# Get task groups
task_groups = task_repo.get_task_groups(
    start_date=start_date,
    end_date=end_date,
    min_duration_minutes=1
)

print(f"\nFound {len(task_groups)} task groups")

# Check first few groups
for i, group in enumerate(task_groups[:3]):
    print(f"\nGroup {i+1}:")
    print(f"  window_title: '{group.window_title}'")
    print(f"  category: {group.category}")
    print(f"  duration: {group.duration_minutes} min")
    print(f"  tasks count: {len(group.tasks)}")
    
    # Check first task details
    if group.tasks:
        task = group.tasks[0]
        print(f"\n  First task details:")
        print(f"    task.title: '{task.title}'")
        print(f"    task.window_title: '{task.window_title}'")
        print(f"    task.category: {task.category}")
        print(f"    task.timestamp: {task.timestamp}")

# The issue might be in the grouping logic
print("\n\nChecking window normalization...")

# Check if window titles are being normalized to "Unknown"
from autotasktracker.dashboards.data.core.window_normalizer import get_window_normalizer
normalizer = get_window_normalizer()

test_windows = ["Chrome", "Terminal", "• paulrohde — * Image Mismatch — claude"]
for window in test_windows:
    normalized = normalizer.normalize(window)
    print(f"  '{window}' -> '{normalized}'")