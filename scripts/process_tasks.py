#!/usr/bin/env python3
"""
Process unprocessed screenshots and extract tasks.
Simple version that handles database permissions correctly.
"""
import sys
import os
import sqlite3
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core.categorizer import ActivityCategorizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def process_unprocessed_screenshots(limit=None):
    """Process screenshots that don't have tasks extracted yet."""
    db_path = os.path.expanduser("~/.memos/database.db")
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
    
    # Connect directly to avoid permission issues
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get task extractor
    extractor = get_task_extractor()
    
    try:
        # Find entities without task extraction
        query = """
            SELECT DISTINCT e.id, m.value as window_title
            FROM entities e
            JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'active_window'
            LEFT JOIN metadata_entries t ON e.id = t.entity_id AND t.key = 'tasks'
            WHERE t.id IS NULL
            ORDER BY e.created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        unprocessed = cursor.fetchall()
        
        logger.info(f"Found {len(unprocessed)} unprocessed screenshots")
        
        processed = 0
        for entity_id, window_title in unprocessed:
            if not window_title:
                continue
            
            # Extract task
            task = extractor.extract_task(window_title)
            if not task:
                task = "Unknown Activity"
            
            # Get category
            category = ActivityCategorizer.categorize(window_title)
            
            # Insert task
            try:
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, 'tasks', ?, 'task_processor', 'text', datetime('now'), datetime('now'))
                """, (entity_id, task))
                
                # Insert category
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, 'category', ?, 'task_processor', 'text', datetime('now'), datetime('now'))
                """, (entity_id, category))
                
                conn.commit()
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"Processed {processed} screenshots...")
                    
            except sqlite3.IntegrityError:
                # Already exists, skip
                pass
            except Exception as e:
                logger.error(f"Error processing entity {entity_id}: {e}")
        
        logger.info(f"Successfully processed {processed} screenshots")
        
    finally:
        conn.close()


def show_sample_results():
    """Show sample of extracted tasks."""
    db_path = os.path.expanduser("~/.memos/database.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT e.created_at, m1.value as window_title, m2.value as task, m3.value as category
            FROM entities e
            JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'active_window'
            JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'tasks'
            JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'category'
            WHERE m2.source_type = 'task_processor'
            ORDER BY e.created_at DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        print("\n=== Sample Extracted Tasks ===")
        for created_at, window_title, task, category in results:
            print(f"\nTime: {created_at}")
            print(f"Window: {window_title[:60]}...")
            print(f"Task: {task}")
            print(f"Category: {category}")
            
    finally:
        conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process tasks from screenshots')
    parser.add_argument('--limit', type=int, help='Limit number of screenshots to process')
    parser.add_argument('--sample', action='store_true', help='Show sample results after processing')
    
    args = parser.parse_args()
    
    process_unprocessed_screenshots(args.limit)
    
    if args.sample:
        show_sample_results()


if __name__ == "__main__":
    main()