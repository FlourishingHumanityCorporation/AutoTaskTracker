"""
Migration planning for Pensieve backend transitions.

Creates detailed plans for migrating between different backend types.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from autotasktracker.pensieve.backend_detection import BackendType, BackendDetector

logger = logging.getLogger(__name__)


@dataclass
class MigrationPlan:
    """Migration plan from one backend to another."""
    source_backend: BackendType
    target_backend: BackendType
    estimated_duration_minutes: int
    required_disk_space_gb: float
    pre_migration_checks: List[str]
    migration_steps: List[str]
    rollback_steps: List[str]
    risk_level: str  # 'low', 'medium', 'high'


class MigrationPlanner:
    """Creates and manages migration plans between backends."""
    
    def __init__(self):
        """Initialize migration planner."""
        self.detector = BackendDetector()
    
    def create_migration_plan(self, source: BackendType, target: BackendType) -> MigrationPlan:
        """Create a detailed migration plan."""
        metrics = self.detector.collect_metrics()
        
        # Estimate duration based on data size and complexity
        base_duration = self._estimate_base_duration(source, target)
        data_factor = max(1.0, metrics.data_size_mb / 1000.0)  # 1 minute per GB
        estimated_duration = int(base_duration * data_factor)
        
        # Estimate disk space (2x current data for safety during migration)
        required_space = max(1.0, metrics.data_size_mb / 1000.0 * 2)
        
        plan = MigrationPlan(
            source_backend=source,
            target_backend=target,
            estimated_duration_minutes=estimated_duration,
            required_disk_space_gb=required_space,
            pre_migration_checks=self._get_pre_migration_checks(source, target),
            migration_steps=self._get_migration_steps(source, target),
            rollback_steps=self._get_rollback_steps(source, target),
            risk_level=self._assess_risk_level(source, target, metrics)
        )
        
        logger.info(f"Created migration plan: {source.value} → {target.value} "
                   f"({estimated_duration}min, {required_space:.1f}GB)")
        
        return plan
    
    def _estimate_base_duration(self, source: BackendType, target: BackendType) -> int:
        """Estimate base migration duration in minutes."""
        # Migration complexity matrix
        durations = {
            (BackendType.SQLITE, BackendType.POSTGRESQL): 15,
            (BackendType.SQLITE, BackendType.PGVECTOR): 20,
            (BackendType.POSTGRESQL, BackendType.SQLITE): 10,
            (BackendType.POSTGRESQL, BackendType.PGVECTOR): 5,
            (BackendType.PGVECTOR, BackendType.POSTGRESQL): 10,
            (BackendType.PGVECTOR, BackendType.SQLITE): 15,
        }
        
        return durations.get((source, target), 30)  # Default 30 minutes
    
    def _get_pre_migration_checks(self, source: BackendType, target: BackendType) -> List[str]:
        """Get pre-migration checks."""
        checks = [
            "Verify Pensieve service is running",
            "Check available disk space",
            "Create backup of current database",
            "Verify network connectivity"
        ]
        
        if target in [BackendType.POSTGRESQL, BackendType.PGVECTOR]:
            checks.extend([
                "Verify PostgreSQL server is accessible",
                "Check PostgreSQL version compatibility",
                "Verify database user permissions"
            ])
        
        if target == BackendType.PGVECTOR:
            checks.append("Verify pgvector extension is installed")
        
        return checks
    
    def _get_migration_steps(self, source: BackendType, target: BackendType) -> List[str]:
        """Get migration steps."""
        steps = [
            "Stop Pensieve service",
            "Create database backup",
            "Export data from source database"
        ]
        
        if target == BackendType.POSTGRESQL:
            steps.extend([
                "Create PostgreSQL database",
                "Set up database schema",
                "Import data to PostgreSQL",
                "Update Pensieve configuration",
                "Test database connectivity"
            ])
        elif target == BackendType.PGVECTOR:
            steps.extend([
                "Create PostgreSQL database with pgvector",
                "Set up database schema with vector columns",
                "Import data to PostgreSQL",
                "Create vector indexes",
                "Update Pensieve configuration for vector operations",
                "Test vector operations"
            ])
        elif target == BackendType.SQLITE:
            steps.extend([
                "Create SQLite database",
                "Set up database schema",
                "Import data to SQLite",
                "Update Pensieve configuration",
                "Optimize SQLite indexes"
            ])
        
        steps.extend([
            "Verify data integrity",
            "Update application configuration",
            "Restart Pensieve service",
            "Run post-migration tests"
        ])
        
        return steps
    
    def _get_rollback_steps(self, source: BackendType, target: BackendType) -> List[str]:
        """Get rollback steps in case migration fails."""
        return [
            "Stop Pensieve service",
            f"Restore {source.value} database from backup",
            f"Revert Pensieve configuration to {source.value}",
            "Restart Pensieve service",
            "Verify system is operational",
            "Clean up failed migration artifacts"
        ]
    
    def _assess_risk_level(self, source: BackendType, target: BackendType, metrics) -> str:
        """Assess migration risk level."""
        # High risk conditions
        if metrics.entity_count > 100000:
            return 'high'
        
        if metrics.data_size_mb > 10000:  # >10GB
            return 'high'
        
        # Medium risk conditions
        if (source == BackendType.SQLITE and target == BackendType.PGVECTOR):
            return 'medium'
        
        if metrics.entity_count > 10000:
            return 'medium'
        
        # Low risk for small datasets and simple migrations
        return 'low'
    
    def validate_migration_plan(self, plan: MigrationPlan) -> Dict[str, Any]:
        """Validate a migration plan before execution."""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check disk space
        try:
            import shutil
            free_space_gb = shutil.disk_usage('.').free / (1024**3)
            if free_space_gb < plan.required_disk_space_gb:
                validation_results['errors'].append(
                    f"Insufficient disk space: {free_space_gb:.1f}GB available, "
                    f"{plan.required_disk_space_gb:.1f}GB required"
                )
                validation_results['valid'] = False
        except Exception as e:
            validation_results['warnings'].append(f"Could not check disk space: {e}")
        
        # Check source backend
        current_backend = self.detector.detect_current_backend()
        if current_backend != plan.source_backend:
            validation_results['errors'].append(
                f"Source backend mismatch: expected {plan.source_backend.value}, "
                f"found {current_backend.value}"
            )
            validation_results['valid'] = False
        
        # Risk-based recommendations
        if plan.risk_level == 'high':
            validation_results['recommendations'].extend([
                "Consider performing migration during maintenance window",
                "Have database administrator review the plan",
                "Test migration on a copy of the data first"
            ])
        elif plan.risk_level == 'medium':
            validation_results['recommendations'].append(
                "Consider scheduling during low-usage period"
            )
        
        return validation_results


def get_migration_planner() -> MigrationPlanner:
    """Get singleton migration planner instance."""
    if not hasattr(get_migration_planner, '_instance'):
        get_migration_planner._instance = MigrationPlanner()
    return get_migration_planner._instance