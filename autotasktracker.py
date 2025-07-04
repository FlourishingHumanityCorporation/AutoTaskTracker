#!/usr/bin/env python3
"""
AutoTaskTracker - Main entry point
AI-powered task discovery from screenshots
"""

import sys
import subprocess
import argparse
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from autotasktracker import get_config


def main():
    """Main entry point for AutoTaskTracker."""
    parser = argparse.ArgumentParser(
        description="AutoTaskTracker - AI-powered task discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  autotasktracker.py start              # Start all services (refactored)
  autotasktracker.py dashboard          # Launch task board (refactored)
  autotasktracker.py analytics          # Launch analytics dashboard (refactored)
  autotasktracker.py launcher           # Interactive dashboard launcher
  autotasktracker.py stop               # Stop all services
        """
    )
    
    parser.add_argument(
        'command',
        choices=['start', 'stop', 'dashboard', 'analytics', 'timetracker', 'notifications', 'vlm-monitor', 'status', 'launcher'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run dashboards in headless mode (no browser)'
    )
    
    args = parser.parse_args()
    config = get_config()
    
    if args.command == 'start':
        print("Starting AutoTaskTracker services...")
        # Start memos
        subprocess.run(['memos', 'start'])
        print("✅ Memos backend started")
        
        # Start main dashboard
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_task_board.py',
            '--server.port', str(config.TASK_BOARD_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        
        subprocess.Popen(cmd)
        print(f"✅ Task board started at http://localhost:{config.TASK_BOARD_PORT}")
        
    elif args.command == 'stop':
        print("Stopping AutoTaskTracker services...")
        subprocess.run(['memos', 'stop'])
        subprocess.run(['pkill', '-f', 'streamlit'])
        print("✅ All services stopped")
        
    elif args.command == 'dashboard':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_task_board.py',
            '--server.port', str(config.TASK_BOARD_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'analytics':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_analytics.py',
            '--server.port', str(config.ANALYTICS_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'timetracker':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_timetracker.py',
            '--server.port', str(config.TIMETRACKER_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'notifications':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_notifications.py',
            '--server.port', str(config.NOTIFICATIONS_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'vlm-monitor':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_vlm_monitor.py',
            '--server.port', '8510'
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'launcher':
        # Use the refactored launcher
        from autotasktracker.dashboards.launcher_refactored import DashboardLauncher
        launcher = DashboardLauncher()
        launcher.print_status()
        
    elif args.command == 'status':
        print("Checking AutoTaskTracker status...")
        # Check memos
        try:
            result = subprocess.run(['memos', 'ps'], capture_output=True, text=True)
            print(result.stdout)
        except FileNotFoundError:
            print("❌ Memos not found in PATH. Make sure it's installed and activated.")
        
        # Check dashboards
        result = subprocess.run(['pgrep', '-f', 'streamlit'], capture_output=True)
        if result.returncode == 0:
            print("✅ Streamlit dashboards are running")
        else:
            print("❌ No Streamlit dashboards running")


if __name__ == '__main__':
    main()