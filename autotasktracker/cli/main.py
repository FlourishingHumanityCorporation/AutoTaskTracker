#!/usr/bin/env python3
"""
AutoTaskTracker Unified CLI

This consolidates all script functionality into a single, discoverable CLI.
"""
import click
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress output')
@click.pass_context
def cli(ctx, verbose, quiet):
    """AutoTaskTracker - AI-powered passive task discovery from screenshots."""
    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    # Adjust logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)


# Import command groups
from .commands import ai, process, dashboard, check, analyze

# Register command groups
cli.add_command(ai.ai_group)
cli.add_command(process.process_group)
cli.add_command(dashboard.dashboard_group)
cli.add_command(check.check_group)
cli.add_command(analyze.analyze_group)


@cli.command()
def version():
    """Show version information."""
    from autotasktracker import __version__
    click.echo(f"AutoTaskTracker v{__version__}")


@cli.command()
def config():
    """Show current configuration."""
    from autotasktracker.config import get_config
    config = get_config()
    click.echo("Current Configuration:")
    click.echo(f"  Database: {config.get_db_path()}")
    click.echo(f"  Memos Directory: {config.memos_dir}")
    click.echo(f"  AI Features Enabled: {config.AI_FEATURES_ENABLED}")
    click.echo(f"  Debug Mode: {config.DEBUG}")


if __name__ == "__main__":
    cli()