"""Utility functions for dashboards (UI-independent)."""

from datetime import datetime, timedelta
from typing import Tuple


def get_time_range(time_filter: str) -> Tuple[datetime, datetime]:
    """Convert time filter to datetime range (UI-independent).
    
    Args:
        time_filter: Time filter string (Today, This Week, etc.)
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.now()
    
    if time_filter == "Today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif time_filter == "Yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59)
    elif time_filter == "This Week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif time_filter == "Last 7 Days":
        start = now - timedelta(days=7)
        end = now
    elif time_filter == "This Month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif time_filter == "Last 30 Days":
        start = now - timedelta(days=30)
        end = now
    else:  # All Time
        start = datetime(2020, 1, 1)
        end = now
        
    return start, end