"""
Backend optimization coordinator for Pensieve.

Provides unified interface to all backend optimization functionality.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from autotasktracker.pensieve.backend_detection import BackendDetector, BackendType, BackendMetrics
from autotasktracker.pensieve.backend_optimization import BackendOptimizer
from autotasktracker.pensieve.migration_planning import MigrationPlanner, MigrationPlan
from autotasktracker.pensieve.migration_execution import MigrationExecutor

logger = logging.getLogger(__name__)


class PensieveBackendCoordinator:
    """
    Coordinates all backend optimization activities.
    
    This replaces the monolithic PensieveBackendOptimizer with a cleaner,
    more maintainable architecture using specialized components.
    """
    
    def __init__(self):
        """Initialize backend coordinator with all components."""
        self.detector = BackendDetector()
        self.optimizer = BackendOptimizer()
        self.planner = MigrationPlanner()
        self.executor = MigrationExecutor()
    
    # Main public interface methods
    def detect_current_backend(self) -> BackendType:
        """Detect the currently configured backend type."""
        return self.detector.detect_current_backend()
    
    def collect_metrics(self) -> BackendMetrics:
        """Collect comprehensive backend performance metrics."""
        return self.detector.collect_metrics()
    
    def determine_optimal_backend(self, metrics: Optional[BackendMetrics] = None) -> BackendType:
        """Determine the optimal backend type based on metrics."""
        return self.optimizer.determine_optimal_backend(metrics)
    
    def assess_migration_need(self) -> Tuple[bool, Optional[MigrationPlan]]:
        """Assess if migration is needed and return plan if so."""
        return self.optimizer.assess_migration_need()
    
    def execute_migration(self, plan: MigrationPlan, dry_run: bool = True) -> bool:
        """Execute migration plan with comprehensive error handling."""
        return self.executor.execute_migration(plan, dry_run)
    
    def get_migration_recommendations(self) -> Dict[str, Any]:
        """Get comprehensive migration recommendations."""
        return self.optimizer.get_optimization_recommendations()
    
    # Convenience methods that combine multiple operations
    def auto_optimize_backend(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Automatically assess and optimize backend configuration.
        
        This is the main entry point for automated optimization.
        """
        try:
            logger.info("Starting automated backend optimization")
            
            # Collect current state
            current_backend = self.detect_current_backend()
            metrics = self.collect_metrics()
            optimal_backend = self.determine_optimal_backend(metrics)
            
            result = {
                'current_backend': current_backend.value,
                'optimal_backend': optimal_backend.value,
                'metrics': {
                    'entity_count': metrics.entity_count,
                    'data_size_mb': metrics.data_size_mb,
                    'avg_query_time_ms': metrics.avg_query_time_ms,
                    'vector_operations': metrics.vector_operations
                },
                'optimization_needed': current_backend != optimal_backend,
                'dry_run': dry_run
            }
            
            if current_backend == optimal_backend:
                result['status'] = 'optimal'
                result['message'] = f"Current {current_backend.value} backend is already optimal"
                logger.info(result['message'])
                return result
            
            # Migration is needed
            logger.info(f"Migration recommended: {current_backend.value} → {optimal_backend.value}")
            
            # Create migration plan
            plan = self.planner.create_migration_plan(current_backend, optimal_backend)
            
            # Validate plan
            validation = self.planner.validate_migration_plan(plan)
            if not validation['valid']:
                result['status'] = 'blocked'
                result['message'] = 'Migration blocked by validation errors'
                result['errors'] = validation['errors']
                result['warnings'] = validation['warnings']
                return result
            
            # Execute migration
            success = self.execute_migration(plan, dry_run)
            
            if success:
                if dry_run:
                    result['status'] = 'plan_ready'
                    result['message'] = 'Migration plan validated and ready for execution'
                else:
                    result['status'] = 'migrated'
                    result['message'] = f'Successfully migrated to {optimal_backend.value}'
            else:
                result['status'] = 'failed'
                result['message'] = 'Migration failed (rollback completed)'
            
            result['migration_plan'] = {
                'source': plan.source_backend.value,
                'target': plan.target_backend.value,
                'duration_minutes': plan.estimated_duration_minutes,
                'disk_space_gb': plan.required_disk_space_gb,
                'risk_level': plan.risk_level
            }
            
            if validation.get('warnings'):
                result['warnings'] = validation['warnings']
            if validation.get('recommendations'):
                result['recommendations'] = validation['recommendations']
            
            return result
            
        except Exception as e:
            logger.error(f"Auto-optimization failed: {e}")
            return {
                'status': 'error',
                'message': f'Optimization failed: {str(e)}',
                'current_backend': 'unknown',
                'optimal_backend': 'unknown',
                'optimization_needed': False,
                'dry_run': dry_run
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status and recommendations."""
        try:
            current_backend = self.detect_current_backend()
            metrics = self.collect_metrics()
            optimal_backend = self.determine_optimal_backend(metrics)
            needs_migration, plan = self.assess_migration_need()
            
            status = {
                'backend': {
                    'current': current_backend.value,
                    'optimal': optimal_backend.value,
                    'is_optimal': current_backend == optimal_backend
                },
                'metrics': {
                    'entity_count': metrics.entity_count,
                    'data_size_mb': metrics.data_size_mb,
                    'avg_query_time_ms': metrics.avg_query_time_ms,
                    'vector_operations': metrics.vector_operations,
                    'search_frequency': metrics.search_frequency
                },
                'performance': {
                    'current_score': self.optimizer.calculate_performance_score(metrics, current_backend),
                    'optimal_score': self.optimizer.calculate_performance_score(metrics, optimal_backend)
                },
                'migration': {
                    'needed': needs_migration,
                    'plan_available': plan is not None
                }
            }
            
            if plan:
                status['migration']['details'] = {
                    'duration_minutes': plan.estimated_duration_minutes,
                    'disk_space_gb': plan.required_disk_space_gb,
                    'risk_level': plan.risk_level
                }
            
            # Add health indicators
            performance_score = status['performance']['current_score']
            if performance_score >= 80:
                status['health'] = 'excellent'
            elif performance_score >= 60:
                status['health'] = 'good'
            elif performance_score >= 40:
                status['health'] = 'fair'
            else:
                status['health'] = 'poor'
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'error': str(e),
                'backend': {'current': 'unknown', 'optimal': 'unknown', 'is_optimal': False},
                'health': 'unknown'
            }


# Singleton pattern for backward compatibility
_coordinator_instance = None

def get_backend_optimizer() -> PensieveBackendCoordinator:
    """Get singleton backend coordinator instance (replaces old optimizer)."""
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = PensieveBackendCoordinator()
    return _coordinator_instance

def auto_optimize_backend(dry_run: bool = True) -> Dict[str, Any]:
    """Auto-optimize backend (convenience function)."""
    coordinator = get_backend_optimizer()
    return coordinator.auto_optimize_backend(dry_run)

def reset_backend_optimizer():
    """Reset backend optimizer instance."""
    global _coordinator_instance
    _coordinator_instance = None