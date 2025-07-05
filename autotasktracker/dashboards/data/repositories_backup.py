"""Data repositories for dashboard data access."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from collections import defaultdict
import re

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.categorizer import extract_window_title
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter, PostgreSQLAdapter
from autotasktracker.pensieve.cache_manager import get_cache_manager
from autotasktracker.pensieve.api_client import PensieveAPIClient
from autotasktracker.dashboards.data.models import Task, Activity, TaskGroup, DailyMetrics

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, use_pensieve: bool = True):
        self.db = db_manager or DatabaseManager()
        self.use_pensieve = use_pensieve
        self.pg_adapter = get_postgresql_adapter() if use_pensieve else None
        self.cache = get_cache_manager()  # Integrate cache manager
        
        # Initialize Pensieve API client for REST operations
        try:
            self.api_client = PensieveAPIClient() if use_pensieve else None
        except Exception as e:
            logger.debug(f"PensieveAPIClient initialization failed: {e}")
            self.api_client = None
        
        # Performance monitoring
        self.performance_stats = {
            'api_requests': 0,
            'api_failures': 0,
            'database_queries': 0,
            'database_failures': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_response_time': 0.0,
            'api_response_time': 0.0,
            'db_response_time': 0.0
        }
        
        # Circuit breaker for failed API endpoints
        self.endpoint_circuit_breaker = {
            'failed_endpoints': set(),
            'failure_counts': defaultdict(int),
            'last_failure_time': {},
            'circuit_open_duration': 300,  # 5 minutes
            'failure_threshold': 3
        }
        
    def _execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pd.DataFrame:
        """Execute query with API-first approach, intelligent caching and error handling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        import hashlib
        import time
        
        start_time = time.time()
        
        # Create cache key from query and params
        cache_key = f"query_{hashlib.md5(f'{query}_{params}'.encode(), usedforsecurity=False).hexdigest()}"
        
        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            self.performance_stats['cache_hits'] += 1
            logger.debug(f"Cache hit for query: {query[:50]}...")
            # Convert back to DataFrame if it was serialized
            if isinstance(cached_result, dict) and 'data' in cached_result:
                return pd.DataFrame(cached_result['data'])
            return cached_result
        
        self.performance_stats['cache_misses'] += 1
        
        # Try Pensieve API first for data queries
        if self.api_client and self._is_data_query(query):
            api_start = time.time()
            try:
                self.performance_stats['api_requests'] += 1
                api_result = self._execute_api_query(query, params)
                if api_result is not None:
                    api_time = time.time() - api_start
                    self.performance_stats['api_response_time'] += api_time
                    
                    # Cache the API result
                    cache_data = {
                        'data': api_result.to_dict('records'),
                        'columns': list(api_result.columns),
                        'shape': api_result.shape
                    }
                    self.cache.set(cache_key, cache_data, ttl=cache_ttl)
                    logger.debug(f"API query successful: {api_result.shape} rows ({api_time:.3f}s)")
                    
                    total_time = time.time() - start_time
                    self.performance_stats['total_response_time'] += total_time
                    return api_result
            except Exception as e:
                self.performance_stats['api_failures'] += 1
                logger.debug(f"API query failed, falling back to database: {e}")
        
        # Fallback to database
        db_start = time.time()
        try:
            self.performance_stats['database_queries'] += 1
            # Fallback to DatabaseManager's connection context manager
            with self.db.get_connection() as conn:
                # Check if query has complex JOINs that pandas struggles with
                query_lower = query.lower()
                has_complex_join = 'join' in query_lower and 'metadata_entries' in query_lower
                
                if has_complex_join:
                    # Use direct cursor for complex JOINs to avoid pandas issues
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    
                    # Fetch column names
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    # Fetch all rows
                    rows = cursor.fetchall()
                    
                    # Convert to DataFrame
                    result = pd.DataFrame(rows, columns=columns)
                    logger.debug(f"Used direct cursor for complex JOIN query")
                else:
                    # Use pandas for simple queries
                    result = pd.read_sql_query(query, conn, params=params)
                
                db_time = time.time() - db_start
                self.performance_stats['db_response_time'] += db_time
                
                # Cache the result (serialize DataFrame for caching)
                cache_data = {
                    'data': result.to_dict('records'),
                    'columns': list(result.columns),
                    'shape': result.shape
                }
                self.cache.set(cache_key, cache_data, ttl=cache_ttl)
                logger.debug(f"Database query successful: {result.shape} rows ({db_time:.3f}s)")
                
                total_time = time.time() - start_time
                self.performance_stats['total_response_time'] += total_time
                return result
        except Exception as e:
            self.performance_stats['database_failures'] += 1
            logger.error(f"Query execution failed: {e}")
            return pd.DataFrame()
    
    def _is_data_query(self, query: str) -> bool:
        """Check if query is suitable for API execution."""
        # Simple heuristic: SELECT queries that don't use complex SQL features
        query_lower = query.lower().strip()
        return (query_lower.startswith('select') and 
                'join' not in query_lower and  # Skip complex joins for now
                'group by' not in query_lower and  # Skip aggregations
                'order by' in query_lower)  # Prefer ordered results
    
    def _execute_api_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute query via Pensieve API with intelligent endpoint routing and circuit breaker."""
        if not self.api_client.is_healthy():
            return None
        
        # Check circuit breaker for API access
        if self._is_circuit_breaker_open():
            logger.debug("API circuit breaker is open, skipping API query")
            return None
            
        try:
            # Smart endpoint routing based on query type and available endpoints
            result = self._route_query_to_available_endpoints(query, params)
            
            # Reset circuit breaker on success
            if result is not None:
                self._reset_circuit_breaker()
            
            return result
        except Exception as e:
            logger.debug(f"API query routing failed: {e}")
            self._record_api_failure(str(e))
            return None
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if the circuit breaker is open (blocking API calls)."""
        import time
        current_time = time.time()
        
        # Check if circuit should be closed (enough time has passed)
        for endpoint, failure_time in list(self.endpoint_circuit_breaker['last_failure_time'].items()):
            if current_time - failure_time > self.endpoint_circuit_breaker['circuit_open_duration']:
                # Reset the endpoint
                self.endpoint_circuit_breaker['failed_endpoints'].discard(endpoint)
                self.endpoint_circuit_breaker['failure_counts'][endpoint] = 0
                del self.endpoint_circuit_breaker['last_failure_time'][endpoint]
        
        # Circuit is open if we have recent failures
        return len(self.endpoint_circuit_breaker['failed_endpoints']) > 0
    
    def _record_api_failure(self, error_message: str):
        """Record an API failure for circuit breaker logic."""
        import time
        current_time = time.time()
        
        # Increment failure count
        self.endpoint_circuit_breaker['failure_counts']['general'] += 1
        
        # If we hit the threshold, open the circuit
        if (self.endpoint_circuit_breaker['failure_counts']['general'] >= 
            self.endpoint_circuit_breaker['failure_threshold']):
            
            self.endpoint_circuit_breaker['failed_endpoints'].add('general')
            self.endpoint_circuit_breaker['last_failure_time']['general'] = current_time
            
            logger.warning(f"API circuit breaker opened due to repeated failures: {error_message}")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful API call."""
        self.endpoint_circuit_breaker['failure_counts']['general'] = 0
        self.endpoint_circuit_breaker['failed_endpoints'].discard('general')
        if 'general' in self.endpoint_circuit_breaker['last_failure_time']:
            del self.endpoint_circuit_breaker['last_failure_time']['general']
    
    def _route_query_to_available_endpoints(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Route queries to available Pensieve API endpoints based on current availability."""
        query_lower = query.lower()
        
        # Available endpoints based on our testing:
        # ✅ /api/search - Text search
        # ✅ /api/entities/{id} - Get specific entity  
        # ✅ /api/libraries/1/folders/1/entities - Entities in folder
        # ✅ /api/config - Configuration
        
        try:
            # Route search-related queries to /api/search
            if any(keyword in query_lower for keyword in ['search', 'like', 'match']):
                return self._execute_search_query(query, params)
            
            # Route entity listing queries to /api/libraries/1/folders/1/entities
            elif any(keyword in query_lower for keyword in ['entities', 'screenshots']) and 'limit' in query_lower:
                return self._execute_entity_listing_query(query, params)
                
            # For other queries, check if we can use specific entity endpoints
            elif 'entity_id' in query_lower or any(p for p in params if isinstance(p, int) and p > 0):
                return self._execute_entity_specific_query(query, params)
            
            # Cannot route this query to available endpoints
            return None
            
        except Exception as e:
            logger.debug(f"Query routing failed: {e}")
            return None
    
    def _execute_search_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute search queries using /api/search endpoint."""
        try:
            # Extract search terms from SQL query parameters
            search_term = None
            limit = 100
            
            # Basic parameter extraction (could be enhanced)
            if params:
                for param in params:
                    if isinstance(param, str) and len(param) > 2:
                        search_term = param.strip('%')  # Remove SQL wildcards
                        break
                    elif isinstance(param, int) and param > 0 and param < 1000:
                        limit = param
            
            if not search_term:
                search_term = "screenshot"  # Default search term
            
            # Use the API client's search functionality
            entities = self.api_client.search_entities(search_term, limit=limit)
            
            if not entities:
                return pd.DataFrame()
            
            # Convert to DataFrame format matching database schema
            data = []
            for entity in entities:
                data.append({
                    'id': entity.id,
                    'filepath': entity.filepath,
                    'filename': entity.filename,
                    'created_at': entity.created_at,
                    'file_created_at': entity.file_created_at,
                    'last_scan_at': entity.last_scan_at,
                    'file_type_group': entity.file_type_group
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.debug(f"Search query execution failed: {e}")
            return None
    
    def _execute_entity_listing_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute entity listing queries using /api/libraries/1/folders/1/entities."""
        try:
            # Use the working entities endpoint through API client
            entities = self.api_client.get_entities(limit=100)
            
            if not entities:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for entity in entities:
                data.append({
                    'id': entity.id,
                    'filepath': entity.filepath,
                    'filename': entity.filename,
                    'created_at': entity.created_at,
                    'file_created_at': entity.file_created_at,
                    'last_scan_at': entity.last_scan_at,
                    'file_type_group': entity.file_type_group
                })
            
            df = pd.DataFrame(data)
            
            # Apply basic filtering based on query parameters
            if params:
                limit = next((p for p in params if isinstance(p, int) and p > 0), None)
                if limit:
                    df = df.head(limit)
            
            return df
            
        except Exception as e:
            logger.debug(f"Entity listing query execution failed: {e}")
            return None
    
    def _execute_entity_specific_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute entity-specific queries using /api/entities/{id}."""
        try:
            # Extract entity ID from parameters
            entity_id = None
            for param in params:
                if isinstance(param, int) and param > 0:
                    entity_id = param
                    break
            
            if not entity_id:
                return None
            
            # Get specific entity
            entity = self.api_client.get_entity(entity_id)
            if not entity:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = [{
                'id': entity.id,
                'filepath': entity.filepath,
                'filename': entity.filename,
                'created_at': entity.created_at,
                'file_created_at': entity.file_created_at,
                'last_scan_at': entity.last_scan_at,
                'file_type_group': entity.file_type_group
            }]
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.debug(f"Entity-specific query execution failed: {e}")
            return None
    
    def invalidate_cache(self, pattern: str = None):
        """Invalidate cached query results.
        
        Args:
            pattern: Pattern to match for selective invalidation (default: all queries)
        """
        if pattern:
            count = self.cache.invalidate_pattern(pattern)
            logger.info(f"Invalidated {count} cached queries matching pattern: {pattern}")
        else:
            count = self.cache.invalidate_pattern("query_")
            logger.info(f"Invalidated {count} cached queries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache.get_stats()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for API vs database usage."""
        stats = self.performance_stats.copy()
        
        # Calculate derived metrics
        total_requests = stats['api_requests'] + stats['database_queries']
        if total_requests > 0:
            stats['api_usage_percentage'] = (stats['api_requests'] / total_requests) * 100
            stats['database_usage_percentage'] = (stats['database_queries'] / total_requests) * 100
        else:
            stats['api_usage_percentage'] = 0
            stats['database_usage_percentage'] = 0
        
        # Calculate average response times
        if stats['api_requests'] > 0:
            stats['avg_api_response_time'] = stats['api_response_time'] / stats['api_requests']
        else:
            stats['avg_api_response_time'] = 0
            
        if stats['database_queries'] > 0:
            stats['avg_db_response_time'] = stats['db_response_time'] / stats['database_queries']
        else:
            stats['avg_db_response_time'] = 0
        
        # Calculate success rates
        if stats['api_requests'] > 0:
            stats['api_success_rate'] = ((stats['api_requests'] - stats['api_failures']) / stats['api_requests']) * 100
        else:
            stats['api_success_rate'] = 100
            
        if stats['database_queries'] > 0:
            stats['db_success_rate'] = ((stats['database_queries'] - stats['database_failures']) / stats['database_queries']) * 100
        else:
            stats['db_success_rate'] = 100
        
        # Cache efficiency
        total_cache_operations = stats['cache_hits'] + stats['cache_misses']
        if total_cache_operations > 0:
            stats['cache_hit_rate'] = (stats['cache_hits'] / total_cache_operations) * 100
        else:
            stats['cache_hit_rate'] = 0
        
        # Circuit breaker status
        stats['circuit_breaker_open'] = self._is_circuit_breaker_open()
        stats['failed_endpoints_count'] = len(self.endpoint_circuit_breaker['failed_endpoints'])
        stats['api_failure_threshold'] = self.endpoint_circuit_breaker['failure_threshold']
        
        return stats

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
            
            # Web browsing with context
            r'Chrome.*?Stack Overflow': 'Research & Problem Solving',
            r'Chrome.*?GitHub': 'Code Repository Management',
            r'Chrome.*?Confluence|Jira': 'Project Management',
            r'Safari.*?LinkedIn': 'Professional Networking',
            
            # AI Tools
            r'AutoTaskTracker.*?✳\s*([^—]+)': r'\1 (AI Consultation)',
            r'ChatGPT|Claude': 'AI Research & Development',
            
            # Design
            r'Figma.*?([^—]+)': r'Design Work (\1)',
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
                
        return groups
        

