"""
Comprehensive error handling and logging for VLM processing.
"""
import logging
import traceback
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from collections import defaultdict, deque
import threading


class VLMErrorHandler:
    """Centralized error handling for VLM operations."""
    
    def __init__(self, max_error_history: int = 1000):
        self.max_error_history = max_error_history
        self.error_history = deque(maxlen=max_error_history)
        self.error_counts = defaultdict(int)
        self.error_lock = threading.Lock()
        
        # Setup dedicated logger
        self.logger = logging.getLogger('vlm_errors')
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup dedicated logging for VLM errors."""
        if not self.logger.handlers:
            # Create file handler for VLM errors
            from pathlib import Path
            log_dir = Path.home() / '.memos' / 'logs'
            log_dir.mkdir(exist_ok=True)
            
            handler = logging.FileHandler(log_dir / 'vlm_errors.log')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.ERROR)
    
    def record_error(self, error: Exception, context: Dict[str, Any]):
        """Record an error with context information."""
        with self.error_lock:
            error_record = {
                'timestamp': datetime.now(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context,
                'traceback': traceback.format_exc()
            }
            
            self.error_history.append(error_record)
            self.error_counts[type(error).__name__] += 1
            
            # Log the error
            self.logger.error(f"{error_record['error_type']}: {error_record['error_message']}")
            self.logger.error(f"Context: {context}")
            self.logger.error(f"Traceback: {error_record['traceback']}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        with self.error_lock:
            recent_errors = [
                e for e in self.error_history 
                if e['timestamp'] > datetime.now() - timedelta(hours=1)
            ]
            
            return {
                'total_errors': len(self.error_history),
                'recent_errors_1h': len(recent_errors),
                'error_types': dict(self.error_counts),
                'most_common_error': max(self.error_counts.items(), key=lambda x: x[1])[0] if self.error_counts else None,
                'recent_error_rate': len(recent_errors) / 60,  # errors per minute
            }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent errors for debugging."""
        with self.error_lock:
            return list(self.error_history)[-limit:]


# Global error handler instance
_error_handler = VLMErrorHandler()


def vlm_error_handler(context: Optional[Dict[str, Any]] = None):
    """Decorator for VLM functions to handle errors consistently."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    'function': func.__name__,
                    'args': str(args)[:200],  # Truncate long args
                    'kwargs': str(kwargs)[:200],
                    **(context or {})
                }
                _error_handler.record_error(e, error_context)
                raise
        return wrapper
    return decorator


class VLMMetrics:
    """Performance and reliability metrics for VLM operations."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.lock = threading.Lock()
    
    def record_latency(self, operation: str, latency_ms: float):
        """Record operation latency."""
        with self.lock:
            self.metrics[f"{operation}_latency"].append({
                'timestamp': time.time(),
                'value': latency_ms
            })
            # Keep only last 1000 measurements
            if len(self.metrics[f"{operation}_latency"]) > 1000:
                self.metrics[f"{operation}_latency"] = self.metrics[f"{operation}_latency"][-1000:]
    
    def increment_counter(self, metric: str):
        """Increment a counter metric."""
        with self.lock:
            self.counters[metric] += 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        with self.lock:
            summary = {'counters': dict(self.counters)}
            
            # Calculate latency statistics
            for metric_name, measurements in self.metrics.items():
                if measurements:
                    recent = [m['value'] for m in measurements[-100:]]  # Last 100 measurements
                    summary[metric_name] = {
                        'count': len(measurements),
                        'avg': sum(recent) / len(recent),
                        'min': min(recent),
                        'max': max(recent),
                        'p95': sorted(recent)[int(len(recent) * 0.95)] if len(recent) > 20 else max(recent)
                    }
            
            return summary


# Global metrics instance
_metrics = VLMMetrics()


def measure_latency(operation: str):
    """Decorator to measure operation latency."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                _metrics.increment_counter(f"{operation}_success")
                return result
            except Exception as e:
                _metrics.increment_counter(f"{operation}_error")
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                _metrics.record_latency(operation, latency_ms)
        return wrapper
    return decorator


class HealthMonitor:
    """Monitor VLM system health and generate alerts."""
    
    def __init__(self):
        self.health_checks = {}
        self.alerts = deque(maxlen=100)
        self.lock = threading.Lock()
    
    def register_health_check(self, name: str, check_func: Callable[[], bool], 
                            alert_threshold: int = 3):
        """Register a health check function."""
        self.health_checks[name] = {
            'func': check_func,
            'failures': 0,
            'alert_threshold': alert_threshold,
            'last_check': None,
            'status': 'unknown'
        }
    
    def run_health_checks(self) -> Dict[str, str]:
        """Run all health checks and return status."""
        with self.lock:
            results = {}
            
            for name, check in self.health_checks.items():
                try:
                    is_healthy = check['func']()
                    check['last_check'] = datetime.now()
                    
                    if is_healthy:
                        check['failures'] = 0
                        check['status'] = 'healthy'
                    else:
                        check['failures'] += 1
                        check['status'] = 'unhealthy'
                        
                        # Generate alert if threshold exceeded
                        if check['failures'] >= check['alert_threshold']:
                            self._generate_alert(name, f"Health check failed {check['failures']} times")
                    
                    results[name] = check['status']
                    
                except Exception as e:
                    check['failures'] += 1
                    check['status'] = 'error'
                    check['last_check'] = datetime.now()
                    results[name] = f"error: {str(e)}"
                    
                    self._generate_alert(name, f"Health check error: {str(e)}")
            
            return results
    
    def _generate_alert(self, source: str, message: str):
        """Generate a system alert."""
        alert = {
            'timestamp': datetime.now(),
            'source': source,
            'message': message,
            'severity': 'warning'
        }
        self.alerts.append(alert)
        
        # Log the alert
        logging.getLogger('vlm_health').warning(f"ALERT [{source}]: {message}")
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        with self.lock:
            return list(self.alerts)[-limit:]


# Global health monitor
_health_monitor = HealthMonitor()


def get_error_handler() -> VLMErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


def get_metrics() -> VLMMetrics:
    """Get the global metrics instance."""
    return _metrics


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    return _health_monitor


# Setup default health checks
def _check_ollama_available():
    """Check if Ollama service is available."""
    import requests
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def _check_database_available():
    """Check if database is available."""
    try:
        from autotasktracker.core.database import DatabaseManager
        db = DatabaseManager()
        return db.test_connection()
    except (requests.RequestException, ImportError):
        return False


def _check_memory_usage():
    """Check if memory usage is reasonable."""
    try:
        import psutil
        memory_percent = psutil.virtual_memory().percent
        return memory_percent < 90  # Alert if memory usage > 90%
    except ImportError:
        return True  # If we can't check, assume it's fine


# Register default health checks
_health_monitor.register_health_check('ollama', _check_ollama_available, alert_threshold=3)
_health_monitor.register_health_check('database', _check_database_available, alert_threshold=2)
_health_monitor.register_health_check('memory', _check_memory_usage, alert_threshold=5)