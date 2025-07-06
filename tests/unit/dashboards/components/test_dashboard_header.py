"""Unit tests for DashboardHeader component."""

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime

from autotasktracker.dashboards.components.dashboard_header import DashboardHeader
from autotasktracker.dashboards.components.realtime_status import RealtimeStatusComponent


class TestDashboardHeader(unittest.TestCase):
    """Test cases for DashboardHeader component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_st = MagicMock()
        self.patch_st = patch('autotasktracker.dashboards.components.dashboard_header.st', self.mock_st)
        self.patch_st.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.patch_st.stop()
        
    def test_render_simple_header(self):
        """Test rendering a simple header without right column."""
        # Test simple header
        DashboardHeader.render_simple(
            title="Test Dashboard",
            subtitle="Test subtitle",
            icon="📊"
        )
        
        # Verify title was rendered with icon
        self.mock_st.title.assert_called_once_with("📊 Test Dashboard")
        
        # Verify subtitle was rendered
        self.mock_st.markdown.assert_called_once_with("Test subtitle")
        
    def test_render_header_without_icon(self):
        """Test rendering header without icon."""
        DashboardHeader.render(
            title="Plain Dashboard",
            subtitle="No icon here"
        )
        
        # Verify title without icon
        self.mock_st.title.assert_called_once_with("Plain Dashboard")
        
    def test_render_header_with_timestamp(self):
        """Test rendering header with timestamp."""
        with patch('autotasktracker.dashboards.components.dashboard_header.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 6, 12, 30, 45)
            
            DashboardHeader.render(
                title="Timed Dashboard",
                show_timestamp=True
            )
            
            # Verify timestamp caption was called
            caption_calls = self.mock_st.caption.call_args_list
            self.assertEqual(len(caption_calls), 1)
            self.assertIn("Last updated: 2025-01-06 12:30:45", caption_calls[0][0][0])
            
    def test_render_header_with_extra_info(self):
        """Test rendering header with extra info."""
        DashboardHeader.render(
            title="Info Dashboard",
            subtitle="Main description",
            extra_info="Additional context here"
        )
        
        # Verify extra info was rendered as caption
        self.mock_st.caption.assert_called_once_with("Additional context here")
        
    def test_render_header_with_right_column(self):
        """Test rendering header with right column content."""
        # Mock columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        self.mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Mock the component
        mock_component = MagicMock()
        mock_component.render = MagicMock()
        
        # Render with right column
        DashboardHeader.render(
            title="Dashboard with Status",
            subtitle="Has right column",
            icon="📋",
            right_column_content={
                'component': mock_component,
                'params': {'mode': 'live', 'event_count': 42}
            }
        )
        
        # Verify columns were created
        self.mock_st.columns.assert_called_once_with([3, 1])
        
        # Verify component render was called with params
        mock_component.render.assert_called_once_with(mode='live', event_count=42)
        
    def test_render_header_with_custom_column_ratio(self):
        """Test rendering header with custom column ratio."""
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        self.mock_st.columns.return_value = [mock_col1, mock_col2]
        
        mock_component = MagicMock()
        mock_component.render = MagicMock()
        
        DashboardHeader.render(
            title="Custom Ratio",
            right_column_content={
                'component': mock_component,
                'params': {}
            },
            column_ratio=[2, 2]  # Equal width
        )
        
        # Verify custom ratio was used
        self.mock_st.columns.assert_called_once_with([2, 2])
        
    def test_render_all_options(self):
        """Test rendering with all options enabled."""
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        self.mock_st.columns.return_value = [mock_col1, mock_col2]
        
        mock_component = MagicMock()
        mock_component.render = MagicMock()
        
        with patch('autotasktracker.dashboards.components.dashboard_header.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 6, 15, 45, 30)
            
            DashboardHeader.render(
                title="Full Featured Dashboard",
                subtitle="All options enabled",
                icon="🚀",
                right_column_content={
                    'component': mock_component,
                    'params': {'status': 'active'}
                },
                show_timestamp=True,
                extra_info="Extra information here",
                column_ratio=[4, 1]
            )
            
        # Verify all elements were rendered
        self.mock_st.columns.assert_called_once_with([4, 1])
        mock_component.render.assert_called_once_with(status='active')
        
        # Check that caption was called twice (extra_info and timestamp)
        self.assertEqual(self.mock_st.caption.call_count, 2)
        
    def test_component_without_render_method(self):
        """Test handling component without render method."""
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        self.mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Component without render method
        mock_component = MagicMock(spec=[])
        
        # Should not raise error
        DashboardHeader.render(
            title="Safe Dashboard",
            right_column_content={
                'component': mock_component,
                'params': {}
            }
        )
        
        # Verify title was still rendered
        self.mock_st.title.assert_called_once()


if __name__ == '__main__':
    unittest.main()