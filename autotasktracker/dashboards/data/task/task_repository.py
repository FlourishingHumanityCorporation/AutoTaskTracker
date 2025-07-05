"""Task repository for task-related data access."""

import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from autotasktracker.core.categorizer import extract_window_title
from autotasktracker.dashboards.data.core.base_repository import BaseRepository
from autotasktracker.dashboards.data.models import Task, TaskGroup

logger = logging.getLogger(__name__)


class TaskRepository(BaseRepository):
    """Repository for task-related data access."""
    
    def get_tasks_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime,
        categories: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Task]:
        """Get tasks for a specific time period.
        
        Args:
            start_date: Start of period
            end_date: End of period  
            categories: Optional category filter
            limit: Maximum results
            
        Returns:
            List of Task objects
        """
        # Pensieve REST API temporarily disabled - using SQLite fallback
        # TODO: Fix REST API task conversion
        # if self.use_pensieve and self.api_client:
        #     try:
        #         screenshots = self.api_client.get_screenshots(
        #             limit=limit,
        #             start_date=start_date.isoformat(),
        #             end_date=end_date.isoformat()
        #         )
        #         # ... rest of API code
        
        # Use reliable SQLite fallback
        return self._get_tasks_sqlite_fallback(start_date, end_date, categories, limit)
        # PostgreSQL adapter temporarily disabled - metadata joins broken
        # if self.use_pensieve and self.pg_adapter:
        #     try:
        #         task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, categories, limit)
        #         return self._convert_task_dicts_to_objects(task_dicts)
        #     except Exception as e:
        #         logger.warning(f"PostgreSQL adapter failed, fallingback to SQLite: {e}")
        
        # Direct SQLite query (reliable)
        # return self._get_tasks_sqlite_fallback(start_date, end_date, categories, limit)
    
    def _get_tasks_sqlite_fallback(
        self, 
        start_date: datetime, 
        end_date: datetime,
        categories: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Task]:
        """Fallback SQLite implementation - uses direct cursor to avoid pandas JOIN issues."""
        tasks = []
        
        try:
            with self.db.get_connection(readonly=True) as conn:
                # Enable WAL mode compatibility settings
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA temp_store=MEMORY;")
                
                # Direct cursor approach to avoid pandas DataFrame issues
                cursor = conn.cursor()
                
                # First get all task entities with direct SQL
                task_query = """
                SELECT e.id, e.created_at, e.filepath, m.value as tasks
                FROM entities e
                INNER JOIN metadata_entries m ON e.id = m.entity_id
                WHERE m.key = 'tasks'
                AND e.created_at >= ? AND e.created_at <= ?
                ORDER BY e.created_at DESC
                LIMIT ?
                """
                
                params = [
                    start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    end_date.strftime('%Y-%m-%d %H:%M:%S'),
                    limit
                ]
                
                cursor.execute(task_query, params)
                task_entities = cursor.fetchall()
                
                if not task_entities:
                    logger.debug(f"No tasks found between {start_date} and {end_date}")
                    return tasks
                
                # Get all metadata for these entities in batches to avoid query size limits
                entity_ids = [entity[0] for entity in task_entities]
                metadata_by_entity = {}
                
                # Process in batches of 100 to avoid SQL parameter limits
                batch_size = 100
                for i in range(0, len(entity_ids), batch_size):
                    batch_ids = entity_ids[i:i + batch_size]
                    placeholders = ','.join(['?' for _ in batch_ids])
                    
                    metadata_query = f"""
                    SELECT entity_id, key, value 
                    FROM metadata_entries 
                    WHERE entity_id IN ({placeholders})
                    AND key IN ('category', 'active_window', 'ocr_result')
                    """
                    
                    cursor.execute(metadata_query, batch_ids)
                    for entity_id, key, value in cursor.fetchall():
                        if entity_id not in metadata_by_entity:
                            metadata_by_entity[entity_id] = {}
                        metadata_by_entity[entity_id][key] = value
                
                # Build task objects
                for entity_id, created_at, filepath, task_text in task_entities:
                    metadata = metadata_by_entity.get(entity_id, {})
                    category = metadata.get('category', 'Other')
                    
                    # Apply category filter if specified
                    if categories and category not in categories:
                        continue
                    
                    # Extract window title
                    window_title = metadata.get('active_window', 'Unknown')
                    if window_title and window_title != 'Unknown':
                        window_title = extract_window_title(window_title) or window_title
                    
                    # Create task object
                    task = Task(
                        id=entity_id,
                        title=task_text,
                        category=category,
                        timestamp=pd.to_datetime(created_at),
                        duration_minutes=5,
                        window_title=window_title,
                        ocr_text=metadata.get('ocr_result', ''),
                        screenshot_path=filepath
                    )
                    tasks.append(task)
                
                logger.info(f"Retrieved {len(tasks)} tasks from SQLite (filtered from {len(task_entities)} entities)")
                
        except Exception as e:
            logger.error(f"Error retrieving tasks from SQLite: {e}")
            logger.exception("Full traceback:")
            
        return tasks
    
    def _convert_task_dicts_to_objects(self, task_dicts: List[Dict[str, Any]]) -> List[Task]:
        """Convert PostgreSQL adapter results to Task objects."""
        # Timezone conversion disabled - using local time directly
        
        tasks = []
        for task_dict in task_dicts:
            # Extract task title from tasks array or use window title
            task_title = task_dict.get("active_window", 'Unknown')
            if task_dict.get("tasks"):
                # Use first task title if available
                first_task = task_dict["tasks"][0] if isinstance(task_dict["tasks"], list) else task_dict["tasks"]
                if isinstance(first_task, dict) and 'title' in first_task:
                    task_title = first_task['title']
                elif isinstance(first_task, str):
                    task_title = first_task
            
            # Extract window title
            window_title = extract_window_title(task_dict.get("active_window", '')) or task_dict.get("active_window", 'Unknown')
            
            # Handle timestamp conversion
            timestamp = task_dict.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            # Use timestamp directly - timezone conversion disabled
            local_timestamp = timestamp or datetime.now()
            
            task = Task(
                id=task_dict.get('id'),
                title=task_title,
                category=task_dict.get("category", 'Other'),
                timestamp=local_timestamp,
                duration_minutes=5,  # Default 5 min per capture
                window_title=window_title,
                ocr_text=task_dict.get("ocr_result"),
                screenshot_path=task_dict.get('filepath')
            )
            tasks.append(task)
            
        return tasks
        
    def _normalize_window_title(self, window_title: str) -> str:
        """Normalize window title for better task context extraction.
        
        Transforms generic app titles into meaningful work descriptions.
        Examples:
        - "AutoTaskTracker — ✳ Project Premortem — claude" → "Project Premortem (AI Consultation)"
        - "Gmail — Inbox (5) — paul@example.com" → "Email Management"
        - "VS Code — task_board.py — AutoTaskTracker" → "Code Development (task_board.py)"
        
        Args:
            window_title: Raw window title
            
        Returns:
            Meaningful task description for grouping
        """
        if not window_title:
            return "Unknown Activity"
            
        # Clean up session-specific noise first
        normalized = window_title
        normalized = re.sub(r'MallocNanoZone=\d+', '', normalized)
        normalized = re.sub(r'—\s*\d+×\d+$', '', normalized)
        normalized = re.sub(r'—\s*▸\s*\w+', '', normalized)  # Remove terminal shell indicators
        normalized = re.sub(r'\([a-f0-9]{7,}\)', '', normalized)  # Remove git hashes
        normalized = re.sub(r'—+', '—', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Extract meaningful task context
        task_name = self._extract_task_context(normalized)
        
        return task_name
    
    def _extract_task_context(self, title: str) -> str:
        """Extract meaningful task context from a normalized window title.
        
        Uses pattern matching to identify work activities and create
        human-readable task descriptions.
        """
        # Common application patterns and their work context
        app_patterns = {
            # Development
            r'VS Code.*?([^—]+\.(?:py|js|ts|jsx|tsx|html|css|sql|md))': r'Code Development (\1)',
            r'Terminal.*?([^—]+)': r'Terminal Work (\1)',
            r'Xcode.*?([^—]+)': r'iOS Development (\1)',
            
            # Communication
            r'Gmail|Mail.*?(?:Inbox|Compose)': 'Email Management',
            r'Slack.*?([^—]+)': r'Team Communication (\1)',
            r'Zoom.*?([^—]+)': r'Video Meeting (\1)',
            r'Teams.*?([^—]+)': r'Team Meeting (\1)',
            
            # Productivity
            r'Excel.*?([^—]+\.xlsx?)': r'Spreadsheet Analysis (\1)',
            r'Word.*?([^—]+\.docx?)': r'Document Writing (\1)',
            r'PowerPoint.*?([^—]+\.pptx?)': r'Presentation Creation (\1)',
            r'Notion.*?([^—]+)': r'Documentation (\1)',
            
            # Creative
            r'Figma.*?([^—]+)': r'UI Design (\1)',
            r'Sketch.*?([^—]+)': r'UI Design (\1)',
            
            # Database
            r'(?:MySQL|PostgreSQL|SQLite).*?([^—]+)': r'Database Management (\1)',
            r'TablePlus.*?([^—]+)': r'Database Analysis (\1)',
        }
        
        # Try to match specific patterns
        for pattern, replacement in app_patterns.items():
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                if '(' in replacement and '\\1' in replacement:
                    # Extract the captured group
                    context = match.group(1).strip()
                    # Clean up context
                    context = re.sub(r'[—\-]+.*$', '', context).strip()
                    if context:
                        return replacement.replace('\\1', context)
                else:
                    return replacement
        
        # Fallback: Extract app name and main context
        if ' — ' in title:
            parts = [p.strip() for p in title.split(' — ') if p.strip()]
            if len(parts) >= 2:
                app_name = parts[0]
                context = parts[1]
                
                # Skip generic markers
                if context in ['✳', '✳ ', '']:
                    context = parts[2] if len(parts) > 2 else app_name
                
                # Create meaningful task name
                if app_name.lower() in ['chrome', 'safari', 'firefox']:
                    return f"Web Research ({context})"
                elif app_name.lower() in ['terminal', 'iterm', 'iterm2']:
                    return f"Terminal Work ({context})"
                elif context != app_name:
                    return f"{context} ({app_name})"
                else:
                    return app_name
        
        # Final fallback: Return cleaned title
        return title.split(' — ')[0] if ' — ' in title else title
    
    def get_task_groups(
        self,
        start_date: datetime,
        end_date: datetime,
        min_duration_minutes: float = 0.5,  # Lowered threshold
        gap_threshold_minutes: float = 15   # Increased gap tolerance
    ) -> List[TaskGroup]:
        """Get grouped tasks based on continuous activity with smart grouping.
        
        Args:
            start_date: Start of period
            end_date: End of period
            min_duration_minutes: Minimum duration to include (lowered to 0.5)
            gap_threshold_minutes: Max gap between activities to group (increased to 15)
            
        Returns:
            List of TaskGroup objects
        """
        # This method uses get_tasks_for_period which now uses PostgreSQL adapter
        tasks = self.get_tasks_for_period(start_date, end_date)
        
        if not tasks:
            return []
            
        # Sort by timestamp
        tasks.sort(key=lambda x: x.timestamp)
        
        groups = []
        current_group = None
        
        for task in tasks:
            normalized_window = self._normalize_window_title(task.window_title)
            
            if current_group is None:
                # Start new group
                current_group = {
                    "active_window": task.window_title,
                    "normalized_window": normalized_window,
                    "category": task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    "tasks": [task]
                }
            elif (normalized_window == current_group["normalized_window"] and
                  (task.timestamp - current_group['end_time']).total_seconds() / 60 <= gap_threshold_minutes):
                # Continue current group (using normalized window for comparison)
                current_group['end_time'] = task.timestamp
                current_group["tasks"].append(task)
            else:
                # Save current group and start new one
                duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
                if duration >= min_duration_minutes or len(current_group["tasks"]) >= 3:  # Include if has many activities
                    groups.append(TaskGroup(
                        window_title=current_group["normalized_window"],  # Use normalized title
                        category=current_group["category"],
                        start_time=current_group['start_time'],
                        end_time=current_group['end_time'],
                        duration_minutes=max(duration, len(current_group["tasks"]) * 0.25),  # Minimum duration based on activity count
                        task_count=len(current_group["tasks"]),
                        tasks=current_group["tasks"]
                    ))
                    
                # Start new group
                current_group = {
                    "active_window": task.window_title,
                    "normalized_window": normalized_window,
                    "category": task.category,
                    'start_time': task.timestamp,
                    'end_time': task.timestamp,
                    "tasks": [task]
                }
                
        # Don't forget last group
        if current_group:
            duration = (current_group['end_time'] - current_group['start_time']).total_seconds() / 60
            if duration >= min_duration_minutes or len(current_group["tasks"]) >= 3:
                groups.append(TaskGroup(
                    window_title=current_group["normalized_window"],
                    category=current_group["category"],
                    start_time=current_group['start_time'],
                    end_time=current_group['end_time'],
                    duration_minutes=max(duration, len(current_group["tasks"]) * 0.25),
                    task_count=len(current_group["tasks"]),
                    tasks=current_group["tasks"]
                ))
                
        return groups