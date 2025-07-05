#!/usr/bin/env python3
"""
Automatic background processor for AutoTaskTracker.
Handles OCR processing and task extraction for new screenshots.
"""
import sys
import os
import time
import logging
from datetime import datetime
import signal
# sqlite3 removed - using DatabaseManager instead

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core.categorizer import ActivityCategorizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoProcessor:
    """Automatic processor for screenshots - handles OCR and task extraction."""
    
    def __init__(self, check_interval=30):
        from autotasktracker.config import get_config
        self.config = get_config()
        self.db_path = self.config.get_db_path()
        self.db = DatabaseManager(use_pensieve_api=True)
        self.task_extractor = get_task_extractor()
        self.categorizer = ActivityCategorizer()
        self.check_interval = check_interval
        self.running = True
        self.stats = {
            'ocr_processed': 0,
            'tasks_extracted': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Check OCR capability
        self.ocr_available = self._check_ocr_capability()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping...")
        self.running = False
    
    def _check_ocr_capability(self):
        """Check if OCR is available."""
        try:
            import ocrmac.ocrmac
            logger.info("OCR capability: ocrmac available")
            return 'ocrmac'
        except ImportError:
            try:
                import pytesseract
                logger.info("OCR capability: pytesseract available")
                return 'pytesseract'
            except ImportError:
                logger.warning("No OCR capability available")
                return None
    
    def process_ocr(self, entity_id, filepath):
        """Process OCR for a single screenshot."""
        if not self.ocr_available:
            return None
        
        try:
            if not os.path.exists(filepath):
                return None
            
            ocr_text = None
            
            if self.ocr_available == 'ocrmac':
                import ocrmac.ocrmac
                ocr_obj = ocrmac.ocrmac.OCR(filepath)
                ocr_obj.recognize()
                # Extract text from results
                text_parts = []
                if hasattr(ocr_obj, 'res') and ocr_obj.res:
                    for item in ocr_obj.res:
                        if isinstance(item, tuple) and len(item) >= 1:
                            text_parts.append(str(item[0]))
                ocr_text = ' '.join(text_parts) if text_parts else None
            
            elif self.ocr_available == 'pytesseract':
                import pytesseract
                from PIL import Image
                img = Image.open(filepath)
                ocr_text = pytesseract.image_to_string(img)
            
            if ocr_text:
                # Store in database using DatabaseManager
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, source, data_type, created_at, updated_at)
                    VALUES (?, 'ocr_text', ?, 'plugin', 'auto_processor', 'text', datetime('now'), datetime('now'))
                """, (entity_id, ocr_text))
                
                # Mark as processed by OCR plugin
                cursor.execute("""
                    INSERT OR REPLACE INTO entity_plugin_status 
                    (entity_id, plugin_id, processed_at)
                    VALUES (?, 2, datetime('now'))
                """, (entity_id,))
                
                conn.commit()
                conn.close()
                
                self.stats['ocr_processed'] += 1
                return ocr_text
                
        except Exception as e:
            logger.error(f"OCR processing error for {filepath}: {e}")
            self.stats['errors'] += 1
            
        return None
    
    def extract_task(self, entity_id, window_title, ocr_text=None):
        """Extract task from window title and OCR text."""
        try:
            # Extract task
            task = self.task_extractor.extract_task(window_title, ocr_text)
            if not task:
                task = "Unknown Activity"
            
            # Get category
            category = self.categorizer.categorize(window_title)
            
            # Store in database using DatabaseManager
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
            
            # Save task
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, "tasks", ?, 'auto_processor', 'text', datetime('now'), datetime('now'))
            """, (entity_id, task))
            
            # Save category
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, "category", ?, 'auto_processor', 'text', datetime('now'), datetime('now'))
            """, (entity_id, category))
            
            conn.commit()
            conn.close()
            
            self.stats['tasks_extracted'] += 1
            return task, category
            
        except Exception as e:
            logger.error(f"Task extraction error for entity {entity_id}: {e}")
            self.stats['errors'] += 1
            return None, None
    
    def get_unprocessed_screenshots(self, limit=50):
        """Get screenshots that need processing."""
        with self.db.get_connection(readonly=True) as conn:
            cursor = conn.cursor()
            
            # Find screenshots without OCR or tasks
            cursor.execute("""
                SELECT DISTINCT e.id, e.filepath, me1.value as window_title,
                       me2.value as ocr_text, me3.value as tasks
                FROM entities e
                LEFT JOIN metadata_entries me1 ON e.id = me1.entity_id AND me1.key = "active_window"
                LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'ocr_text'
                LEFT JOIN metadata_entries me3 ON e.id = me3.entity_id AND me3.key = "tasks"
                WHERE e.file_type_group = 'image'
                AND (me2.id IS NULL OR me3.id IS NULL)
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            return results
    
    def process_batch(self, limit=None):
        """Process a batch of screenshots."""
        batch_limit = limit or 50
        screenshots = self.get_unprocessed_screenshots(batch_limit)
        
        if not screenshots:
            return 0
        
        logger.info(f"Processing {len(screenshots)} screenshots...")
        processed = 0
        
        for entity_id, filepath, window_title, ocr_text, tasks in screenshots:
            # Process OCR if needed
            if not ocr_text and filepath:
                ocr_text = self.process_ocr(entity_id, filepath)
                if ocr_text:
                    logger.debug(f"OCR completed for entity {entity_id}")
            
            # Extract task if needed and window title exists
            if not tasks and window_title:
                task, category = self.extract_task(entity_id, window_title, ocr_text)
                if task:
                    logger.debug(f"Task extracted for entity {entity_id}: {task} ({category})")
            
            processed += 1
        
        return processed
    
    def run_continuous(self):
        """Run continuous processing loop."""
        logger.info(f"Starting automatic processor (check every {self.check_interval}s)")
        logger.info(f"OCR: {self.ocr_available or 'Not available'}")
        
        try:
            while self.running:
                start_time = time.time()
                
                # Process batch
                processed = self.process_batch()
                
                if processed > 0:
                    elapsed = time.time() - start_time
                    logger.info(f"Processed {processed} screenshots in {elapsed:.1f}s")
                    logger.info(f"Stats - OCR: {self.stats['ocr_processed']}, Tasks: {self.stats['tasks_extracted']}, Errors: {self.stats['errors']}")
                
                # Wait for next interval
                sleep_time = max(0, self.check_interval - (time.time() - start_time))
                if sleep_time > 0 and self.running:
                    time.sleep(sleep_time)
                    
        except Exception as e:
            logger.error(f"Processor error: {e}")
            raise
        finally:
            self._print_summary()
    
    def _print_summary(self):
        """Print processing summary."""
        runtime = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info("\n=== Processing Summary ===")
        logger.info(f"Runtime: {runtime:.1f} seconds")
        logger.info(f"OCR processed: {self.stats['ocr_processed']}")
        logger.info(f"Tasks extracted: {self.stats['tasks_extracted']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        # Check current coverage
        with self.db.get_connection(readonly=True) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM entities WHERE file_type_group = 'image'")
            total_screenshots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM metadata_entries WHERE key = 'ocr_text'")
            ocr_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM metadata_entries WHERE key = "tasks"")
            task_count = cursor.fetchone()[0]
        
        logger.info(f"\nCoverage:")
        logger.info(f"- OCR: {ocr_count}/{total_screenshots} ({ocr_count/total_screenshots*100:.1f}%)")
        logger.info(f"- Tasks: {task_count}/{total_screenshots} ({task_count/total_screenshots*100:.1f}%)")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AutoTaskTracker Automatic Processor')
    parser.add_argument('--interval', type=int, default=30,
                        help='Check interval in seconds (default: 30)')
    parser.add_argument('--batch', action='store_true',
                        help='Run single batch and exit')
    parser.add_argument('--limit', type=int, default=50,
                        help='Batch size limit (default: 50)')
    
    args = parser.parse_args()
    
    processor = AutoProcessor(check_interval=args.interval)
    
    if args.batch:
        processed = processor.process_batch(limit=args.limit)
        logger.info(f"Batch complete: {processed} screenshots processed")
        processor._print_summary()
    else:
        processor.run_continuous()


if __name__ == "__main__":
    main()