#!/usr/bin/env python3
"""
AutoTaskTracker - Main entry point
AI-powered task discovery from screenshots
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

# Configuration import
from autotasktracker.config import get_config


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
        choices=['start', 'stop', 'dashboard', 'analytics', 'timetracker', 'notifications', 'vlm-monitor', 'status', 'launcher', 'stop-dashboard'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run dashboards in headless mode (no browser)'
    )
    
    args = parser.parse_args()
    
    # Configuration setup
    config = get_config()
    
    if args.command == 'start':
        print("Starting AutoTaskTracker services...")
        # Set AutoTaskTracker-specific environment variables (Option 2: Environment-Based)
        env = os.environ.copy()
        env['MEMOS_BASE_DIR'] = '/Users/paulrohde/AutoTaskTracker.memos'
        env['MEMOS_SERVER_PORT'] = '8841'
        env['MEMOS_DATABASE_PATH'] = 'postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker'
        print(f"Using AutoTaskTracker environment configuration")
        subprocess.run(['/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python', '-m', 'memos.commands', 'start'], env=env)
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
        # Use AutoTaskTracker-specific environment variables
        env = os.environ.copy()
        env['MEMOS_BASE_DIR'] = '/Users/paulrohde/AutoTaskTracker.memos'
        env['MEMOS_SERVER_PORT'] = '8841'
        env['MEMOS_DATABASE_PATH'] = 'postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker'
        subprocess.run(['/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python', '-m', 'memos.commands', 'stop'], env=env)
        subprocess.run(['pkill', '-f', 'streamlit'])
        print("✅ All services stopped")
        
    elif args.command == 'stop-dashboard':
        from scripts.dashboard_manager import DashboardManager
        manager = DashboardManager()
        manager.stop_all()
        print("✅ All dashboards stopped")
        
    elif args.command == 'dashboard':
        # Use background dashboard manager
        from scripts.dashboard_manager import DashboardManager
        
        manager = DashboardManager()
        pid = manager.start_dashboard(
            dashboard_type='task_board',
            headless=args.headless
        )
        
        if pid:
            print(f"\n🎉 Task Board dashboard is now running in background!")
            print(f"🌐 Open: http://localhost:{config.TASK_BOARD_PORT}")
            print(f"🆔 Process ID: {pid}")
            print(f"\n📋 Management commands:")
            print(f"  Status:    python scripts/dashboard_manager.py status")
            print(f"  Stop:      python scripts/dashboard_manager.py stop --type task_board")
            print(f"  Stop All:  python scripts/dashboard_manager.py stop-all")
            print(f"\n💡 Dashboard will keep running until you close the browser tab or stop it manually.")
        else:
            print("❌ Failed to start dashboard")
        
    elif args.command == 'analytics':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'autotasktracker/dashboards/analytics.py',
            '--server.port', str(config.ANALYTICS_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'timetracker':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'autotasktracker/dashboards/timetracker.py',
            '--server.port', str(config.TIMETRACKER_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'notifications':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'autotasktracker/dashboards/notifications.py',
            '--server.port', str(config.NOTIFICATIONS_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'vlm-monitor':
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'autotasktracker/dashboards/vlm_monitor.py',
            '--server.port', str(config.VLM_MONITOR_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        subprocess.run(cmd)
        
    elif args.command == 'launcher':
        # Use the refactored launcher
        from autotasktracker.dashboards.launcher import DashboardLauncher
        launcher = DashboardLauncher()
        launcher.print_status()
        
    elif args.command == 'status':
        print("Checking AutoTaskTracker status...")
        # Check memos
        try:
            # Use AutoTaskTracker-specific environment variables
            env = os.environ.copy()
            env['MEMOS_BASE_DIR'] = '/Users/paulrohde/AutoTaskTracker.memos'
            env['MEMOS_SERVER_PORT'] = '8841'
            env['MEMOS_DATABASE_PATH'] = 'postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker'
            result = subprocess.run(['/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python', '-m', 'memos.commands', 'ps'], capture_output=True, text=True, env=env)
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