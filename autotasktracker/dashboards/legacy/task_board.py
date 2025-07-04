import streamlit as st
import sqlite3
import pandas as pd
import os
from PIL import Image
from datetime import datetime, timedelta
import json

# --- Configuration ---
# Path to the Pensieve database. Adjust if your home directory is different.
HOME_DIR = os.path.expanduser("~")
PENSIEVE_DB_PATH = os.path.join(HOME_DIR, '.memos', 'database.db')
SCREENSHOTS_DIR = os.path.join(HOME_DIR, '.memos', 'screenshots')

# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="My AI Task Board", page_icon="✅")

# Auto-refresh every 30 seconds
st_autorefresh = st.empty()
with st_autorefresh.container():
    st.markdown(
        '<meta http-equiv="refresh" content="30">',
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

# Sidebar filters with session state
st.sidebar.header("🎛️ Controls")

# Initialize session state
if 'time_filter' not in st.session_state:
    st.session_state.time_filter = "Today"
    
# Show data status
conn = get_db_connection()
if conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM entities WHERE file_type_group = 'image' AND date(created_at, 'localtime') = date('now', 'localtime')")
    today_count = cursor.fetchone()[0]
    conn.close()
    st.sidebar.info(f"📸 {today_count} screenshots today")
if 'show_screenshots' not in st.session_state:
    st.session_state.show_screenshots = True
if 'group_interval' not in st.session_state:
    st.session_state.group_interval = 5

time_filter = st.sidebar.selectbox(
    "Time Range",
    ["Last 15 Minutes", "Last Hour", "Today", "Last 24 Hours", "Last 7 Days", "All Time"],
    index=2,
    key='time_filter'
)

st.session_state.show_screenshots = st.sidebar.checkbox(
    "Show Screenshots", 
    value=st.session_state.show_screenshots,
    help="Toggle screenshot thumbnails for faster loading"
)

st.session_state.group_interval = st.sidebar.slider(
    "Group Similar Tasks (minutes)",
    min_value=1,
    max_value=30,
    value=st.session_state.group_interval,
    help="Group activities within this time window"
)

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(f'file:{PENSIEVE_DB_PATH}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        st.error(f"Error connecting to the database: {e}")
        st.info("Is the Pensieve service running? You can start it with 'memos start'.")
        return None

# --- Data Fetching ---
@st.cache_data(ttl=60) # Cache data for 60 seconds
def fetch_tasks(time_filter, limit=100):
    """Fetches the latest processed screenshots from the Pensieve database."""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    # Calculate time filter
    now = datetime.now()
    if time_filter == "Last 15 Minutes":
        time_threshold = now - timedelta(minutes=15)
    elif time_filter == "Last Hour":
        time_threshold = now - timedelta(hours=1)
    elif time_filter == "Today":
        time_threshold = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "Last 24 Hours":
        time_threshold = now - timedelta(days=1)
    elif time_filter == "Last 7 Days":
        time_threshold = now - timedelta(days=7)
    else:  # All Time
        time_threshold = datetime(2000, 1, 1)
    
    query = """
    SELECT
        e.id,
        e.filepath,
        e.filename,
        datetime(e.created_at, 'localtime') as created_at,
        e.file_created_at,
        e.last_scan_at,
        me.value as ocr_text,
        me2.value as active_window
    FROM
        entities e
        LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
    WHERE
        e.file_type_group = 'image'
        AND datetime(e.created_at, 'localtime') >= ?
    ORDER BY
        e.created_at DESC
    LIMIT ?
    """
    try:
        df = pd.read_sql_query(query, conn, params=(time_threshold.isoformat(), limit))
        conn.close()
        return df
    except pd.io.sql.DatabaseError as e:
        st.error(f"Error querying the database: {e}")
        st.info("The database schema might be different or the table doesn't exist yet. Let Pensieve run for a bit.")
        return pd.DataFrame()

# --- Helper Functions ---
def categorize_activity(window_title, ocr_text):
    """Categorize activity based on window title and OCR content."""
    if not window_title:
        return "Other"
    
    window_lower = window_title.lower()
    
    # Development/Coding
    if any(keyword in window_lower for keyword in ['code', 'vscode', 'vim', 'emacs', 'sublime', 'atom', 'pycharm', 'intellij', 'terminal', 'iterm']):
        return "🧑‍💻 Coding"
    
    # Communication
    if any(keyword in window_lower for keyword in ['mail', 'gmail', 'outlook', 'slack', 'teams', 'discord', 'chat', 'messages']):
        return "💬 Communication"
    
    # Browsing/Research
    if any(keyword in window_lower for keyword in ['chrome', 'firefox', 'safari', 'edge', 'browser', 'google', 'stack overflow']):
        return "🔍 Research/Browsing"
    
    # Documentation
    if any(keyword in window_lower for keyword in ['word', 'docs', 'pages', 'notion', 'obsidian', 'readme']):
        return "📝 Documentation"
    
    # Meetings
    if any(keyword in window_lower for keyword in ['zoom', 'meet', 'webex', 'skype']):
        return "🎥 Meetings"
    
    return "📋 Other"

def extract_task_from_ocr(ocr_text, active_window):
    """Extract a meaningful task description from OCR text and window title."""
    if not ocr_text and not active_window:
        return "Unknown Activity"
    
    # If we have an active window, use it as the primary task identifier
    if active_window:
        try:
            window_data = json.loads(active_window) if isinstance(active_window, str) else active_window
            if isinstance(window_data, dict) and 'title' in window_data:
                return window_data['title']
        except:
            pass
        return str(active_window)
    
    # Otherwise, try to extract something meaningful from OCR text
    if ocr_text:
        try:
            # OCR result is JSON format with bounding boxes and text
            ocr_data = json.loads(ocr_text) if isinstance(ocr_text, str) else ocr_text
            if isinstance(ocr_data, list):
                # Extract all recognized text with confidence > 0.5
                text_parts = []
                for item in ocr_data:
                    if isinstance(item, dict) and 'rec_txt' in item and 'score' in item:
                        if item['score'] > 0.5:
                            text_parts.append(item['rec_txt'])
                
                # Join and create a summary
                if text_parts:
                    combined_text = ' '.join(text_parts[:10])  # First 10 high-confidence texts
                    return combined_text[:100] + "..." if len(combined_text) > 100 else combined_text
        except:
            # Fallback to simple text handling
            first_line = str(ocr_text).split('\n')[0].strip()
            if first_line:
                return first_line[:100] + "..." if len(first_line) > 100 else first_line
    
    return "Activity Captured"

def group_tasks_by_time(df, interval_minutes=None):
    if interval_minutes is None:
        interval_minutes = st.session_state.get('group_interval', 5)
    """Group similar tasks that occur within a time interval."""
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
            if time_diff <= interval_minutes:
                current_group.append(row)
            else:
                groups.append(current_group)
                current_group = [row]
    
    if current_group:
        groups.append(current_group)
    
    return groups

# --- Main App Logic ---
tasks_df = fetch_tasks(time_filter)

if not tasks_df.empty:
    st.header("📊 Activity Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Activities", len(tasks_df))
    with col2:
        unique_windows = tasks_df['active_window'].nunique()
        st.metric("Unique Applications", unique_windows)
    with col3:
        time_range = (pd.to_datetime(tasks_df['created_at'].max()) - pd.to_datetime(tasks_df['created_at'].min()))
        hours = time_range.total_seconds() / 3600
        st.metric("Time Span", f"{hours:.1f} hours")
    with col4:
        avg_per_hour = len(tasks_df) / max(hours, 1)
        st.metric("Avg Screenshots/Hour", f"{avg_per_hour:.1f}")
    
    st.header("📋 Activity Stream")
    
    # Group tasks by time intervals
    task_groups = group_tasks_by_time(tasks_df)
    
    # Display task groups
    for group_idx, group in enumerate(task_groups):
        if not group:
            continue
            
        # Get the primary task for this group (most common window or first entry)
        primary_row = group[0]
        task_title = extract_task_from_ocr(primary_row['ocr_text'], primary_row['active_window'])
        category = categorize_activity(task_title, primary_row['ocr_text'])
        
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
                
                # Show OCR text preview in expander
                if primary_row['ocr_text']:
                    with st.expander("📝 View captured text"):
                        try:
                            # Parse OCR JSON and display readable text
                            ocr_data = json.loads(primary_row['ocr_text']) if isinstance(primary_row['ocr_text'], str) else primary_row['ocr_text']
                            if isinstance(ocr_data, list):
                                readable_texts = []
                                for item in ocr_data:
                                    if isinstance(item, dict) and 'rec_txt' in item and 'score' in item:
                                        if item['score'] > 0.3:  # Include lower confidence for preview
                                            readable_texts.append(item['rec_txt'])
                                
                                if readable_texts:
                                    # Group texts into lines for better readability
                                    st.text(' '.join(readable_texts))
                                else:
                                    st.text("No readable text extracted")
                            else:
                                st.text(str(primary_row['ocr_text'])[:1000])
                        except:
                            st.text(str(primary_row['ocr_text'])[:1000] + "..." if len(str(primary_row['ocr_text'])) > 1000 else primary_row['ocr_text'])
            
            with col2:
                if st.session_state.show_screenshots:
                    # Display the screenshot thumbnail
                    screenshot_path = primary_row['filepath']
                    if screenshot_path and os.path.exists(screenshot_path):
                        try:
                            image = Image.open(screenshot_path)
                            # Create thumbnail
                            image.thumbnail((400, 300))
                            st.image(image, caption=f"Screenshot {group_idx + 1}", use_column_width=True)
                        except Exception as e:
                            st.warning(f"Could not load image: {e}")
                    else:
                        st.info("Screenshot not available")
                else:
                    # Show activity summary instead
                    st.metric(
                        "Activity Duration",
                        f"{duration:.0f} min" if duration > 1 else "< 1 min",
                        delta=f"{len(group)} captures"
                    )
            
            st.divider()
    
    # Activity Timeline
    st.header("📈 Activity Timeline")
    
    # Prepare data for timeline
    timeline_df = tasks_df.copy()
    timeline_df['created_at'] = pd.to_datetime(timeline_df['created_at'])
    timeline_df['hour'] = timeline_df['created_at'].dt.hour
    
    # Count activities per hour
    hourly_counts = timeline_df.groupby('hour').size().reset_index(name='count')
    
    # Create a bar chart
    st.bar_chart(hourly_counts.set_index('hour')['count'])
    
else:
    st.info("🔄 Waiting for task data from Pensieve... Work for a few minutes and then refresh this page.")
    st.balloons()

# Status indicator
st.sidebar.markdown("---")
st.sidebar.header("📊 System Status")

# Check if memos is running
try:
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'memos'], capture_output=True, text=True)
    if result.returncode == 0:
        st.sidebar.success("✅ Memos is running")
    else:
        st.sidebar.error("❌ Memos is not running")
        if st.sidebar.button("Start Memos"):
            subprocess.run(['memos', 'start'], capture_output=True)
            st.rerun()
except:
    st.sidebar.warning("⚠️ Cannot check memos status")

# Storage info
try:
    screenshots_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                          for dirpath, dirnames, filenames in os.walk(SCREENSHOTS_DIR)
                          for filename in filenames) / (1024 * 1024)  # MB
    st.sidebar.metric("Storage Used", f"{screenshots_size:.1f} MB")
except:
    pass

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Powered by Pensieve/Memos")
st.sidebar.caption(f"Database: {PENSIEVE_DB_PATH}")
st.sidebar.caption(f"Screenshots: {SCREENSHOTS_DIR}")