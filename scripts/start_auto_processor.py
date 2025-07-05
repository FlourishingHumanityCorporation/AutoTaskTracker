#!/usr/bin/env python3
"""
Startup script for AutoTaskTracker auto processor.
Handles OCR and task extraction in the background.
"""
import sys
import os
import subprocess
import argparse
import signal
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRIPT_DIR = Path(__file__).parent
AUTO_PROCESSOR_SCRIPT = SCRIPT_DIR / "processing" / "auto_processor.py"
PID_FILE = SCRIPT_DIR / "auto_processor.pid"
LOG_FILE = SCRIPT_DIR / "auto_processor.log"


def start_processor(interval=30, background=True):
    """Start the auto processor."""
    if is_running():
        print("Auto processor is already running")
        return False
    
    cmd = [
        sys.executable,
        str(AUTO_PROCESSOR_SCRIPT),
        "--interval", str(interval)
    ]
    
    if background:
        print(f"Starting auto processor in background (interval: {interval}s)")
        print(f"Log file: {LOG_FILE}")
        
        # Start in background with logging
        with open(LOG_FILE, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        # Save PID
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
        
        print(f"Auto processor started with PID {process.pid}")
        print("Use 'python scripts/start_auto_processor.py stop' to stop")
        return True
    else:
        print(f"Starting auto processor in foreground (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\nAuto processor stopped")
        return True


def stop_processor():
    """Stop the auto processor."""
    if not PID_FILE.exists():
        print("Auto processor is not running (no PID file)")
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Try to terminate gracefully
        os.kill(pid, signal.SIGTERM)
        
        # Wait a bit for graceful shutdown
        time.sleep(2)
        
        # Check if still running
        try:
            os.kill(pid, 0)  # Check if process exists
            print("Process still running, forcing shutdown...")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Process already terminated
        
        PID_FILE.unlink()
        print(f"Auto processor stopped (PID {pid})")
        return True
        
    except (FileNotFoundError, ValueError, ProcessLookupError):
        print("Auto processor was not running")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return False
    except PermissionError:
        print("Permission denied stopping auto processor")
        return False


def is_running():
    """Check if auto processor is running."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        os.kill(pid, 0)
        return True
        
    except (FileNotFoundError, ValueError, ProcessLookupError):
        # Clean up stale PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        return False


def status():
    """Show auto processor status."""
    if is_running():
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        print(f"✅ Auto processor is running (PID {pid})")
        
        # Show log tail if available
        if LOG_FILE.exists():
            print("\nRecent log entries:")
            try:
                with open(LOG_FILE, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-5:]:  # Last 5 lines
                        print(f"   {line.rstrip()}")
            except Exception as e:
                print(f"   Could not read log: {e}")
    else:
        print("❌ Auto processor is not running")
    
    return is_running()


def restart(interval=30):
    """Restart the auto processor."""
    print("Restarting auto processor...")
    stop_processor()
    time.sleep(1)
    return start_processor(interval, background=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='AutoTaskTracker Auto Processor Manager')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'run'],
                        help='Action to perform')
    parser.add_argument('--interval', type=int, default=30,
                        help='Check interval in seconds (default: 30)')
    parser.add_argument('--foreground', action='store_true',
                        help='Run in foreground instead of background')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        success = start_processor(args.interval, background=not args.foreground)
        sys.exit(0 if success else 1)
    elif args.action == 'stop':
        success = stop_processor()
        sys.exit(0 if success else 1)
    elif args.action == 'restart':
        success = restart(args.interval)
        sys.exit(0 if success else 1)
    elif args.action == 'status':
        running = status()
        sys.exit(0 if running else 1)
    elif args.action == 'run':
        # Run single batch
        cmd = [sys.executable, str(AUTO_PROCESSOR_SCRIPT), "--batch"]
        subprocess.run(cmd)


if __name__ == "__main__":
    main()