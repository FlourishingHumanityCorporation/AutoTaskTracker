"""Real-time status indicator component for dashboards."""

from typing import Optional, Dict, Any
import streamlit as st
import logging
from datetime import datetime

from .base_component import StatelessComponent

logger = logging.getLogger(__name__)


class RealtimeStatusComponent(StatelessComponent):
    """Real-time connection and update status indicator."""
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "show_event_count": True,
            "show_last_update": True,
            "show_connection_details": False,
            "compact_mode": False,
            "update_animation": True
        }
    
    def render(self, data: Any, **kwargs) -> None:
        """Render method not used for static component."""
        pass
    
    @staticmethod
    def render(
        mode: str = "static",
        connection_status: Optional[str] = None,
        event_count: Optional[int] = None,
        last_update: Optional[datetime] = None,
        processor_stats: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        container=None
    ) -> None:
        """Render real-time status indicator.
        
        Args:
            mode: Current mode (live/paused/static)
            connection_status: WebSocket connection status
            event_count: Number of events processed
            last_update: Last update timestamp
            processor_stats: Event processor statistics
            config: Optional configuration overrides
            container: Streamlit container to render in (default: current container)
        """
        # Merge configuration
        display_config = RealtimeStatusComponent.get_default_config()
        if config:
            display_config.update(config)
        
        # Use provided container or current position
        target = container or st
        
        if display_config["compact_mode"]:
            # Compact single-line display
            RealtimeStatusComponent._render_compact(
                target, mode, event_count, last_update, display_config
            )
        else:
            # Full status display
            RealtimeStatusComponent._render_full(
                target, mode, connection_status, event_count, 
                last_update, processor_stats, display_config
            )
    
    @staticmethod
    def _render_compact(
        container,
        mode: str,
        event_count: Optional[int],
        last_update: Optional[datetime],
        config: Dict[str, Any]
    ) -> None:
        """Render compact status indicator."""
        status_parts = []
        
        # Mode indicator
        if mode == "live":
            status_parts.append("🔄 Live")
        elif mode == "paused":
            status_parts.append("⏸️ Paused")
        else:
            status_parts.append("📋 Static")
        
        # Event count
        if config["show_event_count"] and event_count is not None:
            status_parts.append(f"Events: {event_count}")
        
        # Last update
        if config["show_last_update"] and last_update:
            time_diff = datetime.now() - last_update
            if time_diff.total_seconds() < 60:
                status_parts.append("Just now")
            elif time_diff.total_seconds() < 3600:
                minutes = int(time_diff.total_seconds() / 60)
                status_parts.append(f"{minutes}m ago")
            else:
                status_parts.append(last_update.strftime("%H:%M"))
        
        container.caption(" | ".join(status_parts))
    
    @staticmethod
    def _render_full(
        container,
        mode: str,
        connection_status: Optional[str],
        event_count: Optional[int],
        last_update: Optional[datetime],
        processor_stats: Optional[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> None:
        """Render full status display."""
        # Main status indicator
        if mode == "live":
            if processor_stats and processor_stats.get('running'):
                container.success("🔄 Live")
            else:
                container.warning("🔄 Live (Starting...)")
        elif mode == "paused":
            container.warning("⏸️ Paused")
        else:
            container.info("📋 Static")
        
        # Event count
        if config["show_event_count"] and event_count is not None:
            container.caption(f"Events: {event_count:,}")
        
        # Connection details
        if config["show_connection_details"] and connection_status:
            if connection_status == "connected":
                container.caption("🟢 WebSocket connected")
            elif connection_status == "connecting":
                container.caption("🟡 Connecting...")
            else:
                container.caption("🔴 Disconnected")
        
        # Last update time
        if config["show_last_update"] and last_update:
            time_diff = datetime.now() - last_update
            if time_diff.total_seconds() < 60:
                update_text = "Updated just now"
            elif time_diff.total_seconds() < 3600:
                minutes = int(time_diff.total_seconds() / 60)
                update_text = f"Updated {minutes}m ago"
            else:
                update_text = f"Updated at {last_update.strftime('%H:%M')}"
            
            container.caption(update_text)
        
        # Additional processor stats
        if processor_stats and config.get("show_processor_stats", False):
            with container.expander("📊 Details", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Queue Size", processor_stats.get('queue_size', 0))
                    st.metric("Threads", processor_stats.get('active_threads', 0))
                with col2:
                    st.metric("Errors", processor_stats.get('errors', 0))
                    st.metric("Uptime", RealtimeStatusComponent._format_uptime(
                        processor_stats.get('uptime_seconds', 0)
                    ))
    
    @staticmethod
    def render_sidebar_controls(
        default_enabled: bool = True,
        show_interval_slider: bool = True,
        show_connection_info: bool = True
    ) -> Dict[str, Any]:
        """Render real-time controls in sidebar.
        
        Args:
            default_enabled: Default state for real-time toggle
            show_interval_slider: Show refresh interval slider
            show_connection_info: Show connection information
            
        Returns:
            Dictionary with control values
        """
        st.sidebar.subheader("🔄 Real-time Updates")
        
        # Enable/disable toggle
        realtime_enabled = st.sidebar.toggle(
            "Auto-refresh", 
            value=st.session_state.get('realtime_enabled', default_enabled),
            help="Automatically refresh when new data is available"
        )
        st.session_state.realtime_enabled = realtime_enabled
        
        result = {"enabled": realtime_enabled}
        
        if realtime_enabled:
            # Refresh interval
            if show_interval_slider:
                refresh_interval = st.sidebar.slider(
                    "Refresh interval (seconds)",
                    min_value=1,
                    max_value=60,
                    value=st.session_state.get('refresh_interval', 5),
                    help="How often to check for updates"
                )
                st.session_state.refresh_interval = refresh_interval
                result["refresh_interval"] = refresh_interval
            
            # Connection info
            if show_connection_info:
                websocket_connected = st.session_state.get('websocket_connected', False)
                if websocket_connected:
                    st.sidebar.success("🟢 WebSocket: Connected")
                    st.sidebar.caption("Real-time events active")
                else:
                    st.sidebar.warning("🟡 WebSocket: Connecting...")
                    st.sidebar.caption("Falling back to polling")
                
                result["websocket_connected"] = websocket_connected
        else:
            st.sidebar.info("Updates paused")
            st.sidebar.caption("Enable to receive real-time updates")
        
        return result
    
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}d {hours}h"