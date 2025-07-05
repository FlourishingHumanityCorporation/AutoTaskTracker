#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta
import os
from pathlib import Path

# Connect to database
db_path = Path.home() / '.memos' / 'database.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("🔍 Checking AutoTaskTracker Data\n")

# Check total screenshots
cursor.execute("SELECT COUNT(*) FROM entities WHERE file_type_group = 'image'")
total = cursor.fetchone()[0]
print(f"Total screenshots: {total}")

# Check today's data (with timezone)
cursor.execute("""
    SELECT 
        COUNT(*) as count,
        MIN(datetime(created_at, 'localtime')) as first,
        MAX(datetime(created_at, 'localtime')) as last
    FROM entities 
    WHERE file_type_group = 'image' 
    AND date(created_at, 'localtime') = date('now', 'localtime')
""")
today_count, first, last = cursor.fetchone()
print(f"\nToday's screenshots: {today_count}")
if today_count > 0:
    print(f"First: {first}")
    print(f"Last: {last}")

# Check last hour
cursor.execute("""
    SELECT COUNT(*) 
    FROM entities 
    WHERE file_type_group = 'image' 
    AND datetime(created_at, 'localtime') >= datetime('now', 'localtime', '-1 hour')
""")
last_hour = cursor.fetchone()[0]
print(f"\nLast hour: {last_hour} screenshots")

# Show recent windows
print("\n📱 Recent Windows:")
cursor.execute("""
    SELECT 
        datetime(e.created_at, 'localtime') as time,
        me.value as window
    FROM entities e
    LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = "active_window"
    WHERE e.file_type_group = 'image'
    ORDER BY e.created_at DESC
    LIMIT 5
""")

for time, window in cursor.fetchall():
    print(f"{time} - {window}")

conn.close()