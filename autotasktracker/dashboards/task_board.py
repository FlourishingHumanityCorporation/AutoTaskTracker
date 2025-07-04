"""
Streamlit dashboard for AutoTaskTracker - Task Board view.
"""

import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime, timedelta
import json

# Import from our new package structure
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


def init_session_state():
    """Initialize session state variables."""
    if 'time_filter' not in st.session_state:
        st.session_state.time_filter = "Today"
    if 'show_screenshots' not in st.session_state:
        st.session_state.show_screenshots = config.SHOW_SCREENSHOTS
    if 'group_interval' not in st.session_state:
        st.session_state.group_interval = config.GROUP_INTERVAL_MINUTES


def group_tasks_by_time(df: pd.DataFrame, interval_minutes: int = None) -> list:
    """Group similar tasks that occur within a time interval."""
    if interval_minutes is None:
        interval_minutes = st.session_state.get('group_interval', config.GROUP_INTERVAL_MINUTES)
    
    if df.empty:
        return []
    
    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.sort_values('created_at')
    
    groups = []
    current_group = []
    current_task = None
    current_category = None
    
    for idx, row in df.iterrows():
        # Extract task and category for current row
        task_title = extract_task_summary(row['ocr_text'], row['active_window'])
        window_title = extract_window_title(row['active_window'])
        category = ActivityCategorizer.categorize(window_title, row['ocr_text'])
        
        if not current_group:
            current_group.append(row)
            current_task = task_title
            current_category = category
        else:
            time_diff = (row['created_at'] - current_group[-1]['created_at']).total_seconds() / 60
            
            # More intelligent grouping - same app/project should group together
            same_context = False
            if time_diff <= interval_minutes:
                # Check if it's the same category
                if category == current_category:
                    same_context = True
                # Also group if it's the same project/file (check for common words)
                elif current_task and task_title:
                    # Extract meaningful words from both tasks
                    current_words = set(word for word in current_task.lower().split() if len(word) > 4)
                    new_words = set(word for word in task_title.lower().split() if len(word) > 4)
                    # If they share significant words, group them
                    if current_words and new_words and len(current_words & new_words) > 0:
                        same_context = True
            
            if same_context:
                current_group.append(row)
            else:
                groups.append(current_group)
                current_group = [row]
                current_task = task_title
                current_category = category
    
    if current_group:
        groups.append(current_group)
    
    return groups


