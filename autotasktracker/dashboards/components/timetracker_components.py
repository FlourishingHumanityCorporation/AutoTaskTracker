"""Time tracker specific components."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None

from .base_component import StatelessComponent


class TimeTrackerTimeline(StatelessComponent):
    """Timeline chart specifically for time tracker dashboard."""
    
    @staticmethod
    def render(
        time_data: Dict[str, List[Dict[str, Any]]],
        title: str = "Task Timeline",
        height_per_task: int = 50,
        min_height: int = 400
    ):
        """Render time tracker timeline chart.
        
        Args:
            time_data: Dict of task_name: list of periods
                      Each period has: start, end, duration, color
            title: Chart title
            height_per_task: Height per task row
            min_height: Minimum chart height
        """
        if not time_data:
            st.info("No timeline data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            st.info(f"📊 **{title}**\n\nInteractive charts require plotly installation")
            return
            
        fig = go.Figure()
        
        # Create a bar for each task
        for task, periods in time_data.items():
            for period in periods:
                fig.add_trace(go.Bar(
                    x=[period['duration']],
                    y=[task],
                    orientation='h',
                    name=task,
                    text=f"{period['duration']:.1f} min",
                    textposition='inside',
                    hovertemplate=(
                        f"<b>{task}</b><br>"
                        f"Start: {period['start'].strftime('%H:%M')}<br>"
                        f"End: {period['end'].strftime('%H:%M')}<br>"
                        f"Duration: {period['duration']:.1f} min<br>"
                        f"Active: {period.get('active_duration', period['duration']):.1f} min<br>"
                        f"Category: {period.get('category', 'Unknown')}<br>"
                        f"Confidence: {period.get('confidence', 1.0):.2f}"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                    marker_color=period.get('color', 'lightblue')
                ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Duration (minutes)",
            yaxis_title="Tasks",
            barmode='stack',
            height=max(min_height, len(time_data) * height_per_task),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)


class TimeTrackerMetrics(StatelessComponent):
    """Enhanced metrics display for time tracker."""
    
    @staticmethod
    def render(daily_summary: Dict[str, Any], category_times: Dict[str, float]):
        """Render time tracker metrics.
        
        Args:
            daily_summary: Summary from TimeTracker.get_daily_summary()
            category_times: Dict of category: total_minutes
        """
        # First row of metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_time = daily_summary['total_time_minutes']
            time_display = f"{total_time:.1f} min" if total_time < 120 else f"{total_time/60:.1f} hours"
            st.metric("Total Time", time_display)
        with col2:
            active_time = daily_summary['active_time_minutes']
            st.metric("Active Time", f"{active_time:.1f} min", 
                     delta=f"-{daily_summary['idle_percentage']:.1f}% idle")
        with col3:
            st.metric("Focus Score", f"{daily_summary['focus_score']}/100", 
                     help="Based on number of 30+ minute sessions")
        with col4:
            st.metric("Sessions", daily_summary['sessions_count'], 
                     delta=f"{daily_summary['average_session_minutes']:.1f} min avg")
        
        # Second row of metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Unique Tasks", daily_summary['unique_tasks'])
        with col2:
            st.metric("Longest Session", f"{daily_summary['longest_session_minutes']:.1f} min")
        with col3:
            high_conf = daily_summary['high_confidence_sessions']
            total_sessions = daily_summary['sessions_count']
            conf_pct = (high_conf / total_sessions * 100) if total_sessions > 0 else 0
            st.metric("High Confidence", f"{high_conf}/{total_sessions}", 
                     delta=f"{conf_pct:.0f}%")
        with col4:
            most_used = max(category_times.items(), key=lambda x: x[1])[0] if category_times else "N/A"
            st.metric("Top Category", most_used)


class TimeTrackerTaskList(StatelessComponent):
    """Enhanced task list for time tracker."""
    
    @staticmethod
    def render(task_groups: Dict[str, Dict[str, Any]], selected_date: datetime):
        """Render time tracker task list.
        
        Args:
            task_groups: Task groups from TimeTracker.group_by_task()
            selected_date: Date for the export filename
        """
        if not task_groups:
            st.info("No tasks to display")
            return
            
        # Create enhanced task summary dataframe
        task_summaries = []
        for task_name, metrics in task_groups.items():
            confidence_icon = "🟢" if metrics['average_confidence'] > 0.8 else "🟡" if metrics['average_confidence'] > 0.5 else "🔴"
            
            task_summaries.append({
                'Task': task_name[:50] + '...' if len(task_name) > 50 else task_name,
                'Total Time (min)': f"{metrics['total_minutes']:.1f}",
                'Active Time (min)': f"{metrics['active_minutes']:.1f}",
                'Sessions': metrics['session_count'],
                'Confidence': f"{confidence_icon} {metrics['average_confidence']:.2f}",
                'Category': metrics["category"],
                'First Seen': metrics['first_seen'].strftime('%H:%M') if metrics['first_seen'] else 'N/A',
                'Last Seen': metrics['last_seen'].strftime('%H:%M') if metrics['last_seen'] else 'N/A'
            })
        
        task_df = pd.DataFrame(task_summaries)
        task_df = task_df.sort_values('Total Time (min)', ascending=False)
        
        # Display dataframe with enhanced formatting
        st.dataframe(
            task_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Time (min)": st.column_config.NumberColumn(
                    "Total Time (min)",
                    format="%.1f",
                    help="Total time including gaps"
                ),
                "Active Time (min)": st.column_config.NumberColumn(
                    "Active Time (min)", 
                    format="%.1f",
                    help="Time excluding long gaps"
                ),
                "Sessions": st.column_config.NumberColumn(
                    "Sessions",
                    format="%d",
                    help="Number of separate work sessions"
                ),
                "Confidence": st.column_config.TextColumn(
                    "Confidence",
                    help="🟢 High (0.8+), 🟡 Medium (0.5+), 🔴 Low (<0.5)"
                )
            }
        )
        
        # Add information about the enhanced metrics
        with st.expander("ℹ️ About Enhanced Time Tracking"):
            st.markdown("""
            **Enhanced Features:**
            - **Active Time**: Excludes idle gaps longer than 5 minutes
            - **Confidence Score**: Based on screenshot density and gap patterns
            - **Smart Session Detection**: Accounts for 4-second screenshot intervals
            - **Category-Aware Gaps**: Different gap thresholds for different activities
            
            **Confidence Levels:**
            - 🟢 **High (0.8+)**: Dense screenshots, few gaps - very accurate
            - 🟡 **Medium (0.5-0.8)**: Some gaps detected - mostly accurate  
            - 🔴 **Low (<0.5)**: Many gaps or sparse data - estimate only
            """)
        
        # Export button
        csv = task_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Task Report (CSV)",
            data=csv,
            file_name=f"time_tracking_{selected_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )