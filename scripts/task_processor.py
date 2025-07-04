#!/usr/bin/env python3
"""
Automatic Task Processing Service
Continuously processes new screenshots to extract tasks and categories.
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import signal

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker import extract_task_summary, categorize_activity
from autotasktracker.core.database import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / '.memos' / 'logs' / 'task_processor.log')
    ]
)
logger = logging.getLogger(__name__)


class TaskProcessor:
    """Automatic task extraction and categorization service."""
    
    def __init__(self, batch_size=50, sleep_interval=30):
        self.db = DatabaseManager()
        self.batch_size = batch_size
        self.sleep_interval = sleep_interval
        self.running = False
        self.stats = {
            'processed': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def start(self):
        """Start the processing service."""
        logger.info("Starting Task Processing Service")
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
        try:
            while self.running:
                processed = self._process_batch()
                if processed > 0:
                    logger.info(f"Processed {processed} new records")
                    self.stats['processed'] += processed
                
                # Sleep between batches
                time.sleep(self.sleep_interval)
                
        except Exception as e:
            logger.error(f"Service error: {e}")
            
    def _shutdown(self, signum=None, frame=None):
        """Graceful shutdown."""
        logger.info("Shutting down Task Processing Service...")
        self.running = False
        self._print_stats()
        
    def _process_batch(self):
        """Process a batch of unprocessed records."""
        try:
            # Get records that need processing
            unprocessed = self._get_unprocessed_records()
            
            if not unprocessed:
                return 0
                
            processed_count = 0
            
            for record in unprocessed:
                try:
                    self._process_record(record)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing record {record['entity_id']}: {e}")
                    self.stats['errors'] += 1
                    
            return processed_count
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return 0
    
    def _get_unprocessed_records(self):
        """Get records that haven't been processed for tasks yet."""
        query = """
        SELECT 
            e.id as entity_id,
            e.filepath,
            m1.value as active_window,
            m2.value as ocr_text,
            e.created_at
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'active_window'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'ocr_result'
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        WHERE m2.value IS NOT NULL 
        AND m3.value IS NULL
        AND e.created_at >= datetime('now', '-7 days')
        ORDER BY e.created_at DESC
        LIMIT ?
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (self.batch_size,))
            return [dict(row) for row in cursor.fetchall()]
    
    def _process_record(self, record):
        """Process a single record to extract task and category."""
        entity_id = record['entity_id']
        active_window = record['active_window']
        ocr_text = record['ocr_text']
        
        # Extract task and category
        task = extract_task_summary(ocr_text, active_window)
        category = categorize_activity(active_window, ocr_text)
        
        # Extract window title from active_window
        from autotasktracker.core.categorizer import extract_window_title
        window_title = extract_window_title(active_window) if active_window else 'Unknown'
        
        # Store in database
        with self.db.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            
            # Insert task summary
            cursor.execute("""
                INSERT OR REPLACE INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (entity_id, 'tasks', task, 'task_extractor', 'text'))
            
            # Insert category
            cursor.execute("""
                INSERT OR REPLACE INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (entity_id, 'category', category, 'categorizer', 'text'))
            
            # Insert window title
            cursor.execute("""
                INSERT OR REPLACE INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (entity_id, 'window_title', window_title, 'window_extractor', 'text'))
            
            # Copy OCR text as 'text' key for compatibility
            cursor.execute("""
                INSERT OR REPLACE INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (entity_id, 'text', ocr_text, 'ocr', 'text'))
            
            conn.commit()
            
        logger.debug(f"Processed entity {entity_id}: {task} [{category}] - {window_title}")
    
    def _print_stats(self):
        """Print processing statistics."""
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        rate = self.stats['processed'] / runtime if runtime > 0 else 0
        
        print(f"\n{'='*50}")
        print(f"Task Processing Service - Final Statistics")
        print(f"{'='*50}")
        print(f"Runtime: {runtime:.1f} minutes")
        print(f"Records processed: {self.stats['processed']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Processing rate: {rate:.1f} records/minute")
        print(f"{'='*50}")
    
    def get_status(self):
        """Get current processing status."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total entities
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities = cursor.fetchone()[0]
            
            # Processed entities
            cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM metadata_entries WHERE key = 'tasks'")
            processed_entities = cursor.fetchone()[0]
            
            # Recent processing (last hour)
            cursor.execute("""
                SELECT COUNT(*) FROM metadata_entries 
                WHERE key = 'tasks' AND created_at >= datetime('now', '-1 hour')
            """)
            recent_processed = cursor.fetchone()[0]
            
            return {
                'total_entities': total_entities,
                'processed_entities': processed_entities,
                'unprocessed_entities': total_entities - processed_entities,
                'processing_percentage': (processed_entities / total_entities * 100) if total_entities > 0 else 0,
                'recent_processed': recent_processed
            }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automatic Task Processing Service')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of records to process in each batch')
    parser.add_argument('--interval', type=int, default=30,
                       help='Sleep interval between batches (seconds)')
    parser.add_argument('--status', action='store_true',
                       help='Show current processing status and exit')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as background daemon')
    
    args = parser.parse_args()
    
    processor = TaskProcessor(
        batch_size=args.batch_size,
        sleep_interval=args.interval
    )
    
    if args.status:
        status = processor.get_status()
        print(f"\n📊 Task Processing Status:")
        print(f"   Total entities: {status['total_entities']}")
        print(f"   Processed: {status['processed_entities']} ({status['processing_percentage']:.1f}%)")
        print(f"   Unprocessed: {status['unprocessed_entities']}")
        print(f"   Recent (1h): {status['recent_processed']}")
        return
    
    if args.daemon:
        # TODO: Implement proper daemonization
        logger.info("Daemon mode not yet implemented, running in foreground")
    
    processor.start()


if __name__ == '__main__':
    main()