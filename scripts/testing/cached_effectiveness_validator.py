#!/usr/bin/env python3
"""
Cached Effectiveness Validator - Enhanced with production caching.

This script demonstrates how to integrate TieredCache with EffectivenessValidator
for repeated mutation testing with improved performance through caching.
"""

import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.health.testing.mutation_effectiveness import EffectivenessValidator
from tests.health.testing.production_cache import TieredCache, CacheStats
from tests.health.testing.config import EffectivenessConfig

logger = logging.getLogger(__name__)


class CachedEffectivenessValidator:
    """EffectivenessValidator enhanced with production caching."""
    
    def __init__(self, project_root: Path, 
                 cache_dir: Optional[Path] = None,
                 cache_memory_size: int = 500,
                 cache_disk_size_mb: int = 200,
                 effectiveness_config: Optional[EffectivenessConfig] = None):
        self.project_root = project_root
        self.effectiveness_config = effectiveness_config or EffectivenessConfig()
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = project_root / ".cache" / "mutation_testing"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.validator = EffectivenessValidator(project_root)
        self.cache = TieredCache(
            cache_dir=cache_dir,
            memory_size=cache_memory_size,
            disk_size_mb=cache_disk_size_mb,
            memory_ttl=1800,  # 30 minutes
            disk_ttl=86400    # 24 hours
        )
        
        self.cache_stats = CacheStats()
    
    def validate_test_effectiveness_cached(self, test_file: Path) -> Dict[str, Any]:
        """Validate test effectiveness with caching support."""
        # Generate cache key based on file content and config
        cache_key = self._generate_cache_key(test_file)
        
        # Try to get from cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            self.cache_stats.hits += 1
            logger.debug(f"Cache hit for {test_file.name}")
            return cached_result
        
        # Cache miss - perform actual validation
        self.cache_stats.misses += 1
        logger.debug(f"Cache miss for {test_file.name}")
        
        start_time = time.time()
        result = self.validator.validate_test_effectiveness(test_file)
        processing_time = time.time() - start_time
        
        # Add cache metadata to result
        result['_cache_metadata'] = {
            'cache_key': cache_key,
            'processing_time': processing_time,
            'cached': False,
            'timestamp': time.time()
        }
        
        # Store in cache with appropriate tags
        tags = [
            f"file:{test_file.stem}",
            f"effectiveness:{int(result.get('overall_effectiveness', 0) // 10) * 10}",  # Round to nearest 10
            "mutation_testing"
        ]
        
        self.cache.set(cache_key, result, tags=tags)
        logger.debug(f"Stored result for {test_file.name} in cache")
        
        return result
    
    def validate_multiple_files_cached(self, test_files: List[Path]) -> List[Dict[str, Any]]:
        """Validate multiple files with caching and performance reporting."""
        results = []
        start_time = time.time()
        
        logger.info(f"Starting cached validation of {len(test_files)} files")
        
        for i, test_file in enumerate(test_files):
            try:
                result = self.validate_test_effectiveness_cached(test_file)
                result['file_index'] = i
                results.append(result)
                
                # Progress logging
                if (i + 1) % 5 == 0 or i == len(test_files) - 1:
                    progress = (i + 1) / len(test_files) * 100
                    cache_hit_rate = self.get_cache_hit_rate()
                    logger.info(f"Progress: {progress:.1f}% ({i + 1}/{len(test_files)}) - Cache hit rate: {cache_hit_rate:.1f}%")
            
            except Exception as e:
                logger.error(f"Validation failed for {test_file}: {e}")
                error_result = {
                    'test_file': test_file.name,
                    'error': str(e),
                    'file_index': i,
                    '_cache_metadata': {
                        'cached': False,
                        'error': True,
                        'timestamp': time.time()
                    }
                }
                results.append(error_result)
        
        total_time = time.time() - start_time
        logger.info(f"Cached validation completed in {total_time:.2f}s")
        
        return results
    
    def _generate_cache_key(self, test_file: Path) -> str:
        """Generate a cache key based on file content and configuration."""
        try:
            # Get file content and modification time
            content = test_file.read_text(encoding='utf-8')
            mtime = test_file.stat().st_mtime
            
            # Include relevant config in cache key
            config_data = {
                'max_mutations': self.effectiveness_config.mutation.max_mutations_per_file,
                'timeout': self.effectiveness_config.mutation.timeout_seconds,
                'version': '2.0'  # Cache version for invalidation
            }
            
            # Create hash of content + mtime + config
            hash_data = f"{content}{mtime}{json.dumps(config_data, sort_keys=True)}"
            cache_key = hashlib.sha256(hash_data.encode('utf-8')).hexdigest()[:16]
            
            return f"effectiveness:{test_file.stem}:{cache_key}"
            
        except Exception as e:
            logger.warning(f"Failed to generate cache key for {test_file}: {e}")
            # Fallback to simple file-based key
            return f"effectiveness:{test_file.stem}:fallback"
    
    def get_cache_hit_rate(self) -> float:
        """Get current cache hit rate as percentage."""
        total_requests = self.cache_stats.hits + self.cache_stats.misses
        if total_requests == 0:
            return 0.0
        return (self.cache_stats.hits / total_requests) * 100
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        cache_internal_stats = self.cache.get_stats()
        
        return {
            'hit_rate': self.get_cache_hit_rate(),
            'total_hits': self.cache_stats.hits,
            'total_misses': self.cache_stats.misses,
            'total_requests': self.cache_stats.hits + self.cache_stats.misses,
            'l1_stats': {
                'size': len(self.cache.l1_cache._data),
                'max_size': self.cache.l1_cache.max_size,
            },
            'l2_stats': cache_internal_stats,
            'tiered_stats': self.cache._stats
        }
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries, optionally matching a pattern."""
        if pattern:
            # Clear specific pattern (would need implementation in TieredCache)
            logger.info(f"Clearing cache entries matching: {pattern}")
        else:
            # Clear all
            self.cache.clear()
            self.cache_stats = CacheStats()
            logger.info("Cleared all cache entries")
    
    def warmup_cache(self, test_files: List[Path], max_files: int = 10):
        """Pre-warm cache with commonly accessed files."""
        logger.info(f"Warming up cache with {min(len(test_files), max_files)} files")
        
        warmup_files = test_files[:max_files]
        for i, test_file in enumerate(warmup_files):
            try:
                self.validate_test_effectiveness_cached(test_file)
                logger.debug(f"Warmed up cache for {test_file.name}")
            except Exception as e:
                logger.warning(f"Cache warmup failed for {test_file}: {e}")
        
        logger.info(f"Cache warmup completed. Hit rate: {self.get_cache_hit_rate():.1f}%")


def demo_cached_validation():
    """Demonstrate cached validation performance."""
    project_root = Path(__file__).parent.parent.parent
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Find test files for demonstration
    test_files = list(project_root.glob("tests/**/test_*.py"))[:8]  # Limit for demo
    
    if not test_files:
        logger.warning("No test files found for demonstration")
        return
    
    logger.info(f"Found {len(test_files)} test files for cached validation demo")
    
    # Create cached validator
    cache_dir = project_root / ".cache" / "demo"
    validator = CachedEffectivenessValidator(
        project_root=project_root,
        cache_dir=cache_dir,
        cache_memory_size=100,
        cache_disk_size_mb=50
    )
    
    print("\\n" + "="*60)
    print("CACHED EFFECTIVENESS VALIDATION DEMO")
    print("="*60)
    
    # First run (cache miss expected)
    print("\\n🔄 First run (building cache)...")
    start_time = time.time()
    results_1 = validator.validate_multiple_files_cached(test_files)
    time_1 = time.time() - start_time
    stats_1 = validator.get_cache_stats()
    
    print(f"✅ First run completed in {time_1:.2f}s")
    print(f"   Cache hit rate: {stats_1['hit_rate']:.1f}%")
    print(f"   Cache requests: {stats_1['total_requests']}")
    
    # Second run (cache hits expected)
    print("\\n🚀 Second run (using cache)...")
    start_time = time.time()
    results_2 = validator.validate_multiple_files_cached(test_files)
    time_2 = time.time() - start_time
    stats_2 = validator.get_cache_stats()
    
    print(f"✅ Second run completed in {time_2:.2f}s")
    print(f"   Cache hit rate: {stats_2['hit_rate']:.1f}%")
    print(f"   Cache requests: {stats_2['total_requests']}")
    
    # Calculate performance improvement
    if time_1 > 0:
        speedup = time_1 / time_2 if time_2 > 0 else float('inf')
        print(f"   🏃‍♂️ Speedup: {speedup:.1f}x faster")
    
    # Detailed stats
    print(f"\\nCache Statistics:")
    print(f"  Memory cache size: {stats_2['l1_stats']['size']}/{stats_2['l1_stats']['max_size']}")
    print(f"  L1 promotions: {stats_2['tiered_stats']['l1_promotions']}")
    print(f"  L2 stores: {stats_2['tiered_stats']['l2_stores']}")
    
    # Effectiveness summary
    successful_results = [r for r in results_2 if 'error' not in r]
    if successful_results:
        avg_effectiveness = sum(r.get('overall_effectiveness', 0) for r in successful_results) / len(successful_results)
        print(f"\\nEffectiveness Summary:")
        print(f"  Average effectiveness: {avg_effectiveness:.1f}%")
        print(f"  Files processed: {len(successful_results)}/{len(test_files)}")
    
    # Cache warmup demonstration
    print("\\n🔥 Testing cache warmup...")
    validator.clear_cache()
    new_test_files = list(project_root.glob("tests/**/test_*.py"))[8:12]  # Different files
    if new_test_files:
        validator.warmup_cache(new_test_files, max_files=3)
        warmup_stats = validator.get_cache_stats()
        print(f"   Warmup cache hit rate: {warmup_stats['hit_rate']:.1f}%")


if __name__ == "__main__":
    demo_cached_validation()