"""PostgreSQL adapter for AutoTaskTracker via Pensieve API."""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
import asyncio
from dataclasses import dataclass

from .api_client import get_pensieve_client, PensieveAPIError
from .config_reader import get_pensieve_config
from autotasktracker.core import DatabaseManager
from autotasktracker.core.exceptions import DatabaseError, PensieveIntegrationError, ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class PostgreSQLCapabilities:
    """PostgreSQL feature capabilities."""
    postgresql_enabled: bool
    vector_search_enabled: bool
    pgvector_available: bool
    vector_dimensions: int
    max_vectors: int
    performance_tier: str  # 'sqlite', 'postgresql', 'pgvector'


class PostgreSQLAdapter:
    """Adapter for Pensieve's PostgreSQL backend with pgvector support."""
    
    def __init__(self):
        self.pensieve_client = get_pensieve_client()
        self.config = get_pensieve_config()
        self.capabilities = self._detect_capabilities()
        self._fallback_db = None  # Lazy initialization
        
        logger.info(f"PostgreSQL adapter initialized - Performance tier: {self.capabilities.performance_tier}")
    
    @property
    def fallback_db(self):
        """Lazy initialization of fallback database."""
        if self._fallback_db is None:
            try:
                self._fallback_db = DatabaseManager(use_pensieve_api=False)
                logger.debug("Initialized fallback SQLite database")
            except DatabaseError as e:
                logger.warning(f"Database error initializing fallback: {e}")
                self._fallback_db = None
            except (OSError, IOError) as e:
                logger.warning(f"File system error initializing fallback database: {e}")
                self._fallback_db = None
            except Exception as e:
                logger.warning(f"Unexpected error initializing fallback database: {e}")
                self._fallback_db = None
        return self._fallback_db
    
    def _detect_capabilities(self) -> PostgreSQLCapabilities:
        """Detect PostgreSQL and pgvector capabilities."""
        try:
            # Check Pensieve health endpoint for database info
            if self.pensieve_client and self.pensieve_client.is_healthy():
                # Try to determine database type from API
                health_data = self._get_health_info()
                postgresql_enabled = health_data.get('postgresql_enabled', False)
                vector_search = health_data.get('vector_search_enabled', False)
                
                # Estimate capabilities based on config
                if postgresql_enabled and vector_search:
                    performance_tier = 'pgvector'
                    max_vectors = 10_000_000  # pgvector can handle millions
                elif postgresql_enabled:
                    performance_tier = 'postgresql'
                    max_vectors = 1_000_000   # PostgreSQL without vectors
                else:
                    performance_tier = 'sqlite'
                    max_vectors = 100_000     # SQLite practical limit
                
                return PostgreSQLCapabilities(
                    postgresql_enabled=postgresql_enabled,
                    vector_search_enabled=vector_search,
                    pgvector_available=postgresql_enabled and vector_search,
                    vector_dimensions=self.config.vector_search_enabled and 768 or 0,
                    max_vectors=max_vectors,
                    performance_tier=performance_tier
                )
            
        except PensieveAPIError as e:
            logger.debug(f"Pensieve API error detecting PostgreSQL capabilities: {e}")
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"Connection error detecting PostgreSQL capabilities: {e}")
        except (KeyError, ValueError) as e:
            logger.debug(f"Invalid response detecting PostgreSQL capabilities: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error detecting PostgreSQL capabilities: {e}")
        
        # Default to SQLite capabilities
        return PostgreSQLCapabilities(
            postgresql_enabled=False,
            vector_search_enabled=False,
            pgvector_available=False,
            vector_dimensions=0,
            max_vectors=100_000,
            performance_tier='sqlite'
        )
    
    def _get_health_info(self) -> Dict[str, Any]:
        """Get health information from Pensieve API."""
        try:
            # Try to get detailed health info (this would be Pensieve-specific)
            response = self.pensieve_client.session.get(f"{self.pensieve_client.base_url}/api/health/detailed")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Failed to get detailed health info: {e}")
        
        # Fallback to config-based detection
        return {
            'postgresql_enabled': self.config.postgresql_enabled,
            'vector_search_enabled': self.config.vector_search_enabled
        }
    
    def get_tasks_optimized(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get tasks using PostgreSQL optimizations when available."""
        
        if self.capabilities.performance_tier == 'pgvector':
            return self._get_tasks_pgvector(start_date, end_date, categories, limit)
        elif self.capabilities.performance_tier == 'postgresql':
            return self._get_tasks_postgresql(start_date, end_date, categories, limit)
        else:
            return self._get_tasks_sqlite(start_date, end_date, categories, limit)
    
    def _get_tasks_pgvector(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get tasks using pgvector-optimized queries."""
        try:
            # Make API call to get optimized results
            entities = self.pensieve_client.get_entities(limit=limit)
            
            # Enhance with metadata and task info, applying date and category filters
            tasks = []
            for entity in entities:
                # Apply date filter
                entity_date = self._parse_frame_date(entity.created_at)
                if not self._is_date_in_range(entity_date, start_date, end_date):
                    continue
                
                metadata = self.pensieve_client.get_entity_metadata(entity.id)
                
                if "tasks" in metadata:
                    task_data = {
                        'id': entity.id,
                        'timestamp': entity.created_at,
                        'filepath': entity.filepath,
                        "tasks": self._parse_tasks_safely(metadata.get("tasks")),
                        "category": metadata.get("category", 'Other'),
                        "active_window": metadata.get("active_window", ''),
                        "ocr_result": self.pensieve_client.get_entity_metadata(entity.id, 'ocr_result').get('ocr_result', '')
                    }
                    
                    # Apply category filter if specified
                    if not categories or task_data["category"] in categories:
                        tasks.append(task_data)
            
            logger.info(f"Retrieved {len(tasks)} tasks using pgvector optimization")
            return tasks
            
        except Exception as e:
            logger.warning(f"pgvector query failed, falling back to PostgreSQL: {e}")
            return self._get_tasks_postgresql(start_date, end_date, categories, limit)
    
    def _get_tasks_postgresql(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get tasks using PostgreSQL-optimized queries."""
        try:
            # Use Pensieve API with PostgreSQL backend
            entities = self.pensieve_client.get_entities(limit=limit)
            
            tasks = []
            # Batch metadata requests for better performance with date filtering
            for entity in entities:
                # Apply date filter
                entity_date = self._parse_frame_date(entity.created_at)
                if not self._is_date_in_range(entity_date, start_date, end_date):
                    continue
                
                metadata = self.pensieve_client.get_entity_metadata(entity.id)
                
                if "tasks" in metadata:
                    task_data = {
                        'id': entity.id,
                        'timestamp': entity.created_at,
                        'filepath': entity.filepath,
                        "tasks": self._parse_tasks_safely(metadata.get("tasks")),
                        "category": metadata.get("category", 'Other'),
                        "active_window": metadata.get("active_window", ''),
                        "ocr_result": self.pensieve_client.get_entity_metadata(entity.id, 'ocr_result').get('ocr_result', '')
                    }
                    
                    if not categories or task_data["category"] in categories:
                        tasks.append(task_data)
            
            logger.info(f"Retrieved {len(tasks)} tasks using PostgreSQL optimization")
            return tasks
            
        except Exception as e:
            logger.warning(f"PostgreSQL query failed, falling back to SQLite: {e}")
            return self._get_tasks_sqlite(start_date, end_date, categories, limit)
    
    def _get_tasks_sqlite(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get tasks using SQLite fallback."""
        try:
            # Check if fallback database is available
            if self.fallback_db is None:
                logger.warning("SQLite fallback database not available")
                return []
            
            # Use direct database access as fallback
            from ..dashboards.data.repositories import TaskRepository
            
            task_repo = TaskRepository(self.fallback_db, use_pensieve=False)  # Prevent infinite recursion
            tasks = task_repo.get_tasks_for_period(start_date, end_date, categories, limit)
            
            # Convert to dict format
            task_dicts = []
            for task in tasks:
                task_dicts.append({
                    'id': task.id,
                    'timestamp': task.timestamp,
                    'filepath': task.screenshot_path,
                    "tasks": [{'title': task.title, "category": task.category}],
                    "category": task.category,
                    "active_window": task.window_title,
                    "ocr_result": task.ocr_text
                })
            
            logger.info(f"Retrieved {len(task_dicts)} tasks using SQLite fallback")
            return task_dicts
            
        except Exception as e:
            logger.error(f"All database queries failed: {e}")
            return []
    
    def _parse_tasks_safely(self, tasks_data: Any) -> List[Dict[str, Any]]:
        """Safely parse task data from various formats."""
        if not tasks_data:
            return []
        
        try:
            if isinstance(tasks_data, str):
                # Try to parse JSON string
                tasks = json.loads(tasks_data)
            elif isinstance(tasks_data, list):
                tasks = tasks_data
            else:
                return []
            
            # Ensure each task has required fields
            normalized_tasks = []
            for task in tasks:
                if isinstance(task, dict):
                    normalized_tasks.append({
                        'title': task.get('title', 'Unknown Task'),
                        "category": task.get("category", 'Other'),
                        'confidence': task.get('confidence', 0.5)
                    })
                elif isinstance(task, str):
                    normalized_tasks.append({
                        'title': task,
                        "category": 'Other',
                        'confidence': 0.5
                    })
            
            return normalized_tasks
            
        except Exception as e:
            logger.debug(f"Failed to parse tasks data: {e}")
            return []
    
    def _parse_frame_date(self, date_str: str) -> datetime:
        """Parse frame date string to datetime object."""
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except Exception:
            # Fallback to basic parsing
            try:
                import pandas as pd
                return pd.to_datetime(date_str).to_pydatetime()
            except Exception:
                logger.warning(f"Failed to parse date: {date_str}")
                return datetime.now()
    
    def _is_date_in_range(self, frame_date: datetime, start_date: datetime, end_date: datetime) -> bool:
        """Check if frame date is within the specified range."""
        try:
            # Convert to date objects for comparison if needed
            if hasattr(frame_date, 'date'):
                frame_date = frame_date.date()
            if hasattr(start_date, 'date'):
                start_date = start_date.date()
            if hasattr(end_date, 'date'):
                end_date = end_date.date()
            
            return start_date <= frame_date <= end_date
        except Exception as e:
            logger.debug(f"Date comparison failed: {e}")
            return True  # Include frame if comparison fails
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the current backend."""
        try:
            # Benchmark query performance
            start_time = datetime.now()
            
            # Simple performance test
            test_date = datetime.now()
            self.get_tasks_optimized(
                start_date=datetime(test_date.year, test_date.month, test_date.day),
                end_date=test_date,
                limit=10
            )
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'backend_type': self.capabilities.performance_tier,
                'postgresql_enabled': self.capabilities.postgresql_enabled,
                'vector_search_enabled': self.capabilities.vector_search_enabled,
                'max_vectors_supported': self.capabilities.max_vectors,
                'vector_dimensions': self.capabilities.vector_dimensions,
                'sample_query_time_ms': round(query_time, 2),
                'estimated_scale': self._get_scale_estimate()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                'backend_type': 'unknown',
                'error': str(e)
            }
    
    def _get_scale_estimate(self) -> str:
        """Get human-readable scale estimate."""
        if self.capabilities.performance_tier == 'pgvector':
            return "Enterprise scale (millions of screenshots)"
        elif self.capabilities.performance_tier == 'postgresql':
            return "Medium scale (hundreds of thousands of screenshots)"
        else:
            return "Small scale (tens of thousands of screenshots)"
    
    def get_migration_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for database migration."""
        current_tier = self.capabilities.performance_tier
        
        recommendations = {
            'current_backend': current_tier,
            'recommendations': []
        }
        
        if current_tier == 'sqlite':
            recommendations['recommendations'].append({
                'priority': 'high',
                'action': 'Upgrade to PostgreSQL',
                'benefit': 'Better performance and concurrent access',
                'command': f'memos migrate --sqlite-url sqlite:///{self.config.get_db_path()} --pg-url postgresql://user:pass@localhost/pensieve'
            })
            
            recommendations['recommendations'].append({
                'priority': 'medium',
                'action': 'Enable pgvector for semantic search',
                'benefit': 'Advanced vector similarity search',
                'command': 'pip install pgvector && UPDATE config SET vector_search_enabled=true'
            })
        
        elif current_tier == 'postgresql':
            recommendations['recommendations'].append({
                'priority': 'medium',
                'action': 'Enable pgvector extension',
                'benefit': 'Native vector operations and semantic search',
                'command': 'CREATE EXTENSION IF NOT EXISTS vector; UPDATE config SET vector_search_enabled=true'
            })
        
        else:  # pgvector
            recommendations['recommendations'].append({
                'priority': 'low',
                'action': 'Configuration is optimal',
                'benefit': 'No action needed - using best available backend',
                'command': 'N/A'
            })
        
        return recommendations


# Singleton instance
_postgresql_adapter: Optional[PostgreSQLAdapter] = None


def get_postgresql_adapter() -> PostgreSQLAdapter:
    """Get singleton PostgreSQL adapter."""
    global _postgresql_adapter
    if _postgresql_adapter is None:
        _postgresql_adapter = PostgreSQLAdapter()
    return _postgresql_adapter


def reset_postgresql_adapter():
    """Reset adapter for testing."""
    global _postgresql_adapter
    _postgresql_adapter = None