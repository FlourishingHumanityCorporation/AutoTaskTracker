"""Performance optimization for effectiveness-based test validation.

This module provides caching, parallel execution, and smart scheduling
to make mutation testing and effectiveness analysis faster and more efficient.
"""

import hashlib
import json
import logging
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
import threading

try:
    from .shared_utilities import BoundedDict, ValidationLimits, standardize_error_message
except ImportError:
    try:
        from shared_utilities import BoundedDict, ValidationLimits, standardize_error_message
    except ImportError:
        # Fallback implementations
        class BoundedDict(dict):
            def __init__(self, max_size=1000):
                super().__init__()
                self.max_size = max_size
                self._access_order = []
            
            def __setitem__(self, key, value):
                if key in self:
                    self._access_order.remove(key)
                self._access_order.append(key)
                super().__setitem__(key, value)
                while len(self) > self.max_size:
                    oldest_key = self._access_order.pop(0)
                    super().__delitem__(oldest_key)
        
        class ValidationLimits:
            MAX_CACHE_ENTRIES = 1000
        
        def standardize_error_message(error, context=""):
            return f"{context}: {type(error).__name__}: {str(error)}"

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached analysis result."""
    file_path: str
    file_hash: str
    timestamp: float
    analysis_type: str
    result: Dict[str, Any]
    config_hash: str


@dataclass  
class PerformanceMetrics:
    """Performance metrics for analysis operations."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    cache_hit: bool
    file_count: int
    error_count: int


