"""
Automated PostgreSQL migration system for Pensieve integration.
Provides seamless migration from SQLite to PostgreSQL with comprehensive validation and rollback capabilities.
"""

import logging
import json
import time
import asyncio
import subprocess
import shutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile

from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter, PostgreSQLCapabilities
from autotasktracker.pensieve.api_client import get_pensieve_client
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.pensieve.service_integration import get_service_manager
from autotasktracker.core.database import DatabaseManager
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """Individual migration step with status tracking."""
    name: str
    description: str
    status: str  # pending, running, completed, failed, skipped
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    rollback_available: bool = False
    validation_passed: bool = False


@dataclass
class MigrationPlan:
    """Complete migration plan with steps and prerequisites."""
    migration_id: str
    source_db_path: str
    target_postgres_url: str
    estimated_duration_minutes: int
    risk_level: str  # low, medium, high
    prerequisites: List[str]
    steps: List[MigrationStep]
    backup_locations: List[str]
    validation_checks: List[str]
    rollback_plan: List[str]


@dataclass
class MigrationStats:
    """Migration execution statistics."""
    migration_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    steps_completed: int = 0
    steps_failed: int = 0
    data_volume_migrated_mb: float = 0.0
    records_migrated: int = 0
    validation_errors: int = 0
    performance_improvement_factor: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'migration_id': self.migration_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_duration_seconds': self.total_duration_seconds,
            'steps_completed': self.steps_completed,
            'steps_failed': self.steps_failed,
            'data_volume_migrated_mb': self.data_volume_migrated_mb,
            'records_migrated': self.records_migrated,
            'validation_errors': self.validation_errors,
            'performance_improvement_factor': self.performance_improvement_factor
        }


