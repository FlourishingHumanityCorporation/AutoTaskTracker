#!/usr/bin/env python3
"""
Task notification system - Provides periodic insights about your work
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import time
import logging

from autotasktracker.core import DatabaseManager, get_config
from autotasktracker.ai import ActivityCategorizer
from autotasktracker.utils import extract_window_title

logger = logging.getLogger(__name__)

try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    notification = None  # Make notification available as None when not installed
    logger.warning("Desktop notifications not available. Install with: pip install plyer")

class TaskNotifier:
    def __init__(self):
        self.config = get_config()
        self.db = DatabaseManager()  # Use Pensieve integration by default
        self.last_notification = datetime.now()
        self.notification_interval = 3600  # 1 hour
            
    def get_recent_stats(self, hours=1):
        """Get statistics for recent activity"""
        if not self.db.test_connection():
            return None
            
        stats = {
            'screenshots': 0,
            "category": {},
            'focus_time': 0,
            'top_activity': None
        }
        
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            # Get recent tasks using DatabaseManager
            df = self.db.fetch_tasks(start_date=since, limit=1000)
            
            activities = []
            for _, row in df.iterrows():
                if row["active_window"]:
                    try:
                        title = extract_window_title(row["active_window"])
                        if title:
                            category = ActivityCategorizer.categorize(title)
                            activities.append({
                                'time': datetime.fromisoformat(row['created_at']),
                                "category": category,
                                'title': title
                            })
                    except (ValueError, TypeError, KeyError):
                        pass
                        
            stats['screenshots'] = len(activities)
            
            # Sort activities by time (oldest first)
            activities.sort(key=lambda x: x['time'])
            
            # Calculate category distribution
            for activity in activities:
                cat = activity["category"]
                stats["category"][cat] = stats["category"].get(cat, 0) + 1
                
            # Find top activity
            if stats["category"]:
                top_cat = max(stats["category"].items(), key=lambda x: x[1])
                stats['top_activity'] = top_cat[0]
                
            # Calculate focus time (continuous work in same category)
            if activities:
                focus_sessions = []
                current_session = {"category": activities[0]["category"], 'start': 0, 'duration': 0}
                
                for i in range(1, len(activities)):
                    # Calculate time difference (newer timestamp - older timestamp)
                    time_diff = (activities[i]['time'] - activities[i-1]['time']).total_seconds() / 60
                    
                    # Check if this continues the current session
                    if time_diff <= 5 and activities[i]["category"] == current_session["category"]:
                        # Accumulate the time difference
                        current_session['duration'] += time_diff
                    else:
                        # Session ended, check if it qualifies as focus time
                        if current_session['duration'] >= 10:  # At least 10 minutes
                            focus_sessions.append(current_session['duration'])
                        # Start new session
                        current_session = {"category": activities[i]["category"], 'start': i, 'duration': 0}
                
                # Don't forget the last session
                if current_session['duration'] >= 10:
                    focus_sessions.append(current_session['duration'])
                        
                stats['focus_time'] = round(sum(focus_sessions), 1)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            
        return stats
        
            
    def generate_insight(self, stats):
        """Generate an insight message based on stats"""
        if not stats or stats['screenshots'] == 0:
            return None
            
        insights = []
        
        # Activity summary
        if stats['top_activity']:
            percentage = (stats["category"][stats['top_activity']] / stats['screenshots']) * 100
            insights.append(f"You spent {percentage:.0f}% of the last hour on {stats['top_activity']}")
            
        # Focus time
        if stats['focus_time'] >= 30:
            insights.append(f"Great focus! {stats['focus_time']:.0f} minutes of deep work")
        elif stats['focus_time'] < 10:
            insights.append("Consider blocking time for focused work")
            
        # Activity variety
        if len(stats["category"]) > 3:
            insights.append("High context switching detected")
        elif len(stats["category"]) == 1:
            insights.append("Excellent single-tasking!")
            
        return " • ".join(insights) if insights else None
        
    def send_notification(self, title, message):
        """Send desktop notification"""
        if NOTIFICATIONS_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name='AutoTaskTracker',
                    timeout=10
                )
                return True
            except Exception as e:
                logger.debug(f"Desktop notification failed: {e}")
        return False
        
    def run_periodic_check(self):
        """Check and send notifications periodically"""
        while True:
            try:
                # Check if it's time for a notification
                if (datetime.now() - self.last_notification).total_seconds() >= self.notification_interval:
                    stats = self.get_recent_stats(hours=1)
                    insight = self.generate_insight(stats) if stats else None
                    
                    if insight:
                        self.send_notification(
                            "📊 Hourly Productivity Update",
                            insight
                        )
                        self.last_notification = datetime.now()
                        
                # Sleep for 5 minutes before next check
                time.sleep(300)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                time.sleep(300)

if __name__ == "__main__":
    logger.info("Starting task notification service...")
    logger.info("You'll receive hourly productivity insights.")
    logger.info("Press Ctrl+C to stop.\n")
    
    notifier = TaskNotifier()
    
    # Send initial notification
    stats = notifier.get_recent_stats(hours=0.25)  # Last 15 minutes
    if stats and stats['screenshots'] > 0:
        notifier.send_notification(
            "✅ AutoTaskTracker Active",
            f"Tracking started. {stats['screenshots']} activities captured so far."
        )
    
    # Run periodic checks
    notifier.run_periodic_check()