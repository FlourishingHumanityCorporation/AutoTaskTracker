#!/usr/bin/env python3
"""
Show what the live AutoTaskTracker dashboards look like
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.categorizer import ActivityCategorizer, extract_window_title
from autotasktracker.core.time_tracker import TimeTracker

def show_dashboard_preview():
    """Show what the dashboard would display"""
    db = DatabaseManager()
    
    print("🖥️  AutoTaskTracker Live Dashboard Preview")
    print("=" * 60)
    
    # Get recent data
    hours = 24
    start_date = datetime.now() - timedelta(hours=hours)
    df = db.fetch_tasks(start_date=start_date, limit=1000)
    
    print(f"\n📊 Data Summary (Last {hours} hours)")
    print(f"Total screenshots: {len(df)}")
    
    if len(df) == 0:
        print("No data available!")
        return
    
    # Show time range
    print(f"Time range: {df['created_at'].min()} to {df['created_at'].max()}")
    
    # Category breakdown
    print("\n📂 Activity Categories:")
    categories = {}
    for _, row in df.iterrows():
        title = extract_window_title(row.get('active_window', ''))
        if title:
            cat = ActivityCategorizer.categorize(title, row.get('ocr_text', ''))
            categories[cat] = categories.get(cat, 0) + 1
    
    # Sort by count
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(df)) * 100
        print(f"  {cat}: {count} ({percentage:.1f}%)")
    
    # Recent activities
    print("\n🕐 Recent Activities (Last 10):")
    recent = df.head(10)
    for _, row in recent.iterrows():
        time = pd.to_datetime(row['created_at']).strftime('%H:%M:%S')
        title = extract_window_title(row.get('active_window', '')) or 'Unknown'
        cat = ActivityCategorizer.categorize(title, row.get('ocr_text', ''))
        # Truncate long titles
        if len(title) > 50:
            title = title[:47] + '...'
        print(f"  {time} | {cat} | {title}")
    
    # Time tracking
    print("\n⏱️  Time Tracking Sessions:")
    tracker = TimeTracker()
    sessions = tracker.track_sessions(df)
    
    if sessions:
        # Show top 5 sessions by duration
        sessions.sort(key=lambda x: x.duration_minutes, reverse=True)
        for i, session in enumerate(sessions[:5]):
            print(f"\n  Session {i+1}:")
            print(f"    Task: {session.task_name}")
            print(f"    Category: {session.category}")
            print(f"    Duration: {session.duration_minutes:.1f} min")
            print(f"    Active: {session.active_time_minutes:.1f} min")
            print(f"    Confidence: {'🟢' if session.confidence > 0.8 else '🟡' if session.confidence > 0.6 else '🔴'} {session.confidence:.2f}")
    
    # Daily summary
    daily_summary = tracker.get_daily_summary(sessions)
    print("\n📈 Daily Summary:")
    print(f"  Total Time: {daily_summary['total_time_minutes']:.1f} minutes")
    print(f"  Active Time: {daily_summary['active_time_minutes']:.1f} minutes")
    print(f"  Unique Tasks: {daily_summary['unique_tasks']}")
    print(f"  Focus Score: {daily_summary['focus_score']}/100")
    print(f"  Longest Session: {daily_summary['longest_session_minutes']:.1f} minutes")
    
    # Show what the Task Board would display
    print("\n🎯 Task Board View (What you'd see in Streamlit):")
    print("┌─────────────────────────────────────────────────────────┐")
    print("│ 📋 AutoTaskTracker - Task Board                        │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ Filters:                                                │")
    print("│   Date Range: [Today ▼] [All Categories ▼]            │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ 📊 Summary Metrics:                                    │")
    print(f"│   • Total Activities: {len(df)}                       │")
    print(f"│   • Unique Tasks: {daily_summary['unique_tasks']}     │")
    print(f"│   • Active Time: {daily_summary['active_time_minutes']:.0f} min │")
    print(f"│   • Top Category: {max(categories.items(), key=lambda x: x[1])[0]} │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ 📈 Activity Timeline:                                   │")
    print("│   [Interactive time series chart would appear here]     │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ 🗂️ Recent Activities:                                  │")
    
    # Show sample recent activities as they'd appear
    for _, row in df.head(5).iterrows():
        time = pd.to_datetime(row['created_at']).strftime('%H:%M')
        title = extract_window_title(row.get('active_window', '')) or 'Unknown'
        cat = ActivityCategorizer.categorize(title, row.get('ocr_text', ''))
        if len(title) > 40:
            title = title[:37] + '...'
        print(f"│   {time} | {cat} {title:<40}│")
    
    print("└─────────────────────────────────────────────────────────┘")

if __name__ == "__main__":
    show_dashboard_preview()