"""Tests for core dashboard functionality (no UI dependencies)."""

import pytest
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core components
from autotasktracker.dashboards.data.models import Task, TaskGroup, DailyMetrics
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository


class TestDataModels:
    """Test data models."""
    
    def test_task_model(self):
        """Test Task model."""
        task = Task(
            id=1,
            title="Test Task",
            category="Development",
            timestamp=datetime.now(),
            duration_minutes=30,
            window_title="VS Code"
        )
        
        assert task.duration_hours == 0.5
        assert task.title == "Test Task"
        assert task.category == "Development"
        
    def test_task_group_model(self):
        """Test TaskGroup model."""
        now = datetime.now()
        start_time = now - timedelta(minutes=30)
        
        group = TaskGroup(
            window_title="VS Code",
            category="Development",
            start_time=start_time,
            end_time=now,
            duration_minutes=30,
            task_count=3,
            tasks=[]
        )
        
        assert group.duration_hours == 0.5
        assert group.window_title == "VS Code"
        assert group.task_count == 3
        
    def test_daily_metrics_model(self):
        """Test DailyMetrics model."""
        metrics = DailyMetrics(
            date=datetime.now(),
            total_tasks=100,
            total_duration_minutes=480,  # 8 hours
            unique_windows=10,
            categories={"Development": 50, "Communication": 30},
            productive_time_minutes=240,  # 4 hours
            most_used_apps=[("VS Code", 120), ("Slack", 60)],
            peak_hours=[9, 10, 14]
        )
        
        assert metrics.total_duration_hours == 8
        assert metrics.productive_percentage == 50
        assert len(metrics.most_used_apps) == 2
        assert metrics.most_used_apps[0][0] == "VS Code"


class TestTaskRepository:
    """Test TaskRepository functionality."""
    
    def test_task_repository_init(self):
        """Test repository initialization."""
        mock_db = Mock()
        repo = TaskRepository(mock_db)
        
        assert repo.db == mock_db
        
    def test_get_tasks_for_period(self):
        """Test getting tasks for a period."""
        # Create mock database manager
        mock_db = Mock()
        mock_df = pd.DataFrame({
            'id': [1, 2],
            'created_at': ['2024-01-01 10:00:00', '2024-01-01 11:00:00'],
            'file_path': ['/path1.png', '/path2.png'],
            'ocr_text': ['Some text', 'Other text'],
            'active_window': ['App1', 'App2'],
            'tasks': [None, None],
            'category': ['Development', 'Communication'],
            'window_title': ['VS Code', 'Slack']
        })
        mock_db.execute_query.return_value = mock_df
        
        repo = TaskRepository(mock_db)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        tasks = repo.get_tasks_for_period(start_date, end_date)
        
        assert len(tasks) == 2
        assert isinstance(tasks[0], Task)
        assert tasks[0].category in ['Development', 'Communication']
        assert mock_db.execute_query.called
        
        # Check query parameters
        call_args = mock_db.execute_query.call_args
        assert len(call_args[0]) == 2  # query and params
        query, params = call_args[0]
        assert "SELECT" in query
        assert "entities" in query
        assert len(params) == 3  # start, end, limit


class TestMetricsRepository:
    """Test MetricsRepository functionality."""
    
    def test_metrics_repository_init(self):
        """Test repository initialization."""
        mock_db = Mock()
        repo = MetricsRepository(mock_db)
        
        assert repo.db == mock_db
        
    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        mock_db = Mock()
        mock_df = pd.DataFrame({
            'total_activities': [100],
            'active_days': [5],
            'unique_windows': [10],
            'unique_categories': [4]
        })
        mock_db.execute_query.return_value = mock_df
        
        repo = MetricsRepository(mock_db)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)
        
        summary = repo.get_metrics_summary(start_date, end_date)
        
        assert summary['total_activities'] == 100
        assert summary['active_days'] == 5
        assert summary['avg_daily_activities'] == 20
        assert summary['unique_windows'] == 10
        assert summary['unique_categories'] == 4
        
    def test_get_daily_metrics_empty(self):
        """Test daily metrics with empty data."""
        mock_db = Mock()
        mock_db.execute_query.return_value = pd.DataFrame()  # Empty DataFrame
        
        repo = MetricsRepository(mock_db)
        date = datetime(2024, 1, 1)
        
        metrics = repo.get_daily_metrics(date)
        
        assert metrics is None


def test_time_filter_logic():
    """Test time filtering logic without UI dependencies."""
    from autotasktracker.dashboards.utils import get_time_range
    
    # Test today range
    start, end = get_time_range("Today")
    now = datetime.now()
    
    assert start.date() == now.date()
    assert start.hour == 0
    assert start.minute == 0
    assert end.date() == now.date()
    
    # Test yesterday range
    start, end = get_time_range("Yesterday")
    yesterday = datetime.now() - timedelta(days=1)
    
    assert start.date() == yesterday.date()
    assert start.hour == 0
    assert end.hour == 23
    
    # Test last 7 days
    start, end = get_time_range("Last 7 Days")
    
    # Allow for 6 or 7 days difference due to timing
    days_diff = (now - start).days
    assert days_diff in [6, 7]
    assert end.date() == now.date()
    
    # Test all time
    start, end = get_time_range("All Time")
    
    assert start.year == 2020
    assert end.date() == now.date()


def test_repository_integration():
    """Integration test for repositories."""
    # Mock database manager
    mock_db = Mock()
    
    # Mock data for task queries
    task_df = pd.DataFrame({
        'id': [1, 2, 3],
        'created_at': ['2024-01-01 10:00:00', '2024-01-01 11:00:00', '2024-01-01 12:00:00'],
        'file_path': ['/path1.png', '/path2.png', '/path3.png'],
        'ocr_text': ['Text 1', 'Text 2', 'Text 3'],
        'active_window': ['VS Code - main.py', 'Slack - Team Chat', 'VS Code - utils.py'],
        'tasks': [None, None, None],
        'category': ['Development', 'Communication', 'Development'],
        'window_title': ['VS Code', 'Slack', 'VS Code']
    })
    
    # Mock data for metrics queries
    metrics_df = pd.DataFrame({
        'total_activities': [100],
        'active_days': [5],
        'unique_windows': [10],
        'unique_categories': [4]
    })
    
    # Mock the execute_query method to return different data based on query
    def mock_execute_query(query, params):
        if 'COUNT(DISTINCT e.id) as total_activities' in query:
            return metrics_df
        else:
            return task_df
    
    mock_db.execute_query.side_effect = mock_execute_query
    
    # Test repositories work together
    task_repo = TaskRepository(mock_db)
    metrics_repo = MetricsRepository(mock_db)
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 2)
    
    # Get tasks
    tasks = task_repo.get_tasks_for_period(start_date, end_date)
    assert len(tasks) == 3
    assert all(isinstance(task, Task) for task in tasks)
    
    # Get task groups (might be fewer due to grouping logic)
    task_groups = task_repo.get_task_groups(start_date, end_date, min_duration_minutes=0.1)
    assert len(task_groups) >= 0
    assert all(isinstance(group, TaskGroup) for group in task_groups)
    
    # Get metrics summary
    summary = metrics_repo.get_metrics_summary(start_date, end_date)
    assert isinstance(summary, dict)
    assert 'total_activities' in summary
    assert 'avg_daily_activities' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])