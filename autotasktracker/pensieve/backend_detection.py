"""
Backend detection and metrics collection for Pensieve optimization.

Handles detecting the current backend type and collecting performance metrics.
"""

import logging
import time
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Supported backend types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    PGVECTOR = "pgvector"


@dataclass
class BackendMetrics:
    """Metrics for backend performance evaluation."""
    entity_count: int
    data_size_mb: float
    avg_query_time_ms: float
    concurrent_users: int
    search_frequency: float
    vector_operations: bool
    geographic_distribution: bool


class BackendDetector:
    """Detects current backend and collects performance metrics."""
    
    def __init__(self):
        """Initialize backend detector."""
        self.pensieve_client = None
        self._last_metrics = None
        self._metrics_cache_time = 0
        
    def detect_current_backend(self) -> BackendType:
        """Detect the currently configured backend type."""
        try:
            # First try to detect via Pensieve API
            if not self.pensieve_client:
                self.pensieve_client = get_pensieve_client()
            
            health = self.pensieve_client.get_health()
            if health and 'database_type' in health:
                db_type = health['database_type'].lower()
                if 'postgres' in db_type or 'postgresql' in db_type:
                    # Check if pgvector is enabled
                    if health.get('vector_enabled', False):
                        return BackendType.PGVECTOR
                    return BackendType.POSTGRESQL
                return BackendType.SQLITE
                
        except Exception as e:
            logger.debug(f"API detection failed: {e}")
        
        # Fallback: check configuration
        try:
            from autotasktracker.pensieve.config_sync import get_synced_config
            config = get_synced_config()
            if config and hasattr(config, 'backend_type'):
                return BackendType(config.backend_type)
        except Exception as e:
            logger.debug(f"Config detection failed: {e}")
        
        # Default fallback
        logger.info("Could not detect backend type, assuming SQLite")
        return BackendType.SQLITE
    
    def collect_metrics(self) -> BackendMetrics:
        """Collect comprehensive backend performance metrics."""
        # Cache metrics for 5 minutes to avoid repeated expensive operations
        if (self._last_metrics and 
            time.time() - self._metrics_cache_time < 300):
            return self._last_metrics
            
        try:
            entity_count = self._get_entity_count()
            data_size = self._get_data_size()
            query_time = self._measure_query_performance()
            
            metrics = BackendMetrics(
                entity_count=entity_count,
                data_size_mb=data_size,
                avg_query_time_ms=query_time,
                concurrent_users=1,  # Single user for now
                search_frequency=self._estimate_search_frequency(),
                vector_operations=self._has_vector_operations(),
                geographic_distribution=False  # Local deployment
            )
            
            self._last_metrics = metrics
            self._metrics_cache_time = time.time()
            
            logger.info(f"Collected metrics: {entity_count} entities, "
                       f"{data_size:.1f}MB data, {query_time:.1f}ms avg query")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            # Return minimal metrics to allow system to continue
            return BackendMetrics(
                entity_count=0,
                data_size_mb=0.0,
                avg_query_time_ms=100.0,
                concurrent_users=1,
                search_frequency=0.0,
                vector_operations=False,
                geographic_distribution=False
            )
    
    def _get_entity_count(self) -> int:
        """Get total number of entities."""
        try:
            if self.pensieve_client:
                health = self.pensieve_client.get_health()
                if health and 'entity_count' in health:
                    return health['entity_count']
        except Exception as e:
            logger.debug(f"API entity count failed: {e}")
        
        # Fallback to direct database query
        try:
            from autotasktracker.core.database import DatabaseManager
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entities")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.warning(f"Failed to get entity count: {e}")
            return 0
    
    def _get_data_size(self) -> float:
        """Estimate total data size in MB."""
        try:
            # Simple estimation based on entity count and average size
            entity_count = self._get_entity_count()
            # Average ~100KB per entity (screenshot + metadata)
            return (entity_count * 0.1)  # MB
        except Exception as e:
            logger.warning(f"Failed to estimate data size: {e}")
            return 0.0
    
    def _measure_query_performance(self) -> float:
        """Measure average query performance in milliseconds."""
        try:
            from autotasktracker.core.database import DatabaseManager
            db = DatabaseManager()
            
            # Run a representative query and measure time
            start_time = time.time()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT e.id, e.filename, me.value 
                    FROM entities e 
                    LEFT JOIN metadata_entries me ON e.id = me.entity_id 
                    WHERE me.key = 'ocr_result' 
                    LIMIT 10
                """)
                cursor.fetchall()
            
            query_time = (time.time() - start_time) * 1000  # Convert to ms
            return max(query_time, 1.0)  # Minimum 1ms
            
        except Exception as e:
            logger.warning(f"Failed to measure query performance: {e}")
            return 100.0  # Default estimate
    
    def _has_vector_operations(self) -> bool:
        """Check if vector operations are being used."""
        try:
            # Check if embeddings search is enabled
            from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine
            engine = EmbeddingsSearchEngine()
            return engine.embeddings_available
        except Exception as e:
            logger.debug(f"Vector operations check failed: {e}")
            return False
    
    def _estimate_search_frequency(self) -> float:
        """Estimate search frequency (searches per hour)."""
        # For now, return a conservative estimate
        # This could be enhanced with actual usage tracking
        entity_count = self._get_entity_count()
        
        if entity_count > 10000:
            return 50.0  # Heavy usage
        elif entity_count > 1000:
            return 10.0  # Moderate usage
        else:
            return 2.0   # Light usage


def get_backend_detector() -> BackendDetector:
    """Get singleton backend detector instance."""
    if not hasattr(get_backend_detector, '_instance'):
        get_backend_detector._instance = BackendDetector()
    return get_backend_detector._instance