"""Pensieve service health monitoring for AutoTaskTracker."""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from autotasktracker.pensieve.api_client import get_pensieve_client
from autotasktracker.pensieve.config_reader import get_pensieve_config_reader

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Pensieve service health status."""
    is_healthy: bool
    api_responding: bool
    service_running: bool
    database_accessible: bool
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    warnings: list = field(default_factory=list)


class PensieveHealthMonitor:
    """Monitors Pensieve service health and provides graceful degradation."""
    
    def __init__(self, check_interval: int = 30):
        """Initialize health monitor.
        
        Args:
            check_interval: Health check interval in seconds
        """
        self.check_interval = check_interval
        self._last_status: Optional[HealthStatus] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[HealthStatus], None]] = []
        self._lock = threading.Lock()
        
        # Health check configuration
        self.api_timeout = 5
        self.max_response_time = 2000  # 2 seconds in ms
        
    def add_health_callback(self, callback: Callable[[HealthStatus], None]):
        """Add callback to be called when health status changes.
        
        Args:
            callback: Function to call with HealthStatus
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_health_callback(self, callback: Callable[[HealthStatus], None]):
        """Remove health callback.
        
        Args:
            callback: Function to remove
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def check_health(self) -> HealthStatus:
        """Perform comprehensive health check of Pensieve service.
        
        Returns:
            HealthStatus object with current status
        """
        start_time = time.time()
        
        try:
            # Check service status via config reader
            config_reader = get_pensieve_config_reader()
            service_status = config_reader.get_memos_status()
            service_running = service_status.get("running", False)
            
            # Check API responsiveness
            api_responding = False
            api_response_time = 0
            api_error = None
            
            try:
                api_start = time.time()
                client = get_pensieve_client()
                api_responding = client.is_healthy()
                api_response_time = (time.time() - api_start) * 1000  # Convert to ms
            except Exception as e:
                api_error = str(e)
                api_response_time = (time.time() - start_time) * 1000
            
            # Check database accessibility
            database_accessible = False
            try:
                # Try to read Pensieve config which requires database access
                pensieve_config = config_reader.read_pensieve_config()
                database_accessible = bool(pensieve_config.database_path)
            except Exception as e:
                logger.debug(f"Database accessibility check failed: {e}")
            
            # Determine overall health
            is_healthy = service_running and api_responding and database_accessible
            
            # Collect warnings
            warnings = []
            if not service_running:
                warnings.append("Memos service is not running")
            if not api_responding:
                warnings.append("API is not responding")
            if not database_accessible:
                warnings.append("Database is not accessible")
            if api_response_time > self.max_response_time:
                warnings.append(f"API response time is high: {api_response_time:.1f}ms")
            
            # Create status object
            status = HealthStatus(
                is_healthy=is_healthy,
                api_responding=api_responding,
                service_running=service_running,
                database_accessible=database_accessible,
                last_check=datetime.now(),
                response_time_ms=api_response_time,
                error_message=api_error,
                warnings=warnings
            )
            
            # Update cached status
            with self._lock:
                self._last_status = status
            
            # Call callbacks if status changed
            self._notify_callbacks(status)
            
            return status
            
        except Exception as e:
            error_status = HealthStatus(
                is_healthy=False,
                api_responding=False,
                service_running=False,
                database_accessible=False,
                last_check=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
                warnings=[f"Health check failed: {e}"]
            )
            
            with self._lock:
                self._last_status = error_status
            
            self._notify_callbacks(error_status)
            return error_status
    
    def get_last_status(self) -> Optional[HealthStatus]:
        """Get last cached health status.
        
        Returns:
            Last HealthStatus or None if never checked
        """
        with self._lock:
            return self._last_status
    
    def is_healthy(self, max_age_seconds: int = 60) -> bool:
        """Check if service is healthy with optional cache check.
        
        Args:
            max_age_seconds: Maximum age of cached status to accept
            
        Returns:
            True if healthy, False otherwise
        """
        with self._lock:
            if self._last_status is None:
                # No cached status, perform fresh check
                return self.check_health().is_healthy
            
            # Check if cached status is too old
            age = (datetime.now() - self._last_status.last_check).total_seconds()
            if age > max_age_seconds:
                # Cached status too old, refresh
                return self.check_health().is_healthy
            
            return self._last_status.is_healthy
    
    def start_monitoring(self):
        """Start background health monitoring."""
        if self._monitoring:
            logger.warning("Health monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="PensieveHealthMonitor"
        )
        self._monitor_thread.start()
        logger.info(f"Started Pensieve health monitoring (interval: {self.check_interval}s)")
    
    def stop_monitoring(self):
        """Stop background health monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("Stopped Pensieve health monitoring")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                self.check_health()
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(self.check_interval):
                if not self._monitoring:
                    break
                time.sleep(1)
    
    def _notify_callbacks(self, status: HealthStatus):
        """Notify callbacks of health status change."""
        with self._lock:
            callbacks = self._callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.error(f"Health callback error: {e}")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary.
        
        Returns:
            Dictionary with health metrics and status
        """
        status = self.get_last_status()
        if not status:
            return {
                "status": "unknown",
                "message": "No health check performed yet",
                "last_check": None
            }
        
        return {
            "status": "healthy" if status.is_healthy else "unhealthy",
            "components": {
                "api": "up" if status.api_responding else "down",
                "service": "running" if status.service_running else "stopped",
                "database": "accessible" if status.database_accessible else "inaccessible"
            },
            "metrics": {
                "response_time_ms": status.response_time_ms,
                "last_check": status.last_check.isoformat(),
                "warnings_count": len(status.warnings)
            },
            "warnings": status.warnings,
            "error": status.error_message
        }


class HealthAwareMixin:
    """Mixin for classes that need Pensieve health awareness."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._health_monitor = PensieveHealthMonitor()
        self._health_monitor.start_monitoring()
        self._degraded_mode = False
    
    def _check_pensieve_health(self) -> bool:
        """Check if Pensieve is healthy and update degraded mode."""
        is_healthy = self._health_monitor.is_healthy()
        
        if not is_healthy and not self._degraded_mode:
            logger.warning("Pensieve unhealthy, entering degraded mode")
            self._degraded_mode = True
            self._on_pensieve_degraded()
        elif is_healthy and self._degraded_mode:
            logger.info("Pensieve healthy, exiting degraded mode")
            self._degraded_mode = False
            self._on_pensieve_recovered()
        
        return is_healthy
    
    def _on_pensieve_degraded(self):
        """Called when Pensieve becomes unhealthy. Override in subclasses."""
        pass
    
    def _on_pensieve_recovered(self):
        """Called when Pensieve recovers. Override in subclasses."""
        pass
    
    def is_pensieve_available(self) -> bool:
        """Check if Pensieve is currently available."""
        return not self._degraded_mode
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return self._health_monitor.get_health_summary()


# Global health monitor instance
_global_monitor: Optional[PensieveHealthMonitor] = None


def get_health_monitor() -> PensieveHealthMonitor:
    """Get global health monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PensieveHealthMonitor()
        _global_monitor.start_monitoring()
    return _global_monitor


def is_pensieve_healthy() -> bool:
    """Quick check if Pensieve is healthy."""
    return get_health_monitor().is_healthy()


def get_health_summary() -> Dict[str, Any]:
    """Get comprehensive health summary."""
    return get_health_monitor().get_health_summary()