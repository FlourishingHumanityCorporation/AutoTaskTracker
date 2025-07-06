"""Dashboard header component for consistent header display across dashboards."""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime

from .base_component import StatelessComponent


class DashboardHeader(StatelessComponent):
    """Reusable dashboard header component with responsive layout."""
    
    @staticmethod
    def render(
        title: str,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        right_column_content: Optional[Dict[str, Any]] = None,
        show_timestamp: bool = False,
        extra_info: Optional[str] = None,
        column_ratio: list = [3, 1]
    ):
        """Render a dashboard header with optional right column content.
        
        Args:
            title: Main dashboard title
            subtitle: Optional subtitle or description
            icon: Optional emoji/icon to prepend to title
            right_column_content: Optional dict with:
                - component: The component class to render
                - params: Dict of parameters to pass to component
            show_timestamp: Whether to show current timestamp
            extra_info: Additional info to display below subtitle
            column_ratio: Column width ratio [left, right]
        
        Example:
            DashboardHeader.render(
                title="Task Board",
                subtitle="Track and visualize your daily tasks",
                icon="📋",
                right_column_content={
                    'component': RealtimeStatusComponent,
                    'params': {'mode': 'live', 'event_count': 42}
                }
            )
        """
        # Create columns if right content is provided
        if right_column_content:
            col1, col2 = st.columns(column_ratio)
            
            with col1:
                DashboardHeader._render_left_content(
                    title, subtitle, icon, show_timestamp, extra_info
                )
            
            with col2:
                # Render the right column component
                component = right_column_content.get('component')
                params = right_column_content.get('params', {})
                if component and hasattr(component, 'render'):
                    component.render(**params)
        else:
            # No right content, render full width
            DashboardHeader._render_left_content(
                title, subtitle, icon, show_timestamp, extra_info
            )
    
    @staticmethod
    def _render_left_content(
        title: str,
        subtitle: Optional[str],
        icon: Optional[str],
        show_timestamp: bool,
        extra_info: Optional[str]
    ):
        """Render the left side content of the header."""
        # Title with optional icon
        if icon:
            st.title(f"{icon} {title}")
        else:
            st.title(title)
        
        # Subtitle
        if subtitle:
            st.markdown(subtitle)
        
        # Extra info
        if extra_info:
            st.caption(extra_info)
        
        # Timestamp
        if show_timestamp:
            st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    @staticmethod
    def render_simple(title: str, subtitle: Optional[str] = None, icon: Optional[str] = None):
        """Convenience method for simple headers without right column.
        
        Args:
            title: Main dashboard title
            subtitle: Optional subtitle
            icon: Optional emoji/icon
        """
        DashboardHeader.render(
            title=title,
            subtitle=subtitle,
            icon=icon,
            right_column_content=None
        )