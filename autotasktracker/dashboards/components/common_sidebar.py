"""Common sidebar component for dashboard consolidation."""

import streamlit as st
from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod

from .filters import TimeFilterComponent, CategoryFilterComponent
from .smart_defaults import SmartDefaultsComponent
from .session_controls import SessionControlsComponent


class SidebarSection:
    """Represents a configurable sidebar section."""
    
    def __init__(self, title: str, render_func: Callable, enabled: bool = True):
        self.title = title
        self.render_func = render_func
        self.enabled = enabled


class CommonSidebar:
    """Common sidebar functionality for all dashboards."""
    
    @staticmethod
    def render(
        header_title: str,
        header_icon: str = "⚙️",
        db_manager=None,
        enable_time_filter: bool = True,
        enable_category_filter: bool = True,
        enable_smart_defaults: bool = True,
        enable_session_controls: bool = True,
        custom_sections: Optional[list] = None,
        session_controls_position: str = "bottom"
    ) -> Dict[str, Any]:
        """Render common sidebar with configurable sections.
        
        Args:
            header_title: Title for the sidebar header
            header_icon: Icon for the header
            db_manager: Database manager for smart defaults
            enable_time_filter: Whether to show time filter
            enable_category_filter: Whether to show category filter
            enable_smart_defaults: Whether to show smart defaults button
            enable_session_controls: Whether to show session controls
            custom_sections: List of SidebarSection objects for custom content
            session_controls_position: Where to place session controls ("top", "bottom", "none")
            
        Returns:
            Dictionary with filter values and any custom section results
        """
        results = {}
        
        with st.sidebar:
            # Header
            st.header(f"{header_icon} {header_title}")
            
            # Session controls at top if requested
            if enable_session_controls and session_controls_position == "top":
                SessionControlsComponent.render_minimal(position="sidebar")
            
            # Time filter section
            if enable_time_filter:
                results['time_filter'] = TimeFilterComponent.render(db_manager=db_manager)
            
            # Smart defaults button
            if enable_smart_defaults and db_manager:
                SmartDefaultsComponent.render_smart_defaults_button(
                    db_manager=db_manager,
                    show_explanation=False  # Keep compact in sidebar
                )
            
            # Category filter section
            if enable_category_filter:
                results['categories'] = CategoryFilterComponent.render(multiselect=True)
            
            # Custom sections
            if custom_sections:
                for section in custom_sections:
                    if section.enabled:
                        if section.title:
                            st.subheader(section.title)
                        section_result = section.render_func()
                        if section_result is not None:
                            results[section.title.lower().replace(' ', '_')] = section_result
            
            # Session controls at bottom if requested (default)
            if enable_session_controls and session_controls_position == "bottom":
                SessionControlsComponent.render_minimal(position="sidebar")
        
        return results


class BaseSidebarMixin:
    """Mixin to provide common sidebar functionality to dashboard classes."""
    
    def render_common_sidebar(
        self,
        header_title: str,
        header_icon: str = "⚙️",
        **kwargs
    ) -> Dict[str, Any]:
        """Render common sidebar using the dashboard's db_manager."""
        return CommonSidebar.render(
            header_title=header_title,
            header_icon=header_icon,
            db_manager=getattr(self, 'db_manager', None),
            **kwargs
        )
    
    def create_display_options_section(self, options: Dict[str, bool]) -> SidebarSection:
        """Create a display options section.
        
        Args:
            options: Dictionary of option_name: default_value
            
        Returns:
            SidebarSection for display options
        """
        def render_display_options():
            results = {}
            for option_name, default_value in options.items():
                # Convert snake_case to Title Case for display
                display_name = option_name.replace('_', ' ').title()
                results[option_name] = st.checkbox(
                    display_name,
                    value=default_value,
                    key=option_name
                )
            return results
        
        return SidebarSection("Display Options", render_display_options)