"""Tests for SessionControlsComponent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import streamlit as st
from autotasktracker.dashboards.components.session_controls import SessionControlsComponent


class TestSessionControlsComponent:
    """Test suite for SessionControlsComponent."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        # Reset session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    def test_render_default(self):
        """Test rendering with default settings."""
        with patch('streamlit.expander') as mock_expander:
            mock_context = MagicMock()
            mock_expander.return_value.__enter__.return_value = mock_context
            
            SessionControlsComponent.render()
            
            mock_expander.assert_called_once_with("🔧 Session Controls", expanded=False)
    
    def test_render_compact_mode(self):
        """Test rendering in compact mode."""
        with patch('streamlit.columns') as mock_columns:
            # Create mock columns with context manager support
            mock_cols = []
            for _ in range(4):
                mock_col = MagicMock()
                mock_col.__enter__ = MagicMock(return_value=mock_col)
                mock_col.__exit__ = MagicMock(return_value=None)
                mock_cols.append(mock_col)
            mock_columns.return_value = mock_cols
            
            with patch('streamlit.button') as mock_button:
                mock_button.return_value = False
                
                SessionControlsComponent.render(compact_mode=True)
                
                mock_columns.assert_called_once_with([1, 1, 1, 1])
                mock_button.assert_called()
    
    def test_cache_clear_functionality(self):
        """Test cache clearing functionality."""
        with patch('autotasktracker.dashboards.cache.DashboardCache.clear_cache') as mock_clear:
            with patch('streamlit.cache_data.clear') as mock_st_clear:
                SessionControlsComponent._clear_cache()
                
                mock_clear.assert_called_once_with(None)
                mock_st_clear.assert_called_once()
    
    def test_debug_mode_toggle(self):
        """Test debug mode toggle functionality."""
        # Initial state - debug mode off
        assert st.session_state.get("debug_mode", False) is False
        
        with patch('streamlit.checkbox') as mock_checkbox:
            # Simulate enabling debug mode
            mock_checkbox.return_value = True
            
            with patch('streamlit.expander'):
                SessionControlsComponent.render(show_debug_toggle=True)
                
                # Check that checkbox was called with correct parameters
                mock_checkbox.assert_any_call(
                    "Enable Debug Mode",
                    value=False,
                    help="Show detailed error messages and debug information"
                )
    
    def test_realtime_toggle(self):
        """Test real-time mode toggle."""
        with patch('streamlit.checkbox') as mock_checkbox:
            mock_checkbox.return_value = True
            
            with patch('streamlit.columns') as mock_columns:
                # Create mock columns with context manager support
                mock_cols = []
                for _ in range(4):
                    mock_col = MagicMock()
                    mock_col.__enter__ = MagicMock(return_value=mock_col)
                    mock_col.__exit__ = MagicMock(return_value=None)
                    mock_cols.append(mock_col)
                mock_columns.return_value = mock_cols
                
                SessionControlsComponent.render(
                    show_realtime_toggle=True,
                    compact_mode=True
                )
                
                # Verify real-time checkbox was created
                checkbox_calls = [call for call in mock_checkbox.call_args_list 
                                if "Live" in str(call) or "Real-time" in str(call)]
                assert len(checkbox_calls) > 0
    
    def test_session_info_display(self):
        """Test session information display."""
        # Set up session start time
        st.session_state.session_start = datetime.now()
        
        with patch('streamlit.metric') as mock_metric:
            with patch('streamlit.expander'):
                SessionControlsComponent.render(show_session_info=True)
                
                # Check that metrics were displayed
                assert mock_metric.call_count >= 2  # Duration and state items
    
    def test_custom_controls(self):
        """Test custom control functionality."""
        custom_called = False
        
        def custom_callback():
            nonlocal custom_called
            custom_called = True
        
        custom_controls = {
            "Test Control": custom_callback
        }
        
        with patch('streamlit.button') as mock_button:
            # Simulate button click
            mock_button.return_value = True
            
            with patch('streamlit.success'):
                with patch('streamlit.expander'):
                    SessionControlsComponent.render(custom_controls=custom_controls)
                    
                    # Verify custom control was rendered
                    button_calls = [call for call in mock_button.call_args_list 
                                  if "Test Control" in str(call)]
                    assert len(button_calls) > 0
    
    def test_cache_stats_display(self):
        """Test cache statistics display."""
        mock_stats = {
            'hit_rate_percent': 85.5,
            'total_requests': 1000,
            'hits': 855,
            'misses': 145,
            'size': 2048
        }
        
        with patch('autotasktracker.pensieve.cache_manager.get_cache_manager') as mock_get_cm:
            mock_manager = Mock()
            mock_manager.get_stats.return_value = mock_stats
            mock_get_cm.return_value = mock_manager
            
            with patch('streamlit.json') as mock_json:
                SessionControlsComponent._show_cache_stats()
                
                mock_json.assert_called_once()
                call_args = mock_json.call_args[0][0]
                assert call_args['Hit Rate'] == "85.5%"
                assert call_args['Total Requests'] == 1000
    
    def test_minimal_render(self):
        """Test minimal render mode."""
        with patch('streamlit.sidebar.button') as mock_button:
            mock_button.return_value = False
            
            SessionControlsComponent.render_minimal(position="sidebar")
            
            mock_button.assert_called_once_with(
                "🔄 Clear Cache",
                help="Clear all cached data"
            )
    
    def test_error_handling(self):
        """Test error handling in controls."""
        def failing_callback():
            raise ValueError("Test error")
        
        custom_controls = {
            "Failing Control": failing_callback
        }
        
        with patch('streamlit.button') as mock_button:
            mock_button.return_value = True
            
            with patch('streamlit.error') as mock_error:
                with patch('streamlit.expander'):
                    SessionControlsComponent.render(custom_controls=custom_controls)
                    
                    mock_error.assert_called()
                    error_msg = mock_error.call_args[0][0]
                    assert "Test error" in error_msg
    
    def test_session_state_filtering(self):
        """Test that sensitive session state items are filtered."""
        # Add some session state items
        st.session_state.update({
            "normal_key": "value",
            "api_key": "secret",
            "user_token": "secret",
            "password": "secret",
            "secret_data": "sensitive"
        })
        
        # Enable debug mode
        st.session_state.debug_mode = True
        
        with patch('streamlit.json') as mock_json:
            with patch('streamlit.expander'):
                SessionControlsComponent.render(show_session_info=True)
                
                # Check if json was called (in debug mode with session info)
                if mock_json.called:
                    displayed_state = mock_json.call_args[0][0]
                    # Sensitive keys should be filtered out
                    assert "api_key" not in displayed_state
                    assert "user_token" not in displayed_state
                    assert "password" not in displayed_state
                    assert "secret_data" not in displayed_state
                    # Normal keys should be present
                    assert "normal_key" in displayed_state or "debug_mode" in displayed_state