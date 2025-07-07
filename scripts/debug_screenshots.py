#!/usr/bin/env python
"""Debug screenshot selection in task groups."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository

# Get recent task groups
end_date = datetime.now()
start_date = end_date - timedelta(hours=1)

print("=== SCREENSHOT DEBUG ===\n")

task_repo = TaskRepository()
task_groups = task_repo.get_task_groups(
    start_date=start_date,
    end_date=end_date,
    min_duration_minutes=1
)

print(f"Found {len(task_groups)} task groups in the last hour\n")

# Examine first few groups
for i, group in enumerate(task_groups[:5]):
    print(f"Group {i+1}: {group.window_title}")
    print(f"  Category: {group.category}")
    print(f"  Duration: {group.duration_minutes:.1f} minutes")
    print(f"  Task count: {len(group.tasks)}")
    print(f"  Time range: {group.start_time.strftime('%H:%M')} - {group.end_time.strftime('%H:%M')}")
    
    if group.tasks:
        print(f"\n  Tasks in group:")
        for j, task in enumerate(group.tasks):
            time_str = task.timestamp.strftime('%H:%M:%S')
            filename = os.path.basename(task.screenshot_path) if task.screenshot_path else "None"
            print(f"    Task {j+1}: {time_str} - {filename}")
            
            # Check if screenshot file exists
            if task.screenshot_path:
                exists = os.path.exists(task.screenshot_path)
                print(f"             File exists: {exists}")
                
                # Parse timestamp from filename
                if filename.startswith("screenshot_"):
                    parts = filename.replace("screenshot_", "").replace(".png", "").split("_")
                    if len(parts) >= 2:
                        time_part = parts[1]
                        file_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                        print(f"             Filename time: {file_time}")
        
        print(f"\n  First task screenshot: {os.path.basename(group.tasks[0].screenshot_path) if group.tasks[0].screenshot_path else 'None'}")
        print(f"  Last task screenshot:  {os.path.basename(group.tasks[-1].screenshot_path) if group.tasks[-1].screenshot_path else 'None'}")
        
        # What dashboard would select
        dashboard_selection = group.tasks[-1].screenshot_path if group.tasks else None
        print(f"  Dashboard would use:   {os.path.basename(dashboard_selection) if dashboard_selection else 'None'}")
    
    print("\n" + "-"*60 + "\n")