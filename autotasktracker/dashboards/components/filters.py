"""Filter components for dashboards."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Tuple, List, Optional
from autotasktracker.core import DatabaseManager


class TimeFilterComponent:
    """Reusable time filter component."""
    
    TIME_OPTIONS = [
        "Today", "Yesterday", "This Week", 
        "Last 7 Days", "This Month", "Last 30 Days", "All Time"
    ]
    
    @staticmethod
    def get_smart_default(db_manager=None) -> str:
        """Get smart default based on actual data availability.
        
        Args:
            db_manager: Database manager to check data
            
        Returns:
            Best default time filter based on data
        """
        if db_manager is None:
            return "Last 7 Days"  # Safe default
            
        try:
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # Check different time periods for data availability
            time_periods = {
                "Today": (now.replace(hour=0, minute=0, second=0, microsecond=0), now),
                "Yesterday": (
                    (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                    (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
                ),
                "Last 7 Days": (now - timedelta(days=7), now),
                "Last 30 Days": (now - timedelta(days=30), now)
            }
            
            # Check each period for substantial data
            period_scores = {}
            for period_name, (start_date, end_date) in time_periods.items():
                try:
                    tasks_df = db_manager.fetch_tasks(start_date=start_date, end_date=end_date, limit=50)
                    task_count = len(tasks_df)
                    
                    # Score based on task count and recency
                    recency_weight = 1.0 if period_name in ["Today", "Yesterday"] else 0.7
                    period_scores[period_name] = task_count * recency_weight
                except Exception:
                    period_scores[period_name] = 0
            
            # Find the best period with substantial data (at least 5 tasks)
            best_period = None
            best_score = 0
            
            # Prioritize recent periods if they have good data
            for period in ["Today", "Yesterday", "Last 7 Days", "Last 30 Days"]:
                score = period_scores.get(period, 0)
                if score >= 5 and score > best_score:  # At least 5 tasks
                    best_period = period
                    best_score = score
            
            # If no period has enough data, default to Last 7 Days
            return best_period if best_period else "Last 7 Days"
            
        except Exception:
            return "Last 7 Days"  # Safe fallback
    
    @staticmethod
    def render(key: str = "time_filter", default: Optional[str] = None, db_manager=None) -> str:
        """Render time filter selectbox.
        
        Args:
            key: Session state key
            default: Default selection (auto-detected if None)
            db_manager: Database manager for smart defaults
            
        Returns:
            Selected time filter
        """
        if default is None:
            default = TimeFilterComponent.get_smart_default(db_manager)
            
        current_value = st.session_state.get(key, default)
        
        return st.selectbox(
            "Time Period",
            TimeFilterComponent.TIME_OPTIONS,
            index=TimeFilterComponent.TIME_OPTIONS.index(current_value),
            key=key,
            help="Automatically selected based on your activity data"
        )
    
    @staticmethod
    def get_time_range(time_filter: str) -> Tuple[datetime, datetime]:
        """Convert time filter to datetime range.
        
        Args:
            time_filter: Time filter string
            
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
        

class CategoryFilterComponent:
    """Reusable category filter component."""
    
    DEFAULT_CATEGORIES = [
        "All Categories",
        "Development",
        "Communication", 
        "Productivity",
        "Browser",
        "System",
        "Other"
    ]
    
    @staticmethod
    def render(
        categories: Optional[List[str]] = None,
        key: str = "category_filter",
        multiselect: bool = False
    ) -> List[str]:
        """Render category filter.
        
        Args:
            categories: List of categories to show (uses defaults if None)
            key: Session state key
            multiselect: Whether to allow multiple selections
            
        Returns:
            Selected category/categories (empty list means all categories)
        """
        if categories is None:
            categories = CategoryFilterComponent.DEFAULT_CATEGORIES
            
        if multiselect:
            # FIXED: Default to empty list (all categories) instead of selecting all
            selected = st.multiselect(
                "Categories",
                categories[1:],  # Skip "All Categories" for multiselect
                default=st.session_state.get(key, []),  # Empty default = all categories
                key=key,
                help="Leave empty to show all categories"
            )
            return selected  # Empty list means all categories
        else:
            selected = st.selectbox(
                "Category",
                categories,
                index=0,
                key=key
            )
            return [] if selected == "All Categories" else [selected]