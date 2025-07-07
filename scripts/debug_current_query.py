#!/usr/bin/env python
"""Debug what the current query is returning."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository
import psycopg2

print("=== CURRENT QUERY DEBUG ===\n")

# Check what time range is being used
now = datetime.now()
print(f"Current time: {now}")
print(f"Today start: {datetime.combine(datetime.today(), datetime.min.time())}")
print(f"Today end: {datetime.combine(datetime.today(), datetime.max.time())}")

# With 8 hour offset
offset_start = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=8)
offset_end = datetime.combine(datetime.today(), datetime.max.time()) + timedelta(hours=8)
print(f"\nWith +8h offset:")
print(f"Query start: {offset_start}")
print(f"Query end: {offset_end}")

# Check database directly
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres",
    password="mysecretpassword"
)
cursor = conn.cursor()

# Count entities in different time ranges
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        MIN(COALESCE(created_at, file_created_at)) as earliest,
        MAX(COALESCE(created_at, file_created_at)) as latest
    FROM entities
    WHERE COALESCE(created_at, file_created_at) IS NOT NULL
""")

total, earliest, latest = cursor.fetchone()
print(f"\nDatabase contents:")
print(f"Total entities: {total}")
print(f"Earliest: {earliest}")
print(f"Latest: {latest}")

# Count for "today" with offset
cursor.execute("""
    SELECT COUNT(*) 
    FROM entities
    WHERE COALESCE(created_at, file_created_at) >= %s 
    AND COALESCE(created_at, file_created_at) <= %s
""", (offset_start, offset_end))

today_count = cursor.fetchone()[0]
print(f"\nEntities for 'today' with +8h offset: {today_count}")

# Try without offset (normal today)
cursor.execute("""
    SELECT COUNT(*) 
    FROM entities
    WHERE COALESCE(created_at, file_created_at) >= %s 
    AND COALESCE(created_at, file_created_at) <= %s
""", (
    datetime.combine(datetime.today(), datetime.min.time()),
    datetime.combine(datetime.today(), datetime.max.time())
))

normal_today = cursor.fetchone()[0]
print(f"Entities for normal 'today': {normal_today}")

# Check what MetricsRepository would return
print("\nChecking MetricsRepository...")
metrics_repo = MetricsRepository()
summary = metrics_repo.get_metrics_summary(
    datetime.combine(datetime.today(), datetime.min.time()),
    datetime.combine(datetime.today(), datetime.max.time())
)
print(f"MetricsRepository total_activities: {summary.get('total_activities', 'N/A')}")

cursor.close()
conn.close()