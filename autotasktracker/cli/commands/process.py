"""Processing-related CLI commands."""
import click
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


@click.group(name='process')
def process_group():
    """Screenshot and task processing operations."""
    pass


@process_group.command()
@click.option('--batch', '-b', is_flag=True, help='Run in batch mode')
@click.option('--limit', '-l', type=int, help='Maximum screenshots to process')
@click.option('--interval', '-i', type=int, default=60, help='Processing interval in seconds')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon process')
def screenshots(batch, limit, interval, daemon):
    """Process screenshots (OCR, metadata extraction)."""
    from scripts.processing.process_screenshots import process_screenshots_batch
    
    if batch or not daemon:
        click.echo(f"🖼️  Processing screenshots in batch mode...")
        if limit:
            click.echo(f"   Processing up to {limit} screenshots")
        
        processed = process_screenshots_batch(limit=limit)
        click.echo(f"✅ Processed {processed} screenshots")
    else:
        click.echo(f"🔄 Starting screenshot processor daemon (interval: {interval}s)")
        click.echo("   Press Ctrl+C to stop")
        
        try:
            while True:
                processed = process_screenshots_batch(limit=limit)
                if processed > 0:
                    click.echo(f"   Processed {processed} screenshots")
                time.sleep(interval)
        except KeyboardInterrupt:
            click.echo("\n✅ Screenshot processor stopped")


@process_group.command()
@click.option('--limit', '-l', type=int, help='Maximum tasks to process')
@click.option('--force', '-f', is_flag=True, help='Force reprocessing')
def tasks(limit, force):
    """Extract tasks from screenshots."""
    from scripts.processing.process_tasks import process_tasks_batch
    
    click.echo("📋 Extracting tasks from screenshots...")
    if limit:
        click.echo(f"   Processing up to {limit} items")
    if force:
        click.echo("   Force reprocessing enabled")
    
    processed = process_tasks_batch(limit=limit, force_reprocess=force)
    click.echo(f"✅ Extracted tasks from {processed} screenshots")


@process_group.command()
@click.option('--min-duration', '-m', type=int, default=60, help='Minimum session duration in seconds')
def sessions(min_duration):
    """Process work sessions from tasks."""
    from scripts.processing.process_sessions import process_sessions_batch
    
    click.echo(f"⏱️  Processing work sessions (min duration: {min_duration}s)...")
    
    sessions_found = process_sessions_batch(min_duration_seconds=min_duration)
    click.echo(f"✅ Found {sessions_found} work sessions")


@process_group.command()
@click.option('--interval', '-i', type=int, default=30, help='Processing interval in seconds')
@click.option('--background', '-b', is_flag=True, help='Run in background')
def auto(interval, background):
    """Run auto-processor for all processing tasks."""
    from scripts.start_auto_processor import start_processor, stop_processor, status
    
    if background:
        click.echo(f"🤖 Starting auto-processor in background (interval: {interval}s)")
        success = start_processor(interval=interval, background=True)
        if success:
            click.echo("✅ Auto-processor started successfully")
            click.echo("   Use 'autotask process auto --stop' to stop")
        else:
            click.echo("❌ Failed to start auto-processor")
    else:
        click.echo(f"🤖 Starting auto-processor in foreground (interval: {interval}s)")
        click.echo("   Press Ctrl+C to stop")
        start_processor(interval=interval, background=False)


@process_group.command(name='stop')
def stop():
    """Stop the auto-processor."""
    from scripts.start_auto_processor import stop_processor
    
    click.echo("🛑 Stopping auto-processor...")
    success = stop_processor()
    
    if success:
        click.echo("✅ Auto-processor stopped")
    else:
        click.echo("❌ Auto-processor was not running")


@process_group.command(name='status')
def process_status():
    """Check auto-processor status."""
    from scripts.start_auto_processor import status
    
    is_running = status()
    if not is_running:
        click.echo("❌ Auto-processor is not running")
        click.echo("   Start with: autotask process auto")