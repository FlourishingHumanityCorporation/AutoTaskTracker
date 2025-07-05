"""Refactored Achievement Board using new dashboard architecture."""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import logging

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components import (
    TimeFilterComponent,
    MetricsRow,
    NoDataMessage
)
from autotasktracker.dashboards.data import TaskRepository, MetricsRepository
from autotasktracker.dashboards.cache import cached_data
from autotasktracker.core import DatabaseManager
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)

# Achievement levels configuration
ACHIEVEMENT_LEVELS = {
    'quick_win': {'min': 1, 'max': 10, 'emoji': '⚡', 'name': 'Quick Win', 'color': '#3498db'},
    'focused_work': {'min': 10, 'max': 30, 'emoji': '🎯', 'name': 'Focused Work', 'color': '#2ecc71'},
    'deep_dive': {'min': 30, 'max': 60, 'emoji': '🏊', 'name': 'Deep Dive', 'color': '#e74c3c'},
    'marathon': {'min': 60, 'max': 999, 'emoji': '🏃', 'name': 'Marathon Session', 'color': '#9b59b6'}
}


class AchievementBoardDashboard(BaseDashboard):
    """Refactored Achievement Board dashboard."""
    
    def __init__(self):
        super().__init__(
            title="Achievement Board - AutoTaskTracker",
            icon="🏆",
            port=get_config().TIMETRACKER_PORT
        )
        
    def init_session_state(self):
        """Initialize achievement board specific session state."""
        super().init_session_state()
        
        if 'show_screenshots' not in st.session_state:
            st.session_state.show_screenshots = True
        if 'min_achievement_duration' not in st.session_state:
            st.session_state.min_achievement_duration = 1
            
    def inject_achievement_css(self):
        """Inject custom CSS for achievement design."""
        st.markdown("""
        <style>
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
        
        .achievement-card.deep_dive {
            border-color: #e74c3c;
            background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
        }
        
        .achievement-card.marathon {
            border-color: #9b59b6;
            background: linear-gradient(135deg, #f9f5ff 0%, #ffffff 100%);
        }
        
        .achievement-badge {
            position: absolute;
            top: 1rem;
            right: 1rem;
            font-size: 2rem;
            opacity: 0.2;
        }
        
        .task-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }
        
        .motivational-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            margin: 2rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
    def categorize_achievement(self, duration_minutes: float) -> dict:
        """Categorize achievement based on duration."""
        for level_key, level_info in ACHIEVEMENT_LEVELS.items():
            if level_info['min'] <= duration_minutes < level_info['max']:
                return {
                    'level': level_key,
                    'level_name': level_info['name'],
                    'emoji': level_info['emoji'],
                    'color': level_info['color'],
                    'duration': duration_minutes
                }
        return {
            'level': 'quick_win',
            'level_name': 'Quick Win',
            'emoji': '⚡',
            'color': '#3498db',
            'duration': duration_minutes
        }
        
    def render_achievement_card(self, task_group, show_screenshot: bool = True):
        """Render a single achievement card."""
        achievement = self.categorize_achievement(task_group.duration_minutes)
        card_class = f"achievement-card {achievement['level']}"
        
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        st.markdown(f'<div class="achievement-badge">{achievement["emoji"]}</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f'<div class="task-title">{task_group.window_title}</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **{achievement['level_name']}** • {task_group.category} • {int(task_group.duration_minutes)} minutes
            """)
            
            # Progress bar
            progress = min(100, (task_group.duration_minutes / 60) * 100)
            st.progress(progress / 100)
            
            # Task details
            st.caption(f"🕒 {task_group.start_time.strftime('%I:%M %p')} - {task_group.end_time.strftime('%I:%M %p')}")
            
        with col2:
            if show_screenshot and task_group.tasks:
                screenshot_path = task_group.tasks[0].screenshot_path
                if screenshot_path and os.path.exists(screenshot_path):
                    try:
                        from PIL import Image
                        img = Image.open(screenshot_path)
                        img.thumbnail((150, 150))
                        st.image(img, use_container_width=True)
                    except Exception as e:
                        logger.debug(f"Failed to load achievement icon: {e}")
                        
        st.markdown('</div>', unsafe_allow_html=True)
        
    def render_motivational_message(self) -> str:
        """Get a motivational message."""
        import random
        
        quotes = [
            "🌟 Every task completed is a step towards greatness!",
            "💪 Your focused work today builds tomorrow's success.",
            "🎯 Consistency beats perfection. Keep going!",
            "🚀 You're making amazing progress, one task at a time.",
            "🌱 Every journey starts with a single step. Keep going!",
            "☀️ A new day brings new opportunities to shine.",
            "💪 You're building great habits, one task at a time."
        ]
        
        return random.choice(quotes)
        
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            st.header("🏆 Achievement Settings")
            
            # Time filter
            time_filter = TimeFilterComponent.render()
            
            # Display options
            st.subheader("Display Options")
            show_screenshots = st.checkbox(
                "Show Screenshots",
                value=st.session_state.show_screenshots,
                key="show_screenshots"
            )
            
            min_duration = st.slider(
                "Minimum Achievement Duration (minutes)",
                min_value=1,
                max_value=30,
                value=st.session_state.min_achievement_duration,
                key="min_achievement_duration"
            )
            
            # Achievement stats
            st.subheader("Achievement Stats")
            for level_key, level_info in ACHIEVEMENT_LEVELS.items():
                st.metric(
                    f"{level_info['emoji']} {level_info['name']}",
                    f"{level_info['min']}-{level_info['max']} min"
                )
                
            # Cache controls
            self.render_cache_controls()
            
            return time_filter, show_screenshots, min_duration
            
    @cached_data(ttl_seconds=300, key_prefix="achievements")
    def get_achievement_data(self, start_date: datetime, end_date: datetime, min_duration: int):
        """Get cached achievement data."""
        task_repo = TaskRepository(self.db_manager)
        return task_repo.get_task_groups(
            start_date=start_date,
            end_date=end_date,
            min_duration_minutes=min_duration
        )
        
    def render_achievements(self, start_date: datetime, end_date: datetime, show_screenshots: bool, min_duration: int):
        """Render achievements section."""
        # Get achievement data (cached)
        task_groups = self.get_achievement_data(start_date, end_date, min_duration)
        
        if not task_groups:
            NoDataMessage.render(
                "No achievements yet! Complete some tasks to see them here.",
                suggestions=[
                    f"Tasks need to run for at least {min_duration} minute(s) to appear as achievements",
                    "Try adjusting the minimum duration in the sidebar",
                    "Check if Memos is capturing screenshots properly"
                ],
                icon="🏆"
            )
            return
            
        # Sort by duration (longest first)
        task_groups.sort(key=lambda x: x.duration_minutes, reverse=True)
        
        # Categorize achievements
        achievement_counts = {'quick_win': 0, 'focused_work': 0, 'deep_dive': 0, 'marathon': 0}
        for group in task_groups:
            level = self.categorize_achievement(group.duration_minutes)['level']
            achievement_counts[level] += 1
            
        # Show achievement summary
        st.subheader("🏆 Achievement Summary")
        MetricsRow.render({
            f"⚡ Quick Wins": achievement_counts['quick_win'],
            f"🎯 Focused Work": achievement_counts['focused_work'], 
            f"🏊 Deep Dives": achievement_counts['deep_dive'],
            f"🏃 Marathons": achievement_counts['marathon']
        })
        
        # Motivational message
        message = self.render_motivational_message()
        st.markdown(f'<div class="motivational-message">{message}</div>', unsafe_allow_html=True)
        
        # Show achievements
        st.subheader(f"🌟 Your Achievements ({len(task_groups)})")
        
        for i, group in enumerate(task_groups[:10]):  # Show top 10
            self.render_achievement_card(group, show_screenshots)
            if i < len(task_groups) - 1:
                st.markdown("---")
                
    def render_insights(self, start_date: datetime, end_date: datetime):
        """Render insights section."""
        st.subheader("💡 Insights")
        
        # Get metrics
        metrics_repo = MetricsRepository(self.db_manager)
        summary = metrics_repo.get_metrics_summary(start_date, end_date)
        
        if summary['total_activities'] > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Productivity Insights:**")
                avg_daily = summary['avg_daily_activities']
                st.write(f"• Average daily activities: **{avg_daily:.1f}**")
                st.write(f"• Total active days: **{summary['active_days']}**")
                st.write(f"• Unique applications: **{summary['unique_windows']}**")
                
            with col2:
                st.markdown("**🎯 Recommendations:**")
                if avg_daily < 20:
                    st.write("• Try to increase daily activity for better tracking")
                elif avg_daily > 100:
                    st.write("• Great activity level! You're very productive")
                else:
                    st.write("• Good balance of activity and focus time")
                    
                if summary['unique_windows'] > 10:
                    st.write("• Consider focusing on fewer applications for deeper work")
                    
    def run(self):
        """Main dashboard execution."""
        # Check database connection
        if not self.ensure_connection():
            return
            
        # Inject CSS
        self.inject_achievement_css()
        
        # Header
        st.title("🏆 Achievement Board")
        st.markdown("Celebrate your productivity wins and track your focused work sessions!")
        
        # Render sidebar and get settings
        time_filter, show_screenshots, min_duration = self.render_sidebar()
        
        # Get time range
        start_date, end_date = TimeFilterComponent.get_time_range(time_filter)
        
        # Main content
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.render_achievements(start_date, end_date, show_screenshots, min_duration)
            
        with col2:
            self.render_insights(start_date, end_date)
            

def main():
    """Run the refactored achievement board."""
    import os
    # Add os import for screenshot path checking
    global os
    
    dashboard = AchievementBoardDashboard()
    dashboard.run()
    

if __name__ == "__main__":
    main()