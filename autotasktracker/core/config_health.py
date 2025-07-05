"""
Configuration Health Monitoring and Metrics for AutoTaskTracker.

This module provides comprehensive health monitoring for the configuration system,
including validation checks, performance metrics, and automated diagnostics.
"""

import os
import time
import logging
import psutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HealthMetric:
    """Individual health metric."""
    name: str
    value: Any
    status: str  # "healthy", "warning", "critical"
    message: str = ""
    timestamp: datetime = None
    threshold: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class HealthReport:
    """Comprehensive health report."""
    overall_status: str
    score: float  # 0-100
    total_checks: int
    passed_checks: int
    warnings: int
    critical_issues: int
    metrics: List[HealthMetric]
    timestamp: datetime = None
    duration_ms: float = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'overall_status': self.overall_status,
            'score': self.score,
            'total_checks': self.total_checks,
            'passed_checks': self.passed_checks,
            'warnings': self.warnings,
            'critical_issues': self.critical_issues,
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': self.duration_ms,
            'metrics': [asdict(metric) for metric in self.metrics]
        }


class ConfigHealthMonitor:
    """Comprehensive configuration health monitoring."""
    
    def __init__(self):
        self._last_report: Optional[HealthReport] = None
        self._check_interval = timedelta(minutes=5)
        self._metrics_history: List[HealthReport] = []
        self._max_history = 100
    
    def run_health_check(self) -> HealthReport:
        """Run comprehensive configuration health check."""
        start_time = time.time()
        metrics = []
        
        try:
            # Configuration loading checks
            metrics.extend(self._check_config_loading())
            
            # Validation checks
            metrics.extend(self._check_config_validation())
            
            # File system checks
            metrics.extend(self._check_file_system())
            
            # Port availability checks
            metrics.extend(self._check_port_availability())
            
            # Pensieve integration checks
            metrics.extend(self._check_pensieve_integration())
            
            # Performance checks
            metrics.extend(self._check_performance())
            
            # Environment checks
            metrics.extend(self._check_environment())
            
            # Security checks
            metrics.extend(self._check_security())
            
            # Calculate overall health
            duration_ms = (time.time() - start_time) * 1000
            report = self._calculate_overall_health(metrics, duration_ms)
            
            # Store in history
            self._last_report = report
            self._metrics_history.append(report)
            if len(self._metrics_history) > self._max_history:
                self._metrics_history.pop(0)
            
            logger.info(f"Configuration health check completed: {report.overall_status} (score: {report.score:.1f})")
            return report
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthReport(
                overall_status="critical",
                score=0.0,
                total_checks=1,
                passed_checks=0,
                warnings=0,
                critical_issues=1,
                metrics=[HealthMetric("health_check", False, "critical", f"Health check failed: {e}")],
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def _check_config_loading(self) -> List[HealthMetric]:
        """Check configuration loading functionality."""
        metrics = []
        
        try:
            from autotasktracker.config import get_config
            
            # Test basic config loading
            start_time = time.time()
            config = get_config()
            load_time = (time.time() - start_time) * 1000
            
            metrics.append(HealthMetric(
                "config_loading",
                True,
                "healthy",
                f"Configuration loaded successfully in {load_time:.1f}ms"
            ))
            
            # Check config type
            if hasattr(config, 'database'):
                metrics.append(HealthMetric(
                    "unified_config_available",
                    True,
                    "healthy",
                    "Unified configuration system active"
                ))
            else:
                metrics.append(HealthMetric(
                    "unified_config_available",
                    False,
                    "warning",
                    "Using fallback Pydantic configuration"
                ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "config_loading",
                False,
                "critical",
                f"Configuration loading failed: {e}"
            ))
        
        return metrics
    
    def _check_config_validation(self) -> List[HealthMetric]:
        """Check configuration validation."""
        metrics = []
        
        try:
            from autotasktracker.config import validate_current_config
            
            validation = validate_current_config()
            
            if validation.get('validation_passed', False):
                metrics.append(HealthMetric(
                    "config_validation",
                    True,
                    "healthy",
                    "Configuration validation passed"
                ))
            else:
                error = validation.get('error', 'Unknown validation error')
                metrics.append(HealthMetric(
                    "config_validation",
                    False,
                    "critical",
                    f"Configuration validation failed: {error}"
                ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "config_validation",
                False,
                "critical",
                f"Validation check failed: {e}"
            ))
        
        return metrics
    
    def _check_file_system(self) -> List[HealthMetric]:
        """Check file system accessibility."""
        metrics = []
        
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            # Check database path
            if hasattr(config, 'database'):
                db_path = Path(config.database.path)
            else:
                db_path = Path(config.DB_PATH)
            
            # Check database directory
            db_dir = db_path.parent
            if db_dir.exists():
                metrics.append(HealthMetric(
                    "database_directory",
                    True,
                    "healthy",
                    f"Database directory accessible: {db_dir}"
                ))
                
                # Check write permissions
                try:
                    test_file = db_dir / ".config_health_test"
                    test_file.touch()
                    test_file.unlink()
                    metrics.append(HealthMetric(
                        "database_write_permission",
                        True,
                        "healthy",
                        "Database directory is writable"
                    ))
                except Exception as e:
                    metrics.append(HealthMetric(
                        "database_write_permission",
                        False,
                        "critical",
                        f"Database directory not writable: {e}"
                    ))
            else:
                metrics.append(HealthMetric(
                    "database_directory",
                    False,
                    "critical",
                    f"Database directory does not exist: {db_dir}"
                ))
            
            # Check database file if it exists
            if db_path.exists():
                file_size = db_path.stat().st_size
                metrics.append(HealthMetric(
                    "database_file",
                    True,
                    "healthy",
                    f"Database file exists ({file_size / 1024 / 1024:.1f}MB)"
                ))
            else:
                metrics.append(HealthMetric(
                    "database_file",
                    False,
                    "warning",
                    "Database file does not exist (will be created)"
                ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "file_system",
                False,
                "critical",
                f"File system check failed: {e}"
            ))
        
        return metrics
    
    def _check_port_availability(self) -> List[HealthMetric]:
        """Check port availability for services."""
        metrics = []
        
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            # Get ports
            if hasattr(config, 'server'):
                ports = {
                    'memos': config.server.memos_port,
                    'task_board': config.server.task_board_port,
                    'analytics': config.server.analytics_port,
                    'timetracker': config.server.timetracker_port
                }
            else:
                ports = {
                    'memos': config.MEMOS_PORT,
                    'task_board': config.TASK_BOARD_PORT,
                    'analytics': config.ANALYTICS_PORT,
                    'timetracker': config.TIMETRACKER_PORT
                }
            
            # Check each port
            for service, port in ports.items():
                is_available = self._is_port_available(port)
                
                metrics.append(HealthMetric(
                    f"port_{service}",
                    is_available,
                    "healthy" if is_available else "warning",
                    f"Port {port} {'available' if is_available else 'in use'}"
                ))
            
            # Check for port conflicts
            unique_ports = set(ports.values())
            if len(unique_ports) == len(ports):
                metrics.append(HealthMetric(
                    "port_conflicts",
                    False,
                    "healthy",
                    "No port conflicts detected"
                ))
            else:
                metrics.append(HealthMetric(
                    "port_conflicts",
                    True,
                    "critical",
                    "Port conflicts detected in configuration"
                ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "port_availability",
                False,
                "critical",
                f"Port availability check failed: {e}"
            ))
        
        return metrics
    
    def _check_pensieve_integration(self) -> List[HealthMetric]:
        """Check Pensieve integration health."""
        metrics = []
        
        try:
            from autotasktracker.pensieve.api_client import get_pensieve_client
            
            client = get_pensieve_client()
            if client:
                # Test API health
                is_healthy = client.is_healthy()
                metrics.append(HealthMetric(
                    "pensieve_api",
                    is_healthy,
                    "healthy" if is_healthy else "warning",
                    f"Pensieve API {'healthy' if is_healthy else 'unavailable'}"
                ))
                
                if is_healthy:
                    # Test endpoint discovery
                    try:
                        endpoints = client.discover_endpoints()
                        metrics.append(HealthMetric(
                            "pensieve_endpoints",
                            len(endpoints),
                            "healthy",
                            f"Discovered {len(endpoints)} Pensieve endpoints"
                        ))
                    except Exception as e:
                        metrics.append(HealthMetric(
                            "pensieve_endpoints",
                            0,
                            "warning",
                            f"Endpoint discovery failed: {e}"
                        ))
            else:
                metrics.append(HealthMetric(
                    "pensieve_api",
                    False,
                    "warning",
                    "Pensieve client not available"
                ))
                
        except Exception as e:
            metrics.append(HealthMetric(
                "pensieve_integration",
                False,
                "warning",
                f"Pensieve integration check failed: {e}"
            ))
        
        return metrics
    
    def _check_performance(self) -> List[HealthMetric]:
        """Check system performance metrics."""
        metrics = []
        
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent < 80:
                status = "healthy"
            elif memory_percent < 90:
                status = "warning"
            else:
                status = "critical"
            
            metrics.append(HealthMetric(
                "memory_usage",
                memory_percent,
                status,
                f"Memory usage: {memory_percent:.1f}%",
                threshold=80.0
            ))
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent < 70:
                status = "healthy"
            elif cpu_percent < 85:
                status = "warning"
            else:
                status = "critical"
            
            metrics.append(HealthMetric(
                "cpu_usage",
                cpu_percent,
                status,
                f"CPU usage: {cpu_percent:.1f}%",
                threshold=70.0
            ))
            
            # Disk usage for database directory
            from autotasktracker.config import get_config
            config = get_config()
            
            if hasattr(config, 'database'):
                db_path = Path(config.database.path)
            else:
                db_path = Path(config.DB_PATH)
            
            disk_usage = psutil.disk_usage(str(db_path.parent))
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            if disk_percent < 80:
                status = "healthy"
            elif disk_percent < 90:
                status = "warning"
            else:
                status = "critical"
            
            metrics.append(HealthMetric(
                "disk_usage",
                disk_percent,
                status,
                f"Disk usage: {disk_percent:.1f}%",
                threshold=80.0
            ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "performance",
                False,
                "warning",
                f"Performance check failed: {e}"
            ))
        
        return metrics
    
    def _check_environment(self) -> List[HealthMetric]:
        """Check environment configuration."""
        metrics = []
        
        try:
            # Check for AutoTaskTracker environment variables
            autotask_vars = {k: v for k, v in os.environ.items() if k.startswith('AUTOTASK_')}
            
            metrics.append(HealthMetric(
                "environment_variables",
                len(autotask_vars),
                "healthy" if autotask_vars else "warning",
                f"Found {len(autotask_vars)} AutoTaskTracker environment variables"
            ))
            
            # Check Python version
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            
            if sys.version_info >= (3, 8):
                metrics.append(HealthMetric(
                    "python_version",
                    python_version,
                    "healthy",
                    f"Python version: {python_version}"
                ))
            else:
                metrics.append(HealthMetric(
                    "python_version",
                    python_version,
                    "warning",
                    f"Python version {python_version} may not be fully supported"
                ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "environment",
                False,
                "warning",
                f"Environment check failed: {e}"
            ))
        
        return metrics
    
    def _check_security(self) -> List[HealthMetric]:
        """Check security-related configuration."""
        metrics = []
        
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            # Check database path security
            if hasattr(config, 'database'):
                db_path = config.database.path
            else:
                db_path = config.DB_PATH
            
            dangerous_patterns = ['/etc/', '/bin/', '/usr/bin/', '/sbin/', '/var/log/']
            is_secure = not any(pattern in db_path.lower() for pattern in dangerous_patterns)
            
            metrics.append(HealthMetric(
                "database_path_security",
                is_secure,
                "healthy" if is_secure else "critical",
                f"Database path {'secure' if is_secure else 'in dangerous location'}: {db_path}"
            ))
            
            # Check file permissions
            db_path_obj = Path(db_path)
            if db_path_obj.parent.exists():
                permissions = oct(db_path_obj.parent.stat().st_mode)[-3:]
                is_secure_perms = permissions in ['755', '750', '700']
                
                metrics.append(HealthMetric(
                    "directory_permissions",
                    is_secure_perms,
                    "healthy" if is_secure_perms else "warning",
                    f"Database directory permissions: {permissions}"
                ))
            
        except Exception as e:
            metrics.append(HealthMetric(
                "security",
                False,
                "warning",
                f"Security check failed: {e}"
            ))
        
        return metrics
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return False
    
    def _calculate_overall_health(self, metrics: List[HealthMetric], duration_ms: float) -> HealthReport:
        """Calculate overall health status from metrics."""
        total_checks = len(metrics)
        passed_checks = len([m for m in metrics if m.status == "healthy"])
        warnings = len([m for m in metrics if m.status == "warning"])
        critical_issues = len([m for m in metrics if m.status == "critical"])
        
        # Calculate score (0-100)
        if total_checks == 0:
            score = 0.0
        else:
            score = (passed_checks / total_checks) * 100
            # Reduce score for warnings and critical issues
            score -= (warnings * 5)  # 5 points per warning
            score -= (critical_issues * 20)  # 20 points per critical issue
            score = max(0, score)
        
        # Determine overall status
        if critical_issues > 0:
            overall_status = "critical"
        elif warnings > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return HealthReport(
            overall_status=overall_status,
            score=score,
            total_checks=total_checks,
            passed_checks=passed_checks,
            warnings=warnings,
            critical_issues=critical_issues,
            metrics=metrics,
            duration_ms=duration_ms
        )
    
    def get_metrics_history(self, hours: int = 24) -> List[HealthReport]:
        """Get metrics history for the specified time period."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [report for report in self._metrics_history if report.timestamp >= cutoff]
    
    def get_latest_report(self) -> Optional[HealthReport]:
        """Get the latest health report."""
        return self._last_report
    
    def export_health_metrics(self) -> Dict[str, Any]:
        """Export health metrics for external monitoring."""
        if not self._last_report:
            return {}
        
        return {
            'autotasktracker_config_health_score': self._last_report.score,
            'autotasktracker_config_total_checks': self._last_report.total_checks,
            'autotasktracker_config_passed_checks': self._last_report.passed_checks,
            'autotasktracker_config_warnings': self._last_report.warnings,
            'autotasktracker_config_critical_issues': self._last_report.critical_issues,
            'autotasktracker_config_check_duration_ms': self._last_report.duration_ms,
            'autotasktracker_config_last_check': self._last_report.timestamp.isoformat()
        }


# Global health monitor instance
_config_health_monitor = None

def get_config_health_monitor() -> ConfigHealthMonitor:
    """Get the global configuration health monitor."""
    global _config_health_monitor
    if _config_health_monitor is None:
        _config_health_monitor = ConfigHealthMonitor()
    return _config_health_monitor

def run_config_health_check() -> HealthReport:
    """Run a configuration health check."""
    monitor = get_config_health_monitor()
    return monitor.run_health_check()

def get_config_health_status() -> Dict[str, Any]:
    """Get current configuration health status."""
    monitor = get_config_health_monitor()
    report = monitor.get_latest_report()
    
    if report:
        return report.to_dict()
    else:
        # Run health check if none exists
        report = monitor.run_health_check()
        return report.to_dict()