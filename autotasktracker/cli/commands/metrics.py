"""Metrics command for AutoTaskTracker CLI."""

import json
from datetime import datetime, timedelta
from typing import Optional

import click

from autotasktracker.dashboards.data.repositories import MetricsRepository


@click.command()
@click.option('--range', '-r', 'date_range', 
              type=click.Choice(['today', 'yesterday', 'week', 'month']), 
              default='today', help='Date range for metrics')
@click.option('--format', '-f', 
              type=click.Choice(['text', 'json', 'csv']), 
              default='text', help='Output format')
@click.option('--live', '-l', is_flag=True, help='Live update mode')
def metrics(date_range: str, format: str, live: bool):
    """Display AutoTaskTracker metrics."""
    
    def get_date_range(range_name: str):
        """Convert range name to date tuple."""
        now = datetime.now()
        
        if range_name == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif range_name == 'yesterday':
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif range_name == 'week':
            start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif range_name == 'month':
            start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start, end
    
    def display_metrics(start_date, end_date):
        """Fetch and display metrics."""
        repo = MetricsRepository()
        summary = repo.get_metrics_summary(start_date, end_date)
        
        if format == 'json':
            output = {
                'timestamp': datetime.now().isoformat(),
                'date_range': date_range,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'metrics': summary
            }
            click.echo(json.dumps(output, indent=2))
        
        elif format == 'csv':
            if not hasattr(display_metrics, 'header_shown'):
                click.echo("timestamp,range,total_activities,active_days,unique_windows,unique_categories,avg_daily")
                display_metrics.header_shown = True
            
            click.echo(f"{datetime.now().isoformat()},{date_range},"
                      f"{summary['total_activities']},{summary['active_days']},"
                      f"{summary['unique_windows']},{summary['unique_categories']},"
                      f"{summary['avg_daily_activities']:.0f}")
        
        else:  # text format
            click.clear()
            click.echo(click.style("📊 AutoTaskTracker Metrics", bold=True))
            click.echo(click.style("━" * 40, dim=True))
            click.echo(f"📅 Range: {click.style(date_range.capitalize(), fg='cyan')}")
            click.echo(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
            click.echo(click.style("━" * 40, dim=True))
            
            # Metrics with colors
            click.echo(f"📈 Total Activities: {click.style(f'{summary[\"total_activities\"]:,}', fg='green', bold=True)}")
            click.echo(f"📅 Active Days: {click.style(str(summary['active_days']), fg='yellow')}")
            click.echo(f"🪟 Unique Windows: {click.style(str(summary['unique_windows']), fg='blue')}")
            click.echo(f"🏷️ Categories: {click.style(str(summary['unique_categories']), fg='magenta')}")
            click.echo(f"📊 Daily Average: {click.style(f\"{summary['avg_daily_activities']:.0f}\", fg='cyan')}")
            
            if live:
                click.echo(click.style("━" * 40, dim=True))
                click.echo(click.style("🔄 Live mode - refreshing every 10s (Ctrl+C to stop)", fg='yellow', blink=True))
    
    # Get date range
    start_date, end_date = get_date_range(date_range)
    
    if live:
        import time
        try:
            while True:
                display_metrics(start_date, end_date)
                time.sleep(10)
        except KeyboardInterrupt:
            click.echo("\n✋ Live mode stopped")
    else:
        display_metrics(start_date, end_date)