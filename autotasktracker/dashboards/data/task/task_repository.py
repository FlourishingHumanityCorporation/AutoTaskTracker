"""Task repository for task-related data access."""

import logging
import re
import sqlite3
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
        try:
            with self.db.get_connection(readonly=True) as conn:
                self._configure_sqlite_connection(conn)
                cursor = conn.cursor()
                
                # Get task entities
                task_entities = self._fetch_task_entities(cursor, start_date, end_date, limit)
                if not task_entities:
                    logger.debug(f"No tasks found between {start_date} and {end_date}")
                    return []
                
                # Get metadata for entities
                entity_ids = [entity[0] for entity in task_entities]
                metadata_by_entity = self._fetch_metadata_for_entities(cursor, entity_ids)
                
                # Build task objects
                tasks = self._build_task_objects(task_entities, metadata_by_entity, categories)
                
                logger.info(f"Retrieved {len(tasks)} tasks from SQLite (filtered from {len(task_entities)} entities)")
                return tasks
                
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.error(f"Database error retrieving tasks from SQLite: {e}")
            logger.exception("Full traceback:")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving tasks from SQLite: {e}")
            logger.exception("Full traceback:")
            return []
    
    def _configure_sqlite_connection(self, conn) -> None:
        """Configure SQLite connection for optimal performance."""
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
    
    def _fetch_task_entities(self, cursor, start_date: datetime, end_date: datetime, limit: int) -> List[tuple]:
        """Fetch task entities from database."""
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
        return cursor.fetchall()
    
    def _fetch_metadata_for_entities(self, cursor, entity_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """Fetch metadata for entities in batches."""
        metadata_by_entity = {}
        batch_size = 100
        
        for i in range(0, len(entity_ids), batch_size):
            batch_ids = entity_ids[i:i + batch_size]
            placeholders = ','.join(['?' for _ in batch_ids])
            
            metadata_query = f"""
            SELECT entity_id, key, value 
            FROM metadata_entries 
            WHERE entity_id IN ({placeholders})
            AND key IN ('category', 'active_window', 'ocr_result', 'minicpm_v_result', 'vlm_result', 'subtasks')
            """
            
            cursor.execute(metadata_query, batch_ids)
            for entity_id, key, value in cursor.fetchall():
                if entity_id not in metadata_by_entity:
                    metadata_by_entity[entity_id] = {}
                metadata_by_entity[entity_id][key] = value
        
        return metadata_by_entity
    
    def _build_task_objects(
        self, 
        task_entities: List[tuple], 
        metadata_by_entity: Dict[int, Dict[str, str]], 
        categories: Optional[List[str]]
    ) -> List[Task]:
        """Build Task objects from entity data and metadata."""
        tasks = []
        
        for entity_id, created_at, filepath, task_text in task_entities:
            metadata = metadata_by_entity.get(entity_id, {})
            category = metadata.get('category', 'Other')
            
            # Apply category filter if specified
            if categories and category not in categories:
                continue
            
            # Extract and normalize window title
            window_title = self._extract_window_title_from_metadata(metadata)
            
            # Create task object with enhanced metadata
            task = Task(
                id=entity_id,
                title=task_text,
                category=category,
                timestamp=pd.to_datetime(created_at),
                duration_minutes=5,
                window_title=window_title,
                ocr_text=metadata.get('ocr_result', ''),
                screenshot_path=filepath,
                metadata={
                    'vlm_result': metadata.get('minicpm_v_result'),
                    'minicpm_v_result': metadata.get('minicpm_v_result'),
                    'subtasks': metadata.get('subtasks'),
                    'tasks': task_text,
                    'active_window': metadata.get('active_window'),
                    'timestamp': created_at,
                    'category': category
                }
            )
            tasks.append(task)
        
        return tasks
    
    def _extract_window_title_from_metadata(self, metadata: Dict[str, str]) -> str:
        """Extract and normalize window title from metadata."""
        window_title = metadata.get('active_window', 'Unknown')
        if window_title and window_title != 'Unknown':
            window_title = extract_window_title(window_title) or window_title
        return window_title
    
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
        tasks = self.get_tasks_for_period(start_date, end_date)
        if not tasks:
            return []
            
        # Sort by timestamp
        tasks.sort(key=lambda x: x.timestamp)
        
        return self._group_tasks_by_activity(tasks, min_duration_minutes, gap_threshold_minutes)
    
    def _group_tasks_by_activity(
        self, 
        tasks: List[Task], 
        min_duration_minutes: float, 
        gap_threshold_minutes: float
    ) -> List[TaskGroup]:
        """Group tasks by continuous activity periods."""
        groups = []
        current_group = None
        
        for task in tasks:
            normalized_window = self._normalize_window_title(task.window_title)
            
            if self._should_start_new_group(current_group, normalized_window, task, gap_threshold_minutes):
                # Save current group if it meets criteria
                if current_group and self._group_meets_criteria(current_group, min_duration_minutes):
                    groups.append(self._create_task_group(current_group))
                
                # Start new group
                current_group = self._create_new_group(task, normalized_window)
            else:
                # Continue current group
                current_group['end_time'] = task.timestamp
                current_group["tasks"].append(task)
        
        # Don't forget last group
        if current_group and self._group_meets_criteria(current_group, min_duration_minutes):
            groups.append(self._create_task_group(current_group))
                
        return groups
    
    def _should_start_new_group(
        self, 
        current_group: Optional[Dict], 
        normalized_window: str, 
        task: Task, 
        gap_threshold_minutes: float
    ) -> bool:
        """Determine if a new group should be started."""
        if current_group is None:
            return True
        
        # Check if window changed or gap too large
        window_changed = normalized_window != current_group["normalized_window"]
        gap_too_large = (task.timestamp - current_group['end_time']).total_seconds() / 60 > gap_threshold_minutes
        
        return window_changed or gap_too_large
    
    def _group_meets_criteria(self, group: Dict, min_duration_minutes: float) -> bool:
        """Check if group meets inclusion criteria."""
        duration = (group['end_time'] - group['start_time']).total_seconds() / 60
        return duration >= min_duration_minutes or len(group["tasks"]) >= 3
    
    def _create_new_group(self, task: Task, normalized_window: str) -> Dict:
        """Create a new task group."""
        return {
            "active_window": task.window_title,
            "normalized_window": normalized_window,
            "category": task.category,
            'start_time': task.timestamp,
            'end_time': task.timestamp,
            "tasks": [task]
        }
    
    def _create_task_group(self, group: Dict) -> TaskGroup:
        """Create TaskGroup object from group data."""
        duration = (group['end_time'] - group['start_time']).total_seconds() / 60
        return TaskGroup(
            window_title=group["normalized_window"],
            category=group["category"],
            start_time=group['start_time'],
            end_time=group['end_time'],
            duration_minutes=max(duration, len(group["tasks"]) * 0.25),
            task_count=len(group["tasks"]),
            tasks=group["tasks"]
        )