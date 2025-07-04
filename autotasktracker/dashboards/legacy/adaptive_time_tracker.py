import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, date
import json
import plotly.graph_objects as go
import plotly.express as px
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from intelligent_task_detector import IntelligentTaskDetector, process_screenshots_intelligently

# --- Configuration ---
HOME_DIR = os.path.expanduser("~")
PENSIEVE_DB_PATH = os.path.join(HOME_DIR, '.memos', 'database.db')

# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="Adaptive Time Tracker", page_icon="🤖")

st.title("🤖 Adaptive AI-Powered Time Tracker")
st.write("Learns your work patterns to automatically detect task boundaries - no configuration needed!")

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
        datetime(e.created_at, 'localtime') as created_at,
        me2.value as active_window
    FROM
        entities e
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
    WHERE
        e.file_type_group = 'image'
        AND datetime(e.created_at, 'localtime') >= ?
        AND datetime(e.created_at, 'localtime') <= ?
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
col1, col2 = st.columns([1, 3])
with col1:
    date_range = st.selectbox(
        "Select timeframe",
        ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Custom Range"],
        index=0
    )
    
with col2:
    if date_range == "Custom Range":
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", date.today() - timedelta(days=7))
        with date_col2:
            end_date = st.date_input("End Date", date.today())
    else:
        if date_range == "Today":
            start_date = end_date = date.today()
        elif date_range == "Yesterday":
            start_date = end_date = date.today() - timedelta(days=1)
        elif date_range == "Last 7 Days":
            end_date = date.today()
            start_date = end_date - timedelta(days=6)
        else:  # Last 30 Days
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

# Fetch and process data
screenshots_df = fetch_screenshot_data(
    datetime.combine(start_date, datetime.min.time()),
    datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
)

