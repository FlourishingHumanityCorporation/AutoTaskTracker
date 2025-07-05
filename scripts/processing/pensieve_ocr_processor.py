#!/usr/bin/env python3
"""
Process screenshots using Pensieve's built-in OCR plugin.
This ensures OCR runs through the proper plugin system.
"""
import sys
import os
import time
import logging
from datetime import datetime
import requests
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.pensieve.api_client import get_pensieve_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PensieveOCRProcessor:
    """Process screenshots using Pensieve's OCR plugin."""
    
    def __init__(self):
        from autotasktracker.config import get_config
        config = get_config()
        self.db_path = config.get_db_path()
        self.pensieve_client = get_pensieve_client()
        self.ocr_plugin_id = 2  # builtin_ocr plugin ID
        self.config = config
    
    def get_unprocessed_screenshots(self, limit=100):
        """Get screenshots that haven't been processed by OCR plugin."""
        from autotasktracker.core import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.id, e.filepath 
                FROM entities e
                WHERE e.file_type_group = 'image'
                AND NOT EXISTS (
                    SELECT 1 FROM entity_plugin_status eps
                    WHERE eps.entity_id = e.id 
                    AND eps.plugin_id = ?
                )
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (self.ocr_plugin_id, limit))
            
            results = cursor.fetchall()
            
        return results
    
    def trigger_ocr_plugin(self, entity_id):
        """Trigger OCR plugin for a specific entity."""
        try:
            # Use Pensieve API to trigger plugin processing
            # The OCR plugin webhook is at /api/plugins/ocr
            response = requests.post(
                f'http://{self.config.SERVER_HOST}:{self.config.MEMOS_PORT}/api/plugins/ocr',
                json={'entity_id': entity_id},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"OCR plugin triggered for entity {entity_id}")
                return True
            else:
                logger.error(f"Failed to trigger OCR for entity {entity_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering OCR plugin: {e}")
            return False
    
    def process_batch(self, limit=50):
        """Process a batch of unprocessed screenshots."""
        unprocessed = self.get_unprocessed_screenshots(limit)
        logger.info(f"Found {len(unprocessed)} unprocessed screenshots")
        
        if not unprocessed:
            return 0
        
        processed = 0
        for entity_id, filepath in unprocessed:
            if self.trigger_ocr_plugin(entity_id):
                processed += 1
                logger.info(f"Processed {filepath}")
                time.sleep(0.5)  # Small delay to avoid overwhelming the system
        
        return processed
    
    def run_continuous(self, check_interval=60):
        """Run continuous OCR processing."""
        logger.info(f"Starting continuous OCR processing (check every {check_interval}s)")
        
        try:
            while True:
                start_time = time.time()
                
                # Process batch
                processed = self.process_batch()
                
                if processed > 0:
                    logger.info(f"Processed {processed} screenshots")
                
                # Wait for next interval
                elapsed = time.time() - start_time
                sleep_time = max(0, check_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Stopping OCR processor")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pensieve OCR Processor')
    parser.add_argument('--batch', action='store_true', 
                        help='Run single batch and exit')
    parser.add_argument('--limit', type=int, default=50,
                        help='Batch size limit')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds')
    
    args = parser.parse_args()
    
    processor = PensieveOCRProcessor()
    
    if args.batch:
        processed = processor.process_batch(args.limit)
        logger.info(f"Batch complete: {processed} screenshots processed")
    else:
        processor.run_continuous(args.interval)


if __name__ == "__main__":
    main()