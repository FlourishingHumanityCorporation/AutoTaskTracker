"""Refactored Analytics Dashboard using new architecture."""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import logging

# Removed sys.path hack - using proper package imports

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components import (
    TimeFilterComponent, 
    CategoryFilterComponent,
    MetricsRow,
    CategoryPieChart,
    HourlyActivityChart,
    TaskDurationChart,
    TrendChart,
    NoDataMessage
)
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository
from autotasktracker.dashboards.cache import MetricsCache
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class AnalyticsDashboard(BaseDashboard):
    """Refactored Analytics dashboard with charts and insights."""
    
    def __init__(self):
        super().__init__(
            title="Analytics - AutoTaskTracker",
            icon="📊",
            port=get_config().ANALYTICS_PORT
        )
        
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            st.header("📊 Analytics Settings")
            
            # Time filter
            time_filter = TimeFilterComponent.render()
            
            # Category filter
            categories = CategoryFilterComponent.render(multiselect=True)
            
            # Display options
            st.subheader("Charts")
            show_categories = st.checkbox("Category Distribution", value=True)
            show_hourly = st.checkbox("Hourly Activity", value=True)
            show_durations = st.checkbox("Task Durations", value=True)
            show_trends = st.checkbox("Daily Trends", value=True)
            
            # Cache controls
            self.render_cache_controls()
            
            return time_filter, categories, {
                'show_categories': show_categories,
                'show_hourly': show_hourly,
                'show_durations': show_durations,
                'show_trends': show_trends
            }
            
    def render_overview_metrics(self, metrics_repo: MetricsRepository, start_date: datetime, end_date: datetime):
        """Render overview metrics section."""
        st.subheader("📈 Overview")
        
        # Get summary metrics
        summary = metrics_repo.get_metrics_summary(start_date, end_date)
        
        # Calculate additional metrics
        period_days = (end_date - start_date).days + 1
        avg_daily = summary['total_activities'] / max(summary['active_days'], 1)
        
        # Display metrics
        MetricsRow.render({
            "📊 Total Activities": summary['total_activities'],
            "📅 Active Days": f"{summary['active_days']}/{period_days}",
            "🪟 Unique Windows": summary['unique_windows'],
            "📱 Daily Average": f"{avg_daily:.0f}"
        })
        
    def render_category_analysis(self, start_date: datetime, end_date: datetime, chart_options: dict):
        """Render category analysis section."""
        if not chart_options['show_categories']:
            return
            
        st.subheader("🏷️ Category Analysis")
        
        # Get cached category breakdown
        category_data = MetricsCache.get_category_breakdown(
            self.db_manager,
            start_date,
            end_date
        )
        
        if category_data:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                CategoryPieChart.render(
                    category_data,
                    title="Activity Distribution by Category"
                )
                
            with col2:
                st.markdown("**Top Categories:**")
                sorted_cats = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
                for i, (category, count) in enumerate(sorted_cats[:5], 1):
                    percentage = (count / sum(category_data.values())) * 100
                    st.metric(
                        f"{i}. {category}",
                        f"{count} activities",
                        f"{percentage:.1f}%"
                    )
        else:
            NoDataMessage.render("No category data available")
            
    def render_time_analysis(self, start_date: datetime, end_date: datetime, chart_options: dict):
        """Render time-based analysis."""
        if not chart_options['show_hourly']:
            return
            
        st.subheader("🕒 Time Analysis")
        
        # Get cached hourly activity
        hourly_data = MetricsCache.get_hourly_activity(
            self.db_manager,
            start_date,
            end_date
        )
        
        if hourly_data:
            HourlyActivityChart.render(
                hourly_data,
                title="Activity by Hour of Day"
            )
            
            # Find peak hours
            peak_hours = sorted(hourly_data.items(), key=lambda x: x[1], reverse=True)[:3]
            
            st.markdown("**Peak Activity Hours:**")
            cols = st.columns(3)
            for i, (hour, count) in enumerate(peak_hours):
                with cols[i]:
                    time_str = f"{hour:02d}:00"
                    st.metric(f"#{i+1}", time_str, f"{count} activities")
        else:
            NoDataMessage.render("No hourly activity data available")
            
    def render_duration_analysis(self, task_repo: TaskRepository, start_date: datetime, end_date: datetime, chart_options: dict):
        """Render task duration analysis."""
        if not chart_options['show_durations']:
            return
            
        st.subheader("⏱️ Duration Analysis")
        
        # Get task groups for duration analysis
        task_groups = task_repo.get_task_groups(start_date, end_date, min_duration_minutes=1)
        
        if task_groups:
            durations = [group.duration_minutes for group in task_groups]
            
            TaskDurationChart.render(
                durations,
                title="Task Duration Distribution"
            )
            
            # Duration statistics
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average", f"{avg_duration:.1f} min")
            with col2:
                st.metric("Maximum", f"{max_duration:.1f} min")
            with col3:
                st.metric("Minimum", f"{min_duration:.1f} min")
            with col4:
                st.metric("Total Tasks", len(task_groups))
        else:
            NoDataMessage.render("No duration data available")
            
    def render_trend_analysis(self, metrics_repo: MetricsRepository, start_date: datetime, end_date: datetime, chart_options: dict):
        """Render trend analysis."""
        if not chart_options['show_trends']:
            return
            
        st.subheader("📈 Trend Analysis")
        
        # Generate daily metrics for the period
        current_date = start_date
        daily_data = []
        
        while current_date <= end_date:
            daily_metrics = metrics_repo.get_daily_metrics(current_date)
            if daily_metrics:
                daily_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'activities': daily_metrics.total_tasks,
                    'productive_time': daily_metrics.productive_time_minutes,
                    'unique_windows': daily_metrics.unique_windows
                })
            current_date += timedelta(days=1)
            
        if daily_data:
            df = pd.DataFrame(daily_data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Activity trend
            TrendChart.render(
                df,
                date_col='date',
                value_col='activities',
                title="Daily Activity Trend"
            )
            
            # Productivity trend
            if df['productive_time'].sum() > 0:
                TrendChart.render(
                    df,
                    date_col='date',
                    value_col='productive_time',
                    title="Daily Productive Time (minutes)"
                )
        else:
            NoDataMessage.render("No trend data available")
            
    def render_insights(self, task_repo: TaskRepository, start_date: datetime, end_date: datetime):
        """Render AI-powered insights."""
        st.subheader("🧠 Insights")
        
        # Get data for insights
        task_groups = task_repo.get_task_groups(start_date, end_date)
        
        if not task_groups:
            st.info("Not enough data for insights")
            return
            
        # Calculate insights
        total_duration = sum(group.duration_minutes for group in task_groups)
        avg_duration = total_duration / len(task_groups)
        
        # Most used app
        app_usage = {}
        for group in task_groups:
            app_usage[group.window_title] = app_usage.get(group.window_title, 0) + group.duration_minutes
        most_used_app = max(app_usage.items(), key=lambda x: x[1])
        
        # Category distribution
        category_time = {}
        for group in task_groups:
            category_time[group.category] = category_time.get(group.category, 0) + group.duration_minutes
        
        # Display insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 Key Insights:**")
            st.write(f"• Most used app: **{most_used_app[0]}** ({most_used_app[1]:.0f} min)")
            st.write(f"• Average task duration: **{avg_duration:.1f} minutes**")
            st.write(f"• Total focused time: **{total_duration/60:.1f} hours**")
            
        with col2:
            st.markdown("**🎯 Recommendations:**")
            if avg_duration < 5:
                st.write("• Consider longer focus sessions for better productivity")
            if len(task_groups) > 50:
                st.write("• You're very active! Consider tracking break time")
            if most_used_app[1] > total_duration * 0.4:
                st.write(f"• {most_used_app[0]} dominates your time - consider diversifying")
                
    def run(self):
        """Main dashboard execution."""
        # Check database connection
        if not self.ensure_connection():
            return
            
        # Header
        st.title("📊 Analytics Dashboard")
        st.markdown("Analyze your productivity patterns and get insights")
        
        # Render sidebar and get filters
        time_filter, categories, chart_options = self.render_sidebar()
        
        # Get time range
        start_date, end_date = TimeFilterComponent.get_time_range(time_filter)
        
        # Initialize repositories
        task_repo = TaskRepository(self.db_manager)
        metrics_repo = MetricsRepository(self.db_manager)
        
        # Render sections
        self.render_overview_metrics(metrics_repo, start_date, end_date)
        
        st.divider()
        
        # Charts section
        self.render_category_analysis(start_date, end_date, chart_options)
        self.render_time_analysis(start_date, end_date, chart_options)
        self.render_duration_analysis(task_repo, start_date, end_date, chart_options)
        self.render_trend_analysis(metrics_repo, start_date, end_date, chart_options)
        
        st.divider()
        
        # Insights section
        self.render_insights(task_repo, start_date, end_date)
        

def main():
    """Run the refactored analytics dashboard."""
    dashboard = AnalyticsDashboard()
    dashboard.run()
    

if __name__ == "__main__":
    main()