if not screenshots_df.empty:
    st.sidebar.success(f"✅ Found {len(screenshots_df)} screenshots")
    # Process with intelligent detector
    with st.spinner("🧠 AI is learning your work patterns and detecting tasks..."):
        tasks_df, statistics = process_screenshots_intelligently(screenshots_df)
    
    if not tasks_df.empty:
        # Show learning statistics
        with st.expander("🎓 AI Learning Statistics", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Avg Task Duration", f"{statistics.get('avg_task_duration', 0):.1f} min")
            with col2:
                st.metric("Avg Windows/Task", f"{statistics.get('avg_windows_per_task', 0):.1f}")
            with col3:
                st.metric("Sessions Analyzed", statistics.get('total_sessions_analyzed', 0))
            with col4:
                st.metric("Detection Threshold", f"{statistics.get('learned_threshold', 0.7):.2f}")
            
            if statistics.get('common_transitions'):
                st.subheader("Learned Task Patterns")
                st.write("The AI has learned these app transitions are usually part of the same task:")
                for transition in statistics['common_transitions'][:5]:
                    st.write(f"• {transition}")
        
        # Summary metrics
        st.header("📊 Intelligent Task Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_hours = tasks_df['duration_minutes'].sum() / 60
        task_count = len(tasks_df)
        avg_duration = tasks_df['duration_minutes'].mean()
        avg_confidence = tasks_df['confidence'].mean()
        
        with col1:
            st.metric("Total Time Tracked", f"{total_hours:.1f} hours")
        with col2:
            st.metric("Tasks Detected", task_count)
        with col3:
            st.metric("Avg Task Duration", f"{avg_duration:.1f} min")
        with col4:
            st.metric("Detection Confidence", f"{avg_confidence:.0%}")
        
        # Task timeline with confidence visualization
        st.header("📅 AI-Detected Task Timeline")
        
        fig_timeline = go.Figure()
        
        # Color by confidence level
        tasks_df['confidence_category'] = pd.cut(
            tasks_df['confidence'], 
            bins=[0, 0.6, 0.8, 1.0], 
            labels=['Low', 'Medium', 'High']
        )
        
        colors = {'Low': '#ffcccc', 'Medium': '#ffffcc', 'High': '#ccffcc'}
        
        for idx, task in tasks_df.iterrows():
            fig_timeline.add_trace(go.Scatter(
                x=[task['start_time'], task['end_time']],
                y=[idx, idx],
                mode='lines',
                line=dict(
                    color=colors[task['confidence_category']],
                    width=20
                ),
                name=task['task_name'],
                hovertemplate=(
                    f"<b>{task['task_name']}</b><br>" +
                    f"Time: %{{x}}<br>" +
                    f"Duration: {task['duration_minutes']:.1f} min<br>" +
                    f"Windows: {task['window_count']}<br>" +
                    f"Confidence: {task['confidence']:.0%}<br>" +
                    "<extra></extra>"
                ),
                showlegend=False
            ))
            
            # Add task name as annotation
            fig_timeline.add_annotation(
                x=task['start_time'] + (task['end_time'] - task['start_time']) / 2,
                y=idx,
                text=task['task_name'][:30] + '...' if len(task['task_name']) > 30 else task['task_name'],
                showarrow=False,
                font=dict(size=10)
            )
        
        fig_timeline.update_layout(
            title="Tasks Detected by AI (Colored by Confidence)",
            xaxis_title="Time",
            yaxis=dict(showticklabels=False, title="Tasks"),
            height=max(400, len(tasks_df) * 30),
            showlegend=False
        )
        
        # Add confidence legend
        for conf_cat, color in colors.items():
            fig_timeline.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=10, color=color),
                name=f"{conf_cat} Confidence"
            ))
        
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Task duration distribution
        st.header("⏱️ Task Duration Patterns")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Histogram of task durations
            fig_hist = px.histogram(
                tasks_df, 
                x='duration_minutes',
                nbins=30,
                title="Distribution of Task Durations",
                labels={'duration_minutes': 'Duration (minutes)', 'count': 'Number of Tasks'}
            )
            fig_hist.add_vline(
                x=avg_duration, 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Average: {avg_duration:.1f} min"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Statistics
            st.subheader("Duration Statistics")
            st.metric("Shortest Task", f"{tasks_df['duration_minutes'].min():.1f} min")
            st.metric("Longest Task", f"{tasks_df['duration_minutes'].max():.1f} min")
            st.metric("Median Duration", f"{tasks_df['duration_minutes'].median():.1f} min")
            
            # Task complexity
            st.subheader("Task Complexity")
            simple_tasks = len(tasks_df[tasks_df['unique_windows'] == 1])
            complex_tasks = len(tasks_df[tasks_df['unique_windows'] > 3])
            st.metric("Simple Tasks", f"{simple_tasks} ({simple_tasks/len(tasks_df):.0%})")
            st.metric("Complex Tasks", f"{complex_tasks} ({complex_tasks/len(tasks_df):.0%})")
        
        # Detailed task list with AI insights
        st.header("🔍 Detailed Task Analysis")
        
        # Add confidence filter
        confidence_filter = st.slider(
            "Minimum Confidence Level",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Filter tasks by AI confidence level"
        )
        
        filtered_df = tasks_df[tasks_df['confidence'] >= confidence_filter].copy()
        
        # Prepare display
        filtered_df['start_time_str'] = filtered_df['start_time'].dt.strftime('%H:%M:%S')
        filtered_df['end_time_str'] = filtered_df['end_time'].dt.strftime('%H:%M:%S')
        filtered_df['duration_str'] = filtered_df['duration_minutes'].apply(lambda x: f"{int(x)}m {int((x % 1) * 60)}s")
        filtered_df['confidence_str'] = filtered_df['confidence'].apply(lambda x: f"{x:.0%}")
        
        # Display table
        display_columns = ['task_name', 'start_time_str', 'end_time_str', 'duration_str', 
                          'window_count', 'unique_windows', 'confidence_str']
        
        st.dataframe(
            filtered_df[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "task_name": st.column_config.TextColumn("Task", width="large"),
                "start_time_str": st.column_config.TextColumn("Start", width="small"),
                "end_time_str": st.column_config.TextColumn("End", width="small"),
                "duration_str": st.column_config.TextColumn("Duration", width="small"),
                "window_count": st.column_config.NumberColumn("Events", width="small"),
                "unique_windows": st.column_config.NumberColumn("Windows", width="small"),
                "confidence_str": st.column_config.TextColumn("Confidence", width="small")
            }
        )
        
        # Export section
        st.header("💾 Export AI-Detected Tasks")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Tasks (CSV)",
                data=csv,
                file_name=f"ai_tasks_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Include AI statistics in export
            export_data = {
                'date_range': f"{start_date} to {end_date}",
                'summary': {
                    'total_hours': round(total_hours, 1),
                    'task_count': task_count,
                    'avg_duration': round(avg_duration, 1),
                    'avg_confidence': round(avg_confidence, 2)
                },
                'ai_statistics': statistics,
                'tasks': filtered_df.to_dict('records')
            }
            st.download_button(
                label="📥 Download with AI Stats (JSON)",
                data=json.dumps(export_data, indent=2, default=str),
                file_name=f"ai_analysis_{start_date}_{end_date}.json",
                mime="application/json"
            )
        
        with col3:
            # Human-readable report
            report = f"""AI-Powered Time Tracking Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Date Range: {start_date} to {end_date}

SUMMARY:
Total Time: {total_hours:.1f} hours
Tasks Detected: {task_count}
Average Task Duration: {avg_duration:.1f} minutes
AI Confidence: {avg_confidence:.0%}

AI LEARNING INSIGHTS:
- Analyzed {statistics.get('total_sessions_analyzed', 0)} work sessions
- Average task contains {statistics.get('avg_windows_per_task', 0):.1f} window switches
- Adaptive threshold: {statistics.get('learned_threshold', 0.7):.2f}

DETECTED TASKS:
"""
            for _, task in filtered_df.head(50).iterrows():
                report += f"\n{task['task_name']}"
                report += f"\n  Time: {task['start_time_str']} - {task['end_time_str']}"
                report += f"\n  Duration: {task['duration_str']}"
                report += f"\n  Confidence: {task['confidence_str']}\n"
            
            st.download_button(
                label="📥 Download Report (TXT)",
                data=report,
                file_name=f"ai_time_report_{start_date}_{end_date}.txt",
                mime="text/plain"
            )
        
        # AI Insights
        st.header("🧠 AI Insights")
        
        # Work pattern analysis
        if len(tasks_df) > 5:
            st.subheader("Your Work Patterns")
            
            # Peak productivity times
            tasks_df['hour'] = tasks_df['start_time'].dt.hour
            hourly_tasks = tasks_df.groupby('hour').agg({
                'duration_minutes': 'sum',
                'task_id': 'count'
            }).rename(columns={'task_id': 'task_count'})
            
            if not hourly_tasks.empty:
                peak_hour = hourly_tasks['duration_minutes'].idxmax()
                st.write(f"🎯 **Peak Productivity Hour**: {peak_hour}:00 - {peak_hour+1}:00")
                st.write(f"   You completed {hourly_tasks.loc[peak_hour, 'task_count']} tasks totaling {hourly_tasks.loc[peak_hour, 'duration_minutes']:.0f} minutes")
            
            # Task switching patterns
            avg_gap = tasks_df['start_time'].diff().dt.total_seconds().dropna().mean() / 60
            if avg_gap < 5:
                st.write("⚡ **Rapid Task Switching**: You switch tasks every {:.1f} minutes on average".format(avg_gap))
            elif avg_gap > 30:
                st.write("🎯 **Deep Focus**: You maintain focus for {:.0f} minutes on average between tasks".format(avg_gap))
            else:
                st.write("⚖️ **Balanced Workflow**: You have a healthy {:.0f}-minute average between task switches".format(avg_gap))
            
            # Complexity insights
            simple_ratio = len(tasks_df[tasks_df['unique_windows'] <= 2]) / len(tasks_df)
            if simple_ratio > 0.7:
                st.write("📋 **Task Style**: You prefer focused, single-application tasks")
            elif simple_ratio < 0.3:
                st.write("🔄 **Task Style**: You work on complex, multi-application tasks")
            else:
                st.write("🎨 **Task Style**: You have a mix of simple and complex tasks")
    else:
        st.info("No tasks detected in the selected period. The AI needs at least a few window switches to detect task boundaries.")
else:
    st.info("No data available for the selected date range. Make sure AutoTaskTracker is running.")

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.header("🤖 How AI Detection Works")
st.sidebar.markdown("""
This tracker uses **machine learning** to:

1. **Learn Your Patterns**
   - Analyzes window switch timing
   - Identifies common app transitions
   - Adapts to your work style

2. **Detect Task Boundaries**
   - Statistical analysis of gaps
   - Content similarity matching
   - Behavioral pattern recognition

3. **No Configuration Needed**
   - Starts learning immediately
   - Improves with more data
   - Adapts to changes in routine

**The AI gets smarter the more you use it!**
""")
st.sidebar.caption(f"Database: {PENSIEVE_DB_PATH}")