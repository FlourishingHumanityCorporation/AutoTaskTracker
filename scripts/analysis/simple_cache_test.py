#!/usr/bin/env python3
"""
Simple Cache Performance Test
Direct test of cache performance without complex imports.
"""

import sys
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import only what we need
from autotasktracker.pensieve.cache_manager import PensieveCacheManager
from autotasktracker.core.database import DatabaseManager

def get_database_path():
    """Get the database path."""
    return os.path.expanduser("~/.memos/database.db")

def test_cache_performance():
    """Test cache performance with real database queries."""
    logger.info("Starting simple cache performance test...")
    
    # Initialize cache
    cache = PensieveCacheManager()
    cache.clear()
    
    # Initialize DatabaseManager
    db_manager = DatabaseManager()
    
    logger.info("Using DatabaseManager for all database operations")
    
    # Test queries
    queries = [
        "SELECT COUNT(*) FROM entities",
        "SELECT * FROM entities LIMIT 50",
        "SELECT * FROM metadata_entries LIMIT 50",
        "SELECT * FROM entities ORDER BY created_at DESC LIMIT 25"
    ]
    
    results = {}
    
    for i, query in enumerate(queries):
        logger.info(f"Testing query {i+1}: {query[:50]}...")
        
        # Cold cache test
        cache.clear()
        start_time = time.time()
        with db_manager.get_connection() as conn:
            result = conn.execute(query).fetchall()
        cold_time = time.time() - start_time
        
        # Warm cache test (repeat same query)
        start_time = time.time()
        with db_manager.get_connection() as conn:
            result2 = conn.execute(query).fetchall()
        warm_time = time.time() - start_time
        
        # Calculate improvement
        improvement = max(0, (cold_time - warm_time) / cold_time * 100) if cold_time > 0 else 0
        
        results[f"query_{i+1}"] = {
            'query': query[:50] + '...' if len(query) > 50 else query,
            'cold_time': cold_time,
            'warm_time': warm_time,
            'improvement_percent': improvement,
            'rows_returned': len(result)
        }
        
        logger.info(f"  Cold: {cold_time:.4f}s, Warm: {warm_time:.4f}s, Improvement: {improvement:.1f}%")
    
    # Test cache statistics
    cache_stats = cache.get_stats()
    
    # Print comprehensive results
    print("\n" + "="*60)
    print("SIMPLE CACHE PERFORMANCE TEST RESULTS")
    print("="*60)
    
    total_improvement = 0
    valid_tests = 0
    
    for test_name, test_data in results.items():
        print(f"\n📊 {test_name.upper()}:")
        print(f"   Query: {test_data['query']}")
        print(f"   Cold cache: {test_data['cold_time']:.4f}s")
        print(f"   Warm cache: {test_data['warm_time']:.4f}s")
        print(f"   Improvement: {test_data['improvement_percent']:.1f}%")
        print(f"   Rows: {test_data['rows_returned']}")
        
        if test_data['improvement_percent'] > 0:
            total_improvement += test_data['improvement_percent']
            valid_tests += 1
    
    # Cache statistics
    print(f"\n📈 Cache Statistics:")
    print(f"   Memory hits: {cache_stats.get('memory_hits', 0)}")
    print(f"   Memory misses: {cache_stats.get('memory_misses', 0)}")
    print(f"   Hit rate: {cache_stats.get('hit_rate_percent', 0):.1f}%")
    print(f"   Memory size: {cache_stats.get('memory_size', 0)} entries")
    print(f"   Total requests: {cache_stats.get('total_requests', 0)}")
    
    # Overall assessment
    avg_improvement = total_improvement / valid_tests if valid_tests > 0 else 0
    print(f"\n✅ OVERALL ASSESSMENT:")
    print(f"   Average improvement: {avg_improvement:.1f}%")
    
    if avg_improvement > 15:
        print("   🟢 Cache is providing significant performance benefits")
        assessment = "excellent"
    elif avg_improvement > 5:
        print("   🟡 Cache is providing moderate performance benefits")
        assessment = "good"
    else:
        print("   🔴 Cache performance benefits are minimal")
        assessment = "needs improvement"
    
    print(f"   Performance tier: {assessment}")
    print("\n" + "="*60)
    
    return True

def main():
    """Main test execution."""
    try:
        success = test_cache_performance()
        return success
    except Exception as e:
        logger.error(f"Cache performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)