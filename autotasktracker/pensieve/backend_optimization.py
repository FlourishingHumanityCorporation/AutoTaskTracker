"""
Backend optimization logic for Pensieve.

Determines optimal backend configuration based on performance metrics.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from autotasktracker.pensieve.backend_detection import BackendType, BackendMetrics, BackendDetector

logger = logging.getLogger(__name__)


class BackendOptimizer:
    """Determines optimal backend configuration based on metrics."""
    
    def __init__(self):
        """Initialize backend optimizer."""
        self.detector = BackendDetector()
    
    def determine_optimal_backend(self, metrics: Optional[BackendMetrics] = None) -> BackendType:
        """Determine the optimal backend type based on current metrics."""
        if not metrics:
            metrics = self.detector.collect_metrics()
        
        # Decision logic based on usage patterns and scale
        
        # Large scale with vector operations -> pgvector
        if (metrics.entity_count > 100000 or 
            metrics.data_size_mb > 10000 or
            (metrics.vector_operations and metrics.entity_count > 10000)):
            return BackendType.PGVECTOR
        
        # Medium scale or high concurrency -> PostgreSQL
        if (metrics.entity_count > 10000 or
            metrics.avg_query_time_ms > 500 or
            metrics.concurrent_users > 5 or
            metrics.search_frequency > 20):
            return BackendType.POSTGRESQL
        
        # Small scale or local usage -> SQLite
        return BackendType.SQLITE
    
    def assess_migration_need(self) -> Tuple[bool, Optional['MigrationPlan']]:
        """Assess if migration is needed and return plan if so."""
        from autotasktracker.pensieve.migration_planning import MigrationPlanner
        
        current_backend = self.detector.detect_current_backend()
        optimal_backend = self.determine_optimal_backend()
        
        if current_backend == optimal_backend:
            logger.info(f"Current backend {current_backend.value} is optimal")
            return False, None
        
        logger.info(f"Migration recommended: {current_backend.value} → {optimal_backend.value}")
        
        # Create migration plan
        planner = MigrationPlanner()
        plan = planner.create_migration_plan(current_backend, optimal_backend)
        
        return True, plan
    
    def calculate_performance_score(self, metrics: BackendMetrics, backend: BackendType) -> float:
        """Calculate performance score for a backend with given metrics."""
        score = 100.0  # Start with perfect score
        
        # Penalize based on query performance
        if metrics.avg_query_time_ms > 100:
            score -= min(50, (metrics.avg_query_time_ms - 100) / 10)
        
        # Penalize SQLite for large datasets
        if backend == BackendType.SQLITE:
            if metrics.entity_count > 10000:
                score -= 30
            if metrics.data_size_mb > 1000:
                score -= 20
            if metrics.concurrent_users > 3:
                score -= 25
        
        # Penalize PostgreSQL for small datasets (overhead)
        elif backend == BackendType.POSTGRESQL:
            if metrics.entity_count < 1000:
                score -= 15
            if metrics.data_size_mb < 100:
                score -= 10
        
        # Penalize pgvector without vector operations
        elif backend == BackendType.PGVECTOR:
            if not metrics.vector_operations:
                score -= 40
            if metrics.entity_count < 5000:
                score -= 20
        
        return max(0.0, score)
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get optimization recommendations with detailed analysis."""
        try:
            current_backend = self.detector.detect_current_backend()
            metrics = self.detector.collect_metrics()
            optimal_backend = self.determine_optimal_backend(metrics)
            
            # Calculate scores for all backends
            scores = {}
            for backend in BackendType:
                scores[backend.value] = self.calculate_performance_score(metrics, backend)
            
            needs_migration, plan = self.assess_migration_need()
            
            recommendations = {
                'current_backend': current_backend.value,
                'optimal_backend': optimal_backend.value,
                'needs_migration': needs_migration,
                'performance_scores': scores,
                'metrics': {
                    'entity_count': metrics.entity_count,
                    'data_size_mb': metrics.data_size_mb,
                    'avg_query_time_ms': metrics.avg_query_time_ms,
                    'vector_operations': metrics.vector_operations
                },
                'recommendations': []
            }
            
            # Add specific recommendations
            if metrics.avg_query_time_ms > 200:
                recommendations['recommendations'].append(
                    "Consider adding database indexes for frequently queried fields"
                )
            
            if metrics.entity_count > 50000 and current_backend == BackendType.SQLITE:
                recommendations['recommendations'].append(
                    "SQLite may become bottleneck with this data size - consider PostgreSQL"
                )
            
            if metrics.vector_operations and current_backend != BackendType.PGVECTOR:
                recommendations['recommendations'].append(
                    "Vector operations detected - pgvector would improve performance"
                )
            
            if plan:
                recommendations['migration_plan'] = {
                    'estimated_duration_minutes': plan.estimated_duration_minutes,
                    'required_disk_space_gb': plan.required_disk_space_gb,
                    'complexity': 'low' if plan.estimated_duration_minutes < 30 else 'high'
                }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return {
                'error': str(e),
                'current_backend': 'unknown',
                'optimal_backend': 'sqlite',
                'needs_migration': False,
                'recommendations': ['Unable to analyze - check system health']
            }


def get_backend_optimizer() -> BackendOptimizer:
    """Get singleton backend optimizer instance."""
    if not hasattr(get_backend_optimizer, '_instance'):
        get_backend_optimizer._instance = BackendOptimizer()
    return get_backend_optimizer._instance