"""Refactored Task Board Dashboard using new architecture.

This is an example of how to refactor existing dashboards to use:
- Base dashboard class
- Reusable components
- Data repositories
- Cleaner separation of concerns
"""

import streamlit as st
from datetime import datetime
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.dashboards.base import BaseDashboard
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
        """Initialize dashboard-specific session state."""
        super().init_session_state()
        
        # Task board specific state
        if 'group_by' not in st.session_state:
            st.session_state.group_by = 'window'
        if 'show_screenshots' not in st.session_state:
            st.session_state.show_screenshots = True
        if 'min_duration' not in st.session_state:
            st.session_state.min_duration = 1
            
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            st.header("⚙️ Task Board Settings")
            
            # Time filter
            time_filter = TimeFilterComponent.render()
            
            # Category filter
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
        
        # Filter by categories if specified
        if categories and "All Categories" not in categories:
            task_groups = [
                group for group in task_groups 
                if group.category in categories
            ]
            
        if not task_groups:
            NoDataMessage.render(
                "No tasks found for the selected filters",
                suggestions=[
                    "Try expanding the time range",
                    "Check if Memos is capturing screenshots",
                    "Adjust the minimum duration filter"
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
                screenshot_path=screenshot_path,
                show_screenshot=show_screenshots,
                expanded=(i < 3)  # Expand first 3
            )
            
    def run(self):
        """Main dashboard execution."""
        # Check database connection
        if not self.ensure_connection():
            return
            
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
        
        # Render metrics
        self.render_metrics(metrics_repo, start_date, end_date)
        
        st.divider()
        
        # Render task groups
        self.render_task_groups(
            task_repo,
            start_date,
            end_date,
            categories,
            show_screenshots,
            min_duration
        )
        
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