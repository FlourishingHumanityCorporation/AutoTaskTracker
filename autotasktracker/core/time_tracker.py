"""
Enhanced Time Tracking Module for AutoTaskTracker

This module provides intelligent time tracking that accounts for:
- Screenshot capture intervals
- Natural work breaks vs interruptions  
- Session boundaries and task switching
- Idle time detection
- Confidence scoring for time estimates
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import pandas as pd
from collections import defaultdict
import logging

from autotasktracker.core.categorizer import ActivityCategorizer, extract_window_title
from autotasktracker.utils.config import get_config


logger = logging.getLogger(__name__)


@dataclass
class TaskSession:
    """Represents a continuous work session on a single task."""
    task_name: str
    window_title: str
    category: str
    start_time: datetime
    end_time: datetime
    screenshot_count: int = 1
    gaps: List[float] = field(default_factory=list)  # Gap durations in seconds
    confidence: float = 1.0  # Confidence in time estimate (0-1)
    
    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def duration_minutes(self) -> float:
        """Total duration in minutes."""
        return self.duration_seconds / 60
    
    @property
    def active_time_seconds(self) -> float:
        """Active time excluding gaps."""
        return self.duration_seconds - sum(self.gaps)
    
    @property
    def active_time_minutes(self) -> float:
        """Active time in minutes."""
        return self.active_time_seconds / 60
    
    def add_screenshot(self, timestamp: datetime, gap_seconds: float):
        """Add a screenshot to the session."""
        self.screenshot_count += 1
        self.end_time = timestamp
        if gap_seconds > 0:
            self.gaps.append(gap_seconds)


class TimeTracker:
    """Enhanced time tracking with intelligent session detection."""
    
    # Default configuration
    DEFAULT_SCREENSHOT_INTERVAL = 4  # seconds (from memos config)
    MAX_SESSION_GAP = 600  # 10 minutes - max gap before new session
    MIN_SESSION_DURATION = 30  # 30 seconds - minimum to count as a session
    IDLE_THRESHOLD = 300  # 5 minutes - consider idle after this gap
    
    # Task-specific gap thresholds (in seconds)
    CATEGORY_GAP_THRESHOLDS = {
        '🧑‍💻 Coding': 600,           # 10 min - developers often pause to think
        '💬 Communication': 300,      # 5 min - quick context switches
        '🔍 Research/Browsing': 900, # 15 min - research can have longer gaps
        '📝 Documentation': 600,      # 10 min - writing needs thinking time
        '🎥 Meetings': 300,          # 5 min - meetings are continuous
        '🎨 Design': 600,            # 10 min - design work has thinking time
        '📊 Data Analysis': 600,     # 10 min - analysis involves switching
        '🎬 Media/Video': 1200,      # 20 min - videos can have breaks
        '🎮 Gaming': 300,            # 5 min - games are more continuous
        '🏠 System/Settings': 300,   # 5 min - quick tasks
        '🤖 AI Tools': 600,          # 10 min - AI interactions
        '📋 Other': 600              # 10 min - default
    }
    
    def __init__(self, screenshot_interval: int = None):
        """
        Initialize the time tracker.
        
        Args:
            screenshot_interval: Seconds between screenshots (auto-detect or use config)
        """
        config = get_config()
        self.screenshot_interval = (screenshot_interval or 
                                  self._detect_screenshot_interval() or 
                                  config.SCREENSHOT_INTERVAL_SECONDS)
        self.min_session_duration = config.MIN_SESSION_DURATION_SECONDS
        self.max_session_gap = config.MAX_SESSION_GAP_SECONDS
        self.idle_threshold = config.IDLE_THRESHOLD_SECONDS
        
    def track_sessions(self, df: pd.DataFrame) -> List[TaskSession]:
        """
        Process screenshot data into task sessions.
        
        Args:
            df: DataFrame with columns: created_at, active_window, ocr_text
            
        Returns:
            List of TaskSession objects
        """
        if df.empty:
            return []
        
        # Ensure proper datetime column
        df = df.copy()
        df['created_at'] = pd.to_datetime(df['created_at'])
        df = df.sort_values('created_at')
        
        sessions = []
        current_session = None
        
        for idx, row in df.iterrows():
            timestamp = row['created_at']
            window_title = extract_window_title(row['active_window']) or 'Unknown'
            category = ActivityCategorizer.categorize(window_title, row.get('ocr_text', ''))
            
            # Simplify task name (remove redundant app names)
            task_name = self._extract_task_name(window_title)
            
            if current_session is None:
                # Start first session
                current_session = TaskSession(
                    task_name=task_name,
                    window_title=window_title,
                    category=category,
                    start_time=timestamp,
                    end_time=timestamp
                )
            else:
                # Calculate gap from last screenshot
                gap_seconds = (timestamp - current_session.end_time).total_seconds()
                
                # Determine if this continues the current session
                if (task_name == current_session.task_name and 
                    gap_seconds <= self._get_max_gap_for_category(category)):
                    # Continue current session
                    current_session.add_screenshot(timestamp, max(0, gap_seconds - self.screenshot_interval))
                else:
                    # End current session and start new one
                    if current_session.duration_seconds >= self.min_session_duration:
                        self._calculate_confidence(current_session)
                        sessions.append(current_session)
                    
                    current_session = TaskSession(
                        task_name=task_name,
                        window_title=window_title,
                        category=category,
                        start_time=timestamp,
                        end_time=timestamp
                    )
        
        # Don't forget the last session
        if current_session and current_session.duration_seconds >= self.min_session_duration:
            # Add padding for time after last screenshot
            current_session.end_time += timedelta(seconds=self.screenshot_interval)
            self._calculate_confidence(current_session)
            sessions.append(current_session)
        
        return sessions
    
    def _extract_task_name(self, window_title: str) -> str:
        """Extract simplified task name from window title."""
        if not window_title:
            return 'Unknown'
        
        # Remove common app suffixes
        for suffix in [' - Google Chrome', ' - Mozilla Firefox', ' - Safari', 
                      ' - Visual Studio Code', ' - Microsoft Edge', ' - Opera']:
            window_title = window_title.replace(suffix, '')
        
        # Truncate if too long
        if len(window_title) > 60:
            window_title = window_title[:57] + '...'
        
        return window_title.strip()
    
    def _get_max_gap_for_category(self, category: str) -> float:
        """Get maximum allowed gap for a category before starting new session."""
        return self.CATEGORY_GAP_THRESHOLDS.get(category, self.MAX_SESSION_GAP)
    
    def _calculate_confidence(self, session: TaskSession):
        """Calculate confidence score for time estimate."""
        # Base confidence on screenshot density
        expected_screenshots = session.duration_seconds / self.screenshot_interval
        actual_screenshots = session.screenshot_count
        screenshot_ratio = min(1.0, actual_screenshots / max(1, expected_screenshots))
        
        # Penalize sessions with many/long gaps
        gap_ratio = sum(session.gaps) / session.duration_seconds if session.duration_seconds > 0 else 0
        gap_penalty = max(0, 1 - gap_ratio * 2)  # 50% gaps = 0 confidence
        
        # Final confidence score
        session.confidence = screenshot_ratio * gap_penalty
    
    def get_daily_summary(self, sessions: List[TaskSession]) -> Dict:
        """
        Generate daily summary statistics.
        
        Returns:
            Dictionary with summary metrics
        """
        if not sessions:
            return {
                'total_time_minutes': 0,
                'active_time_minutes': 0,
                'unique_tasks': 0,
                'longest_session_minutes': 0,
                'focus_score': 0,
                'idle_percentage': 0
            }
        
        total_time = sum(s.duration_minutes for s in sessions)
        active_time = sum(s.active_time_minutes for s in sessions)
        unique_tasks = len(set(s.task_name for s in sessions))
        longest_session = max(s.duration_minutes for s in sessions)
        
        # Calculate focus score (based on session lengths)
        focus_sessions = [s for s in sessions if s.duration_minutes >= 30]
        focus_score = min(100, len(focus_sessions) * 10)  # 10 points per 30+ min session
        
        # Idle percentage
        idle_percentage = ((total_time - active_time) / total_time * 100) if total_time > 0 else 0
        
        return {
            'total_time_minutes': round(total_time, 1),
            'active_time_minutes': round(active_time, 1),
            'unique_tasks': unique_tasks,
            'longest_session_minutes': round(longest_session, 1),
            'focus_score': focus_score,
            'idle_percentage': round(idle_percentage, 1),
            'sessions_count': len(sessions),
            'average_session_minutes': round(total_time / len(sessions), 1) if sessions else 0,
            'high_confidence_sessions': sum(1 for s in sessions if s.confidence > 0.8)
        }
    
    def group_by_task(self, sessions: List[TaskSession]) -> Dict[str, Dict]:
        """
        Group sessions by task name with aggregated metrics.
        
        Returns:
            Dictionary mapping task names to their metrics
        """
        task_groups = defaultdict(lambda: {
            'total_minutes': 0,
            'active_minutes': 0,
            'session_count': 0,
            'category': '',
            'first_seen': None,
            'last_seen': None,
            'average_confidence': 0
        })
        
        for session in sessions:
            group = task_groups[session.task_name]
            group['total_minutes'] += session.duration_minutes
            group['active_minutes'] += session.active_time_minutes
            group['session_count'] += 1
            group['category'] = session.category
            
            if group['first_seen'] is None or session.start_time < group['first_seen']:
                group['first_seen'] = session.start_time
            if group['last_seen'] is None or session.end_time > group['last_seen']:
                group['last_seen'] = session.end_time
            
            # Running average of confidence
            prev_avg = group['average_confidence']
            prev_count = group['session_count'] - 1
            group['average_confidence'] = (prev_avg * prev_count + session.confidence) / group['session_count']
        
        # Round values for display
        for task, metrics in task_groups.items():
            metrics['total_minutes'] = round(metrics['total_minutes'], 1)
            metrics['active_minutes'] = round(metrics['active_minutes'], 1)
            metrics['average_confidence'] = round(metrics['average_confidence'], 2)
        
        return dict(task_groups)
    
    def _detect_screenshot_interval(self) -> Optional[int]:
        """
        Auto-detect screenshot interval from memos config.
        
        Returns:
            Screenshot interval in seconds, or None if cannot detect
        """
        try:
            import yaml
            config = get_config()
            config_path = config.memos_dir / "config.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    memos_config = yaml.safe_load(f)
                return memos_config.get('record_interval', None)
        except Exception as e:
            logger.debug(f"Could not auto-detect screenshot interval: {e}")
        
        return None