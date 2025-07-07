#!/usr/bin/env python
"""Fix window titles that were stored as tuples instead of strings."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import ast

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="autotasktracker",
    user="postgres",
    password="mysecretpassword"
)

cursor = conn.cursor()

# Find metadata entries with tuple window titles
cursor.execute("""
    SELECT id, entity_id, value
    FROM metadata_entries
    WHERE key = 'active_window'
    AND value LIKE '(%'
""")

entries = cursor.fetchall()
print(f"Found {len(entries)} window titles stored as tuples\n")

fixed_count = 0
for meta_id, entity_id, value in entries:
    try:
        # Parse the tuple string
        parsed = ast.literal_eval(value)
        if isinstance(parsed, tuple) and len(parsed) >= 1:
            # Extract just the text part
            window_title = parsed[0]
            
            # Update the entry
            cursor.execute("""
                UPDATE metadata_entries
                SET value = %s
                WHERE id = %s
            """, (window_title, meta_id))
            
            fixed_count += 1
            print(f"Fixed entity {entity_id}: {window_title}")
        
    except Exception as e:
        print(f"Error parsing entry {meta_id}: {e}")

conn.commit()
print(f"\nFixed {fixed_count} window titles")

# Verify the fix
cursor.execute("""
    SELECT COUNT(*) 
    FROM metadata_entries
    WHERE key = 'active_window'
    AND value NOT LIKE '(%'
""")

good_count = cursor.fetchone()[0]
print(f"Clean window titles: {good_count}")

cursor.close()
conn.close()