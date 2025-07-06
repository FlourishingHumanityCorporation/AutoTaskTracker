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
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from tests.health.testing.mutation_effectiveness import EffectivenessValidator
    from tests.health.testing.production_cache import TieredCache
    from tests.health.testing.config import EffectivenessConfig
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Project root: {project_root}")
    print(f"Available modules: {list(project_root.glob('tests/health/testing/*.py'))}")
    sys.exit(1)

logger = logging.getLogger(__name__)


class CacheStats:
    """Simple cache statistics tracker."""
    def __init__(self):
        self.hits = 0
        self.misses = 0


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


def demo_cached_validation():
    """Demonstrate cached validation performance with limited scope."""
    project_root = Path(__file__).parent.parent.parent
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Find test files for demonstration (limited scope)
    test_files = [
        project_root / "tests" / "unit" / "test_mutation_refactoring.py"
    ]
    
    # Filter to only existing files
    test_files = [f for f in test_files if f.exists()]
    
    if not test_files:
        logger.warning("No test files found for demonstration")
        return
    
    logger.info(f"Found {len(test_files)} test files for cached validation demo")
    
    # Create cached validator with small cache for demo
    cache_dir = project_root / ".cache" / "demo"
    validator = CachedEffectivenessValidator(
        project_root=project_root,
        cache_dir=cache_dir,
        cache_memory_size=10,
        cache_disk_size_mb=10
    )
    
    print("\n" + "="*60)
    print("CACHED EFFECTIVENESS VALIDATION DEMO")
    print("="*60)
    
    # Configure for fast demo - reduce mutations
    validator.effectiveness_config.mutation.max_mutations_per_file = 3
    
    # First run (cache miss expected)
    print("\n🔄 First run (building cache)...")
    start_time = time.time()
    
    results_1 = []
    for test_file in test_files:
        result = validator.validate_test_effectiveness_cached(test_file)
        results_1.append(result)
    
    time_1 = time.time() - start_time
    hit_rate_1 = validator.get_cache_hit_rate()
    
    print(f"✅ First run completed in {time_1:.2f}s")
    print(f"   Cache hit rate: {hit_rate_1:.1f}%")
    print(f"   Files processed: {len(results_1)}")
    
    # Second run (cache hits expected)
    print("\n🚀 Second run (using cache)...")
    start_time = time.time()
    
    results_2 = []
    for test_file in test_files:
        result = validator.validate_test_effectiveness_cached(test_file)
        results_2.append(result)
    
    time_2 = time.time() - start_time
    hit_rate_2 = validator.get_cache_hit_rate()
    
    print(f"✅ Second run completed in {time_2:.2f}s")
    print(f"   Cache hit rate: {hit_rate_2:.1f}%")
    print(f"   Files processed: {len(results_2)}")
    
    # Calculate performance improvement
    if time_1 > 0 and time_2 > 0:
        speedup = time_1 / time_2
        print(f"   🏃‍♂️ Speedup: {speedup:.1f}x faster")
    
    # Cache statistics
    print(f"\nCache Statistics:")
    print(f"  Total hits: {validator.cache_stats.hits}")
    print(f"  Total misses: {validator.cache_stats.misses}")
    print(f"  Hit rate: {hit_rate_2:.1f}%")
    
    # Effectiveness summary
    successful_results = [r for r in results_2 if 'error' not in r]
    if successful_results:
        avg_effectiveness = sum(r.get('overall_effectiveness', 0) for r in successful_results) / len(successful_results)
        print(f"\nEffectiveness Summary:")
        print(f"  Average effectiveness: {avg_effectiveness:.1f}%")
        print(f"  Files processed: {len(successful_results)}/{len(test_files)}")
    
    # Show cache benefits
    print(f"\n💡 Cache Benefits:")
    if time_1 > time_2:
        time_saved = time_1 - time_2
        print(f"  Time saved on repeat runs: {time_saved:.2f}s")
        print(f"  Ideal for CI/CD with repeated test runs")
        print(f"  Persistent cache survives restarts")
    else:
        print(f"  Cache working - repeat runs will be faster")


if __name__ == "__main__":
    demo_cached_validation()