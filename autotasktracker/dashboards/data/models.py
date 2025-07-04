"""Data models for dashboards."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class Task:
    """Represents a task extracted from screenshots."""
    id: int
    title: str
    category: str
    timestamp: datetime
    duration_minutes: float
    window_title: str
    ocr_text: Optional[str] = None
    screenshot_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return self.duration_minutes / 60
        

@dataclass
class Activity:
    """Represents a single activity/screenshot."""
    id: int
    timestamp: datetime
    window_title: str
    category: str
    ocr_text: Optional[str] = None
    tasks: Optional[List[str]] = None
    screenshot_path: Optional[str] = None
    active_window: Optional[str] = None
    

@dataclass 
class TaskGroup:
    """Represents a group of related tasks."""
    window_title: str
    category: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    task_count: int
    tasks: List[Task]
    
    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return self.duration_minutes / 60
        

@dataclass
class DailyMetrics:
    """Daily productivity metrics."""
    date: datetime
    total_tasks: int
    total_duration_minutes: float
    unique_windows: int
    categories: Dict[str, int]
    productive_time_minutes: float
    most_used_apps: List[tuple[str, float]]  # (app_name, minutes)
    peak_hours: List[int]  # Hours with most activity
    
    @property
    def total_duration_hours(self) -> float:
        """Get total duration in hours."""
        return self.total_duration_minutes / 60
        
    @property
    def productive_percentage(self) -> float:
        """Get productive time percentage."""
        if self.total_duration_minutes == 0:
            return 0
        return (self.productive_time_minutes / self.total_duration_minutes) * 100