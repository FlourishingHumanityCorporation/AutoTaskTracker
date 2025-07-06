"""Refactored dashboard launcher using new architecture."""

import subprocess
import sys
import os
import time
from pathlib import Path
import logging

from autotasktracker.config import get_config

logger = logging.getLogger(__name__)

# Dashboard configurations
config = get_config()
DASHBOARD_CONFIGS = {
    'task_board': {
        'module': 'autotasktracker.dashboards.task_board',
        'port': config.TASK_BOARD_PORT,
        'name': 'Task Board',
        'icon': '📋',
        'description': 'Main task tracking and visualization'
    },
    'analytics': {
        'module': 'autotasktracker.dashboards.analytics', 
        'port': config.ANALYTICS_PORT,
        'name': 'Analytics',
        'icon': '📊',
        'description': 'Productivity analytics and insights'
    },
    'timetracker': {
        'module': 'autotasktracker.dashboards.timetracker',
        'port': config.TIMETRACKER_PORT,
        'name': 'Time Tracker',
        'icon': '⏱️',
        'description': 'Detailed time tracking and sessions'
    },
    'notifications': {
        'module': 'autotasktracker.dashboards.notifications',
        'port': config.TIME_TRACKER_PORT,
        'name': 'Notifications',
        'icon': '📬',
        'description': 'Task notifications and alerts'
    },
    'vlm_monitor': {
        'module': 'autotasktracker.dashboards.vlm_monitor',
        'port': config.DAILY_SUMMARY_PORT,
        'name': 'VLM Monitor',
        'icon': '👁️',
        'description': 'Visual language model processing status'
    }
}


class DashboardLauncher:
    """Enhanced dashboard launcher for refactored architecture."""
    
    def __init__(self):
        self.config = get_config()
        self.running_processes = {}
        
    def is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((get_config().SERVER_HOST, port))
                return True
        except OSError:
            return False
            
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        # Check if database is accessible
        try:
            from autotasktracker.core import DatabaseManager
            db = DatabaseManager()
            if not db.test_connection():
                logger.error("Database connection failed")
                return False
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False
            
        # Check if required packages are installed
        try:
            import streamlit
            import plotly
            import pandas
        except ImportError as e:
            logger.error(f"Missing required package: {e}")
            return False
            
        return True
        
    def launch_dashboard(self, dashboard_name: str) -> bool:
        """Launch a specific dashboard."""
        if dashboard_name not in DASHBOARD_CONFIGS:
            logger.error(f"Unknown dashboard: {dashboard_name}")
            return False
            
        config = DASHBOARD_CONFIGS[dashboard_name]
        
        # Check if port is available
        if not self.is_port_available(config['port']):
            logger.warning(f"Port {config['port']} is already in use")
            # Try to find the dashboard in running processes
            if dashboard_name in self.running_processes:
                proc = self.running_processes[dashboard_name]
                if proc.poll() is None:  # Still running
                    logger.info(f"Dashboard {dashboard_name} already running on port {config['port']}")
                    return True
                    
        try:
            # Launch dashboard
            cmd = [
                sys.executable, '-m', 'streamlit', 'run',
                f"{config['module'].replace('.', '/')}.py",
                '--server.port', str(config['port']),
                '--server.headless', 'true',
                '--server.enableCORS', 'false',
                '--server.enableXsrfProtection', 'false'
            ]
            
            logger.info(f"Launching {config['name']} on port {config['port']}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.running_processes[dashboard_name] = proc
            
            # Wait a moment to see if it starts successfully
            time.sleep(2)
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                logger.error(f"Dashboard {dashboard_name} failed to start:")
                logger.error(f"stdout: {stdout}")
                logger.error(f"stderr: {stderr}")
                return False
                
            logger.info(f"✅ {config['name']} started successfully on http://{get_config().SERVER_HOST}:{config['port']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch dashboard {dashboard_name}: {e}")
            return False
            
    def launch_all(self) -> dict:
        """Launch all dashboards."""
        results = {}
        
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed")
            return results
            
        logger.info("🚀 Launching all refactored dashboards...")
        
        for dashboard_name, config in DASHBOARD_CONFIGS.items():
            logger.info(f"Starting {config['name']}...")
            results[dashboard_name] = self.launch_dashboard(dashboard_name)
            time.sleep(1)  # Stagger launches
            
        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"\n📊 Launch Summary: {successful}/{total} dashboards started successfully")
        
        if successful > 0:
            logger.info("\n🌐 Available Dashboards:")
            for dashboard_name, success in results.items():
                if success:
                    config = DASHBOARD_CONFIGS[dashboard_name]
                    logger.info(f"  {config['icon']} {config['name']}: http://{get_config().SERVER_HOST}:{config['port']}")
                    
        return results
        
    def stop_dashboard(self, dashboard_name: str) -> bool:
        """Stop a specific dashboard."""
        if dashboard_name not in self.running_processes:
            logger.warning(f"Dashboard {dashboard_name} not tracked")
            return False
            
        proc = self.running_processes[dashboard_name]
        try:
            proc.terminate()
            proc.wait(timeout=5)
            logger.info(f"✅ Stopped {dashboard_name}")
            del self.running_processes[dashboard_name]
            return True
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.warning(f"Force killed {dashboard_name}")
            del self.running_processes[dashboard_name]
            return True
        except Exception as e:
            logger.error(f"Failed to stop {dashboard_name}: {e}")
            return False
            
    def stop_all(self) -> dict:
        """Stop all running dashboards."""
        results = {}
        
        for dashboard_name in list(self.running_processes.keys()):
            results[dashboard_name] = self.stop_dashboard(dashboard_name)
            
        return results
        
    def status(self) -> dict:
        """Get status of all dashboards."""
        status = {}
        
        for dashboard_name, config in DASHBOARD_CONFIGS.items():
            if dashboard_name in self.running_processes:
                proc = self.running_processes[dashboard_name]
                is_running = proc.poll() is None
            else:
                is_running = False
                
            port_available = self.is_port_available(config['port'])
            
            # If port is not available but we don't have the process, 
            # assume external process is running
            if not port_available and not is_running:
                is_running = True  # External process detected
            
            status[dashboard_name] = {
                'name': config['name'],
                'port': config['port'],
                'running': is_running,
                'port_available': port_available,
                'url': f"http://{get_config().SERVER_HOST}:{config['port']}" if is_running else None
            }
            
        return status
        
    def print_status(self):
        """Print dashboard status in a formatted way."""
        status = self.status()
        
        logger.info("\n📊 Dashboard Status:")
        logger.info("=" * 60)
        
        for dashboard_name, info in status.items():
            icon = "🟢" if info['running'] else "🔴"
            status_text = "Running" if info['running'] else "Stopped"
            port_text = f"Port {info['port']}"
            
            # Show external process indication
            if not info['port_available'] and info['running']:
                if dashboard_name not in self.running_processes:
                    status_text += " (External)"
                
            logger.info(f"{icon} {info['name']:<20} {status_text:<15} {port_text}")
            
            if info['url']:
                logger.info(f"   └─ {info['url']}")
                
        logger.info("")


