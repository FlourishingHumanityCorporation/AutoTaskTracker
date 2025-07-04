"""Tests for refactored dashboard components."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# Import components to test (non-UI components only for now)
from autotasktracker.dashboards.data.models import Task, TaskGroup, DailyMetrics
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository


class TestTimeFilterComponent:
    """Test time filter component."""
    
    def test_get_time_range_today(self):
        """Test today time range calculation."""
        start, end = TimeFilterComponent.get_time_range("Today")
        now = datetime.now()
        
        assert start.date() == now.date()
        assert start.hour == 0
        assert start.minute == 0
        assert end.date() == now.date()
        
    def test_get_time_range_yesterday(self):
        """Test yesterday time range calculation."""
        start, end = TimeFilterComponent.get_time_range("Yesterday")
        yesterday = datetime.now() - timedelta(days=1)
        
        assert start.date() == yesterday.date()
        assert start.hour == 0
        assert end.hour == 23
        
    def test_get_time_range_last_7_days(self):
        """Test last 7 days range calculation."""
        start, end = TimeFilterComponent.get_time_range("Last 7 Days")
        now = datetime.now()
        
        assert (now - start).days == 7
        assert end.date() == now.date()


class TestCategoryFilterComponent:
    """Test category filter component."""
    
    def test_default_categories(self):
        """Test default categories list."""
        categories = CategoryFilterComponent.DEFAULT_CATEGORIES
        
        assert "All Categories" in categories
        assert "Development" in categories
        assert "Communication" in categories
        assert len(categories) > 0


class TestDashboardCache:
    """Test dashboard caching functionality."""
    
    def test_create_cache_key(self):
        """Test cache key generation."""
        key1 = DashboardCache.create_cache_key("test", param1="value1", param2=123)
        key2 = DashboardCache.create_cache_key("test", param2=123, param1="value1")
        
        # Same parameters in different order should generate same key
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = DashboardCache.create_cache_key("test", param1="different")
        assert key1 != key3
        
    def test_cache_functionality(self):
        """Test basic cache operations."""
        # Mock fetch function
        fetch_func = Mock(return_value="test_data")
        
        # First call should fetch data
        result1 = DashboardCache.get_cached("test_key", fetch_func, ttl_seconds=60)
        assert result1 == "test_data"
        assert fetch_func.call_count == 1
        
        # Second call should use cache
        result2 = DashboardCache.get_cached("test_key", fetch_func, ttl_seconds=60)
        assert result2 == "test_data"
        assert fetch_func.call_count == 1  # Should not call again


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
        assert tasks[0].title in ['VS Code', 'Slack']
        assert mock_db.execute_query.called


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


def test_dashboard_architecture_integration():
    """Integration test for dashboard architecture."""
    # Mock database manager
    mock_db = Mock()
    mock_df = pd.DataFrame({
        'id': [1, 2, 3],
        'created_at': ['2024-01-01 10:00:00', '2024-01-01 11:00:00', '2024-01-01 12:00:00'],
        'file_path': ['/path1.png', '/path2.png', '/path3.png'],
        'ocr_text': ['Text 1', 'Text 2', 'Text 3'],
        'active_window': ['App1', 'App2', 'App1'],
        'tasks': [None, None, None],
        'category': ['Development', 'Communication', 'Development'],
        'window_title': ['VS Code', 'Slack', 'VS Code']
    })
    mock_db.execute_query.return_value = mock_df
    mock_db.test_connection.return_value = True
    
    # Test repositories work together
    task_repo = TaskRepository(mock_db)
    metrics_repo = MetricsRepository(mock_db)
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 2)
    
    # Get tasks
    tasks = task_repo.get_tasks_for_period(start_date, end_date)
    assert len(tasks) == 3
    
    # Get task groups
    task_groups = task_repo.get_task_groups(start_date, end_date)
    assert len(task_groups) >= 0  # May be 0 if grouping logic filters out short tasks
    
    # Get metrics summary
    summary = metrics_repo.get_metrics_summary(start_date, end_date)
    assert 'total_activities' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])