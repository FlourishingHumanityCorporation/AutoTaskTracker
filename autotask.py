#!/usr/bin/env python3
"""
AutoTaskTracker - Alternative entry point that works with PostgreSQL
This bypasses the complex import timeout issues in the main package.
"""

import subprocess
import sys
import argparse
from pathlib import Path

def launch_task_board():
    """Launch the task board dashboard."""
    print("Starting AutoTaskTracker Task Board...")
    cmd = ["python", "autotasktracker.py", "dashboard", "--headless"]
    return subprocess.run(cmd)

def launch_analytics():
    """Launch analytics dashboard."""
    print("Starting AutoTaskTracker Analytics...")
    cmd = ["python", "autotasktracker.py", "analytics", "--headless"]
    return subprocess.run(cmd)

def launch_timetracker():
    """Launch time tracker dashboard."""
    print("Starting AutoTaskTracker Time Tracker...")
    cmd = ["python", "autotasktracker.py", "timetracker", "--headless"]
    return subprocess.run(cmd)

def show_status():
    """Show system status."""
    print("AutoTaskTracker Status:")
    print("- Backend: PostgreSQL")
    print("- Task Board: Available via 'python autotask.py dashboard'")
    print("- Analytics: Available via 'python autotask.py analytics'")
    print("- Time Tracker: Available via 'python autotask.py timetracker'")
    
    # Test PostgreSQL connection
    try:
        from autotasktracker.config import get_config
        config = get_config()
        
        if config.test_database_connection():
            print("- PostgreSQL: ✅ Connected")
        else:
            print("- PostgreSQL: ❌ Connection failed")
    except Exception as e:
        print(f"- PostgreSQL: ❌ Error: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AutoTaskTracker - PostgreSQL-compatible launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python autotask.py dashboard     # Launch task board
  python autotask.py analytics     # Launch analytics dashboard  
  python autotask.py timetracker   # Launch time tracker dashboard
  python autotask.py status        # Show system status
  python launch_dashboard.py       # Alternative launcher
        """
    )
    
    parser.add_argument(
        'command',
        choices=['dashboard', 'analytics', 'timetracker', 'status', 'test'],
        help='Command to execute'
    )
    
    args = parser.parse_args()
    
    if args.command == 'dashboard':
        return launch_task_board().returncode
    elif args.command == 'analytics':
        return launch_analytics().returncode
    elif args.command == 'timetracker':
        return launch_timetracker().returncode
    elif args.command == 'status':
        show_status()
        return 0
    elif args.command == 'test':
        print("Testing PostgreSQL connection...")
        try:
            from autotasktracker.core.database import DatabaseManager
            
            db = DatabaseManager()
            entity_count = db.get_entity_count()
            metadata_count = db.get_metadata_count()
            
            print(f"✅ PostgreSQL connection successful")
            print(f"   Entities: {entity_count:,}")
            print(f"   Metadata: {metadata_count:,}")
            return 0
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(main())