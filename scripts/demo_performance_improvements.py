#!/usr/bin/env python3
"""Demo script showing performance improvements with parallel analysis and caching."""

import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.health.testing.parallel_analyzer import PerformanceManager, ParallelGitAnalyzer


def simulate_analysis_function(file_path: Path) -> dict:
    """Simulate a time-consuming analysis function."""
    # Simulate processing time
    time.sleep(0.1)
    
    # Return some analysis results
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        return {
            'lines': len(content.split('\n')),
            'chars': len(content),
            'has_tests': 'def test_' in content,
            'complexity_estimate': min(content.count('if') + content.count('for') + content.count('while'), 20)
        }
    except OSError:
        return {'error': 'Could not read file'}


def demo_sequential_vs_parallel():
    """Demonstrate sequential vs parallel analysis performance."""
    project_root = Path.cwd()
    
    # Find Python files to analyze
    python_files = list(project_root.glob('tests/unit/*.py'))[:8]  # Limit to 8 files for demo
    
    if not python_files:
        print("❌ No Python test files found for demo")
        return
    
    print("🚀 Performance Demonstration")
    print("=" * 50)
    print(f"Analyzing {len(python_files)} files:")
    for file in python_files:
        print(f"  - {file.relative_to(project_root)}")
    print()
    
    # Sequential analysis
    print("📊 Sequential Analysis:")
    start_time = time.time()
    sequential_results = []
    for file_path in python_files:
        result = simulate_analysis_function(file_path)
        sequential_results.append(result)
    sequential_time = time.time() - start_time
    print(f"  Time: {sequential_time:.2f} seconds")
    print(f"  Files processed: {len(sequential_results)}")
    print()
    
    # Parallel analysis
    print("⚡ Parallel Analysis:")
    analyzer = ParallelGitAnalyzer(project_root, max_workers=4)
    start_time = time.time()
    parallel_results = analyzer.analyze_files_parallel(python_files, simulate_analysis_function)
    parallel_time = time.time() - start_time
    
    successful_results = [r for r in parallel_results if r.success]
    print(f"  Time: {parallel_time:.2f} seconds")
    print(f"  Files processed: {len(successful_results)}")
    print(f"  Speedup: {sequential_time / parallel_time:.1f}x")
    print()
    
    return sequential_time, parallel_time


def demo_caching_benefits():
    """Demonstrate caching performance benefits."""
    project_root = Path.cwd()
    python_files = list(project_root.glob('tests/unit/*.py'))[:5]  # Smaller set for caching demo
    
    if not python_files:
        print("❌ No Python test files found for caching demo")
        return
    
    print("💾 Caching Performance Demonstration")
    print("=" * 50)
    
    # Create performance manager
    manager = PerformanceManager(project_root)
    
    # Clear any existing cache
    manager.clear_cache()
    
    # First run - populate cache
    print("📝 First run (populating cache):")
    start_time = time.time()
    results1 = manager.analyze_files_with_cache(
        python_files, 
        "demo_analysis", 
        simulate_analysis_function,
        cache_ttl=300  # 5 minutes
    )
    first_run_time = time.time() - start_time
    
    stats1 = manager.get_performance_stats()
    print(f"  Time: {first_run_time:.2f} seconds")
    print(f"  Cache hit rate: {stats1['cache_hit_rate_percent']:.1f}%")
    print(f"  Files processed: {len([r for r in results1 if r.success])}")
    print()
    
    # Second run - use cache
    print("⚡ Second run (using cache):")
    start_time = time.time()
    results2 = manager.analyze_files_with_cache(
        python_files, 
        "demo_analysis", 
        simulate_analysis_function,
        cache_ttl=300
    )
    second_run_time = time.time() - start_time
    
    stats2 = manager.get_performance_stats()
    print(f"  Time: {second_run_time:.2f} seconds")
    print(f"  Cache hit rate: {stats2['cache_hit_rate_percent']:.1f}%")
    print(f"  Files processed: {len([r for r in results2 if r.success])}")
    print(f"  Speedup: {first_run_time / max(second_run_time, 0.001):.1f}x")
    print()
    
    # Show cache statistics
    cache_stats = stats2['cache_stats']
    print("📊 Cache Statistics:")
    print(f"  Files cached: {cache_stats['file_count']}")
    print(f"  Cache size: {cache_stats['total_size_mb']:.2f} MB")
    print(f"  Utilization: {cache_stats['utilization_percent']:.1f}%")
    print()
    
    return first_run_time, second_run_time


