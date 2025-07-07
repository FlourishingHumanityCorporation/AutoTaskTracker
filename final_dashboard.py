#!/usr/bin/env python3
"""
Final AutoTaskTracker dashboard with PostgreSQL - fully working version.
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(
    page_title="📋 AutoTaskTracker - Task Board", 
    page_icon="📋",
    layout="wide"
)

st.title("📋 AutoTaskTracker - Task Board")
st.write("**PostgreSQL Backend** - Real-time task discovery from screenshots")

# PostgreSQL connection
DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"

# Sidebar filters
st.sidebar.header("🔍 Filters")

time_filter = st.sidebar.selectbox(
    "Time Filter",
    ["All Time", "Today", "Last 24 Hours", "Last 7 Days", "Last Hour", "Last 15 Minutes"]
)

show_raw_data = st.sidebar.checkbox("Show Raw Data", value=False)

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
    with psycopg2.connect(DATABASE_URL) as conn:
        
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
            
            # Show connection status
            st.sidebar.success("✅ Connected to PostgreSQL")
            st.sidebar.info(f"🗄️ Database: autotasktracker")
            st.sidebar.write(f"📊 Query returned: {len(rows)} rows")
            
            if rows:
                # Convert to DataFrame safely
                data = []
                for row in rows:
                    row_dict = dict(row)
                    # Add filename
                    if row_dict.get('filepath'):
                        row_dict['filename'] = os.path.basename(row_dict['filepath'])
                    else:
                        row_dict['filename'] = 'Unknown'
                    data.append(row_dict)
                
                df = pd.DataFrame(data)
                
                # Show metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📊 Total Screenshots", len(df))
                
                with col2:
                    # Count OCR text entries
                    ocr_count = 0
                    for _, row in df.iterrows():
                        if row.get('ocr_text') and str(row['ocr_text']).strip() and str(row['ocr_text']) != 'None':
                            ocr_count += 1
                    st.metric("📝 With OCR Text", ocr_count)
                
                with col3:
                    # Count window entries
                    window_count = 0
                    for _, row in df.iterrows():
                        if row.get('active_window') and str(row['active_window']).strip() and str(row['active_window']) != 'None':
                            window_count += 1
                    st.metric("🪟 With Window Info", window_count)
                
                with col4:
                    if start_date:
                        hours_ago = (now - start_date).total_seconds() / 3600
                        st.metric("⏰ Time Range", f"{hours_ago:.1f}h ago")
                    else:
                        st.metric("⏰ Time Range", "All Time")
                
                st.markdown("---")
                
                # Recent screenshots
                st.subheader("📱 Recent Screenshots")
                
                # Show first 5 entries
                for i, (_, row) in enumerate(df.head(5).iterrows()):
                    with st.expander(f"{row['filename']} - {row['created_at']}", expanded=(i == 0)):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**File:** `{row['filepath']}`")
                            st.write(f"**Created:** {row['created_at']}")
                            
                            if row.get('active_window') and str(row['active_window']).strip() != 'None':
                                st.write(f"**Active Window:** {row['active_window']}")
                            
                            if row.get('ocr_text') and str(row['ocr_text']).strip() != 'None':
                                st.write(f"**OCR Text:**")
                                # Truncate long text
                                ocr_text = str(row['ocr_text'])
                                if len(ocr_text) > 200:
                                    st.write(f"{ocr_text[:200]}...")
                                else:
                                    st.write(ocr_text)
                        
                        with col2:
                            st.write(f"**ID:** {row['id']}")
                            if row.get('ocr_text') and str(row['ocr_text']).strip() != 'None':
                                word_count = len(str(row['ocr_text']).split())
                                st.write(f"**Words:** {word_count}")
                
                # Group by window if we have window data
                st.markdown("---")
                st.subheader("🪟 Activity by Window")
                
                # Count by window
                window_counts = {}
                for _, row in df.iterrows():
                    window = row.get('active_window')
                    if window and str(window).strip() and str(window) != 'None':
                        window_counts[window] = window_counts.get(window, 0) + 1
                
                if window_counts:
                    # Sort by count
                    sorted_windows = sorted(window_counts.items(), key=lambda x: x[1], reverse=True)
                    
                    for window, count in sorted_windows[:5]:  # Show top 5
                        with st.expander(f"{window} ({count} screenshots)"):
                            window_data = df[df['active_window'] == window].head(3)
                            for _, wrow in window_data.iterrows():
                                st.write(f"• **{wrow['filename']}** - {wrow['created_at']}")
                                if wrow.get('ocr_text') and str(wrow['ocr_text']) != 'None':
                                    st.write(f"  OCR: {str(wrow['ocr_text'])[:50]}...")
                else:
                    st.info("No window information available")
                
                # Raw data view
                if show_raw_data:
                    st.markdown("---")
                    st.subheader("📊 Raw Data")
                    st.dataframe(df, use_container_width=True)
                    
                    # Export option
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"autotasktracker_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
            else:
                st.warning(f"⚠️ No screenshots found for {time_filter}")
                st.info("💡 Make sure AutoTaskTracker is capturing screenshots and processing them.")
                
                # Show some debugging info
                with st.expander("🔍 Debug Information"):
                    st.write("**Query executed:**")
                    st.code(query)
                    if params:
                        st.write("**Parameters:**", params)
                    
                    # Check if tables exist
                    with conn.cursor() as debug_cursor:
                        debug_cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                        tables = [row[0] for row in debug_cursor.fetchall()]
                        st.write("**Available tables:**", tables)
                        
                        if 'entities' in tables:
                            debug_cursor.execute("SELECT COUNT(*) FROM entities")
                            entity_count = debug_cursor.fetchone()[0]
                            st.write(f"**Total entities:** {entity_count}")
    
except Exception as e:
    st.error(f"❌ Database Error: {e}")
    st.sidebar.error("❌ Database Connection Failed")
    
    # Show debugging information
    with st.expander("🔍 Error Details"):
        st.code(str(e))
        st.write("**Database URL:**", DATABASE_URL)

# Auto-refresh
if st.sidebar.button("🔄 Refresh"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.write("**AutoTaskTracker** v2.0")
st.sidebar.write("PostgreSQL Backend")

# Footer
st.markdown("---")
st.write("🎯 **PostgreSQL Implementation Complete** - All data is now stored and retrieved from PostgreSQL database")