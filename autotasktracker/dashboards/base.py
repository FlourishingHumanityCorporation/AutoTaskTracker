"""Base dashboard class with common functionality for all dashboards."""

import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pandas as pd

from ..core.database import DatabaseManager
from ..utils.config import get_config
from ..utils.streamlit_helpers import configure_page, show_error_message
from .cache import DashboardCache, QueryCache

logger = logging.getLogger(__name__)


class BaseDashboard:
    """Base class for all AutoTaskTracker dashboards.
    
    Provides common functionality:
    - Database connection management
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
        self.title = title
        self.icon = icon
        self.port = port
        self.config = get_config()
        self._db_manager: Optional[DatabaseManager] = None
        
        # Configure page
        self.setup_page()
        
        # Initialize session state
        self.init_session_state()
        
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
            self._db_manager = DatabaseManager(self.config.DB_PATH)
        return self._db_manager
        
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
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
            LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
            LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
            LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = 'window_title'
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
            
    def run(self):
        """Main dashboard execution method. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the run() method")