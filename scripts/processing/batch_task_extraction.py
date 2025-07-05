#!/usr/bin/env python3
"""
Batch task extraction script for processing unprocessed screenshots.
Extracts tasks from screenshots that don't have task metadata yet.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core.categorizer import ActivityCategorizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchTaskProcessor:
    """Process screenshots in batches to extract tasks."""
    
    def __init__(self, batch_size: int = 100):
        self.db = DatabaseManager()
        self.task_extractor = get_task_extractor()
        self.batch_size = batch_size
        self.stats = {
            'total_processed': 0,
            'tasks_extracted': 0,
            'categories_assigned': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def get_unprocessed_screenshots(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get screenshots that don't have task metadata yet."""
        try:
            with self.db.get_connection(readonly=True) as conn:
                cursor = conn.cursor()
                
                # Find entities without task metadata
                query = """
                SELECT 
                    e.id,
                    e.created_at,
                    e.filepath,
                    m1.value as active_window,
                    m2.value as ocr_result
                FROM entities e
                LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'active_window'
                LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'ocr_result'
                WHERE NOT EXISTS (
                    SELECT 1 FROM metadata_entries m3 
                    WHERE m3.entity_id = e.id AND m3.key = 'tasks'
                )
                ORDER BY e.created_at DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                screenshots = []
                for row in results:
                    screenshots.append({
                        'id': row[0],
                        'created_at': row[1],
                        'filepath': row[2],
                        'active_window': row[3],
                        'ocr_result': row[4]
                    })
                
                logger.info(f"Found {len(screenshots)} unprocessed screenshots")
                return screenshots
                
        except Exception as e:
            logger.error(f"Error getting unprocessed screenshots: {e}")
            return []
    
    def process_batch(self, screenshots: List[Dict[str, Any]]) -> None:
        """Process a batch of screenshots to extract tasks."""
        for screenshot in screenshots:
            try:
                entity_id = screenshot['id']
                window_title = screenshot.get('active_window', '')
                ocr_text = screenshot.get('ocr_result')
                
                # Extract task
                task = self.task_extractor.extract_and_store_task(
                    entity_id, 
                    window_title, 
                    ocr_text
                )
                
                if task:
                    self.stats['tasks_extracted'] += 1
                    logger.debug(f"Extracted task for entity {entity_id}: {task}")
                    
                    # Also categorize the activity
                    category = ActivityCategorizer.categorize(window_title, ocr_text)
                    self._store_category(entity_id, category)
                    self.stats['categories_assigned'] += 1
                else:
                    # Even if no specific task extracted, store a basic task
                    # based on window title to ensure all screenshots have tasks
                    basic_task = self._create_basic_task(window_title)
                    if basic_task:
                        self._store_task(entity_id, basic_task)
                        self.stats['tasks_extracted'] += 1
                        
                        # Store category
                        category = ActivityCategorizer.categorize(window_title, ocr_text)
                        self._store_category(entity_id, category)
                        self.stats['categories_assigned'] += 1
                
                self.stats['total_processed'] += 1
                
                # Log progress every 100 items
                if self.stats['total_processed'] % 100 == 0:
                    logger.info(f"Progress: {self.stats['total_processed']} processed, "
                              f"{self.stats['tasks_extracted']} tasks extracted")
                    
            except Exception as e:
                logger.error(f"Error processing entity {screenshot.get('id')}: {e}")
                self.stats['errors'] += 1
    
    def _create_basic_task(self, window_title: str) -> str:
        """Create a basic task description from window title."""
        if not window_title:
            return None
            
        # Clean up window title
        title = window_title.strip()
        
        # Remove common noise
        title = title.replace('MallocNanoZone=1', '').strip()
        
        # Extract the most meaningful part
        if ' — ' in title:
            parts = [p.strip() for p in title.split(' — ') if p.strip()]
            if parts:
                # Get the user and first meaningful part
                user_part = parts[0]
                if len(parts) > 1 and parts[1] != '✳':
                    return f"{parts[1]}: {user_part}"
                else:
                    return f"Activity: {user_part}"
        
        # Fallback
        if len(title) > 60:
            title = title[:57] + "..."
        
        return f"Activity: {title}"
    
    def _store_task(self, entity_id: int, task: str) -> None:
        """Store task in metadata_entries."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, source, data_type) 
                    VALUES (?, 'tasks', ?, 'task_extractor', 'batch_extraction', 'text')""",
                    (entity_id, task)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing task for entity {entity_id}: {e}")
    
    def _store_category(self, entity_id: int, category: str) -> None:
        """Store category in metadata_entries."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if category already exists
                cursor.execute(
                    "SELECT id FROM metadata_entries WHERE entity_id = ? AND key = 'category'",
                    (entity_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute(
                        "UPDATE metadata_entries SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE entity_id = ? AND key = 'category'",
                        (category, entity_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, source, data_type) 
                        VALUES (?, 'category', ?, 'categorizer', 'batch_extraction', 'text')""",
                        (entity_id, category)
                    )
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing category for entity {entity_id}: {e}")
    
    def process_all(self, max_screenshots: int = None) -> Dict[str, Any]:
        """Process all unprocessed screenshots in batches."""
        logger.info("Starting batch task extraction...")
        self.stats['start_time'] = datetime.now()
        
        # Get all unprocessed screenshots
        screenshots = self.get_unprocessed_screenshots(limit=max_screenshots)
        total_count = len(screenshots)
        
        if total_count == 0:
            logger.info("No unprocessed screenshots found")
            return self.stats
        
        logger.info(f"Processing {total_count} screenshots in batches of {self.batch_size}")
        
        # Process in batches
        for i in range(0, total_count, self.batch_size):
            batch = screenshots[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_count + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            self.process_batch(batch)
            
            # Small delay between batches to avoid overloading
            if i + self.batch_size < total_count:
                time.sleep(0.5)
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Final report
        logger.info("=" * 60)
        logger.info("Batch Task Extraction Complete")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.stats['total_processed']}")
        logger.info(f"Tasks extracted: {self.stats['tasks_extracted']}")
        logger.info(f"Categories assigned: {self.stats['categories_assigned']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Rate: {self.stats['total_processed'] / duration:.2f} screenshots/second")
        logger.info("=" * 60)
        
        return self.stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch extract tasks from unprocessed screenshots')
    parser.add_argument('--batch-size', type=int, default=100, 
                       help='Number of screenshots to process per batch (default: 100)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Maximum number of screenshots to process (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without actually processing')
    
    args = parser.parse_args()
    
    if args.dry_run:
        processor = BatchTaskProcessor(batch_size=args.batch_size)
        screenshots = processor.get_unprocessed_screenshots(limit=args.limit)
        logger.info(f"Dry run: Would process {len(screenshots)} screenshots")
        if screenshots and len(screenshots) > 0:
            logger.info(f"First screenshot: {screenshots[0]}")
        return
    
    # Run the batch processor
    processor = BatchTaskProcessor(batch_size=args.batch_size)
    stats = processor.process_all(max_screenshots=args.limit)
    
    # Exit with error code if there were errors
    sys.exit(1 if stats['errors'] > 0 else 0)


if __name__ == '__main__':
    main()