class ActivityRepository(BaseRepository):
    """Repository for activity/screenshot data."""
    
    def get_recent_activities(
        self,
        limit: int = 50,
        categories: Optional[List[str]] = None
    ) -> List[Activity]:
        """Get recent activities.
        
        Args:
            limit: Maximum number of activities
            categories: Optional category filter
            
        Returns:
            List of Activity objects
        """
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                # Get recent activities using PostgreSQL adapter
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)  # Get last week of activities
                
                task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, categories, limit)
                return self._convert_task_dicts_to_activities(task_dicts)
            except Exception as e:
                logger.warning(f"PostgreSQL adapter failed for activities, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        return self._get_activities_sqlite_fallback(limit, categories)
    
    def _get_activities_sqlite_fallback(
        self,
        limit: int = 50,
        categories: Optional[List[str]] = None
    ) -> List[Activity]:
        """Fallback SQLite implementation for activities."""
        query = """
        SELECT 
            e.id,
            e.created_at,
            e.filepath,
            m1.value as ocr_text,
            m2.value as active_window,
            m3.value as tasks,
            m4.value as category
        FROM entities e
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = "ocr_result"
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "active_window"  
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = "tasks"
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = "category"
        WHERE 1=1
        """
        
        params = []
        
        if categories:
            placeholders = ','.join(['?' for _ in categories])
            query += f" AND m4.value IN ({placeholders})"
            params.extend(categories)
            
        query += " ORDER BY e.created_at DESC LIMIT ?"
        params.append(limit)
        
        df = self._execute_query(query, tuple(params))
        
        activities = []
        for _, row in df.iterrows():
            activity = Activity(
                id=row['id'],
                timestamp=pd.to_datetime(row['created_at']),
                window_title=extract_window_title(row.get("active_window", '')) or row.get("active_window", 'Unknown'),
                category=row.get("category", 'Other'),
                ocr_text=row.get("ocr_result"),
                tasks=None,  # TODO: Parse tasks safely from JSON/string
                screenshot_path=row.get('filepath'),
                active_window=row.get("active_window")
            )
            activities.append(activity)
            
        return activities
    
    def _convert_task_dicts_to_activities(self, task_dicts: List[Dict[str, Any]]) -> List[Activity]:
        """Convert PostgreSQL adapter results to Activity objects."""
        # Timezone conversion disabled - using local time directly
        
        activities = []
        for task_dict in task_dicts:
            # Handle timestamp conversion
            timestamp = task_dict.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            # Use timestamp directly - timezone conversion disabled
            local_timestamp = timestamp or datetime.now()
            
            # Extract window title
            window_title = extract_window_title(task_dict.get("active_window", '')) or task_dict.get("active_window", 'Unknown')
            
            activity = Activity(
                id=task_dict.get('id'),
                timestamp=local_timestamp,
                window_title=window_title,
                category=task_dict.get("category", 'Other'),
                ocr_text=task_dict.get("ocr_result"),
                tasks=task_dict.get("tasks"),  # Keep tasks data if available
                screenshot_path=task_dict.get('filepath'),
                active_window=task_dict.get("active_window")
            )
            activities.append(activity)
            
        return activities
        

class MetricsRepository(BaseRepository):
    """Repository for metrics and analytics data."""
    
    def get_daily_metrics(
        self,
        date: datetime
    ) -> Optional[DailyMetrics]:
        """Get metrics for a specific day.
        
        Args:
            date: Date to get metrics for
            
        Returns:
            DailyMetrics object or None
        """
        if hasattr(date, 'date'):
            # If it's already a datetime, extract the date
            date = date.date()
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        # Try PostgreSQL adapter first if available
        if self.use_pensieve and self.pg_adapter:
            try:
                task_dicts = self.pg_adapter.get_tasks_optimized(start, end, None, 10000)  # Get all tasks for the day
                return self._calculate_daily_metrics_from_tasks(task_dicts, date)
            except Exception as e:
                logger.warning(f"PostgreSQL adapter failed for daily metrics, falling back to SQLite: {e}")
        
        # Fallback to direct SQLite query
        return self._get_daily_metrics_sqlite_fallback(date, start, end)
    
    def _get_daily_metrics_sqlite_fallback(
        self,
        date,
        start: datetime,
        end: datetime
    ) -> Optional[DailyMetrics]:
        """Fallback SQLite implementation for daily metrics."""
        # Get all data for the day
        query = """
        SELECT 
            e.created_at,
            m2.value as active_window,
            m4.value as category
        FROM entities e
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = "active_window"
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = "category"
        WHERE e.created_at >= ? AND e.created_at <= ?
        ORDER BY e.created_at
        """
        
        df = self._execute_query(query, (
            start.strftime('%Y-%m-%d %H:%M:%S'),
            end.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        if df.empty:
            return None
            
        # Calculate metrics
        total_tasks = len(df)
        unique_windows = df["active_window"].nunique()
        
        # Category breakdown
        categories = df["category"].value_counts().to_dict()
        
        # Calculate productive time (Development + Productivity categories)
        productive_categories = ['Development', 'Productivity']
        productive_tasks = df[df["category"].isin(productive_categories)]
        productive_time_minutes = len(productive_tasks) * 5  # 5 min per capture
        
        # Most used apps (by time spent)
        app_time = defaultdict(float)
        for _, row in df.iterrows():
            window = extract_window_title(row.get("active_window", '')) or row.get("active_window", 'Unknown')
            app_time[window] += 5  # 5 min per capture
            
        most_used = sorted(app_time.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Peak hours
        df['hour'] = pd.to_datetime(df['created_at']).dt.hour
        peak_hours = df['hour'].value_counts().head(3).index.tolist()
        
        return DailyMetrics(
            date=date,
            total_tasks=total_tasks,
            total_duration_minutes=total_tasks * 5,
            unique_windows=unique_windows,
            categories=categories,
            productive_time_minutes=productive_time_minutes,
            most_used_apps=most_used,
            peak_hours=peak_hours
        )
    
    def _calculate_daily_metrics_from_tasks(self, task_dicts: List[Dict[str, Any]], date) -> DailyMetrics:
        """Calculate daily metrics from PostgreSQL adapter task data."""
        if not task_dicts:
            return None
        
        # Calculate metrics
        total_tasks = len(task_dicts)
        
        # Extract categories and windows
        categories = defaultdict(int)
        unique_windows = set()
        app_time = defaultdict(float)
        hours = defaultdict(int)
        
        for task_dict in task_dicts:
            category = task_dict.get("category", 'Other')
            categories[category] += 1
            
            window_title = task_dict.get("active_window", 'Unknown')
            unique_windows.add(window_title)
            
            # Extract app name for time tracking
            window = extract_window_title(window_title) or window_title
            app_time[window] += 5  # 5 min per capture
            
            # Extract hour for peak analysis
            timestamp = task_dict.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                hours[timestamp.hour] += 1
        
        # Calculate productive time
        productive_categories = ['Development', 'Productivity']
        productive_tasks = sum(categories[cat] for cat in productive_categories if cat in categories)
        productive_time_minutes = productive_tasks * 5
        
        # Most used apps
        most_used = sorted(app_time.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Peak hours
        peak_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [hour for hour, _ in peak_hours]
        
        return DailyMetrics(
            date=date,
            total_tasks=total_tasks,
            total_duration_minutes=total_tasks * 5,
            unique_windows=len(unique_windows),
            categories=dict(categories),
            productive_time_minutes=productive_time_minutes,
            most_used_apps=most_used,
            peak_hours=peak_hours
        )
        
    def get_metrics_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get summary metrics for a period.
        
        Args:
            start_date: Start of period
            end_date: End of period
            
        Returns:
            Dictionary of metrics
        """
        # PostgreSQL adapter temporarily disabled due to metadata join issues
        # TODO: Fix PostgreSQL adapter to properly join with metadata_entries
        # if self.use_pensieve and self.pg_adapter:
        #     try:
        #         task_dicts = self.pg_adapter.get_tasks_optimized(start_date, end_date, None, 50000)
        #         return self._calculate_metrics_summary_from_tasks(task_dicts, start_date, end_date)
        #     except Exception as e:
        #         logger.warning(f"PostgreSQL adapter failed for metrics summary, falling back to SQLite: {e}")
        
        # Use direct SQLite query (reliable)
        return self._get_metrics_summary_sqlite_fallback(start_date, end_date)
    
    def _get_metrics_summary_sqlite_fallback(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Fallback SQLite implementation for metrics summary."""
        # Get basic activity metrics
        basic_query = """
        SELECT 
            COUNT(DISTINCT e.id) as total_activities,
            COUNT(DISTINCT DATE(e.created_at)) as active_days
        FROM entities e
        WHERE e.created_at >= ? AND e.created_at <= ?
        """
        
        df_basic = self._execute_query(basic_query, (
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        if df_basic.empty:
            return {
                'total_activities': 0,
                'active_days': 0,
                'unique_windows': 0,
                'unique_categories': 0,
                'avg_daily_activities': 0
            }
            
        # Get unique categories and windows separately using DATE comparison for broader match
        category_query = """
        SELECT COUNT(DISTINCT m.value) as unique_categories
        FROM metadata_entries m 
        JOIN entities e ON m.entity_id = e.id 
        WHERE m.key = "category" 
        AND DATE(e.created_at) >= DATE(?) 
        AND DATE(e.created_at) <= DATE(?)
        """
        
        window_query = """
        SELECT COUNT(DISTINCT m.value) as unique_windows
        FROM metadata_entries m 
        JOIN entities e ON m.entity_id = e.id 
        WHERE m.key = "active_window" 
        AND DATE(e.created_at) >= DATE(?) 
        AND DATE(e.created_at) <= DATE(?)
        """
        
        # Use longer cache TTL for aggregated metrics (10 minutes for historical, 2 minutes for today)
        metrics_cache_ttl = 120 if (datetime.now().date() == start_date.date()) else 600
        
        df_categories = self._execute_query(category_query, (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ), cache_ttl=metrics_cache_ttl)
        
        df_windows = self._execute_query(window_query, (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ), cache_ttl=metrics_cache_ttl)
        
        basic_row = df_basic.iloc[0]
        total_activities = basic_row['total_activities']
        active_days = basic_row['active_days'] or 1
        unique_categories = df_categories.iloc[0]['unique_categories'] if not df_categories.empty else 0
        unique_windows = df_windows.iloc[0]['unique_windows'] if not df_windows.empty else 0
        
        return {
            'total_activities': total_activities,
            'active_days': active_days,
            'unique_windows': unique_windows,
            'unique_categories': unique_categories,
            'avg_daily_activities': total_activities / active_days
        }
    
    def _calculate_metrics_summary_from_tasks(
        self,
        task_dicts: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate metrics summary from PostgreSQL adapter task data."""
        if not task_dicts:
            return {
                'total_activities': 0,
                'active_days': 0,
                'unique_windows': 0,
                'unique_categories': 0,
                'avg_daily_activities': 0
            }
        
        total_activities = len(task_dicts)
        unique_categories = set()
        unique_windows = set()
        active_dates = set()
        
        for task_dict in task_dicts:
            # Track unique categories
            category = task_dict.get("category")
            if category:
                unique_categories.add(category)
            
            # Track unique windows
            window_title = task_dict.get("active_window")
            if window_title:
                unique_windows.add(window_title)
            
            # Track active dates
            timestamp = task_dict.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                active_dates.add(timestamp.date())
        
        active_days = len(active_dates) or 1
        avg_daily_activities = total_activities / active_days
        
        return {
            'total_activities': total_activities,
            'active_days': active_days,
            'unique_windows': len(unique_windows),
            'unique_categories': len(unique_categories),
            'avg_daily_activities': avg_daily_activities
        }
