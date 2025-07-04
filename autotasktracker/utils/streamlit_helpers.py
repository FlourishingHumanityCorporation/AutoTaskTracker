"""
Streamlit utility functions to reduce code duplication across dashboards.
"""

import streamlit as st


def configure_page(title: str, icon: str = "📊", layout: str = "wide", initial_sidebar_state: str = "auto"):
    """
    Configure Streamlit page with common settings.
    
    Args:
        title: Page title for browser tab
        icon: Page icon emoji
        layout: Page layout ('wide' or 'centered')
        initial_sidebar_state: Sidebar state ('auto', 'expanded', 'collapsed')
    """
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,
        initial_sidebar_state=initial_sidebar_state
    )


def show_header(title: str, subtitle: str = None):
    """
    Display a consistent header across dashboards.
    
    Args:
        title: Main title
        subtitle: Optional subtitle
    """
    st.title(title)
    if subtitle:
        st.markdown(f"*{subtitle}*")
    st.divider()


def show_error_message(message: str, details: str = None):
    """
    Display consistent error messages.
    
    Args:
        message: Error message
        details: Optional additional details
    """
    st.error(message)
    if details:
        with st.expander("Details"):
            st.text(details)


def show_info_message(message: str, icon: str = "ℹ️"):
    """
    Display consistent info messages.
    
    Args:
        message: Info message
        icon: Icon to show
    """
    st.info(f"{icon} {message}")


def initialize_session_state(defaults: dict):
    """
    Initialize session state variables with defaults.
    
    Args:
        defaults: Dictionary of key-value pairs for session state
    """
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value