def display_task_group(group: list, group_idx: int):
    """Display a group of related tasks."""
    if not group:
        return
    
    # Get the primary task for this group
    primary_row = group[0]
    window_title = extract_window_title(primary_row['active_window'])
    task_title = extract_task_summary(primary_row['ocr_text'], primary_row['active_window'])
    category = ActivityCategorizer.categorize(window_title, primary_row['ocr_text'])
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"{category} | {task_title}")
            
            # Time information
            start_time = pd.to_datetime(group[0]['created_at'])
            end_time = pd.to_datetime(group[-1]['created_at'])
            duration = (end_time - start_time).total_seconds() / 60
            
            if duration > 1:
                st.caption(f"⏱️ {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} ({duration:.0f} minutes, {len(group)} screenshots)")
            else:
                st.caption(f"⏱️ {start_time.strftime('%H:%M:%S')}")
            
            # Extract and show subtasks from group
            subtasks = []
            seen_tasks = {task_title}
            
            # Try to get task extractor for advanced subtask extraction
            try:
                from autotasktracker.core.task_extractor import get_task_extractor
                extractor = get_task_extractor()
                
                for row in group[1:]:  # Skip first as it's the primary
                    # Get task for this row
                    row_task = extract_task_summary(row['ocr_text'], row['active_window'])
                    if row_task and row_task not in seen_tasks:
                        seen_tasks.add(row_task)
                        subtasks.append(row_task)
                    
                    # Extract actions from OCR
                    if row['ocr_text']:
                        ocr_subtasks = extractor.extract_subtasks_from_ocr(row['ocr_text'])
                        for subtask in ocr_subtasks:
                            if subtask not in seen_tasks:
                                seen_tasks.add(subtask)
                                subtasks.append(subtask)
            except ImportError:
                # Fallback to basic subtask extraction
                for row in group[1:]:
                    row_task = extract_task_summary(row['ocr_text'], row['active_window'])
                    if row_task and row_task not in seen_tasks and row_task != task_title:
                        seen_tasks.add(row_task)
                        subtasks.append(row_task)
            
            # Display subtasks if any
            if subtasks:
                st.markdown("**Also worked on:**")
                for subtask in subtasks[:5]:  # Show max 5 subtasks
                    st.markdown(f"• {subtask}")
            
            # Show OCR text preview in expander
            if primary_row['ocr_text']:
                with st.expander("📝 View captured text"):
                    try:
                        # Parse OCR JSON and display readable text
                        ocr_data = json.loads(primary_row['ocr_text']) if isinstance(primary_row['ocr_text'], str) else primary_row['ocr_text']
                        if isinstance(ocr_data, list):
                            readable_texts = []
                            for item in ocr_data[:20]:  # First 20 items
                                if isinstance(item, list) and len(item) >= 2:
                                    text_data = item[1]
                                    if isinstance(text_data, tuple) and len(text_data) >= 2:
                                        text_content = text_data[0].strip()
                                        if text_content:
                                            readable_texts.append(text_content)
                            
                            if readable_texts:
                                st.text('\n'.join(readable_texts))
                            else:
                                st.text("No readable text found")
                        else:
                            st.text(str(primary_row['ocr_text'])[:500])
                    except:
                        st.text(str(primary_row['ocr_text'])[:500])
        
        with col2:
            # Show screenshot thumbnail if enabled
            if st.session_state.show_screenshots and primary_row['filepath']:
                try:
                    img_path = primary_row['filepath']
                    if os.path.exists(img_path):
                        img = Image.open(img_path)
                        # Create thumbnail
                        img.thumbnail((config.MAX_SCREENSHOT_SIZE, config.MAX_SCREENSHOT_SIZE))
                        st.image(img, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not load image: {e}")
        
        st.divider()


def main():
    """Main dashboard function."""
    # Page config
    st.set_page_config(
        layout="wide", 
        page_title="My AI Task Board", 
        page_icon="✅"
    )
    
    # Initialize session state
    init_session_state()
    
    # Auto-refresh
    st_autorefresh = st.empty()
    with st_autorefresh.container():
        st.markdown(
            f'<meta http-equiv="refresh" content="{config.AUTO_REFRESH_SECONDS}">',
            unsafe_allow_html=True
        )
    
    # Header with live indicator
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("✅ My AI-Powered Daily Task Board")
        st.write("A passive and engaging look at what you've accomplished today.")
    with col2:
        st.markdown("<div style='text-align: right; padding-top: 20px;'>🟢 <b>LIVE</b></div>", unsafe_allow_html=True)
        st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    
    # Sidebar controls
    st.sidebar.header("🎛️ Controls")
    
    # Database connection and status
    db_manager = DatabaseManager(config.DB_PATH)
    if db_manager.test_connection():
        today_count = db_manager.get_screenshot_count()
        st.sidebar.info(f"📸 {today_count} screenshots today")
    else:
        st.sidebar.error("❌ Database connection failed")
        st.error("Cannot connect to database. Is Memos running? Start with: memos start")
        return
    
    # Time filter
    time_filter = st.sidebar.selectbox(
        "Time Range",
        ["Last 15 Minutes", "Last Hour", "Today", "Last 24 Hours", "Last 7 Days", "All Time"],
        index=2,
        key='time_filter'
    )
    
    # Show screenshots toggle
    st.session_state.show_screenshots = st.sidebar.checkbox(
        "Show Screenshots", 
        value=st.session_state.show_screenshots,
        help="Toggle screenshot thumbnails for faster loading"
    )
    
    # Group interval slider
    st.session_state.group_interval = st.sidebar.slider(
        "Group Similar Tasks (minutes)",
        min_value=1,
        max_value=30,
        value=st.session_state.group_interval,
        help="Group activities within this time window"
    )
    
    # Fetch and display tasks
    with st.spinner("Loading activities..."):
        tasks_df = db_manager.fetch_tasks_by_time_filter(
            time_filter, 
            limit=config.DEFAULT_TASK_LIMIT
        )
    
    if not tasks_df.empty:
        # Activity Summary
        st.header("📊 Activity Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Activities", len(tasks_df))
        with col2:
            # Count unique window titles
            unique_windows = tasks_df['active_window'].apply(extract_window_title).nunique()
            st.metric("Unique Applications", unique_windows)
        with col3:
            time_range = (pd.to_datetime(tasks_df['created_at'].max()) - pd.to_datetime(tasks_df['created_at'].min()))
            hours = time_range.total_seconds() / 3600
            st.metric("Time Span", f"{hours:.1f} hours")
        with col4:
            avg_per_hour = len(tasks_df) / max(hours, 1)
            st.metric("Avg Screenshots/Hour", f"{avg_per_hour:.1f}")
        
        # Activity Stream
        st.header("📋 Activity Stream")
        
        # Group tasks by time intervals
        task_groups = group_tasks_by_time(tasks_df)
        
        # Display task groups
        for group_idx, group in enumerate(task_groups):
            display_task_group(group, group_idx)
    else:
        st.info("🔍 No activities found for the selected time range.")
        st.write("Make sure Memos is running and capturing screenshots.")


if __name__ == "__main__":
    main()