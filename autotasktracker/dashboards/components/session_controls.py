"""Session and debug controls component for dashboard administration."""

import streamlit as st
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import logging

from .base_component import StatelessComponent
from autotasktracker.dashboards.cache import DashboardCache

logger = logging.getLogger(__name__)


class SessionControlsComponent(StatelessComponent):
    """Reusable component for session management and debug controls."""
    
    @staticmethod
    def render(
        show_cache_controls: bool = True,
        show_debug_toggle: bool = True,
        show_session_info: bool = True,
        show_realtime_toggle: bool = False,
        custom_controls: Optional[Dict[str, Callable]] = None,
        compact_mode: bool = False
    ):
        """Render session and debug controls.
        
        Args:
            show_cache_controls: Whether to show cache management buttons
            show_debug_toggle: Whether to show debug mode toggle
            show_session_info: Whether to show session information
            show_realtime_toggle: Whether to show real-time mode toggle
            custom_controls: Dict of custom control labels and callbacks
            compact_mode: Whether to use compact layout
        
        Example:
            SessionControlsComponent.render(
                show_cache_controls=True,
                show_debug_toggle=True,
                custom_controls={
                    "Reset Filters": lambda: st.session_state.update({"filters": {}})
                }
            )
        """
        if compact_mode:
            # Horizontal layout for compact mode
            cols = st.columns([1, 1, 1, 1])
            col_idx = 0
        else:
            # Vertical layout in expander
            with st.expander("🔧 Session Controls", expanded=False):
                SessionControlsComponent._render_all_controls(
                    show_cache_controls=show_cache_controls,
                    show_debug_toggle=show_debug_toggle,
                    show_session_info=show_session_info,
                    show_realtime_toggle=show_realtime_toggle,
                    custom_controls=custom_controls
                )
                return
        
        # Compact mode rendering
        if show_cache_controls and col_idx < len(cols):
            with cols[col_idx]:
                if st.button("🔄 Clear", help="Clear cache", use_container_width=True):
                    SessionControlsComponent._clear_cache()
            col_idx += 1
        
        if show_debug_toggle and col_idx < len(cols):
            with cols[col_idx]:
                debug_mode = st.checkbox(
                    "🐛 Debug",
                    value=st.session_state.get("debug_mode", False),
                    key="debug_mode_toggle"
                )
                if debug_mode != st.session_state.get("debug_mode", False):
                    st.session_state.debug_mode = debug_mode
            col_idx += 1
        
        if show_realtime_toggle and col_idx < len(cols):
            with cols[col_idx]:
                realtime = st.checkbox(
                    "⚡ Live",
                    value=st.session_state.get("realtime_enabled", False),
                    key="realtime_toggle"
                )
                if realtime != st.session_state.get("realtime_enabled", False):
                    st.session_state.realtime_enabled = realtime
            col_idx += 1
    
    @staticmethod
    def _render_all_controls(
        show_cache_controls: bool,
        show_debug_toggle: bool,
        show_session_info: bool,
        show_realtime_toggle: bool,
        custom_controls: Optional[Dict[str, Callable]]
    ):
        """Render all controls in vertical layout."""
        
        # Cache controls
        if show_cache_controls:
            st.subheader("Cache Management")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Clear All Cache", use_container_width=True):
                    SessionControlsComponent._clear_cache()
                    st.success("Cache cleared!")
            
            with col2:
                if st.button("📊 Show Cache Stats", use_container_width=True):
                    SessionControlsComponent._show_cache_stats()
        
        # Debug controls
        if show_debug_toggle:
            st.subheader("Debug Settings")
            
            debug_mode = st.checkbox(
                "Enable Debug Mode",
                value=st.session_state.get("debug_mode", False),
                help="Show detailed error messages and debug information"
            )
            if debug_mode != st.session_state.get("debug_mode", False):
                st.session_state.debug_mode = debug_mode
                st.rerun()
            
            if st.session_state.get("debug_mode", False):
                st.info("🐛 Debug mode is active - detailed errors will be shown")
        
        # Real-time controls
        if show_realtime_toggle:
            st.subheader("Real-time Settings")
            
            realtime_enabled = st.checkbox(
                "Enable Real-time Updates",
                value=st.session_state.get("realtime_enabled", False),
                help="Automatically refresh data in real-time"
            )
            if realtime_enabled != st.session_state.get("realtime_enabled", False):
                st.session_state.realtime_enabled = realtime_enabled
                st.rerun()
            
            if st.session_state.get("realtime_enabled", False):
                refresh_rate = st.slider(
                    "Refresh Rate (seconds)",
                    min_value=1,
                    max_value=60,
                    value=st.session_state.get("refresh_rate", 5),
                    help="How often to refresh data"
                )
                st.session_state.refresh_rate = refresh_rate
        
        # Session info
        if show_session_info:
            st.subheader("Session Information")
            
            # Calculate session duration
            if "session_start" not in st.session_state:
                st.session_state.session_start = datetime.now()
            
            session_duration = datetime.now() - st.session_state.session_start
            
            info_cols = st.columns(2)
            with info_cols[0]:
                st.metric("Session Duration", f"{session_duration.seconds // 60}m {session_duration.seconds % 60}s")
            
            with info_cols[1]:
                st.metric("Session State Items", len(st.session_state))
            
            # Show session state in debug mode
            if st.session_state.get("debug_mode", False):
                with st.expander("Session State Details", expanded=False):
                    # Filter out sensitive items
                    safe_state = {
                        k: v for k, v in st.session_state.items()
                        if not any(sensitive in str(k).lower() for sensitive in ["key", "token", "password", "secret"])
                    }
                    st.json(safe_state)
        
        # Custom controls
        if custom_controls:
            st.subheader("Custom Controls")
            
            for label, callback in custom_controls.items():
                if st.button(label, use_container_width=True):
                    try:
                        callback()
                        st.success(f"✅ {label} completed")
                    except Exception as e:
                        st.error(f"❌ Error in {label}: {str(e)}")
                        if st.session_state.get("debug_mode", False):
                            st.exception(e)
    
    @staticmethod
    def _clear_cache(pattern: Optional[str] = None) -> None:
        """Clear dashboard cache."""
        try:
            DashboardCache.clear_cache(pattern)
            # Clear Streamlit's native cache
            st.cache_data.clear()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            if st.session_state.get("debug_mode", False):
                st.exception(e)
    
    @staticmethod
    def _show_cache_stats():
        """Display cache statistics."""
        try:
            from autotasktracker.pensieve.cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            stats = cache_manager.get_stats()
            
            st.json({
                "Hit Rate": f"{stats.get('hit_rate_percent', 0):.1f}%",
                "Total Requests": stats.get('total_requests', 0),
                "Cache Hits": stats.get('hits', 0),
                "Cache Misses": stats.get('misses', 0),
                "Cache Size": stats.get('size', 0)
            })
        except Exception as e:
            st.info("Cache statistics not available")
            if st.session_state.get("debug_mode", False):
                st.exception(e)
    
    @staticmethod
    def render_minimal(position: str = "sidebar") -> None:
        """Render minimal cache clear button.
        
        Args:
            position: Where to render ("sidebar" or "main")
        """
        container = st.sidebar if position == "sidebar" else st
        
        if container.button("🔄 Clear Cache", help="Clear all cached data"):
            SessionControlsComponent._clear_cache()
            st.success("Cache cleared!")