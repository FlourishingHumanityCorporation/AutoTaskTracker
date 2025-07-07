#!/usr/bin/env python3
"""Get current dashboard metrics programmatically."""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.dashboards.data.repositories import MetricsRepository
from autotasktracker.core.database import DatabaseManager


def get_metrics(date_range='today', format='text'):
    """Get metrics for specified date range."""
    # Calculate date range
    now = datetime.now()
    if date_range == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_range == 'yesterday':
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_range == 'week':
        start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        raise ValueError(f"Unknown date range: {date_range}")
    
    # Get metrics
    repo = MetricsRepository()
    summary = repo.get_metrics_summary(start_date, end_date)
    
    # Add metadata and convert numpy types to Python types
    metrics_clean = {
        'total_activities': int(summary['total_activities']),
        'active_days': int(summary['active_days']),
        'unique_windows': int(summary['unique_windows']),
        'unique_categories': int(summary['unique_categories']),
        'avg_daily_activities': float(summary['avg_daily_activities'])
    }
    
    result = {
        'timestamp': now.isoformat(),
        'date_range': date_range,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'metrics': metrics_clean
    }
    
    # Format output
    if format == 'json':
        return json.dumps(result, indent=2)
    elif format == 'csv':
        metrics = result['metrics']
        return f"timestamp,total_activities,active_days,unique_windows,unique_categories,avg_daily_activities\n" \
               f"{result['timestamp']},{metrics['total_activities']},{metrics['active_days']}," \
               f"{metrics['unique_windows']},{metrics['unique_categories']},{metrics['avg_daily_activities']}"
    else:  # text
        metrics = result['metrics']
        return f"""
📊 AutoTaskTracker Metrics Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date Range: {date_range.capitalize()}
🕐 Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}

📈 Total Activities: {metrics['total_activities']:,}
📅 Active Days: {metrics['active_days']}
🪟 Unique Windows: {metrics['unique_windows']}
🏷️ Categories: {metrics['unique_categories']}
📊 Daily Average: {metrics['avg_daily_activities']:.0f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def main():
    parser = argparse.ArgumentParser(description='Get AutoTaskTracker metrics')
    parser.add_argument('--range', '-r', choices=['today', 'yesterday', 'week'], 
                        default='today', help='Date range for metrics')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'csv'], 
                        default='text', help='Output format')
    parser.add_argument('--watch', '-w', action='store_true',
                        help='Watch mode - refresh every 30 seconds')
    
    args = parser.parse_args()
    
    if args.watch:
        import time
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                print(get_metrics(args.range, args.format))
                print("\n🔄 Refreshing in 30 seconds... (Ctrl+C to stop)")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n✋ Watch mode stopped")
    else:
        print(get_metrics(args.range, args.format))


if __name__ == '__main__':
    main()