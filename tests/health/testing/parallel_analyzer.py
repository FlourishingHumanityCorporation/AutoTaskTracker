"""Parallel analysis utilities for high-performance testing validation.

This module provides parallel execution capabilities and smart caching
to dramatically improve the performance of test analysis operations.
"""

import asyncio
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Tuple, Set
import multiprocessing as mp

from .retry_utils import GitOperations, RetryConfig

logger = logging.getLogger(__name__)


@dataclass
class AnalysisTask:
    """Represents a single analysis task that can be executed in parallel."""
    task_id: str
    file_path: Path
    analysis_type: str
    priority: int = 1  # Higher numbers = higher priority
    dependencies: List[str] = None  # Task IDs this depends on
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class AnalysisResult:
    """Result of a parallel analysis task."""
    task_id: str
    file_path: Path
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


class ParallelGitAnalyzer:
    """Parallel Git operations for analyzing multiple files efficiently."""
    
    def __init__(self, project_root: Path, max_workers: Optional[int] = None):
        self.project_root = project_root
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.git_ops = GitOperations(project_root)
        
    def analyze_files_parallel(self, file_paths: List[Path], 
                              analysis_func: Callable[[Path], Dict]) -> List[AnalysisResult]:
        """Analyze multiple files in parallel using Git operations.
        
        Args:
            file_paths: List of file paths to analyze
            analysis_func: Function that takes a Path and returns analysis dict
            
        Returns:
            List of AnalysisResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {}
            for i, file_path in enumerate(file_paths):
                future = executor.submit(self._analyze_single_file, file_path, analysis_func, f"task_{i}")
                future_to_path[future] = file_path
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Analysis failed for {file_path}: {e}")
                    results.append(AnalysisResult(
                        task_id=f"task_{len(results)}",
                        file_path=file_path,
                        success=False,
                        error=str(e)
                    ))
        
        return results
    
    def _analyze_single_file(self, file_path: Path, analysis_func: Callable, task_id: str) -> AnalysisResult:
        """Analyze a single file with timing and error handling."""
        start_time = time.time()
        
        try:
            result = analysis_func(file_path)
            execution_time = time.time() - start_time
            
            return AnalysisResult(
                task_id=task_id,
                file_path=file_path,
                success=True,
                result=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return AnalysisResult(
                task_id=task_id,
                file_path=file_path,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def get_file_history_parallel(self, file_paths: List[Path], 
                                 max_commits: int = 5) -> Dict[Path, List[Dict]]:
        """Get Git history for multiple files in parallel.
        
        Args:
            file_paths: List of file paths
            max_commits: Maximum commits per file
            
        Returns:
            Dictionary mapping file paths to their commit history
        """
        def get_history(file_path: Path) -> List[Dict]:
            try:
                return self.git_ops.get_file_history(file_path, max_commits)
            except Exception as e:
                logger.warning(f"Could not get history for {file_path}: {e}")
                return []
        
        results = self.analyze_files_parallel(file_paths, get_history)
        
        # Convert to dictionary
        history_map = {}
        for result in results:
            if result.success:
                history_map[result.file_path] = result.result
            else:
                history_map[result.file_path] = []
        
        return history_map


class SmartCache:
    """Smart cache with automatic cleanup and performance optimization."""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 100, cleanup_interval_hours: int = 24):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cleanup_interval = cleanup_interval_hours * 3600
        self.last_cleanup = time.time()
        self._lock = threading.Lock()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with automatic cleanup."""
        self._maybe_cleanup()
        
        cache_file = self.cache_dir / f"{key}.cache"
        
        try:
            if cache_file.exists():
                import pickle
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # Check if cache is still valid
                if cached_data.get('expires', float('inf')) > time.time():
                    # Update access time
                    cached_data['last_access'] = time.time()
                    with open(cache_file, 'wb') as f:
                        pickle.dump(cached_data, f)
                    
                    return cached_data['data']
                else:
                    # Cache expired, remove it
                    cache_file.unlink()
            
        except (pickle.PickleError, OSError) as e:
            logger.debug(f"Cache read error for {key}: {e}")
            # Remove corrupted cache file
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        return None
    
    def set(self, key: str, data: Any, ttl_seconds: int = 3600) -> bool:
        """Set item in cache with TTL."""
        cache_file = self.cache_dir / f"{key}.cache"
        
        try:
            import pickle
            cached_data = {
                'data': data,
                'created': time.time(),
                'last_access': time.time(),
                'expires': time.time() + ttl_seconds
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cached_data, f)
            
            return True
            
        except (pickle.PickleError, OSError) as e:
            logger.warning(f"Cache write error for {key}: {e}")
            return False
    
    def _maybe_cleanup(self):
        """Perform cleanup if interval has passed."""
        current_time = time.time()
        
        if current_time - self.last_cleanup > self.cleanup_interval:
            # Use lock to prevent concurrent cleanup
            with self._lock:
                # Double-check after acquiring lock
                if current_time - self.last_cleanup > self.cleanup_interval:
                    self._cleanup_cache()
                    self.last_cleanup = current_time
    
    def _cleanup_cache(self):
        """Clean up expired and least-recently-used cache entries."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            total_size = 0
            file_info = []
            
            # Collect information about all cache files
            for cache_file in cache_files:
                try:
                    stat = cache_file.stat()
                    file_size = stat.st_size
                    total_size += file_size
                    
                    # Try to get last access time from cache data
                    import pickle
                    try:
                        with open(cache_file, 'rb') as f:
                            cached_data = pickle.load(f)
                        
                        # Check if expired
                        if cached_data.get('expires', float('inf')) <= time.time():
                            cache_file.unlink()
                            logger.debug(f"Removed expired cache file: {cache_file}")
                            continue
                        
                        last_access = cached_data.get('last_access', stat.st_atime)
                        
                    except (pickle.PickleError, KeyError):
                        # Use file system access time as fallback
                        last_access = stat.st_atime
                    
                    file_info.append({
                        'path': cache_file,
                        'size': file_size,
                        'last_access': last_access
                    })
                    
                except OSError as e:
                    logger.debug(f"Error reading cache file {cache_file}: {e}")
            
            # If we're over the size limit, remove least recently used files
            removed_size = 0  # Initialize here
            if total_size > self.max_size_bytes:
                # Sort by last access time (oldest first)
                file_info.sort(key=lambda x: x['last_access'])
                
                target_size = self.max_size_bytes * 0.8  # Remove 20% extra for buffer
                
                for file_data in file_info:
                    if total_size - removed_size <= target_size:
                        break
                    
                    try:
                        file_data['path'].unlink()
                        removed_size += file_data['size']
                        logger.debug(f"Removed LRU cache file: {file_data['path']}")
                    except OSError as e:
                        logger.debug(f"Could not remove cache file {file_data['path']}: {e}")
            
            logger.info(f"Cache cleanup completed. Total size: {(total_size - removed_size) / 1024 / 1024:.1f}MB")
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                except OSError:
                    pass
            logger.info(f"Cleared {len(cache_files)} cache entries")
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files if f.exists())
            
            return {
                'file_count': len(cache_files),
                'total_size_mb': total_size / 1024 / 1024,
                'max_size_mb': self.max_size_bytes / 1024 / 1024,
                'utilization_percent': (total_size / self.max_size_bytes) * 100,
                'last_cleanup': self.last_cleanup
            }
        except Exception as e:
            logger.error(f"Could not get cache stats: {e}")
            return {}


class PerformanceManager:
    """Manages parallel execution and caching for optimal performance."""
    
    def __init__(self, project_root: Path, cache_dir: Optional[Path] = None):
        self.project_root = project_root
        self.cache_dir = cache_dir or (project_root / ".cache" / "analysis")
        
        self.cache = SmartCache(self.cache_dir)
        self.git_analyzer = ParallelGitAnalyzer(project_root)
        
        # Performance metrics
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'parallel_tasks_executed': 0,
            'total_execution_time': 0.0
        }
    
    def analyze_files_with_cache(self, file_paths: List[Path], 
                                analysis_type: str,
                                analysis_func: Callable[[Path], Dict],
                                cache_ttl: int = 3600) -> List[AnalysisResult]:
        """Analyze files with intelligent caching and parallel execution.
        
        Args:
            file_paths: Files to analyze
            analysis_type: Type of analysis for cache key generation
            analysis_func: Function to perform analysis
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            List of analysis results
        """
        start_time = time.time()
        
        # Check cache for each file
        uncached_files = []
        cached_results = []
        
        for i, file_path in enumerate(file_paths):
            cache_key = self._generate_cache_key(file_path, analysis_type)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                self._metrics['cache_hits'] += 1
                cached_results.append(AnalysisResult(
                    task_id=f"cached_{i}",
                    file_path=file_path,
                    success=True,
                    result=cached_result,
                    execution_time=0.0
                ))
            else:
                self._metrics['cache_misses'] += 1
                uncached_files.append(file_path)
        
        # Analyze uncached files in parallel
        new_results = []
        if uncached_files:
            new_results = self.git_analyzer.analyze_files_parallel(uncached_files, analysis_func)
            
            # Cache the new results
            for result in new_results:
                if result.success:
                    cache_key = self._generate_cache_key(result.file_path, analysis_type)
                    self.cache.set(cache_key, result.result, cache_ttl)
        
        # Combine cached and new results
        all_results = cached_results + new_results
        
        # Update metrics
        self._metrics['parallel_tasks_executed'] += len(uncached_files)
        self._metrics['total_execution_time'] += time.time() - start_time
        
        return all_results
    
    def _generate_cache_key(self, file_path: Path, analysis_type: str) -> str:
        """Generate a cache key based on file path, modification time, and analysis type."""
        try:
            # Include file modification time to invalidate cache when file changes
            mtime = file_path.stat().st_mtime
            path_str = str(file_path.relative_to(self.project_root))
            
            import hashlib
            key_data = f"{path_str}:{analysis_type}:{mtime}"
            return hashlib.md5(key_data.encode()).hexdigest()
            
        except (OSError, ValueError):
            # Fallback to path-only key
            import hashlib
            key_data = f"{file_path}:{analysis_type}"
            return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance metrics and cache statistics."""
        cache_stats = self.cache.get_stats()
        
        total_requests = self._metrics['cache_hits'] + self._metrics['cache_misses']
        hit_rate = (self._metrics['cache_hits'] / max(total_requests, 1)) * 100
        
        return {
            'cache_hit_rate_percent': hit_rate,
            'cache_stats': cache_stats,
            'parallel_tasks': self._metrics['parallel_tasks_executed'],
            'total_execution_time': self._metrics['total_execution_time'],
            'average_task_time': (
                self._metrics['total_execution_time'] / 
                max(self._metrics['parallel_tasks_executed'], 1)
            )
        }
    
    def cleanup_cache(self):
        """Manually trigger cache cleanup."""
        self.cache._cleanup_cache()
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()