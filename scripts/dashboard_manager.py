#!/usr/bin/env python3
"""
Dashboard Manager - Background dashboard controller for AutoTaskTracker
Allows running dashboards in background with monitoring and control.
"""

import os
import sys
import subprocess
import signal
import time
import json
import psutil
from pathlib import Path
from datetime import datetime
import logging

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autotasktracker.utils.config import get_config
from autotasktracker.utils.debug_capture import start_debug_session, stop_debug_session

logger = logging.getLogger(__name__)


class DashboardManager:
    """Manager for running AutoTaskTracker dashboards in background."""
    
    def __init__(self):
        self.config = get_config()
        self.processes = {}
        self.debug_sessions = {}
        self.pid_file = Path.home() / ".autotasktracker_pids.json"
        
    def start_dashboard(self, dashboard_type="task_board", port=None, headless=False):
        """Start a dashboard in background.
        
        Args:
            dashboard_type: Type of dashboard (task_board, analytics, etc.)
            port: Port to run on (uses default if None)
            headless: Whether to run headless
            
        Returns:
            Process ID of started dashboard
        """
        if port is None:
            port = self.config.TASK_BOARD_PORT if dashboard_type == "task_board" else self.config.ANALYTICS_PORT
        
        # Check if already running
        if self._is_port_in_use(port):
            print(f"⚠️ Port {port} already in use")
            return None
        
        # Start debug capture
        print(f"🐛 Starting debug capture for {dashboard_type}...")
        debug_session = start_debug_session()
        
        # Build command - use venv Python to ensure correct dependencies
        venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python"
        python_exe = str(venv_python) if venv_python.exists() else sys.executable
        
        dashboard_file = f"autotasktracker/dashboards/{dashboard_type}.py"
        cmd = [
            python_exe, '-m', 'streamlit', 'run',
            dashboard_file,
            '--server.port', str(port),
            '--server.runOnSave', 'false',  # Prevent auto-reload
        ]
        
        if headless:
            cmd.extend(['--server.headless', 'true'])
        
        # Start process
        print(f"🚀 Starting {dashboard_type} dashboard on port {port}...")
        
        try:
            # Use subprocess.Popen for background execution
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait a moment to see if it starts successfully
            time.sleep(3)
            
            if process.poll() is None:  # Still running
                # Store process info
                self.processes[dashboard_type] = {
                    'pid': process.pid,
                    'port': port,
                    'started_at': datetime.now().isoformat(),
                    'command': ' '.join(cmd)
                }
                
                self.debug_sessions[dashboard_type] = debug_session
                
                # Save to persistent storage
                self._save_process_info()
                
                print(f"✅ {dashboard_type} dashboard started successfully!")
                print(f"📱 URL: http://localhost:{port}")
                print(f"🆔 PID: {process.pid}")
                print(f"📸 Debug capture: {debug_session.session_dir}")
                
                return process.pid
            else:
                # Process failed to start
                stdout, stderr = process.communicate()
                print(f"❌ Failed to start {dashboard_type} dashboard")
                print(f"Error: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting dashboard: {e}")
            return None
    
    def stop_dashboard(self, dashboard_type=None, pid=None):
        """Stop a running dashboard.
        
        Args:
            dashboard_type: Type of dashboard to stop
            pid: Specific PID to stop
        """
        if pid:
            # Stop specific PID
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                print(f"✅ Stopped process {pid}")
            except Exception as e:
                print(f"❌ Error stopping PID {pid}: {e}")
        
        elif dashboard_type:
            # Stop specific dashboard type
            if dashboard_type in self.processes:
                pid = self.processes[dashboard_type]['pid']
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    
                    # Stop debug capture
                    if dashboard_type in self.debug_sessions:
                        summary = stop_debug_session()
                        print(f"🐛 Debug session ended: {summary['screenshot_count']} screenshots")
                    
                    # Remove from tracking
                    del self.processes[dashboard_type]
                    if dashboard_type in self.debug_sessions:
                        del self.debug_sessions[dashboard_type]
                    
                    self._save_process_info()
                    print(f"✅ Stopped {dashboard_type} dashboard")
                    
                except Exception as e:
                    print(f"❌ Error stopping {dashboard_type}: {e}")
            else:
                print(f"⚠️ {dashboard_type} dashboard not found in running processes")
    
    def stop_all(self):
        """Stop all running dashboards."""
        dashboard_types = list(self.processes.keys())
        for dashboard_type in dashboard_types:
            self.stop_dashboard(dashboard_type)
        
        # Also kill any remaining streamlit processes
        try:
            subprocess.run(['pkill', '-f', 'streamlit'], check=False)
            print("🧹 Cleaned up any remaining streamlit processes")
        except Exception:
            pass
    
    def status(self):
        """Show status of all dashboards."""
        self._load_process_info()
        
        if not self.processes:
            print("📋 No dashboards currently running")
            return
        
        print("📋 Running Dashboards:")
        print("-" * 60)
        
        for dashboard_type, info in self.processes.items():
            pid = info['pid']
            port = info['port']
            started_at = info['started_at']
            
            # Check if process is still alive
            try:
                psutil.Process(pid)
                status = "🟢 Running"
                url = f"http://localhost:{port}"
            except psutil.NoSuchProcess:
                status = "🔴 Dead"
                url = "N/A"
                
            print(f"{dashboard_type.ljust(15)} | PID: {str(pid).ljust(6)} | Port: {str(port).ljust(4)} | {status}")
            print(f"{''.ljust(15)} | URL: {url}")
            print(f"{''.ljust(15)} | Started: {started_at}")
            print()
    
    def _is_port_in_use(self, port):
        """Check if a port is in use."""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0
        except Exception:
            return False
    
    def _save_process_info(self):
        """Save process information to persistent storage."""
        try:
            with open(self.pid_file, 'w') as f:
                json.dump(self.processes, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save process info: {e}")
    
    def _load_process_info(self):
        """Load process information from persistent storage."""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    stored_processes = json.load(f)
                
                # Verify processes are still alive
                for dashboard_type, info in stored_processes.items():
                    try:
                        psutil.Process(info['pid'])
                        self.processes[dashboard_type] = info
                    except psutil.NoSuchProcess:
                        # Process died, remove from tracking
                        pass
                        
        except Exception as e:
            logger.error(f"Failed to load process info: {e}")


def main():
    """Main CLI interface for dashboard manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoTaskTracker Dashboard Manager")
    parser.add_argument('command', choices=['start', 'stop', 'status', 'stop-all'], 
                       help='Command to execute')
    parser.add_argument('--type', default='task_board', 
                       choices=['task_board', 'analytics'], 
                       help='Dashboard type')
    parser.add_argument('--port', type=int, help='Port to run on')
    parser.add_argument('--headless', action='store_true', help='Run headless')
    parser.add_argument('--pid', type=int, help='Specific PID to stop')
    
    args = parser.parse_args()
    
    manager = DashboardManager()
    
    if args.command == 'start':
        pid = manager.start_dashboard(
            dashboard_type=args.type,
            port=args.port,
            headless=args.headless
        )
        if pid:
            print(f"\n🎉 Dashboard running! Close browser tab to stop or use:")
            print(f"python {__file__} stop --type {args.type}")
    
    elif args.command == 'stop':
        if args.pid:
            manager.stop_dashboard(pid=args.pid)
        else:
            manager.stop_dashboard(dashboard_type=args.type)
    
    elif args.command == 'stop-all':
        manager.stop_all()
    
    elif args.command == 'status':
        manager.status()


if __name__ == "__main__":
    main()