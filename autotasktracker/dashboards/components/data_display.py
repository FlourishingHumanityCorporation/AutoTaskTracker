import logging
logger = logging.getLogger(__name__)

"""Data display components for dashboards."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from PIL import Image

# Enhanced search capabilities  
try:
    from ...pensieve.enhanced_search import get_enhanced_search, SearchQuery
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    ENHANCED_SEARCH_AVAILABLE = False


class EnhancedSearch:
    """Enhanced search component with semantic capabilities."""
    
    @staticmethod
    def render(
        key: str = "enhanced_search",
        placeholder: str = "🔍 Search...",
        show_search_type: bool = True,
        default_type: str = "Text"
    ) -> Dict[str, Any]:
        """Render enhanced search component.
        
        Args:
            key: Unique key for the search component
            placeholder: Placeholder text for search input
            show_search_type: Whether to show search type selector
            default_type: Default search type
            
        Returns:
            Dictionary with search query and type
        """
        search_result = {"query": "", "type": "text", "has_query": False}
        
        if show_search_type and ENHANCED_SEARCH_AVAILABLE:
            col1, col2 = st.columns([3, 1])
            with col1:
                query = st.text_input(placeholder, key=f"{key}_input")
            with col2:
                search_type = st.selectbox(
                    "Type",
                    ["Text", "Semantic", "Hybrid"],
                    index=["Text", "Semantic", "Hybrid"].index(default_type) if default_type in ["Text", "Semantic", "Hybrid"] else 0,
                    key=f"{key}_type"
                )
        else:
            query = st.text_input(placeholder, key=f"{key}_input")
            search_type = default_type
        
        if query:
            search_result.update({
                "query": query,
                "type": search_type.lower(),
                "has_query": True
            })
            
        return search_result
    
    @staticmethod
    def execute_search(search_result: Dict[str, Any], data: pd.DataFrame) -> pd.DataFrame:
        """Execute search on DataFrame.
        
        Args:
            search_result: Result from render() method
            data: DataFrame to search
            
        Returns:
            Filtered DataFrame
        """
        if not search_result["has_query"]:
            return data
            
        query = search_result["query"]
        search_type = search_result["type"]
        
        if (ENHANCED_SEARCH_AVAILABLE and 
            search_type in ["semantic", "hybrid"] and 
            len(query) > 3):
            
            try:
                enhanced_search = get_enhanced_search()
                search_query = SearchQuery(
                    query=query,
                    search_type=search_type,
                    limit=len(data),
                    min_relevance=0.3
                )
                
                # Get entity IDs that match the search
                search_results = enhanced_search.search(search_query)
                matching_ids = {result.entity.id for result in search_results}
                
                # Filter data to matching entities if ID column exists
                if 'id' in data.columns:
                    filtered_data = data[data['id'].isin(matching_ids)]
                    if len(search_results) > 0:
                        st.info(f"🎯 Found {len(search_results)} semantic matches")
                    return filtered_data
                    
            except Exception as e:
                logger.debug(f"Enhanced search failed, falling back to text: {e}")
        
        # Fallback to basic text search
        mask = data.astype(str).apply(
            lambda x: x.str.contains(query, case=False, na=False)
        ).any(axis=1)
        return data[mask]


class TaskGroup:
    """Component for displaying grouped tasks with AI-enhanced visualization.
    
    This component can handle both traditional task lists and AI-enriched task data.
    For AI-enhanced display, tasks should be dictionaries containing AI metadata.
    """
    
    @staticmethod
    def render(
        window_title: str,
        duration_minutes: float,
        tasks: List[Any],
        category: str,
        timestamp: datetime,
        end_time: Optional[datetime] = None,
        screenshot_path: Optional[str] = None,
        show_screenshot: bool = True,
        expanded: bool = False,
        use_ai_display: bool = True
    ) -> None:
        """Render a task group with optional AI-enhanced visualization.
        
        Args:
            window_title: Window/application title
            duration_minutes: Duration in minutes
            tasks: List of tasks/activities (can be strings or dicts with AI metadata)
            category: Task category
            timestamp: When the task started
            end_time: When the task ended (optional)
            screenshot_path: Optional path to screenshot
            show_screenshot: Whether to show screenshot
            expanded: Whether to expand by default
            use_ai_display: Whether to use AI-enhanced display when possible
        """
        # Try to use AI display if available and requested
        if use_ai_display and tasks and isinstance(tasks[0], dict):
            from .ai_task_display import AITaskDisplay
            AITaskDisplay.render_task_group(
                window_title=window_title,
                duration_minutes=duration_minutes,
                tasks=tasks,
                category=category,
                timestamp=timestamp,
                end_time=end_time,
                screenshot_path=screenshot_path,
                show_screenshot=show_screenshot,
                expanded=expanded
            )
            return
            
        # Fall back to basic display for non-AI tasks or if AI display is disabled
        TaskGroup._render_basic(
            window_title=window_title,
            duration_minutes=duration_minutes,
            tasks=tasks,
            category=category,
            timestamp=timestamp,
            end_time=end_time,
            screenshot_path=screenshot_path,
            show_screenshot=show_screenshot,
            expanded=expanded
        )
    
    @staticmethod
    def _render_basic(
        window_title: str,
        duration_minutes: float,
        tasks: List[Any],
        category: str,
        timestamp: datetime,
        end_time: Optional[datetime] = None,
        screenshot_path: Optional[str] = None,
        show_screenshot: bool = True,
        expanded: bool = False
    ) -> None:
        """Render a basic task group without AI enhancements."""
        from ...core.timezone_manager import get_timezone_manager
        import os
        from PIL import Image
        
        tz_manager = get_timezone_manager()
        if end_time:
            time_period = tz_manager.format_time_period(timestamp, end_time, format_12h=False)
            confidence_indicator = "🟢" if duration_minutes >= 2 else "🟡" if duration_minutes >= 1 else "🔴"
        else:
            time_period = f"[{tz_manager.format_for_display(timestamp)}]"
            confidence_indicator = "🔴"  # Low confidence without end time
        
        # Main header with enhanced format
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
                        task_text = task.get('title', task) if isinstance(task, dict) else str(task)
                        st.markdown(f"• {task_text}")
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
                        except Exception as e:
                            logger.debug(f"Failed to load screenshot thumbnail: {e}")
                            
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
            # Use enhanced search component
            search_result = EnhancedSearch.render(
                key="table_search",
                placeholder="🔍 Search table..."
            )
            
            if search_result["has_query"]:
                data = EnhancedSearch.execute_search(search_result, data)
                
        st.dataframe(
            data,
            column_config=column_config,
            use_container_width=use_container_width,
            hide_index=not show_index
        )