#!/usr/bin/env python3
"""
AutoTaskTracker - Main entry point
AI-powered task discovery from screenshots
"""

import sys
import subprocess
import argparse
import logging
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from autotasktracker import get_config

logger = logging.getLogger(__name__)


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
    config = get_config()
    
    if args.command == 'start':
        logger.info("Starting AutoTaskTracker services...")
        # Start memos
        subprocess.run(['memos', 'start'])
        logger.info("✅ Memos backend started")
        
        # Start main dashboard
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'run_task_board.py',
            '--server.port', str(config.TASK_BOARD_PORT)
        ]
        if args.headless:
            cmd.extend(['--server.headless', 'true'])
        
        subprocess.Popen(cmd)
        logger.info(f"✅ Task board started at http://localhost:{config.TASK_BOARD_PORT}")
        
    elif args.command == 'stop':
        logger.info("Stopping AutoTaskTracker services...")
        subprocess.run(['memos', 'stop'])
        subprocess.run(['pkill', '-f', 'streamlit'])
        logger.info("✅ All services stopped")
        
    elif args.command == 'stop-dashboard':
        from scripts.dashboard_manager import DashboardManager
        manager = DashboardManager()
        manager.stop_all()
        logger.info("✅ All dashboards stopped")
        
    elif args.command == 'dashboard':
        # Use background dashboard manager
        from scripts.dashboard_manager import DashboardManager
        
        manager = DashboardManager()
        pid = manager.start_dashboard(
            dashboard_type='task_board',
            headless=args.headless
        )
        
        if pid:
            logger.info(f"\n🎉 Task Board dashboard is now running in background!")
            logger.info(f"🌐 Open: http://localhost:{config.TASK_BOARD_PORT}")
            logger.info(f"🆔 Process ID: {pid}")
            logger.info(f"\n📋 Management commands:")
            logger.info(f"  Status:    python scripts/dashboard_manager.py status")
            logger.info(f"  Stop:      python scripts/dashboard_manager.py stop --type task_board")
            logger.info(f"  Stop All:  python scripts/dashboard_manager.py stop-all")
            logger.info(f"\n💡 Dashboard will keep running until you close the browser tab or stop it manually.")
        else:
            logger.error("❌ Failed to start dashboard")
        
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
            '--server.port', '8510'
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
        logger.info("Checking AutoTaskTracker status...")
        # Check memos
        try:
            result = subprocess.run(['memos', 'ps'], capture_output=True, text=True)
            logger.info(result.stdout)
        except FileNotFoundError:
            logger.error("❌ Memos not found in PATH. Make sure it's installed and activated.")
        
        # Check dashboards
        result = subprocess.run(['pgrep', '-f', 'streamlit'], capture_output=True)
        if result.returncode == 0:
            logger.info("✅ Streamlit dashboards are running")
        else:
            logger.info("❌ No Streamlit dashboards running")


if __name__ == '__main__':
    main()