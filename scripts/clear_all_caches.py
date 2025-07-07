#!/usr/bin/env python
"""Clear all caches to force fresh data."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.pensieve.cache_manager import get_cache_manager, reset_cache_manager

# Clear Pensieve cache
print("Clearing Pensieve cache...")
cache = get_cache_manager()
cache.clear()
reset_cache_manager()
print("✓ Pensieve cache cleared")

# Clear any SQLite cache files
cache_dir = os.path.expanduser("~/.memos/autotask_cache")
if os.path.exists(cache_dir):
    import shutil
    shutil.rmtree(cache_dir)
    os.makedirs(cache_dir)
    print("✓ Disk cache cleared")

print("\nAll caches cleared. Restart the dashboard to see fresh data.")