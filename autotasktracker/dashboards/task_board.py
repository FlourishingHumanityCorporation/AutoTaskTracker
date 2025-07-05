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

# Removed sys.path hack - using proper package imports

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.utils.debug_capture import get_debug_capture, capture_event
from autotasktracker.dashboards.components import (
    TimeFilterComponent, 
    CategoryFilterComponent,
    MetricsRow,
    TaskGroup as TaskGroupComponent,
    NoDataMessage
)
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository

logger = logging.getLogger(__name__)


class TaskBoardDashboard(BaseDashboard):
    """Refactored Task Board dashboard."""
    
    def __init__(self):
        super().__init__(
            title="Task Board - AutoTaskTracker",
            icon="📋",
            port=8502
        )
        
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
            
        # Initialize smart time filter if not set
        if 'time_filter' not in st.session_state:
            from .components.filters import TimeFilterComponent
            st.session_state.time_filter = TimeFilterComponent.get_smart_default(self.db_manager)
            
        # Initialize category filter to empty (all categories) if not set
        if 'category_filter' not in st.session_state:
            st.session_state.category_filter = []  # Empty = all categories
            
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
            
            # Auto refresh
            st.subheader("Auto Refresh")
            auto_refresh = st.checkbox("Enable (5 min)", value=True)
            if auto_refresh:
                self.add_auto_refresh(300)
            
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
                from .components.filters import TimeFilterComponent
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
        
        # Display task groups
        st.subheader(f"📋 Tasks ({len(task_groups)})")
        
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
        """Main dashboard execution with debug capture."""
        # Capture dashboard startup
        capture_event("dashboard_startup")
        
        # Check database connection
        if not self.ensure_connection():
            capture_event("database_connection_failed")
            return
        
        capture_event("database_connected")
            
        # Header
        st.title("📋 Task Board")
        st.markdown("Track and visualize your daily tasks and activities")
        
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