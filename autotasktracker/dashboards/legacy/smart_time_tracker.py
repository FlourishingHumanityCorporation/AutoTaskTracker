import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta, date
import json
import plotly.graph_objects as go
import plotly.express as px
from context_aware_tracker import ContextAwareTimeTracker, process_screenshots_with_context

# --- Configuration ---
HOME_DIR = os.path.expanduser("~")
PENSIEVE_DB_PATH = os.path.join(HOME_DIR, '.memos', 'database.db')

# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="Smart Time Tracker", page_icon="🧠")

st.title("🧠 Smart Context-Aware Time Tracker")
st.write("Intelligently tracks your tasks based on context, not just window titles")

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(f'file:{PENSIEVE_DB_PATH}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        st.error(f"Error connecting to the database: {e}")
        return None

# --- Data Fetching ---
@st.cache_data(ttl=60)
def fetch_screenshot_data(start_date, end_date):
    """Fetch raw screenshot data with window titles."""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT
        e.created_at,
        me2.value as active_window
    FROM
        entities e
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
    WHERE
        e.file_type_group = 'image'
        AND e.created_at >= ?
        AND e.created_at <= ?
    ORDER BY
        e.created_at ASC
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
        conn.close()
        
        # Process timestamps
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Extract window title from JSON if needed
        def extract_window_title(window_data):
            if not window_data:
                return "Unknown"
            try:
                if isinstance(window_data, str) and window_data.startswith('{'):
                    data = json.loads(window_data)
                    return data.get('title', window_data)
                return str(window_data)
            except:
                return str(window_data)
                
        df['active_window'] = df['active_window'].apply(extract_window_title)
        
        return df
    except Exception as e:
        st.error(f"Error querying the database: {e}")
        return pd.DataFrame()

# --- Main App ---
# Date selection
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    selected_date = st.date_input("Select Date", date.today())
with col2:
    date_range = st.selectbox(
        "Or select range",
        ["Single Day", "Last 7 Days", "Last 30 Days", "Custom Range"],
        index=0
    )
with col3:
    if date_range == "Custom Range":
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", date.today() - timedelta(days=7))
        with date_col2:
            end_date = st.date_input("End Date", date.today())
    else:
        if date_range == "Single Day":
            start_date = selected_date
            end_date = selected_date
        elif date_range == "Last 7 Days":
            end_date = date.today()
            start_date = end_date - timedelta(days=6)
        else:  # Last 30 Days
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

# Advanced settings
with st.expander("⚙️ Advanced Settings"):
    col1, col2, col3 = st.columns(3)
    with col1:
        context_threshold = st.slider(
            "Context Switch Threshold (seconds)",
            min_value=10,
            max_value=120,
            value=30,
            help="Time before considering a window switch as a new task"
        )
    with col2:
        return_threshold = st.slider(
            "Task Return Window (minutes)",
            min_value=1,
            max_value=15,
            value=5,
            help="Time window to return to a previous task"
        )
    with col3:
        min_duration = st.slider(
            "Minimum Task Duration (minutes)",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Minimum duration to count as a task"
        )

# Fetch and process data
screenshots_df = fetch_screenshot_data(
    datetime.combine(start_date, datetime.min.time()),
    datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
)

if not screenshots_df.empty:
    # Process with context-aware tracker
    with st.spinner("Analyzing task context..."):
        # Create custom tracker with user settings
        tracker = ContextAwareTimeTracker(
            context_switch_threshold_seconds=context_threshold,
            task_return_threshold_minutes=return_threshold,
            min_task_duration_minutes=min_duration
        )
        
        # Process screenshots
        screenshots_df = screenshots_df.sort_values('created_at')
        for idx, row in screenshots_df.iterrows():
            tracker.process_screenshot(row['active_window'], row['created_at'])
        
        # Get tasks
        tasks = tracker.get_completed_tasks()
        
        # Convert to dataframe
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'task_id': task.task_id,
                'task_name': task.name,
                'category': task.category.title(),
                'main_app': task.main_app,
                'start_time': task.start_time,
                'end_time': task.end_time,
                'duration_minutes': round(task.active_duration, 1),
                'screenshots': task.total_screenshots,
                'context_switches': len(task.context_windows),
                'windows_used': ', '.join(set([w.split(' - ')[-1] for w in task.context_windows]))
            })
        
        tasks_df = pd.DataFrame(tasks_data)
    
    if not tasks_df.empty:
        # Summary metrics
        st.header("📊 Smart Task Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_hours = tasks_df['duration_minutes'].sum() / 60
        unique_tasks = len(tasks_df)
        avg_duration = tasks_df['duration_minutes'].mean()
        context_switches = tasks_df['context_switches'].sum()
        
        with col1:
            st.metric("Total Tracked Time", f"{total_hours:.1f} hours")
        with col2:
            st.metric("Distinct Tasks", unique_tasks)
        with col3:
            st.metric("Avg Task Duration", f"{avg_duration:.1f} min")
        with col4:
            st.metric("Context Switches", context_switches)
        
        # Task timeline
        st.header("📅 Task Timeline")
        
        fig_timeline = go.Figure()
        
        # Group by category for coloring
        categories = tasks_df['category'].unique()
        colors = px.colors.qualitative.Set3[:len(categories)]
        color_map = dict(zip(categories, colors))
        
        # Add task bars
        for idx, task in tasks_df.iterrows():
            fig_timeline.add_trace(go.Bar(
                x=[task['duration_minutes']],
                y=[task['task_name']],
                orientation='h',
                name=task['category'],
                marker_color=color_map[task['category']],
                hovertemplate=(
                    f"<b>{task['task_name']}</b><br>" +
                    f"Category: {task['category']}<br>" +
                    f"Duration: {task['duration_minutes']} min<br>" +
                    f"Time: {task['start_time'].strftime('%H:%M')} - {task['end_time'].strftime('%H:%M')}<br>" +
                    f"Apps used: {task['windows_used']}<br>" +
                    "<extra></extra>"
                ),
                showlegend=idx == tasks_df[tasks_df['category'] == task['category']].index[0]
            ))
        
        fig_timeline.update_layout(
            title="Tasks by Duration",
            xaxis_title="Duration (minutes)",
            yaxis_title="Task",
            height=max(400, len(tasks_df) * 30),
            barmode='stack',
            showlegend=True
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Gantt chart view
        st.header("⏰ Task Schedule")
        
        fig_gantt = go.Figure()
        
        for idx, task in tasks_df.iterrows():
            fig_gantt.add_trace(go.Scatter(
                x=[task['start_time'], task['end_time']],
                y=[task['category'], task['category']],
                mode='lines',
                line=dict(
                    color=color_map[task['category']],
                    width=20
                ),
                name=task['task_name'],
                hovertemplate=(
                    f"<b>{task['task_name']}</b><br>" +
                    f"Start: %{x}<br>" +
                    f"Duration: {task['duration_minutes']} min<br>" +
                    "<extra></extra>"
                ),
                showlegend=False
            ))
        
        fig_gantt.update_layout(
            title="Task Timeline by Category",
            xaxis_title="Time",
            yaxis_title="Category",
            height=400,
            hovermode='closest'
        )
        st.plotly_chart(fig_gantt, use_container_width=True)
        
        # Detailed task table
        st.header("📋 Detailed Task List")
        
        # Add filters
        col1, col2 = st.columns([1, 3])
        with col1:
            category_filter = st.multiselect(
                "Filter by Category",
                options=tasks_df['category'].unique(),
                default=tasks_df['category'].unique()
            )
        
        # Filter dataframe
        filtered_df = tasks_df[tasks_df['category'].isin(category_filter)]
        
        # Display table
        display_df = filtered_df[['task_name', 'category', 'start_time', 'end_time', 'duration_minutes', 'windows_used']]
        display_df['start_time'] = display_df['start_time'].dt.strftime('%H:%M:%S')
        display_df['end_time'] = display_df['end_time'].dt.strftime('%H:%M:%S')
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "task_name": st.column_config.TextColumn("Task", width="large"),
                "category": st.column_config.TextColumn("Category", width="small"),
                "start_time": st.column_config.TextColumn("Start", width="small"),
                "end_time": st.column_config.TextColumn("End", width="small"),
                "duration_minutes": st.column_config.NumberColumn("Duration (min)", format="%.1f", width="small"),
                "windows_used": st.column_config.TextColumn("Applications", width="medium")
            }
        )
        
        # Category breakdown
        st.header("🎯 Time by Category")
        
        category_time = filtered_df.groupby('category')['duration_minutes'].sum().sort_values(ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_pie = px.pie(
                values=category_time.values,
                names=category_time.index,
                title="Time Distribution by Category"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("Category Summary")
            for category, minutes in category_time.items():
                hours = minutes / 60
                st.metric(category, f"{hours:.1f} hours", f"{minutes:.0f} min")
        
        # Export section
        st.header("💾 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Detailed export
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Tasks (CSV)",
                data=csv,
                file_name=f"smart_tasks_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Summary export
            summary = {
                'date_range': f"{start_date} to {end_date}",
                'total_hours': round(total_hours, 1),
                'task_count': unique_tasks,
                'categories': category_time.to_dict(),
                'settings': {
                    'context_threshold_seconds': context_threshold,
                    'return_threshold_minutes': return_threshold,
                    'min_duration_minutes': min_duration
                }
            }
            st.download_button(
                label="📥 Download Summary (JSON)",
                data=json.dumps(summary, indent=2, default=str),
                file_name=f"task_summary_{start_date}_{end_date}.json",
                mime="application/json"
            )
        
        with col3:
            # Time report
            report = f"""Smart Time Tracking Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Date Range: {start_date} to {end_date}

SUMMARY:
Total Time: {total_hours:.1f} hours
Tasks Tracked: {unique_tasks}
Average Task Duration: {avg_duration:.1f} minutes

CATEGORY BREAKDOWN:
"""
            for category, minutes in category_time.items():
                report += f"{category}: {minutes/60:.1f} hours ({minutes:.0f} minutes)\n"
            
            report += f"\nDETAILED TASKS:\n"
            for _, task in filtered_df.iterrows():
                report += f"\n{task['task_name']}\n"
                report += f"  Time: {task['start_time']} - {task['end_time']}\n"
                report += f"  Duration: {task['duration_minutes']} minutes\n"
                report += f"  Apps: {task['windows_used']}\n"
            
            st.download_button(
                label="📥 Download Report (TXT)",
                data=report,
                file_name=f"time_report_{start_date}_{end_date}.txt",
                mime="text/plain"
            )
    else:
        st.info("No tasks found for the selected period with current settings. Try adjusting the thresholds.")
else:
    st.info("No data available for the selected date range. Make sure AutoTaskTracker is running.")

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.header("🧠 How Smart Tracking Works")
st.sidebar.markdown("""
This tracker understands **context**:

1. **Email Tasks**: Tracks each recipient separately
2. **Research**: Groups related browsing with main task
3. **Context Switching**: Knows when you return to a task
4. **Supporting Apps**: Links research/terminal to main work

**Example**: 
- Writing email to John → Research LinkedIn → Back to email
- All tracked as one "Email to John" task!
""")
st.sidebar.caption(f"Database: {PENSIEVE_DB_PATH}")