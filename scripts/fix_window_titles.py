#!/usr/bin/env python3
"""
Fix missing window_title entries for already processed records.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.categorizer import extract_window_title

def main():
    db = DatabaseManager()
    
    # Get processed records missing window_title
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT 
                m1.entity_id,
                m2.value as active_window
            FROM metadata_entries m1
            LEFT JOIN metadata_entries m2 ON m1.entity_id = m2.entity_id AND m2.key = 'active_window'
            LEFT JOIN metadata_entries m3 ON m1.entity_id = m3.entity_id AND m3.key = 'window_title'
            WHERE m1.key = 'tasks' 
            AND m3.entity_id IS NULL
        """)
        
        records = cursor.fetchall()
        print(f"Found {len(records)} records needing window_title")
        
    # Process in batches
    batch_size = 100
    processed = 0
    
    with db.get_connection(readonly=False) as conn:
        cursor = conn.cursor()
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            
            for entity_id, active_window in batch:
                window_title = extract_window_title(active_window) if active_window else 'Unknown'
                
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (entity_id, 'window_title', window_title, 'window_extractor', 'text'))
                
                processed += 1
                
            conn.commit()
            print(f"Processed {min(i+batch_size, len(records))}/{len(records)} records")
    
    print(f"✅ Added window_title entries for {processed} records")

if __name__ == '__main__':
    main()