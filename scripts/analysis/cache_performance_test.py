#!/usr/bin/env python3
"""
Cache Performance Test Script
Tests cache performance with real data volume to validate integration.
"""

import sys
import os
import time
import logging
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.pensieve.cache_manager import PensieveCacheManager

# Set up logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import TaskRepository more carefully to avoid circular imports
try:
    from autotasktracker.dashboards.data.repositories import TaskRepository
except ImportError as e:
    # If import fails, we'll test database only
    logger.warning(f"Could not import TaskRepository: {e}")
    TaskRepository = None

class CachePerformanceTester:
    """Test cache performance with real data volume."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.repo = TaskRepository() if TaskRepository else None
        self.cache = PensieveCacheManager()
        self.results = {}
    
    def test_database_query_performance(self) -> Dict[str, Any]:
        """Test database query performance with and without cache."""
        logger.info("Testing database query performance...")
        
        # Clear cache first
        self.cache.clear()
        
        # Test 1: Cold cache (no cache hits)
        start_time = time.time()
        with self.db.get_connection() as conn:
            entities = conn.execute("SELECT * FROM entities LIMIT 100").fetchall()
        cold_time = time.time() - start_time
        
        # Test 2: Warm cache (repeat same query)
        start_time = time.time()
        with self.db.get_connection() as conn:
            entities = conn.execute("SELECT * FROM entities LIMIT 100").fetchall()
        warm_time = time.time() - start_time
        
        return {
            'cold_cache_time': cold_time,
            'warm_cache_time': warm_time,
            'entities_fetched': len(entities),
            'cache_improvement': max(0, (cold_time - warm_time) / cold_time * 100) if cold_time > 0 else 0
        }
    
    def test_repository_cache_performance(self) -> Dict[str, Any]:
        """Test repository-level cache performance."""
        logger.info("Testing repository cache performance...")
        
        if not self.repo:
            logger.warning("TaskRepository not available, skipping repository test")
            return {
                'repository_cold_time': 0.0,
                'repository_warm_time': 0.0,
                'tasks_fetched': 0,
                'repository_cache_improvement': 0.0,
                'status': 'skipped - import error'
            }
        
        # Clear cache
        self.cache.clear()
        
        # Test get_tasks_for_period performance  
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_time = time.time()
        tasks_cold = self.repo.get_tasks_for_period(start_date, end_date, limit=100)
        cold_time = time.time() - start_time
        
        # Test warm cache
        start_time = time.time()
        tasks_warm = self.repo.get_tasks_for_period(start_date, end_date, limit=100)
        warm_time = time.time() - start_time
        
        return {
            'repository_cold_time': cold_time,
            'repository_warm_time': warm_time,
            'tasks_fetched': len(tasks_cold),
            'repository_cache_improvement': max(0, (cold_time - warm_time) / cold_time * 100) if cold_time > 0 else 0
        }
    
    def test_cache_hit_rates(self) -> Dict[str, Any]:
        """Test cache hit rates under various load patterns."""
        logger.info("Testing cache hit rates...")
        
        # Clear cache and reset stats
        self.cache.clear()
        
        # Perform various queries to build cache
        queries = [
            ("SELECT * FROM entities LIMIT 50", "entities_50"),
            ("SELECT * FROM entities LIMIT 100", "entities_100"),
            ("SELECT * FROM metadata_entries LIMIT 50", "metadata_50"),
            ("SELECT * FROM entities LIMIT 50", "entities_50_repeat"),  # Should hit cache
        ]
        
        results = {}
        for query, label in queries:
            start_time = time.time()
            with self.db.get_connection() as conn:
                result = conn.execute(query).fetchall()
            query_time = time.time() - start_time
            results[label] = {
                'time': query_time,
                'rows': len(result)
            }
        
        # Get cache statistics
        cache_stats = self.cache.get_stats()
        
        return {
            'query_results': results,
            'cache_stats': cache_stats
        }
    
    def test_memory_usage(self) -> Dict[str, Any]:
        """Test cache memory usage patterns."""
        logger.info("Testing cache memory usage...")
        
        # Clear cache
        self.cache.clear()
        initial_stats = self.cache.get_stats()
        initial_size = initial_stats.get('memory_size', 0)
        
        # Fill cache with various queries
        large_queries = [
            "SELECT * FROM entities LIMIT 200",
            "SELECT * FROM metadata_entries LIMIT 200",
            "SELECT * FROM entities ORDER BY created_at DESC LIMIT 150"
        ]
        
        for query in large_queries:
            with self.db.get_connection() as conn:
                result = conn.execute(query).fetchall()
        
        final_stats = self.cache.get_stats()
        final_size = final_stats.get('memory_size', 0)
        
        return {
            'initial_cache_size': initial_size,
            'final_cache_size': final_size,
            'cache_growth': final_size - initial_size,
            'cache_limit': getattr(self.cache, 'memory_size_limit', 'N/A')
        }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive cache performance test suite."""
        logger.info("Starting comprehensive cache performance test...")
        
        # Test 1: Database query performance
        db_results = self.test_database_query_performance()
        
        # Test 2: Repository cache performance
        repo_results = self.test_repository_cache_performance()
        
        # Test 3: Cache hit rates
        hit_rate_results = self.test_cache_hit_rates()
        
        # Test 4: Memory usage
        memory_results = self.test_memory_usage()
        
        # Compile comprehensive results
        results = {
            'database_performance': db_results,
            'repository_performance': repo_results,
            'hit_rate_analysis': hit_rate_results,
            'memory_analysis': memory_results,
            'test_timestamp': time.time()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted test results."""
        print("\n" + "="*60)
        print("CACHE PERFORMANCE TEST RESULTS")
        print("="*60)
        
        # Database performance
        db_perf = results['database_performance']
        print(f"\n📊 Database Query Performance:")
        print(f"   Cold cache: {db_perf['cold_cache_time']:.4f}s")
        print(f"   Warm cache: {db_perf['warm_cache_time']:.4f}s")
        print(f"   Improvement: {db_perf['cache_improvement']:.1f}%")
        print(f"   Entities: {db_perf['entities_fetched']}")
        
        # Repository performance
        repo_perf = results['repository_performance']
        print(f"\n🗂️  Repository Performance:")
        print(f"   Cold cache: {repo_perf['repository_cold_time']:.4f}s")
        print(f"   Warm cache: {repo_perf['repository_warm_time']:.4f}s")
        print(f"   Improvement: {repo_perf['repository_cache_improvement']:.1f}%")
        print(f"   Tasks: {repo_perf['tasks_fetched']}")
        
        # Cache statistics
        cache_stats = results['hit_rate_analysis']['cache_stats']
        print(f"\n📈 Cache Statistics:")
        print(f"   Current entries: {cache_stats.get('current_size', 'N/A')}")
        print(f"   Memory usage: {cache_stats.get('memory_usage', 'N/A')}")
        
        # Memory analysis
        memory = results['memory_analysis']
        print(f"\n💾 Memory Usage:")
        print(f"   Initial size: {memory['initial_cache_size']}")
        print(f"   Final size: {memory['final_cache_size']}")
        print(f"   Growth: {memory['cache_growth']}")
        print(f"   Limit: {memory['cache_limit']}")
        
        print("\n" + "="*60)


def main():
    """Main test execution."""
    try:
        tester = CachePerformanceTester()
        results = tester.run_comprehensive_test()
        tester.print_results(results)
        
        # Determine if performance is acceptable
        db_improvement = results['database_performance']['cache_improvement']
        repo_improvement = results['repository_performance']['cache_improvement']
        
        print(f"\n✅ ASSESSMENT:")
        if db_improvement > 10 or repo_improvement > 10:
            print("   Cache performance is providing measurable benefits")
        else:
            print("   Cache performance improvements are minimal")
        
        if results['memory_analysis']['final_cache_size'] < results['memory_analysis']['cache_limit']:
            print("   Memory usage is within acceptable limits")
        else:
            print("   ⚠️  Memory usage approaching limits")
            
        return True
        
    except Exception as e:
        logger.error(f"Cache performance test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)