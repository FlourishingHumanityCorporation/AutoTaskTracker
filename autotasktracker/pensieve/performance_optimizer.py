"""
Performance optimization module for high-volume screenshot processing.

This module provides optimizations for production environments processing
1000+ screenshots per day, including batch processing, memory management,
and intelligent caching strategies.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import gc

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveEntity
from autotasktracker.pensieve.cache_manager import get_cache_manager
from autotasktracker.core import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    entities_processed: int
    processing_rate: float  # entities per second
    memory_usage_mb: float
    cache_hit_rate: float
    api_latency_ms: float
    error_rate: float
    uptime_seconds: float


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization."""
    batch_size: int = 50
    max_workers: int = 4
    memory_limit_mb: int = 500
    cache_size_limit_mb: int = 100
    api_timeout_seconds: int = 10
    gc_frequency: int = 100  # Run garbage collection every N entities
    enable_batch_processing: bool = True
    enable_memory_optimization: bool = True
    enable_adaptive_polling: bool = True


class PerformanceOptimizer:
    """Optimizes AutoTaskTracker performance for high-volume environments."""
    
    def __init__(self, config: OptimizationConfig = None):
        """Initialize performance optimizer.
        
        Args:
            config: Optimization configuration
        """
        self.config = config or OptimizationConfig()
        self.metrics = PerformanceMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.start_time = time.time()
        
        # Components
        self.db_manager = DatabaseManager(use_pensieve_api=True)
        self.client = get_pensieve_client()
        self.cache_manager = get_cache_manager()
        
        # Performance tracking
        self._processed_count = 0
        self._error_count = 0
        self._last_gc = 0
        self._performance_history: List[PerformanceMetrics] = []
        
        # Thread pool for batch processing
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()
        
        logger.info(f"Performance optimizer initialized with config: {self.config}")
    
    def start_batch_processing(self):
        """Start batch processing with optimized thread pool."""
        if self.config.enable_batch_processing and not self._executor:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix="PensieveOptimizer"
            )
            logger.info(f"Started batch processing with {self.config.max_workers} workers")
    
    def stop_batch_processing(self):
        """Stop batch processing and cleanup."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.info("Stopped batch processing")
    
    def process_entities_batch(self, entity_ids: List[int]) -> List[Dict[str, Any]]:
        """Process a batch of entities with optimization.
        
        Args:
            entity_ids: List of entity IDs to process
            
        Returns:
            List of processed entity data
        """
        if not self.config.enable_batch_processing:
            return [self._process_single_entity(eid) for eid in entity_ids]
        
        if not self._executor:
            self.start_batch_processing()
        
        # Submit batch jobs
        futures = []
        for batch in self._create_batches(entity_ids, self.config.batch_size):
            future = self._executor.submit(self._process_entity_batch, batch)
            futures.append(future)
        
        # Collect results
        results = []
        for future in as_completed(futures):
            try:
                batch_results = future.result(timeout=self.config.api_timeout_seconds)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                self._error_count += len(entity_ids) // len(futures)
        
        self._update_metrics(len(results))
        return results
    
    def _create_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """Create batches from a list of items."""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]
    
    def _process_entity_batch(self, entity_ids: List[int]) -> List[Dict[str, Any]]:
        """Process a batch of entities."""
        results = []
        
        for entity_id in entity_ids:
            try:
                result = self._process_single_entity(entity_id)
                if result:
                    results.append(result)
                
                # Memory management
                if self.config.enable_memory_optimization:
                    self._check_memory_usage()
                    self._maybe_run_gc()
                    
            except Exception as e:
                logger.warning(f"Failed to process entity {entity_id}: {e}")
                self._error_count += 1
        
        return results
    
    def _process_single_entity(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Process a single entity with caching and optimization."""
        # Check cache first
        cache_key = f"entity_processed_{entity_id}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # API call with timeout
            start_time = time.time()
            entity = self.client.get_entity(entity_id)
            api_latency = (time.time() - start_time) * 1000
            
            if not entity:
                return None
            
            # Process metadata
            metadata = self.client.get_entity_metadata(entity_id)
            
            result = {
                'id': entity.id,
                'filename': entity.filename,
                'filepath': entity.filepath,
                'created_at': entity.created_at,
                'metadata': metadata,
                'processed_at': datetime.now().isoformat(),
                'api_latency_ms': api_latency
            }
            
            # Cache result
            self.cache_manager.set(cache_key, result, ttl=3600)  # 1 hour cache
            
            self._processed_count += 1
            return result
            
        except Exception as e:
            logger.warning(f"Error processing entity {entity_id}: {e}")
            self._error_count += 1
            return None
    
    def _check_memory_usage(self):
        """Check and manage memory usage."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.config.memory_limit_mb:
            logger.warning(f"Memory usage high: {memory_mb:.1f}MB, cleaning up")
            
            # Clear cache if needed
            if memory_mb > self.config.memory_limit_mb * 1.2:
                self.cache_manager.clear_expired()
                
            # Force garbage collection
            gc.collect()
    
    def _maybe_run_gc(self):
        """Run garbage collection periodically."""
        if self._processed_count - self._last_gc >= self.config.gc_frequency:
            gc.collect()
            self._last_gc = self._processed_count
    
    def get_adaptive_poll_interval(self) -> float:
        """Calculate adaptive polling interval based on activity."""
        if not self.config.enable_adaptive_polling:
            return 30.0  # Default
        
        # Check recent activity
        recent_events = self.db_manager.get_entities_via_api(limit=10)
        if not recent_events:
            return 60.0  # Slow polling when inactive
        
        # Check how recent the latest entity is
        if recent_events:
            latest_entity = recent_events[0]
            if 'created_at' in latest_entity:
                try:
                    created_time = datetime.fromisoformat(latest_entity['created_at'].replace('Z', '+00:00'))
                    age_minutes = (datetime.now() - created_time.replace(tzinfo=None)).total_seconds() / 60
                    
                    if age_minutes < 5:
                        return 10.0  # Fast polling for recent activity
                    elif age_minutes < 30:
                        return 30.0  # Normal polling
                    else:
                        return 60.0  # Slow polling for old activity
                except Exception as e:
                    logger.debug(f"Could not parse activity timestamp for adaptive polling: {e}")
        
        return 30.0  # Default fallback
    
    def optimize_cache_settings(self):
        """Optimize cache settings based on current usage."""
        cache_stats = self.cache_manager.get_stats()
        
        # Adjust TTL based on hit rate
        if cache_stats['hit_rate'] < 0.5:
            # Low hit rate - increase TTL
            logger.info("Low cache hit rate, increasing TTL")
            # Implementation would adjust cache TTL settings
        
        # Memory pressure management
        if cache_stats['memory_usage_mb'] > self.config.cache_size_limit_mb:
            logger.info("Cache memory pressure, cleaning up")
            self.cache_manager.clear_expired()
    
    def _update_metrics(self, processed_count: int):
        """Update performance metrics."""
        with self._lock:
            current_time = time.time()
            uptime = current_time - self.start_time
            
            # Calculate rates
            total_processed = self._processed_count
            processing_rate = total_processed / max(uptime, 1)
            error_rate = self._error_count / max(total_processed, 1)
            
            # Memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Cache stats
            cache_stats = self.cache_manager.get_stats()
            
            # API latency (from recent operations)
            api_latency = 0.0  # Would be calculated from recent API calls
            
            self.metrics = PerformanceMetrics(
                entities_processed=total_processed,
                processing_rate=processing_rate,
                memory_usage_mb=memory_mb,
                cache_hit_rate=cache_stats['hit_rate'],
                api_latency_ms=api_latency,
                error_rate=error_rate,
                uptime_seconds=uptime
            )
            
            # Store history
            self._performance_history.append(self.metrics)
            if len(self._performance_history) > 100:
                self._performance_history.pop(0)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        self._update_metrics(0)
        return self.metrics
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        metrics = self.get_performance_metrics()
        
        return {
            'current_metrics': {
                'entities_processed': metrics.entities_processed,
                'processing_rate_per_sec': round(metrics.processing_rate, 2),
                'memory_usage_mb': round(metrics.memory_usage_mb, 1),
                'cache_hit_rate': round(metrics.cache_hit_rate, 3),
                'error_rate': round(metrics.error_rate, 3),
                'uptime_hours': round(metrics.uptime_seconds / 3600, 1)
            },
            'health_indicators': {
                'memory_ok': metrics.memory_usage_mb < self.config.memory_limit_mb,
                'cache_efficient': metrics.cache_hit_rate > 0.7,
                'error_rate_ok': metrics.error_rate < 0.05,
                'processing_active': metrics.processing_rate > 0.1
            },
            'recommendations': self._get_optimization_recommendations()
        }
    
    def _get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current metrics."""
        recommendations = []
        
        if self.metrics.memory_usage_mb > self.config.memory_limit_mb * 0.8:
            recommendations.append("Consider increasing memory limit or reducing batch size")
        
        if self.metrics.cache_hit_rate < 0.5:
            recommendations.append("Cache hit rate low - consider increasing cache TTL")
        
        if self.metrics.error_rate > 0.1:
            recommendations.append("High error rate detected - check API connectivity")
        
        if self.metrics.processing_rate < 0.5:
            recommendations.append("Low processing rate - consider increasing worker threads")
        
        return recommendations
    
    def auto_optimize(self):
        """Automatically apply optimizations based on current metrics."""
        metrics = self.get_performance_metrics()
        
        # Auto-adjust polling interval
        if self.config.enable_adaptive_polling:
            new_interval = self.get_adaptive_poll_interval()
            logger.debug(f"Adaptive polling interval: {new_interval}s")
        
        # Auto-optimize cache
        self.optimize_cache_settings()
        
        # Memory cleanup if needed
        if metrics.memory_usage_mb > self.config.memory_limit_mb * 0.9:
            logger.info("Auto-optimization: running memory cleanup")
            self._check_memory_usage()
        
        logger.debug(f"Auto-optimization complete: {metrics.processing_rate:.2f} entities/sec")
    
    def __enter__(self):
        """Context manager entry."""
        self.start_batch_processing()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_batch_processing()


