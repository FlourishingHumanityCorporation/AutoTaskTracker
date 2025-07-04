#!/usr/bin/env python3
"""
Capture and display the current state of the AutoTaskTracker dashboard
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.categorizer import ActivityCategorizer, extract_window_title
from autotasktracker.core.time_tracker import TimeTracker
import json

def capture_dashboard_state():
    """Capture what the dashboard is currently showing"""
    db = DatabaseManager()
    
    print("🖥️  AUTOTASKTRACKER LIVE DASHBOARD STATE")
    print("=" * 70)
    print(f"Captured at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dashboard URL: http://localhost:8502")
    print("=" * 70)
    
    # Get data for different time ranges
    time_ranges = {
        "Last Hour": timedelta(hours=1),
        "Today": timedelta(days=1),
        "Last 7 Days": timedelta(days=7)
    }
    
    for range_name, delta in time_ranges.items():
        print(f"\n📊 {range_name.upper()} VIEW")
        print("-" * 50)
        
        start_date = datetime.now() - delta
        df = db.fetch_tasks(start_date=start_date, limit=5000)
        
        if len(df) == 0:
            print("No data available for this period")
            continue
            
        # Basic stats
        print(f"Total Activities: {len(df)}")
        
        # Category breakdown
        categories = {}
        unique_tasks = set()
        
        for _, row in df.iterrows():
            title = extract_window_title(row.get('active_window', ''))
            if title:
                unique_tasks.add(title)
                cat = ActivityCategorizer.categorize(title, row.get('ocr_text', ''))
                categories[cat] = categories.get(cat, 0) + 1
        
        print(f"Unique Tasks: {len(unique_tasks)}")
        
        # Show top categories
        print("\nTop Categories:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            percentage = (count / len(df)) * 100
            bar = "█" * int(percentage / 5)
            print(f"  {cat:<25} {bar:<20} {percentage:>5.1f}%")
        
        # Time tracking for today's data
        if range_name == "Today":
            print("\n⏱️  Time Sessions:")
            tracker = TimeTracker()
            sessions = tracker.track_sessions(df)
            
            if sessions:
                # Show top 5 sessions
                sessions.sort(key=lambda x: x.duration_minutes, reverse=True)
                for i, session in enumerate(sessions[:5]):
                    confidence_icon = '🟢' if session.confidence > 0.8 else '🟡' if session.confidence > 0.6 else '🔴'
                    print(f"\n  {i+1}. {session.task_name[:50]}")
                    print(f"     Duration: {session.duration_minutes:.1f} min | Active: {session.active_time_minutes:.1f} min")
                    print(f"     Confidence: {confidence_icon} {session.confidence:.2f}")
    
    # Show what filters are available
    print("\n🎛️  DASHBOARD FILTERS")
    print("-" * 50)
    print("Date Range: Today, Yesterday, Last 7 Days, Last 30 Days, Custom")
    print("Categories: All, " + ", ".join(list(categories.keys())[:5]))
    print("Export Options: CSV, JSON")
    
    # Show recent activities like the dashboard would
    print("\n📜 RECENT ACTIVITIES (as shown in dashboard)")
    print("-" * 50)
    recent_df = db.fetch_tasks(start_date=datetime.now() - timedelta(hours=1), limit=10)
    
    if len(recent_df) > 0:
        print(f"{'Time':<8} {'Category':<20} {'Window Title':<40}")
        print("-" * 70)
        
        for _, row in recent_df.iterrows():
            time = pd.to_datetime(row['created_at']).strftime('%H:%M')
            title = extract_window_title(row.get('active_window', '')) or 'Unknown'
            cat = ActivityCategorizer.categorize(title, row.get('ocr_text', ''))
            
            # Truncate title if too long
            if len(title) > 38:
                title = title[:35] + '...'
            
            print(f"{time:<8} {cat:<20} {title:<40}")
    
    print("\n" + "=" * 70)
    print("💡 The live dashboard updates automatically every 60 seconds")
    print("💡 Click on any time period or category to filter the data")
    print("💡 Hover over charts for detailed information")

if __name__ == "__main__":
    capture_dashboard_state()