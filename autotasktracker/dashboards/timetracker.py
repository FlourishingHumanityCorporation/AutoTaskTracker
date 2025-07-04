"""
Time Tracker Dashboard for AutoTaskTracker
Provides detailed time tracking with intelligent task recognition
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
import plotly.graph_objects as go
from collections import defaultdict

from autotasktracker import (
    DatabaseManager,
    ActivityCategorizer,
    extract_task_summary,
    extract_window_title,
    Config,
    get_config
)
from autotasktracker.core.time_tracker import TimeTracker

# Initialize configuration
config = get_config()

# --- Helper Functions ---
def extract_task_info(active_window, ocr_text=None):
    """Extract task name and application from window data using advanced extraction."""
    if not active_window:
        return "Unknown Task", "Unknown App"
    
    # Get task using advanced extraction
    task = extract_task_summary(ocr_text, active_window)
    window_title = extract_window_title(active_window)
    
    # Extract app name from window title
    if window_title and ' - ' in window_title:
        parts = window_title.split(' - ')
        app = parts[-1].strip()
    else:
        app = "Unknown App"
    
    return task, app

def create_timeline_chart(time_data):
    """Create an interactive timeline chart."""
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
                hovertemplate=f"<b>{task}</b><br>Start: {period['start'].strftime('%H:%M')}<br>End: {period['end'].strftime('%H:%M')}<br>Duration: {period['duration']:.1f} min<extra></extra>",
                showlegend=False,
                marker_color=period.get('color', 'lightblue')
            ))
    
    fig.update_layout(
        title="Task Timeline",
        xaxis_title="Duration (minutes)",
        yaxis_title="Tasks",
        barmode='stack',
        height=max(400, len(time_data) * 50),
        showlegend=False
    )
    
    return fig

def create_time_distribution_pie(category_times):
    """Create a pie chart of time distribution by category."""
    categories = list(category_times.keys())
    values = list(category_times.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=values,
        hole=.3,
        textinfo='label+percent',
        textposition='auto'
    )])
    
    fig.update_layout(
        title="Time Distribution by Category",
        showlegend=True
    )
    
    return fig

# --- Main App ---
def main():
    st.set_page_config(
        layout="wide", 
        page_title="Task Time Tracker", 
        page_icon="⏱️"
    )

    st.title("⏱️ Task Time Tracker")
    st.write("Detailed time tracking for all your activities with intelligent task recognition")

    # Database connection
    db = DatabaseManager(config.DB_PATH)
    if not db.test_connection():
        st.error("❌ Cannot connect to database. Make sure Memos is running.")
        st.stop()

    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Select Date", value=date.today())
    
    # Convert to datetime for queries
    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = datetime.combine(selected_date, datetime.max.time())
    
    # Fetch data
    with st.spinner("Loading time tracking data..."):
        df = db.fetch_tasks(
            start_date=start_datetime,
            end_date=end_datetime,
            limit=5000
        )
    
    if df.empty:
        st.info("📭 No data found for the selected date.")
        st.write("Make sure Memos is running and capturing screenshots.")
        return
    
    # Process data with enhanced time tracking
    with st.spinner("Analyzing time sessions..."):
        tracker = TimeTracker()
        sessions = tracker.track_sessions(df)
        daily_summary = tracker.get_daily_summary(sessions)
        task_groups = tracker.group_by_task(sessions)
    
    if not sessions:
        st.info("📭 No significant tasks detected for the selected date.")
        st.write("Tasks need to run for at least 30 seconds to appear in time tracking.")
        return
    
    # Convert sessions to display format
    tasks_data = defaultdict(list)
    category_times = defaultdict(float)
    total_tracked_time = daily_summary['total_time_minutes']
    
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
            'color': 'lightblue'  # Default color
        })
        
        category_times[category] += session.duration_minutes
    
    # Display enhanced summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_time = daily_summary['total_time_minutes']
        time_display = f"{total_time:.1f} min" if total_time < 120 else f"{total_time/60:.1f} hours"
        st.metric("Total Time", time_display)
    with col2:
        active_time = daily_summary['active_time_minutes']
        st.metric("Active Time", f"{active_time:.1f} min", delta=f"-{daily_summary['idle_percentage']:.1f}% idle")
    with col3:
        st.metric("Focus Score", f"{daily_summary['focus_score']}/100", 
                 help="Based on number of 30+ minute sessions")
    with col4:
        st.metric("Sessions", daily_summary['sessions_count'], 
                 delta=f"{daily_summary['average_session_minutes']:.1f} min avg")
    
    # Additional metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Unique Tasks", daily_summary['unique_tasks'])
    with col2:
        st.metric("Longest Session", f"{daily_summary['longest_session_minutes']:.1f} min")
    with col3:
        high_conf = daily_summary['high_confidence_sessions']
        total_sessions = daily_summary['sessions_count']
        conf_pct = (high_conf / total_sessions * 100) if total_sessions > 0 else 0
        st.metric("High Confidence", f"{high_conf}/{total_sessions}", delta=f"{conf_pct:.0f}%")
    with col4:
        most_used = max(category_times.items(), key=lambda x: x[1])[0] if category_times else "N/A"
        st.metric("Top Category", most_used)
    
    # Time distribution
    st.header("📊 Time Distribution")
    if category_times:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = create_time_distribution_pie(category_times)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Category Breakdown")
            for category, time_spent in sorted(category_times.items(), key=lambda x: x[1], reverse=True):
                percentage = (time_spent / total_tracked_time) * 100
                st.write(f"{category}: {time_spent:.1f} min ({percentage:.1f}%)")
                st.progress(percentage / 100)
    
    # Task timeline
    st.header("📅 Task Timeline")
    if tasks_data:
        # Sort tasks by total time spent
        sorted_tasks = sorted(
            [(task, sum(p['duration'] for p in periods)) for task, periods in tasks_data.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Show top 20 tasks
        top_tasks = dict(sorted_tasks[:20])
        timeline_data = {task: tasks_data[task] for task in top_tasks.keys()}
        
        fig = create_timeline_chart(timeline_data)
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed task list with enhanced metrics
    st.header("📋 Detailed Task List")
    
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
            'Category': metrics['category'],
            'First Seen': metrics['first_seen'].strftime('%H:%M') if metrics['first_seen'] else 'N/A',
            'Last Seen': metrics['last_seen'].strftime('%H:%M') if metrics['last_seen'] else 'N/A'
        })
    
    if task_summaries:
        task_df = pd.DataFrame(task_summaries)
        task_df = task_df.sort_values('Total Time (min)', ascending=False)
        
        # Use dataframe display with enhanced formatting
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

if __name__ == "__main__":
    main()