"""
Shared utilities for health test analyzers.

Provides common functionality like caching, parallel processing,
and auto-fix capabilities.
"""

import os
import time
import hashlib
import pickle
import threading
from pathlib import Path
from typing import List, Any, Optional, Callable
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class FileAnalysisCache:
    """Cache analysis results to speed up repeated runs."""
    
    def __init__(self, cache_dir=".pensieve_health_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._cleanup_old_cache()
    
    def _cleanup_old_cache(self, max_age_days=7):
        """Remove cache files older than max_age_days."""
        now = time.time()
        for cache_file in self.cache_dir.glob("*.pkl"):
            if (now - cache_file.stat().st_mtime) > (max_age_days * 86400):
                cache_file.unlink()
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return "error"
    
    def get_cached_result(self, file_path: Path, analysis_type: str) -> Optional[Any]:
        """Retrieve cached analysis result if file hasn't changed."""
        file_hash = self.get_file_hash(file_path)
        cache_file = self.cache_dir / f"{file_path.stem}_{analysis_type}_{file_hash}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                cache_file.unlink()  # Remove corrupted cache
        return None
    
    def cache_result(self, file_path: Path, analysis_type: str, result: Any):
        """Cache analysis result."""
        file_hash = self.get_file_hash(file_path)
        cache_file = self.cache_dir / f"{file_path.stem}_{analysis_type}_{file_hash}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception:
            pass  # Caching is optional


class ParallelAnalyzer:
    """Analyze files in parallel for better performance."""
    
    def __init__(self, max_workers=None):
        from multiprocessing import cpu_count
        self.max_workers = max_workers or min(cpu_count(), 8)
        self.cache = FileAnalysisCache()
    
    def analyze_files_parallel(self, files: List[Path], analysis_func: Callable, 
                             analysis_type: str, timeout_per_file: int = 2) -> List[tuple]:
        """Analyze multiple files (sequential processing to avoid hanging)."""
        results = []
        
        total_files = len(files)
        for i, file_path in enumerate(files, 1):
            # Progress indicator every 20 files
            if i % 20 == 0 or i == total_files:
                print(f"Processing files: {i}/{total_files}")
            
            # Check cache first
            cached_result = self.cache.get_cached_result(file_path, analysis_type)
            if cached_result is not None:
                results.append((file_path, cached_result))
                continue
            
            # Process file sequentially with basic timeout protection
            try:
                result_container = [None]
                exception_container = [None]
                
                def analyze_with_timeout():
                    try:
                        result_container[0] = analysis_func(file_path)
                    except Exception as e:
                        exception_container[0] = e
                
                thread = threading.Thread(target=analyze_with_timeout)
                thread.daemon = True
                thread.start()
                thread.join(timeout=timeout_per_file)
                
                if thread.is_alive():
                    # Thread is still running - timeout occurred
                    logger.warning(f"Timeout analyzing {file_path}")
                    results.append((file_path, None))
                elif exception_container[0]:
                    logger.warning(f"Error analyzing {file_path}: {exception_container[0]}")
                    results.append((file_path, None))
                else:
                    results.append((file_path, result_container[0]))
                    # Cache the result
                    if result_container[0] is not None:
                        self.cache.cache_result(file_path, analysis_type, result_container[0])
                    
            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {e}")
                results.append((file_path, None))
        
        return results


class IncrementalTestRunner:
    """Run tests only on changed files."""
    
    @staticmethod
    def get_changed_files(since_commit='HEAD~1', base_branch=None) -> Optional[List[Path]]:
        """Get list of Python files changed since a commit or against a base branch."""
        import subprocess
        try:
            # If base branch is specified (e.g., in PR), compare against it
            if base_branch:
                cmd = ['git', 'diff', '--name-only', f'{base_branch}...HEAD']
            else:
                cmd = ['git', 'diff', '--name-only', since_commit, 'HEAD']
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                changed_files = []
                for file in result.stdout.strip().split('\n'):
                    if file.endswith('.py') and os.path.exists(file):
                        changed_files.append(Path(file))
                return changed_files
                
        except Exception as e:
            logger.warning(f"Failed to get changed files: {e}")
        return None
    
    @staticmethod
    def should_run_incremental() -> bool:
        """Check if we should run in incremental mode."""
        return any([
            os.getenv('PENSIEVE_TEST_INCREMENTAL'),
            os.getenv('CI'),  # Most CI systems set this
            os.getenv('GITHUB_ACTIONS'),
            os.getenv('GITLAB_CI')
        ])