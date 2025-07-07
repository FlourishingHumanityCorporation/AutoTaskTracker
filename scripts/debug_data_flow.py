#!/usr/bin/env python
"""Debug script to trace data flow from DB to dashboard."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository
from autotasktracker.pensieve.postgresql_adapter import PostgreSQLAdapter
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def trace_data_flow():
    """Trace data flow through all layers."""
    print("=== TRACING DATA FLOW FROM DB TO DASHBOARD ===\n")
    
    # 1. Direct DatabaseManager
    print("1. DatabaseManager (direct):")
    try:
        db = DatabaseManager()
        metrics = db.fetch_summary_metrics()
        print(f"   Total activities: {metrics.get('total_activities', 'N/A')}")
        print(f"   Total windows: {metrics.get('total_windows', 'N/A')}")
        print(f"   Date range: {metrics.get('date_range', 'N/A')}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. PostgreSQL Adapter
    print("\n2. PostgreSQLAdapter:")
    try:
        adapter = PostgreSQLAdapter()
        
        # Check connection
        print(f"   Connected: {adapter.is_connected()}")
        
        # Get metrics via adapter
        with adapter.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM entities")
            count = cursor.fetchone()[0]
            print(f"   Entity count (direct SQL): {count}")
            
            # Check for NULL created_at values
            cursor.execute("SELECT COUNT(*) FROM entities WHERE created_at IS NULL")
            null_count = cursor.fetchone()[0]
            print(f"   Entities with NULL created_at: {null_count}")
            
            # Count using COALESCE
            cursor.execute("SELECT COUNT(*) FROM entities WHERE COALESCE(created_at, file_created_at) >= NOW() - INTERVAL '30 days'")
            coalesced_count = cursor.fetchone()[0]
            print(f"   30-day count with COALESCE: {coalesced_count}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 3. MetricsRepository
    print("\n3. MetricsRepository:")
    try:
        # Get summary metrics
        metrics_repo = MetricsRepository()
        summary = metrics_repo.get_summary_metrics()
        print(f"   Total activities: {summary.get('total_activities', 'N/A')}")
        print(f"   Total windows: {summary.get('total_windows', 'N/A')}")
        print(f"   Unique AI tasks: {summary.get('unique_ai_tasks', 'N/A')}")
        
        # Get date filter options
        task_repo = TaskRepository()
        date_options = task_repo.get_date_filter_options()
        print(f"   Date filter options: {list(date_options.keys()) if date_options else 'None'}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 4. Check for caching
    print("\n4. Cache Analysis:")
    try:
        # Check if there's a difference between direct and repository
        if 'metrics' in locals() and 'summary' in locals():
            direct_count = metrics.get('total_activities', 0)
            repo_count = summary.get('total_activities', 0)
            if direct_count != repo_count:
                print(f"   CACHE ISSUE DETECTED!")
                print(f"   Direct DB: {direct_count}")
                print(f"   Repository: {repo_count}")
                print(f"   Difference: {direct_count - repo_count}")
            else:
                print(f"   No cache issue - both show {direct_count}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 5. Check configuration
    print("\n5. Configuration Check:")
    try:
        from autotasktracker.config import DATABASE_URL, SCREENSHOTS_DIR
        print(f"   Database URL: {DATABASE_URL}")
        print(f"   Screenshots dir: {SCREENSHOTS_DIR}")
        
        # Check if using PostgreSQL
        if 'postgresql' in DATABASE_URL:
            print("   Using PostgreSQL ✓")
        else:
            print("   WARNING: Not using PostgreSQL!")
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    trace_data_flow()