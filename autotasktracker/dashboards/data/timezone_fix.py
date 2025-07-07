#!/usr/bin/env python
"""Temporary timezone fix for AutoTaskTracker queries."""

from datetime import timedelta

# Timezone offset to add to queries (8 hours)
TIMEZONE_OFFSET_HOURS = 8

def adjust_query_time(dt):
    """Add timezone offset to query times."""
    return dt + timedelta(hours=TIMEZONE_OFFSET_HOURS)

def adjust_display_time(dt):
    """Subtract timezone offset for display."""
    return dt - timedelta(hours=TIMEZONE_OFFSET_HOURS)
