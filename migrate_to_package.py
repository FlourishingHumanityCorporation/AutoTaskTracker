#!/usr/bin/env python3
"""
Migration script to update existing dashboards to use the new package structure.
This demonstrates how to refactor the code to use centralized modules.
"""

import os
import sys

# Add the package to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("AutoTaskTracker Migration Guide")
print("=" * 50)
print()

print("To migrate your existing dashboards to use the new package structure:")
print()

print("1. Replace database connection code:")
print("   OLD:")
print("   ```python")
print("   def get_db_connection():")
print("       conn = sqlite3.connect(f'file:{PENSIEVE_DB_PATH}?mode=ro', uri=True)")
print("       conn.row_factory = sqlite3.Row")
print("       return conn")
print("   ```")
print()
print("   NEW:")
print("   ```python")
print("   from autotasktracker import DatabaseManager")
print("   db = DatabaseManager()")
print("   # Use db.fetch_tasks() instead of raw SQL")
print("   ```")
print()

print("2. Replace categorize_activity function:")
print("   OLD:")
print("   ```python")
print("   def categorize_activity(window_title, ocr_text):")
print("       # ... duplicate code ...")
print("   ```")
print()
print("   NEW:")
print("   ```python")
print("   from autotasktracker import ActivityCategorizer")
print("   category = ActivityCategorizer.categorize(window_title, ocr_text)")
print("   ```")
print()

print("3. Replace hardcoded configuration:")
print("   OLD:")
print("   ```python")
print("   PENSIEVE_DB_PATH = os.path.join(HOME_DIR, '.memos', 'database.db')")
print("   TASK_BOARD_PORT = 8502")
print("   ```")
print()
print("   NEW:")
print("   ```python")
print("   from autotasktracker import get_config")
print("   config = get_config()")
print("   db_path = config.DB_PATH")
print("   port = config.TASK_BOARD_PORT")
print("   ```")
print()

print("4. Use environment variables for configuration:")
print("   ```bash")
print("   export AUTOTASK_TASK_BOARD_PORT=8510")
print("   export AUTOTASK_AUTO_REFRESH_SECONDS=60")
print("   python task_board.py")
print("   ```")
print()

print("5. Example refactored imports:")
print("   ```python")
print("   # At the top of your dashboard file")
print("   from autotasktracker import (")
print("       DatabaseManager,")
print("       ActivityCategorizer,")
print("       extract_task_summary,")
print("       Config,")
print("       get_config")
print("   )")
print("   ```")
print()

print("Benefits of this refactoring:")
print("- No more duplicate code across dashboards")
print("- Centralized configuration management")
print("- Easier to maintain and test")
print("- Better performance with connection pooling")
print("- Cleaner, more professional codebase")
print()

# Test that imports work
try:
    from autotasktracker import DatabaseManager, ActivityCategorizer, Config
    print("✅ Package imports working correctly!")
    
    # Test configuration
    config = Config()
    print(f"✅ Default database path: {config.DB_PATH}")
    print(f"✅ Default task board port: {config.TASK_BOARD_PORT}")
    
    # Test categorizer
    category = ActivityCategorizer.categorize("Visual Studio Code - main.py")
    print(f"✅ Test categorization: 'Visual Studio Code' → {category}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")