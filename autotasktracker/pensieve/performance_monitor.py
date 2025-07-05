"""
Performance monitoring system for Pensieve integration.
Tracks cache hit rates, search response times, and system metrics.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricEntry:
    """Represents a single metric measurement."""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    total_requests: int = 0
    errors_per_minute: float = 0.0
    database_query_time_ms: float = 0.0
    search_response_time_ms: float = 0.0
    websocket_connections: int = 0
    memory_usage_mb: float = 0.0
    last_updated: float = field(default_factory=time.time)


class PerformanceMonitor:
    """Monitors and tracks performance metrics for Pensieve integration."""
    
    def __init__(self, retention_hours: int = 24, max_samples: int = 10000):
        """Initialize performance monitor.
        
        Args:
            retention_hours: How long to keep metrics data
            max_samples: Maximum number of samples to keep per metric
        """
        self.retention_hours = retention_hours
        self.max_samples = max_samples
        
        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, float] = {}
        
        # Threading protection
        self._lock = threading.RLock()
        
        # Background cleanup
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
        
        logger.info(f"Performance monitor initialized (retention: {retention_hours}h, max_samples: {max_samples})")
    
    def record_metric(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            metadata: Optional metadata about the measurement
        """
        with self._lock:
            entry = MetricEntry(
                timestamp=time.time(),
                value=value,
                metadata=metadata or {}
            )
            
            self.metrics[metric_name].append(entry)
            logger.debug(f"Recorded metric {metric_name}: {value}")
            
            # Cleanup old metrics if needed
            self._cleanup_old_metrics_if_needed()
    
    def start_timer(self, timer_name: str):
        """Start a named timer for measuring duration.
        
        Args:
            timer_name: Name of the timer
        """
        with self._lock:
            self.timers[timer_name] = time.time()
    
    def end_timer(self, timer_name: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """End a named timer and record the duration.
        
        Args:
            timer_name: Name of the timer
            metadata: Optional metadata
            
        Returns:
            Duration in milliseconds
        """
        with self._lock:
            if timer_name not in self.timers:
                logger.warning(f"Timer {timer_name} was not started")
                return 0.0
            
            start_time = self.timers.pop(timer_name)
            duration_ms = (time.time() - start_time) * 1000
            
            self.record_metric(f"{timer_name}_duration_ms", duration_ms, metadata)
            return duration_ms
    
    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a counter metric.
        
        Args:
            counter_name: Name of the counter
            amount: Amount to increment by
        """
        with self._lock:
            self.counters[counter_name] += amount
            logger.debug(f"Incremented counter {counter_name} by {amount}")
    
    def record_cache_hit(self, cache_type: str = "default"):
        """Record a cache hit."""
        self.increment_counter(f"cache_hit_{cache_type}")
        self.record_metric("cache_operation", 1.0, {"type": cache_type, "result": "hit"})
    
    def record_cache_miss(self, cache_type: str = "default"):
        """Record a cache miss."""
        self.increment_counter(f"cache_miss_{cache_type}")
        self.record_metric("cache_operation", 0.0, {"type": cache_type, "result": "miss"})
    
    def record_database_query(self, duration_ms: float, query_type: str = "unknown"):
        """Record database query performance.
        
        Args:
            duration_ms: Query duration in milliseconds
            query_type: Type of query (select, insert, update, etc.)
        """
        self.record_metric("database_query_ms", duration_ms, {"query_type": query_type})
        self.increment_counter("database_queries_total")
    
    def record_search_operation(self, duration_ms: float, result_count: int, search_type: str = "embeddings"):
        """Record search operation performance.
        
        Args:
            duration_ms: Search duration in milliseconds
            result_count: Number of results returned
            search_type: Type of search (embeddings, text, etc.)
        """
        self.record_metric("search_duration_ms", duration_ms, {
            "search_type": search_type,
            "result_count": result_count
        })
        self.increment_counter("search_operations_total")
    
    def record_websocket_connection(self, connected: bool):
        """Record WebSocket connection state change.
        
        Args:
            connected: True if connected, False if disconnected
        """
        if connected:
            self.increment_counter("websocket_connections")
        else:
            self.increment_counter("websocket_disconnections")
        
        self.record_metric("websocket_connection", 1.0 if connected else 0.0)
    
    def record_error(self, error_type: str, context: str = ""):
        """Record an error occurrence.
        
        Args:
            error_type: Type of error
            context: Additional context about the error
        """
        self.increment_counter(f"error_{error_type}")
        self.record_metric("error_occurrence", 1.0, {
            "error_type": error_type,
            "context": context
        })
    
    def get_cache_metrics(self, cache_type: str = "default") -> Dict[str, float]:
        """Get cache performance metrics.
        
        Args:
            cache_type: Type of cache to get metrics for
            
        Returns:
            Dictionary of cache metrics
        """
        with self._lock:
            hits = self.counters.get(f"cache_hit_{cache_type}", 0)
            misses = self.counters.get(f"cache_miss_{cache_type}", 0)
            total = hits + misses
            
            if total == 0:
                return {
                    "hit_rate": 0.0,
                    "miss_rate": 0.0,
                    "total_operations": 0,
                    "hits": 0,
                    "misses": 0
                }
            
            hit_rate = (hits / total) * 100
            miss_rate = (misses / total) * 100
            
            return {
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "total_operations": total,
                "hits": hits,
                "misses": misses
            }
    
    def get_response_time_metrics(self, metric_name: str) -> Dict[str, float]:
        """Get response time statistics for a metric.
        
        Args:
            metric_name: Name of the timing metric
            
        Returns:
            Dictionary of timing statistics
        """
        with self._lock:
            if metric_name not in self.metrics:
                return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}
            
            values = [entry.value for entry in self.metrics[metric_name]]
            
            if not values:
                return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}
            
            sorted_values = sorted(values)
            count = len(sorted_values)
            
            return {
                "avg": statistics.mean(values),
                "p50": sorted_values[int(count * 0.5)] if count > 0 else 0.0,
                "p95": sorted_values[int(count * 0.95)] if count > 0 else 0.0,
                "p99": sorted_values[int(count * 0.99)] if count > 0 else 0.0,
                "min": min(values),
                "max": max(values)
            }
    
    def get_comprehensive_metrics(self) -> PerformanceMetrics:
        """Get comprehensive performance metrics.
        
        Returns:
            PerformanceMetrics object with current statistics
        """
        with self._lock:
            # Cache metrics
            cache_metrics = self.get_cache_metrics()
            
            # Response time metrics
            db_metrics = self.get_response_time_metrics("database_query_ms")
            search_metrics = self.get_response_time_metrics("search_duration_ms")
            
            # General response times (if available)
            response_metrics = self.get_response_time_metrics("response_time_ms")
            
            # Error rate (errors per minute in last hour)
            error_rate = self._calculate_error_rate()
            
            # WebSocket connections
            ws_connections = self.counters.get("websocket_connections", 0) - self.counters.get("websocket_disconnections", 0)
            
            return PerformanceMetrics(
                cache_hit_rate=cache_metrics["hit_rate"],
                cache_miss_rate=cache_metrics["miss_rate"],
                avg_response_time_ms=response_metrics["avg"],
                p95_response_time_ms=response_metrics["p95"],
                p99_response_time_ms=response_metrics["p99"],
                total_requests=self.counters.get("total_requests", cache_metrics["total_operations"]),
                errors_per_minute=error_rate,
                database_query_time_ms=db_metrics["avg"],
                search_response_time_ms=search_metrics["avg"],
                websocket_connections=max(0, ws_connections),
                memory_usage_mb=self._get_memory_usage(),
                last_updated=time.time()
            )
    
    def get_metric_history(self, metric_name: str, hours: int = 1) -> List[Tuple[float, float]]:
        """Get historical data for a metric.
        
        Args:
            metric_name: Name of the metric
            hours: Number of hours of history to return
            
        Returns:
            List of (timestamp, value) tuples
        """
        with self._lock:
            if metric_name not in self.metrics:
                return []
            
            cutoff_time = time.time() - (hours * 3600)
            
            history = []
            for entry in self.metrics[metric_name]:
                if entry.timestamp >= cutoff_time:
                    history.append((entry.timestamp, entry.value))
            
            return sorted(history, key=lambda x: x[0])
    
    def _calculate_error_rate(self) -> float:
        """Calculate errors per minute in the last hour."""
        error_entries = []
        cutoff_time = time.time() - 3600  # Last hour
        
        for metric_name in self.metrics:
            if metric_name == "error_occurrence":
                for entry in self.metrics[metric_name]:
                    if entry.timestamp >= cutoff_time and entry.value > 0:
                        error_entries.append(entry.timestamp)
        
        if not error_entries:
            return 0.0
        
        # Calculate errors per minute
        time_span_minutes = (time.time() - min(error_entries)) / 60
        return len(error_entries) / max(time_span_minutes, 1.0)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _cleanup_old_metrics_if_needed(self):
        """Clean up old metrics if cleanup interval has passed."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = current_time - (self.retention_hours * 3600)
        
        for metric_name in list(self.metrics.keys()):
            metric_deque = self.metrics[metric_name]
            
            # Remove old entries
            while metric_deque and metric_deque[0].timestamp < cutoff_time:
                metric_deque.popleft()
            
            # Remove empty metrics
            if not metric_deque:
                del self.metrics[metric_name]
        
        self._last_cleanup = current_time
        logger.debug(f"Cleaned up metrics older than {self.retention_hours} hours")
    
    def export_metrics(self, filepath: Optional[Path] = None) -> Dict[str, Any]:
        """Export metrics to JSON format.
        
        Args:
            filepath: Optional path to save metrics to
            
        Returns:
            Dictionary of exported metrics
        """
        with self._lock:
            export_data = {
                "timestamp": time.time(),
                "comprehensive_metrics": self.get_comprehensive_metrics().__dict__,
                "counters": dict(self.counters),
                "cache_metrics": self.get_cache_metrics(),
                "response_time_metrics": {
                    "database": self.get_response_time_metrics("database_query_ms"),
                    "search": self.get_response_time_metrics("search_duration_ms"),
                    "general": self.get_response_time_metrics("response_time_ms")
                }
            }
            
            if filepath:
                filepath = Path(filepath)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                logger.info(f"Metrics exported to {filepath}")
            
            return export_data
    
    def reset_metrics(self):
        """Reset all metrics and counters."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.timers.clear()
            logger.info("All metrics reset")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def reset_performance_monitor():
    """Reset global performance monitor."""
    global _performance_monitor
    _performance_monitor = None


# Convenience functions
def record_cache_hit(cache_type: str = "default"):
    """Record a cache hit."""
    get_performance_monitor().record_cache_hit(cache_type)


def record_cache_miss(cache_type: str = "default"):
    """Record a cache miss."""
    get_performance_monitor().record_cache_miss(cache_type)


def record_database_query(duration_ms: float, query_type: str = "unknown"):
    """Record database query performance."""
    get_performance_monitor().record_database_query(duration_ms, query_type)


def record_search_operation(duration_ms: float, result_count: int, search_type: str = "embeddings"):
    """Record search operation performance."""
    get_performance_monitor().record_search_operation(duration_ms, result_count, search_type)


def start_timer(timer_name: str):
    """Start a named timer."""
    get_performance_monitor().start_timer(timer_name)


def end_timer(timer_name: str, metadata: Optional[Dict[str, Any]] = None) -> float:
    """End a named timer and return duration in ms."""
    return get_performance_monitor().end_timer(timer_name, metadata)


def get_performance_metrics() -> PerformanceMetrics:
    """Get comprehensive performance metrics."""
    return get_performance_monitor().get_comprehensive_metrics()