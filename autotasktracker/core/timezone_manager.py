"""
Centralized timezone management for AutoTaskTracker.

Provides proper timezone handling that integrates with Pensieve's storage conventions.
Pensieve stores timestamps in UTC but filenames use local time.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import time
import os

logger = logging.getLogger(__name__)


class TimezoneManager:
    """Centralized timezone management for the AutoTaskTracker system."""
    
    def __init__(self):
        """Initialize timezone manager with system timezone detection."""
        self._local_timezone = self._detect_local_timezone()
        self._utc_offset_hours = self._calculate_utc_offset()
        logger.info(f"Initialized TimezoneManager with UTC offset: {self._utc_offset_hours} hours")
    
    def _detect_local_timezone(self) -> timezone:
        """Detect the local system timezone."""
        try:
            # Get the current UTC offset accounting for DST
            if time.daylight:
                offset_seconds = -time.altzone  # DST offset (negative because altzone is negative)
            else:
                offset_seconds = -time.timezone  # Standard offset
                
            return timezone(timedelta(seconds=offset_seconds))
        except Exception as e:
            logger.warning(f"Failed to detect local timezone, using UTC: {e}")
            return timezone.utc
    
    def _calculate_utc_offset(self) -> float:
        """Calculate UTC offset in hours for the current local timezone."""
        try:
            if time.daylight:
                return time.altzone / 3600  # DST offset in hours
            else:
                return time.timezone / 3600  # Standard offset in hours
        except (OSError, AttributeError, ValueError) as e:
            logger.debug(f"Error getting timezone offset: {e}")
            return 0.0
    
    def local_to_utc(self, local_dt: datetime) -> datetime:
        """Convert local datetime to UTC for database storage.
        
        Args:
            local_dt: Local datetime (timezone-naive)
            
        Returns:
            UTC datetime for database storage
        """
        if local_dt is None:
            return None
            
        # Add local timezone info if naive
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=self._local_timezone)
        
        # Convert to UTC
        utc_dt = local_dt.astimezone(timezone.utc)
        
        # Return as naive UTC datetime (matching Pensieve's storage format)
        return utc_dt.replace(tzinfo=None)
    
    def utc_to_local(self, utc_dt: datetime) -> datetime:
        """Convert UTC datetime from database to local datetime for display.
        
        Args:
            utc_dt: UTC datetime from database (timezone-naive)
            
        Returns:
            Local datetime for display
        """
        if utc_dt is None:
            return None
            
        # Add UTC timezone info if naive
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        # Convert to local timezone
        local_dt = utc_dt.astimezone(self._local_timezone)
        
        # Return as naive local datetime
        return local_dt.replace(tzinfo=None)
    
    def convert_query_range(self, start_local: datetime, end_local: datetime) -> tuple[datetime, datetime]:
        """Convert local time range to UTC for database queries.
        
        Args:
            start_local: Start time in local timezone
            end_local: End time in local timezone
            
        Returns:
            Tuple of (start_utc, end_utc) for database queries
        """
        start_utc = self.local_to_utc(start_local)
        end_utc = self.local_to_utc(end_local)
        
        logger.debug(f"Converted query range: {start_local} - {end_local} (local) -> {start_utc} - {end_utc} (UTC)")
        
        return start_utc, end_utc
    
    def format_for_display(self, dt: datetime, format_12h: bool = False) -> str:
        """Format datetime for user display.
        
        Args:
            dt: Datetime to format (should be in local timezone)
            format_12h: Whether to use 12-hour format
            
        Returns:
            Formatted time string
        """
        if dt is None:
            return "Unknown"
            
        if format_12h:
            return dt.strftime("%I:%M %p")  # 02:30 PM
        else:
            return dt.strftime("%H:%M")     # 14:30
    
    def format_time_period(self, start_dt: datetime, end_dt: datetime, format_12h: bool = False) -> str:
        """Format time period for display.
        
        Args:
            start_dt: Start datetime (local timezone)
            end_dt: End datetime (local timezone)
            format_12h: Whether to use 12-hour format
            
        Returns:
            Formatted time period string like [14:30-15:45] or [2:30-3:45 PM]
        """
        if start_dt is None or end_dt is None:
            return "[Unknown]"
            
        start_str = self.format_for_display(start_dt, format_12h)
        end_str = self.format_for_display(end_dt, format_12h)
        
        return f"[{start_str}-{end_str}]"
    
    def validate_pensieve_timestamp(self, db_timestamp: str, expected_local_time: Optional[datetime] = None) -> bool:
        """Validate that a Pensieve database timestamp follows expected UTC conventions.
        
        Args:
            db_timestamp: Timestamp string from Pensieve database
            expected_local_time: Optional expected local time for validation
            
        Returns:
            True if timestamp follows expected format and timezone
        """
        try:
            utc_dt = datetime.fromisoformat(db_timestamp)
            
            if expected_local_time:
                # Convert expected local time to UTC and compare
                expected_utc = self.local_to_utc(expected_local_time)
                diff_seconds = abs((utc_dt - expected_utc).total_seconds())
                
                # Allow up to 60 seconds difference for processing delays
                if diff_seconds > 60:
                    logger.warning(f"Pensieve timestamp validation failed: {diff_seconds}s difference")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate Pensieve timestamp '{db_timestamp}': {e}")
            return False
    
    @property
    def local_timezone(self) -> timezone:
        """Get the local timezone."""
        return self._local_timezone
    
    @property
    def utc_offset_hours(self) -> float:
        """Get the UTC offset in hours."""
        return self._utc_offset_hours


# Singleton instance
_timezone_manager: Optional[TimezoneManager] = None


def get_timezone_manager() -> TimezoneManager:
    """Get the singleton TimezoneManager instance."""
    global _timezone_manager
    if _timezone_manager is None:
        _timezone_manager = TimezoneManager()
    return _timezone_manager


def local_to_utc(local_dt: datetime) -> datetime:
    """Convenience function to convert local time to UTC."""
    return get_timezone_manager().local_to_utc(local_dt)


def utc_to_local(utc_dt: datetime) -> datetime:
    """Convenience function to convert UTC time to local."""
    return get_timezone_manager().utc_to_local(utc_dt)


def format_time_period(start_dt: datetime, end_dt: datetime, format_12h: bool = False) -> str:
    """Convenience function to format time period."""
    return get_timezone_manager().format_time_period(start_dt, end_dt, format_12h)