#!/usr/bin/env python
"""Diagnostic script to identify exact timezone offset issue."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime, timezone, timedelta
import pytz
import re

print("=== TIMEZONE DIAGNOSTIC REPORT ===\n")

# 1. System Information
print("1. SYSTEM INFORMATION")
print(f"   Current local time: {datetime.now()}")
print(f"   Current UTC time: {datetime.now(timezone.utc)}")
print(f"   Timezone offset: {datetime.now(timezone.utc).astimezone().strftime('%z')}")
print(f"   System timezone: {datetime.now().astimezone().tzinfo}")

# 2. Database Connection
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres",
    password="mysecretpassword"
)
cursor = conn.cursor()

# 3. Database Timezone
print("\n2. DATABASE CONFIGURATION")
cursor.execute("SHOW timezone")
db_timezone = cursor.fetchone()[0]
print(f"   PostgreSQL timezone: {db_timezone}")

cursor.execute("SELECT NOW()")
db_now = cursor.fetchone()[0]
print(f"   Database NOW(): {db_now}")

# 4. Sample Data Analysis
print("\n3. SAMPLE DATA ANALYSIS")
cursor.execute("""
    SELECT 
        id,
        filepath,
        created_at,
        file_created_at,
        created_at AT TIME ZONE 'UTC' as created_at_utc,
        file_created_at AT TIME ZONE 'UTC' as file_created_at_utc
    FROM entities
    WHERE filepath IS NOT NULL
    ORDER BY id DESC
    LIMIT 5
""")

results = cursor.fetchall()
for row in results:
    entity_id, filepath, created_at, file_created_at, created_utc, file_created_utc = row
    
    # Extract timestamp from filename
    filename = os.path.basename(filepath) if filepath else ""
    file_match = re.search(r'(\d{8})-(\d{6})', filename)
    
    if file_match:
        date_part = file_match.group(1)
        time_part = file_match.group(2)
        
        # Parse expected timestamp from filename
        expected = datetime(
            int(date_part[:4]), int(date_part[4:6]), int(date_part[6:8]),
            int(time_part[:2]), int(time_part[2:4]), int(time_part[4:6])
        )
        
        print(f"\n   Entity {entity_id}:")
        print(f"      Filename: {filename}")
        print(f"      Expected (from filename): {expected}")
        print(f"      created_at: {created_at}")
        print(f"      file_created_at: {file_created_at}")
        
        if created_at:
            # Calculate offset
            offset_hours = (created_at.replace(tzinfo=None) - expected).total_seconds() / 3600
            print(f"      Offset: {offset_hours:+.1f} hours")

# 5. Query Time Range Analysis
print("\n4. QUERY TIME RANGE ANALYSIS")
local_now = datetime.now()
local_1h_ago = local_now - timedelta(hours=1)

print(f"   Local query range: {local_1h_ago} to {local_now}")

# Check what this matches in the database
cursor.execute("""
    SELECT COUNT(*) 
    FROM entities 
    WHERE COALESCE(created_at, file_created_at) >= %s 
    AND COALESCE(created_at, file_created_at) <= %s
""", (local_1h_ago, local_now))

count_local = cursor.fetchone()[0]
print(f"   Results with local time: {count_local}")

# Try with UTC
utc_now = datetime.now(timezone.utc)
utc_1h_ago = utc_now - timedelta(hours=1)

cursor.execute("""
    SELECT COUNT(*) 
    FROM entities 
    WHERE COALESCE(created_at, file_created_at) >= %s 
    AND COALESCE(created_at, file_created_at) <= %s
""", (utc_1h_ago, utc_now))

count_utc = cursor.fetchone()[0]
print(f"   Results with UTC time: {count_utc}")

# Try with offset
offset_now = local_now + timedelta(hours=8)  # Based on observed +8 hour offset
offset_1h_ago = offset_now - timedelta(hours=1)

cursor.execute("""
    SELECT COUNT(*) 
    FROM entities 
    WHERE COALESCE(created_at, file_created_at) >= %s 
    AND COALESCE(created_at, file_created_at) <= %s
""", (offset_1h_ago, offset_now))

count_offset = cursor.fetchone()[0]
print(f"   Results with +8h offset: {count_offset}")

# 6. Recommendations
print("\n5. RECOMMENDATIONS")
if count_local == 0 and count_offset > 0:
    print("   ⚠️  Timestamps are stored 8 hours in the future")
    print("   ⚠️  Queries need to add 8 hours to time ranges")
    print("   ⚠️  Root cause: Database may be interpreting local time as UTC")

cursor.close()
conn.close()

print("\n=== END DIAGNOSTIC REPORT ===")