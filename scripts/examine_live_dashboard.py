#!/usr/bin/env python3
"""
Script to examine the live dashboard and show what's actually displayed.
This simulates what a user would see when opening the dashboard.
"""

import sys
import os
import subprocess
import time
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_dashboard_content():
    """Simulate the dashboard content by running the same logic."""
    print("🔍 EXAMINING LIVE DASHBOARD CONTENT")
    print("="*60)
    
    try:
        # Import the dashboard components
        from autotasktracker.dashboards.base import BaseDashboard
        from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository
        from autotasktracker.core.database import DatabaseManager
        from autotasktracker.utils.config import get_config
        
        # Mock the dashboard initialization (without Streamlit)
        class MockDashboard(BaseDashboard):
            def __init__(self):
                self.title = "AutoTaskTracker - Task Board"
                self.icon = "📋"
                self.config = get_config()
                self._db_manager = None
                
        dashboard = MockDashboard()
        
        # Get database connection and repositories
        db = dashboard.db_manager
        task_repo = TaskRepository(db)
        metrics_repo = MetricsRepository(db)
        
        print(f"📊 Dashboard: {dashboard.title}")
        print(f"🔗 Database: {dashboard.config.DB_PATH}")
        print()
        
        # Check database connectivity
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM metadata_entries")
            total_metadata = cursor.fetchone()[0]
            
        print(f"📈 Database Status:")
        print(f"   ✅ Connected successfully")
        print(f"   📸 Total screenshots: {total_entities}")
        print(f"   📝 Total metadata entries: {total_metadata}")
        print()
        
        # Get time range for today
        start_time, end_time = dashboard.get_time_range("Today")
        print(f"⏰ Time Filter: Today ({start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')})")
        print()
        
        # Get today's data
        tasks = task_repo.get_tasks_for_period(start_time, end_time, limit=50)
        
        print(f"📋 TASK DATA:")
        if tasks:
            print(f"   📊 Found {len(tasks)} tasks for today")
            print()
            print("   Recent Tasks:")
            for i, task in enumerate(tasks[:5]):
                print(f"   {i+1}. [{task.timestamp.strftime('%H:%M')}] {task.title}")
                print(f"      Category: {task.category}")
                if task.ocr_text:
                    # Show first 100 chars of OCR text
                    ocr_preview = task.ocr_text[:100] + "..." if len(task.ocr_text) > 100 else task.ocr_text
                    print(f"      Text: {ocr_preview}")
                print()
        else:
            print("   ❌ No tasks found for today")
            print("   💡 This could mean:")
            print("      - Memos is not running (run 'memos start')")
            print("      - No screenshots captured today") 
            print("      - Database is empty")
            print()
            
        # Get task groups (continuous activity sessions)
        task_groups = task_repo.get_task_groups(start_time, end_time)
        
        print(f"🎯 ACTIVITY SESSIONS:")
        if task_groups:
            print(f"   📊 Found {len(task_groups)} activity sessions")
            print()
            for i, group in enumerate(task_groups[:3]):
                duration_str = f"{group.duration_minutes:.1f} min"
                print(f"   {i+1}. {group.window_title}")
                print(f"      ⏱️  Duration: {duration_str}")
                print(f"      📂 Category: {group.category}")
                print(f"      🔢 Screenshots: {group.task_count}")
                print(f"      🕐 Time: {group.start_time.strftime('%H:%M')} - {group.end_time.strftime('%H:%M')}")
                print()
        else:
            print("   ❌ No activity sessions found")
            print()
            
        # Get metrics summary  
        metrics = metrics_repo.get_metrics_summary(start_time, end_time)
        
        print(f"📈 METRICS SUMMARY:")
        print(f"   🔢 Total activities: {metrics['total_activities']}")
        print(f"   📅 Active days: {metrics['active_days']}")
        print(f"   🪟 Unique windows: {metrics['unique_windows']}")
        print(f"   📂 Categories: {metrics['unique_categories']}")
        print(f"   📊 Avg daily activities: {metrics['avg_daily_activities']:.1f}")
        print()
        
        # Show what the dashboard UI would display
        print("🖥️  DASHBOARD UI ELEMENTS:")
        print("   ✅ Time filter dropdown (Today, Yesterday, This Week, etc.)")
        print("   ✅ Category filter with all available categories")
        print("   ✅ Metrics cards showing key numbers")
        if task_groups:
            print("   ✅ Task groups showing continuous activity sessions")
        else:
            print("   ⚠️  'No data' message (no activity sessions)")
        print("   ✅ Raw data toggle for detailed view")
        print("   ✅ Cache management controls")
        print("   ✅ Refresh button")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error examining dashboard: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dashboard_status():
    """Check if the dashboard is actually running."""
    print("🚀 DASHBOARD STATUS CHECK")
    print("="*40)
    
    try:
        # Check if streamlit is running
        result = subprocess.run(['pgrep', '-f', 'streamlit'], capture_output=True)
        if result.returncode == 0:
            print("✅ Streamlit is running")
            
            # Try to connect to the dashboard
            import urllib.request
            try:
                with urllib.request.urlopen('http://localhost:8502', timeout=5) as response:
                    if response.status == 200:
                        print("✅ Dashboard is accessible at http://localhost:8502")
                        return True
                    else:
                        print(f"⚠️  Dashboard returned status {response.status}")
            except Exception as e:
                print(f"❌ Cannot connect to dashboard: {e}")
                
        else:
            print("❌ Streamlit is not running")
            print("💡 Start with: python autotasktracker.py dashboard")
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        
    return False

def main():
    print("🔍 LIVE DASHBOARD EXAMINATION")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if dashboard is running
    dashboard_running = check_dashboard_status()
    print()
    
    # Examine the content
    content_examined = get_dashboard_content()
    
    print("="*60)
    if dashboard_running and content_examined:
        print("🎉 DASHBOARD EXAMINATION COMPLETE")
        print("✅ Dashboard is running and functional")
        print("🌐 Open http://localhost:8502 to see the live interface")
    else:
        print("⚠️  EXAMINATION COMPLETED WITH ISSUES")
        if not dashboard_running:
            print("🔧 Start dashboard: python autotasktracker.py dashboard")
        if not content_examined:
            print("🔧 Check logs for data loading issues")

if __name__ == "__main__":
    main()