import logging
logger = logging.getLogger(__name__)

"""Data display components for dashboards."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from PIL import Image


class TaskGroup:
    """Component for displaying grouped tasks."""
    
    @staticmethod
    def render(
        window_title: str,
        duration_minutes: float,
        tasks: List[str],
        category: str,
        timestamp: datetime,
        end_time: Optional[datetime] = None,
        screenshot_path: Optional[str] = None,
        show_screenshot: bool = True,
        expanded: bool = False
    ):
        """Render a task group.
        
        Args:
            window_title: Window/application title
            duration_minutes: Duration in minutes
            tasks: List of tasks/activities
            category: Task category
            timestamp: When the task started
            end_time: When the task ended (optional)
            screenshot_path: Optional path to screenshot
            show_screenshot: Whether to show screenshot
            expanded: Whether to expand by default
        """
        # Format time period display using proper timezone manager
        from ...core.timezone_manager import get_timezone_manager
        
        tz_manager = get_timezone_manager()
        if end_time:
            time_period = tz_manager.format_time_period(timestamp, end_time, format_12h=False)
            confidence_indicator = "🟢" if duration_minutes >= 2 else "🟡" if duration_minutes >= 1 else "🔴"
        else:
            time_period = f"[{tz_manager.format_for_display(timestamp)}]"
            confidence_indicator = "🔴"  # Low confidence without end time
        
        # Main header with enhanced format: "Task Name (duration) [time-period] confidence"
        header = f"**{window_title}** ({duration_minutes:.0f} min) {time_period} {confidence_indicator}"
        
        with st.expander(header, expanded=expanded):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Show category with icon
                category_display = f"🏷️ {category}"
                if end_time:
                    gap_minutes = (end_time - timestamp).total_seconds() / 60
                    if gap_minutes > duration_minutes * 1.5:
                        category_display += f" ⚠️ ({gap_minutes - duration_minutes:.0f}min gaps)"
                st.caption(category_display)
                
                if tasks:
                    st.markdown("**Activities:**")
                    for task in tasks[:5]:  # Limit to 5 tasks
                        st.markdown(f"• {task}")
                    if len(tasks) > 5:
                        st.caption(f"... and {len(tasks) - 5} more")
                        
            with col2:
                if show_screenshot and screenshot_path and os.path.exists(screenshot_path):
                    try:
                        img = Image.open(screenshot_path)
                        img.thumbnail((200, 200))
                        st.image(img, use_container_width=True)
                    except Exception:
                        st.caption("Screenshot unavailable")
                        

class ActivityCard:
    """Component for displaying individual activities."""
    
    @staticmethod
    def render(
        title: str,
        timestamp: datetime,
        category: str,
        ocr_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        screenshot_path: Optional[str] = None,
        compact: bool = False
    ):
        """Render an activity card.
        
        Args:
            title: Activity title
            timestamp: When it occurred
            category: Activity category
            ocr_text: Optional OCR text
            metadata: Optional additional metadata
            screenshot_path: Optional screenshot path
            compact: Whether to use compact layout
        """
        if compact:
            # Compact single-line display
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.text(title[:50] + "..." if len(title) > 50 else title)
            with cols[1]:
                st.text(category)
            with cols[2]:
                st.text(timestamp.strftime("%H:%M"))
        else:
            # Full card display
            with st.container():
                st.markdown(f"### {title}")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.caption(f"📅 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.caption(f"🏷️ {category}")
                    
                    if ocr_text and len(ocr_text.strip()) > 0:
                        with st.expander("📝 OCR Text"):
                            st.text(ocr_text[:500])
                            
                    if metadata:
                        with st.expander("🔍 Metadata"):
                            for key, value in metadata.items():
                                st.text(f"{key}: {value}")
                                
                with col2:
                    if screenshot_path and os.path.exists(screenshot_path):
                        try:
                            img = Image.open(screenshot_path)
                            img.thumbnail((300, 300))
                            st.image(img, use_container_width=True)
                        except Exception:
                            pass
                            
                st.divider()
                

class NoDataMessage:
    """Component for displaying no-data messages."""
    
    @staticmethod
    def render(
        message: str = "No data available",
        suggestions: Optional[List[str]] = None,
        icon: str = "📊"
    ):
        """Render a no-data message.
        
        Args:
            message: Main message to display
            suggestions: Optional list of suggestions
            icon: Icon to display
        """
        st.info(f"{icon} {message}")
        
        if suggestions:
            st.markdown("**Try these:**")
            for suggestion in suggestions:
                st.markdown(f"• {suggestion}")
                

class DataTable:
    """Enhanced data table component."""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        columns: Optional[List[str]] = None,
        column_config: Optional[Dict[str, Any]] = None,
        use_container_width: bool = True,
        show_index: bool = False,
        enable_search: bool = True
    ):
        """Render an enhanced data table.
        
        Args:
            data: DataFrame to display
            columns: Columns to display (all if None)
            column_config: Column configuration for st.dataframe
            use_container_width: Whether to use full width
            show_index: Whether to show index
            enable_search: Whether to enable search
        """
        if columns:
            data = data[columns]
            
        if enable_search and len(data) > 10:
            search = st.text_input("🔍 Search table...", key="table_search")
            if search:
                # Search across all string columns
                mask = data.astype(str).apply(
                    lambda x: x.str.contains(search, case=False, na=False)
                ).any(axis=1)
                data = data[mask]
                
        st.dataframe(
            data,
            column_config=column_config,
            use_container_width=use_container_width,
            hide_index=not show_index
        )