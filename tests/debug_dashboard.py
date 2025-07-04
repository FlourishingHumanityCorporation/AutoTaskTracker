#!/usr/bin/env python3
"""
Quick debug dashboard to show exactly what data we have
"""

import streamlit as st
from autotasktracker import DatabaseManager, extract_window_title, ActivityCategorizer
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Debug Dashboard", layout="wide")

st.title("🔧 Debug Dashboard - What Data Do We Have?")

db = DatabaseManager()

# Get all recent data
st.subheader("Raw Data Inspection")
df_all = db.fetch_tasks(limit=50)

st.write(f"**Total records found:** {len(df_all)}")

if not df_all.empty:
    # Process data
    df_all['window_title'] = df_all['active_window'].apply(extract_window_title)
    df_all['category'] = df_all['window_title'].apply(lambda x: ActivityCategorizer.categorize(x) if x else '📋 Other')
    df_all['created_at'] = pd.to_datetime(df_all['created_at'])
    
    # Show date range
    st.write(f"**Date range:** {df_all['created_at'].min()} to {df_all['created_at'].max()}")
    
    # Group by date
    st.subheader("Records by Date")
    date_counts = df_all.groupby(df_all['created_at'].dt.date).size()
    for date, count in date_counts.items():
        st.write(f"- **{date}**: {count} records")
    
    # Show sample data
    st.subheader("Sample Activities")
    for idx, row in df_all.head(10).iterrows():
        with st.expander(f"{row['created_at']} - {row['window_title'][:50]}..."):
            st.write(f"**Window:** {row['window_title']}")
            st.write(f"**Category:** {row['category']}")
            st.write(f"**File:** {row['filepath']}")
            if row['ocr_text']:
                st.write("**Has OCR data:** Yes")
            else:
                st.write("**Has OCR data:** No")

    # Test grouping
    st.subheader("Task Grouping Test")
    
    # Simple grouping by window title
    df_grouped = df_all.groupby(['window_title', 'category']).agg({
        'created_at': ['min', 'max', 'count']
    }).reset_index()
    
    df_grouped.columns = ['Window Title', 'Category', 'Start Time', 'End Time', 'Screenshot Count']
    df_grouped['Duration (min)'] = (
        pd.to_datetime(df_grouped['End Time']) - pd.to_datetime(df_grouped['Start Time'])
    ).dt.total_seconds() / 60
    
    # Sort by duration
    df_grouped = df_grouped.sort_values('Duration (min)', ascending=False)
    
    st.write("**Discovered Tasks (grouped by window title):**")
    st.dataframe(df_grouped[df_grouped['Duration (min)'] > 0.5], use_container_width=True)
    
    # Show categories
    st.subheader("Category Distribution")
    category_counts = df_all['category'].value_counts()
    st.bar_chart(category_counts)
    
else:
    st.error("No data found!")
    st.write("Make sure Memos is running: `memos start`")