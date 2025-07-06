"""Tests for the RealtimeStatus component."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from autotasktracker.dashboards.components.realtime_status import RealtimeStatusComponent


class TestRealtimeStatusComponent(unittest.TestCase):
    """Test cases for RealtimeStatusComponent."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_container = Mock()
        self.mock_st = Mock()
        
    def test_default_config(self):
        """Test default configuration."""
        config = RealtimeStatusComponent.get_default_config()
        
        self.assertTrue(config['show_event_count'])
        self.assertTrue(config['show_last_update'])
        self.assertFalse(config['show_connection_details'])
        self.assertFalse(config['compact_mode'])
        self.assertTrue(config['update_animation'])
    
    def test_format_uptime(self):
        """Test uptime formatting."""
        # Seconds
        self.assertEqual(RealtimeStatusComponent._format_uptime(45), "45s")
        
        # Minutes
        self.assertEqual(RealtimeStatusComponent._format_uptime(120), "2m")
        self.assertEqual(RealtimeStatusComponent._format_uptime(3599), "59m")
        
        # Hours
        self.assertEqual(RealtimeStatusComponent._format_uptime(3600), "1h 0m")
        self.assertEqual(RealtimeStatusComponent._format_uptime(7200), "2h 0m")
        self.assertEqual(RealtimeStatusComponent._format_uptime(3665), "1h 1m")
        
        # Days
        self.assertEqual(RealtimeStatusComponent._format_uptime(86400), "1d 0h")
        self.assertEqual(RealtimeStatusComponent._format_uptime(90000), "1d 1h")
    
    @patch('streamlit.success')
    @patch('streamlit.caption')
    def test_render_full_live_mode(self, mock_caption, mock_success):
        """Test full render in live mode."""
        processor_stats = {
            'running': True,
            'events_processed': 42,
            'queue_size': 5,
            'active_threads': 2
        }
        
        RealtimeStatusComponent.render(
            mode="live",
            event_count=42,
            processor_stats=processor_stats,
            config={"compact_mode": False}
        )
        
        mock_success.assert_called_once_with("🔄 Live")
        mock_caption.assert_called_with("Events: 42")
    
    @patch('streamlit.warning')
    def test_render_full_paused_mode(self, mock_warning):
        """Test full render in paused mode."""
        RealtimeStatusComponent.render(
            mode="paused",
            config={"compact_mode": False}
        )
        
        mock_warning.assert_called_once_with("⏸️ Paused")
    
    @patch('streamlit.info')
    def test_render_full_static_mode(self, mock_info):
        """Test full render in static mode."""
        RealtimeStatusComponent.render(
            mode="static",
            config={"compact_mode": False}
        )
        
        mock_info.assert_called_once_with("📋 Static")
    
    def test_render_compact_mode(self):
        """Test compact mode rendering."""
        mock_container = Mock()
        last_update = datetime.now() - timedelta(minutes=5)
        
        RealtimeStatusComponent._render_compact(
            mock_container,
            mode="live",
            event_count=100,
            last_update=last_update,
            config={
                "show_event_count": True,
                "show_last_update": True
            }
        )
        
        # Check caption was called
        mock_container.caption.assert_called_once()
        caption_text = mock_container.caption.call_args[0][0]
        
        # Verify content
        self.assertIn("🔄 Live", caption_text)
        self.assertIn("Events: 100", caption_text)
        self.assertIn("5m ago", caption_text)
    
    def test_render_compact_mode_just_now(self):
        """Test compact mode with recent update."""
        mock_container = Mock()
        last_update = datetime.now() - timedelta(seconds=30)
        
        RealtimeStatusComponent._render_compact(
            mock_container,
            mode="live",
            event_count=50,
            last_update=last_update,
            config={
                "show_event_count": True,
                "show_last_update": True
            }
        )
        
        caption_text = mock_container.caption.call_args[0][0]
        self.assertIn("Just now", caption_text)
    
    @patch('streamlit.sidebar.subheader')
    @patch('streamlit.sidebar.toggle')
    @patch('streamlit.sidebar.slider')
    @patch('streamlit.sidebar.success')
    @patch('streamlit.sidebar.caption')
    @patch('streamlit.session_state')
    def test_render_sidebar_controls_enabled(
        self, mock_session_state, mock_caption, mock_success, 
        mock_slider, mock_toggle, mock_subheader
    ):
        """Test sidebar controls when enabled."""
        # Set up session state mock
        mock_session_state.get.return_value = True
        mock_session_state.__setitem__ = Mock()
        mock_session_state.__getitem__ = Mock(side_effect=lambda k: True if k == 'websocket_connected' else None)
        
        mock_toggle.return_value = True
        mock_slider.return_value = 10
        
        result = RealtimeStatusComponent.render_sidebar_controls(
            default_enabled=True,
            show_interval_slider=True,
            show_connection_info=True
        )
        
        self.assertTrue(result['enabled'])
        self.assertEqual(result['refresh_interval'], 10)
        self.assertTrue(result['websocket_connected'])
        
        mock_subheader.assert_called_with("🔄 Real-time Updates")
        mock_success.assert_called_with("🟢 WebSocket: Connected")
        mock_caption.assert_called_with("Real-time events active")
    
    @patch('streamlit.sidebar.subheader')
    @patch('streamlit.sidebar.toggle')
    @patch('streamlit.sidebar.info')
    @patch('streamlit.sidebar.caption')
    @patch('streamlit.session_state')
    def test_render_sidebar_controls_disabled(
        self, mock_session_state, mock_caption, mock_info, 
        mock_toggle, mock_subheader
    ):
        """Test sidebar controls when disabled."""
        # Set up session state mock
        mock_session_state.get.return_value = False
        mock_session_state.__setitem__ = Mock()
        
        mock_toggle.return_value = False
        
        result = RealtimeStatusComponent.render_sidebar_controls(
            default_enabled=False
        )
        
        self.assertFalse(result['enabled'])
        mock_info.assert_called_with("Updates paused")
        mock_caption.assert_called_with("Enable to receive real-time updates")
    
    @patch('streamlit.caption')
    def test_last_update_formatting(self, mock_caption):
        """Test last update time formatting."""
        # Test "just now"
        last_update = datetime.now() - timedelta(seconds=30)
        RealtimeStatusComponent.render(
            mode="static",
            last_update=last_update,
            config={"show_last_update": True}
        )
        
        # Find the caption call with update time
        caption_calls = [call[0][0] for call in mock_caption.call_args_list]
        self.assertTrue(any("just now" in call.lower() for call in caption_calls))
        
        # Test minutes ago
        mock_caption.reset_mock()
        last_update = datetime.now() - timedelta(minutes=15)
        RealtimeStatusComponent.render(
            mode="static",
            last_update=last_update,
            config={"show_last_update": True}
        )
        
        caption_calls = [call[0][0] for call in mock_caption.call_args_list]
        self.assertTrue(any("15m ago" in call for call in caption_calls))
        
        # Test hours (shows time)
        mock_caption.reset_mock()
        last_update = datetime.now() - timedelta(hours=2)
        RealtimeStatusComponent.render(
            mode="static",
            last_update=last_update,
            config={"show_last_update": True}
        )
        
        caption_calls = [call[0][0] for call in mock_caption.call_args_list]
        expected_time = last_update.strftime("%H:%M")
        self.assertTrue(any(expected_time in call for call in caption_calls))


if __name__ == '__main__':
    unittest.main()