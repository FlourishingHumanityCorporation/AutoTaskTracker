"""
Refactored Time Tracker Dashboard using component architecture
Provides detailed time tracking with intelligent task recognition
"""

import streamlit as st
from datetime import datetime, date
from collections import defaultdict
import logging

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components import (
    TimeFilterComponent,
    CategoryPieChart,
    NoDataMessage,
    TimeTrackerTimeline,
    TimeTrackerMetrics,
    TimeTrackerTaskList,
    DashboardHeader
)
from autotasktracker.dashboards.components.common_sidebar import CommonSidebar, SidebarSection
from autotasktracker.dashboards.data.repositories import TaskRepository
from autotasktracker.core import TimeTracker
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class TimeTrackerDashboard(BaseDashboard):
    """Refactored time tracking dashboard with enhanced session analysis."""
    
    def __init__(self):
        super().__init__(
            title="Task Time Tracker",
            icon="⏱️",
            port=get_config().TIMETRACKER_PORT
        )
        
    def render_sidebar(self):
        """Render sidebar controls using common sidebar component."""
        # Define custom sections for time tracker specific options
        def render_date_selection():
            selected_date = st.date_input("Select Date", value=date.today())
            # Convert to datetime for queries
            start_datetime = datetime.combine(selected_date, datetime.min.time())
            end_datetime = datetime.combine(selected_date, datetime.max.time())
            return {
                'selected_date': selected_date,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime
            }
        
        def render_display_options():
            show_distribution = st.checkbox("Time Distribution", value=True)
            show_timeline = st.checkbox("Task Timeline", value=True)
            show_detailed_list = st.checkbox("Detailed Task List", value=True)
            max_timeline_tasks = st.slider(
                "Max Timeline Tasks",
                min_value=10,
                max_value=50,
                value=20,
                help="Maximum number of tasks to show in timeline"
            )
            return {
                'show_distribution': show_distribution,
                'show_timeline': show_timeline,
                'show_detailed_list': show_detailed_list,
                'max_timeline_tasks': max_timeline_tasks
            }
        
        def render_session_analysis():
            min_session_minutes = st.slider(
                "Min Session Duration (min)",
                min_value=0.5,
                max_value=10.0,
                value=0.5,
                step=0.5,
                help="Minimum duration to count as a session"
            )
            return {'min_session_minutes': min_session_minutes}
        
        # Custom sections for time tracker
        custom_sections = [
            SidebarSection("Date Selection", render_date_selection),
            SidebarSection("Display Options", render_display_options),
            SidebarSection("Session Analysis", render_session_analysis)
        ]
        
        # Render common sidebar with custom sections
        results = CommonSidebar.render(
            header_title="Time Tracker Settings",
            header_icon="⏱️",
            db_manager=self.db_manager,
            enable_time_filter=False,  # We use custom date selection
            enable_category_filter=False,  # Not used in time tracker
            custom_sections=custom_sections
        )
        
        # Combine all results for backwards compatibility
        final_results = {}
        for section_key, section_data in results.items():
            if isinstance(section_data, dict):
                final_results.update(section_data)
        
        return final_results
            
    def prepare_timeline_data(self, sessions, max_tasks):
        """Prepare data for timeline visualization."""
        tasks_data = defaultdict(list)
        category_times = defaultdict(float)
        
        for session in sessions:
            task_name = session.task_name
            category = session.category
            
            # Add to tasks_data for timeline chart
            tasks_data[task_name].append({
                'start': session.start_time,
                'end': session.end_time,
                'duration': session.duration_minutes,
                'active_duration': session.active_time_minutes,
                'category': category,
                'confidence': session.confidence,
                'screenshot_count': session.screenshot_count,
                'color': 'lightblue'  # Could be customized by category
            })
            
            category_times[category] += session.duration_minutes
            
        # Sort tasks by total time spent and limit
        sorted_tasks = sorted(
            [(task, sum(p['duration'] for p in periods)) for task, periods in tasks_data.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top tasks only
        top_tasks = dict(sorted_tasks[:max_tasks])
        timeline_data = {task: tasks_data[task] for task in top_tasks.keys()}
        
        return timeline_data, category_times
        
    def render_time_distribution(self, category_times, total_tracked_time):
        """Render time distribution section."""
        st.header("📊 Time Distribution")
        
        if not category_times:
            NoDataMessage.render("No category data available")
            return
            
        col1, col2 = st.columns([2, 1])
        
        with col1:
            CategoryPieChart.render(
                category_times,
                title="Time Distribution by Category",
                height=400
            )
            
        with col2:
            st.subheader("Category Breakdown")
            for category, time_spent in sorted(category_times.items(), key=lambda x: x[1], reverse=True):
                percentage = (time_spent / total_tracked_time) * 100
                st.write(f"{category}: {time_spent:.1f} min ({percentage:.1f}%)")
                st.progress(percentage / 100)
                
    def run(self):
        """Main dashboard execution."""
        # Check database connection
        if not self.ensure_connection():
            return
            
        # Header using DashboardHeader component
        DashboardHeader.render_simple(
            title="Task Time Tracker",
            subtitle="Detailed time tracking for all your activities with intelligent task recognition",
            icon="⏱️"
        )
        
        # Render sidebar and get settings
        settings = self.render_sidebar()
        
        # Initialize repository
        task_repo = TaskRepository(self.db_manager)
        
        # Fetch data
        with st.spinner("Loading time tracking data..."):
            df = task_repo.get_raw_data(
                start_date=settings['start_datetime'],
                end_date=settings['end_datetime']
            )
        
        if df.empty:
            NoDataMessage.render(
                "No data found for the selected date.",
                suggestions=[
                    "Make sure Memos is running and capturing screenshots",
                    "Try selecting a different date",
                    "Check if Memos service is enabled"
                ]
            )
            return
            
        # Process data with enhanced time tracking
        with st.spinner("Analyzing time sessions..."):
            tracker = TimeTracker()
            sessions = tracker.track_sessions(df)
            daily_summary = tracker.get_daily_summary(sessions)
            task_groups = tracker.group_by_task(sessions)
            
        if not sessions:
            NoDataMessage.render(
                "No significant tasks detected for the selected date.",
                suggestions=[
                    f"Tasks need to run for at least {settings['min_session_minutes']} minutes to appear",
                    "Check if screenshots are being captured regularly",
                    "Try adjusting the minimum session duration"
                ]
            )
            return
            
        # Prepare data for visualizations
        timeline_data, category_times = self.prepare_timeline_data(
            sessions, 
            settings['max_timeline_tasks']
        )
        total_tracked_time = daily_summary['total_time_minutes']
        
        # Display enhanced summary metrics
        TimeTrackerMetrics.render(daily_summary, category_times)
        
        # Time distribution
        if settings['show_distribution']:
            self.render_time_distribution(category_times, total_tracked_time)
            
        # Task timeline
        if settings['show_timeline'] and timeline_data:
            st.header("📅 Task Timeline")
            TimeTrackerTimeline.render(
                timeline_data,
                title=f"Top {len(timeline_data)} Tasks by Time Spent"
            )
            
        # Detailed task list
        if settings['show_detailed_list']:
            st.header("📋 Detailed Task List")
            TimeTrackerTaskList.render(task_groups, settings['selected_date'])
            

def main():
    """Run the refactored time tracker dashboard."""
    dashboard = TimeTrackerDashboard()
    dashboard.run()
    

if __name__ == "__main__":
    main()