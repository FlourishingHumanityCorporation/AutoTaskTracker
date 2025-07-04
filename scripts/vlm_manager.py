#!/usr/bin/env python3
"""
VLM Manager - Comprehensive management for VLM processing
"""
import sys
import os
import subprocess
import time
from pathlib import Path
import click

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_processor import SmartVLMProcessor


@click.group()
def cli():
    """VLM Manager - Control VLM processing for AutoTaskTracker"""
    pass


@cli.command()
def status():
    """Check VLM processing status"""
    db = DatabaseManager()
    
    # Get overall stats
    stats = db.get_ai_coverage_stats()
    
    # Get recent processing
    query = """
    SELECT 
        COUNT(*) as vlm_last_hour,
        MIN(datetime(e.created_at, 'localtime')) as oldest,
        MAX(datetime(e.created_at, 'localtime')) as newest
    FROM entities e
    JOIN metadata_entries me ON e.id = me.entity_id 
    WHERE me.key IN ('minicpm_v_result', 'vlm_structured')
    AND e.created_at >= datetime('now', '-1 hour')
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        recent = cursor.fetchone()
    
    # Check services
    memos_running = subprocess.run(['pgrep', '-f', 'memos watch'], 
                                  capture_output=True).returncode == 0
    service_running = subprocess.run(['pgrep', '-f', 'vlm_processing_service'], 
                                    capture_output=True).returncode == 0
    ollama_running = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'],
                                   capture_output=True).returncode == 0
    
    print("🔍 VLM Status Report")
    print("=" * 50)
    
    # Service status
    print("\n📊 Services:")
    print(f"  Memos Watch: {'✅ Running' if memos_running else '❌ Stopped'}")
    print(f"  VLM Service: {'✅ Running' if service_running else '❌ Stopped'}")
    print(f"  Ollama: {'✅ Running' if ollama_running else '❌ Stopped'}")
    
    # Coverage stats
    print(f"\n📈 Coverage:")
    print(f"  Total screenshots: {stats['total_screenshots']:,}")
    print(f"  VLM processed: {stats['vlm_count']:,} ({stats['vlm_percentage']:.1f}%)")
    print(f"  OCR processed: {stats['ocr_count']:,} ({stats['ocr_percentage']:.1f}%)")
    
    # Recent activity
    print(f"\n⏰ Recent Activity:")
    print(f"  Last hour: {recent['vlm_last_hour']} processed")
    if recent['oldest'] and recent['newest']:
        print(f"  Time range: {recent['oldest'][:16]} - {recent['newest'][11:16]}")
    
    # Cache status
    processor = SmartVLMProcessor()
    proc_stats = processor.get_processing_stats()
    if proc_stats:
        print(f"\n💾 Cache:")
        print(f"  Cached results: {proc_stats.get('cached_results', 0)}")
        if proc_stats.get('cache_hit_rate') is not None:
            print(f"  Cache hit rate: {proc_stats['cache_hit_rate']:.1%}")


@cli.command()
@click.option('--workers', default=2, help='Number of worker threads')
@click.option('--daemon', is_flag=True, help='Run as daemon process')
def start(workers, daemon):
    """Start VLM processing service"""
    cmd = [
        sys.executable, 
        'scripts/vlm_processing_service.py',
        '--workers', str(workers)
    ]
    
    if daemon:
        # Run in background
        log_file = Path.home() / '.memos' / 'logs' / 'vlm_service.log'
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=log,
                start_new_session=True
            )
        
        print(f"✅ VLM Service started (PID: {process.pid})")
        print(f"   Logs: {log_file}")
    else:
        # Run in foreground
        subprocess.run(cmd)


@cli.command()
def stop():
    """Stop VLM processing service"""
    result = subprocess.run(['pkill', '-f', 'vlm_processing_service'], 
                          capture_output=True)
    
    if result.returncode == 0:
        print("✅ VLM Service stopped")
    else:
        print("❌ VLM Service not running")


@cli.command()
@click.option('--limit', default=10, help='Number of images to process')
@click.option('--force', is_flag=True, help='Force reprocessing')
def process(limit, force):
    """Process pending VLM tasks"""
    db = DatabaseManager()
    processor = SmartVLMProcessor()
    
    # Get unprocessed screenshots
    query = """
    SELECT 
        e.id,
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
    AND (me_vlm.value IS NULL OR ?)
    ORDER BY e.created_at DESC
    LIMIT ?
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (force, limit))
        tasks = cursor.fetchall()
    
    print(f"🔄 Processing {len(tasks)} screenshots...")
    
    processed = 0
    skipped = 0
    errors = 0
    
    for task in tasks:
        try:
            # Check if should process
            if not force:
                should_proc, reason = processor.should_process(
                    task['filepath'], 
                    task['window_title']
                )
                if not should_proc:
                    print(f"⏭️  Skipped: {reason}")
                    skipped += 1
                    continue
            
            # Process
            print(f"🔄 Processing: {task['filepath'][-50:]}")
            result = processor.process_image(
                task['filepath'],
                task['window_title']
            )
            
            if result:
                processed += 1
                print(f"✅ Processed successfully")
                
                # Store result
                import json
                with db.get_connection(readonly=False) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO metadata_entries 
                        (entity_id, key, value, source_type, created_at) 
                        VALUES (?, ?, ?, 'vlm', datetime('now'))
                    """, (task['id'], 'vlm_structured', json.dumps(result)))
                    conn.commit()
            else:
                errors += 1
                print(f"❌ Processing failed")
                
        except Exception as e:
            errors += 1
            print(f"❌ Error: {e}")
    
    # Final report
    print(f"\n📊 Summary:")
    print(f"  Processed: {processed}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    
    # Save cache
    processor._save_cache()


@cli.command()
def clear_cache():
    """Clear VLM processing cache"""
    cache_dir = Path.home() / '.memos' / 'vlm_cache'
    cache_file = cache_dir / 'vlm_cache.json'
    
    if cache_file.exists():
        cache_file.unlink()
        print("✅ VLM cache cleared")
    else:
        print("ℹ️  No cache found")


@cli.command()
@click.option('--days', default=7, help='Analyze last N days')
def analyze(days):
    """Analyze VLM processing performance"""
    db = DatabaseManager()
    
    # Get processing times
    query = """
    SELECT 
        e.id,
        datetime(e.created_at, 'localtime') as screenshot_time,
        datetime(me.created_at, 'localtime') as vlm_time,
        (julianday(me.created_at) - julianday(e.created_at)) * 24 * 60 as delay_minutes,
        LENGTH(me.value) as result_length
    FROM entities e
    JOIN metadata_entries me ON e.id = me.entity_id
    WHERE me.key IN ('minicpm_v_result', 'vlm_structured')
    AND e.created_at >= datetime('now', '-{} days')
    ORDER BY e.created_at DESC
    """.format(days)
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
    
    if not results:
        print("No VLM processing data found")
        return
    
    print(f"📊 VLM Performance Analysis (Last {days} days)")
    print("=" * 50)
    
    # Calculate metrics
    delays = [r['delay_minutes'] for r in results if r['delay_minutes'] is not None]
    lengths = [r['result_length'] for r in results if r['result_length'] is not None]
    
    if delays:
        print(f"\n⏱️  Processing Delays:")
        print(f"  Average: {sum(delays)/len(delays):.1f} minutes")
        print(f"  Min: {min(delays):.1f} minutes")
        print(f"  Max: {max(delays):.1f} minutes")
    
    if lengths:
        print(f"\n📝 Result Quality:")
        print(f"  Average length: {sum(lengths)/len(lengths):.0f} chars")
        print(f"  Min: {min(lengths)} chars")
        print(f"  Max: {max(lengths)} chars")
    
    # Hourly distribution
    print(f"\n📈 Processing by Hour:")
    hourly = {}
    for r in results:
        if r['vlm_time']:
            hour = int(r['vlm_time'][11:13])
            hourly[hour] = hourly.get(hour, 0) + 1
    
    for hour in sorted(hourly.keys()):
        bar = '█' * min(hourly[hour] // 5, 20)
        print(f"  {hour:02d}:00 {bar} {hourly[hour]}")


@cli.command()
def benchmark():
    """Benchmark VLM processing speed"""
    processor = SmartVLMProcessor()
    
    print("🏃 Running VLM benchmark...")
    
    # Get a test image
    db = DatabaseManager()
    query = """
    SELECT e.filepath, me.value as active_window 
    FROM entities e
    LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'active_window'
    WHERE e.file_type_group = 'image'
    ORDER BY e.created_at DESC
    LIMIT 1
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        test_image = cursor.fetchone()
    
    if not test_image:
        print("No test image found")
        return
    
    # Test processing
    filepath = test_image['filepath']
    window = test_image['active_window']
    
    print(f"\nTest image: {filepath[-50:]}")
    print(f"Window: {window[:50] if window else 'Unknown'}...")
    
    # Time different operations
    import time
    
    # Hash calculation
    start = time.time()
    hash_val = processor.get_image_hash(filepath)
    hash_time = time.time() - start
    print(f"\n⚡ Hash calculation: {hash_time*1000:.1f}ms")
    
    # App detection
    start = time.time()
    app_type = processor.detect_application_type(window or '')
    detect_time = time.time() - start
    print(f"⚡ App detection: {detect_time*1000:.1f}ms")
    
    # Should process check
    start = time.time()
    should_proc, reason = processor.should_process(filepath, window)
    check_time = time.time() - start
    print(f"⚡ Should process check: {check_time*1000:.1f}ms ({reason})")
    
    # Full processing (if not cached)
    if should_proc:
        print(f"\n🔄 Processing with VLM...")
        start = time.time()
        result = processor.process_image(filepath, window)
        process_time = time.time() - start
        
        if result:
            print(f"✅ VLM processing: {process_time:.1f}s")
            print(f"   Description length: {len(result['description'])} chars")
            print(f"   App type: {result['app_type']}")
        else:
            print(f"❌ VLM processing failed")


@cli.command()
@click.option('--batch-size', default=20, help='Images per batch')
@click.option('--max-concurrent', default=5, help='Max concurrent requests')
@click.option('--max-batches', default=10, help='Max batches to process')
def optimize(batch_size, max_concurrent, max_batches):
    """Run high-performance batch optimization"""
    print("🚀 Starting VLM Batch Optimization...")
    
    # Run the async optimizer
    import asyncio
    from scripts.vlm_batch_optimizer import VLMBatchOptimizer
    
    async def run():
        optimizer = VLMBatchOptimizer(max_concurrent=max_concurrent)
        await optimizer.run_optimization(
            batch_size=batch_size,
            max_batches=max_batches
        )
    
    asyncio.run(run())


if __name__ == '__main__':
    cli()