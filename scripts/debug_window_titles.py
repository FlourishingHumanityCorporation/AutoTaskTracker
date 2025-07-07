#!/usr/bin/env python
"""Debug why window titles are missing."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime, timedelta

# Direct database query
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres", 
    password="mysecretpassword"
)

cursor = conn.cursor()

# Check recent metadata entries
print("=== WINDOW TITLE DEBUG ===\n")

# Get recent entities
cursor.execute("""
    SELECT e.id, e.filepath, COALESCE(e.created_at, e.file_created_at) as timestamp
    FROM entities e
    WHERE COALESCE(e.created_at, e.file_created_at) >= NOW() - INTERVAL '10 minutes'
    ORDER BY COALESCE(e.created_at, e.file_created_at) DESC
    LIMIT 10
""")

entities = cursor.fetchall()
print(f"Found {len(entities)} recent entities\n")

for entity_id, filepath, timestamp in entities:
    filename = os.path.basename(filepath) if filepath else "None"
    print(f"Entity {entity_id}: {timestamp}")
    print(f"  File: {filename}")
    
    # Check metadata for this entity
    cursor.execute("""
        SELECT key, value 
        FROM metadata_entries 
        WHERE entity_id = %s 
        AND key IN ('active_window', 'window_title', 'category', 'ocr_text', 'ai_task_raw')
    """, (entity_id,))
    
    metadata = cursor.fetchall()
    print("  Metadata:")
    for key, value in metadata:
        if key == 'ocr_text' and value:
            value = value[:100] + "..." if len(value) > 100 else value
        print(f"    {key}: {value}")
    
    if not any(key == 'active_window' for key, _ in metadata):
        print("    ⚠️ NO active_window metadata!")
    
    print()

# Check if metadata is being written at all
cursor.execute("""
    SELECT COUNT(DISTINCT entity_id) as entities_with_metadata,
           COUNT(DISTINCT CASE WHEN key = 'active_window' THEN entity_id END) as with_window,
           COUNT(DISTINCT CASE WHEN key = 'ocr_text' THEN entity_id END) as with_ocr
    FROM metadata_entries
    WHERE entity_id IN (
        SELECT id FROM entities 
        WHERE COALESCE(created_at, file_created_at) >= NOW() - INTERVAL '1 hour'
    )
""")

stats = cursor.fetchone()
print("\nMetadata Statistics (last hour):")
print(f"  Entities with any metadata: {stats[0]}")
print(f"  Entities with window title: {stats[1]}")
print(f"  Entities with OCR text: {stats[2]}")

cursor.close()
conn.close()