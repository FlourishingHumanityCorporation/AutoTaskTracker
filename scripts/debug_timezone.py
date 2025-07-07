#!/usr/bin/env python
"""Debug timezone conversion issues."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
import pytz
from autotasktracker.core.timezone_manager import get_timezone_manager
from autotasktracker.dashboards.data.repositories import TaskRepository
from autotasktracker.pensieve.postgresql_adapter import PostgreSQLAdapter
import psycopg2

print("=== TIMEZONE DEBUG ===\n")

# 1. Check system timezone
print("1. System Timezone:")
tz_mgr = get_timezone_manager()
print(f"   UTC offset: {tz_mgr._utc_offset_hours} hours")
print(f"   Current local time: {datetime.now()}")
print(f"   Current UTC time: {datetime.now(timezone.utc)}")
print(f"   Difference: {(datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 3600} hours")

# 2. Check database timestamps
print("\n2. Database Timestamps:")
try:
    # Direct PostgreSQL connection
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database="autotasktracker",
        user="postgres",
        password="mysecretpassword"
    )
    cursor = conn.cursor()
    
    # Get sample recent entries
    cursor.execute("""
        SELECT id, created_at, file_created_at, file_path
        FROM entities 
        WHERE created_at IS NOT NULL
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    print("   Recent entries with created_at:")
    for row in cursor.fetchall():
        id, created_at, file_created_at, file_path = row
        filename = os.path.basename(file_path) if file_path else "N/A"
        print(f"   ID {id}: created_at={created_at}, file_created_at={file_created_at}")
        print(f"           file: {filename}")
        
        # Parse expected time from filename
        if filename and filename.startswith("screenshot_"):
            parts = filename.replace("screenshot_", "").replace(".png", "").split("_")
            if len(parts) >= 2:
                date_str = parts[0]
                time_str = parts[1]
                expected_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                print(f"           expected from filename: {expected_time}")
                
                # Compare
                if created_at:
                    db_time_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if db_time_str != expected_time:
                        print(f"           ⚠️ MISMATCH: DB has {db_time_str}, filename suggests {expected_time}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"   ERROR: {e}")

# 3. Check task repository conversions
print("\n3. Task Repository Timezone Handling:")
try:
    task_repo = TaskRepository()
    
    # Get a recent task
    recent_tasks = task_repo.get_tasks(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now(),
        limit=1
    )
    
    if recent_tasks:
        task = recent_tasks[0]
        print(f"   Task ID: {task.id}")
        print(f"   Timestamp (task object): {task.timestamp}")
        print(f"   Timestamp type: {type(task.timestamp)}")
        print(f"   Timestamp timezone: {task.timestamp.tzinfo if hasattr(task.timestamp, 'tzinfo') else 'No tzinfo'}")
        
        # Check display format
        from autotasktracker.dashboards.components.filters import format_timestamp
        formatted = format_timestamp(task.timestamp)
        print(f"   Formatted for display: {formatted}")
        
except Exception as e:
    print(f"   ERROR: {e}")

# 4. Check for timezone in conversion
print("\n4. Timezone Conversion Analysis:")
# Check a specific time
test_time = datetime(2025, 7, 6, 19, 20, 0)  # What we expect
print(f"   Expected local time: {test_time}")

# What might be in DB (stored as UTC but actually local time)
db_time = test_time.replace(tzinfo=timezone.utc)  # If DB thinks local time is UTC
print(f"   If DB stored as UTC: {db_time}")

# Convert back to local using timezone manager
back_to_local = tz_mgr.to_local(db_time)
print(f"   Converted back to local: {back_to_local}")

# Calculate difference
if hasattr(back_to_local, 'replace'):
    back_naive = back_to_local.replace(tzinfo=None) if back_to_local.tzinfo else back_to_local
    diff_hours = (back_naive - test_time).total_seconds() / 3600
    print(f"   Difference: {diff_hours} hours")

