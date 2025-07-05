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
import threading

# Real-time integration imports - lazy loaded for performance
# These will be imported only when real-time features are enabled
from autotasktracker.core import DatabaseManager

# Removed sys.path hack - using proper package imports

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.utils.debug_capture import get_debug_capture, capture_event
from autotasktracker.dashboards.components import (
    TimeFilterComponent, 
    CategoryFilterComponent,
    MetricsRow,
    TaskGroup as TaskGroupComponent,
    NoDataMessage,
    EnhancedSearch
)
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
        
        # Real-time integration setup - lazy loaded for performance
        self._event_processor = None
        self._cache_manager = None
        self._api_client = None
        self._webhook_server = None
        self._advanced_search = None
        
        self.last_refresh = time.time()
        self.refresh_interval = 30  # seconds
        self.use_api = False
        
        # Real-time features are initialized only when needed
        self._realtime_initialized = False
        
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
            from autotasktracker.dashboards.components.filters import TimeFilterComponent
            st.session_state.time_filter = TimeFilterComponent.get_smart_default(self.db_manager)
            
        # Initialize category filter to empty (all categories) if not set
        if 'category_filter' not in st.session_state:
            st.session_state.category_filter = []  # Empty = all categories
    
    @property
    def event_processor(self):
        """Lazy load event processor only when real-time features are needed."""
        if self._event_processor is None:
            from autotasktracker.pensieve.event_processor import get_event_processor
            self._event_processor = get_event_processor()
            # Register handlers when first loaded
            self._event_processor.register_event_handler('entity_added', self._handle_realtime_update)
            self._event_processor.register_event_handler('entity_processed', self._handle_realtime_update)
        return self._event_processor
    
    @property
    def cache_manager(self):
        """Lazy load cache manager."""
        if self._cache_manager is None:
            from autotasktracker.pensieve.cache_manager import get_cache_manager
            self._cache_manager = get_cache_manager()
        return self._cache_manager
    
    @property
    def api_client(self):
        """Lazy load API client."""
        if self._api_client is None:
            try:
                from autotasktracker.pensieve.api_client import PensieveAPIClient
                self._api_client = PensieveAPIClient()
                self.use_api = True
                logger.info("Pensieve API client initialized for real-time features")
            except Exception as e:
                logger.debug(f"Pensieve API client initialization failed: {e}")
                self.use_api = False
        return self._api_client
    
    @property
    def webhook_server(self):
        """Lazy load webhook server."""
        if self._webhook_server is None:
            try:
                from autotasktracker.pensieve.webhook_server import get_webhook_server
                self._webhook_server = get_webhook_server()
                # Register handlers when first loaded
                self._webhook_server.register_handler('entity_processed', self._handle_webhook_update)
                self._webhook_server.register_handler('entity_created', self._handle_webhook_update)
                self._webhook_server.register_handler('metadata_updated', self._handle_webhook_update)
                logger.info("Webhook handlers registered for task board dashboard")
            except Exception as e:
                logger.debug(f"Webhook server initialization failed: {e}")
        return self._webhook_server
    
    @property
    def advanced_search(self):
        """Lazy load advanced search."""
        if self._advanced_search is None:
            try:
                from autotasktracker.pensieve.advanced_search import PensieveEnhancedSearch
                self._advanced_search = PensieveEnhancedSearch()
                logger.info("Advanced search initialized")
            except Exception as e:
                logger.debug(f"Advanced search initialization failed: {e}")
        return self._advanced_search
            
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            st.header("⚙️ Task Board Settings")
            
            # Time filter with smart defaults
            time_filter = TimeFilterComponent.render(db_manager=self.db_manager)
            
            # Smart default button
            if st.button("🎯 Smart Default", help="Reset to optimal time period based on your data"):
                smart_default = TimeFilterComponent.get_smart_default(self.db_manager)
                st.session_state.time_filter = smart_default
                st.rerun()
            
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
            
            # Export functionality
            st.subheader("📥 Export Data")
            if st.button("Export to CSV", help="Export current task data as CSV for reporting"):
                # This will be handled in the main run method
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
                
                # Webhook status
                if self.webhook_server:
                    webhook_stats = self.webhook_server.stats
                    if webhook_stats.requests_received > 0:
                        st.sidebar.success(f"🔗 Webhooks active: {webhook_stats.requests_processed} processed")
                    else:
                        st.sidebar.info("🔗 Webhook server ready")
                
                # API status  
                if self.use_api and self.api_client:
                    try:
                        health = self.api_client.get_health()
                        if health:
                            st.sidebar.success("🌐 API connected")
                        else:
                            st.sidebar.warning("🌐 API limited")
                    except Exception as e:
                        logger.debug(f"API health check failed: {e}")
                        st.sidebar.warning("🌐 API fallback mode")
                
                # Performance metrics
                if st.sidebar.button("📊 Performance Stats"):
                    task_repo = TaskRepository(self.db_manager)
                    perf_stats = task_repo.get_performance_stats()
                    
                    if perf_stats['api_requests'] > 0 or perf_stats['database_queries'] > 0:
                        st.sidebar.markdown("**API vs Database Usage:**")
                        col1, col2 = st.sidebar.columns(2)
                        with col1:
                            st.metric("API %", f"{perf_stats['api_usage_percentage']:.1f}%")
                        with col2:
                            st.metric("DB %", f"{perf_stats['database_usage_percentage']:.1f}%")
                        
                        st.sidebar.metric("Cache Hit Rate", f"{perf_stats['cache_hit_rate']:.1f}%")
                    else:
                        st.sidebar.info("No performance data yet")
            
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
            
    def export_task_data_to_csv(
        self, 
        task_groups: list,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Export task data to CSV format for professional reporting.
        
        Returns:
            CSV content as string
        """
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row matching user story example
        writer.writerow([
            'Date',
            'Task Group', 
            'Duration',
            'Start Time',
            'End Time',
            'Category',
            'Description',
            'Activities',
            'Confidence'
        ])
        
        for group in task_groups:
            # Format data for CSV
            date = group.start_time.strftime('%Y-%m-%d')
            task_name = group.window_title
            duration = f"{group.duration_minutes:.0f}min"
            start_time = group.start_time.strftime('%H:%M')
            end_time = group.end_time.strftime('%H:%M')
            category = group.category
            
            # Create description from task activities
            activities = [task.title for task in group.tasks[:3]]  # First 3 activities
            description = '; '.join(activities) if activities else task_name
            activity_count = len(group.tasks)
            
            # Confidence indicator
            confidence = 'High' if group.duration_minutes >= 2 else 'Medium' if group.duration_minutes >= 1 else 'Low'
            
            writer.writerow([
                date,
                task_name,
                duration,
                start_time,
                end_time,
                category,
                description,
                activity_count,
                confidence
            ])
        
        return output.getvalue()

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
        # Check if we have advanced search results to use
        search_results = st.session_state.get('advanced_search_results')
        search_active = st.session_state.get('search_active', False)
        
        if search_active and search_results:
            # Convert search results to task groups
            task_groups = self._convert_search_results_to_task_groups(
                search_results, task_repo, start_date, end_date, min_duration
            )
        else:
            # Get grouped tasks normally
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
                from autotasktracker.dashboards.components.filters import TimeFilterComponent
                smart_default = TimeFilterComponent.get_smart_default(self.db_manager)
                
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
        
        # Display task groups with filtering info
        total_count = len(task_groups)
        display_count = min(total_count, 20)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"📋 Tasks ({total_count} found)")
        with col2:
            if total_count > 20:
                st.caption(f"Showing top {display_count} of {total_count}")
            elif total_count > 0:
                st.caption(f"Showing all {total_count} tasks")
        
        # Add filter summary if filters are active
        active_filters = []
        if categories:
            active_filters.append(f"Categories: {', '.join(categories)}")
        if min_duration > 1:
            active_filters.append(f"Min duration: {min_duration} min")
        
        if active_filters:
            with st.expander("🔍 Active Filters", expanded=False):
                for filter_info in active_filters:
                    st.info(filter_info)
                if st.button("Clear All Filters"):
                    st.session_state.category_filter = []
                    st.session_state.min_duration = 1
                    st.rerun()
        
        for i, group in enumerate(task_groups[:20]):  # Limit to top 20
            # Extract first task for screenshot
            screenshot_path = group.tasks[0].screenshot_path if group.tasks else None
            
            # Get task descriptions
            task_descriptions = []
            for task in group.tasks[:3]:  # Show first 3 tasks
                if task.metadata and 'description' in task.metadata:
                    task_descriptions.append(task.metadata['description'])
                    
            TaskGroupComponent.render(
                window_title=group.window_title,
                duration_minutes=group.duration_minutes,
                tasks=task_descriptions,
                category=group.category,
                timestamp=group.start_time,
                end_time=group.end_time,
                screenshot_path=screenshot_path,
                show_screenshot=show_screenshots,
                expanded=(i < 3)  # Expand first 3
            )
            
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
            
        # Header with real-time status
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title("📋 Task Board")
            st.markdown("Track and visualize your daily tasks and activities")
        
        with col2:
            # Real-time status indicator
            if st.session_state.get('realtime_enabled', False):
                processor_stats = self.event_processor.get_statistics()
                if processor_stats['running']:
                    st.success("🔄 Live")
                    st.caption(f"Events: {processor_stats['events_processed']}")
                else:
                    st.warning("⏸️ Paused")
            else:
                st.info("📋 Static")
        
        # Enhanced search section with Pensieve integration - more prominent
        st.markdown("### 🔍 Search & Filter")
        search_col1, search_col2 = st.columns([4, 1])
        
        with search_col1:
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
                
                # Enhanced search using Pensieve advanced search if available
                if self.advanced_search:
                    with st.spinner("🔍 Searching with AI..."):
                        try:
                            search_query = SearchQuery(
                                query=search_result["query"],
                                search_type=search_result["type"].lower(),
                                time_range=(start_date, end_date),
                                categories=categories,
                                limit=20,
                                semantic_threshold=0.7
                            )
                            
                            # Execute async search in sync context
                            import asyncio
                            
                            # Handle async search in Streamlit context
                            try:
                                search_results = self._handle_async_search(search_query, search_result)
                                
                                # Store search results in session state for use by data repositories
                                st.session_state.advanced_search_results = search_results
                                
                                # Display search status
                                if search_results:
                                    st.success(f"🎯 Found {len(search_results)} results for '{search_result['query']}' ({search_result['type']})")
                                    
                                    # Show top result context as preview
                                    if search_results[0].context_snippet:
                                        with st.expander("Preview top result"):
                                            st.text(search_results[0].context_snippet)
                                else:
                                    st.info(f"🔍 No results found for '{search_result['query']}' - showing all tasks")
                                    
                            except Exception as e:
                                logger.warning(f"Async search execution failed: {e}")
                                st.session_state.advanced_search_results = []
                                st.info(f"🔍 Search configured for '{search_result['query']}' - using standard search")
                            
                            # Show search stats if available
                            if hasattr(self.advanced_search, 'stats'):
                                stats = self.advanced_search.stats
                                if stats['total_searches'] > 0:
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Total Searches", stats['total_searches'])
                                    with col2:
                                        st.metric("Cache Hit Rate", f"{(stats['cache_hits']/stats['total_searches']*100):.1f}%")
                                    with col3:
                                        st.metric("Avg Response", f"{stats['avg_response_time']:.2f}s")
                        except Exception as e:
                            logger.warning(f"Advanced search failed: {e}")
                            st.warning("🔍 Advanced search unavailable, using basic search")
            else:
                st.session_state.search_active = False
        
        with search_col2:
            # Add search help/info
            if st.button("ℹ️ Search Help", help="Learn about search options"):
                with st.expander("Search Help", expanded=True):
                    st.markdown("""
                    **Search Types:**
                    - **Text**: Direct text matching
                    - **Semantic**: AI-powered meaning search  
                    - **Hybrid**: Combines both approaches
                    
                    **Tips:**
                    - Use specific keywords for better results
                    - Try different search types for different needs
                    """)
        
        # Render sidebar and get filters first
        time_filter, categories, show_screenshots, min_duration = self.render_sidebar()
        
        # Get time range
        start_date, end_date = TimeFilterComponent.get_time_range(time_filter)
        
        st.divider()
        
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
                    csv_content = self.export_task_data_to_csv(export_groups, start_date, end_date)
                    
                    # Create download button
                    filename = f"autotasktracker_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_content,
                        file_name=filename,
                        mime="text/csv",
                        help=f"Export contains {len(export_groups)} task groups from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
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
    
    def _handle_realtime_update(self, event):
        """Handle real-time updates from EventProcessor with API integration."""
        if st.session_state.get('realtime_enabled', False):
            # Try API-first real-time update if available
            if self.use_api and self.api_client:
                try:
                    self._handle_api_realtime_update(event)
                except Exception as e:
                    logger.debug(f"API real-time update failed, using fallback: {e}")
                    self._handle_fallback_realtime_update(event)
            else:
                self._handle_fallback_realtime_update(event)
    
    def _handle_api_realtime_update(self, event):
        """Handle real-time updates using Pensieve API."""
        # Check if new data is available via API
        try:
            # Get latest entity count from API
            health_status = self.api_client.get_health()
            if health_status and 'entity_count' in health_status:
                current_count = health_status['entity_count']
                last_count = st.session_state.get('last_entity_count', 0)
                
                if current_count > last_count:
                    # New entities available - invalidate caches
                    self._invalidate_caches()
                    st.session_state.last_entity_count = current_count
                    st.session_state.last_update_time = datetime.now()
                    
                    # Show notification of new data
                    if hasattr(st, 'toast'):
                        st.toast(f"📸 New screenshot processed ({current_count - last_count} new)", icon="🔄")
                    
                    # Force refresh
                    st.rerun()
                    
        except Exception as e:
            logger.warning(f"API real-time update error: {e}")
            raise Exception(f"API update failed: {e}")
    
    def _handle_fallback_realtime_update(self, event):
        """Fallback real-time update using event processor."""
        # Invalidate relevant caches
        self._invalidate_caches()
        
        # Update last update time
        st.session_state.last_update_time = datetime.now()
        
        # Force Streamlit rerun if in active session
        try:
            st.rerun()
        except Exception:
            # Graceful handling if rerun fails
            logger.debug("Could not trigger Streamlit rerun from event handler")
    
    def _invalidate_caches(self):
        """Invalidate relevant caches for real-time updates."""
        self.cache_manager.invalidate_pattern('fetch_tasks_*')
        self.cache_manager.invalidate_pattern('task_groups_*')
        self.cache_manager.invalidate_pattern('query_*')  # Also invalidate repository query cache
    
    def _handle_webhook_update(self, event):
        """Handle webhook updates from Pensieve for enhanced real-time features."""
        if not st.session_state.get('realtime_enabled', False):
            return
            
        logger.info(f"Webhook update received: {event.event_type} for entity {event.entity_id}")
        
        # Enhanced webhook processing with entity-specific updates
        if event.event_type == 'entity_processed':
            # New screenshot has been processed with OCR/VLM
            self._handle_entity_processed_webhook(event)
        elif event.event_type == 'entity_created':
            # New screenshot captured
            self._handle_entity_created_webhook(event)
        elif event.event_type == 'metadata_updated':
            # Task extraction or other metadata updated
            self._handle_metadata_updated_webhook(event)
        
        # General cache invalidation and UI refresh
        self._invalidate_caches()
        st.session_state.last_update_time = datetime.now()
        
        # Try to trigger Streamlit rerun for immediate update
        try:
            st.rerun()
        except Exception:
            logger.debug("Could not trigger Streamlit rerun from webhook handler")
    
    def _handle_entity_processed_webhook(self, event):
        """Handle entity processed webhook with enhanced notifications."""
        # Show detailed notification for processed entities
        entity_id = event.entity_id
        
        # Get entity details if possible
        try:
            if self.api_client:
                entity_details = self.api_client.get_entity(entity_id)
                if entity_details:
                    if hasattr(st, 'toast'):
                        st.toast(f"📸 Screenshot processed: {entity_details.get('filepath', f'Entity {entity_id}')}", icon="✅")
                    return
        except Exception as e:
            logger.debug(f"Could not show detailed toast notification: {e}")
        
        # Fallback notification
        if hasattr(st, 'toast'):
            st.toast(f"📸 New screenshot processed (ID: {entity_id})", icon="✅")
    
    def _handle_entity_created_webhook(self, event):
        """Handle entity created webhook."""
        if hasattr(st, 'toast'):
            st.toast(f"📷 New screenshot captured", icon="📸")
    
    def _handle_metadata_updated_webhook(self, event):
        """Handle metadata updated webhook."""
        # Check if this was task extraction
        if 'tasks' in event.data or 'extracted_tasks' in event.data:
            if hasattr(st, 'toast'):
                st.toast(f"🎯 Tasks extracted for screenshot {event.entity_id}", icon="🔍")
    
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
    
    def _handle_async_search(self, search_query, search_result):
        """Handle async search in Streamlit context with proper error handling."""
        import asyncio
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        search_results = []
        
        try:
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # If we get here, there's already a loop running
                st.info(f"🎯 Advanced search configured: '{search_result['query']}' ({search_result['type']})")
                st.warning("⚠️ Async search requires environment setup - using fallback search")
                return []
            except RuntimeError:
                # No loop running, safe to create one
                try:
                    # Use thread pool to run async code
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self._run_async_search, search_query)
                        search_results = future.result(timeout=10)  # 10 second timeout
                    
                    return search_results
                except Exception as e:
                    logger.warning(f"Threaded async search failed: {e}")
                    st.info(f"🔍 Search configured for '{search_result['query']}' - using standard search")
                    return []
                    
        except Exception as e:
            logger.warning(f"Async search handling failed: {e}")
            st.info(f"🔍 Search fallback for '{search_result['query']}'")
            return []
    
    def _run_async_search(self, search_query):
        """Run async search in a new event loop."""
        import asyncio
        
        async def _execute_search():
            return await self.advanced_search.search(search_query)
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_execute_search())
        finally:
            loop.close()

    def _convert_search_results_to_task_groups(self, search_results, task_repo, start_date, end_date, min_duration):
        """Convert advanced search results to task groups format."""
        from autotasktracker.dashboards.data.repositories import TaskGroup
        
        task_groups = []
        
        for result in search_results:
            try:
                # Extract AI tasks from the search result
                ai_tasks = result.ai_extracted_tasks
                
                if ai_tasks:
                    for task_data in ai_tasks:
                        # Create a task group from the search result
                        task_group = TaskGroup(
                            id=f"search_{result.entity.id}_{hash(task_data.get('task', ''))}",
                            window_title=result.entity.metadata.get('active_window', 'Unknown'),
                            category=result.category or 'Uncategorized',
                            main_task=task_data.get('task', 'Task extracted from search'),
                            total_duration_minutes=1.0,  # Default duration for search results
                            screenshot_count=1,
                            first_timestamp=result.entity.created_at,
                            last_timestamp=result.entity.created_at,
                            tasks=[],  # Individual tasks would need to be built from metadata
                            screenshots=[result.entity.filepath] if result.entity.filepath else []
                        )
                        
                        # Apply minimum duration filter
                        if task_group.total_duration_minutes >= min_duration:
                            task_groups.append(task_group)
                else:
                    # No AI tasks, create a basic group from OCR content
                    ocr_text = result.entity.metadata.get('ocr_result', '')
                    if ocr_text:
                        task_group = TaskGroup(
                            id=f"search_{result.entity.id}",
                            window_title=result.entity.metadata.get('active_window', 'Unknown'),
                            category=result.category or 'Uncategorized',
                            main_task=f"Content: {ocr_text[:100]}..." if len(ocr_text) > 100 else ocr_text,
                            total_duration_minutes=1.0,
                            screenshot_count=1,
                            first_timestamp=result.entity.created_at,
                            last_timestamp=result.entity.created_at,
                            tasks=[],
                            screenshots=[result.entity.filepath] if result.entity.filepath else []
                        )
                        
                        if task_group.total_duration_minutes >= min_duration:
                            task_groups.append(task_group)
                            
            except Exception as e:
                logger.warning(f"Failed to convert search result to task group: {e}")
                continue
        
        return task_groups


def main():
    """Run the refactored task board."""
    dashboard = TaskBoardDashboard()
    dashboard.run()
    

if __name__ == "__main__":
    main()