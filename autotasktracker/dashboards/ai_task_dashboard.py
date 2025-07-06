"""AI Task Extraction Dashboard for AutoTaskTracker.

This dashboard displays AI-extracted tasks from screenshots with filtering and search capabilities.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components.ai_task_display import AITaskDisplay
from autotasktracker.dashboards.components.common_sidebar import CommonSidebar, SidebarSection
from autotasktracker.core import DatabaseManager
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)

class AITaskDashboard(BaseDashboard):
    """Dashboard for viewing AI-extracted tasks from screenshots."""
    
    def __init__(self):
        # Initialize the base dashboard first
        super().__init__(title="AI Task Explorer", icon="🤖", port=get_config().TASK_BOARD_PORT)
        
        # Initialize database connection
        self._db_manager = DatabaseManager()
        self.screenshots_dir = Path(get_config().SCREENSHOTS_DIR)
        
        # Initialize session state
        if 'selected_task' not in st.session_state:
            st.session_state.selected_task = None
        if 'task_filters' not in st.session_state:
            st.session_state.task_filters = {
                'status': 'all',
                'date_range': 7,  # days
                'search_query': ''
            }
    
    @property
    def db_manager(self):
        """Get the database manager instance."""
        return self._db_manager
        
    def _get_tasks(self, time_filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Fetch tasks from the database with current filters."""
        try:
            # Use time filter from CommonSidebar if provided, otherwise use session state
            if time_filter:
                start_date = time_filter.get('start_date')
                end_date = time_filter.get('end_date')
            else:
                # Fallback to session state date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=st.session_state.task_filters['date_range'])
            
            # Get tasks using the fetch_tasks method
            df = self.db_manager.fetch_tasks(
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Adjust limit as needed
            )
            
            if df.empty:
                logger.info("No tasks found in the database")
                return []
            
            # Ensure required columns exist
            for col in ['title', 'description', 'status', 'created_at']:
                if col not in df.columns:
                    df[col] = ''
            
            # Convert timestamp to string if it's a datetime
            if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
                df['created_at'] = df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Apply status filter if needed
            if st.session_state.task_filters['status'] != 'all':
                if 'status' in df.columns:
                    df = df[df['status'] == st.session_state.task_filters['status']]
            
            # Apply search filter if provided
            if st.session_state.task_filters['search_query']:
                search_query = st.session_state.task_filters['search_query'].lower()
                search_columns = []
                
                # Check which columns exist in the dataframe
                for col in ['title', 'description', 'ai_metadata', 'window_title', 'ocr_text']:
                    if col in df.columns:
                        search_columns.append(col)
                
                if search_columns:
                    # Create a mask for search across all available columns
                    mask = pd.Series(False, index=df.index)
                    for col in search_columns:
                        # Convert column to string and handle NaN values
                        col_series = df[col].astype(str).str.lower()
                        mask = mask | col_series.str.contains(search_query, na=False)
                    
                    df = df[mask]
            
            # Convert to list of dicts and ensure all required fields exist
            tasks = []
            for _, row in df.iterrows():
                task = row.to_dict()
                
                # Ensure required fields exist with sensible defaults
                task.setdefault('title', 'Untitled Task')
                task.setdefault('description', '')
                task.setdefault('status', 'new')
                task.setdefault('created_at', datetime.now().isoformat())
                task.setdefault('ai_metadata', {})
                task.setdefault('screenshot_path', task.get('filepath', ''))
                
                # If no title, try to get it from other fields
                if not task['title'] or task['title'] == 'Untitled Task':
                    task['title'] = task.get('window_title', 'Untitled Task')
                
                tasks.append(task)
            
            logger.info(f"Fetched {len(tasks)} tasks from the database")
            return tasks
            
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}", exc_info=True)
            st.error(f"Error loading tasks: {e}")
            return []
    
    def _render_filters(self) -> Dict[str, Any]:
        """Render the filter controls using CommonSidebar."""
        # Create custom sections for AI task specific filters
        ai_filters_section = SidebarSection(
            title="🔍 AI Task Filters",
            content=lambda: self._render_ai_filters()
        )
        
        # Render CommonSidebar with custom sections
        sidebar_data = CommonSidebar.render(
            title="AI Task Explorer",
            icon="🤖",
            db_manager=self.db_manager,
            custom_sections=[ai_filters_section],
            session_controls_position="bottom"
        )
        
        return sidebar_data
    
    def _render_ai_filters(self) -> None:
        """Render AI-specific filter controls."""
        # Status filter
        status = st.selectbox(
            "Status",
            ['all', 'pending', 'in_progress', 'completed'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key="ai_status_filter"
        )
        
        # Search box
        search_query = st.text_input("Search tasks", key="ai_search_filter")
        
        # Update filters in session state
        if status != st.session_state.task_filters['status']:
            st.session_state.task_filters['status'] = status
        if search_query != st.session_state.task_filters['search_query']:
            st.session_state.task_filters['search_query'] = search_query
    
    def _render_task_list(self, tasks: List[Dict[str, Any]]) -> None:
        """Render the list of tasks."""
        st.header("📋 Extracted Tasks")
        
        if not tasks:
            st.info("No tasks found matching your criteria.")
            return
        
        # Group tasks by date
        tasks_by_date = {}
        for task in tasks:
            # Safely get created_at with default to current time if not available
            created_at = task.get('created_at', datetime.now().isoformat())
            try:
                # Extract date part safely
                task_date = created_at.split('T')[0] if 'T' in created_at else created_at.split(' ')[0]
                if task_date not in tasks_by_date:
                    tasks_by_date[task_date] = []
                tasks_by_date[task_date].append(task)
            except (IndexError, AttributeError) as e:
                logger.warning(f"Error parsing date from task: {task}. Error: {e}")
                # Use a default date for tasks with invalid dates
                default_date = datetime.now().strftime('%Y-%m-%d')
                if default_date not in tasks_by_date:
                    tasks_by_date[default_date] = []
                tasks_by_date[default_date].append(task)
        
        # Display tasks grouped by date
        for date, date_tasks in sorted(tasks_by_date.items(), reverse=True):
            st.subheader(date)
            
            for task in date_tasks:
                # Safely get title with a default if not available
                title = task.get('title', 'Untitled Task')
                if not title or title == 'Untitled Task':
                    # Try to get a better title from other fields
                    title = task.get('description', 'Untitled Task')
                    if len(title) > 50:
                        title = title[:47] + '...'
                
                with st.expander(title):
                    try:
                        AITaskDisplay.render_task_with_ai_insights(task)
                        
                        # Show screenshot if available
                        try:
                            screenshot_path = None
                            # Try multiple possible path fields
                            for path_field in ['screenshot_path', 'filepath', 'screenshot']:
                                if task.get(path_field):
                                    screenshot_path = Path(str(task[path_field]))
                                    # If path is relative, try resolving against screenshots_dir
                                    if not screenshot_path.is_absolute():
                                        screenshot_path = self.screenshots_dir / screenshot_path
                                    if screenshot_path.exists():
                                        break
                                    screenshot_path = None
                            
                            if screenshot_path and screenshot_path.exists():
                                try:
                                    st.image(
                                        str(screenshot_path), 
                                        caption=f"Screenshot: {screenshot_path.name}",
                                        use_container_width=True
                                    )
                                except Exception as img_error:
                                    logger.warning(f"Error loading image {screenshot_path}: {img_error}")
                                    st.warning(f"Could not load image: {screenshot_path.name}")
                                    st.json({
                                        "error": "Image load error",
                                        "path": str(screenshot_path),
                                        "details": str(img_error)
                                    })
                            else:
                                st.warning("No screenshot available for this task")
                                if screenshot_path:
                                    st.info(f"Expected path: {screenshot_path}")
                        except Exception as e:
                            logger.error(f"Error handling screenshot for task: {e}", exc_info=True)
                            st.error(f"Error loading screenshot: {e}")
                    except Exception as e:
                        st.error(f"Error displaying task: {e}")
                        st.json({k: v for k, v in task.items() if not k.startswith('_')})
                            
    def run(self):
        """Run the AI Task Explorer dashboard."""
        try:
            # Set page config
            st.set_page_config(
                page_title="AI Task Explorer",
                page_icon="🤖",
                layout="wide"
            )
            
            # Add title and description
            st.title("🤖 AI Task Explorer")
            st.markdown("""
            View and manage tasks extracted from your screenshots using AI.
            Use the filters on the left to narrow down the results.
            """)
            
            # Show Pensieve health status
            self.show_health_status()
            
            # Add auto-refresh
            self.add_auto_refresh(interval_seconds=60)  # Refresh every 60 seconds
            
            # Render sidebar with filters and get filter data
            sidebar_data = self._render_filters()
            
            # Get and render tasks using time filter from sidebar
            tasks = self._get_tasks(time_filter=sidebar_data.get('time_filter'))
            
            # Show task metrics
            self._render_task_metrics(tasks)
            
            # Show task list
            self._render_task_list(tasks)
            
        except Exception as e:
            self.handle_error(e, "running the AI Task Explorer dashboard")
            
    def _render_task_metrics(self, tasks: List[Dict[str, Any]]) -> None:
        """Render task metrics."""
        if not tasks:
            return
            
        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get('status') == 'completed')
        in_progress_tasks = sum(1 for t in tasks if t.get('status') == 'in_progress')
        pending_tasks = total_tasks - completed_tasks - in_progress_tasks
        
        # Get tasks created today
        try:
            from autotasktracker.dashboards.data.repositories import TaskRepository
            task_repo = TaskRepository()
            tasks_today = task_repo.count_tasks_today()
        except Exception as e:
            logger.warning(f"Could not get today's task count: {e}")
            tasks_today = "N/A"
        
        # Display metrics in two rows for better mobile responsiveness
        metrics_row1 = {
            "📊 Total Tasks": total_tasks,
            "✅ Completed": completed_tasks,
            "📅 Tasks Today": tasks_today
        }
        
        metrics_row2 = {
            "🔄 In Progress": in_progress_tasks,
            "⏳ Pending": pending_tasks
        }
        
        # Render metrics in two rows
        self.render_metrics_row(metrics_row1, columns=3)
        self.render_metrics_row(metrics_row2, columns=2)
    



def main():
    """Main entry point for the AI Task Explorer dashboard."""
    dashboard = AITaskDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
