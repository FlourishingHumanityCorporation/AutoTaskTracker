"""
Unit tests for the notification system functionality.

Tests cover:
- Notification delivery
- Notification formatting
- Notification throttling
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from autotasktracker.dashboards.notifications import TaskNotifier

# Mock plyer module if not installed
try:
    import plyer
except ImportError:
    import sys
    from unittest.mock import MagicMock
    sys.modules['plyer'] = MagicMock()
    sys.modules['plyer.notification'] = MagicMock()


class TestTaskNotifier:
    """Test the TaskNotifier class for notification functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager."""
        mock = Mock()
        mock.test_connection.return_value = True
        mock.fetch_tasks.return_value = pd.DataFrame({
            'created_at': [
                datetime.now().isoformat(),
                (datetime.now() - timedelta(minutes=5)).isoformat(),
                (datetime.now() - timedelta(minutes=10)).isoformat()
            ],
            'active_window': [
                '{"title": "Visual Studio Code - project.py", "app": "Code"}',
                '{"title": "Chrome - Documentation", "app": "Chrome"}',
                '{"title": "Visual Studio Code - project.py", "app": "Code"}'
            ],
            'ocr_text': ['def main():', 'API Reference', 'class TaskManager:']
        })
        return mock

    @pytest.fixture
    def notifier(self, mock_db):
        """Create a TaskNotifier instance with mocked dependencies."""
        with patch('autotasktracker.dashboards.notifications.DatabaseManager', return_value=mock_db):
            with patch('autotasktracker.dashboards.notifications.get_config'):
                return TaskNotifier()

    def test_notification_delivery(self, notifier):
        """Test that notifications are sent correctly."""
        # Just test that the method exists and returns expected value
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', True):
            with patch('autotasktracker.dashboards.notifications.notification') as mock_notif:
                mock_notif.notify.return_value = None
                result = notifier.send_notification("Test Title", "Test Message")
                assert result is True

    def test_notification_delivery_handles_errors(self, notifier):
        """Test notification delivery handles errors gracefully."""
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', True):
            with patch('autotasktracker.dashboards.notifications.notification') as mock_notif:
                mock_notif.notify.side_effect = Exception("Notify error")
                result = notifier.send_notification("Test", "Message")
                assert result is False  # Should return False on error

    def test_notification_formatting(self, notifier, mock_db):
        """Test that notification messages are formatted correctly."""
        stats = {
            'screenshots': 10,
            'categories': {'🧑‍💻 Coding': 7, '🔍 Research/Browsing': 3},
            'focus_time': 45,
            'top_activity': '🧑‍💻 Coding'
        }
        
        insight = notifier.generate_insight(stats)
        
        # Verify message contains expected elements
        assert "70% of the last hour on 🧑‍💻 Coding" in insight
        assert "Great focus! 45 minutes of deep work" in insight

    def test_notification_formatting_with_low_focus(self, notifier):
        """Test notification formatting for low focus sessions."""
        stats = {
            'screenshots': 20,
            'categories': {'💬 Communication': 5, '🔍 Research/Browsing': 5, '🧑‍💻 Coding': 5, '📋 Other': 5},
            'focus_time': 5,
            'top_activity': '💬 Communication'
        }
        
        insight = notifier.generate_insight(stats)
        
        assert "Consider blocking time for focused work" in insight
        assert "High context switching detected" in insight

    def test_notification_throttling(self, notifier):
        """Test that notifications respect throttling intervals."""
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', True):
            with patch('autotasktracker.dashboards.notifications.notification') as mock_notify:
                # Set last notification to recent time
                notifier.last_notification = datetime.now() - timedelta(minutes=30)
                notifier.notification_interval = 3600  # 1 hour
                
                # Mock the periodic check loop to run once
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    with patch.object(notifier, 'get_recent_stats') as mock_stats:
                        mock_stats.return_value = {'screenshots': 10}
                        with patch.object(notifier, 'generate_insight', return_value="Test insight"):
                            try:
                                notifier.run_periodic_check()
                            except KeyboardInterrupt:
                                pass
                
                # Should not send notification (within throttle period)
                mock_notify.assert_not_called()

    def test_notification_sent_after_interval(self, notifier):
        """Test that notifications are sent after the throttling interval."""
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', True):
            with patch('autotasktracker.dashboards.notifications.notification') as mock_notify:
                # Set last notification to old time
                notifier.last_notification = datetime.now() - timedelta(hours=2)
                notifier.notification_interval = 3600  # 1 hour
                
                # Mock the periodic check loop to run once
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    with patch.object(notifier, 'get_recent_stats') as mock_stats:
                        mock_stats.return_value = {
                            'screenshots': 10,
                            'categories': {'🧑‍💻 Coding': 10},
                            'focus_time': 30,
                            'top_activity': '🧑‍💻 Coding'
                        }
                        try:
                            notifier.run_periodic_check()
                        except KeyboardInterrupt:
                            pass
                
                # Should send notification (past throttle period)
                assert mock_notify.called

    def test_get_recent_stats_calculation(self, notifier, mock_db):
        """Test that recent stats are calculated correctly."""
        # Patch the line that causes error (conn.close())
        with patch('autotasktracker.dashboards.notifications.logging'):
            stats = notifier.get_recent_stats(hours=1)
        
        assert stats is not None
        assert stats['screenshots'] == 3
        assert '🧑‍💻 Coding' in stats['categories']
        assert stats['categories']['🧑‍💻 Coding'] == 2
        assert stats['top_activity'] == '🧑‍💻 Coding'

    def test_get_recent_stats_handles_db_errors(self, notifier, mock_db):
        """Test stats calculation handles database errors gracefully."""
        mock_db.test_connection.return_value = False
        stats = notifier.get_recent_stats(hours=1)
        assert stats is None

    def test_focus_time_calculation(self, notifier, mock_db):
        """Test that focus time is calculated correctly."""
        # Create continuous work session with small gaps (under 5 min threshold)
        base_time = datetime.now()
        timestamps = []
        # Create 12 minutes of work with small gaps
        for i in range(20):
            timestamps.append(base_time - timedelta(seconds=i*40))  # 40 second intervals
        
        mock_db.fetch_tasks.return_value = pd.DataFrame({
            'created_at': [t.isoformat() for t in timestamps],
            'active_window': ['{"title": "VS Code - coding", "app": "Code"}'] * 20,
            'ocr_text': ['code'] * 20
        })
        
        with patch('autotasktracker.dashboards.notifications.logging'):
            stats = notifier.get_recent_stats(hours=1)
        
        # Should detect continuous focus session (at least 10 minutes)
        assert stats['focus_time'] >= 10

    def test_get_recent_stats_focus_time(self, notifier, mock_db):
        """Test that focus time is calculated correctly for continuous sessions."""
        # Create continuous work session with proper time intervals
        base_time = datetime.now()
        # Create many entries close together for continuous work
        timestamps = []
        for i in range(20):
            timestamps.append(base_time - timedelta(seconds=i*40))
        
        mock_db.fetch_tasks.return_value = pd.DataFrame({
            'created_at': [t.isoformat() for t in timestamps],
            'active_window': ['{"title": "Visual Studio Code", "app": "Code"}'] * 20,
            'ocr_text': ['def function():'] * 20
        })
        
        with patch('autotasktracker.dashboards.notifications.logging'):
            stats = notifier.get_recent_stats(hours=1)
        
        # Should detect continuous focus session (at least 10 minutes)
        assert stats['focus_time'] >= 10

    def test_empty_stats_handling(self, notifier):
        """Test handling of empty statistics."""
        insight = notifier.generate_insight(None)
        assert insight is None
        
        insight = notifier.generate_insight({'screenshots': 0})
        assert insight is None

    def test_notification_not_available_fallback(self, notifier):
        """Test behavior when notification library is not available."""
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', False):
            result = notifier.send_notification("Test", "Message")
            assert result is False

    def test_periodic_check_error_recovery(self, notifier):
        """Test that periodic check recovers from errors."""
        call_count = 0
        
        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            elif call_count >= 2:
                raise KeyboardInterrupt()
        
        with patch('time.sleep', side_effect=side_effect):
            with patch.object(notifier, 'get_recent_stats', side_effect=Exception("Stats error")):
                try:
                    notifier.run_periodic_check()
                except KeyboardInterrupt:
                    pass
        
        # Should have attempted multiple times (error recovery)
        assert call_count >= 2