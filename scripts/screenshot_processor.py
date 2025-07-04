#!/usr/bin/env python3
"""
Background processing service for AutoTaskTracker.
Automatically processes new screenshots with task extraction and AI enhancement.
"""
import time
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core.categorizer import ActivityCategorizer
from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScreenshotProcessor:
    """Process screenshots and extract tasks in real-time."""
    
    def __init__(self, check_interval: int = 30):
        """Initialize processor with specified check interval in seconds."""
        self.db = DatabaseManager()
        self.task_extractor = get_task_extractor()
        self.check_interval = check_interval
        self.processed_count = 0
        
        # Try to initialize AI extractor
        try:
            self.ai_extractor = AIEnhancedTaskExtractor(self.db.db_path)
            self.ai_available = True
            logger.info("AI-enhanced extraction available")
        except Exception as e:
            logger.warning(f"AI extraction not available: {e}")
            self.ai_extractor = None
            self.ai_available = False
    
    def get_unprocessed_screenshots(self, limit: int = 100) -> List[Dict]:
        """Get screenshots that haven't been processed yet."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find entities without task extraction
                cursor.execute("""
                    SELECT DISTINCT e.id, e.filepath, e.created_at
                    FROM entities e
                    LEFT JOIN metadata_entries m_task 
                        ON e.id = m_task.entity_id AND m_task.key = 'tasks'
                    LEFT JOIN metadata_entries m_cat
                        ON e.id = m_cat.entity_id AND m_cat.key = 'category'
                    WHERE m_task.id IS NULL OR m_cat.id IS NULL
                    ORDER BY e.created_at DESC
                    LIMIT ?
                """, (limit,))
                
                results = []
                for row in cursor.fetchall():
                    entity_id, filepath, created_at = row
                    
                    # Get window title
                    cursor.execute("""
                        SELECT value FROM metadata_entries
                        WHERE entity_id = ? AND key = 'active_window'
                    """, (entity_id,))
                    
                    window_row = cursor.fetchone()
                    window_title = window_row[0] if window_row else None
                    
                    # Get OCR text if available
                    cursor.execute("""
                        SELECT value FROM metadata_entries
                        WHERE entity_id = ? AND key = 'ocr_result'
                    """, (entity_id,))
                    
                    ocr_row = cursor.fetchone()
                    ocr_text = ocr_row[0] if ocr_row else None
                    
                    results.append({
                        'id': entity_id,
                        'filepath': filepath,
                        'created_at': created_at,
                        'window_title': window_title,
                        'ocr_text': ocr_text
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting unprocessed screenshots: {e}")
            return []
    
    def process_screenshot(self, screenshot: Dict) -> bool:
        """Process a single screenshot and extract task information."""
        entity_id = screenshot['id']
        window_title = screenshot.get('window_title', '')
        ocr_text = screenshot.get('ocr_text')
        
        if not window_title:
            logger.debug(f"Skipping entity {entity_id} - no window title")
            return False
        
        try:
            # Extract task
            if self.ai_available and self.ai_extractor:
                # Use AI-enhanced extraction
                result = self.ai_extractor.extract_enhanced_task(
                    window_title=window_title,
                    ocr_text=ocr_text,
                    entity_id=entity_id
                )
                task = result.get('task', 'Unknown Activity')
                category = result.get('category', ActivityCategorizer.DEFAULT_CATEGORY)
                confidence = result.get('confidence', 0.5)
            else:
                # Fallback to basic extraction
                task = self.task_extractor.extract_task(window_title, ocr_text)
                category = ActivityCategorizer.categorize(window_title)
                confidence = 0.5
            
            if not task:
                task = "Unknown Activity"
            
            # Save to database
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Save task
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, 'tasks', ?, 'auto_processor', 'text', datetime('now'), datetime('now'))
                """, (entity_id, task))
                
                # Save category
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, 'category', ?, 'auto_processor', 'text', datetime('now'), datetime('now'))
                """, (entity_id, category))
                
                # Save confidence score
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, 'task_confidence', ?, 'auto_processor', 'float', datetime('now'), datetime('now'))
                """, (entity_id, str(confidence)))
                
                conn.commit()
                
            logger.info(f"Processed entity {entity_id}: {task} ({category}) - confidence: {confidence:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing entity {entity_id}: {e}")
            return False
    
    def run_batch(self) -> int:
        """Process a batch of unprocessed screenshots."""
        screenshots = self.get_unprocessed_screenshots()
        
        if not screenshots:
            logger.debug("No unprocessed screenshots found")
            return 0
        
        logger.info(f"Processing {len(screenshots)} screenshots...")
        
        processed = 0
        for screenshot in screenshots:
            if self.process_screenshot(screenshot):
                processed += 1
                self.processed_count += 1
        
        logger.info(f"Batch complete: {processed}/{len(screenshots)} processed successfully")
        return processed
    
    def run_continuous(self):
        """Run continuous processing loop."""
        logger.info(f"Starting continuous processing (check every {self.check_interval}s)")
        logger.info(f"AI features available: {self.ai_available}")
        
        try:
            while True:
                start_time = time.time()
                
                # Process batch
                processed = self.run_batch()
                
                # Calculate processing time
                process_time = time.time() - start_time
                
                if processed > 0:
                    logger.info(f"Total processed: {self.processed_count} (took {process_time:.2f}s)")
                
                # Wait for next interval
                sleep_time = max(0, self.check_interval - process_time)
                if sleep_time > 0:
                    logger.debug(f"Sleeping for {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Stopping processor (user interrupt)")
        except Exception as e:
            logger.error(f"Processor error: {e}")
            raise
        finally:
            logger.info(f"Processor stopped. Total processed: {self.processed_count}")
    
    def catchup_processing(self, days_back: int = 7):
        """Process all unprocessed screenshots from the last N days."""
        logger.info(f"Running catchup processing for last {days_back} days...")
        
        total_processed = 0
        while True:
            processed = self.run_batch()
            if processed == 0:
                break
            total_processed += processed
            logger.info(f"Catchup progress: {total_processed} screenshots processed")
        
        logger.info(f"Catchup complete: {total_processed} total screenshots processed")
        return total_processed


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AutoTaskTracker Screenshot Processor')
    parser.add_argument('--interval', type=int, default=30,
                        help='Check interval in seconds (default: 30)')
    parser.add_argument('--catchup', type=int, metavar='DAYS',
                        help='Run catchup processing for N days')
    parser.add_argument('--batch', action='store_true',
                        help='Run single batch and exit')
    
    args = parser.parse_args()
    
    processor = ScreenshotProcessor(check_interval=args.interval)
    
    if args.catchup:
        processor.catchup_processing(args.catchup)
    elif args.batch:
        processor.run_batch()
    else:
        processor.run_continuous()


if __name__ == "__main__":
    main()