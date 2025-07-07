#!/usr/bin/env python
"""Fix the timezone offset to use correct +7h instead of +8h."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== FIXING TIMEZONE OFFSET ===\n")

# The correct offset is +7 hours (PDT to UTC interpretation error)
# Data at 19:15 PDT is stored as 19:15 "UTC" but should be 02:15 UTC
# So it's 19:15 - 02:15 = 17:00 difference, but since we're in PDT (-7), 
# the data is effectively stored as local time without timezone = +7h ahead

repo_file = "autotasktracker/dashboards/data/repositories.py"

# Read the file
with open(repo_file, 'r') as f:
    content = f.read()

# Replace all instances of timedelta(hours=8) with timedelta(hours=7)
replacements = [
    ("timedelta(hours=8)", "timedelta(hours=7)"),
]

changes_made = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        changes_made += content.count(new)
        print(f"✓ Replaced '{old}' with '{new}'")

# Write back
with open(repo_file, 'w') as f:
    f.write(content)

print(f"\n✓ Fixed {changes_made} timezone offset references")
print("Note: The correct offset is +7h because PDT (UTC-7) is being stored as if it were UTC")

# Also fix the display offset
display_file = "autotasktracker/dashboards/components/ai_task_display.py"

with open(display_file, 'r') as f:
    content = f.read()

# Replace display offset
content = content.replace("timedelta(hours=8)", "timedelta(hours=7)")

with open(display_file, 'w') as f:
    f.write(content)

print("✓ Fixed display timezone offset")
print("\nNext: Restart dashboard and verify times are correct")