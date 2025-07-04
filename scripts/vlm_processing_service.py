#!/usr/bin/env python3
"""
VLM Processing Service - Efficient background processor for VLM tasks
"""
import sys
import os
import time
import logging
import threading
import queue
from pathlib import Path
from datetime import datetime, timedelta
import signal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_processor import SmartVLMProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VLMProcessingService:
    """Background service for efficient VLM processing."""
    
    def __init__(self, max_workers=2, batch_size=5):
        """Initialize the VLM processing service."""
        self.db = DatabaseManager()
        self.processor = SmartVLMProcessor()
        self.max_workers = max_workers
        self.batch_size = batch_size
        
        # Processing queue
        self.queue = queue.PriorityQueue()
        self.batch_queue = queue.Queue()  # For batch processing
        self.workers = []
        self.running = False
        
        # Stats
        self.stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
    def start(self):
        """Start the processing service."""
        logger.info(f"Starting VLM Processing Service with {self.max_workers} workers")
        self.running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        # Start queue filler thread
        filler = threading.Thread(target=self._fill_queue)
        filler.daemon = True
        filler.start()
        
        # Start stats reporter thread
        reporter = threading.Thread(target=self._report_stats)
        reporter.daemon = True
        reporter.start()
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._shutdown()
    
    def _shutdown(self, signum=None, frame=None):
        """Graceful shutdown."""
        logger.info("Shutting down VLM Processing Service...")
        self.running = False
        
        # Save processor cache
        self.processor._save_cache()
        
        # Final stats
        self._print_final_stats()
        
        sys.exit(0)
    
    def _worker(self, worker_id):
        """Worker thread to process VLM tasks in batches."""
        logger.info(f"Worker {worker_id} started")
        
        batch = []
        last_batch_time = time.time()
        
        while self.running:
            try:
                # Try to fill batch
                timeout = 0.5 if len(batch) < self.batch_size else 0.1
                
                try:
                    priority, task = self.queue.get(timeout=timeout)
                    batch.append(task)
                except queue.Empty:
                    pass
                
                # Process batch if full or timeout
                should_process_batch = (
                    len(batch) >= self.batch_size or 
                    (len(batch) > 0 and time.time() - last_batch_time > 5) or
                    (len(batch) > 0 and self.queue.empty())
                )
                
                if should_process_batch and batch:
                    start_time = time.time()
                    processed = self._process_batch(batch, worker_id)
                    processing_time = time.time() - start_time
                    
                    logger.info(f"Worker {worker_id} processed batch of {len(batch)} in {processing_time:.1f}s ({processing_time/len(batch):.1f}s per item)")
                    
                    # Clear batch
                    batch = []
                    last_batch_time = time.time()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.stats['errors'] += 1
                batch = []  # Clear batch on error
    
    def _process_batch(self, batch, worker_id):
        """Process a batch of VLM tasks with atomic processing."""
        processed = 0
        
        # Prepare tasks with entity IDs for atomic processing
        tasks = []
        for task in batch:
            tasks.append({
                'filepath': task['filepath'],
                'entity_id': task['entity_id'],
                'window_title': task.get('window_title'),
                'ocr_text': task.get('ocr_text'),
                'priority': task.get('priority', 'normal')
            })
        
        # Process batch with atomic checking
        try:
            results = self.processor.batch_process(tasks, max_concurrent=1)  # Single thread per worker
            
            # Store results (already stored by processor now)
            for filepath, result in results.items():
                if result:
                    self.stats['processed'] += 1
                    processed += 1
                else:
                    self.stats['skipped'] += 1
            
            # Mark tasks as done
            for _ in batch:
                self.queue.task_done()
                
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            self.stats['errors'] += len(batch)
            # Mark tasks as done even on error
            for _ in batch:
                self.queue.task_done()
        
        return processed
    
    def _store_vlm_result(self, entity_id, result):
        """Store VLM result in database."""
        try:
            import json
            with self.db.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                
                # Store as structured JSON
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata_entries 
                    (entity_id, key, value, source_type, created_at) 
                    VALUES (?, ?, ?, 'vlm', datetime('now'))
                """, (entity_id, 'vlm_structured', json.dumps(result)))
                
                # Also store description for compatibility
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata_entries 
                    (entity_id, key, value, source_type, created_at) 
                    VALUES (?, ?, ?, 'vlm', datetime('now'))
                """, (entity_id, 'minicpm_v_result', result['description']))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store VLM result: {e}")
    
    def _fill_queue(self):
        """Fill the processing queue with pending tasks."""
        while self.running:
            try:
                # Get unprocessed screenshots
                query = """
                SELECT 
                    e.id as entity_id,
                    e.filepath,
                    me_window.value as window_title,
                    me_ocr.value as ocr_text,
                    datetime(e.created_at) as created_at
                FROM entities e
                LEFT JOIN metadata_entries me_vlm 
                    ON e.id = me_vlm.entity_id 
                    AND me_vlm.key IN ('minicpm_v_result', 'vlm_structured')
                LEFT JOIN metadata_entries me_window 
                    ON e.id = me_window.entity_id 
                    AND me_window.key = 'active_window'
                LEFT JOIN metadata_entries me_ocr 
                    ON e.id = me_ocr.entity_id 
                    AND me_ocr.key = 'ocr_result'
                WHERE e.file_type_group = 'image'
                AND me_vlm.value IS NULL
                AND e.created_at >= datetime('now', '-24 hours')
                ORDER BY e.created_at DESC
                LIMIT 100
                """
                
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    tasks = cursor.fetchall()
                
                # Add tasks to queue with priority
                added = 0
                for task in tasks:
                    task_dict = dict(task)
                    
                    # Skip if should not process
                    should_process, reason = self.processor.should_process(
                        task_dict['filepath'],
                        task_dict.get('window_title')
                    )
                    
                    if should_process:
                        # Calculate priority (newer = higher priority)
                        created_at = datetime.fromisoformat(task_dict['created_at'])
                        age_hours = (datetime.now() - created_at).total_seconds() / 3600
                        priority = max(1, min(10, int(age_hours)))  # 1-10, lower is higher priority
                        
                        task_dict['priority'] = 'high' if priority <= 2 else 'normal'
                        
                        self.queue.put((priority, task_dict))
                        added += 1
                
                if added > 0:
                    logger.info(f"Added {added} tasks to processing queue")
                
                # Sleep before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error filling queue: {e}")
                time.sleep(60)
    
    def _report_stats(self):
        """Periodically report processing statistics."""
        while self.running:
            time.sleep(60)  # Report every minute
            
            runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
            rate = self.stats['processed'] / runtime if runtime > 0 else 0
            
            logger.info(f"Stats - Processed: {self.stats['processed']}, "
                       f"Skipped: {self.stats['skipped']}, "
                       f"Errors: {self.stats['errors']}, "
                       f"Rate: {rate:.1f}/min, "
                       f"Queue: {self.queue.qsize()}")
            
            # Also log processor stats
            proc_stats = self.processor.get_processing_stats()
            if proc_stats:
                logger.info(f"Processor - Cached: {proc_stats['cached_results']}, "
                           f"Avg time: {proc_stats.get('avg_processing_time', 0):.1f}s, "
                           f"Cache hit rate: {proc_stats.get('cache_hit_rate', 0):.1%}")
    
    def _print_final_stats(self):
        """Print final statistics on shutdown."""
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        
        print("\n" + "="*50)
        print("VLM Processing Service - Final Statistics")
        print("="*50)
        print(f"Runtime: {runtime:.1f} minutes")
        print(f"Total processed: {self.stats['processed']}")
        print(f"Total skipped: {self.stats['skipped']}")
        print(f"Total errors: {self.stats['errors']}")
        print(f"Processing rate: {self.stats['processed'] / runtime:.1f} per minute")
        
        proc_stats = self.processor.get_processing_stats()
        if proc_stats:
            print(f"\nProcessor Statistics:")
            print(f"Cache size: {proc_stats['cached_results']} results")
            print(f"Avg processing time: {proc_stats.get('avg_processing_time', 0):.1f}s")
            print(f"Cache hit rate: {proc_stats.get('cache_hit_rate', 0):.1%}")
        print("="*50)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VLM Processing Service')
    parser.add_argument('--workers', type=int, default=2,
                       help='Number of worker threads (default: 2)')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Batch size for processing (default: 5)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start service
    service = VLMProcessingService(
        max_workers=args.workers,
        batch_size=args.batch_size
    )
    
    logger.info("Starting VLM Processing Service...")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Batch size: {args.batch_size}")
    
    try:
        service.start()
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()