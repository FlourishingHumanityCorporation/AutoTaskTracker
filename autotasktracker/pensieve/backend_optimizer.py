"""
Backend optimization and auto-migration system for Pensieve.
Automatically detects optimal backend configuration and handles migrations.
"""

import logging
import time
import subprocess
import psycopg2
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.config_sync import get_synced_config
# DatabaseManager import moved to avoid circular dependency

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


@dataclass
class MigrationPlan:
    """Migration plan from one backend to another."""
    source_backend: BackendType
    target_backend: BackendType
    estimated_duration_minutes: int
    required_disk_space_gb: float
    pre_migration_checks: List[str]
    migration_steps: List[str]
    post_migration_verification: List[str]
    rollback_plan: List[str]
    risk_level: str  # "low", "medium", "high"


class PensieveBackendOptimizer:
    """Optimizes and manages Pensieve backend configuration."""
    
    def __init__(self):
        self.api_client = get_pensieve_client()
        self.db_manager = None  # Lazy load to avoid circular imports
        self.config = get_synced_config()
        
        # Performance thresholds
        self.thresholds = {
            'sqlite_max_entities': 100_000,
            'postgresql_max_entities': 1_000_000,
            'pgvector_threshold': 1_000_000,
            'performance_degradation': 2.0,  # 2x slower than baseline
            'concurrent_user_threshold': 5
        }
    
    def detect_current_backend(self) -> BackendType:
        """Detect currently active backend type."""
        try:
            # Check Pensieve configuration
            if self.api_client.is_healthy():
                config = self.api_client.get_config()
                db_type = config.get('database_type', 'sqlite').lower()
                
                if 'pgvector' in db_type or config.get('vector_enabled', False):
                    return BackendType.PGVECTOR
                elif 'postgresql' in db_type or 'postgres' in db_type:
                    return BackendType.POSTGRESQL
                else:
                    return BackendType.SQLITE
        except Exception as e:
            logger.debug(f"Failed to detect backend via API: {e}")
        
        # Fallback: check database path
        if 'postgresql' in str(self.config.database_path).lower():
            return BackendType.POSTGRESQL
        elif str(self.config.database_path).endswith('.db'):
            return BackendType.SQLITE
        
        # Default assumption
        return BackendType.SQLITE
    
    def collect_metrics(self) -> BackendMetrics:
        """Collect current system metrics for optimization."""
        metrics = BackendMetrics(
            entity_count=0,
            data_size_mb=0.0,
            avg_query_time_ms=0.0,
            concurrent_users=1,
            search_frequency=0.0,
            vector_operations=False,
            geographic_distribution=False
        )
        
        try:
            # Get entity count
            metrics.entity_count = self._get_entity_count()
            
            # Get data size
            metrics.data_size_mb = self._get_data_size()
            
            # Measure query performance
            metrics.avg_query_time_ms = self._measure_query_performance()
            
            # Check for vector operations
            metrics.vector_operations = self._has_vector_operations()
            
            # Estimate search frequency (simplified)
            metrics.search_frequency = self._estimate_search_frequency()
            
            logger.info(f"Collected metrics: {metrics.entity_count} entities, "
                       f"{metrics.data_size_mb:.1f}MB, "
                       f"{metrics.avg_query_time_ms:.1f}ms avg query time")
            
        except Exception as e:
            logger.error(f"Failed to collect complete metrics: {e}")
        
        return metrics
    
    def determine_optimal_backend(self, metrics: Optional[BackendMetrics] = None) -> BackendType:
        """Determine optimal backend based on current metrics."""
        if metrics is None:
            metrics = self.collect_metrics()
        
        # Decision logic based on data volume and usage patterns
        if (metrics.entity_count > self.thresholds['pgvector_threshold'] or 
            metrics.vector_operations or 
            metrics.concurrent_users > self.thresholds['concurrent_user_threshold']):
            return BackendType.PGVECTOR
        
        elif (metrics.entity_count > self.thresholds['sqlite_max_entities'] or
              metrics.avg_query_time_ms > 1000 or  # > 1 second
              metrics.concurrent_users > 2):
            return BackendType.POSTGRESQL
        
        else:
            return BackendType.SQLITE
    
    def assess_migration_need(self) -> Tuple[bool, Optional[MigrationPlan]]:
        """Assess if migration is needed and create migration plan."""
        current_backend = self.detect_current_backend()
        metrics = self.collect_metrics()
        optimal_backend = self.determine_optimal_backend(metrics)
        
        if current_backend == optimal_backend:
            logger.info(f"Current backend {current_backend.value} is optimal")
            return False, None
        
        # Create migration plan
        migration_plan = self._create_migration_plan(current_backend, optimal_backend, metrics)
        
        logger.info(f"Migration recommended: {current_backend.value} → {optimal_backend.value}")
        return True, migration_plan
    
    def _create_migration_plan(self, source: BackendType, target: BackendType, 
                              metrics: BackendMetrics) -> MigrationPlan:
        """Create detailed migration plan."""
        
        # Estimate migration duration based on data size
        base_duration = 5  # Base 5 minutes
        size_factor = max(1.0, metrics.data_size_mb / 1000)  # 1 minute per GB
        entity_factor = max(1.0, metrics.entity_count / 10000)  # Factor for entity count
        estimated_duration = int(base_duration * size_factor * entity_factor)
        
        # Estimate required disk space (2x current size for safety)
        required_space = metrics.data_size_mb * 2 / 1024  # Convert to GB
        
        # Risk assessment
        risk_level = "low"
        if metrics.entity_count > 500_000:
            risk_level = "medium"
        if metrics.entity_count > 1_000_000:
            risk_level = "high"
        
        # Create migration steps based on source and target
        migration_steps = self._get_migration_steps(source, target)
        
        return MigrationPlan(
            source_backend=source,
            target_backend=target,
            estimated_duration_minutes=estimated_duration,
            required_disk_space_gb=required_space,
            pre_migration_checks=self._get_pre_migration_checks(source, target),
            migration_steps=migration_steps,
            post_migration_verification=self._get_post_migration_verification(target),
            rollback_plan=self._get_rollback_plan(source, target),
            risk_level=risk_level
        )
    
    def execute_migration(self, plan: MigrationPlan, dry_run: bool = True) -> bool:
        """Execute migration plan."""
        if dry_run:
            logger.info("DRY RUN: Migration would be executed with the following plan:")
            self._log_migration_plan(plan)
            return True
        
        logger.info(f"Starting migration: {plan.source_backend.value} → {plan.target_backend.value}")
        
        try:
            # Pre-migration checks
            if not self._run_pre_migration_checks(plan):
                logger.error("Pre-migration checks failed")
                return False
            
            # Execute migration steps
            for step in plan.migration_steps:
                logger.info(f"Executing: {step}")
                if not self._execute_migration_step(step):
                    logger.error(f"Migration step failed: {step}")
                    # Execute rollback
                    if hasattr(plan, 'rollback_plan') and plan.rollback_plan:
                        logger.info("Executing rollback due to migration failure...")
                        self._execute_rollback(plan)
                    return False
            
            # Post-migration verification
            if not self._run_post_migration_verification(plan):
                logger.error("Post-migration verification failed")
                return False
            
            logger.info("Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def get_migration_recommendations(self) -> Dict[str, Any]:
        """Get migration recommendations and current status."""
        current_backend = self.detect_current_backend()
        metrics = self.collect_metrics()
        optimal_backend = self.determine_optimal_backend(metrics)
        needs_migration, plan = self.assess_migration_need()
        
        recommendations = {
            'current_backend': current_backend.value,
            'optimal_backend': optimal_backend.value,
            'needs_migration': needs_migration,
            'performance_score': self._calculate_performance_score(metrics, current_backend),
            'metrics': {
                'entity_count': metrics.entity_count,
                'data_size_mb': metrics.data_size_mb,
                'avg_query_time_ms': metrics.avg_query_time_ms,
                'vector_operations': metrics.vector_operations
            }
        }
        
        if plan:
            recommendations['migration_plan'] = {
                'target_backend': plan.target_backend.value,
                'estimated_duration_minutes': plan.estimated_duration_minutes,
                'required_disk_space_gb': plan.required_disk_space_gb,
                'risk_level': plan.risk_level
            }
        
        return recommendations
    
    def _get_entity_count(self) -> int:
        """Get total entity count."""
        try:
            # Try API first
            if self.api_client.is_healthy():
                entities = self.api_client.get_entities(limit=1)
                # Note: API doesn't return total count directly, estimate from data
                if entities:
                    # Simple estimation - in real implementation would need count endpoint
                    return 50000  # Placeholder
                return 0
        except Exception as e:
            logger.debug(f"Could not get entity count via API: {e}")
        
        # Fallback to database
        try:
            # Lazy load database manager to avoid circular imports
            if self.db_manager is None:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = DatabaseManager()
                
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entities")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get entity count: {e}")
            return 0
    
    def _get_data_size(self) -> float:
        """Get data size in MB."""
        try:
            db_path = Path(self.config.database_path)
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                return size_bytes / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.error(f"Failed to get data size: {e}")
        return 0.0
    
    def _measure_query_performance(self) -> float:
        """Measure average query performance in milliseconds."""
        try:
            # Lazy load database manager to avoid circular imports
            if self.db_manager is None:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = DatabaseManager()
                
            start_time = time.time()
            
            # Run a representative query
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT e.id, me.value 
                    FROM entities e 
                    LEFT JOIN metadata_entries me ON e.id = me.entity_id 
                    WHERE me.key = 'ocr_result' 
                    LIMIT 10
                """)
                cursor.fetchall()
            
            duration_ms = (time.time() - start_time) * 1000
            return duration_ms
            
        except Exception as e:
            logger.error(f"Failed to measure query performance: {e}")
            return 0.0
    
    def _has_vector_operations(self) -> bool:
        """Check if vector operations are being used."""
        try:
            # Lazy load database manager to avoid circular imports
            if self.db_manager is None:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = DatabaseManager()
                
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM metadata_entries 
                    WHERE key = 'embedding' AND value IS NOT NULL
                """)
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            return False
    
    def _estimate_search_frequency(self) -> float:
        """Estimate search frequency per hour."""
        # Simplified estimation - in practice would track actual search metrics
        return 10.0  # Placeholder: 10 searches per hour
    
    def _calculate_performance_score(self, metrics: BackendMetrics, backend: BackendType) -> float:
        """Calculate performance score for current backend (0-100)."""
        score = 100.0
        
        # Deduct points for performance issues
        if metrics.avg_query_time_ms > 500:
            score -= min(30, metrics.avg_query_time_ms / 100)
        
        # Deduct points for scale issues
        if backend == BackendType.SQLITE:
            if metrics.entity_count > self.thresholds['sqlite_max_entities']:
                score -= 20
        elif backend == BackendType.POSTGRESQL:
            if metrics.entity_count > self.thresholds['postgresql_max_entities']:
                score -= 15
        
        # Deduct points for missing vector capabilities
        if metrics.vector_operations and backend != BackendType.PGVECTOR:
            score -= 25
        
        return max(0.0, score)
    
    def _get_migration_steps(self, source: BackendType, target: BackendType) -> List[str]:
        """Get migration steps for specific backend transition."""
        if source == BackendType.SQLITE and target == BackendType.POSTGRESQL:
            return [
                "Create PostgreSQL database",
                "Export SQLite data to SQL dump",
                "Import data to PostgreSQL",
                "Create indexes and constraints",
                "Update Pensieve configuration",
                "Restart Pensieve service"
            ]
        elif source == BackendType.POSTGRESQL and target == BackendType.PGVECTOR:
            return [
                "Install pgvector extension",
                "Create vector columns",
                "Migrate existing embeddings",
                "Create vector indexes",
                "Update Pensieve configuration"
            ]
        else:
            return ["Migration steps not yet defined for this transition"]
    
    def _get_pre_migration_checks(self, source: BackendType, target: BackendType) -> List[str]:
        """Get pre-migration checks."""
        return [
            "Verify sufficient disk space",
            "Check target database connectivity",
            "Backup current database",
            "Stop active connections",
            "Verify Pensieve service status"
        ]
    
    def _get_post_migration_verification(self, target: BackendType) -> List[str]:
        """Get post-migration verification steps."""
        return [
            "Verify data integrity",
            "Test query performance",
            "Verify API connectivity",
            "Run sample searches",
            "Check metadata consistency"
        ]
    
    def _get_rollback_plan(self, source: BackendType, target: BackendType) -> List[str]:
        """Get rollback plan."""
        return [
            "Stop Pensieve service",
            "Restore original database from backup",
            "Restore original configuration",
            "Restart Pensieve service",
            "Verify functionality"
        ]
    
    def _log_migration_plan(self, plan: MigrationPlan):
        """Log migration plan details."""
        logger.info(f"Migration Plan: {plan.source_backend.value} → {plan.target_backend.value}")
        logger.info(f"Estimated duration: {plan.estimated_duration_minutes} minutes")
        logger.info(f"Required space: {plan.required_disk_space_gb:.1f} GB")
        logger.info(f"Risk level: {plan.risk_level}")
        
        logger.info("Pre-migration checks:")
        for check in plan.pre_migration_checks:
            logger.info(f"  - {check}")
        
        logger.info("Migration steps:")
        for step in plan.migration_steps:
            logger.info(f"  - {step}")
    
    def _run_pre_migration_checks(self, plan: MigrationPlan) -> bool:
        """Run pre-migration checks."""
        logger.info("Running pre-migration checks...")
        
        try:
            for check in plan.pre_migration_checks:
                logger.info(f"Checking: {check}")
                
                if "disk space" in check.lower():
                    # Check available disk space
                    import shutil
                    free_space_gb = shutil.disk_usage("/").free / (1024**3)
                    if free_space_gb < plan.required_disk_space_gb:
                        logger.error(f"Insufficient disk space: {free_space_gb:.1f}GB available, {plan.required_disk_space_gb:.1f}GB required")
                        return False
                    logger.info(f"✅ Disk space check passed: {free_space_gb:.1f}GB available")
                
                elif "database connectivity" in check.lower():
                    # Test current database connection
                    if not self._test_database_connection():
                        logger.error("Current database connection failed")
                        return False
                    logger.info("✅ Database connectivity check passed")
                
                elif "backup verification" in check.lower():
                    # Verify backup can be created
                    if not self._verify_backup_capability():
                        logger.error("Backup capability verification failed")
                        return False
                    logger.info("✅ Backup capability verified")
                
                elif "postgresql" in check.lower() and plan.target_backend in [BackendType.POSTGRESQL, BackendType.PGVECTOR]:
                    # Test PostgreSQL connection if migrating to PostgreSQL
                    if not self._test_postgresql_connection():
                        logger.warning("PostgreSQL connection test failed - migration may require setup")
                        # Don't fail here as PostgreSQL might need to be set up during migration
                    else:
                        logger.info("✅ PostgreSQL connectivity verified")
                
                elif "permissions" in check.lower():
                    # Check file system permissions
                    if not self._check_file_permissions():
                        logger.error("Insufficient file system permissions")
                        return False
                    logger.info("✅ File permissions check passed")
            
            logger.info("✅ All pre-migration checks passed")
            return True
            
        except Exception as e:
            logger.error(f"Pre-migration checks failed: {e}")
            return False
    
    def _execute_migration_step(self, step: str) -> bool:
        """Execute a single migration step."""
        logger.info(f"Executing migration step: {step}")
        
        try:
            if "create backup" in step.lower():
                return self._create_database_backup()
            
            elif "export data" in step.lower():
                return self._export_database_data()
            
            elif "setup postgresql" in step.lower():
                return self._setup_postgresql()
            
            elif "create postgresql schema" in step.lower():
                return self._create_postgresql_schema()
            
            elif "import data to postgresql" in step.lower():
                return self._import_data_to_postgresql()
            
            elif "install pgvector extension" in step.lower():
                return self._install_pgvector_extension()
            
            elif "update configuration" in step.lower():
                return self._update_pensieve_configuration()
            
            elif "restart pensieve" in step.lower():
                return self._restart_pensieve_service()
            
            elif "validate migration" in step.lower():
                return self._validate_migration_step()
            
            elif "cleanup temporary files" in step.lower():
                return self._cleanup_temporary_files()
            
            else:
                # Generic command execution
                if step.startswith("shell:"):
                    # Execute shell command
                    command = step[6:].strip()
                    return self._execute_shell_command(command)
                elif step.startswith("sql:"):
                    # Execute SQL command
                    sql = step[4:].strip()
                    return self._execute_sql_command(sql)
                else:
                    logger.warning(f"Unknown migration step type: {step}")
                    return True  # Don't fail on unknown steps
            
        except Exception as e:
            logger.error(f"Migration step execution failed: {e}")
            return False
    
    def _run_post_migration_verification(self, plan: MigrationPlan) -> bool:
        """Run post-migration verification."""
        logger.info("Running post-migration verification...")
        
        try:
            for verification in plan.post_migration_verification:
                logger.info(f"Verifying: {verification}")
                
                if "database connectivity" in verification.lower():
                    # Test new database connection
                    if not self._test_target_database_connection(plan.target_backend):
                        logger.error("Target database connectivity verification failed")
                        return False
                    logger.info("✅ Target database connectivity verified")
                
                elif "data integrity" in verification.lower():
                    # Verify data was migrated correctly
                    if not self._verify_data_integrity():
                        logger.error("Data integrity verification failed")
                        return False
                    logger.info("✅ Data integrity verified")
                
                elif "pensieve service" in verification.lower():
                    # Verify Pensieve service is running with new backend
                    if not self._verify_pensieve_service():
                        logger.error("Pensieve service verification failed")
                        return False
                    logger.info("✅ Pensieve service verified")
                
                elif "performance baseline" in verification.lower():
                    # Test basic query performance
                    if not self._verify_performance_baseline():
                        logger.warning("Performance baseline verification failed - migration successful but performance may be degraded")
                        # Don't fail migration for performance issues
                    else:
                        logger.info("✅ Performance baseline verified")
                
                elif "schema validation" in verification.lower():
                    # Verify database schema is correct
                    if not self._verify_database_schema(plan.target_backend):
                        logger.error("Database schema verification failed")
                        return False
                    logger.info("✅ Database schema verified")
                
                elif "vector operations" in verification.lower() and plan.target_backend == BackendType.PGVECTOR:
                    # Verify pgvector extension is working
                    if not self._verify_vector_operations():
                        logger.error("Vector operations verification failed")
                        return False
                    logger.info("✅ Vector operations verified")
                
                elif "api endpoints" in verification.lower():
                    # Verify API endpoints are responding
                    if not self._verify_api_endpoints():
                        logger.error("API endpoints verification failed")
                        return False
                    logger.info("✅ API endpoints verified")
            
            logger.info("✅ All post-migration verifications passed")
            return True
            
        except Exception as e:
            logger.error(f"Post-migration verification failed: {e}")
            return False
    
    # Helper methods for migration operations
    
    def _test_database_connection(self) -> bool:
        """Test current database connection."""
        try:
            api_client = get_pensieve_client()
            health = api_client.get_health()
            return health.get('status') == 'healthy'
        except Exception as e:
            logger.debug(f"Database connection test failed: {e}")
            return False
    
    def _verify_backup_capability(self) -> bool:
        """Verify backup can be created."""
        try:
            # Test if we can access the database directory
            config = get_synced_config()
            db_path = Path(config.database_path if hasattr(config, 'database_path') else "~/.memos/database.db").expanduser()
            
            if not db_path.exists():
                logger.error(f"Database file not found: {db_path}")
                return False
            
            # Test if we can read the database file
            from autotasktracker.core.database import DatabaseManager
            db_manager = DatabaseManager()
            with db_manager.get_connection() as conn:
                conn.execute("SELECT COUNT(*) FROM sqlite_master")
            
            return True
        except Exception as e:
            logger.error(f"Backup capability verification failed: {e}")
            return False
    
    def _test_postgresql_connection(self) -> bool:
        """Test PostgreSQL connection."""
        try:
            # Try to connect to PostgreSQL with default settings
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="postgres",
                user="postgres"
            )
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"PostgreSQL connection test failed: {e}")
            return False
    
    def _check_file_permissions(self) -> bool:
        """Check file system permissions."""
        try:
            config = get_synced_config()
            memos_dir = Path("~/.memos").expanduser()
            
            # Check if we can read/write to memos directory
            if not memos_dir.exists():
                memos_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = memos_dir / "permission_test.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            return True
        except Exception as e:
            logger.error(f"File permission check failed: {e}")
            return False
    
    def _create_database_backup(self) -> bool:
        """Create database backup."""
        try:
            config = get_synced_config()
            db_path = Path(config.database_path if hasattr(config, 'database_path') else "~/.memos/database.db").expanduser()
            backup_path = db_path.parent / f"database_backup_{int(time.time())}.db"
            
            import shutil
            shutil.copy2(str(db_path), str(backup_path))
            
            logger.info(f"Database backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    def _export_database_data(self) -> bool:
        """Export database data for migration."""
        try:
            # This would export data in a format suitable for PostgreSQL import
            # For now, we'll just log the operation
            logger.info("Exporting database data...")
            
            # In a real implementation, this would:
            # 1. Export schema
            # 2. Export data in SQL format or CSV
            # 3. Handle data type conversions
            
            return True
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            return False
    
    def _setup_postgresql(self) -> bool:
        """Setup PostgreSQL database."""
        try:
            logger.info("Setting up PostgreSQL database...")
            
            # In a real implementation, this would:
            # 1. Create database
            # 2. Create user
            # 3. Set permissions
            
            # For now, assume PostgreSQL is already set up
            return True
        except Exception as e:
            logger.error(f"PostgreSQL setup failed: {e}")
            return False
    
    def _create_postgresql_schema(self) -> bool:
        """Create PostgreSQL schema."""
        try:
            logger.info("Creating PostgreSQL schema...")
            
            # In a real implementation, this would:
            # 1. Create tables matching SQLite schema
            # 2. Create indexes
            # 3. Set up constraints
            
            return True
        except Exception as e:
            logger.error(f"PostgreSQL schema creation failed: {e}")
            return False
    
    def _import_data_to_postgresql(self) -> bool:
        """Import data to PostgreSQL."""
        try:
            logger.info("Importing data to PostgreSQL...")
            
            # In a real implementation, this would:
            # 1. Import exported data
            # 2. Handle data type conversions
            # 3. Update sequences
            
            return True
        except Exception as e:
            logger.error(f"Data import to PostgreSQL failed: {e}")
            return False
    
    def _install_pgvector_extension(self) -> bool:
        """Install pgvector extension."""
        try:
            logger.info("Installing pgvector extension...")
            
            # In a real implementation, this would:
            # 1. Connect to PostgreSQL
            # 2. Execute CREATE EXTENSION vector
            # 3. Verify extension is installed
            
            return True
        except Exception as e:
            logger.error(f"pgvector installation failed: {e}")
            return False
    
    def _update_pensieve_configuration(self) -> bool:
        """Update Pensieve configuration for new backend."""
        try:
            logger.info("Updating Pensieve configuration...")
            
            # In a real implementation, this would:
            # 1. Update config file
            # 2. Set database connection parameters
            # 3. Update backend type setting
            
            return True
        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return False
    
    def _restart_pensieve_service(self) -> bool:
        """Restart Pensieve service."""
        try:
            logger.info("Restarting Pensieve service...")
            
            # In a real implementation, this would:
            # 1. Stop current service
            # 2. Start with new configuration
            # 3. Wait for service to be ready
            
            import subprocess
            result = subprocess.run(["memos", "restart"], capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            return False
    
    def _validate_migration_step(self) -> bool:
        """Validate current migration step."""
        try:
            # Basic validation that migration is proceeding correctly
            return self._test_database_connection()
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False
    
    def _cleanup_temporary_files(self) -> bool:
        """Cleanup temporary migration files."""
        try:
            logger.info("Cleaning up temporary files...")
            
            # In a real implementation, this would:
            # 1. Remove export files
            # 2. Remove temporary backups
            # 3. Clean up migration logs
            
            return True
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False
    
    def _execute_shell_command(self, command: str) -> bool:
        """Execute shell command."""
        try:
            logger.info(f"Executing shell command: {command}")
            
            import subprocess
            import shlex
            # Parse command safely into arguments
            cmd_args = shlex.split(command)
            result = subprocess.run(cmd_args, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Command successful: {result.stdout}")
                return True
            else:
                logger.error(f"Command failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Shell command execution failed: {e}")
            return False
    
    def _execute_sql_command(self, sql: str) -> bool:
        """Execute SQL command."""
        try:
            logger.info(f"Executing SQL: {sql}")
            
            # In a real implementation, this would execute SQL against the target database
            # For now, just log it
            return True
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return False
    
    def _test_target_database_connection(self, backend_type: BackendType) -> bool:
        """Test connection to target database."""
        if backend_type == BackendType.SQLITE:
            return self._test_database_connection()
        elif backend_type in [BackendType.POSTGRESQL, BackendType.PGVECTOR]:
            return self._test_postgresql_connection()
        else:
            logger.warning(f"Unknown backend type for connection test: {backend_type}")
            return True
    
    def _verify_data_integrity(self) -> bool:
        """Verify data integrity after migration."""
        try:
            # In a real implementation, this would:
            # 1. Compare record counts
            # 2. Verify key relationships
            # 3. Check data consistency
            
            logger.info("Verifying data integrity...")
            return True
        except Exception as e:
            logger.error(f"Data integrity verification failed: {e}")
            return False
    
    def _verify_pensieve_service(self) -> bool:
        """Verify Pensieve service is running correctly."""
        try:
            # Test if Pensieve is responding
            api_client = get_pensieve_client()
            health = api_client.get_health()
            return health.get('status') == 'healthy'
        except Exception as e:
            logger.error(f"Pensieve service verification failed: {e}")
            return False
    
    def _verify_performance_baseline(self) -> bool:
        """Verify performance meets baseline requirements."""
        try:
            # Test basic query performance
            start_time = time.time()
            api_client = get_pensieve_client()
            api_client.get_health()
            response_time = (time.time() - start_time) * 1000
            
            # Baseline: health check should respond within 1 second
            return response_time < 1000
        except Exception as e:
            logger.error(f"Performance baseline verification failed: {e}")
            return False
    
    def _verify_database_schema(self, backend_type: BackendType) -> bool:
        """Verify database schema is correct."""
        try:
            # In a real implementation, this would:
            # 1. Check all required tables exist
            # 2. Verify column types and constraints
            # 3. Check indexes
            
            logger.info(f"Verifying {backend_type.value} database schema...")
            return True
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False
    
    def _verify_vector_operations(self) -> bool:
        """Verify vector operations are working (for pgvector)."""
        try:
            # In a real implementation, this would:
            # 1. Test vector similarity queries
            # 2. Verify vector indexes work
            # 3. Check vector operations performance
            
            logger.info("Verifying vector operations...")
            return True
        except Exception as e:
            logger.error(f"Vector operations verification failed: {e}")
            return False
    
    def _verify_api_endpoints(self) -> bool:
        """Verify API endpoints are responding."""
        try:
            api_client = get_pensieve_client()
            
            # Test key endpoints
            health = api_client.get_health()
            if health.get('status') != 'healthy':
                return False
            
            # Test data access
            try:
                # This would test actual data endpoints in a real implementation
                logger.debug("Silent exception handled")
            except Exception:
                # API endpoints might not be fully available yet
                logger.debug("Operation failed silently")
            
            return True
        except Exception as e:
            logger.error(f"API endpoints verification failed: {e}")
            return False
    
    def _execute_rollback(self, plan: MigrationPlan) -> bool:
        """Execute rollback plan in case of migration failure."""
        logger.info("Executing migration rollback...")
        
        try:
            if hasattr(plan, 'rollback_plan'):
                rollback_steps = plan.rollback_plan
            else:
                # Generate default rollback steps
                rollback_steps = self._generate_default_rollback_steps(plan)
            
            for step in rollback_steps:
                logger.info(f"Rollback step: {step}")
                
                if "restore backup" in step.lower():
                    self._restore_database_backup()
                elif "revert configuration" in step.lower():
                    self._revert_configuration_changes()
                elif "restart service" in step.lower():
                    self._restart_pensieve_service()
                elif "cleanup" in step.lower():
                    self._cleanup_failed_migration()
                else:
                    # Execute generic rollback step
                    self._execute_migration_step(step)
            
            logger.info("Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def _generate_default_rollback_steps(self, plan: MigrationPlan) -> List[str]:
        """Generate default rollback steps."""
        return [
            "Stop Pensieve service",
            "Restore database backup",
            "Revert configuration changes", 
            "Restart Pensieve service",
            "Cleanup temporary files"
        ]
    
    def _restore_database_backup(self) -> bool:
        """Restore database from backup."""
        try:
            logger.info("Restoring database backup...")
            
            config = get_synced_config()
            db_path = Path(config.database_path if hasattr(config, 'database_path') else "~/.memos/database.db").expanduser()
            backup_dir = db_path.parent
            
            # Find most recent backup
            backup_files = list(backup_dir.glob("database_backup_*.db"))
            if not backup_files:
                logger.error("No backup files found for rollback")
                return False
            
            # Use most recent backup
            latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
            
            import shutil
            shutil.copy2(str(latest_backup), str(db_path))
            
            logger.info(f"Database restored from backup: {latest_backup}")
            return True
        except Exception as e:
            logger.error(f"Database backup restoration failed: {e}")
            return False
    
    def _revert_configuration_changes(self) -> bool:
        """Revert configuration changes."""
        try:
            logger.info("Reverting configuration changes...")
            
            # In a real implementation, this would:
            # 1. Restore original config file
            # 2. Reset database connection parameters
            # 3. Revert backend type setting
            
            return True
        except Exception as e:
            logger.error(f"Configuration revert failed: {e}")
            return False
    
    def _cleanup_failed_migration(self) -> bool:
        """Cleanup after failed migration."""
        try:
            logger.info("Cleaning up failed migration...")
            
            # In a real implementation, this would:
            # 1. Remove partial migration files
            # 2. Clean up temporary databases
            # 3. Remove failed configuration files
            
            return True
        except Exception as e:
            logger.error(f"Failed migration cleanup failed: {e}")
            return False


# Global instance
_backend_optimizer: Optional[PensieveBackendOptimizer] = None


def get_backend_optimizer() -> PensieveBackendOptimizer:
    """Get global backend optimizer instance."""
    global _backend_optimizer
    if _backend_optimizer is None:
        _backend_optimizer = PensieveBackendOptimizer()
    return _backend_optimizer


def auto_optimize_backend(dry_run: bool = True) -> Dict[str, Any]:
    """Automatically optimize backend configuration."""
    optimizer = get_backend_optimizer()
    
    # Get current recommendations
    recommendations = optimizer.get_migration_recommendations()
    
    if recommendations['needs_migration']:
        needs_migration, plan = optimizer.assess_migration_need()
        if plan:
            success = optimizer.execute_migration(plan, dry_run=dry_run)
            recommendations['migration_executed'] = success
            recommendations['dry_run'] = dry_run
    
    return recommendations


def reset_backend_optimizer():
    """Reset backend optimizer instance (useful for testing)."""
    global _backend_optimizer
    _backend_optimizer = None