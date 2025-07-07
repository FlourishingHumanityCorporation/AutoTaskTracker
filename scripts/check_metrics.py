#!/usr/bin/env python
"""Check metrics from all sources."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from autotasktracker.dashboards.data.repositories import MetricsRepository
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter

# Date range
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

print(f"Checking metrics for {start_date.date()} to {end_date.date()}\n")

# 1. Check via MetricsRepository
print("1. MetricsRepository:")
try:
    metrics_repo = MetricsRepository()
    summary = metrics_repo.get_metrics_summary(start_date, end_date)
    print(f"   Total activities: {summary.get('total_activities', 'N/A')}")
    print(f"   Active days: {summary.get('active_days', 'N/A')}")
    print(f"   Unique windows: {summary.get('unique_windows', 'N/A')}")
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Check PostgreSQL directly
print("\n2. PostgreSQL Direct Query:")
try:
    pg = get_postgresql_adapter()
    with pg.get_connection() as conn:
        cursor = conn.cursor()
        
        # Total entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]
        print(f"   Total entities (all time): {total}")
        
        # 30-day count with COALESCE
        cursor.execute("""
            SELECT COUNT(*) FROM entities 
            WHERE COALESCE(created_at, file_created_at) >= NOW() - INTERVAL '30 days'
        """)
        month_count = cursor.fetchone()[0]
        print(f"   30-day count: {month_count}")
        
        # Check for NULL created_at
        cursor.execute("SELECT COUNT(*) FROM entities WHERE created_at IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"   Entities with NULL created_at: {null_count}")
        
except Exception as e:
    print(f"   ERROR: {e}")

print("\n✓ Check complete. If numbers differ, cache may still be active.")