def main():
    """Main launcher function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoTaskTracker Dashboard Launcher (Refactored)")
    parser.add_argument('action', choices=['start', 'stop', 'status', 'launch'], 
                       help="Action to perform")
    parser.add_argument('--dashboard', '-d', choices=list(DASHBOARD_CONFIGS.keys()),
                       help="Specific dashboard to operate on")
    parser.add_argument('--verbose', '-v', action='store_true',
                       help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    launcher = DashboardLauncher()
    
    if args.action == 'start':
        if args.dashboard:
            launcher.launch_dashboard(args.dashboard)
        else:
            launcher.launch_all()
            
    elif args.action == 'stop':
        if args.dashboard:
            launcher.stop_dashboard(args.dashboard)
        else:
            launcher.stop_all()
            
    elif args.action == 'status':
        launcher.print_status()
        
    elif args.action == 'launch':
        # Interactive mode
        launcher.print_status()
        logger.info("\nWhich dashboard would you like to launch?")
        for i, (name, config) in enumerate(DASHBOARD_CONFIGS.items(), 1):
            logger.info(f"{i}. {config['icon']} {config['name']} - {config['description']}")
            
        try:
            choice = int(input("\nEnter number (or 0 for all): "))
            if choice == 0:
                launcher.launch_all()
            elif 1 <= choice <= len(DASHBOARD_CONFIGS):
                dashboard_name = list(DASHBOARD_CONFIGS.keys())[choice - 1]
                launcher.launch_dashboard(dashboard_name)
            else:
                logger.warning("Invalid choice")
        except (ValueError, KeyboardInterrupt):
            logger.info("Cancelled")


if __name__ == "__main__":
    main()