def demo_smart_cache_cleanup():
    """Demonstrate smart cache cleanup functionality."""
    project_root = Path.cwd()
    
    print("🧹 Smart Cache Cleanup Demonstration")
    print("=" * 50)
    
    # Create performance manager with small cache for demo
    manager = PerformanceManager(project_root)
    
    # Clear existing cache
    manager.clear_cache()
    
    # Add several items to cache
    print("📝 Adding items to cache...")
    test_data = [
        ("item1", {"data": "x" * 1000}),  # 1KB
        ("item2", {"data": "y" * 2000}),  # 2KB
        ("item3", {"data": "z" * 3000}),  # 3KB
    ]
    
    for key, data in test_data:
        manager.cache.set(key, data, ttl_seconds=60)
    
    initial_stats = manager.cache.get_stats()
    print(f"  Initial cache size: {initial_stats['total_size_mb']:.3f} MB")
    print(f"  Files in cache: {initial_stats['file_count']}")
    print()
    
    # Demonstrate manual cleanup
    print("🧹 Running cache cleanup...")
    manager.cleanup_cache()
    
    cleanup_stats = manager.cache.get_stats()
    print(f"  Cache size after cleanup: {cleanup_stats['total_size_mb']:.3f} MB")
    print(f"  Files in cache: {cleanup_stats['file_count']}")
    print()
    
    # Demonstrate cache clearing
    print("🗑️  Clearing entire cache...")
    manager.clear_cache()
    
    final_stats = manager.cache.get_stats()
    print(f"  Final cache size: {final_stats['total_size_mb']:.3f} MB")
    print(f"  Files in cache: {final_stats['file_count']}")
    print()


def main():
    """Run all performance demonstrations."""
    print("🎯 AutoTaskTracker Performance Improvements Demo")
    print("=" * 60)
    print()
    
    # Demo 1: Sequential vs Parallel
    try:
        seq_time, par_time = demo_sequential_vs_parallel()
        improvement_factor = seq_time / par_time
    except Exception as e:
        print(f"❌ Parallel demo failed: {e}")
        improvement_factor = 1.0
    
    print()
    
    # Demo 2: Caching benefits
    try:
        first_time, second_time = demo_caching_benefits()
        cache_improvement = first_time / max(second_time, 0.001)
    except Exception as e:
        print(f"❌ Caching demo failed: {e}")
        cache_improvement = 1.0
    
    print()
    
    # Demo 3: Cache cleanup
    try:
        demo_smart_cache_cleanup()
    except Exception as e:
        print(f"❌ Cache cleanup demo failed: {e}")
    
    # Summary
    print("📈 Performance Summary")
    print("=" * 30)
    print(f"🚀 Parallel processing improvement: {improvement_factor:.1f}x faster")
    print(f"💾 Caching improvement: {cache_improvement:.1f}x faster (second run)")
    print(f"🧹 Smart cache cleanup: Automatic maintenance")
    print()
    print("✅ Benefits:")
    print("  • Parallel execution uses multiple CPU cores")
    print("  • Smart caching avoids redundant analysis")
    print("  • Automatic cleanup prevents cache bloat")
    print("  • Configurable cache TTL and size limits")
    print("  • Robust error handling and fallbacks")


if __name__ == "__main__":
    main()