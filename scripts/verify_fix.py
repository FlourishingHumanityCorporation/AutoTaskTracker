#!/usr/bin/env python
"""Verify the timezone fix is working correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository
import psycopg2

print("=== VERIFYING TIMEZONE FIX ===\n")

# Current time
now = datetime.now()
print(f"Current local time: {now}")

# Repository test
task_repo = TaskRepository()
start = now - timedelta(hours=2)
end = now

print(f"\nQuerying for tasks from {start.strftime('%H:%M')} to {end.strftime('%H:%M')}")

tasks = task_repo.get_tasks_for_period(start, end, limit=5)
print(f"Found {len(tasks)} tasks")

for i, task in enumerate(tasks):
    print(f"\nTask {i+1}:")
    print(f"  Window: {task.window_title}")
    print(f"  Category: {task.category}")
    print(f"  Display time: {task.timestamp.strftime('%H:%M:%S')}")
    print(f"  Screenshot: {os.path.basename(task.screenshot_path) if task.screenshot_path else 'None'}")

# Direct DB check
print("\n\nDirect DB validation:")
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres",
    password="mysecretpassword"
)
cursor = conn.cursor()

# Check with +7h offset
adjusted_start = start + timedelta(hours=7)
adjusted_end = end + timedelta(hours=7)

cursor.execute("""
    SELECT COUNT(*) 
    FROM entities e
    LEFT JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'active_window'
    WHERE COALESCE(e.created_at, e.file_created_at) >= %s 
    AND COALESCE(e.created_at, e.file_created_at) <= %s
""", (adjusted_start, adjusted_end))

count = cursor.fetchone()[0]
print(f"Entities in adjusted range: {count}")

# Sample window titles
cursor.execute("""
    SELECT DISTINCT m.value
    FROM metadata_entries m
    JOIN entities e ON m.entity_id = e.id
    WHERE m.key = 'active_window'
    AND COALESCE(e.created_at, e.file_created_at) >= %s 
    AND COALESCE(e.created_at, e.file_created_at) <= %s
    AND m.value IS NOT NULL
    LIMIT 5
""", (adjusted_start, adjusted_end))

windows = cursor.fetchall()
print(f"\nSample window titles:")
for window in windows:
    print(f"  - {window[0]}")

cursor.close()
conn.close()

print("\n✓ Verification complete")