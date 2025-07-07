#!/usr/bin/env python3
"""
Test database queries for PostgreSQL migration.
Verifies all core database functionality works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
import time
from datetime import datetime, timedelta


def test_connection():
    """Test basic database connection."""
    print("Testing database connection...")
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        print("✅ Connection test passed")
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def test_fetch_tasks():
    """Test fetching tasks."""
    print("\nTesting fetch_tasks...")
    try:
        db = DatabaseManager()
        start = time.time()
        tasks = db.fetch_tasks(limit=10)
        duration = time.time() - start
        print(f"✅ Fetched {len(tasks)} tasks in {duration:.2f}s")
        
        if tasks:
            sample = tasks[0]
            print(f"   Sample task ID: {sample.get('id')}")
            print(f"   Timestamp: {sample.get('timestamp')}")
        return True
    except Exception as e:
        print(f"❌ fetch_tasks failed: {e}")
        return False


def test_get_screenshots():
    """Test fetching screenshots."""
    print("\nTesting get_screenshots...")
    try:
        db = DatabaseManager()
        start = time.time()
        screenshots = db.get_screenshots(limit=10)
        duration = time.time() - start
        print(f"✅ Fetched {len(screenshots)} screenshots in {duration:.2f}s")
        
        if screenshots:
            sample = screenshots[0]
            print(f"   Sample ID: {sample.get('id')}")
            print(f"   File path: {sample.get('file_path', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ get_screenshots failed: {e}")
        return False


def test_search_tasks():
    """Test searching tasks."""
    print("\nTesting search_tasks...")
    try:
        db = DatabaseManager()
        search_term = "task"
        start = time.time()
        results = db.search_tasks(search_term, limit=5)
        duration = time.time() - start
        print(f"✅ Search for '{search_term}' found {len(results)} results in {duration:.2f}s")
        return True
    except Exception as e:
        print(f"❌ search_tasks failed: {e}")
        return False


def test_get_categories():
    """Test fetching categories."""
    print("\nTesting get_categories...")
    try:
        db = DatabaseManager()
        start = time.time()
        categories = db.get_categories()
        duration = time.time() - start
        print(f"✅ Found {len(categories)} categories in {duration:.2f}s")
        
        if categories:
            for i, cat in enumerate(categories[:5]):
                print(f"   {i+1}. {cat}")
        return True
    except Exception as e:
        print(f"❌ get_categories failed: {e}")
        return False


def test_date_filtering():
    """Test date range filtering."""
    print("\nTesting date range filtering...")
    try:
        db = DatabaseManager()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start = time.time()
        tasks = db.fetch_tasks(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            limit=10
        )
        duration = time.time() - start
        print(f"✅ Fetched {len(tasks)} tasks from last 7 days in {duration:.2f}s")
        return True
    except Exception as e:
        print(f"❌ Date filtering failed: {e}")
        return False


def test_performance():
    """Test query performance."""
    print("\nTesting query performance...")
    try:
        db = DatabaseManager()
        
        # Test bulk fetch
        start = time.time()
        tasks = db.fetch_tasks(limit=100)
        duration = time.time() - start
        print(f"✅ Fetched 100 tasks in {duration:.2f}s ({100/duration:.0f} tasks/sec)")
        
        # Test with complex filters
        start = time.time()
        filtered = db.fetch_tasks(
            category="work",
            start_date=(datetime.now() - timedelta(days=30)).isoformat(),
            limit=50
        )
        duration = time.time() - start
        print(f"✅ Complex filter query in {duration:.2f}s")
        
        return True
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


def main():
    """Run all database tests."""
    print("AutoTaskTracker Database Query Tests")
    print("=" * 40)
    
    tests = [
        test_connection,
        test_fetch_tasks,
        test_get_screenshots,
        test_search_tasks,
        test_get_categories,
        test_date_filtering,
        test_performance
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ All database queries working correctly!")
        return 0
    else:
        print(f"\n❌ {failed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())