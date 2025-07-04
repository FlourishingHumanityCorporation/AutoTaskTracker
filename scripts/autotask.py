#!/usr/bin/env python3
"""
AutoTaskTracker - Unified launcher and manager
Handles all services and provides system tray integration for live use
"""

import sys
import os
import subprocess
import time
import signal
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
import threading
import webbrowser

# Add venv to path if it exists
venv_path = Path(__file__).parent / "venv"
if venv_path.exists():
    sys.path.insert(0, str(venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"))

try:
    import psutil
except ImportError:
    print("Installing required dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "pystray", "pillow"])
    import psutil

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("System tray support not available. Install with: pip install pystray pillow")

class AutoTaskTracker:
    def __init__(self):
        self.home_dir = Path.home()
        self.memos_dir = self.home_dir / ".memos"
        self.project_dir = Path(__file__).parent
        self.venv_bin = self.project_dir / "venv" / "bin"
        self.processes = {}
        self.tray_icon = None
        self.running = True
        
        # Service configurations
        self.services = {
            "memos": {
                "name": "Memos Backend",
                "check_cmd": ["pgrep", "-f", "memos"],
                "start_cmd": ["memos", "start"],
                "stop_cmd": ["memos", "stop"],
                "required": True
            },
            "task_board": {
                "name": "Task Board",
                "port": 8502,
                "script": "task_board.py",
                "url": "http://localhost:8502",
                "required": True
            },
            "analytics": {
                "name": "Analytics Dashboard", 
                "port": 8503,
                "script": "task_analytics.py",
                "url": "http://localhost:8503",
                "required": False
            },
            "timetracker": {
                "name": "Time Tracker",
                "port": 8504,
                "script": "task_timetracker.py",
                "url": "http://localhost:8504",
                "required": False
            },
            "smarttracker": {
                "name": "Smart Time Tracker",
                "port": 8505,
                "script": "smart_time_tracker.py",
                "url": "http://localhost:8505",
                "required": False
            },
            "adaptive": {
                "name": "Adaptive AI Tracker",
                "port": 8506,
                "script": "adaptive_time_tracker.py",
                "url": "http://localhost:8506",
                "required": False
            }
        }
        
    def create_tray_icon(self):
        """Create system tray icon"""
        # Create a simple icon
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        # Draw a checkmark
        draw.line([(10, 35), (25, 50), (54, 20)], fill='green', width=6)
        return image
        
    def check_memos_running(self):
        """Check if memos services are running"""
        try:
            result = subprocess.run(["pgrep", "-f", "memos"], capture_output=True)
            return result.returncode == 0
        except:
            return False
            
    def start_memos(self):
        """Start memos backend services"""
        if not self.check_memos_running():
            print("Starting Memos backend...")
            subprocess.run(["memos", "start"], capture_output=True)
            time.sleep(3)  # Give it time to start
            if self.check_memos_running():
                print("✅ Memos started successfully")
                return True
            else:
                print("❌ Failed to start Memos")
                return False
        else:
            print("✅ Memos already running")
            return True
            
    def stop_memos(self):
        """Stop memos backend services"""
        print("Stopping Memos backend...")
        subprocess.run(["memos", "stop"], capture_output=True)
        
    def start_streamlit(self, name, script, port):
        """Start a Streamlit dashboard"""
        script_path = self.project_dir / script
        if not script_path.exists():
            print(f"❌ Script not found: {script}")
            return None
            
        cmd = [
            str(self.venv_bin / "streamlit"),
            "run",
            str(script_path),
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        print(f"Starting {name} on port {port}...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for it to start
        start_time = time.time()
        while time.time() - start_time < 20:
            try:
                import requests
                if requests.get(f"http://localhost:{port}").status_code == 200:
                    print(f"✅ {name} started successfully")
                    return process
            except:
                pass
            time.sleep(1)
            
        print(f"❌ {name} failed to start")
        process.terminate()
        return None
        
    def stop_streamlit(self, process):
        """Stop a Streamlit process"""
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
            
    def start_all(self):
        """Start all services"""
        print("\n🚀 Starting AutoTaskTracker services...\n")
        
        # Start memos first
        if not self.start_memos():
            print("Failed to start Memos. Exiting.")
            return False
            
        # Start Streamlit dashboards
        self.processes["task_board"] = self.start_streamlit(
            "Task Board", 
            "task_board.py",
            self.services["task_board"]["port"]
        )
        
        self.processes["analytics"] = self.start_streamlit(
            "Analytics Dashboard",
            "task_analytics.py", 
            self.services["analytics"]["port"]
        )
        
        self.processes["timetracker"] = self.start_streamlit(
            "Time Tracker",
            "task_timetracker.py",
            self.services["timetracker"]["port"]
        )
        
        print("\n✅ All services started successfully!")
        print(f"\n📋 Task Board: {self.services['task_board']['url']}")
        print(f"📊 Analytics: {self.services['analytics']['url']}")
        print(f"⏱️  Time Tracker: {self.services['timetracker']['url']}")
        print(f"🗄️ Memos API: http://localhost:8839\n")
        
        return True
        
    def stop_all(self):
        """Stop all services"""
        print("\n🛑 Stopping all services...\n")
        
        # Stop Streamlit processes
        for name, process in self.processes.items():
            if process:
                print(f"Stopping {name}...")
                self.stop_streamlit(process)
                
        # Stop memos
        self.stop_memos()
        
        print("\n✅ All services stopped\n")
        
    def get_status(self):
        """Get status of all services"""
        status = {
            "memos": self.check_memos_running(),
            "task_board": False,
            "analytics": False,
            "stats": self.get_stats()
        }
        
        # Check Streamlit services
        for service_name in ["task_board", "analytics", "timetracker"]:
            if service_name in self.processes and self.processes[service_name]:
                status[service_name] = self.processes[service_name].poll() is None
                
        return status
        
    def get_stats(self):
        """Get system statistics"""
        stats = {
            "screenshots": 0,
            "ocr_results": 0,
            "storage_mb": 0,
            "last_capture": None
        }
        
        try:
            # Count screenshots
            screenshots_dir = self.memos_dir / "screenshots"
            if screenshots_dir.exists():
                for date_dir in screenshots_dir.iterdir():
                    if date_dir.is_dir():
                        stats["screenshots"] += len(list(date_dir.glob("*.webp"))) + len(list(date_dir.glob("*.png")))
                        
            # Get storage size
            if screenshots_dir.exists():
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(screenshots_dir):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)
                stats["storage_mb"] = total_size / (1024 * 1024)
                
            # Get database stats
            db_path = self.memos_dir / "database.db"
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Count OCR results
                cursor.execute("SELECT COUNT(*) FROM metadata_entries WHERE key = 'ocr_result'")
                stats["ocr_results"] = cursor.fetchone()[0]
                
                # Get last capture time
                cursor.execute("SELECT MAX(created_at) FROM entities WHERE file_type_group = 'image'")
                last_capture = cursor.fetchone()[0]
                if last_capture:
                    stats["last_capture"] = datetime.fromisoformat(last_capture)
                    
                conn.close()
                
        except Exception as e:
            print(f"Error getting stats: {e}")
            
        return stats
        
    def show_status(self):
        """Display current status"""
        status = self.get_status()
        stats = status["stats"]
        
        print("\n📊 AutoTaskTracker Status\n")
        print("Services:")
        print(f"  Memos Backend: {'✅ Running' if status['memos'] else '❌ Stopped'}")
        print(f"  Task Board: {'✅ Running' if status['task_board'] else '❌ Stopped'}")
        print(f"  Analytics: {'✅ Running' if status['analytics'] else '❌ Stopped'}")
        print(f"  Time Tracker: {'✅ Running' if status.get('timetracker', False) else '❌ Stopped'}")
        
        print(f"\nStatistics:")
        print(f"  Screenshots: {stats['screenshots']:,}")
        print(f"  OCR Results: {stats['ocr_results']:,}")
        print(f"  Storage Used: {stats['storage_mb']:.1f} MB")
        
        if stats['last_capture']:
            time_ago = datetime.now() - stats['last_capture']
            seconds = abs(time_ago.total_seconds())
            if seconds < 60:
                print(f"  Last Capture: {int(seconds)} seconds ago")
            elif seconds < 3600:
                print(f"  Last Capture: {int(seconds / 60)} minutes ago")
            else:
                print(f"  Last Capture: {int(seconds / 3600)} hours ago")
        print()
        
    def cleanup_old_data(self, days=7):
        """Clean up old screenshots and data"""
        print(f"\n🧹 Cleaning up data older than {days} days...\n")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        freed_space = 0
        
        screenshots_dir = self.memos_dir / "screenshots"
        if screenshots_dir.exists():
            for date_dir in screenshots_dir.iterdir():
                if date_dir.is_dir():
                    try:
                        # Parse date from directory name (YYYYMMDD)
                        dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                        if dir_date < cutoff_date:
                            # Calculate size before deletion
                            for file in date_dir.iterdir():
                                freed_space += file.stat().st_size
                                deleted_count += 1
                            # Remove directory
                            import shutil
                            shutil.rmtree(date_dir)
                            print(f"  Deleted {date_dir.name}")
                    except:
                        pass
                        
        print(f"\n✅ Cleanup complete:")
        print(f"  Files deleted: {deleted_count}")
        print(f"  Space freed: {freed_space / (1024 * 1024):.1f} MB\n")
        
    def open_dashboard(self, dashboard="task_board"):
        """Open dashboard in browser"""
        if dashboard in self.services:
            url = self.services[dashboard].get("url")
            if url:
                webbrowser.open(url)
                
    def run_tray(self):
        """Run system tray icon"""
        if not TRAY_AVAILABLE:
            print("System tray not available. Running in console mode.")
            self.run_console()
            return
            
        def on_quit():
            self.running = False
            self.stop_all()
            if self.tray_icon:
                self.tray_icon.stop()
                
        def on_open_task_board():
            self.open_dashboard("task_board")
            
        def on_open_analytics():
            self.open_dashboard("analytics")
            
        def on_open_timetracker():
            self.open_dashboard("timetracker")
            
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem("Task Board", on_open_task_board),
            pystray.MenuItem("Analytics", on_open_analytics),
            pystray.MenuItem("Time Tracker", on_open_timetracker),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Status", lambda: self.show_status()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit)
        )
        
        # Create icon
        image = self.create_tray_icon()
        self.tray_icon = pystray.Icon(
            "AutoTaskTracker",
            image,
            "AutoTaskTracker - Click for options",
            menu
        )
        
        # Start services
        self.start_all()
        
        # Run icon
        print("AutoTaskTracker running in system tray...")
        self.tray_icon.run()
        
    def run_console(self):
        """Run in console mode"""
        self.start_all()
        
        print("\nAutoTaskTracker is running. Press Ctrl+C to stop.\n")
        print("Commands:")
        print("  status - Show current status")
        print("  open task - Open task board")
        print("  open analytics - Open analytics dashboard")
        print("  open time - Open time tracker")
        print("  cleanup - Clean up old data")
        print("  quit - Stop all services and exit\n")
        
        try:
            while self.running:
                try:
                    cmd = input("> ").strip().lower()
                    if cmd == "quit":
                        break
                    elif cmd == "status":
                        self.show_status()
                    elif cmd == "open task":
                        self.open_dashboard("task_board")
                    elif cmd == "open analytics":
                        self.open_dashboard("analytics")
                    elif cmd == "open time":
                        self.open_dashboard("timetracker")
                    elif cmd == "cleanup":
                        self.cleanup_old_data()
                    elif cmd:
                        print("Unknown command. Type 'quit' to exit.")
                except EOFError:
                    break
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            self.stop_all()

def main():
    parser = argparse.ArgumentParser(description="AutoTaskTracker - AI-powered task discovery")
    parser.add_argument("command", nargs="?", default="start",
                       choices=["start", "stop", "status", "cleanup", "console"],
                       help="Command to execute")
    parser.add_argument("--days", type=int, default=7,
                       help="Days to keep data (for cleanup command)")
    parser.add_argument("--no-tray", action="store_true",
                       help="Run without system tray")
    
    args = parser.parse_args()
    
    tracker = AutoTaskTracker()
    
    if args.command == "start":
        if args.no_tray or not TRAY_AVAILABLE:
            tracker.run_console()
        else:
            tracker.run_tray()
    elif args.command == "stop":
        tracker.stop_all()
    elif args.command == "status":
        tracker.show_status()
    elif args.command == "cleanup":
        tracker.cleanup_old_data(args.days)
    elif args.command == "console":
        tracker.run_console()

if __name__ == "__main__":
    main()