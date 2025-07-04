"""
Achievement Board - The Ultimate AutoTaskTracker Dashboard
Shows discovered tasks as achievements and insights
"""

import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime, timedelta
import json
import plotly.graph_objects as go
from collections import defaultdict

from autotasktracker import (
    DatabaseManager,
    ActivityCategorizer,
    extract_task_summary,
    extract_window_title,
    Config,
    get_config
)
from autotasktracker.utils.streamlit_helpers import configure_page

# Initialize configuration
config = get_config()

# Achievement levels based on focus time
ACHIEVEMENT_LEVELS = {
    'quick_win': {'min': 1, 'max': 10, 'emoji': '⚡', 'name': 'Quick Win', 'color': '#3498db'},
    'focused_work': {'min': 10, 'max': 30, 'emoji': '🎯', 'name': 'Focused Work', 'color': '#2ecc71'},
    'deep_dive': {'min': 30, 'max': 60, 'emoji': '🏊', 'name': 'Deep Dive', 'color': '#e74c3c'},
    'marathon': {'min': 60, 'max': 999, 'emoji': '🏃', 'name': 'Marathon Session', 'color': '#9b59b6'}
}

def inject_achievement_css():
    """Custom CSS for achievement-focused design"""
    st.markdown("""
    <style>
    /* Achievement Cards */
    .achievement-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        border: 2px solid transparent;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .achievement-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    }
    
    .achievement-card.deep-dive {
        border-color: #e74c3c;
        background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
    }
    
    .achievement-card.marathon {
        border-color: #9b59b6;
        background: linear-gradient(135deg, #f9f5ff 0%, #ffffff 100%);
    }
    
    /* Achievement Badge */
    .achievement-badge {
        position: absolute;
        top: 1rem;
        right: 1rem;
        font-size: 2rem;
        opacity: 0.2;
    }
    
    /* Task Title */
    .task-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 0.5rem;
        line-height: 1.3;
    }
    
    /* Progress Ring */
    .progress-ring {
        width: 80px;
        height: 80px;
        margin: 0 auto;
    }
    
    /* Insight Cards */
    .insight-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        height: 100%;
    }
    
    .insight-number {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
    }
    
    /* Daily Journey Timeline */
    .timeline-container {
        position: relative;
        padding: 2rem 0;
    }
    
    .timeline-line {
        position: absolute;
        left: 50%;
        top: 0;
        bottom: 0;
        width: 2px;
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    .timeline-item {
        position: relative;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
    }
    
    .timeline-dot {
        width: 20px;
        height: 20px;
        background: #667eea;
        border-radius: 50%;
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1;
    }
    
    /* Motivational Quote */
    .motivation-quote {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        font-size: 1.2rem;
        font-style: italic;
        margin: 2rem 0;
    }
    
    /* Focus Meter */
    .focus-meter {
        background: #f8f9fa;
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .focus-bar {
        height: 30px;
        background: #e9ecef;
        border-radius: 15px;
        overflow: hidden;
        position: relative;
    }
    
    .focus-fill {
        height: 100%;
        background: linear-gradient(90deg, #3498db 0%, #2ecc71 50%, #e74c3c 100%);
        transition: width 0.5s ease;
    }
    </style>
    """, unsafe_allow_html=True)

def format_task_as_achievement(task_title, duration_minutes, category):
    """Format a task as an achievement"""
    # Determine achievement level
    achievement_level = 'quick_win'
    for level, config in ACHIEVEMENT_LEVELS.items():
        if config['min'] <= duration_minutes <= config['max']:
            achievement_level = level
            break
    
    level_config = ACHIEVEMENT_LEVELS[achievement_level]
    
    # Smart task title extraction
    if ' - ' in task_title:
        parts = task_title.split(' - ')
        if len(parts) > 2:
            task_title = f"{parts[0]} - {parts[-1]}"
    
    # Remove common suffixes
    for suffix in [' - Google Chrome', ' - Visual Studio Code', ' - Mozilla Firefox']:
        task_title = task_title.replace(suffix, '')
    
    return {
        'title': task_title[:60] + '...' if len(task_title) > 60 else task_title,
        'duration': duration_minutes,
        'level': achievement_level,
        'emoji': level_config['emoji'],
        'level_name': level_config['name'],
        'color': level_config['color'],
        'category': category
    }

def calculate_insights(df):
    """Calculate meaningful insights from activities"""
    insights = {}
    
    if df.empty:
        return insights
    
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['hour'] = df['created_at'].dt.hour
    
    # Focus Score (based on session lengths)
    session_lengths = []
    current_start = df.iloc[0]['created_at']
    
    for i in range(1, len(df)):
        time_gap = (df.iloc[i]['created_at'] - df.iloc[i-1]['created_at']).total_seconds() / 60
        if time_gap > 10:  # New session
            session_length = (df.iloc[i-1]['created_at'] - current_start).total_seconds() / 60
            if session_length > 5:
                session_lengths.append(session_length)
            current_start = df.iloc[i]['created_at']
    
    # Focus score calculation
    if session_lengths:
        avg_session = sum(session_lengths) / len(session_lengths)
        long_sessions = sum(1 for s in session_lengths if s > 30)
        focus_score = min(100, int((avg_session / 30) * 50 + (long_sessions / len(session_lengths)) * 50 * 100))
    else:
        focus_score = 0
    
    insights['focus_score'] = focus_score
    insights['total_sessions'] = len(session_lengths)
    insights['longest_session'] = max(session_lengths) if session_lengths else 0
    
    # Most productive hour
    hour_counts = df['hour'].value_counts()
    insights['peak_hour'] = hour_counts.index[0] if not hour_counts.empty else 12
    
    # Task diversity
    unique_tasks = df['active_window'].apply(extract_window_title).nunique()
    insights['task_diversity'] = unique_tasks
    
    return insights