class AnalysisCache:
    """Intelligent caching system for analysis results with bounded memory usage."""
    
    def __init__(self, cache_dir: Path, max_age_hours: int = 24, max_entries: int = None):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_seconds = max_age_hours * 3600
        self._lock = threading.Lock()
        
        # In-memory cache with LRU eviction
        if max_entries is None:
            max_entries = ValidationLimits.MAX_CACHE_ENTRIES
        self._memory_cache = BoundedDict(max_entries)
        
        # Load existing cache entries into memory (up to limit)
        self._load_existing_cache()
        
    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents for cache invalidation."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()[:16]
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not hash file {file_path}: {e}")
            return "unknown"
    
    def _get_config_hash(self, config: Dict) -> str:
        """Get hash of configuration for cache invalidation."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def _get_cache_path(self, file_path: Path, analysis_type: str) -> Path:
        """Get cache file path for a given analysis."""
        safe_name = str(file_path).replace('/', '_').replace('\\', '_')
        cache_file = f"{safe_name}_{analysis_type}.cache"
        return self.cache_dir / cache_file
    
    def _get_cache_key(self, file_path: Path, analysis_type: str) -> str:
        """Get cache key for memory cache."""
        return f"{file_path}:{analysis_type}"
    
    def _is_cache_entry_valid(self, entry: CacheEntry, file_path: Path, config: Dict) -> bool:
        """Check if a cache entry is still valid."""
        # Check if cache is too old
        if time.time() - entry.timestamp > self.max_age_seconds:
            return False
        
        # Check if file has changed
        current_hash = self._get_file_hash(file_path)
        if entry.file_hash != current_hash:
            return False
        
        # Check if config has changed
        config_hash = self._get_config_hash(config)
        if entry.config_hash != config_hash:
            return False
        
        return True
    
    def _load_existing_cache(self) -> None:
        """Load existing cache entries into memory (up to limit)."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            # Sort by modification time (newest first)
            cache_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            loaded_count = 0
            for cache_file in cache_files:
                if loaded_count >= self._memory_cache.max_size:
                    break
                
                try:
                    with open(cache_file, 'rb') as f:
                        entry: CacheEntry = pickle.load(f)
                    
                    # Only load if not expired
                    if time.time() - entry.timestamp <= self.max_age_seconds:
                        cache_key = self._get_cache_key(Path(entry.file_path), entry.analysis_type)
                        self._memory_cache[cache_key] = entry
                        loaded_count += 1
                        
                except Exception as e:
                    logger.debug(f"Could not load cache file {cache_file}: {e}")
                    # Remove corrupted cache file
                    cache_file.unlink(missing_ok=True)
            
            if loaded_count > 0:
                logger.debug(f"Loaded {loaded_count} cache entries into memory")
                
        except Exception as e:
            logger.warning(standardize_error_message(e, "Error loading existing cache"))
    
    def get(self, file_path: Path, analysis_type: str, config: Dict) -> Optional[Dict]:
        """Get cached result if valid, checking both memory and disk cache."""
        cache_key = self._get_cache_key(file_path, analysis_type)
        
        with self._lock:
            # Check memory cache first (fastest)
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                
                # Validate entry is still current
                if self._is_cache_entry_valid(entry, file_path, config):
                    logger.debug(f"Memory cache hit for {file_path.name} ({analysis_type})")
                    return entry.result
                else:
                    # Remove invalid entry
                    del self._memory_cache[cache_key]
            
            # Check disk cache
            cache_path = self._get_cache_path(file_path, analysis_type)
            if not cache_path.exists():
                return None
            
            try:
                with open(cache_path, 'rb') as f:
                    entry: CacheEntry = pickle.load(f)
                
                if self._is_cache_entry_valid(entry, file_path, config):
                    # Add to memory cache for faster future access
                    self._memory_cache[cache_key] = entry
                    logger.debug(f"Disk cache hit for {file_path.name} ({analysis_type})")
                    return entry.result
                else:
                    cache_path.unlink(missing_ok=True)
                    return None
                
            except Exception as e:
                logger.warning(standardize_error_message(e, f"Cache read error for {cache_path}"))
                cache_path.unlink(missing_ok=True)
                return None
    
    def put(self, file_path: Path, analysis_type: str, config: Dict, result: Dict) -> None:
        """Store result in both memory and disk cache."""
        cache_key = self._get_cache_key(file_path, analysis_type)
        
        with self._lock:
            try:
                entry = CacheEntry(
                    file_path=str(file_path),
                    file_hash=self._get_file_hash(file_path),
                    timestamp=time.time(),
                    analysis_type=analysis_type,
                    result=result,
                    config_hash=self._get_config_hash(config)
                )
                
                # Store in memory cache (with LRU eviction)
                self._memory_cache[cache_key] = entry
                
                # Store in disk cache
                cache_path = self._get_cache_path(file_path, analysis_type)
                with open(cache_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                logger.debug(f"Cached result for {file_path.name} ({analysis_type})")
                
            except Exception as e:
                logger.warning(standardize_error_message(e, "Cache write error"))
    
    def clear(self) -> None:
        """Clear all cached results from both memory and disk."""
        with self._lock:
            try:
                # Clear memory cache
                self._memory_cache.clear()
                
                # Clear disk cache
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                logger.info("Cache cleared (memory and disk)")
            except Exception as e:
                logger.warning(standardize_error_message(e, "Cache clear error"))
    
    def cleanup_old(self) -> None:
        """Remove expired cache entries from both memory and disk."""
        with self._lock:
            try:
                current_time = time.time()
                removed_count = 0
                
                # Clean up memory cache
                memory_keys_to_remove = []
                for key, entry in self._memory_cache.items():
                    if current_time - entry.timestamp > self.max_age_seconds:
                        memory_keys_to_remove.append(key)
                
                for key in memory_keys_to_remove:
                    del self._memory_cache[key]
                    removed_count += 1
                
                # Clean up disk cache
                for cache_file in self.cache_dir.glob("*.cache"):
                    try:
                        if current_time - cache_file.stat().st_mtime > self.max_age_seconds:
                            cache_file.unlink()
                            removed_count += 1
                    except Exception:
                        continue
                
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} expired cache entries")
                    
            except Exception as e:
                logger.warning(standardize_error_message(e, "Cache cleanup error"))


