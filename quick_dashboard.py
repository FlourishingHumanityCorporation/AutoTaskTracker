#!/usr/bin/env python3
"""
Quick AutoTaskTracker dashboard with direct PostgreSQL connection.
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="📋 AutoTaskTracker - Task Board", 
    page_icon="📋",
    layout="wide"
)

st.title("📋 AutoTaskTracker - Task Board")

# PostgreSQL connection
DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"

# Sidebar filters
st.sidebar.header("🔍 Filters")

time_filter = st.sidebar.selectbox(
    "Time Filter",
    ["All Time", "Today", "Last 24 Hours", "Last 7 Days", "Last Hour", "Last 15 Minutes"]
)

# Convert time filter to date range
now = datetime.now()
start_date = None

if time_filter == "Last 15 Minutes":
    start_date = now - timedelta(minutes=15)
elif time_filter == "Last Hour":
    start_date = now - timedelta(hours=1)
elif time_filter == "Today":
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
elif time_filter == "Last 24 Hours":
    start_date = now - timedelta(days=1)
elif time_filter == "Last 7 Days":
    start_date = now - timedelta(days=7)

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    
    # Base query
    query = """
    SELECT
        e.id,
        e.filepath,
        e.created_at,
        me1.value as ocr_text,
        me2.value as active_window
    FROM
        entities e
        LEFT JOIN metadata_entries me1 ON e.id = me1.entity_id AND me1.key = 'ocr_result'
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
    WHERE
        (e.filepath LIKE '%.png' 
         OR e.filepath LIKE '%.jpg' 
         OR e.filepath LIKE '%.jpeg'
         OR e.filepath LIKE '%.webp')
    """
    
    params = []
    if start_date:
        query += " AND e.created_at >= %s"
        params.append(start_date)
    
    query += " ORDER BY e.created_at DESC LIMIT 100"
    
    # Execute query
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if rows:
            # Convert to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            
            # Add filename column
            import os
            df['filename'] = df['filepath'].apply(lambda x: os.path.basename(x) if x else None)
            
            # Show metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Total Screenshots", len(df))
            
            with col2:
                # Safe check for OCR text
                try:
                    with_ocr = len(df[df['ocr_text'].notna() & (df['ocr_text'] != '') & (df['ocr_text'].astype(str) != 'None')])
                except:
                    with_ocr = 0
                st.metric("📝 With OCR Text", with_ocr)
            
            with col3:
                # Safe check for window info
                try:
                    with_window = len(df[df['active_window'].notna() & (df['active_window'] != '') & (df['active_window'].astype(str) != 'None')])
                except:
                    with_window = 0
                st.metric("🪟 With Window Info", with_window)
            
            with col4:
                if start_date:
                    hours_ago = (now - start_date).total_seconds() / 3600
                    st.metric("⏰ Time Range", f"{hours_ago:.1f}h ago")
                else:
                    st.metric("⏰ Time Range", "All Time")
            
            st.markdown("---")
            
            # Group by window if we have window data
            if 'active_window' in df.columns:
                windows = df['active_window'].value_counts()
                if not windows.empty:
                    st.subheader("🪟 Activity by Window")
                    
                    for window, count in windows.head(10).items():
                        if pd.notna(window) and window:
                            with st.expander(f"{window} ({count} screenshots)"):
                                window_df = df[df['active_window'] == window].head(5)
                                for _, row in window_df.iterrows():
                                    st.write(f"**{row['filename']}** - {row['created_at']}")
                                    if row['ocr_text']:
                                        st.write(f"OCR: {row['ocr_text'][:100]}...")
                                    st.write("---")
            
            st.markdown("---")
            
            # Recent screenshots
            st.subheader("📱 Recent Screenshots")
            
            for _, row in df.head(10).iterrows():
                with st.expander(f"{row['filename']} - {row['created_at']}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**File:** {row['filepath']}")
                        st.write(f"**Created:** {row['created_at']}")
                        if row['active_window']:
                            st.write(f"**Window:** {row['active_window']}")
                        if row['ocr_text']:
                            st.write(f"**OCR Text:**")
                            st.write(row['ocr_text'])
                    
                    with col2:
                        st.write(f"**ID:** {row['id']}")
                        if row['ocr_text']:
                            word_count = len(row['ocr_text'].split())
                            st.write(f"**Words:** {word_count}")
            
            # Raw data view
            if st.checkbox("Show Raw Data"):
                st.subheader("📊 Raw Data")
                st.dataframe(df, use_container_width=True)
                
                # Export option
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"autotasktracker_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
        else:
            st.warning(f"⚠️ No screenshots found for {time_filter}")
            st.info("💡 Make sure AutoTaskTracker is capturing screenshots and processing them.")
    
    conn.close()
    
    # Show status
    st.sidebar.success("✅ Connected to PostgreSQL")
    st.sidebar.info(f"🗄️ Database: autotasktracker")
    
except Exception as e:
    st.error(f"❌ Database Error: {e}")
    st.sidebar.error("❌ Database Connection Failed")

# Auto-refresh
if st.sidebar.button("🔄 Refresh"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.write("**AutoTaskTracker** v2.0")
st.sidebar.write("PostgreSQL Backend")