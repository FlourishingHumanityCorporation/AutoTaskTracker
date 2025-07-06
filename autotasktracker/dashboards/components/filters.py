"""Filter components for dashboards."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Tuple, List, Optional


class TimeFilterComponent:
    """Reusable time filter component."""
    
    TIME_OPTIONS = [
        "Today", "Yesterday", "This Week", 
        "Last 7 Days", "This Month", "Last 30 Days", "All Time"
    ]
    
    
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
            from .smart_defaults import SmartDefaultsComponent
            default = SmartDefaultsComponent.get_time_period_default(db_manager)
            
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