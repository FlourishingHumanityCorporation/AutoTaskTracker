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
    
    # Process data
    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.sort_values('created_at')
    
    # Extract tasks and categories
    tasks_data = defaultdict(list)
    category_times = defaultdict(float)
    total_tracked_time = 0
    
    # Group continuous activities
    current_task = None
    current_start = None
    current_category = None
    
    for idx, row in df.iterrows():
        task, app = extract_task_info(row['active_window'], row['ocr_text'])
        window_title = extract_window_title(row['active_window'])
        category = ActivityCategorizer.categorize(window_title, row['ocr_text'])
        
        # Check if this is a continuation of the previous task
        if current_task and current_task == task:
            # Check if time gap is reasonable (< 10 minutes)
            time_gap = (row['created_at'] - prev_time).total_seconds() / 60
            if time_gap > 10:
                # Save current task period
                duration = (prev_time - current_start).total_seconds() / 60
                if duration > 1:  # Only track tasks > 1 minute
                    tasks_data[current_task].append({
                        'start': current_start,
                        'end': prev_time,
                        'duration': duration,
                        'category': current_category,
                        'app': app,
                        'color': ActivityCategorizer.CATEGORIES.get(
                            next((k for k, v in ActivityCategorizer.CATEGORIES.items() if v[0] == current_category), 'other'),
                            ('', [])
                        )[0].split()[0] if current_category else 'lightgray'  # Extract emoji as color hint
                    })
                    category_times[current_category] += duration
                    total_tracked_time += duration
                
                # Start new period
                current_start = row['created_at']
        else:
            # New task - save previous if exists
            if current_task and current_start:
                duration = (prev_time - current_start).total_seconds() / 60
                if duration > 1:
                    tasks_data[current_task].append({
                        'start': current_start,
                        'end': prev_time,
                        'duration': duration,
                        'category': current_category,
                        'app': app,
                        'color': ActivityCategorizer.CATEGORIES.get(
                            next((k for k, v in ActivityCategorizer.CATEGORIES.items() if v[0] == current_category), 'other'),
                            ('', [])
                        )[0].split()[0] if current_category else 'lightgray'
                    })
                    category_times[current_category] += duration
                    total_tracked_time += duration
            
            # Start tracking new task
            current_task = task
            current_start = row['created_at']
            current_category = category
        
        prev_time = row['created_at']
    
    # Don't forget the last task
    if current_task and current_start:
        duration = (prev_time - current_start).total_seconds() / 60
        if duration > 1:
            tasks_data[current_task].append({
                'start': current_start,
                'end': prev_time,
                'duration': duration,
                'category': current_category,
                'app': app
            })
            category_times[current_category] += duration
            total_tracked_time += duration
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tracked Time", f"{total_tracked_time:.1f} min" if total_tracked_time < 120 else f"{total_tracked_time/60:.1f} hours")
    with col2:
        st.metric("Unique Tasks", len(tasks_data))
    with col3:
        st.metric("Most Used Category", max(category_times.items(), key=lambda x: x[1])[0] if category_times else "N/A")
    with col4:
        avg_task_duration = total_tracked_time / len(tasks_data) if tasks_data else 0
        st.metric("Avg Task Duration", f"{avg_task_duration:.1f} min")
    
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
    
    # Detailed task list
    st.header("📋 Detailed Task List")
    
    # Create task summary dataframe
    task_summaries = []
    for task, periods in tasks_data.items():
        total_duration = sum(p['duration'] for p in periods)
        first_seen = min(p['start'] for p in periods)
        last_seen = max(p['end'] for p in periods)
        categories = list(set(p.get('category', 'Other') for p in periods))
        
        task_summaries.append({
            'Task': task[:60] + '...' if len(task) > 60 else task,
            'Total Time (min)': f"{total_duration:.1f}",
            'Sessions': len(periods),
            'First Seen': first_seen.strftime('%H:%M'),
            'Last Seen': last_seen.strftime('%H:%M'),
            'Categories': ', '.join(categories)
        })
    
    if task_summaries:
        task_df = pd.DataFrame(task_summaries)
        task_df = task_df.sort_values('Total Time (min)', ascending=False)
        
        # Use dataframe display with formatting
        st.dataframe(
            task_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Time (min)": st.column_config.NumberColumn(
                    "Total Time (min)",
                    format="%.1f"
                ),
                "Sessions": st.column_config.NumberColumn(
                    "Sessions",
                    format="%d"
                )
            }
        )
        
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