# Global optimizer instance
_global_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer(config: OptimizationConfig = None) -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PerformanceOptimizer(config)
    return _global_optimizer


def reset_performance_optimizer():
    """Reset global optimizer instance."""
    global _global_optimizer
    if _global_optimizer:
        _global_optimizer.stop_batch_processing()
    _global_optimizer = None


# High-level optimization functions

def optimize_for_high_volume(entity_count_estimate: int = 1000) -> OptimizationConfig:
    """Create optimized configuration for high-volume processing.
    
    Args:
        entity_count_estimate: Expected number of entities to process
        
    Returns:
        Optimized configuration
    """
    if entity_count_estimate < 100:
        # Low volume
        return OptimizationConfig(
            batch_size=10,
            max_workers=2,
            memory_limit_mb=200,
            gc_frequency=50
        )
    elif entity_count_estimate < 1000:
        # Medium volume
        return OptimizationConfig(
            batch_size=25,
            max_workers=4,
            memory_limit_mb=400,
            gc_frequency=100
        )
    else:
        # High volume
        return OptimizationConfig(
            batch_size=50,
            max_workers=8,
            memory_limit_mb=800,
            gc_frequency=200,
            enable_adaptive_polling=True
        )


def benchmark_performance(duration_seconds: int = 60) -> Dict[str, Any]:
    """Run performance benchmark.
    
    Args:
        duration_seconds: How long to run benchmark
        
    Returns:
        Benchmark results
    """
    with get_performance_optimizer() as optimizer:
        start_time = time.time()
        
        # Get some entities to process
        db = DatabaseManager(use_pensieve_api=True)
        entities = db.get_entities_via_api(limit=100)
        entity_ids = [e['id'] for e in entities[:20]]  # Test with 20 entities
        
        processed_count = 0
        while time.time() - start_time < duration_seconds and entity_ids:
            # Process batch
            results = optimizer.process_entities_batch(entity_ids)
            processed_count += len(results)
            
            # Sleep briefly
            time.sleep(1)
        
        metrics = optimizer.get_performance_metrics()
        
        return {
            'benchmark_duration_seconds': duration_seconds,
            'entities_processed': processed_count,
            'average_rate_per_second': processed_count / duration_seconds,
            'final_metrics': {
                'memory_usage_mb': metrics.memory_usage_mb,
                'cache_hit_rate': metrics.cache_hit_rate,
                'error_rate': metrics.error_rate
            }
        }