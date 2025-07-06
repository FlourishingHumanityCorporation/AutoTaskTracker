"""Base dashboard class with common functionality for all dashboards."""

import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pandas as pd

from autotasktracker.core import DatabaseManager
from autotasktracker.config import get_config
from autotasktracker.utils.streamlit_helpers import configure_page, show_error_message
from autotasktracker.dashboards.cache import DashboardCache, QueryCache
from autotasktracker.pensieve.health_monitor import get_health_monitor, HealthAwareMixin
from autotasktracker.pensieve.api_client import get_pensieve_client
from autotasktracker.pensieve.event_integration import get_event_integrator
from autotasktracker.dashboards.websocket_client import StreamlitWebSocketMixin, get_websocket_client_for_dashboard
from autotasktracker.dashboards.components.performance_display import render_performance_sidebar, render_mini_performance_status

logger = logging.getLogger(__name__)


class BaseDashboard(HealthAwareMixin, StreamlitWebSocketMixin):
    """Base class for all AutoTaskTracker dashboards.
    
    Provides common functionality:
    - Database connection management
    - Pensieve health monitoring with graceful degradation
    - Real-time WebSocket event integration
    - Page configuration
    - Error handling
    - Time filtering
    - Session state management
    """
    
    def __init__(self, title: str, icon: str = "🤖", port: Optional[int] = None):
        """Initialize dashboard with common setup.
        
        Args:
            title: Dashboard title
            icon: Emoji icon for the page
            port: Optional port number for the dashboard
        """
        # Initialize health monitoring and WebSocket first
        super().__init__()
        
        self.title = title
        self.icon = icon
        self.port = port
        self.config = get_config()
        self._db_manager: Optional[DatabaseManager] = None
        
        # Set dashboard ID for WebSocket client
        self.dashboard_id = f"{self.__class__.__name__}_{port}" if port else self.__class__.__name__
        
        # Configure page
        self.setup_page()
        
        # Initialize real-time updates
        self.setup_realtime_updates()
        
        # Initialize session state
        self.init_session_state()
        
        # Setup real-time updates if enabled
        self.setup_realtime_updates()
        self.setup_event_listeners()
        
        # Show Pensieve health status
        self.show_health_status()
        
    def setup_page(self):
        """Configure Streamlit page settings."""
        configure_page(self.title, self.icon)
        
    def init_session_state(self):
        """Initialize common session state variables."""
        if 'time_filter' not in st.session_state:
            st.session_state.time_filter = 'Today'
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = datetime.now()
        if 'show_raw_data' not in st.session_state:
            st.session_state.show_raw_data = False
            
    @property
    def db_manager(self) -> DatabaseManager:
        """Get database manager instance (lazy loading)."""
        if self._db_manager is None:
            try:
                # For dashboards, use a simplified connection approach to avoid timeouts
                from autotasktracker.dashboards.simple_db import SimpleDatabaseManager
                
                logger.info(f"Dashboard using simplified PostgreSQL connection: {self.config.DB_PATH}")
                self._db_manager = SimpleDatabaseManager(self.config.DB_PATH)
                logger.info(f"Database type: {self._db_manager.get_database_type()}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize simplified database manager: {e}")
                # Fallback to regular DatabaseManager
                try:
                    self._db_manager = DatabaseManager(
                        db_path=self.config.DB_PATH, 
                        use_pensieve_api=False
                    )
                    logger.info("Fallback to regular DatabaseManager succeeded")
                except Exception as e2:
                    logger.error(f"All database managers failed: {e2}")
                    # Create emergency simple connection
                    from autotasktracker.dashboards.simple_db import SimpleDatabaseManager
                    self._db_manager = SimpleDatabaseManager("sqlite://~/.memos/database.db")
        return self._db_manager
    
    def show_health_status(self):
        """Show Pensieve service health status in sidebar."""
        with st.sidebar:
            st.divider()
            
            # Get health status
            health_summary = self.get_health_status()
            status = health_summary.get('status', 'unknown')
            
            if status == 'healthy':
                st.success("🟢 Pensieve Healthy")
            elif status == 'unhealthy':
                st.error("🔴 Pensieve Issues")
                
                # Show specific issues
                if 'warnings' in health_summary:
                    for warning in health_summary['warnings'][:3]:  # Show max 3 warnings
                        st.warning(f"⚠️ {warning}")
                
                # Show degraded mode notice
                if self._degraded_mode:
                    st.info("📊 Running in degraded mode (direct database access)")
            else:
                st.warning("🟡 Pensieve Status Unknown")
            
            # Show cache status
            self._show_cache_status()
            
            # Show performance metrics
            render_performance_sidebar()
            
            # Show quick metrics
            if 'metrics' in health_summary:
                metrics = health_summary['metrics']
                response_time = metrics.get('response_time_ms', 0)
                
                if response_time > 0:
                    if response_time < 500:
                        st.caption(f"⚡ Response: {response_time:.0f}ms")
                    else:
                        st.caption(f"🐌 Response: {response_time:.0f}ms")
    
    def _on_pensieve_degraded(self):
        """Handle Pensieve becoming unhealthy."""
        logger.warning("Dashboard entering degraded mode - Pensieve unavailable")
        st.toast("⚠️ Pensieve unavailable - using direct database access", icon="⚠️")
    
    def _on_pensieve_recovered(self):
        """Handle Pensieve recovery."""
        logger.info("Dashboard exiting degraded mode - Pensieve recovered")
        st.toast("✅ Pensieve recovered - full functionality restored", icon="✅")
        
    def ensure_connection(self) -> bool:
        """Ensure database connection is available.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.db_manager.test_connection():
            show_error_message(
                "Cannot connect to database",
                "Make sure Memos is running: memos start"
            )
            return False
        return True
        
    def get_time_range(self, time_filter: str) -> Tuple[datetime, datetime]:
        """Convert time filter to datetime range.
        
        Args:
            time_filter: Time filter string (Today, This Week, etc.)
            
        Returns:
            Tuple of (start_datetime, end_datetime)
        """
        now = datetime.now()
        
        if time_filter == "Today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_filter == "Yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
        elif time_filter == "This Week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_filter == "Last 7 Days":
            start = now - timedelta(days=7)
            end = now
        elif time_filter == "This Month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_filter == "Last 30 Days":
            start = now - timedelta(days=30)
            end = now
        else:  # All Time
            start = datetime(2020, 1, 1)
            end = now
            
        return start, end
        
    def get_filtered_data(self, time_filter: str, limit: int = 1000, use_cache: bool = True) -> pd.DataFrame:
        """Get filtered data based on time range.
        
        Args:
            time_filter: Time filter string
            limit: Maximum number of records to return
            use_cache: Whether to use caching
            
        Returns:
            DataFrame with filtered data
        """
        start_date, end_date = self.get_time_range(time_filter)
        
        if use_cache:
            # Use cached query
            return QueryCache.get_time_filtered_data(
                self.db_manager,
                start_date,
                end_date,
                limit
            )
        else:
            # Direct query without caching
            query = """
            SELECT 
                e.id,
                e.created_at,
                e.file_path,
                m1.value as ocr_text,
                m2.value as active_window,
                m3.value as tasks,
                m4.value as category,
                m5.value as window_title
            FROM entities e
            LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'text'
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "active_window"
            LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = "tasks"
            LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = "category"
            LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = "active_window"
            WHERE e.created_at >= ? AND e.created_at <= ?
            ORDER BY e.created_at DESC
            LIMIT ?
            """
            
            params = (
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S'),
                limit
            )
            
            return self.db_manager.execute_query(query, params)
        
    def render_time_filter(self, key: str = "time_filter") -> str:
        """Render time filter selectbox.
        
        Args:
            key: Session state key for the filter
            
        Returns:
            Selected time filter value
        """
        time_options = [
            "Today", "Yesterday", "This Week", 
            "Last 7 Days", "This Month", "Last 30 Days", "All Time"
        ]
        
        return st.selectbox(
            "Time Period",
            time_options,
            index=time_options.index(st.session_state.get(key, "Today")),
            key=key
        )
        
    def render_metrics_row(self, metrics: Dict[str, Any], columns: int = 4):
        """Render a row of metrics.
        
        Args:
            metrics: Dictionary of metric_name: metric_value
            columns: Number of columns to display
        """
        cols = st.columns(columns)
        for i, (label, value) in enumerate(metrics.items()):
            with cols[i % columns]:
                st.metric(label, value)
                
    def show_no_data_message(self, message: str = "No data available for the selected time period"):
        """Display a friendly no-data message."""
        st.info(f"📊 {message}")
        
    def add_auto_refresh(self, interval_seconds: int = 300):
        """Add auto-refresh functionality to the dashboard.
        
        Args:
            interval_seconds: Refresh interval in seconds
        """
        # Add meta refresh tag
        st.markdown(
            f'<meta http-equiv="refresh" content="{interval_seconds}">',
            unsafe_allow_html=True
        )
        
        # Show last refresh time
        if st.session_state.last_refresh:
            st.caption(f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
            
    def handle_error(self, error: Exception, context: str = ""):
        """Handle errors gracefully.
        
        Args:
            error: The exception that occurred
            context: Additional context about what was being done
        """
        logger.error(f"Dashboard error in {context}: {str(error)}", exc_info=True)
        st.error(f"❌ An error occurred{f' while {context}' if context else ''}: {str(error)}")
        
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear dashboard cache.
        
        Args:
            pattern: Optional pattern to match cache keys
        """
        DashboardCache.clear_cache(pattern)
        st.rerun()
        
    def render_cache_controls(self):
        """Render cache control buttons in sidebar."""
        if st.sidebar.button("🔄 Clear Cache", help="Clear all cached data"):
            self.clear_cache()
            st.success("Cache cleared!")
    
    def _show_cache_status(self):
        """Show cache performance status in sidebar."""
        try:
            from autotasktracker.pensieve.cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            stats = cache_manager.get_stats()
            
            hit_rate = stats.get('hit_rate_percent', 0)
            total_requests = stats.get('total_requests', 0)
            
            if total_requests > 0:
                if hit_rate >= 70:
                    st.caption(f"🚀 Cache: {hit_rate:.0f}% hit rate")
                elif hit_rate >= 40:
                    st.caption(f"⚡ Cache: {hit_rate:.0f}% hit rate")
                else:
                    st.caption(f"📈 Cache: {hit_rate:.0f}% hit rate")
            else:
                st.caption("💾 Cache: Ready")
                
        except (AttributeError, TypeError, ImportError) as e:
            # Don't show cache status if there's an error
            logger.debug(f"Error showing cache status: {e}")
            pass
    
    def setup_realtime_updates(self):
        """Setup real-time dashboard updates with WebSocket integration."""
        # Initialize real-time state
        if 'realtime_enabled' not in st.session_state:
            st.session_state.realtime_enabled = True
        if 'last_update_time' not in st.session_state:
            st.session_state.last_update_time = datetime.now()
        
        # Initialize WebSocket connection status
        if 'websocket_connected' not in st.session_state:
            st.session_state.websocket_connected = False
        if 'websocket_status' not in st.session_state:
            st.session_state.websocket_status = "Connecting"
        
        # Remove auto_refresh_interval - no longer needed with WebSocket events
        if 'auto_refresh_interval' in st.session_state:
            del st.session_state.auto_refresh_interval
    
    def setup_event_listeners(self):
        """Setup event listeners for real-time dashboard updates."""
        try:
            # Get event integrator but don't fail if not available
            event_integrator = get_event_integrator()
            
            # Set up a simple event handler for screenshot processing
            def handle_screenshot_event(event):
                """Handle new screenshot events by triggering refresh."""
                if st.session_state.get('realtime_enabled', False):
                    # Set a flag that can be checked in the next dashboard refresh cycle
                    st.session_state.needs_refresh = True
                    st.session_state.refresh_reason = f"New screenshot processed: {event.entity_id}"
            
            # Note: In a real implementation, we'd register this handler
            # For now, we'll rely on the time-based refresh mechanism
            
        except Exception as e:
            logger.debug(f"Could not setup event listeners: {e}")
    
    def check_for_updates(self) -> bool:
        """Check if dashboard needs to refresh due to new data.
        
        With WebSocket integration, refreshes are triggered by real-time events
        instead of polling. This method now only checks for manual refresh triggers.
        
        Returns:
            True if refresh is needed
        """
        if not st.session_state.get('realtime_enabled', False):
            return False
        
        # Check for event-driven refresh first (triggered by WebSocket events)
        if st.session_state.get('needs_refresh', False):
            st.session_state.needs_refresh = False  # Reset flag
            return True
            
        # WebSocket events trigger automatic refreshes via st.rerun()
        # No more time-based polling needed
        return False
    
    def trigger_refresh(self, reason: str = "Data updated"):
        """Trigger a dashboard refresh.
        
        Args:
            reason: Reason for the refresh
        """
        st.session_state.last_update_time = datetime.now()
        
        # Invalidate relevant cache
        if hasattr(self, 'db_manager') and hasattr(self.db_manager, 'cache'):
            # Invalidate recent data cache
            from autotasktracker.dashboards.data.repositories import BaseRepository
            repo = BaseRepository(self.db_manager)
            repo.invalidate_cache("query_")  # Invalidate query cache
        
        # Clear Streamlit cache
        DashboardCache.clear_cache()
        
        # Force Streamlit to rerun
        st.rerun()
    
    def render_realtime_controls(self):
        """Render real-time update controls in sidebar."""
        with st.sidebar:
            st.subheader("🔄 Real-time Updates")
            
            # Enable/disable toggle
            realtime_enabled = st.toggle(
                "Auto-refresh", 
                value=st.session_state.get('realtime_enabled', True),
                help="Automatically refresh when new data is available"
            )
            st.session_state.realtime_enabled = realtime_enabled
            
            if realtime_enabled:
                # Show WebSocket connection status
                websocket_connected = st.session_state.get('websocket_connected', False)
                websocket_status = st.session_state.get('websocket_status', 'Unknown')
                
                if websocket_connected:
                    st.success("🟢 Real-time: Connected")
                    st.caption("Dashboard updates automatically via WebSocket events")
                else:
                    st.warning(f"🟡 Real-time: {websocket_status}")
                    st.caption("Attempting to connect to event server...")
                
                # Manual refresh button (still useful for manual updates)
                if st.button("🔄 Refresh Now"):
                    self.trigger_refresh("Manual refresh")
                
                # Show last update time
                last_update = st.session_state.get('last_update_time')
                if last_update:
                    time_ago = (datetime.now() - last_update).total_seconds()
                    if time_ago < 60:
                        st.caption(f"Last updated {time_ago:.0f}s ago")
                    else:
                        st.caption(f"Last updated {time_ago//60:.0f}m ago")
                        
                # Show WebSocket metrics if available
                if hasattr(self, 'websocket_client') and self.websocket_client:
                    status = self.websocket_client.get_connection_status()
                    if status.get('messages_received', 0) > 0:
                        st.caption(f"📊 Events received: {status['messages_received']}")
            
    def run(self):
        """Main dashboard execution method. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the run() method")