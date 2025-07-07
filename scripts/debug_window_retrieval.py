#!/usr/bin/env python
"""Debug why window titles aren't being retrieved."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository
import psycopg2

print("=== WINDOW TITLE RETRIEVAL DEBUG ===\n")

# Test the repository query
task_repo = TaskRepository()

# Get current time range
end_date = datetime.now()
start_date = end_date - timedelta(hours=1)

print(f"Query range: {start_date} to {end_date}")

# Get tasks
tasks = task_repo.get_tasks_for_period(start_date, end_date, limit=10)

print(f"\nFound {len(tasks)} tasks")
for i, task in enumerate(tasks[:5]):
    print(f"\nTask {i+1}:")
    print(f"  Title: {task.title}")
    print(f"  Window: {task.window_title}")
    print(f"  Category: {task.category}")
    print(f"  Timestamp: {task.timestamp}")
    print(f"  Screenshot: {os.path.basename(task.screenshot_path) if task.screenshot_path else 'None'}")

# Check database directly with the adjusted query
print("\n\nDirect database check with adjusted time:")
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres",
    password="mysecretpassword"
)
cursor = conn.cursor()

# Use the same adjusted time as repository
adjusted_start = start_date + timedelta(hours=8)
adjusted_end = end_date + timedelta(hours=8)

cursor.execute("""
    SELECT 
        e.id,
        COALESCE(e.created_at, e.file_created_at) as timestamp,
        m2.value as active_window,
        m4.value as category
    FROM entities e
    LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
    LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
    WHERE COALESCE(e.created_at, e.file_created_at) >= %s 
    AND COALESCE(e.created_at, e.file_created_at) <= %s
    ORDER BY COALESCE(e.created_at, e.file_created_at) DESC
    LIMIT 5
""", (adjusted_start, adjusted_end))

results = cursor.fetchall()
print(f"\nDirect query returned {len(results)} rows:")
for entity_id, timestamp, window, category in results:
    print(f"  Entity {entity_id}: window='{window}', category='{category}'")

cursor.close()
conn.close()