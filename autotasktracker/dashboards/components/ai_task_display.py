"""AI Task Display Components for AutoTaskTracker.

This module provides components for displaying AI-processed task information,
including VLM results, extracted tasks, and processing status indicators.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class AITaskDisplay:
    """Component for displaying AI-extracted task information."""
    
    @staticmethod
    def render_task_with_ai_insights(
        task_data: Dict[str, Any],
        show_raw: bool = False
    ) -> None:
        """Render a task with AI-extracted insights.
        
        Args:
            task_data: Dictionary containing task information and AI metadata
            show_raw: Whether to show raw metadata for debugging
        """
        if not task_data:
            st.warning("No task data provided")
            return
            
        # Extract task text and metadata
        task_text = task_data.get('title', 'Untitled Task')
        metadata = task_data.get('metadata', {}) if isinstance(task_data.get('metadata'), dict) else {}
        
        # Show main task with processing status
        with st.container():
            col1, col2 = st.columns([1, 12])
            
            with col1:
                # Show status indicator
                status_emoji = AITaskDisplay._get_processing_status_emoji(task_data)
                st.write(f"{status_emoji}")
                
            with col2:
                # Show main task with formatting
                st.markdown(f"**{task_text}**")
                
                # Show timestamp if available
                if 'timestamp' in task_data:
                    from datetime import datetime
                    try:
                        timestamp = task_data['timestamp']
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp)
                        st.caption(f"🕒 {timestamp.strftime('%H:%M:%S')}")
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not parse timestamp: {e}")
                
                # Show extracted tasks if available
                tasks = metadata.get('tasks')
                if tasks and isinstance(tasks, list) and tasks:
                    with st.expander(f"📋 {len(tasks)} Tasks"):
                        for i, task in enumerate(tasks, 1):
                            if isinstance(task, dict):
                                task_text = task.get('title') or task.get('task') or str(task)
                                st.markdown(f"{i}. {task_text}")
                            else:
                                st.markdown(f"{i}. {task}")
                
                # Show extracted subtasks if available
                subtasks = metadata.get('subtasks')
                if subtasks and isinstance(subtasks, list) and subtasks:
                    with st.expander(f"📝 {len(subtasks)} Subtasks"):
                        for i, subtask in enumerate(subtasks, 1):
                            st.markdown(f"{i}. {subtask}")
                
                # Show VLM result if available
                vlm_result = metadata.get('vlm_result')
                if vlm_result:
                    with st.expander("🔍 VLM Analysis", expanded=False):
                        if isinstance(vlm_result, str):
                            st.markdown(vlm_result)
                        elif isinstance(vlm_result, dict):
                            st.json(vlm_result)
                        else:
                            st.write(vlm_result)
                
                # Show raw metadata if requested
                if show_raw:
                    with st.expander("🔧 Raw Metadata", expanded=False):
                        st.json(task_data, expanded=False)
    
    @staticmethod
    def _get_processing_status_emoji(metadata: Dict[str, Any]) -> str:
        """Get emoji indicating processing status."""
        if not metadata:
            return "❓"  # Unknown status
            
        has_vlm = 'vlm_result' in metadata and metadata['vlm_result']
        has_ocr = 'ocr_text' in metadata and metadata.get('ocr_text')
        has_tasks = 'tasks' in metadata and metadata.get('tasks')
        
        if has_vlm and has_ocr and has_tasks:
            return "✅"  # Fully processed
        elif has_ocr and has_tasks:
            return "🔍"  # OCR and tasks processed
        elif has_ocr:
            return "📝"  # Only OCR processed
        else:
            return "⏳"  # Processing
    
    @staticmethod
    def render_processing_status(metadata: Dict[str, Any]) -> None:
        """Render a status indicator for AI processing."""
        if not metadata:
            return
            
        status_items = []
        
        # Check OCR status
        ocr_status = "✅" if metadata.get('ocr_text') else "❌"
        status_items.append(f"OCR: {ocr_status}")
        
        # Check VLM status
        vlm_status = "✅" if metadata.get('vlm_result') else "❌"
        status_items.append(f"VLM: {vlm_status}")
        
        # Check task extraction status
        tasks_status = "✅" if metadata.get('tasks') else "❌"
        status_items.append(f"Tasks: {tasks_status}")
        
        st.caption(" | ".join(status_items))

    @classmethod
    def render_task_group(
        cls,
        window_title: str,
        duration_minutes: float,
        tasks: List[Dict[str, Any]],
        category: str,
        timestamp: datetime,
        end_time: Optional[datetime] = None,
        screenshot_path: Optional[str] = None,
        show_screenshot: bool = True,
        expanded: bool = False,
        use_ai_display: bool = True
    ) -> None:
        """Render a task group with AI insights.
        
        This is a drop-in replacement for TaskGroup.render() that includes
        AI-extracted task information.
        """
        # Format time period display
        from autotasktracker.core.timezone_manager import get_timezone_manager
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
                
                # Show tasks with AI or basic display
                if tasks:
                    if use_ai_display:
                        st.markdown("### 📋 Tasks")
                        for task in tasks[:5]:  # Limit to 5 tasks
                            cls.render_task_with_ai_insights(task)
                            
                            # Add a subtle divider between tasks (but not after the last one)
                            if task != tasks[-1] and task != tasks[4]:  # Not the last task in the list
                                st.divider()
                        
                        if len(tasks) > 5:
                            st.caption(f"... and {len(tasks) - 5} more tasks")
                    else:
                        # Basic task display without AI enhancements
                        st.markdown("### 📋 Tasks")
                        for task in tasks[:5]:  # Limit to 5 tasks
                            if isinstance(task, dict):
                                task_text = task.get('title', task.get('text', 'Untitled Task'))
                                st.markdown(f"• {task_text}")
                            else:
                                st.markdown(f"• {task}")
                        
                        if len(tasks) > 5:
                            st.caption(f"... and {len(tasks) - 5} more")
            
            with col2:
                # Show screenshot if available
                if show_screenshot and screenshot_path:
                    try:
                        import os
                        from PIL import Image
                        
                        if os.path.exists(screenshot_path):
                            img = Image.open(screenshot_path)
                            img.thumbnail((200, 200))
                            st.image(img, use_column_width=True)
                        else:
                            st.info("No screenshot available")
                    except Exception as e:
                        logger.warning(f"Failed to load image {screenshot_path}: {e}")
                        st.warning("Screenshot unavailable")
                
                # Show processing status
                if tasks and isinstance(tasks[0], dict):
                    cls.render_processing_status(tasks[0])
                    
                # Add a button to show raw data for debugging
                if st.session_state.get('show_debug_info', False):
                    with st.expander("🔍 Debug Info", expanded=False):
                        st.json({
                            'window_title': window_title,
                            'task_count': len(tasks),
                            'first_task': tasks[0] if tasks else None
                        }, expanded=False)
