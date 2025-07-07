#!/usr/bin/env python
"""Debug what the task query is returning from the database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime, timedelta

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres",
    password="mysecretpassword"
)

cursor = conn.cursor()

# Check a recent entity with its metadata
print("=== TASK QUERY DEBUG ===\n")

# Get recent entities with metadata
cursor.execute("""
    SELECT 
        e.id,
        e.filepath,
        COALESCE(e.created_at, e.file_created_at) as timestamp,
        m1.value as ocr_text,
        m2.value as active_window,
        m3.value as category
    FROM entities e
    LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'ocr_text'
    LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'  
    LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'category'
    WHERE COALESCE(e.created_at, e.file_created_at) >= NOW() - INTERVAL '1 hour'
    ORDER BY COALESCE(e.created_at, e.file_created_at) DESC
    LIMIT 10
""")

results = cursor.fetchall()
print(f"Found {len(results)} recent entities with metadata\n")

for entity_id, filepath, timestamp, ocr_text, window, category in results:
    filename = os.path.basename(filepath) if filepath else "None"
    ocr_len = len(ocr_text) if ocr_text else 0
    print(f"Entity {entity_id}: {timestamp}")
    print(f"  File: {filename}")
    print(f"  Window: {window}")
    print(f"  Category: {category}")
    print(f"  OCR text: {ocr_len} chars")
    print()

# Check the actual query used by TaskRepository
print("\nChecking TaskRepository query pattern...")

# This mimics what the repository does
query = """
    SELECT 
        e.id,
        COALESCE(e.created_at, e.file_created_at) as created_at,
        e.filepath as screenshot_path,
        m1.value as ocr_text,
        m2.value as active_window,
        m3.value as ai_task_raw,
        m4.value as category
    FROM entities e
    LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'ocr_text'
    LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
    LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'ai_task_raw'
    LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
    WHERE COALESCE(e.created_at, e.file_created_at) >= %s 
    AND COALESCE(e.created_at, e.file_created_at) <= %s
    ORDER BY COALESCE(e.created_at, e.file_created_at)
    LIMIT 5
"""

end_time = datetime.now()
start_time = end_time - timedelta(hours=2)  # Use 2 hours to account for timezone issues

cursor.execute(query, (
    start_time.strftime('%Y-%m-%d %H:%M:%S'),
    end_time.strftime('%Y-%m-%d %H:%M:%S')
))

results = cursor.fetchall()
print(f"\nRepository query returned {len(results)} rows:")
for row in results:
    entity_id, created_at, path, ocr, window, ai_task, category = row
    print(f"  ID {entity_id}: window='{window}', category='{category}'")

cursor.close()
conn.close()