class ParallelAnalyzer:
    """Parallel execution manager for effectiveness analysis."""
    
    def __init__(self, max_workers: int = None, use_processes: bool = False):
        self.max_workers = max_workers or min(4, os.cpu_count() or 1)
        self.use_processes = use_processes
        self._metrics: List[PerformanceMetrics] = []
        
    def analyze_files_parallel(
        self, 
        analysis_func: Callable,
        file_list: List[Path],
        config: Dict,
        cache: Optional[AnalysisCache] = None
    ) -> List[Tuple[Path, Dict]]:
        """Analyze multiple files in parallel with optional caching."""
        
        start_time = time.time()
        results = []
        cache_hits = 0
        errors = 0
        
        # Create executor based on configuration
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_file = {}
            
            for file_path in file_list:
                # Check cache first
                if cache:
                    cached_result = cache.get(file_path, analysis_func.__name__, config)
                    if cached_result:
                        results.append((file_path, cached_result))
                        cache_hits += 1
                        continue
                
                # Submit for analysis
                future = executor.submit(self._safe_analysis, analysis_func, file_path, config)
                future_to_file[future] = file_path
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                
                try:
                    result = future.result()
                    results.append((file_path, result))
                    
                    # Cache successful result
                    if cache and result.get('analysis_errors', []) == []:
                        cache.put(file_path, analysis_func.__name__, config, result)
                        
                except Exception as e:
                    logger.error(f"Parallel analysis failed for {file_path}: {e}")
                    errors += 1
                    
                    # Create error result
                    error_result = {
                        'test_file': file_path.name,
                        'mutation_effectiveness': 0.0,
                        'overall_effectiveness': 0.0,
                        'actionable_recommendations': [f"Analysis failed: {e}"],
                        'analysis_errors': [str(e)]
                    }
                    results.append((file_path, error_result))
        
        # Record metrics
        end_time = time.time()
        metrics = PerformanceMetrics(
            operation="parallel_analysis",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            cache_hit=cache_hits > 0,
            file_count=len(file_list),
            error_count=errors
        )
        self._metrics.append(metrics)
        
        logger.info(f"Parallel analysis completed: {len(results)} files, {cache_hits} cache hits, {errors} errors in {metrics.duration:.1f}s")
        
        return results
    
    def _safe_analysis(self, analysis_func: Callable, file_path: Path, config: Dict) -> Dict:
        """Safely run analysis with error handling."""
        try:
            return analysis_func(file_path, config)
        except Exception as e:
            logger.warning(f"Analysis failed for {file_path}: {e}")
            return {
                'test_file': file_path.name,
                'mutation_effectiveness': 0.0,
                'overall_effectiveness': 0.0,
                'actionable_recommendations': [f"Analysis failed: {e}"],
                'analysis_errors': [str(e)]
            }
    
    def get_performance_metrics(self) -> List[PerformanceMetrics]:
        """Get performance metrics for analysis operations."""
        return self._metrics.copy()
    
    def clear_metrics(self) -> None:
        """Clear performance metrics."""
        self._metrics.clear()


