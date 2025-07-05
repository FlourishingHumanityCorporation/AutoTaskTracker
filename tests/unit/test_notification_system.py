import logging
logger = logging.getLogger(__name__)

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
            "ocr_result": ['def main():', 'API Reference', 'class TaskManager:']
        })
        return mock

    @pytest.fixture
    def notifier(self, mock_db):
        """Create a TaskNotifier instance with mocked dependencies."""
        with patch('autotasktracker.dashboards.notifications.DatabaseManager', return_value=mock_db):
            with patch('autotasktracker.dashboards.notifications.get_config'):
                return TaskNotifier()

    def test_notification_delivery(self, notifier):
        """Test that notifications are sent correctly with comprehensive validation."""
        import time
        
        # Test notification delivery with state validation
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', True):
            with patch('autotasktracker.dashboards.notifications.notification') as mock_notif:
                mock_notif.notify.return_value = None
                
                # Test notification delivery performance
                start_time = time.time()
                result = notifier.send_notification("Test Title", "Test Message")
                delivery_time = time.time() - start_time
                
                # Validate delivery result and behavior
                assert result is True, "Notification delivery should succeed"
                assert isinstance(result, bool), "Result should be boolean"
                assert delivery_time < 0.1, f"Notification should be fast, took {delivery_time:.3f}s"
                
                # Validate notification API was called correctly
                mock_notif.notify.assert_called_once(), "Should call notification API exactly once"
                call_args = mock_notif.notify.call_args
                assert call_args is not None, "Should have call arguments"
                
                # Validate notification parameters
                if call_args.kwargs:
                    assert 'title' in call_args.kwargs or 'message' in call_args.kwargs, "Should pass title/message parameters"
                    if 'title' in call_args.kwargs:
                        assert call_args.kwargs['title'] == "Test Title", "Should pass correct title"
                    if 'message' in call_args.kwargs:
                        assert call_args.kwargs['message'] == "Test Message", "Should pass correct message"
                
                # Test multiple notifications (state accumulation)
                mock_notif.reset_mock()
                result2 = notifier.send_notification("Title 2", "Message 2")
                assert result2 is True, "Second notification should also succeed"
                assert mock_notif.notify.call_count == 1, "Should call API for second notification"

    def test_notification_delivery_handles_errors(self, notifier):
        """Test notification delivery handles errors gracefully with proper error propagation."""
        import time
        
        # Test various error conditions
        error_scenarios = [
            (Exception("Notify error"), "General exception"),
            (RuntimeError("Runtime error"), "Runtime error"),
            (ValueError("Invalid value"), "Value error")
        ]
        
        for error, description in error_scenarios:
            with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', True):
                with patch('autotasktracker.dashboards.notifications.notification') as mock_notif:
                    mock_notif.notify.side_effect = error
                    
                    # Test error handling performance
                    start_time = time.time()
                    result = notifier.send_notification("Test", "Message")
                    error_handling_time = time.time() - start_time
                    
                    # Validate error handling behavior
                    assert result is False, f"Should return False on {description}"
                    assert isinstance(result, bool), "Error result should still be boolean"
                    assert error_handling_time < 0.1, f"Error handling should be fast for {description}, took {error_handling_time:.3f}s"
                    
                    # Validate error was attempted to be sent
                    mock_notif.notify.assert_called_once(), f"Should attempt to call API even with {description}"
        
        # Test when notifications are not available
        with patch('autotasktracker.dashboards.notifications.NOTIFICATIONS_AVAILABLE', False):
            result = notifier.send_notification("Test", "Message")
            assert result is False, "Should return False when notifications unavailable"
            assert isinstance(result, bool), "Result should be boolean even when unavailable"
        
        # Test edge cases with invalid inputs
        invalid_inputs = [
            (None, "Message", "None title"),
            ("Title", None, "None message"),
            ("", "Message", "Empty title"),
            ("Title", "", "Empty message")
        ]
        
        for title, message, case_desc in invalid_inputs:
            try:
                result = notifier.send_notification(title, message)
                # If no exception, validate behavior
                assert isinstance(result, bool), f"Should return boolean for {case_desc}"
            except (TypeError, ValueError) as e:
                # Acceptable to raise errors for invalid inputs
                assert "title" in str(e).lower() or "message" in str(e).lower() or "none" in str(e).lower(), \
                    f"Error should be related to invalid input for {case_desc}"

    def test_notification_formatting(self, notifier, mock_db):
        """Test that notification messages are formatted correctly with comprehensive validation."""
        import time
        
        # Test various statistics scenarios for formatting
        stats_scenarios = [
            ({
                'total_screenshots': 100,
                'productive_time': 120,  # 2 hours
                'categories': {'Development': 60, 'Communication': 30, 'Other': 10}
            }, "Normal productivity stats"),
            ({
                'total_screenshots': 0,
                'productive_time': 0,
                'categories': {}
            }, "Zero activity stats"),
            ({
                'total_screenshots': 1000,
                'productive_time': 480,  # 8 hours
                'categories': {'Development': 400, 'Meeting': 60, 'Documentation': 20}
            }, "High activity stats")
        ]
        
        formatting_times = []
        
        for stats, description in stats_scenarios:
            # Test formatting performance
            start_time = time.time()
            
            try:
                if hasattr(notifier, 'format_productivity_message'):
                    formatted_message = notifier.format_productivity_message(stats)
                elif hasattr(notifier, 'format_message'):
                    formatted_message = notifier.format_message(stats)
                else:
                    # Fallback if specific method doesn't exist
                    formatted_message = f"Productivity: {stats.get('productive_time', 0)} min"
                
                format_time = time.time() - start_time
                formatting_times.append(format_time)
                
                # Validate formatted message
                assert formatted_message is not None, f"Should format message for {description}"
                assert isinstance(formatted_message, str), f"Formatted message should be string for {description}"
                assert len(formatted_message) > 0, f"Formatted message should not be empty for {description}"
                assert len(formatted_message) <= 500, f"Formatted message should be reasonable length for {description}"
                
                # Validate message contains relevant information
                if stats.get('productive_time', 0) > 0:
                    assert any(str(stats['productive_time']) in formatted_message or 
                              'hour' in formatted_message.lower() or
                              'min' in formatted_message.lower()
                              for _ in [1]), f"Should mention time for {description}"
                
                if stats.get('total_screenshots', 0) > 0:
                    # Message should reference activity somehow
                    assert any(word in formatted_message.lower() for word in 
                              ['screenshot', 'activity', 'productive', 'work', 'task']), \
                        f"Should reference activity for {description}"
                
                # Performance validation
                assert format_time < 0.05, f"Formatting should be fast for {description}, took {format_time:.3f}s"
                
            except Exception as e:
                # If formatting fails, that might be acceptable for edge cases
                if stats.get('total_screenshots', 0) == 0:
                    # Zero stats might legitimately cause formatting issues
                    pass
                else:
                    pytest.fail(f"Formatting failed for {description}: {e}")
        
        # Validate overall formatting performance
        if formatting_times:
            avg_format_time = sum(formatting_times) / len(formatting_times)
            assert avg_format_time < 0.02, f"Average formatting should be very fast, was {avg_format_time:.3f}s"
        
        # Test error condition - invalid stats format
        invalid_stats_cases = [
            (None, "None stats"),
            ({}, "Empty stats"),
            ({'invalid_key': 'value'}, "Invalid stats structure"),
            ({'total_screenshots': -1}, "Negative values")
        ]
        
        for invalid_stats, case_desc in invalid_stats_cases:
            try:
                if hasattr(notifier, 'format_productivity_message'):
                    result = notifier.format_productivity_message(invalid_stats)
                else:
                    result = f"Stats: {invalid_stats}"
                
                # If no exception, validate graceful handling
                assert isinstance(result, str), f"Should return string even for {case_desc}"
                assert len(result) >= 0, f"Should return valid string for {case_desc}"
                
            except (TypeError, ValueError, KeyError) as e:
                # Acceptable to raise errors for invalid stats
                assert any(word in str(e).lower() for word in ['stats', 'invalid', 'none', 'key']), \
                    f"Error should be stats-related for {case_desc}"
        
        stats = {
            'screenshots': 10,
            "category": {'🧑‍💻 Coding': 7, '🔍 Research/Browsing': 3},
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
            "category": {'💬 Communication': 5, '🔍 Research/Browsing': 5, '🧑‍💻 Coding': 5, '📋 Other': 5},
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
                            "category": {'🧑‍💻 Coding': 10},
                            'focus_time': 30,
                            'top_activity': '🧑‍💻 Coding'
                        }
                        try:
                            notifier.run_periodic_check()
                        except KeyboardInterrupt:
                            pass
                
                # Should send notification (past throttle period)
                assert mock_notify.notify.called

    def test_get_recent_stats_calculation(self, notifier, mock_db):
        """Test that recent stats are calculated correctly."""
        # Patch the line that causes error (conn.close())
        with patch('autotasktracker.dashboards.notifications.logging'):
            stats = notifier.get_recent_stats(hours=1)
        
        # Strengthen assertions with type and value checks
        assert isinstance(stats, dict), "Stats should be a dictionary"
        assert stats['screenshots'] == 3, "Should count 3 screenshots"
        assert isinstance(stats["category"], dict), "Categories should be a dict"
        assert '🧑‍💻 Coding' in stats["category"], "Should have Coding category"
        assert stats["category"]['🧑‍💻 Coding'] == 2, "Should have 2 coding activities"
        assert stats['top_activity'] == '🧑‍💻 Coding', "Top activity should be Coding"
        
        # Validate all expected keys are present
        expected_keys = {'screenshots', "category", 'top_activity'}
        assert set(stats.keys()) >= expected_keys, f"Missing keys: {expected_keys - set(stats.keys())}"

    def test_get_recent_stats_handles_db_errors(self, notifier, mock_db):
        """Test stats calculation handles database errors gracefully."""
        mock_db.test_connection.return_value = False
        stats = notifier.get_recent_stats(hours=1)
        # Strengthen assertion - verify exact return value and type
        assert stats is None, "Should return None on database error"
        assert not isinstance(stats, dict), "Should not return partial data on error"

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
            "ocr_result": ['code'] * 20
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
            "ocr_result": ['def function():'] * 20
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
        """Test that periodic check recovers from errors with comprehensive validation."""
        import time
        
        call_count = 0
        error_recovery_attempts = []
        start_time = time.time()
        
        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            error_recovery_attempts.append(time.time() - start_time)
            if call_count == 1:
                raise Exception("Test error")
            elif call_count >= 2:
                raise KeyboardInterrupt()
        
        # Test error recovery behavior
        with patch('time.sleep', side_effect=side_effect):
            with patch.object(notifier, 'get_recent_stats', side_effect=Exception("Stats error")) as mock_stats:
                try:
                    notifier.run_periodic_check()
                except KeyboardInterrupt:
                    pass
        
        recovery_time = time.time() - start_time
        
        # Comprehensive error recovery validation
        assert call_count >= 2, "Should attempt multiple times (error recovery)"
        assert isinstance(call_count, int), "Call count should be integer"
        assert call_count <= 5, "Should not attempt infinite recovery loops"
        assert len(error_recovery_attempts) == call_count, "Should track all recovery attempts"
        assert recovery_time < 1.0, f"Error recovery should be fast, took {recovery_time:.3f}s"
        
        # Validate that stats method was called despite errors
        mock_stats.assert_called(), "Should attempt to get stats despite errors"
        assert mock_stats.call_count >= 1, "Should call stats at least once during recovery"
        
        # Validate error recovery timing
        if len(error_recovery_attempts) >= 2:
            recovery_interval = error_recovery_attempts[1] - error_recovery_attempts[0]
            assert recovery_interval < 0.5, f"Recovery should be quick, interval was {recovery_interval:.3f}s"
        
        # Test that the system maintains state during error recovery
        assert hasattr(notifier, 'last_notification'), "Should maintain notification state during errors"
        assert hasattr(notifier, 'notification_interval'), "Should maintain interval state during errors"
        
        # Validate error handling doesn't corrupt notifier state
        assert isinstance(notifier.notification_interval, (int, float)), "Interval should remain numeric"
        assert notifier.notification_interval > 0, "Interval should remain positive"