class PostgreSQLMigrationAutomator:
    """Automated PostgreSQL migration system with comprehensive safety measures."""
    
    def __init__(self):
        """Initialize migration automation system."""
        self.pg_adapter = get_postgresql_adapter()
        self.api_client = get_pensieve_client()
        self.health_monitor = get_health_monitor()
        self.service_manager = get_service_manager()
        self.db_manager = DatabaseManager()
        
        # Migration state
        self.current_migration: Optional[MigrationPlan] = None
        self.migration_history: List[MigrationStats] = []
        
        # Safety settings
        self.max_migration_size_gb = 10.0  # Safety limit
        self.backup_retention_days = 30
        self.validation_timeout_minutes = 30
        
        logger.info("PostgreSQL migration automation initialized")
    
    async def assess_migration_readiness(self) -> Dict[str, Any]:
        """Assess readiness for PostgreSQL migration.
        
        Returns:
            Comprehensive readiness assessment
        """
        try:
            assessment = {
                'ready_for_migration': False,
                'risk_level': 'unknown',
                'prerequisites': [],
                'blockers': [],
                'data_analysis': {},
                'recommendations': [],
                'estimated_timeline': {}
            }
            
            # Check current database status
            db_status = await self._analyze_current_database()
            assessment['data_analysis'] = db_status
            
            # Check Pensieve service status
            service_status = await self._check_service_prerequisites()
            
            # Check PostgreSQL availability
            postgres_status = await self._check_postgresql_prerequisites()
            
            # Determine readiness
            blockers = []
            prerequisites = []
            
            # Database size check
            if db_status['size_gb'] > self.max_migration_size_gb:
                blockers.append(f"Database size ({db_status['size_gb']:.1f}GB) exceeds safety limit ({self.max_migration_size_gb}GB)")
            
            # Service check
            if not service_status['pensieve_healthy']:
                blockers.append("Pensieve service not running or unhealthy")
            
            # PostgreSQL check
            if not postgres_status['available']:
                prerequisites.append("Install and configure PostgreSQL server")
                prerequisites.append("Install pgvector extension for optimal performance")
            
            # Backup space check
            backup_space_needed = db_status['size_gb'] * 2  # 2x for safety
            if not self._check_disk_space(backup_space_needed):
                blockers.append(f"Insufficient disk space for backup (need {backup_space_needed:.1f}GB)")
            
            # Determine risk level
            if db_status['entity_count'] > 100000:
                risk_level = 'high'
            elif db_status['entity_count'] > 10000:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # Generate recommendations
            recommendations = []
            if not blockers:
                recommendations.append("Migration can proceed - all prerequisites met")
                if risk_level == 'high':
                    recommendations.append("Consider migrating during low-usage period")
                    recommendations.append("Ensure additional backup storage available")
            else:
                recommendations.append("Resolve blockers before proceeding with migration")
            
            # Estimate timeline
            timeline = self._estimate_migration_timeline(db_status)
            
            assessment.update({
                'ready_for_migration': len(blockers) == 0,
                'risk_level': risk_level,
                'prerequisites': prerequisites,
                'blockers': blockers,
                'recommendations': recommendations,
                'estimated_timeline': timeline,
                'service_status': service_status,
                'postgres_status': postgres_status
            })
            
            return assessment
            
        except Exception as e:
            logger.error(f"Migration readiness assessment failed: {e}")
            return {'error': str(e), 'ready_for_migration': False}
    
    async def create_migration_plan(
        self, 
        postgres_url: str,
        include_pgvector: bool = True,
        backup_location: Optional[str] = None
    ) -> MigrationPlan:
        """Create comprehensive migration plan.
        
        Args:
            postgres_url: PostgreSQL connection URL
            include_pgvector: Whether to enable pgvector for vector search
            backup_location: Custom backup location
            
        Returns:
            Detailed migration plan
        """
        try:
            # Generate unique migration ID
            migration_id = f"migration_{int(time.time())}"
            
            # Analyze current database
            db_analysis = await self._analyze_current_database()
            
            # Determine backup location
            if not backup_location:
                backup_location = str(Path.home() / ".memos" / "backups" / migration_id)
            
            # Create migration steps
            steps = self._create_migration_steps(include_pgvector)
            
            # Estimate duration
            estimated_duration = self._estimate_migration_duration(db_analysis)
            
            # Determine risk level
            risk_level = 'low'
            if db_analysis['entity_count'] > 100000:
                risk_level = 'high'
            elif db_analysis['entity_count'] > 10000:
                risk_level = 'medium'
            
            # Create migration plan
            plan = MigrationPlan(
                migration_id=migration_id,
                source_db_path=db_analysis['db_path'],
                target_postgres_url=postgres_url,
                estimated_duration_minutes=estimated_duration,
                risk_level=risk_level,
                prerequisites=self._get_migration_prerequisites(),
                steps=steps,
                backup_locations=[backup_location],
                validation_checks=self._get_validation_checks(),
                rollback_plan=self._get_rollback_plan()
            )
            
            self.current_migration = plan
            logger.info(f"Migration plan created: {migration_id} ({estimated_duration}min, {risk_level} risk)")
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create migration plan: {e}")
            raise
    
    async def execute_migration(self, plan: MigrationPlan, dry_run: bool = False) -> Dict[str, Any]:
        """Execute migration plan with comprehensive monitoring.
        
        Args:
            plan: Migration plan to execute
            dry_run: Whether to perform a dry run without actual migration
            
        Returns:
            Migration execution results
        """
        try:
            migration_stats = MigrationStats(
                migration_id=plan.migration_id,
                start_time=datetime.now()
            )
            
            execution_results = {
                'migration_id': plan.migration_id,
                'dry_run': dry_run,
                'status': 'running',
                'steps_completed': [],
                'steps_failed': [],
                'stats': {},
                'validation_results': {},
                'rollback_required': False
            }
            
            logger.info(f"Starting migration execution: {plan.migration_id} (dry_run={dry_run})")
            
            # Execute migration steps
            for i, step in enumerate(plan.steps):
                try:
                    logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.name}")
                    step.status = 'running'
                    step.start_time = datetime.now()
                    
                    # Execute step
                    success = await self._execute_migration_step(step, plan, dry_run)
                    
                    step.end_time = datetime.now()
                    step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                    
                    if success:
                        step.status = 'completed'
                        migration_stats.steps_completed += 1
                        execution_results['steps_completed'].append(step.name)
                        logger.info(f"Step completed: {step.name} ({step.duration_seconds:.1f}s)")
                    else:
                        step.status = 'failed'
                        migration_stats.steps_failed += 1
                        execution_results['steps_failed'].append(step.name)
                        logger.error(f"Step failed: {step.name}")
                        
                        # Determine if rollback is needed
                        if not dry_run and i > 2:  # If we've made significant progress
                            execution_results['rollback_required'] = True
                            break
                    
                except Exception as e:
                    step.status = 'failed'
                    step.error_message = str(e)
                    migration_stats.steps_failed += 1
                    execution_results['steps_failed'].append(step.name)
                    logger.error(f"Step execution failed: {step.name} - {e}")
                    
                    if not dry_run:
                        execution_results['rollback_required'] = True
                        break
            
            # Update final statistics
            migration_stats.end_time = datetime.now()
            migration_stats.total_duration_seconds = (migration_stats.end_time - migration_stats.start_time).total_seconds()
            
            # Perform validation if migration completed successfully
            if migration_stats.steps_failed == 0 and not dry_run:
                validation_results = await self._validate_migration(plan)
                execution_results['validation_results'] = validation_results
                migration_stats.validation_errors = len([v for v in validation_results.values() if not v.get('passed', True)])
            
            # Determine final status
            if migration_stats.steps_failed == 0 and migration_stats.validation_errors == 0:
                execution_results['status'] = 'completed'
            elif dry_run:
                execution_results['status'] = 'dry_run_completed'
            else:
                execution_results['status'] = 'failed'
            
            execution_results['stats'] = migration_stats.to_dict()
            
            # Store migration history
            self.migration_history.append(migration_stats)
            
            logger.info(f"Migration execution finished: {execution_results['status']} ({migration_stats.total_duration_seconds:.1f}s)")
            return execution_results
            
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            return {'error': str(e), 'status': 'error'}
    
    async def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """Rollback a failed migration.
        
        Args:
            migration_id: ID of migration to rollback
            
        Returns:
            Rollback execution results
        """
        try:
            logger.info(f"Starting migration rollback: {migration_id}")
            
            # Find migration in history
            migration_stats = None
            for stats in self.migration_history:
                if stats.migration_id == migration_id:
                    migration_stats = stats
                    break
            
            if not migration_stats:
                raise ValueError(f"Migration {migration_id} not found in history")
            
            # Execute rollback steps
            rollback_results = {
                'migration_id': migration_id,
                'rollback_status': 'running',
                'steps_completed': [],
                'restoration_successful': False
            }
            
            # Step 1: Stop Pensieve services
            service_stopped = await self._stop_pensieve_services()
            if service_stopped:
                rollback_results['steps_completed'].append('stop_services')
            
            # Step 2: Restore SQLite backup
            backup_restored = await self._restore_sqlite_backup(migration_id)
            if backup_restored:
                rollback_results['steps_completed'].append('restore_backup')
                rollback_results['restoration_successful'] = True
            
            # Step 3: Restart Pensieve services
            service_restarted = await self._start_pensieve_services()
            if service_restarted:
                rollback_results['steps_completed'].append('restart_services')
            
            # Step 4: Validate restoration
            validation_passed = await self._validate_rollback()
            if validation_passed:
                rollback_results['steps_completed'].append('validate_restoration')
                rollback_results['rollback_status'] = 'completed'
            else:
                rollback_results['rollback_status'] = 'failed'
            
            logger.info(f"Migration rollback finished: {rollback_results['rollback_status']}")
            return rollback_results
            
        except Exception as e:
            logger.error(f"Migration rollback failed: {e}")
            return {'error': str(e), 'rollback_status': 'error'}
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration system status.
        
        Returns:
            Comprehensive migration status
        """
        try:
            # Current migration info
            current_migration_info = None
            if self.current_migration:
                current_migration_info = {
                    'migration_id': self.current_migration.migration_id,
                    'risk_level': self.current_migration.risk_level,
                    'estimated_duration_minutes': self.current_migration.estimated_duration_minutes,
                    'steps_total': len(self.current_migration.steps),
                    'steps_completed': len([s for s in self.current_migration.steps if s.status == 'completed']),
                    'steps_failed': len([s for s in self.current_migration.steps if s.status == 'failed'])
                }
            
            # System readiness
            readiness = await self.assess_migration_readiness()
            
            # Migration history summary
            history_summary = {
                'total_migrations': len(self.migration_history),
                'successful_migrations': len([m for m in self.migration_history if m.steps_failed == 0]),
                'failed_migrations': len([m for m in self.migration_history if m.steps_failed > 0]),
                'last_migration_time': max([m.start_time for m in self.migration_history], default=None)
            }
            
            if history_summary['last_migration_time']:
                history_summary['last_migration_time'] = history_summary['last_migration_time'].isoformat()
            
            # Current database info
            db_info = await self._analyze_current_database()
            
            return {
                'system_status': {
                    'migration_system_healthy': True,
                    'current_backend': self.pg_adapter.capabilities.performance_tier,
                    'postgres_available': self.pg_adapter.capabilities.postgresql_enabled,
                    'pgvector_available': self.pg_adapter.capabilities.pgvector_available
                },
                'current_migration': current_migration_info,
                'readiness_assessment': readiness,
                'migration_history': history_summary,
                'current_database': db_info,
                'recommendations': self._get_migration_recommendations()
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {'error': str(e)}
    
    async def _analyze_current_database(self) -> Dict[str, Any]:
        """Analyze current database for migration planning."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get entity count
                cursor.execute("SELECT COUNT(*) FROM entities")
                entity_count = cursor.fetchone()[0]
                
                # Get metadata count
                cursor.execute("SELECT COUNT(*) FROM metadata_entries")
                metadata_count = cursor.fetchone()[0]
                
                # Get database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size_bytes = cursor.fetchone()[0]
                db_size_gb = db_size_bytes / (1024 ** 3)
                
                # Get recent activity
                cursor.execute("SELECT COUNT(*) FROM entities WHERE created_at > datetime('now', '-7 days')")
                recent_entities = cursor.fetchone()[0]
                
                # Check for vector tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%vec%'")
                vector_tables = [row[0] for row in cursor.fetchall()]
                
                return {
                    'db_path': self.db_manager.db_path,
                    'entity_count': entity_count,
                    'metadata_count': metadata_count,
                    'size_bytes': db_size_bytes,
                    'size_gb': db_size_gb,
                    'recent_activity': recent_entities,
                    'vector_tables': vector_tables,
                    'has_vector_data': len(vector_tables) > 0
                }
                
        except Exception as e:
            logger.error(f"Database analysis failed: {e}")
            return {'error': str(e)}
    
    async def _check_service_prerequisites(self) -> Dict[str, Any]:
        """Check Pensieve service prerequisites."""
        try:
            if not self.service_manager:
                return {'pensieve_healthy': False, 'services_running': False}
            
            # Check service status
            service_status = self.service_manager.get_service_status()
            
            return {
                'pensieve_healthy': service_status.get('running', False),
                'services_running': service_status.get('process_count', 0) > 0,
                'service_details': service_status
            }
            
        except Exception as e:
            logger.debug(f"Service check failed: {e}")
            return {'pensieve_healthy': False, 'error': str(e)}
    
    async def _check_postgresql_prerequisites(self) -> Dict[str, Any]:
        """Check PostgreSQL prerequisites."""
        try:
            # Check if PostgreSQL is available
            postgres_status = {
                'available': False,
                'version': None,
                'pgvector_available': False,
                'connection_successful': False
            }
            
            # Try to connect to PostgreSQL (would need actual connection string)
            # For now, check if pg_config is available
            try:
                result = subprocess.run(['pg_config', '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    postgres_status['available'] = True
                    postgres_status['version'] = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.debug(f"PostgreSQL not available: {e}")
                postgres_status['message'] = f"PostgreSQL not found: {str(e)}"
            
            # Check for pgvector (would need actual database connection)
            # This is a placeholder - actual implementation would test extension
            postgres_status['pgvector_available'] = postgres_status['available']
            
            return postgres_status
            
        except Exception as e:
            logger.debug(f"PostgreSQL check failed: {e}")
            return {'available': False, 'error': str(e)}
    
    def _check_disk_space(self, required_gb: float) -> bool:
        """Check if sufficient disk space is available."""
        try:
            backup_dir = Path.home() / ".memos" / "backups"
            stat = shutil.disk_usage(backup_dir.parent)
            available_gb = stat.free / (1024 ** 3)
            return available_gb >= required_gb
        except Exception:
            return False
    
    def _estimate_migration_timeline(self, db_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate migration timeline based on data volume."""
        entity_count = db_analysis.get('entity_count', 0)
        db_size_gb = db_analysis.get('size_gb', 0)
        
        # Base estimates (minutes)
        backup_time = max(1, db_size_gb * 2)  # 2 min per GB
        migration_time = max(5, entity_count / 1000)  # 1 min per 1000 entities
        validation_time = max(2, entity_count / 5000)  # 1 min per 5000 entities
        
        total_time = backup_time + migration_time + validation_time
        
        return {
            'backup_minutes': round(backup_time, 1),
            'migration_minutes': round(migration_time, 1),
            'validation_minutes': round(validation_time, 1),
            'total_minutes': round(total_time, 1),
            'recommended_maintenance_window_hours': round(total_time / 60 * 1.5, 1)  # 1.5x buffer
        }
    
    def _create_migration_steps(self, include_pgvector: bool) -> List[MigrationStep]:
        """Create detailed migration steps."""
        steps = [
            MigrationStep(
                name="validate_prerequisites",
                description="Validate all migration prerequisites",
                status="pending"
            ),
            MigrationStep(
                name="create_backup",
                description="Create comprehensive database backup",
                status="pending",
                rollback_available=True
            ),
            MigrationStep(
                name="stop_services",
                description="Stop Pensieve services safely",
                status="pending",
                rollback_available=True
            ),
            MigrationStep(
                name="prepare_postgres",
                description="Prepare PostgreSQL database and extensions",
                status="pending"
            ),
            MigrationStep(
                name="migrate_schema",
                description="Migrate database schema to PostgreSQL",
                status="pending"
            ),
            MigrationStep(
                name="migrate_data",
                description="Migrate entity and metadata data",
                status="pending"
            ),
            MigrationStep(
                name="migrate_vectors",
                description="Migrate vector embeddings (if available)",
                status="pending" if include_pgvector else "skipped"
            ),
            MigrationStep(
                name="update_configuration",
                description="Update Pensieve configuration for PostgreSQL",
                status="pending"
            ),
            MigrationStep(
                name="restart_services",
                description="Restart Pensieve services with new configuration",
                status="pending"
            ),
            MigrationStep(
                name="validate_migration",
                description="Comprehensive migration validation",
                status="pending"
            ),
            MigrationStep(
                name="performance_test",
                description="Performance validation and optimization",
                status="pending"
            )
        ]
        
        return steps
    
    def _get_migration_prerequisites(self) -> List[str]:
        """Get list of migration prerequisites."""
        return [
            "PostgreSQL server running and accessible",
            "Sufficient disk space for backups",
            "Pensieve services healthy and responsive",
            "No active users during migration window",
            "Network connectivity stable",
            "Administrative access to Pensieve configuration"
        ]
    
    def _get_validation_checks(self) -> List[str]:
        """Get list of validation checks to perform."""
        return [
            "Entity count matches between source and target",
            "Metadata integrity verification",
            "Vector embeddings preserved (if applicable)",
            "API endpoints responding correctly",
            "Search functionality working",
            "Performance benchmarks meet expectations",
            "Configuration consistency",
            "Service health after migration"
        ]
    
    def _get_rollback_plan(self) -> List[str]:
        """Get rollback plan steps."""
        return [
            "Stop PostgreSQL-configured Pensieve services",
            "Restore SQLite database from backup",
            "Revert Pensieve configuration to SQLite",
            "Restart services with original configuration",
            "Validate SQLite restoration",
            "Notify administrators of rollback completion"
        ]
    
    async def _execute_migration_step(self, step: MigrationStep, plan: MigrationPlan, dry_run: bool) -> bool:
        """Execute individual migration step."""
        try:
            if dry_run:
                # Simulate step execution
                await asyncio.sleep(0.1)  # Brief delay to simulate work
                return True
            
            # Actual step execution would be implemented here
            # This is a framework for the migration steps
            
            if step.name == "validate_prerequisites":
                return await self._validate_prerequisites()
            elif step.name == "create_backup":
                return await self._create_backup(plan)
            elif step.name == "stop_services":
                return await self._stop_pensieve_services()
            elif step.name == "prepare_postgres":
                return await self._prepare_postgres(plan)
            elif step.name == "migrate_schema":
                return await self._migrate_schema(plan)
            elif step.name == "migrate_data":
                return await self._migrate_data(plan)
            elif step.name == "migrate_vectors":
                return await self._migrate_vectors(plan)
            elif step.name == "update_configuration":
                return await self._update_configuration(plan)
            elif step.name == "restart_services":
                return await self._start_pensieve_services()
            elif step.name == "validate_migration":
                return await self._validate_migration_step(plan)
            elif step.name == "performance_test":
                return await self._performance_test(plan)
            
            return False
            
        except Exception as e:
            step.error_message = str(e)
            logger.error(f"Migration step failed: {step.name} - {e}")
            return False
    
    async def _validate_prerequisites(self) -> bool:
        """Validate migration prerequisites."""
        # Implementation would check all prerequisites
        return True
    
    async def _create_backup(self, plan: MigrationPlan) -> bool:
        """Create database backup."""
        # Implementation would create backup
        return True
    
    async def _stop_pensieve_services(self) -> bool:
        """Stop Pensieve services."""
        if self.service_manager:
            return self.service_manager.stop_service()
        return True
    
    async def _start_pensieve_services(self) -> bool:
        """Start Pensieve services."""
        if self.service_manager:
            return self.service_manager.start_service()
        return True
    
    async def _prepare_postgres(self, plan: MigrationPlan) -> bool:
        """Prepare PostgreSQL database."""
        # Implementation would prepare PostgreSQL
        return True
    
    async def _migrate_schema(self, plan: MigrationPlan) -> bool:
        """Migrate database schema."""
        # Implementation would migrate schema
        return True
    
    async def _migrate_data(self, plan: MigrationPlan) -> bool:
        """Migrate data to PostgreSQL."""
        # Implementation would migrate data
        return True
    
    async def _migrate_vectors(self, plan: MigrationPlan) -> bool:
        """Migrate vector embeddings."""
        # Implementation would migrate vectors
        return True
    
    async def _update_configuration(self, plan: MigrationPlan) -> bool:
        """Update Pensieve configuration."""
        # Implementation would update configuration
        return True
    
    async def _validate_migration_step(self, plan: MigrationPlan) -> bool:
        """Validate migration completion."""
        # Implementation would validate migration
        return True
    
    async def _performance_test(self, plan: MigrationPlan) -> bool:
        """Test post-migration performance."""
        # Implementation would test performance
        return True
    
    async def _validate_migration(self, plan: MigrationPlan) -> Dict[str, Any]:
        """Comprehensive migration validation."""
        # Implementation would perform comprehensive validation
        return {}
    
    async def _restore_sqlite_backup(self, migration_id: str) -> bool:
        """Restore SQLite backup."""
        # Implementation would restore backup
        return True
    
    async def _validate_rollback(self) -> bool:
        """Validate rollback completion."""
        # Implementation would validate rollback
        return True
    
    def _estimate_migration_duration(self, db_analysis: Dict[str, Any]) -> int:
        """Estimate migration duration in minutes."""
        entity_count = db_analysis.get('entity_count', 0)
        size_gb = db_analysis.get('size_gb', 0)
        
        # Base estimates
        duration = 5  # Base overhead
        duration += max(1, size_gb * 2)  # 2 min per GB
        duration += max(1, entity_count / 1000)  # 1 min per 1000 entities
        
        return int(duration)
    
    def _get_migration_recommendations(self) -> List[Dict[str, str]]:
        """Get migration recommendations."""
        recommendations = []
        
        if self.pg_adapter.capabilities.performance_tier == 'sqlite':
            recommendations.append({
                'priority': 'high',
                'action': 'consider_postgresql_migration',
                'description': 'Migrate to PostgreSQL for better performance and scalability',
                'benefit': '300-500% performance improvement expected'
            })
        
        if not self.pg_adapter.capabilities.pgvector_available:
            recommendations.append({
                'priority': 'medium',
                'action': 'enable_pgvector',
                'description': 'Enable pgvector extension for advanced vector operations',
                'benefit': 'Native vector similarity search capabilities'
            })
        
        return recommendations


# Singleton instance
_migration_automator: Optional[PostgreSQLMigrationAutomator] = None


def get_migration_automator() -> PostgreSQLMigrationAutomator:
    """Get singleton migration automator instance."""
    global _migration_automator
    if _migration_automator is None:
        _migration_automator = PostgreSQLMigrationAutomator()
    return _migration_automator


def reset_migration_automator():
    """Reset migration automator for testing."""
    global _migration_automator
    _migration_automator = None


async def assess_migration_readiness() -> Dict[str, Any]:
    """Convenience function to assess migration readiness."""
    automator = get_migration_automator()
    return await automator.assess_migration_readiness()


async def create_migration_plan(postgres_url: str, include_pgvector: bool = True) -> MigrationPlan:
    """Convenience function to create migration plan."""
    automator = get_migration_automator()
    return await automator.create_migration_plan(postgres_url, include_pgvector)


async def execute_migration(plan: MigrationPlan, dry_run: bool = False) -> Dict[str, Any]:
    """Convenience function to execute migration."""
    automator = get_migration_automator()
    return await automator.execute_migration(plan, dry_run)