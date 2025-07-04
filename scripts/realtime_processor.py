#!/usr/bin/env python3
"""
Real-time screenshot processor for AutoTaskTracker.
Monitors for new screenshots and processes them immediately.
"""
import sys
import os
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Set
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core.categorizer import ActivityCategorizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealtimeProcessor:
    """Process new screenshots in real-time."""
    
    def __init__(self, check_interval: int = 10):
        self.db_path = os.path.expanduser("~/.memos/database.db")
        self.check_interval = check_interval
        self.task_extractor = get_task_extractor()
        self.processed_ids: Set[int] = set()
        self.running = True
        
        # Load already processed IDs to avoid reprocessing
        self._load_processed_ids()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, stopping...")
        self.running = False
    
    def _load_processed_ids(self):
        """Load IDs of already processed entities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get entities that have tasks
            cursor.execute("""
                SELECT DISTINCT entity_id 
                FROM metadata_entries 
                WHERE key = 'tasks'
            """)
            
            self.processed_ids = {row[0] for row in cursor.fetchall()}
            logger.info(f"Loaded {len(self.processed_ids)} already processed entities")
            
        finally:
            conn.close()
    
    def get_new_screenshots(self, limit: int = 50):
        """Get screenshots that haven't been processed yet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get recent unprocessed entities
            cursor.execute("""
                SELECT e.id, m.value as window_title
                FROM entities e
                JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'active_window'
                WHERE e.id NOT IN (
                    SELECT DISTINCT entity_id 
                    FROM metadata_entries 
                    WHERE key = 'tasks'
                )
                AND e.created_at > datetime('now', '-1 hour')
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (limit,))
            
            new_screenshots = []
            for entity_id, window_title in cursor.fetchall():
                if entity_id not in self.processed_ids:
                    new_screenshots.append({
                        'id': entity_id,
                        'window_title': window_title
                    })
            
            return new_screenshots
            
        finally:
            conn.close()
    
    def process_screenshot(self, screenshot: dict) -> bool:
        """Process a single screenshot."""
        entity_id = screenshot['id']
        window_title = screenshot['window_title']
        
        if not window_title:
            return False
        
        # Extract task and category
        task = self.task_extractor.extract_task(window_title)
        category = ActivityCategorizer.categorize(window_title)
        
        if not task:
            task = "Unknown Activity"
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if already processed (double check)
            cursor.execute("""
                SELECT 1 FROM metadata_entries 
                WHERE entity_id = ? AND key = 'tasks'
            """, (entity_id,))
            
            if cursor.fetchone():
                self.processed_ids.add(entity_id)
                return False
            
            # Insert task
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, 'tasks', ?, 'realtime_processor', 'text', datetime('now'), datetime('now'))
            """, (entity_id, task))
            
            # Insert category
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, 'category', ?, 'realtime_processor', 'text', datetime('now'), datetime('now'))
            """, (entity_id, category))
            
            conn.commit()
            self.processed_ids.add(entity_id)
            
            logger.info(f"Processed: {task} ({category})")
            return True
            
        except sqlite3.IntegrityError:
            # Already exists
            self.processed_ids.add(entity_id)
            return False
        except Exception as e:
            logger.error(f"Error processing entity {entity_id}: {e}")
            return False
        finally:
            conn.close()
    
    def run_once(self) -> int:
        """Run one processing cycle."""
        new_screenshots = self.get_new_screenshots()
        
        if not new_screenshots:
            return 0
        
        processed = 0
        for screenshot in new_screenshots:
            if self.process_screenshot(screenshot):
                processed += 1
        
        if processed > 0:
            logger.info(f"Processed {processed} new screenshots")
        
        return processed
    
    def run(self):
        """Run continuous processing loop."""
        logger.info(f"Starting real-time processor (checking every {self.check_interval}s)")
        logger.info("Press Ctrl+C to stop")
        
        last_status = time.time()
        total_processed = 0
        
        while self.running:
            try:
                processed = self.run_once()
                total_processed += processed
                
                # Show status every minute
                if time.time() - last_status > 60:
                    logger.info(f"Status: {len(self.processed_ids)} total processed, "
                              f"{total_processed} in this session")
                    last_status = time.time()
                
                # Sleep before next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(self.check_interval)
        
        logger.info(f"Stopped. Processed {total_processed} screenshots in this session")
    
    def show_stats(self):
        """Show processing statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total entities
            cursor.execute("SELECT COUNT(*) FROM entities")
            total = cursor.fetchone()[0]
            
            # Processed entities
            cursor.execute("""
                SELECT COUNT(DISTINCT entity_id) 
                FROM metadata_entries 
                WHERE key = 'tasks'
            """)
            processed = cursor.fetchone()[0]
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) 
                FROM entities 
                WHERE created_at > datetime('now', '-1 hour')
            """)
            recent = cursor.fetchone()[0]
            
            print(f"\n=== Processing Statistics ===")
            print(f"Total screenshots: {total}")
            print(f"Processed: {processed} ({processed/total*100:.1f}%)")
            print(f"Last hour: {recent} screenshots")
            
        finally:
            conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time screenshot processor')
    parser.add_argument('--interval', type=int, default=10,
                        help='Check interval in seconds (default: 10)')
    parser.add_argument('--stats', action='store_true',
                        help='Show statistics and exit')
    
    args = parser.parse_args()
    
    processor = RealtimeProcessor(check_interval=args.interval)
    
    if args.stats:
        processor.show_stats()
    else:
        processor.run()


if __name__ == "__main__":
    main()