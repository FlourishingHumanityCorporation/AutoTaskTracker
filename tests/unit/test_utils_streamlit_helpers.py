"""
Comprehensive tests for Streamlit helpers utility module.

Tests cover all Streamlit helper functionality including:
- Page configuration
- Header display
- Error and info message display
- Session state initialization
"""
import pytest
from unittest.mock import Mock, patch, call

from autotasktracker.utils.streamlit_helpers import (
    configure_page, show_header, show_error_message, 
    show_info_message, initialize_session_state
)


class TestConfigurePage:
    """Test the configure_page function."""
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_configure_page_with_all_parameters(self, mock_st):
        """Test page configuration with all parameters specified."""
        configure_page(
            title="Test Dashboard",
            icon="🧪",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
        
        mock_st.set_page_config.assert_called_once_with(
            page_title="Test Dashboard",
            page_icon="🧪",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
        
        # Validate actual functionality - function should execute without errors
        assert mock_st.set_page_config.called, "configure_page should call streamlit configuration"
        call_args = mock_st.set_page_config.call_args[1]
        assert call_args['page_title'] == "Test Dashboard", "Should set correct page title"
        assert call_args['page_icon'] == "🧪", "Should set correct page icon"
        assert call_args['layout'] == "centered", "Should set correct layout"
        assert call_args['initial_sidebar_state'] == "collapsed", "Should set correct sidebar state"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_configure_page_with_defaults(self, mock_st):
        """Test page configuration with default parameter values."""
        configure_page("My Dashboard")
        
        mock_st.set_page_config.assert_called_once_with(
            page_title="My Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="auto"
        )
        
        # Validate default parameter handling
        call_args = mock_st.set_page_config.call_args[1]
        assert call_args['page_title'] == "My Dashboard", "Should use provided title"
        assert call_args['page_icon'] == "📊", "Should use default icon when not specified"
        assert call_args['layout'] == "wide", "Should use default wide layout"
        assert call_args['initial_sidebar_state'] == "auto", "Should use default auto sidebar"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_configure_page_with_partial_parameters(self, mock_st):
        """Test page configuration with some parameters specified."""
        configure_page(
            title="Analytics Dashboard",
            icon="📈",
            layout="centered"
        )
        
        mock_st.set_page_config.assert_called_once_with(
            page_title="Analytics Dashboard",
            page_icon="📈",
            layout="centered",
            initial_sidebar_state="auto"
        )
        
        # Validate partial parameter override behavior
        call_args = mock_st.set_page_config.call_args[1]
        assert call_args['page_title'] == "Analytics Dashboard", "Should override title"
        assert call_args['page_icon'] == "📈", "Should override icon"
        assert call_args['layout'] == "centered", "Should override layout"
        assert call_args['initial_sidebar_state'] == "auto", "Should use default for unspecified param"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_configure_page_parameter_validation(self, mock_st):
        """Test that configure_page handles various parameter types correctly."""
        # Test with empty title
        configure_page("")
        mock_st.set_page_config.assert_called_with(
            page_title="",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="auto"
        )
        
        # Test with special characters in title
        configure_page("Dashboard: Analysis & Metrics")
        mock_st.set_page_config.assert_called_with(
            page_title="Dashboard: Analysis & Metrics",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="auto"
        )
        
        # Validate parameter validation behavior
        assert mock_st.set_page_config.call_count == 2, "Should be called twice for two tests"
        first_call = mock_st.set_page_config.call_args_list[0][1]
        second_call = mock_st.set_page_config.call_args_list[1][1]
        assert first_call['page_title'] == "", "Should handle empty title"
        assert second_call['page_title'] == "Dashboard: Analysis & Metrics", "Should handle special characters"


class TestShowHeader:
    """Test the show_header function."""
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_header_with_title_only(self, mock_st):
        """Test header display with title only."""
        show_header("Dashboard Title")
        
        # Verify correct sequence of calls
        expected_calls = [
            call.title("Dashboard Title"),
            call.divider()
        ]
        mock_st.assert_has_calls(expected_calls)
        # Should not call markdown for subtitle
        mock_st.markdown.assert_not_called()
        
        # Validate actual behavior - function should execute without errors
        assert mock_st.title.called, "Should display title"
        assert mock_st.divider.called, "Should display divider"
        title_call_arg = mock_st.title.call_args[0][0]
        assert title_call_arg == "Dashboard Title", "Should display correct title text"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_header_with_title_and_subtitle(self, mock_st):
        """Test header display with title and subtitle."""
        show_header("Main Title", "This is a subtitle")
        
        # Verify correct sequence of calls
        expected_calls = [
            call.title("Main Title"),
            call.markdown("*This is a subtitle*"),
            call.divider()
        ]
        mock_st.assert_has_calls(expected_calls)
        
        # Validate subtitle formatting and content
        assert mock_st.title.called, "Should display title"
        assert mock_st.markdown.called, "Should display subtitle"
        assert mock_st.divider.called, "Should display divider"
        title_arg = mock_st.title.call_args[0][0]
        markdown_arg = mock_st.markdown.call_args[0][0]
        assert title_arg == "Main Title", "Should display correct title"
        assert markdown_arg == "*This is a subtitle*", "Should format subtitle in italics"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_header_with_empty_subtitle(self, mock_st):
        """Test header display with empty subtitle."""
        show_header("Title", "")
        
        # Empty subtitle should not trigger markdown call
        mock_st.title.assert_called_once_with("Title")
        mock_st.markdown.assert_not_called()
        mock_st.divider.assert_called_once()
        
        # Validate empty subtitle handling
        assert mock_st.title.call_count == 1, "Should call title exactly once"
        assert mock_st.markdown.call_count == 0, "Should not call markdown for empty subtitle"
        assert mock_st.divider.call_count == 1, "Should call divider exactly once"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_header_with_none_subtitle(self, mock_st):
        """Test header display with None subtitle."""
        show_header("Title", None)
        
        # None subtitle should not trigger markdown call
        mock_st.title.assert_called_once_with("Title")
        
        # Validate None subtitle handling
        assert mock_st.title.call_count == 1, "Should call title exactly once"
        assert mock_st.markdown.call_count == 0, "Should not call markdown for None subtitle"
        assert mock_st.divider.call_count == 1, "Should call divider exactly once"
        mock_st.markdown.assert_not_called()
        mock_st.divider.assert_called_once()
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_header_with_special_characters(self, mock_st):
        """Test header display with special characters and formatting."""
        show_header("Title with **bold**", "Subtitle with *italic* and emoji 📊")
        
        mock_st.title.assert_called_once_with("Title with **bold**")
        mock_st.markdown.assert_called_once_with("*Subtitle with *italic* and emoji 📊*")
        mock_st.divider.assert_called_once()
        
        # Validate special character handling
        title_arg = mock_st.title.call_args[0][0]
        markdown_arg = mock_st.markdown.call_args[0][0]
        assert "**bold**" in title_arg, "Should preserve markdown formatting in title"
        assert "emoji 📊" in markdown_arg, "Should preserve emoji in subtitle"
        assert markdown_arg.startswith("*") and markdown_arg.endswith("*"), "Should wrap subtitle in italics"


class TestShowErrorMessage:
    """Test the show_error_message function."""
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_error_message_without_details(self, mock_st):
        """Test error message display without details."""
        show_error_message("Something went wrong")
        
        mock_st.error.assert_called_once_with("Something went wrong")
        # Should not create expander for details
        mock_st.expander.assert_not_called()
        
        # Validate actual functionality
        assert mock_st.error.called, "Should display error message"
        error_message = mock_st.error.call_args[0][0]
        assert error_message == "Something went wrong", "Should display correct error text"
        assert mock_st.expander.call_count == 0, "Should not create expander without details"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_error_message_with_details(self, mock_st):
        """Test error message display with details."""
        # Mock the expander context manager
        mock_expander = Mock()
        mock_st.expander.return_value.__enter__.return_value = mock_expander
        mock_st.expander.return_value.__exit__.return_value = None
        
        show_error_message("Database connection failed", "Connection timeout after 30 seconds")
        
        mock_st.error.assert_called_once_with("Database connection failed")
        mock_st.expander.assert_called_once_with("Details")
        mock_st.text.assert_called_once_with("Connection timeout after 30 seconds")
        
        # Validate actual functionality with details
        assert mock_st.error.called, "Should display error message"
        assert mock_st.expander.called, "Should create expander for details"
        assert mock_st.text.called, "Should display detail text"
        
        error_msg = mock_st.error.call_args[0][0]
        expander_title = mock_st.expander.call_args[0][0]
        detail_text = mock_st.text.call_args[0][0]
        
        assert error_msg == "Database connection failed", "Should display correct error message"
        assert expander_title == "Details", "Should create Details expander"
        assert detail_text == "Connection timeout after 30 seconds", "Should display correct detail text"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_error_message_with_empty_details(self, mock_st):
        """Test error message display with empty details."""
        show_error_message("Error occurred", "")
        
        mock_st.error.assert_called_once_with("Error occurred")
        # Empty details should not create expander
        mock_st.expander.assert_not_called()
        
        # Validate empty details handling
        assert mock_st.error.called, "Should display error message"
        assert mock_st.expander.call_count == 0, "Should not create expander for empty details"
        error_msg = mock_st.error.call_args[0][0]
        assert error_msg == "Error occurred", "Should display correct error message"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_error_message_with_none_details(self, mock_st):
        """Test error message display with None details."""
        show_error_message("Error occurred", None)
        
        mock_st.error.assert_called_once_with("Error occurred")
        # None details should not create expander
        mock_st.expander.assert_not_called()
        
        # Validate None details handling
        assert mock_st.error.called, "Should display error message"
        assert mock_st.expander.call_count == 0, "Should not create expander for None details"
        error_msg = mock_st.error.call_args[0][0]
        assert error_msg == "Error occurred", "Should display correct error message"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_error_message_with_multiline_details(self, mock_st):
        """Test error message display with multiline details."""
        # Mock the expander context manager
        mock_expander = Mock()
        mock_st.expander.return_value.__enter__.return_value = mock_expander
        mock_st.expander.return_value.__exit__.return_value = None
        
        multiline_details = "Line 1\nLine 2\nLine 3"
        show_error_message("Complex error", multiline_details)
        
        mock_st.error.assert_called_once_with("Complex error")
        mock_st.expander.assert_called_once_with("Details")
        mock_st.text.assert_called_once_with(multiline_details)
        
        # Validate multiline details handling
        assert mock_st.error.called, "Should display error message"
        assert mock_st.expander.called, "Should create expander for multiline details"
        assert mock_st.text.called, "Should display detail text"
        
        error_msg = mock_st.error.call_args[0][0]
        detail_text = mock_st.text.call_args[0][0]
        
        assert error_msg == "Complex error", "Should display correct error message"
        assert "\n" in detail_text, "Should preserve multiline formatting"
        assert "Line 1" in detail_text and "Line 3" in detail_text, "Should contain all lines"


class TestShowInfoMessage:
    """Test the show_info_message function."""
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_info_message_with_default_icon(self, mock_st):
        """Test info message display with default icon."""
        show_info_message("This is an info message")
        
        mock_st.info.assert_called_once_with("ℹ️ This is an info message")
        
        # Validate default icon functionality
        assert mock_st.info.called, "Should display info message"
        info_message = mock_st.info.call_args[0][0]
        assert info_message == "ℹ️ This is an info message", "Should prepend default icon"
        assert info_message.startswith("ℹ️"), "Should start with default info icon"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_info_message_with_custom_icon(self, mock_st):
        """Test info message display with custom icon."""
        show_info_message("Success message", "✅")
        
        mock_st.info.assert_called_once_with("✅ Success message")
        
        # Validate custom icon functionality
        assert mock_st.info.called, "Should display info message"
        info_message = mock_st.info.call_args[0][0]
        assert info_message == "✅ Success message", "Should use custom icon"
        assert info_message.startswith("✅"), "Should start with custom icon"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_info_message_with_empty_icon(self, mock_st):
        """Test info message display with empty icon."""
        show_info_message("No icon message", "")
        
        mock_st.info.assert_called_once_with(" No icon message")
        
        # Validate empty icon handling
        assert mock_st.info.called, "Should display info message"
        info_message = mock_st.info.call_args[0][0]
        assert info_message == " No icon message", "Should handle empty icon"
        assert info_message.startswith(" "), "Should start with space when icon is empty"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_info_message_with_multiple_icons(self, mock_st):
        """Test info message display with multiple emoji icons."""
        show_info_message("Multiple icons", "🎉🎊")
        
        mock_st.info.assert_called_once_with("🎉🎊 Multiple icons")
        
        # Validate multiple icons functionality
        assert mock_st.info.called, "Should display info message"
        info_message = mock_st.info.call_args[0][0]
        assert info_message == "🎉🎊 Multiple icons", "Should handle multiple emoji icons"
        assert "🎉" in info_message and "🎊" in info_message, "Should contain both emojis"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_info_message_with_special_characters(self, mock_st):
        """Test info message display with special characters in message."""
        show_info_message("Message with **bold** and *italic*", "📝")
        
        mock_st.info.assert_called_once_with("📝 Message with **bold** and *italic*")
        
        # Validate special characters handling
        assert mock_st.info.called, "Should display info message"
        info_message = mock_st.info.call_args[0][0]
        assert info_message == "📝 Message with **bold** and *italic*", "Should preserve markdown formatting"
        assert "**bold**" in info_message, "Should preserve bold markdown"
        assert "*italic*" in info_message, "Should preserve italic markdown"


class TestInitializeSessionState:
    """Test the initialize_session_state function."""
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_with_empty_session(self, mock_st):
        """Test session state initialization with empty session state."""
        # Mock empty session state
        mock_st.session_state = {}
        
        defaults = {
            'filter_category': 'All',
            'show_screenshots': True,
            'refresh_interval': 30,
            'selected_date': None
        }
        
        initialize_session_state(defaults)
        
        # All defaults should be set
        assert mock_st.session_state['filter_category'] == 'All'
        assert mock_st.session_state['show_screenshots'] is True
        assert mock_st.session_state['refresh_interval'] == 30
        assert mock_st.session_state['selected_date'] is None
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_with_existing_values(self, mock_st):
        """Test session state initialization with existing values."""
        # Mock session state with some existing values
        mock_st.session_state = {
            'filter_category': 'Development',
            'show_screenshots': False
        }
        
        defaults = {
            'filter_category': 'All',        # Should not override
            'show_screenshots': True,        # Should not override
            'refresh_interval': 30,          # Should set (new)
            'selected_date': None           # Should set (new)
        }
        
        initialize_session_state(defaults)
        
        # Existing values should be preserved
        assert mock_st.session_state['filter_category'] == 'Development'
        assert mock_st.session_state['show_screenshots'] is False
        
        # New values should be set
        assert mock_st.session_state['refresh_interval'] == 30
        assert mock_st.session_state['selected_date'] is None
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_with_empty_defaults(self, mock_st):
        """Test session state initialization with empty defaults dictionary."""
        mock_st.session_state = {}
        
        initialize_session_state({})
        
        # Session state should remain empty
        assert len(mock_st.session_state) == 0
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_with_various_types(self, mock_st):
        """Test session state initialization with various data types."""
        mock_st.session_state = {}
        
        defaults = {
            'string_value': 'test',
            'int_value': 42,
            'float_value': 3.14,
            'bool_value': True,
            'list_value': [1, 2, 3],
            'dict_value': {'key': 'value'},
            'none_value': None
        }
        
        initialize_session_state(defaults)
        
        # All types should be set correctly
        assert mock_st.session_state['string_value'] == 'test'
        assert mock_st.session_state['int_value'] == 42
        assert mock_st.session_state['float_value'] == 3.14
        assert mock_st.session_state['bool_value'] is True
        assert mock_st.session_state['list_value'] == [1, 2, 3]
        assert mock_st.session_state['dict_value'] == {'key': 'value'}
        assert mock_st.session_state['none_value'] is None
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_preserves_complex_objects(self, mock_st):
        """Test that existing complex objects in session state are preserved."""
        from datetime import datetime
        
        # Mock session state with complex existing object
        existing_datetime = datetime.now()
        mock_st.session_state = {
            'current_time': existing_datetime,
            'user_data': {'name': 'John', 'preferences': {'theme': 'dark'}}
        }
        
        defaults = {
            'current_time': datetime(2024, 1, 1),  # Should not override
            'user_data': {},                       # Should not override
            'new_setting': 'default_value'         # Should set
        }
        
        initialize_session_state(defaults)
        
        # Complex objects should be preserved
        assert mock_st.session_state['current_time'] is existing_datetime
        assert mock_st.session_state['user_data']['name'] == 'John'
        assert mock_st.session_state['user_data']['preferences']['theme'] == 'dark'
        
        # New setting should be added
        assert mock_st.session_state['new_setting'] == 'default_value'


class TestStreamlitHelpersIntegration:
    """Test integration between streamlit helper functions."""
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_complete_dashboard_setup_sequence(self, mock_st):
        """Test a complete dashboard setup sequence using multiple helpers."""
        # Mock session state
        mock_st.session_state = {}
        
        # 1. Configure page
        configure_page("Test Dashboard", "🧪", "wide")
        
        # 2. Initialize session state
        session_defaults = {
            'initialized': True,
            'current_page': 'dashboard'
        }
        initialize_session_state(session_defaults)
        
        # 3. Show header
        show_header("Test Dashboard", "Automated testing interface")
        
        # 4. Show info message
        show_info_message("Dashboard loaded successfully", "✅")
        
        # Verify all functions were called correctly
        mock_st.set_page_config.assert_called_once()
        assert mock_st.session_state['initialized'] is True
        assert mock_st.session_state['current_page'] == 'dashboard'
        mock_st.title.assert_called_once()
        mock_st.markdown.assert_called_once()
        mock_st.divider.assert_called_once()
        mock_st.info.assert_called_once()
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_error_handling_workflow(self, mock_st):
        """Test error handling workflow using helper functions."""
        # Mock expander context manager
        mock_expander = Mock()
        mock_st.expander.return_value.__enter__.return_value = mock_expander
        mock_st.expander.return_value.__exit__.return_value = None
        
        # Configure page for error display
        configure_page("Error Dashboard", "⚠️")
        
        # Show header
        show_header("Error Dashboard", "Something went wrong")
        
        # Show error with details
        show_error_message(
            "Database connection failed",
            "Could not connect to database at ~/.memos/database.db\nPlease check if memos is running"
        )
        
        # Show info for next steps
        show_info_message("Try restarting the memos service", "💡")
        
        # Verify error workflow
        mock_st.set_page_config.assert_called_once()
        mock_st.error.assert_called_once()
        mock_st.expander.assert_called_once_with("Details")
        
        # Validate complete error handling workflow functionality
        assert mock_st.set_page_config.called, "Should configure page"
        assert mock_st.title.called, "Should display header title"
        assert mock_st.markdown.called, "Should display header subtitle"
        assert mock_st.divider.called, "Should display header divider"
        assert mock_st.error.called, "Should display error message"
        assert mock_st.expander.called, "Should create details expander"
        assert mock_st.text.called, "Should display error details"
        assert mock_st.info.called, "Should display info message"
        
        # Validate workflow execution order and content
        page_config_call = mock_st.set_page_config.call_args[1]
        error_call = mock_st.error.call_args[0][0]
        info_call = mock_st.info.call_args[0][0]
        
        assert page_config_call['page_title'] == "Error Dashboard", "Should set correct page title"
        assert page_config_call['page_icon'] == "⚠️", "Should set error icon"
        assert "Database connection failed" in error_call, "Should display specific error"
        assert "💡 Try restarting" in info_call, "Should provide helpful info with icon"
        mock_st.text.assert_called_once()
        mock_st.info.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])