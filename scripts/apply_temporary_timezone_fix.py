#!/usr/bin/env python
"""Apply temporary timezone fix to repository queries."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta

print("=== APPLYING TEMPORARY TIMEZONE FIX ===\n")

# Create a patch file for the repositories
patch_content = '''
def _adjust_for_timezone_issue(self, dt):
    """Temporary fix: Add 8 hours to compensate for timezone storage issue."""
    # TODO: Remove this once root cause is fixed
    return dt + timedelta(hours=8)
'''

# Read the current repositories.py file
repo_file = "/Users/paulrohde/CodeProjects/AutoTaskTracker/autotasktracker/dashboards/data/repositories.py"
with open(repo_file, 'r') as f:
    content = f.read()

# Check if fix already applied
if "_adjust_for_timezone_issue" in content:
    print("✓ Timezone fix already applied")
else:
    print("Applying timezone fix to repositories.py...")
    
    # Find where to insert the fix (after imports)
    import_end = content.find("logger = logging.getLogger(__name__)")
    if import_end == -1:
        print("❌ Could not find insertion point")
        sys.exit(1)
    
    # Insert after the logger line
    insert_pos = content.find('\n', import_end) + 1
    
    # Add the timezone adjustment to date parameters
    # Update get_tasks_for_period method
    method_start = content.find("def get_tasks_for_period(")
    if method_start != -1:
        # Find the query execution
        query_pos = content.find("self._execute_query(query", method_start)
        if query_pos != -1:
            # Find the parameters
            params_start = content.find("(", query_pos + len("self._execute_query(query"))
            params_end = content.find(")", params_start)
            
            old_params = content[params_start:params_end+1]
            
            # Modify to add timezone adjustment
            new_params = old_params.replace(
                "start_date.strftime('%Y-%m-%d %H:%M:%S')",
                "(start_date + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')"
            ).replace(
                "end_date.strftime('%Y-%m-%d %H:%M:%S')",
                "(end_date + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')"
            )
            
            if new_params != old_params:
                content = content[:params_start] + new_params + content[params_end+1:]
                print("✓ Updated get_tasks_for_period query parameters")
    
    # Write the updated file
    with open(repo_file, 'w') as f:
        f.write(content)
    
    print("✓ Timezone fix applied successfully")

# Also create a simple override file that can be imported
override_content = '''#!/usr/bin/env python
"""Temporary timezone fix for AutoTaskTracker queries."""

from datetime import timedelta

# Timezone offset to add to queries (8 hours)
TIMEZONE_OFFSET_HOURS = 8

def adjust_query_time(dt):
    """Add timezone offset to query times."""
    return dt + timedelta(hours=TIMEZONE_OFFSET_HOURS)

def adjust_display_time(dt):
    """Subtract timezone offset for display."""
    return dt - timedelta(hours=TIMEZONE_OFFSET_HOURS)
'''

override_file = "/Users/paulrohde/CodeProjects/AutoTaskTracker/autotasktracker/dashboards/data/timezone_fix.py"
with open(override_file, 'w') as f:
    f.write(override_content)

print(f"✓ Created timezone fix module at {override_file}")
print("\nNext steps:")
print("1. Restart the dashboard")
print("2. Clear caches")
print("3. Verify data is now showing correctly")
print("\nNote: This is a temporary fix. The root cause still needs to be addressed.")