def create_daily_journey_timeline(task_groups):
    """Create a visual timeline of the day's journey"""
    timeline_html = '<div class="timeline-container"><div class="timeline-line"></div>'
    
    for i, (task, duration, start_time, category) in enumerate(task_groups[:10]):  # Top 10
        side = 'left' if i % 2 == 0 else 'right'
        
        timeline_html += f'''
        <div class="timeline-item" style="justify-content: {'flex-start' if side == 'left' else 'flex-end'};">
            <div class="timeline-dot"></div>
            <div style="{'margin-right' if side == 'left' else 'margin-left'}: 60%; 
                        text-align: {'right' if side == 'left' else 'left'};">
                <div style="font-weight: 600; color: #2c3e50;">{start_time.strftime("%I:%M %p")}</div>
                <div style="color: #7f8c8d; font-size: 0.9rem;">{task[:40]}...</div>
                <div style="color: #95a5a6; font-size: 0.8rem;">{int(duration)} min</div>
            </div>
        </div>
        '''
    
    timeline_html += '</div>'
    return timeline_html

def get_motivational_quote(focus_score, task_count):
    """Get a contextual motivational quote"""
    if focus_score >= 80:
        quotes = [
            "🔥 You're in the zone! Your focus today is extraordinary.",
            "🌟 Incredible concentration! You're mastering the art of deep work.",
            "💎 Your focus is diamond-sharp today. Keep this momentum!"
        ]
    elif focus_score >= 60:
        quotes = [
            "🎯 Great focus today! You're hitting your targets.",
            "⚡ Strong performance! Your productivity is impressive.",
            "🚀 You're flying high with focused work sessions!"
        ]
    elif task_count > 10:
        quotes = [
            "🌈 Wonderful variety in your work today!",
            "🎨 You're painting a diverse picture of productivity.",
            "🔄 Great job juggling multiple tasks effectively!"
        ]
    else:
        quotes = [
            "🌱 Every journey starts with a single step. Keep going!",
            "☀️ A new day brings new opportunities to shine.",
            "💪 You're building great habits, one task at a time."
        ]
    
    import random
    return random.choice(quotes)

