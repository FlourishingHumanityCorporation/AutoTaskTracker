#!/usr/bin/env python3
"""
VLM Batch Optimizer - High-performance batch processing for VLM
"""
import sys
import os
import time
import asyncio
import aiohttp
import base64
import json
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_processor import SmartVLMProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLMBatchOptimizer:
    """Optimized batch processor for VLM with async operations."""
    
    def __init__(self, max_concurrent=5, image_size=768):
        self.max_concurrent = max_concurrent
        self.image_size = image_size
        self.db = DatabaseManager()
        self.processor = SmartVLMProcessor()
        
    async def process_batch_async(self, tasks: List[Dict]) -> Dict[str, Dict]:
        """Process a batch of images asynchronously."""
        async with aiohttp.ClientSession() as session:
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            # Process all tasks concurrently
            results = await asyncio.gather(
                *[self._process_single_async(task, session, semaphore) for task in tasks],
                return_exceptions=True
            )
            
            # Map results back to tasks
            processed_results = {}
            for task, result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing {task['filepath']}: {result}")
                elif result:
                    processed_results[task['filepath']] = result
                    
            return processed_results
    
    async def _process_single_async(self, task: Dict, session: aiohttp.ClientSession, 
                                   semaphore: asyncio.Semaphore) -> Dict:
        """Process a single image asynchronously."""
        async with semaphore:
            try:
                # Check if should process
                should_process, reason = self.processor.should_process(
                    task['filepath'], 
                    task.get('window_title')
                )
                
                if not should_process:
                    return None
                
                # Prepare image in thread pool (CPU-bound)
                loop = asyncio.get_event_loop()
                image_base64 = await loop.run_in_executor(
                    None, 
                    self._prepare_image, 
                    task['filepath']
                )
                
                if not image_base64:
                    return None
                
                # Get appropriate prompt
                app_type = self.processor.detect_application_type(
                    task.get('window_title', ''),
                    task.get('ocr_text', '')
                )
                prompt = self.processor.task_prompts[app_type]
                
                # Make async API call
                result = await self._call_vlm_async(
                    session, 
                    image_base64, 
                    prompt,
                    task.get('priority', 'normal')
                )
                
                if result:
                    # Structure the result
                    structured = self.processor._structure_vlm_result(
                        result, 
                        app_type, 
                        task.get('window_title', '')
                    )
                    structured['entity_id'] = task['entity_id']
                    return structured
                    
            except Exception as e:
                logger.error(f"Error processing {task['filepath']}: {e}")
                return None
    
    def _prepare_image(self, image_path: str) -> str:
        """Prepare and encode image for VLM processing."""
        try:
            with Image.open(image_path) as img:
                # Resize for faster processing
                if img.width > self.image_size or img.height > self.image_size:
                    img.thumbnail((self.image_size, self.image_size), Image.Resampling.LANCZOS)
                
                # Convert to RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Encode to base64
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=80)
                return base64.b64encode(buffer.getvalue()).decode()
                
        except Exception as e:
            logger.error(f"Error preparing image {image_path}: {e}")
            return None
    
    async def _call_vlm_async(self, session: aiohttp.ClientSession, 
                             image_base64: str, prompt: str, priority: str) -> str:
        """Make async VLM API call."""
        timeout = aiohttp.ClientTimeout(total=15)
        
        try:
            async with session.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'minicpm-v',
                    'prompt': prompt,
                    'images': [image_base64],
                    'options': {
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'max_tokens': 250,
                        'num_predict': 250
                    }
                },
                timeout=timeout
            ) as response:
                full_response = ""
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            full_response += data.get('response', '')
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
                return full_response
                
        except asyncio.TimeoutError:
            logger.warning("VLM request timeout")
            return None
        except Exception as e:
            logger.error(f"VLM API error: {e}")
            return None
    
    def get_pending_tasks(self, limit: int = 100) -> List[Dict]:
        """Get pending VLM tasks from database."""
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
        AND e.created_at >= datetime('now', '-7 days')
        ORDER BY e.created_at DESC
        LIMIT ?
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def store_results(self, results: Dict[str, Dict]):
        """Store VLM results in database."""
        with self.db.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            
            for filepath, result in results.items():
                if 'entity_id' in result:
                    # Store structured result
                    cursor.execute("""
                        INSERT OR REPLACE INTO metadata_entries 
                        (entity_id, key, value, source_type, created_at) 
                        VALUES (?, ?, ?, 'vlm', datetime('now'))
                    """, (result['entity_id'], 'vlm_structured', json.dumps(result)))
                    
                    # Store description for compatibility
                    cursor.execute("""
                        INSERT OR REPLACE INTO metadata_entries 
                        (entity_id, key, value, source_type, created_at) 
                        VALUES (?, ?, ?, 'vlm', datetime('now'))
                    """, (result['entity_id'], 'minicpm_v_result', result['description']))
            
            conn.commit()
            logger.info(f"Stored {len(results)} VLM results")
    
    async def run_optimization(self, batch_size: int = 20, max_batches: int = 10):
        """Run the optimization process."""
        logger.info(f"Starting VLM batch optimization (batch_size={batch_size}, max_concurrent={self.max_concurrent})")
        
        total_processed = 0
        total_time = 0
        
        for batch_num in range(max_batches):
            # Get pending tasks
            tasks = self.get_pending_tasks(limit=batch_size)
            
            if not tasks:
                logger.info("No more tasks to process")
                break
            
            logger.info(f"Processing batch {batch_num + 1} with {len(tasks)} tasks")
            
            # Process batch
            start_time = time.time()
            results = await self.process_batch_async(tasks)
            batch_time = time.time() - start_time
            
            # Store results
            if results:
                self.store_results(results)
                
                # Update cache
                for filepath, result in results.items():
                    img_hash = self.processor.get_image_hash(filepath)
                    self.processor.result_cache[img_hash] = result
                
                self.processor._save_cache()
            
            # Stats
            total_processed += len(results)
            total_time += batch_time
            
            logger.info(f"Batch {batch_num + 1} completed: {len(results)} processed in {batch_time:.1f}s ({batch_time/len(tasks):.1f}s per item)")
            
            # Brief pause between batches
            await asyncio.sleep(1)
        
        # Final stats
        if total_processed > 0:
            avg_time = total_time / total_processed
            logger.info(f"\nOptimization complete:")
            logger.info(f"  Total processed: {total_processed}")
            logger.info(f"  Total time: {total_time:.1f}s")
            logger.info(f"  Average time: {avg_time:.1f}s per image")
            logger.info(f"  Throughput: {total_processed / total_time:.1f} images/second")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VLM Batch Optimizer')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of images per batch (default: 20)')
    parser.add_argument('--max-concurrent', type=int, default=5,
                       help='Maximum concurrent VLM requests (default: 5)')
    parser.add_argument('--max-batches', type=int, default=10,
                       help='Maximum number of batches to process (default: 10)')
    parser.add_argument('--image-size', type=int, default=768,
                       help='Maximum image dimension (default: 768)')
    
    args = parser.parse_args()
    
    # Create optimizer
    optimizer = VLMBatchOptimizer(
        max_concurrent=args.max_concurrent,
        image_size=args.image_size
    )
    
    # Run optimization
    await optimizer.run_optimization(
        batch_size=args.batch_size,
        max_batches=args.max_batches
    )


if __name__ == '__main__':
    asyncio.run(main())