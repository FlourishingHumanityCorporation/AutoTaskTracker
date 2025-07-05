#!/usr/bin/env python3
"""
Process unprocessed screenshots and extract tasks.
Updated to use Pensieve API integration with graceful fallback.
"""
import sys
import os
import sqlite3
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core import ActivityCategorizer
from autotasktracker.core import DatabaseManager
from autotasktracker.pensieve.health_monitor import is_pensieve_healthy
from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def process_unprocessed_screenshots(limit=None):
    """Process screenshots that don't have tasks extracted yet."""
    # Use Pensieve API when available, fallback to DatabaseManager
    use_api = is_pensieve_healthy()
    
    if use_api:
        logger.info("Using Pensieve API for data access")
        return _process_via_pensieve_api(limit=limit)
    else:
        logger.info("Pensieve API unavailable, using direct database access")
        return _process_via_database(limit=limit)


def _process_via_pensieve_api(limit=None):
    """Process screenshots using Pensieve REST API."""
    try:
        client = get_pensieve_client()
        
        # Get unprocessed frames via API
        frames = client.get_frames(limit=limit or 100, processed_only=False)
        
        if not frames:
            logger.info("No frames to process")
            return
        
        extractor = get_task_extractor()
        categorizer = ActivityCategorizer()
        processed_count = 0
        
        for frame in frames:
            # Check if already has task extraction
            metadata = client.get_metadata(frame.id, 'extracted_tasks')
            if metadata.get('extracted_tasks'):
                continue  # Already processed
            
            # Get window title and OCR text
            window_title = client.get_metadata(frame.id, "active_window").get("active_window", '')
            ocr_text = client.get_ocr_result(frame.id) or ''
            
            if not window_title and not ocr_text:
                continue  # No data to process
            
            # Extract tasks
            tasks = extractor.extract_tasks(window_title, ocr_text)
            if tasks:
                # Store results via API
                client.store_metadata(frame.id, 'extracted_tasks', {
                    "tasks": tasks,
                    'extracted_at': datetime.now().isoformat(),
                    'method': 'pensieve_api'
                })
                
                # Categorize activity
                category = categorizer.categorize_activity(window_title)
                if category:
                    client.store_metadata(frame.id, 'activity_category', category)
                
                processed_count += 1
                logger.info(f"Processed frame {frame.id}: {len(tasks)} tasks found")
            
            if limit and processed_count >= limit:
                break
        
        logger.info(f"Processed {processed_count} frames via Pensieve API")
        
    except PensieveAPIError as e:
        logger.error(f"Pensieve API error: {e.message}")
        # Fallback to database
        return _process_via_database(limit=limit)
    except Exception as e:
        logger.error(f"Error processing via API: {e}")
        return _process_via_database(limit=limit)


def _process_via_database(limit=None):
    """Process screenshots using DatabaseManager (fallback when API unavailable)."""
    try:
        db = DatabaseManager()
        extractor = get_task_extractor()
        categorizer = ActivityCategorizer()
        
        with db.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            
            # Find entities without task extraction
            query = """
                SELECT DISTINCT e.id, m.value as window_title
                FROM entities e
                JOIN metadata_entries m ON e.id = m.entity_id AND m.key = "active_window"
                LEFT JOIN metadata_entries t ON e.id = t.entity_id AND t.key = "tasks"
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
                category = categorizer.categorize(window_title)
                
                # Insert task
                try:
                    cursor.execute("""
                        INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, data_type, created_at, updated_at)
                        VALUES (?, "tasks", ?, 'task_processor', 'text', datetime('now'), datetime('now'))
                    """, (entity_id, task))
                    
                    # Insert category
                    cursor.execute("""
                        INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, data_type, created_at, updated_at)
                        VALUES (?, "category", ?, 'task_processor', 'text', datetime('now'), datetime('now'))
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
            
    except Exception as e:
        logger.error(f"Database processing failed: {e}")


def show_sample_results():
    """Show sample of extracted tasks."""
    try:
        db = DatabaseManager()
        with db.get_connection(readonly=True) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.created_at, m1.value as window_title, m2.value as task, m3.value as category
                FROM entities e
                JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = "active_window"
                JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "tasks"
                JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = "category"
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
                
    except Exception as e:
        logger.error(f"Failed to show sample results: {e}")


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