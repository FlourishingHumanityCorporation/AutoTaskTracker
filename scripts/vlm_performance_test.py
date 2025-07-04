#!/usr/bin/env python3
"""
Test VLM Optimization - Compare performance before and after optimization
"""
import sys
import os
import time
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_processor import SmartVLMProcessor
from scripts.vlm_batch_optimizer import VLMBatchOptimizer


def test_single_processing(limit=10):
    """Test traditional single-threaded processing."""
    print("🐌 Testing Single-Threaded Processing...")
    
    db = DatabaseManager()
    processor = SmartVLMProcessor()
    
    # Get test images
    query = """
    SELECT 
        e.id as entity_id,
        e.filepath,
        me_window.value as window_title
    FROM entities e
    LEFT JOIN metadata_entries me_vlm 
        ON e.id = me_vlm.entity_id 
        AND me_vlm.key IN ('minicpm_v_result', 'vlm_structured')
    LEFT JOIN metadata_entries me_window 
        ON e.id = me_window.entity_id 
        AND me_window.key = 'active_window'
    WHERE e.file_type_group = 'image'
    AND me_vlm.value IS NULL
    ORDER BY RANDOM()
    LIMIT ?
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        tasks = cursor.fetchall()
    
    if not tasks:
        print("No test images found")
        return 0, 0
    
    processed = 0
    start_time = time.time()
    
    for task in tasks:
        try:
            result = processor.process_image(
                task['filepath'],
                task['window_title']
            )
            if result:
                processed += 1
                print(f"  ✅ Processed {task['filepath'][-30:]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    total_time = time.time() - start_time
    
    print(f"\n📊 Single-threaded Results:")
    print(f"  Processed: {processed}/{len(tasks)}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average: {total_time/len(tasks):.1f}s per image")
    
    return processed, total_time


def test_batch_processing(limit=10):
    """Test optimized batch processing."""
    print("\n🚀 Testing Batch Processing...")
    
    db = DatabaseManager()
    processor = SmartVLMProcessor()
    
    # Get test images
    query = """
    SELECT filepath FROM entities e
    LEFT JOIN metadata_entries me_vlm 
        ON e.id = me_vlm.entity_id 
        AND me_vlm.key IN ('minicpm_v_result', 'vlm_structured')
    WHERE e.file_type_group = 'image'
    AND me_vlm.value IS NULL
    ORDER BY RANDOM()
    LIMIT ?
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        filepaths = [row['filepath'] for row in cursor.fetchall()]
    
    if not filepaths:
        print("No test images found")
        return 0, 0
    
    start_time = time.time()
    
    # Process batch with concurrency
    results = processor.batch_process(filepaths, max_concurrent=3)
    
    total_time = time.time() - start_time
    processed = len(results)
    
    print(f"\n📊 Batch Processing Results:")
    print(f"  Processed: {processed}/{len(filepaths)}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average: {total_time/len(filepaths):.1f}s per image")
    
    return processed, total_time


async def test_async_processing(limit=10):
    """Test async batch optimization."""
    print("\n⚡ Testing Async Batch Optimization...")
    
    optimizer = VLMBatchOptimizer(max_concurrent=5, image_size=768)
    
    # Get test tasks
    tasks = optimizer.get_pending_tasks(limit=limit)
    
    if not tasks:
        print("No test tasks found")
        return 0, 0
    
    start_time = time.time()
    
    # Process async
    results = await optimizer.process_batch_async(tasks)
    
    total_time = time.time() - start_time
    processed = len(results)
    
    print(f"\n📊 Async Optimization Results:")
    print(f"  Processed: {processed}/{len(tasks)}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average: {total_time/len(tasks):.1f}s per image")
    print(f"  Throughput: {processed/total_time:.2f} images/second")
    
    return processed, total_time


def main():
    """Run performance comparison tests."""
    print("🔬 VLM Optimization Performance Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Test configuration
    test_size = 10
    
    # Check if Ollama is running
    import subprocess
    ollama_check = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'],
                                 capture_output=True)
    if ollama_check.returncode != 0:
        print("❌ Ollama is not running. Please start it with: ollama serve")
        return
    
    # Run tests
    results = {}
    
    # Single-threaded test
    single_processed, single_time = test_single_processing(test_size)
    results['single'] = (single_processed, single_time)
    
    # Batch processing test
    batch_processed, batch_time = test_batch_processing(test_size)
    results['batch'] = (batch_processed, batch_time)
    
    # Async processing test
    async_processed, async_time = asyncio.run(test_async_processing(test_size))
    results['async'] = (async_processed, async_time)
    
    # Summary comparison
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE COMPARISON SUMMARY")
    print("=" * 50)
    
    if results['single'][0] > 0:
        single_avg = results['single'][1] / test_size
        batch_avg = results['batch'][1] / test_size if results['batch'][0] > 0 else float('inf')
        async_avg = results['async'][1] / test_size if results['async'][0] > 0 else float('inf')
        
        print(f"\nAverage Processing Time per Image:")
        print(f"  Single-threaded: {single_avg:.1f}s")
        print(f"  Batch processing: {batch_avg:.1f}s ({single_avg/batch_avg:.1f}x speedup)")
        print(f"  Async optimization: {async_avg:.1f}s ({single_avg/async_avg:.1f}x speedup)")
        
        print(f"\nThroughput (images/second):")
        print(f"  Single-threaded: {1/single_avg:.2f}")
        print(f"  Batch processing: {1/batch_avg:.2f}")
        print(f"  Async optimization: {1/async_avg:.2f}")
    
    print("\n✅ Test completed!")


if __name__ == '__main__':
    main()