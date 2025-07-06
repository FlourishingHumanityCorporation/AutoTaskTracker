#!/usr/bin/env python3
"""Test the dashboard with real data."""
import sys
import os
import logging
import unittest
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from autotasktracker.core.database import DatabaseManager
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestDashboardFunctionality(unittest.TestCase):
    """Test dashboard functionality with real data."""
    
    def setUp(self):
        """Set up test environment."""
        self.db = DatabaseManager()
        self.task_repo = TaskRepository(self.db)
        self.metrics_repo = MetricsRepository(self.db)
    
    def test_dashboard_data_retrieval(self):
        """Test dashboard data retrieval."""
        logger.info("=== TESTING DASHBOARD DATA ===")
        
        # Test different time ranges
        now = datetime.now()
        
        # Last hour
        logger.info("Tasks from last hour:")
        tasks = self.task_repo.get_tasks_for_period(now - timedelta(hours=1), now)
        if tasks:
            for task in tasks[:5]:
                logger.info(f"  - {task.title} ({task.category})")
            self.assertIsInstance(tasks, list)
        else:
            logger.info("  No tasks found")
        
        # Today
        logger.info("Tasks from today:")
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tasks_today = self.task_repo.get_tasks_for_period(start_of_day, now)
        logger.info(f"  Total: {len(tasks_today)} tasks")
        
        # Show category breakdown
        if tasks_today:
            categories = Counter(task.category for task in tasks_today)
            logger.info("  Category breakdown:")
            for cat, count in categories.most_common():
                logger.info(f"    {cat}: {count}")
        
        # Test task groups
        logger.info("Task groups (last 24h):")
        groups = self.task_repo.get_task_groups(now - timedelta(hours=24), now)
        if groups:
            for group in groups[:5]:
                logger.info(f"  - {group.window_title[:50]}... ({group.duration_minutes:.1f} min)")
            self.assertIsInstance(groups, list)
        else:
            logger.info("  No groups found")
        
        # Test metrics
        logger.info("Metrics summary (last 7 days):")
        metrics = self.metrics_repo.get_metrics_summary(
            now - timedelta(days=7), 
            now
        )
        self.assertIsInstance(metrics, dict)
        for key, value in metrics.items():
            logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    unittest.main()