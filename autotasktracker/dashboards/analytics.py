"""
Analytics Dashboard for AutoTaskTracker
Shows productivity metrics and insights
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import plotly.express as px
import plotly.graph_objects as go

from autotasktracker import (
    DatabaseManager,
    ActivityCategorizer,
    extract_window_title,
    Config,
    get_config
)

# Initialize configuration
config = get_config()

# --- Data Fetching ---
@st.cache_data(ttl=60)
def fetch_analytics_data(start_date, end_date):
    """Fetch data for analytics within date range."""
    db = DatabaseManager(config.DB_PATH)
    
    # Fetch tasks
    df = db.fetch_tasks(start_date=start_date, end_date=end_date, limit=10000)
    
    if df.empty:
        return pd.DataFrame()
    
    # Add derived columns
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['hour'] = df['created_at'].dt.hour
    df['date'] = df['created_at'].dt.date
    df['weekday'] = df['created_at'].dt.day_name()
    
    # Extract window titles and categories
    df['window_title'] = df['active_window'].apply(extract_window_title)
    df['category'] = df.apply(
        lambda row: ActivityCategorizer.categorize(row['window_title'], row['ocr_text']), 
        axis=1
    )
    
    return df

# --- Analytics Functions ---
def calculate_productivity_metrics(df):
    """Calculate productivity metrics from the dataframe."""
    if df.empty:
        return {}
    
    # Time range
    time_range = df['created_at'].max() - df['created_at'].min()
    total_hours = time_range.total_seconds() / 3600
    
    # Activity counts
    total_activities = len(df)
    unique_apps = df['window_title'].nunique()
    
    # Category distribution
    category_counts = df['category'].value_counts()
    
    # Most active hours
    hourly_activity = df['hour'].value_counts().sort_index()
    
    # Daily activity
    daily_activity = df.groupby('date').size()
    
    # Focus sessions (continuous work > 30 min)
    df_sorted = df.sort_values('created_at')
    df_sorted['time_diff'] = df_sorted['created_at'].diff()
    df_sorted['session_break'] = df_sorted['time_diff'] > timedelta(minutes=10)
    df_sorted['session_id'] = df_sorted['session_break'].cumsum()
    
    session_durations = []
    for session_id, group in df_sorted.groupby('session_id'):
        duration = (group['created_at'].max() - group['created_at'].min()).total_seconds() / 60
        if duration > 30:  # Focus sessions > 30 minutes
            session_durations.append(duration)
    
    metrics = {
        'total_hours': total_hours,
        'total_activities': total_activities,
        'unique_apps': unique_apps,
        'avg_activities_per_hour': total_activities / max(total_hours, 1),
        'category_distribution': category_counts.to_dict(),
        'hourly_activity': hourly_activity.to_dict(),
        'daily_activity': daily_activity.to_dict(),
        'focus_sessions': len(session_durations),
        'avg_focus_duration': sum(session_durations) / len(session_durations) if session_durations else 0,
        'longest_focus': max(session_durations) if session_durations else 0
    }
    
    return metrics

# --- Visualization Functions ---
def create_category_pie_chart(category_distribution):
    """Create pie chart for category distribution."""
    df = pd.DataFrame(
        list(category_distribution.items()), 
        columns=['Category', 'Count']
    )
    fig = px.pie(
        df, 
        values='Count', 
        names='Category', 
        title='Activity Distribution by Category'
    )
    return fig

def create_hourly_heatmap(df):
    """Create heatmap showing activity by hour and day."""
    # Create hour x day matrix
    pivot = df.pivot_table(
        index='hour', 
        columns='weekday', 
        values='id', 
        aggfunc='count',
        fill_value=0
    )
    
    # Reorder days
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex(columns=[d for d in days_order if d in pivot.columns])
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='Blues',
        hoverongaps=False
    ))
    
    fig.update_layout(
        title='Activity Heatmap by Hour and Day',
        xaxis_title='Day of Week',
        yaxis_title='Hour of Day',
        yaxis=dict(autorange='reversed')
    )
    
    return fig

def create_timeline_chart(df):
    """Create timeline chart of activities."""
    # Sample data if too large
    if len(df) > 1000:
        df_sample = df.sample(n=1000).sort_values('created_at')
    else:
        df_sample = df
    
    fig = px.scatter(
        df_sample,
        x='created_at',
        y='category',
        color='category',
        title='Activity Timeline',
        hover_data=['window_title']
    )
    
    fig.update_layout(
        showlegend=False,
        height=400
    )
    
    return fig

# --- Streamlit App ---
def main():
    st.set_page_config(
        layout="wide", 
        page_title="Task Analytics Dashboard", 
        page_icon="📊"
    )
    
    st.title("📊 Task Analytics Dashboard")
    st.write("Deep insights into your productivity patterns")
    
    # Sidebar for date selection
    st.sidebar.header("📅 Date Range")
    
    # Date range options
    date_option = st.sidebar.selectbox(
        "Select Range",
        ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Custom"]
    )
    
    # Calculate date range
    end_date = datetime.now()
    if date_option == "Today":
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_option == "Yesterday":
        start_date = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_option == "Last 7 Days":
        start_date = datetime.now() - timedelta(days=7)
    elif date_option == "Last 30 Days":
        start_date = datetime.now() - timedelta(days=30)
    else:  # Custom
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())
    
    # Database check
    db = DatabaseManager(config.DB_PATH)
    if not db.test_connection():
        st.error("❌ Cannot connect to database. Make sure Memos is running.")
        st.stop()
    
    # Fetch data
    with st.spinner("Loading analytics data..."):
        df = fetch_analytics_data(start_date, end_date)
    
    if df.empty:
        st.info("📭 No data found for the selected date range.")
        return
    
    # Calculate metrics
    metrics = calculate_productivity_metrics(df)
    
    # Display key metrics
    st.header("🎯 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Hours Tracked",
            f"{metrics['total_hours']:.1f}h",
            help="Total time span of captured activities"
        )
    
    with col2:
        st.metric(
            "Activities Captured",
            metrics['total_activities'],
            help="Total number of screenshots analyzed"
        )
    
    with col3:
        st.metric(
            "Unique Applications",
            metrics['unique_apps'],
            help="Number of different applications used"
        )
    
    with col4:
        st.metric(
            "Focus Sessions",
            metrics['focus_sessions'],
            help="Work sessions longer than 30 minutes"
        )
    
    # Category distribution
    st.header("📊 Activity Breakdown")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Category Distribution")
        fig = create_category_pie_chart(metrics['category_distribution'])
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Top Applications")
        top_apps = df['window_title'].value_counts().head(10)
        st.bar_chart(top_apps)
    
    # Time patterns
    st.header("⏰ Time Patterns")
    
    # Hourly heatmap
    if len(df) > 10:
        fig = create_hourly_heatmap(df)
        st.plotly_chart(fig, use_container_width=True)
    
    # Timeline
    st.subheader("📈 Activity Timeline")
    fig = create_timeline_chart(df)
    st.plotly_chart(fig, use_container_width=True)
    
    # Focus metrics
    if metrics['focus_sessions'] > 0:
        st.header("🎯 Focus Analysis")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Average Focus Duration",
                f"{metrics['avg_focus_duration']:.0f} min",
                help="Average length of focus sessions"
            )
        
        with col2:
            st.metric(
                "Longest Focus Session",
                f"{metrics['longest_focus']:.0f} min",
                help="Your longest uninterrupted work session"
            )
        
        with col3:
            focus_percentage = (metrics['focus_sessions'] * metrics['avg_focus_duration'] / 60) / metrics['total_hours'] * 100
            st.metric(
                "Focus Time %",
                f"{focus_percentage:.1f}%",
                help="Percentage of time in focus sessions"
            )
    
    # Export options
    st.header("💾 Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download Raw Data (CSV)"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"task_data_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📊 Generate Report"):
            report = f"""# Productivity Report
Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}

## Summary
- Total Hours Tracked: {metrics['total_hours']:.1f}h
- Activities Captured: {metrics['total_activities']}
- Unique Applications: {metrics['unique_apps']}
- Focus Sessions: {metrics['focus_sessions']}

## Category Distribution
"""
            for cat, count in metrics['category_distribution'].items():
                percentage = (count / metrics['total_activities']) * 100
                report += f"- {cat}: {count} ({percentage:.1f}%)\n"
            
            st.download_button(
                label="Download Report",
                data=report,
                file_name=f"productivity_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()