def display_achievement_card(achievement_data, screenshot_path=None):
    """Display a task as an achievement card"""
    card_class = f"achievement-card {achievement_data['level']}"
    
    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
    st.markdown(f'<div class="achievement-badge">{achievement_data["emoji"]}</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f'<div class="task-title">{achievement_data["title"]}</div>', unsafe_allow_html=True)
        
        # Achievement details
        st.markdown(f"""
        **{achievement_data['level_name']}** • {achievement_data['category']} • {int(achievement_data['duration'])} minutes
        """)
        
        # Progress bar for this session
        progress = min(100, (achievement_data['duration'] / 60) * 100)
        st.progress(progress / 100)
    
    with col2:
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                img = Image.open(screenshot_path)
                img.thumbnail((150, 150))
                st.image(img, use_container_width=True)
            except (OSError, IOError, FileNotFoundError):
                pass
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    configure_page("Achievement Board - AutoTaskTracker", "🏆", "wide")
    
    inject_achievement_css()
    
    # Header will be set after we know which day we're showing
    header_placeholder = st.empty()
    
    # Database connection
    db = DatabaseManager(config.DB_PATH)
    if not db.test_connection():
        st.error("Cannot connect to database. Start Memos with: `memos start`")
        return
    
    # Get last 7 days of data to find the most recent day with activity
    week_ago = datetime.now() - timedelta(days=7)
    df_all = db.fetch_tasks(start_date=week_ago, limit=1000)
    
    if df_all.empty:
        st.info("No activities recorded yet. Make sure Memos is running!")
        return
    
    # Find the most recent date with data
    df_all['created_at'] = pd.to_datetime(df_all['created_at'])
    most_recent_date = df_all['created_at'].max().date()
    current_date = datetime.now().date()
    
    # Get that day's data
    date_start = datetime.combine(most_recent_date, datetime.min.time())
    date_end = datetime.combine(most_recent_date, datetime.max.time())
    df = db.fetch_tasks(start_date=date_start, end_date=date_end, limit=1000)
    
    # Show notice if not showing today's data
    if most_recent_date != current_date:
        st.info(f"Showing data from {most_recent_date.strftime('%A, %B %d, %Y')} (most recent activity)")
    
    # Now show the header with the correct date
    date_display = "Today" if most_recent_date == datetime.now().date() else most_recent_date.strftime('%A, %B %d')
    header_placeholder.markdown(f"""
    <h1 style="text-align: center; color: #2c3e50;">
        🏆 Your Achievement Board - {date_display}
    </h1>
    <p style="text-align: center; color: #7f8c8d; font-size: 1.2rem;">
        Discover what you've accomplished
    </p>
    """, unsafe_allow_html=True)
    
    # Process data
    df['window_title'] = df['active_window'].apply(extract_window_title)
    df['category'] = df['window_title'].apply(lambda x: ActivityCategorizer.categorize(x) if x else '📋 Other')
    df['task'] = df.apply(lambda r: extract_task_summary(r['ocr_text'], r['active_window']), axis=1)
    
    # Calculate insights
    insights = calculate_insights(df)
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'''
        <div class="insight-card">
            <h2 class="insight-number">{insights.get("focus_score", 0)}%</h2>
            <p style="margin: 0; opacity: 0.9;">Focus Score</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'''
        <div class="insight-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h2 class="insight-number">{insights.get("total_sessions", 0)}</h2>
            <p style="margin: 0; opacity: 0.9;">Work Sessions</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'''
        <div class="insight-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h2 class="insight-number">{insights.get("task_diversity", 0)}</h2>
            <p style="margin: 0; opacity: 0.9;">Different Tasks</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        peak_hour = insights.get("peak_hour", 12)
        st.markdown(f'''
        <div class="insight-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <h2 class="insight-number">{peak_hour}:00</h2>
            <p style="margin: 0; opacity: 0.9;">Peak Hour</p>
        </div>
        ''', unsafe_allow_html=True)
    
    # Motivational quote
    quote = get_motivational_quote(insights.get('focus_score', 50), insights.get('task_diversity', 0))
    st.markdown(f'<div class="motivation-quote">{quote}</div>', unsafe_allow_html=True)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## 🎯 Today's Achievements")
        
        # Simplified task grouping - group by window title similarity and time proximity
        task_groups = []
        df_sorted = df.sort_values('created_at')
        
        # Group consecutive activities with same window into tasks
        current_window = None
        current_start = None
        current_end = None
        current_category = None
        
        for idx, row in df_sorted.iterrows():
            window_title = row['window_title'] or 'Unknown'
            timestamp = pd.to_datetime(row['created_at'])
            category = row['category']
            
            # If this is a new window or significant time gap, start new task
            if (current_window is None or 
                current_window != window_title or 
                (current_end and (timestamp - current_end).total_seconds() > 300)):  # 5 min gap
                
                # Save previous task if it existed for >30 seconds
                if current_window and current_start and current_end:
                    duration = (current_end - current_start).total_seconds() / 60
                    if duration > 0.5:  # At least 30 seconds
                        task_groups.append((current_window, duration, current_start, current_category))
                
                # Start new task
                current_window = window_title
                current_start = timestamp
                current_category = category
            
            current_end = timestamp
        
        # Don't forget the last task
        if current_window and current_start and current_end:
            duration = (current_end - current_start).total_seconds() / 60
            if duration > 0.5:
                task_groups.append((current_window, duration, current_start, current_category))
        
        # Sort by duration and display top achievements
        task_groups.sort(key=lambda x: x[1], reverse=True)
        
        # Debug info
        st.write(f"**Debug:** Found {len(task_groups)} task groups from {len(df)} screenshots")
        
        if len(task_groups) == 0:
            st.info("No task groups found. This might indicate all activities were too short (< 30 seconds) or data processing issues.")
            # Show raw data for debugging
            with st.expander("Debug: Raw Data"):
                st.write("Sample data:")
                for i, row in df.head(3).iterrows():
                    st.write(f"- {row['created_at']}: {row['window_title']} ({row['category']})")
        else:
            for task, duration, start_time, category in task_groups[:8]:  # Top 8 achievements
                achievement = format_task_as_achievement(task, duration, category)
                display_achievement_card(achievement)
    
    with col2:
        st.markdown("## 📅 Daily Journey")
        
        # Timeline visualization
        if len(task_groups) > 0:
            timeline_html = create_daily_journey_timeline(task_groups)
            st.markdown(timeline_html, unsafe_allow_html=True)
        
        # Focus meter
        st.markdown("### 🎯 Focus Meter")
        focus_score = insights.get('focus_score', 0)
        st.markdown(f'''
        <div class="focus-meter">
            <div class="focus-bar">
                <div class="focus-fill" style="width: {focus_score}%;"></div>
            </div>
            <p style="text-align: center; margin-top: 0.5rem; color: #7f8c8d;">
                {focus_score}% Focus Score
            </p>
        </div>
        ''', unsafe_allow_html=True)
        
        # Quick stats
        st.markdown("### 📊 Quick Stats")
        longest_session = insights.get('longest_session', 0)
        st.metric("Longest Focus Session", f"{int(longest_session)} min")
        st.metric("Screenshots Today", len(df))
        
        # Category pie chart
        fig = go.Figure(data=[go.Pie(
            labels=df['category'].value_counts().index,
            values=df['category'].value_counts().values,
            hole=.3
        )])
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()