class SmartScheduler:
    """Smart scheduling for analysis operations based on file characteristics."""
    
    def __init__(self, cache: AnalysisCache):
        self.cache = cache
        
    def prioritize_files(self, file_list: List[Path]) -> List[Path]:
        """Prioritize files for analysis based on various factors."""
        file_priorities = []
        
        for file_path in file_list:
            priority = self._calculate_priority(file_path)
            file_priorities.append((priority, file_path))
        
        # Sort by priority (higher first)
        file_priorities.sort(key=lambda x: x[0], reverse=True)
        
        return [file_path for _, file_path in file_priorities]
    
    def _calculate_priority(self, file_path: Path) -> float:
        """Calculate priority score for a file."""
        priority = 0.0
        
        try:
            # File size factor (smaller files get higher priority for speed)
            file_size = file_path.stat().st_size
            if file_size < 10 * 1024:  # < 10KB
                priority += 30
            elif file_size < 50 * 1024:  # < 50KB
                priority += 20
            elif file_size < 100 * 1024:  # < 100KB
                priority += 10
            
            # File age factor (newer files get higher priority)
            file_age_days = (time.time() - file_path.stat().st_mtime) / (24 * 3600)
            if file_age_days < 7:
                priority += 20
            elif file_age_days < 30:
                priority += 10
            
            # File type factors
            if 'test_' in file_path.name:
                priority += 15
            if any(keyword in file_path.name.lower() for keyword in ['critical', 'core', 'main']):
                priority += 25
            if any(keyword in file_path.name.lower() for keyword in ['experimental', 'draft', 'temp']):
                priority -= 10
            
            # Cache status (uncached files get higher priority)
            if not self._has_valid_cache(file_path):
                priority += 15
                
        except Exception:
            priority = 0.0
        
        return priority
    
    def _has_valid_cache(self, file_path: Path) -> bool:
        """Check if file has valid cached results."""
        # This is a simplified check - could be made more sophisticated
        cache_path = self.cache._get_cache_path(file_path, "effectiveness")
        return cache_path.exists()


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self, project_root: Path, config: Dict):
        self.project_root = project_root
        self.config = config
        
        # Initialize components
        cache_dir = project_root / ".cache" / "effectiveness_validation"
        self.cache = AnalysisCache(cache_dir)
        
        max_workers = config.get('max_worker_threads', 4)
        use_processes = config.get('use_process_pool', False)
        self.parallel_analyzer = ParallelAnalyzer(max_workers, use_processes)
        
        self.scheduler = SmartScheduler(self.cache)
        
        # Clean up old cache entries
        self.cache.cleanup_old()
    
    def optimize_analysis(
        self,
        analysis_func: Callable,
        file_list: List[Path],
        enable_parallel: bool = True,
        enable_caching: bool = True,
        enable_scheduling: bool = True
    ) -> List[Tuple[Path, Dict]]:
        """Run optimized analysis with all performance features."""
        
        logger.info(f"Starting optimized analysis of {len(file_list)} files")
        
        # Smart scheduling
        if enable_scheduling and len(file_list) > 1:
            file_list = self.scheduler.prioritize_files(file_list)
            logger.debug("Applied smart scheduling")
        
        # Parallel execution with caching
        if enable_parallel and len(file_list) > 1:
            cache = self.cache if enable_caching else None
            results = self.parallel_analyzer.analyze_files_parallel(
                analysis_func, file_list, self.config, cache
            )
        else:
            # Sequential execution
            results = []
            for file_path in file_list:
                try:
                    result = analysis_func(file_path, self.config)
                    results.append((file_path, result))
                except Exception as e:
                    logger.error(f"Analysis failed for {file_path}: {e}")
                    error_result = {
                        'test_file': file_path.name,
                        'analysis_errors': [str(e)]
                    }
                    results.append((file_path, error_result))
        
        logger.info(f"Optimized analysis completed: {len(results)} results")
        return results
    
    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report."""
        metrics = self.parallel_analyzer.get_performance_metrics()
        
        if not metrics:
            return {"message": "No performance data available"}
        
        total_duration = sum(m.duration for m in metrics)
        total_files = sum(m.file_count for m in metrics)
        total_cache_hits = sum(1 for m in metrics if m.cache_hit)
        total_errors = sum(m.error_count for m in metrics)
        
        return {
            "total_operations": len(metrics),
            "total_duration": total_duration,
            "total_files_analyzed": total_files,
            "cache_hit_rate": total_cache_hits / len(metrics) if metrics else 0,
            "error_rate": total_errors / total_files if total_files > 0 else 0,
            "average_files_per_second": total_files / total_duration if total_duration > 0 else 0,
            "parallel_workers": self.parallel_analyzer.max_workers,
            "cache_enabled": True
        }
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
    
    def clear_metrics(self) -> None:
        """Clear performance metrics."""
        self.parallel_analyzer.clear_metrics()