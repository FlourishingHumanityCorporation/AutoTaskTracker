#!/usr/bin/env python3
"""Test the dashboard with real data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from autotasktracker.core.database import DatabaseManager
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository

def test_dashboard_data():
    """Test dashboard data retrieval."""
    print("=== TESTING DASHBOARD DATA ===\n")
    
    db = DatabaseManager()
    task_repo = TaskRepository(db)
    metrics_repo = MetricsRepository(db)
    
    # Test different time ranges
    now = datetime.now()
    
    # Last hour
    print("Tasks from last hour:")
    tasks = task_repo.get_tasks_for_period(now - timedelta(hours=1), now)
    if tasks:
        for task in tasks[:5]:
            print(f"  - {task.title} ({task.category})")
    else:
        print("  No tasks found")
    
    # Today
    print("\nTasks from today:")
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tasks_today = task_repo.get_tasks_for_period(start_of_day, now)
    print(f"  Total: {len(tasks_today)} tasks")
    
    # Show category breakdown
    if tasks_today:
        from collections import Counter
        categories = Counter(task.category for task in tasks_today)
        print("\n  Category breakdown:")
        for cat, count in categories.most_common():
            print(f"    {cat}: {count}")
    
    # Test task groups
    print("\nTask groups (last 24h):")
    groups = task_repo.get_task_groups(now - timedelta(hours=24), now)
    if groups:
        for group in groups[:5]:
            print(f"  - {group.window_title[:50]}... ({group.duration_minutes:.1f} min)")
    else:
        print("  No groups found")
    
    # Test metrics
    print("\nMetrics summary (last 7 days):")
    metrics = metrics_repo.get_metrics_summary(
        now - timedelta(days=7), 
        now
    )
    for key, value in metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_dashboard_data()