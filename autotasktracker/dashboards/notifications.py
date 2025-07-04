#!/usr/bin/env python3
"""
Task notification system - Provides periodic insights about your work
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import time

from autotasktracker import ActivityCategorizer, extract_window_title

try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("Desktop notifications not available. Install with: pip install plyer")

class TaskNotifier:
    def __init__(self):
        self.home_dir = Path.home()
        self.db_path = self.home_dir / ".memos" / "database.db"
        self.last_notification = datetime.now()
        self.notification_interval = 3600  # 1 hour
        
    def get_db_connection(self):
        """Connect to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except:
            return None
            
    def get_recent_stats(self, hours=1):
        """Get statistics for recent activity"""
        conn = self.get_db_connection()
        if not conn:
            return None
            
        stats = {
            'screenshots': 0,
            'categories': {},
            'focus_time': 0,
            'top_activity': None
        }
        
        try:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Get recent screenshots with window data
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.created_at, me.value as active_window
                FROM entities e
                LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'active_window'
                WHERE e.file_type_group = 'image' AND e.created_at >= ?
                ORDER BY e.created_at DESC
            """, (since,))
            
            activities = []
            for row in cursor.fetchall():
                if row['active_window']:
                    try:
                        title = extract_window_title(row['active_window'])
                        if title:
                            category = ActivityCategorizer.categorize(title)
                            activities.append({
                                'time': datetime.fromisoformat(row['created_at']),
                                'category': category,
                                'title': title
                            })
                    except:
                        pass
                        
            stats['screenshots'] = len(activities)
            
            # Calculate category distribution
            for activity in activities:
                cat = activity['category']
                stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
                
            # Find top activity
            if stats['categories']:
                top_cat = max(stats['categories'].items(), key=lambda x: x[1])
                stats['top_activity'] = top_cat[0]
                
            # Calculate focus time (continuous work in same category)
            if activities:
                focus_sessions = []
                current_session = {'category': activities[0]['category'], 'duration': 0}
                
                for i in range(1, len(activities)):
                    time_diff = (activities[i-1]['time'] - activities[i]['time']).total_seconds() / 60
                    if time_diff <= 5 and activities[i]['category'] == current_session['category']:
                        current_session['duration'] += time_diff
                    else:
                        if current_session['duration'] >= 10:  # At least 10 minutes
                            focus_sessions.append(current_session['duration'])
                        current_session = {'category': activities[i]['category'], 'duration': 0}
                        
                stats['focus_time'] = sum(focus_sessions)
                
            conn.close()
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            
        return stats
        
            
    def generate_insight(self, stats):
        """Generate an insight message based on stats"""
        if not stats or stats['screenshots'] == 0:
            return None
            
        insights = []
        
        # Activity summary
        if stats['top_activity']:
            percentage = (stats['categories'][stats['top_activity']] / stats['screenshots']) * 100
            insights.append(f"You spent {percentage:.0f}% of the last hour on {stats['top_activity']}")
            
        # Focus time
        if stats['focus_time'] >= 30:
            insights.append(f"Great focus! {stats['focus_time']:.0f} minutes of deep work")
        elif stats['focus_time'] < 10:
            insights.append("Consider blocking time for focused work")
            
        # Activity variety
        if len(stats['categories']) > 3:
            insights.append("High context switching detected")
        elif len(stats['categories']) == 1:
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
            except:
                pass
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
                print(f"Error in notification loop: {e}")
                time.sleep(300)

if __name__ == "__main__":
    print("Starting task notification service...")
    print("You'll receive hourly productivity insights.")
    print("Press Ctrl+C to stop.\n")
    
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