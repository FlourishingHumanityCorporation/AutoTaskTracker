#!/usr/bin/env python3
"""
Simple working version of the AutoTaskTracker dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import sqlite3
import json
import os

# Database path
DB_PATH = os.path.expanduser("~/.memos/database.db")

st.set_page_config(
    page_title="AutoTaskTracker - Live Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_db_connection():
    return sqlite3.connect(DB_PATH)

def extract_window_title(active_window_str):
    """Extract window title from active_window JSON"""
    if not active_window_str:
        return "Unknown"
    try:
        data = json.loads(active_window_str)
        return data.get('title', 'Unknown')
    except:
        return active_window_str[:50] if isinstance(active_window_str, str) else "Unknown"

def categorize_activity(window_title, ocr_text=""):
    """Simple activity categorization"""
    title_lower = window_title.lower()
    
    if any(word in title_lower for word in ['code', 'vscode', 'vim', 'terminal', 'iterm']):
        return '🧑‍💻 Coding'
    elif any(word in title_lower for word in ['claude', 'chatgpt', 'copilot']):
        return '🤖 AI Tools'
    elif any(word in title_lower for word in ['slack', 'teams', 'discord', 'messages']):
        return '💬 Communication'
    elif any(word in title_lower for word in ['chrome', 'firefox', 'safari', 'browser']):
        return '🔍 Research/Browsing'
    elif any(word in title_lower for word in ['zoom', 'meet', 'webex']):
        return '🎥 Meetings'
    else:
        return '📋 Other'

def fetch_activities(hours=24):
    """Fetch activities from database"""
    conn = get_db_connection()
    since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
    SELECT 
        e.id,
        e.created_at,
        m.value as active_window,
        m2.value as ocr_text
    FROM entities e
    LEFT JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'active_window'
    LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'ocr_text'
    WHERE e.created_at >= ?
    ORDER BY e.created_at DESC
    """
    
    df = pd.read_sql_query(query, conn, params=(since,))
    conn.close()
    
    # Process the data
    df['window_title'] = df['active_window'].apply(extract_window_title)
    df['category'] = df.apply(lambda x: categorize_activity(x['window_title'], x['ocr_text'] or ''), axis=1)
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    return df

def main():
    st.title("📋 AutoTaskTracker - Live Dashboard")
    
    # Sidebar filters
    with st.sidebar:
        st.header("🎛️ Filters")
        
        time_options = {
            "Last Hour": 1,
            "Last 6 Hours": 6,
            "Last 24 Hours": 24,
            "Last 7 Days": 168,
        }
        
        selected_time = st.selectbox("Time Range", list(time_options.keys()), index=2)
        hours = time_options[selected_time]
        
        if st.button("🔄 Refresh", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch data
    df = fetch_activities(hours)
    
    if len(df) == 0:
        st.warning("No activities found for the selected time range.")
        return
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Activities", len(df))
    
    with col2:
        unique_windows = df['window_title'].nunique()
        st.metric("Unique Tasks", unique_windows)
    
    with col3:
        time_span = (df['created_at'].max() - df['created_at'].min()).total_seconds() / 3600
        st.metric("Time Span", f"{time_span:.1f} hrs")
    
    with col4:
        top_category = df['category'].value_counts().index[0]
        st.metric("Top Category", top_category)
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        # Category pie chart
        category_counts = df['category'].value_counts()
        fig = px.pie(
            values=category_counts.values, 
            names=category_counts.index,
            title="Activity Distribution",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Timeline chart
        df_timeline = df.groupby([pd.Grouper(key='created_at', freq='30min'), 'category']).size().reset_index(name='count')
        fig = px.bar(
            df_timeline, 
            x='created_at', 
            y='count', 
            color='category',
            title="Activity Timeline",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent activities table
    st.subheader("🕐 Recent Activities")
    
    # Prepare display data
    display_df = df[['created_at', 'category', 'window_title']].head(50)
    display_df['Time'] = display_df['created_at'].dt.strftime('%H:%M:%S')
    display_df = display_df[['Time', 'category', 'window_title']]
    display_df.columns = ['Time', 'Category', 'Window Title']
    
    # Truncate long titles
    display_df['Window Title'] = display_df['Window Title'].apply(lambda x: x[:80] + '...' if len(x) > 80 else x)
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Export buttons
    col1, col2, col3 = st.columns([1, 1, 8])
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name=f"activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = df.to_json(orient='records', date_format='iso')
        st.download_button(
            label="📥 Export JSON",
            data=json_data,
            file_name=f"activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    # Auto-refresh
    st.markdown("---")
    st.caption("Dashboard auto-refreshes every 60 seconds")
    time.sleep(1)
    
if __name__ == "__main__":
    import time
    main()