"""
Enhanced Task Board Dashboard for AutoTaskTracker
Combines the visual appeal of the original with the refactored architecture
"""

import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime, timedelta
import json

# Import from our package
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

# Custom CSS for better styling
def inject_custom_css():
    st.markdown("""
    <style>
    /* Main container styling */
    .main {
        padding-top: 1rem;
    }
    
    /* Task cards */
    .task-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    
    .task-card.coding {
        border-left-color: #2ca02c;
    }
    
    .task-card.ai-tools {
        border-left-color: #ff7f0e;
    }
    
    .task-card.communication {
        border-left-color: #d62728;
    }
    
    .task-card.research {
        border-left-color: #9467bd;
    }
    
    /* Live indicator pulse */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .live-indicator {
        animation: pulse 2s infinite;
        color: #2ca02c;
        font-weight: bold;
    }
    
    /* Screenshot thumbnails */
    .screenshot-thumb {
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }
    
    .screenshot-thumb:hover {
        transform: scale(1.05);
    }
    
    /* Metrics cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    
    /* Time badges */
    .time-badge {
        background-color: #e9ecef;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        display: inline-block;
        margin-right: 0.5rem;
    }
    
    /* Category badges */
    .category-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'time_filter' not in st.session_state:
        st.session_state.time_filter = "Today"
    if 'show_screenshots' not in st.session_state:
        st.session_state.show_screenshots = True
    if 'group_interval' not in st.session_state:
        st.session_state.group_interval = 5


def format_duration(minutes):
    """Format duration in a human-readable way."""
    if minutes < 1:
        return "< 1 min"
    elif minutes < 60:
        return f"{int(minutes)} min"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{hours}h"


def get_category_color(category):
    """Get color for category badges."""
    colors = {
        '🧑‍💻 Coding': '#2ca02c',
        '🤖 AI Tools': '#ff7f0e',
        '💬 Communication': '#d62728',
        '🔍 Research/Browsing': '#9467bd',
        '📝 Documentation': '#8c564b',
        '🎥 Meetings': '#e377c2',
        '📊 Data Analysis': '#7f7f7f',
        '🎮 Entertainment': '#bcbd22',
        '📋 Other': '#17becf'
    }
    return colors.get(category, '#666666')


def group_tasks_by_time(df, interval_minutes=None):
    """Group similar tasks that occur within a time interval."""
    if interval_minutes is None:
        interval_minutes = st.session_state.get('group_interval', 5)
    
    if df.empty:
        return []
    
    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.sort_values('created_at')
    
    groups = []
    current_group = []
    
    for idx, row in df.iterrows():
        if not current_group:
            current_group.append(row)
        else:
            time_diff = (row['created_at'] - current_group[-1]['created_at']).total_seconds() / 60
            
            # Check if it's the same task or within time interval
            same_task = (extract_task_summary(row['ocr_text'], row['active_window']) == 
                        extract_task_summary(current_group[0]['ocr_text'], current_group[0]['active_window']))
            
            if time_diff <= interval_minutes and (same_task or time_diff <= 2):
                current_group.append(row)
            else:
                groups.append(current_group)
                current_group = [row]
    
    if current_group:
        groups.append(current_group)
    
    return groups


def display_task_card(group, group_idx):
    """Display a beautiful task card for a group of activities."""
    if not group:
        return
    
    primary_row = group[0]
    window_title = extract_window_title(primary_row['active_window'])
    task_title = extract_task_summary(primary_row['ocr_text'], primary_row['active_window'])
    category = ActivityCategorizer.categorize(window_title, primary_row['ocr_text'])
    
    # Determine card class based on category
    category_class = category.split()[1].lower().replace('/', '-') if len(category.split()) > 1 else 'other'
    
    # Create card container
    card_html = f'<div class="task-card {category_class}">'
    st.markdown(card_html, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Category and title
            category_color = get_category_color(category)
            st.markdown(
                f'<span class="category-badge" style="background-color: {category_color}; color: white;">{category}</span>',
                unsafe_allow_html=True
            )
            st.markdown(f"### {task_title[:80]}{'...' if len(task_title) > 80 else ''}")
            
            # Time information
            start_time = pd.to_datetime(group[0]['created_at'])
            end_time = pd.to_datetime(group[-1]['created_at'])
            duration = (end_time - start_time).total_seconds() / 60
            
            time_info = f'<span class="time-badge">🕐 {start_time.strftime("%H:%M")}'
            if duration > 1:
                time_info += f' - {end_time.strftime("%H:%M")}</span>'
                time_info += f'<span class="time-badge">⏱️ {format_duration(duration)}</span>'
            else:
                time_info += '</span>'
            time_info += f'<span class="time-badge">📸 {len(group)} screenshots</span>'
            
            st.markdown(time_info, unsafe_allow_html=True)
            
            # OCR text preview
            if primary_row['ocr_text']:
                with st.expander("📝 View captured text", expanded=False):
                    try:
                        ocr_data = json.loads(primary_row['ocr_text']) if isinstance(primary_row['ocr_text'], str) else primary_row['ocr_text']
                        if isinstance(ocr_data, list):
                            readable_texts = []
                            for item in ocr_data[:20]:
                                if isinstance(item, list) and len(item) >= 2:
                                    text_data = item[1]
                                    if isinstance(text_data, tuple) and len(text_data) >= 2:
                                        text_content = text_data[0].strip()
                                        confidence = text_data[1]
                                        if text_content and confidence > 0.8:
                                            readable_texts.append(text_content)
                            
                            if readable_texts:
                                # Group related text
                                st.text('\n'.join(readable_texts[:10]))
                            else:
                                st.text("No high-confidence text found")
                        else:
                            st.text(str(primary_row['ocr_text'])[:500])
                    except:
                        st.text("Unable to parse OCR data")
        
        with col2:
            # Progress indicator
            if duration > 30:  # Long session
                st.markdown("🔥 **Deep Focus**")
            elif duration > 10:
                st.markdown("⚡ **Focused**")
            else:
                st.markdown("👀 **Quick Task**")
        
        with col3:
            # Screenshot thumbnail
            if st.session_state.show_screenshots and primary_row['filepath']:
                try:
                    img_path = primary_row['filepath']
                    if os.path.exists(img_path):
                        img = Image.open(img_path)
                        img.thumbnail((200, 200))
                        st.image(img, use_container_width=True, caption="Screenshot")
                except:
                    st.empty()
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_metrics_dashboard(df):
    """Display beautiful metrics dashboard."""
    st.markdown("## 📊 Today's Activity Dashboard")
    
    # Calculate metrics
    total_screenshots = len(df)
    if total_screenshots > 0:
        df['created_at'] = pd.to_datetime(df['created_at'])
        time_range = df['created_at'].max() - df['created_at'].min()
        total_hours = time_range.total_seconds() / 3600
        
        # Extract categories
        df['window_title'] = df['active_window'].apply(extract_window_title)
        df['category'] = df['window_title'].apply(lambda x: ActivityCategorizer.categorize(x) if x else '📋 Other')
        
        unique_apps = df['window_title'].nunique()
        top_category = df['category'].value_counts().index[0] if not df['category'].empty else "N/A"
        
        # Display metrics in beautiful cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 1.5rem; border-radius: 10px; text-align: center;">
                <h2 style="margin: 0; color: white;">""" + str(total_screenshots) + """</h2>
                <p style="margin: 0; opacity: 0.9;">Total Activities</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        color: white; padding: 1.5rem; border-radius: 10px; text-align: center;">
                <h2 style="margin: 0; color: white;">{unique_apps}</h2>
                <p style="margin: 0; opacity: 0.9;">Applications</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                        color: white; padding: 1.5rem; border-radius: 10px; text-align: center;">
                <h2 style="margin: 0; color: white;">{total_hours:.1f}h</h2>
                <p style="margin: 0; opacity: 0.9;">Time Tracked</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                        color: white; padding: 1.5rem; border-radius: 10px; text-align: center;">
                <h2 style="margin: 0; color: white;">{top_category}</h2>
                <p style="margin: 0; opacity: 0.9;">Top Category</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Category breakdown
        st.markdown("### 🎯 Activity Breakdown")
        category_counts = df['category'].value_counts()
        
        # Create a beautiful bar chart using columns
        for category, count in category_counts.head(5).items():
            percentage = (count / total_screenshots) * 100
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                        <span style="font-weight: 600;">{category}</span>
                    </div>
                    <div style="background-color: #e9ecef; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="background-color: {get_category_color(category)}; 
                                    width: {percentage}%; height: 100%; 
                                    transition: width 0.3s ease;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{count}** ({percentage:.1f}%)")


def main():
    """Main dashboard function."""
    # Page config
    st.set_page_config(
        layout="wide",
        page_title="My AI Task Board",
        page_icon="✅"
    )
    
    # Inject custom CSS
    inject_custom_css()
    
    # Initialize session state
    init_session_state()
    
    # Auto-refresh
    st.markdown(
        f'<meta http-equiv="refresh" content="{config.AUTO_REFRESH_SECONDS}">',
        unsafe_allow_html=True
    )
    
    # Header with live indicator
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("# ✅ My AI-Powered Daily Task Board")
        st.markdown("*A passive and engaging look at what you've accomplished today.*")
    with col2:
        st.markdown(
            f'<div style="text-align: right; padding-top: 20px;">'
            f'<span class="live-indicator">🟢 LIVE</span><br>'
            f'<small>Last update: {datetime.now().strftime("%H:%M:%S")}</small>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # Sidebar
    st.sidebar.markdown("## 🎛️ Controls")
    
    # Database connection
    db_manager = DatabaseManager(config.DB_PATH)
    if db_manager.test_connection():
        today_count = db_manager.get_screenshot_count()
        st.sidebar.success(f"📸 **{today_count}** screenshots today")
    else:
        st.sidebar.error("❌ Database connection failed")
        st.error("Cannot connect to database. Is Memos running? Start with: `memos start`")
        return
    
    # Time filter
    time_filter = st.sidebar.selectbox(
        "⏰ Time Range",
        ["Last 15 Minutes", "Last Hour", "Today", "Last 24 Hours", "Last 7 Days", "All Time"],
        index=2,
        key='time_filter'
    )
    
    # Show screenshots toggle
    st.session_state.show_screenshots = st.sidebar.checkbox(
        "🖼️ Show Screenshots",
        value=st.session_state.show_screenshots,
        help="Toggle screenshot thumbnails for faster loading"
    )
    
    # Group interval
    st.session_state.group_interval = st.sidebar.slider(
        "🔗 Group Similar Tasks (minutes)",
        min_value=1,
        max_value=30,
        value=st.session_state.group_interval,
        help="Group activities within this time window"
    )
    
    # Add refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()
    
    # Fetch data
    with st.spinner("Loading your activities..."):
        tasks_df = db_manager.fetch_tasks_by_time_filter(
            time_filter,
            limit=config.DEFAULT_TASK_LIMIT
        )
    
    if not tasks_df.empty:
        # Display metrics dashboard
        display_metrics_dashboard(tasks_df)
        
        # Activity stream
        st.markdown("## 📋 Activity Stream")
        st.markdown("---")
        
        # Group tasks
        task_groups = group_tasks_by_time(tasks_df)
        
        # Display task groups
        for group_idx, group in enumerate(task_groups):
            display_task_card(group, group_idx)
        
        # Footer
        st.markdown("---")
        st.markdown(
            f'<div style="text-align: center; color: #666; padding: 2rem;">'
            f'<small>AutoTaskTracker is continuously monitoring your productivity. '
            f'Data is stored locally and processed with AI for insights.</small>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        # Empty state
        st.markdown("""
        <div style="text-align: center; padding: 4rem;">
            <h2>🔍 No activities found</h2>
            <p>No activities recorded for the selected time range.</p>
            <p>Make sure Memos is running and capturing screenshots.</p>
            <br>
            <p><code>memos ps</code> - Check status</p>
            <p><code>memos start</code> - Start capturing</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()