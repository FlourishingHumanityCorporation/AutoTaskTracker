"""Refactored Task Board Dashboard using new architecture.

This is an example of how to refactor existing dashboards to use:
- Base dashboard class
- Reusable components
- Data repositories
- Cleaner separation of concerns
"""

import streamlit as st
from datetime import datetime, timedelta
import logging
import time

# Real-time integration imports
from autotasktracker.pensieve.event_processor import get_event_processor, PensieveEvent
from autotasktracker.pensieve.cache_manager import get_cache_manager

# Removed sys.path hack - using proper package imports

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.utils.debug_capture import get_debug_capture, capture_event
from autotasktracker.dashboards.components import (
    TimeFilterComponent, 
    CategoryFilterComponent,
    MetricsRow,
    TaskGroup as TaskGroupComponent,
    NoDataMessage,
    EnhancedSearch,
    ExportComponent,
    RealtimeStatusComponent,
    DashboardHeader
)
from autotasktracker.dashboards.components.smart_defaults import SmartDefaultsComponent
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class TaskBoardDashboard(BaseDashboard):
    """Refactored Task Board dashboard."""
    
    def __init__(self):
        super().__init__(
            title="Task Board - AutoTaskTracker",
            icon="📋",
            port=get_config().TASK_BOARD_PORT
        )
        
        # Real-time integration setup
        self.event_processor = get_event_processor()
        self.cache_manager = get_cache_manager()
        self.last_refresh = time.time()
        self.refresh_interval = 30  # seconds
        
        # Register dashboard update handler
        self.event_processor.register_event_handler('entity_added', self._handle_realtime_update)
        self.event_processor.register_event_handler('entity_processed', self._handle_realtime_update)
        
    def init_session_state(self):
        """Initialize dashboard-specific session state with smart defaults."""
        super().init_session_state()
        
        # Task board specific state with smart defaults
        if 'group_by' not in st.session_state:
            st.session_state.group_by = 'window'
        if 'show_screenshots' not in st.session_state:
            st.session_state.show_screenshots = True
        if 'min_duration' not in st.session_state:
            st.session_state.min_duration = 1
        if 'realtime_enabled' not in st.session_state:
            st.session_state.realtime_enabled = True
        if 'last_update_time' not in st.session_state:
            st.session_state.last_update_time = datetime.now()
            
        # Initialize smart time filter if not set
        if 'time_filter' not in st.session_state:
            st.session_state.time_filter = SmartDefaultsComponent.get_time_period_default(self.db_manager)
            
        # Initialize category filter to empty (all categories) if not set
        if 'category_filter' not in st.session_state:
            st.session_state.category_filter = []  # Empty = all categories
            
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            st.header("⚙️ Task Board Settings")
            
            # Time filter with smart defaults
            time_filter = TimeFilterComponent.render(db_manager=self.db_manager)
            
            # Smart default button using new component
            SmartDefaultsComponent.render_smart_defaults_button(
                db_manager=self.db_manager,
                show_explanation=False  # Keep it compact in sidebar
            )
            
            # Category filter (fixed logic)
            categories = CategoryFilterComponent.render(multiselect=True)
            
            # Display options
            st.subheader("Display Options")
            show_screenshots = st.checkbox(
                "Show Screenshots",
                value=st.session_state.show_screenshots,
                key="show_screenshots"
            )
            
            min_duration = st.slider(
                "Minimum Duration (minutes)",
                min_value=1,
                max_value=30,
                value=st.session_state.min_duration,
                key="min_duration"
            )
            
            # Real-time updates
            self.render_realtime_controls()
            
            # Export functionality in sidebar for quick access
            st.subheader("📥 Export Data")
            if st.button("Export to CSV", help="Export current task data as CSV for reporting"):
                st.session_state.export_csv = True
            
            # Debug capture controls
            st.subheader("🐛 Debug Capture")
            debug_capture = get_debug_capture()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📸 Capture Now", help="Capture current dashboard state"):
                    path = debug_capture.capture_browser_window()
                    if path:
                        st.success(f"Screenshot saved!")
                    else:
                        st.error("Capture failed")
            
            with col2:
                if st.button("📊 Session Info", help="Show debug session information"):
                    summary = debug_capture.get_session_summary()
                    st.json(summary)
                
            # Real-time controls
            st.sidebar.markdown("### 🔄 Real-time Updates")
            realtime_enabled = st.sidebar.checkbox(
                "Enable real-time updates",
                value=st.session_state.realtime_enabled,
                help="Automatically refresh when new screenshots are processed"
            )
            st.session_state.realtime_enabled = realtime_enabled
            
            if realtime_enabled:
                refresh_interval = st.sidebar.slider(
                    "Refresh interval (seconds)",
                    min_value=10,
                    max_value=120,
                    value=30,
                    step=10
                )
                self.refresh_interval = refresh_interval
                
                # Show last update time
                st.sidebar.caption(f"Last updated: {st.session_state.last_update_time.strftime('%H:%M:%S')}")
            
            return time_filter, categories, show_screenshots, min_duration
            
    def render_metrics(self, metrics_repo: MetricsRepository, start_date: datetime, end_date: datetime):
        """Render metrics section."""
        # Get summary metrics
        summary = metrics_repo.get_metrics_summary(start_date, end_date)
        
        # Display metrics
        MetricsRow.render({
            "📊 Total Activities": summary['total_activities'],
            "📅 Active Days": summary['active_days'],
            "🪟 Unique Windows": summary['unique_windows'],
            "🏷️ Categories": summary['unique_categories']
        })
        
        # Daily average
        if summary['active_days'] > 0:
            st.metric(
                "Daily Average",
                f"{summary['avg_daily_activities']:.0f} activities",
                help="Average number of activities per active day"
            )
            

    def render_task_groups(
        self, 
        task_repo: TaskRepository,
        start_date: datetime,
        end_date: datetime,
        categories: list,
        show_screenshots: bool,
        min_duration: int
    ):
        """Render task groups."""
        # Get grouped tasks
        task_groups = task_repo.get_task_groups(
            start_date=start_date,
            end_date=end_date,
            min_duration_minutes=min_duration
        )
        
        # Filter by categories if specified (empty list means all categories)
        if categories:  # If specific categories selected
            task_groups = [
                group for group in task_groups 
                if group.category in categories
            ]
            
        if not task_groups:
            # Check if this is a data availability issue or filter issue
            total_tasks = task_repo.get_task_groups(
                start_date=start_date - timedelta(days=30),  # Check last 30 days
                end_date=end_date,
                min_duration_minutes=0  # No duration filter
            )
            
            if not total_tasks:
                # No data at all
                NoDataMessage.render(
                    "No task data available",
                    suggestions=[
                        "Check if Memos/Pensieve is running: 'memos ps'",
                        "Start screenshot capture: 'memos start'",
                        "Wait a few minutes for data to be captured"
                    ]
                )
            else:
                # Data exists, but filters are too restrictive
                smart_default = SmartDefaultsComponent.get_time_period_default(self.db_manager)
                
                NoDataMessage.render(
                    "No tasks found for current filters",
                    suggestions=[
                        f"Found {len(total_tasks)} tasks in last 30 days",
                        f"💡 Try clicking 'Smart Default' (suggests: {smart_default})",
                        "Or select 'Last 7 Days' or 'Yesterday' manually",
                        "Clear category filters (leave empty for all)",
                        "Lower minimum duration to 1 minute"
                    ]
                )
            return
            
        # Sort by duration
        task_groups.sort(key=lambda x: x.duration_minutes, reverse=True)
        
        # Display task groups with AI-enhanced display
        st.subheader(f"📋 Tasks ({len(task_groups)})")
        
        # Add a toggle to switch between AI and basic view
        col1, col2 = st.columns(2)
        with col1:
            use_ai_display = st.toggle(
                "✨ AI-Enhanced View", 
                value=True,
                help="Enable AI-powered task extraction and analysis"
            )
        
        # Group tasks by window title and category for display
        for i, group in enumerate(task_groups[:20]):  # Limit to top 20
            # Extract first task for screenshot
            screenshot_path = group.tasks[0].screenshot_path if group.tasks else None
            
            # Prepare task data - pass full task objects for AI display
            task_data = []
            for task in group.tasks[:5]:  # Show up to 5 tasks
                task_info = {
                    'id': task.id,
                    'title': task.title,
                    'timestamp': task.timestamp.isoformat(),
                    'ocr_text': task.ocr_text,
                    'screenshot_path': task.screenshot_path
                }
                
                # Include AI metadata if available
                if task.metadata:
                    task_info.update(task.metadata)
                
                task_data.append(task_info)
            
            # Render the task group with AI-enhanced display
            TaskGroupComponent.render(
                window_title=group.window_title,
                duration_minutes=group.duration_minutes,
                tasks=task_data,  # Pass full task data including AI metadata
                category=group.category,
                timestamp=group.start_time,
                end_time=group.end_time,
                screenshot_path=screenshot_path,
                show_screenshot=show_screenshots,
                expanded=(i < 3),  # Expand first 3
                use_ai_display=use_ai_display  # Pass the toggle state
            )
            
            # Add a subtle divider between task groups
            if i < len(task_groups[:20]) - 1:
                st.divider()
            
    def run(self):
        """Main dashboard execution with debug capture and real-time updates."""
        # Start event processing for real-time updates
        if not self.event_processor.running:
            self.event_processor.start_processing()
        
        # Check for real-time updates
        if self.check_for_updates():
            self.trigger_refresh("New data available")
        
        # Capture dashboard startup
        capture_event("dashboard_startup")
        
        # Check database connection
        if not self.ensure_connection():
            capture_event("database_connection_failed")
            return
        
        capture_event("database_connected")
            
        # Header with real-time status using DashboardHeader component
        realtime_mode = "static"
        processor_stats = None
        
        if st.session_state.get('realtime_enabled', False):
            processor_stats = self.event_processor.get_statistics()
            realtime_mode = "live" if processor_stats.get('running') else "paused"
        
        DashboardHeader.render(
            title="Task Board",
            subtitle="Track and visualize your daily tasks and activities",
            icon="📋",
            right_column_content={
                'component': RealtimeStatusComponent,
                'params': {
                    'mode': realtime_mode,
                    'event_count': processor_stats.get('events_processed') if processor_stats else None,
                    'last_update': st.session_state.get('last_update_time'),
                    'processor_stats': processor_stats,
                    'config': {"compact_mode": False, "show_connection_details": False}
                }
            }
        )
        
        # Enhanced search section
        with st.expander("🔍 Enhanced Search", expanded=False):
            search_result = EnhancedSearch.render(
                key="main_search",
                placeholder="Search tasks, activities, or content...",
                show_search_type=True,
                default_type="Hybrid"
            )
            
            if search_result["has_query"]:
                st.session_state.search_active = True
                st.session_state.search_query = search_result["query"]
                st.session_state.search_type = search_result["type"]
            else:
                st.session_state.search_active = False
        
        # Render sidebar and get filters
        time_filter, categories, show_screenshots, min_duration = self.render_sidebar()
        
        # Get time range
        start_date, end_date = TimeFilterComponent.get_time_range(time_filter)
        
        # Initialize repositories
        task_repo = TaskRepository(self.db_manager)
        metrics_repo = MetricsRepository(self.db_manager)
        
        # Handle CSV export if requested
        if st.session_state.get('export_csv', False):
            with st.spinner("Generating CSV export..."):
                # Get task groups for export
                export_groups = task_repo.get_task_groups(
                    start_date=start_date,
                    end_date=end_date,
                    min_duration_minutes=min_duration
                )
                
                # Filter by categories if specified
                if categories:
                    export_groups = [
                        group for group in export_groups 
                        if group.category in categories
                    ]
                
                if export_groups:
                    # Use ExportComponent for CSV generation
                    csv_content = ExportComponent.format_task_export(
                        export_groups, start_date, end_date
                    )
                    
                    # Create download button using ExportComponent
                    filename = f"autotasktracker_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                    ExportComponent.render_csv_button(
                        data=csv_content,
                        filename=filename,
                        label="📥 Download CSV",
                        help_text=f"Export contains {len(export_groups)} task groups from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                    )
                    st.success(f"✅ CSV export ready! {len(export_groups)} task groups included.")
                else:
                    st.warning("No task groups found for the selected time period and filters.")
            
            # Reset export flag
            st.session_state.export_csv = False
        
        # Render metrics
        self.render_metrics(metrics_repo, start_date, end_date)
        
        st.divider()
        
        # Render task groups
        capture_event("before_task_groups_render")
        self.render_task_groups(
            task_repo,
            start_date,
            end_date,
            categories,
            show_screenshots,
            min_duration
        )
    
    def _handle_realtime_update(self, event: PensieveEvent):
        """Handle real-time updates from EventProcessor."""
        if st.session_state.get('realtime_enabled', False):
            # Invalidate relevant caches
            self.cache_manager.invalidate_pattern('fetch_tasks_*')
            self.cache_manager.invalidate_pattern('task_groups_*')
            
            # Update last update time
            st.session_state.last_update_time = datetime.now()
            
            # Force Streamlit rerun if in active session
            try:
                st.rerun()
            except Exception:
                # Graceful handling if rerun fails
                logger.debug("Could not trigger Streamlit rerun from event handler")
    
    def _check_auto_refresh(self):
        """Check if dashboard should auto-refresh."""
        if not st.session_state.get('realtime_enabled', False):
            return False
        
        current_time = time.time()
        if current_time - self.last_refresh > self.refresh_interval:
            self.last_refresh = current_time
            st.session_state.last_update_time = datetime.now()
            
            # Clear caches to get fresh data
            self.cache_manager.invalidate_pattern('fetch_tasks_*')
            
            return True
        return False
        capture_event("after_task_groups_render")
        
        # Final dashboard loaded capture
        capture_event("dashboard_loaded")
        
        # Raw data view (debug)
        if st.session_state.show_raw_data:
            with st.expander("🔍 Raw Data"):
                tasks = task_repo.get_tasks_for_period(start_date, end_date)
                if tasks:
                    import pandas as pd
                    df = pd.DataFrame([
                        {
                            'ID': t.id,
                            'Window': t.window_title,
                            'Category': t.category,
                            'Timestamp': t.timestamp,
                            'Duration': f"{t.duration_minutes:.1f} min"
                        }
                        for t in tasks[:100]
                    ])
                    st.dataframe(df, use_container_width=True)
                    

def main():
    """Run the refactored task board."""
    dashboard = TaskBoardDashboard()
    dashboard.run()
    

if __name__ == "__main__":
    main()