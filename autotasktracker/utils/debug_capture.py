"""
Debug screenshot capture utility for AutoTaskTracker dashboard debugging.

Automatically captures screenshots during app execution for debugging purposes.
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess
import threading

from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class DebugCapture:
    """Automated screenshot capture for dashboard debugging."""
    
    def __init__(self, capture_dir: Optional[str] = None):
        """Initialize debug capture system.
        
        Args:
            capture_dir: Directory to save debug screenshots
        """
        if capture_dir is None:
            capture_dir = Path.home() / ".autotasktracker_debug"
        
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.capture_dir / f"session_{self.session_id}"
        self.session_dir.mkdir(exist_ok=True)
        
        self.is_capturing = False
        self.capture_thread = None
        
        logger.info(f"Debug capture initialized: {self.session_dir}")
    
    def capture_screenshot(self, label: str = "") -> Optional[str]:
        """Capture a single screenshot with optional label.
        
        Args:
            label: Optional label for the screenshot
            
        Returns:
            Path to captured screenshot or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{timestamp}_{label}.png" if label else f"{timestamp}.png"
            filepath = self.session_dir / filename
            
            # Use macOS screencapture utility
            result = subprocess.run([
                "screencapture", 
                "-x",  # No sound
                "-t", "png",  # PNG format
                str(filepath)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.debug(f"Screenshot captured: {filepath}")
                return str(filepath)
            else:
                logger.warning(f"Screenshot failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    def capture_browser_window(self, url: str = None) -> Optional[str]:
        """Capture just the browser window showing the dashboard.
        
        Args:
            url: URL of the dashboard to capture
            
        Returns:
            Path to captured screenshot or None if failed
        """
        if url is None:
            url = get_config().get_service_url('task_board')
        
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{timestamp}_dashboard.png"
            filepath = self.session_dir / filename
            
            # Try to capture specific browser window
            # First, get the window ID of the browser with our URL
            result = subprocess.run([
                "osascript", "-e",
                f'''
                tell application "Google Chrome"
                    set windowIndex to 0
                    repeat with w from 1 to count of windows
                        repeat with t from 1 to count of tabs in window w
                            if URL of tab t of window w contains "{url.replace('http://', '')}" then
                                set windowIndex to w
                                exit repeat
                            end if
                        end repeat
                        if windowIndex > 0 then exit repeat
                    end repeat
                    if windowIndex > 0 then
                        set index of window windowIndex to 1
                        activate
                    end if
                end tell
                '''
            ], capture_output=True, text=True, timeout=5)
            
            # Small delay for window to come to front
            time.sleep(0.5)
            
            # Capture the screen
            result = subprocess.run([
                "screencapture", 
                "-x",  # No sound
                "-t", "png",  # PNG format
                str(filepath)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"Dashboard screenshot captured: {filepath}")
                return str(filepath)
            else:
                # Fallback to full screen capture
                return self.capture_screenshot("dashboard_fallback")
                
        except Exception as e:
            logger.warning(f"Browser capture failed, using fallback: {e}")
            return self.capture_screenshot("dashboard_fallback")
    
    def start_periodic_capture(self, interval: int = 30, label_prefix: str = "periodic"):
        """Start periodic screenshot capture in background thread.
        
        Args:
            interval: Seconds between captures
            label_prefix: Prefix for periodic screenshot labels
        """
        if self.is_capturing:
            logger.warning("Periodic capture already running")
            return
        
        self.is_capturing = True
        
        def capture_loop():
            counter = 0
            while self.is_capturing:
                try:
                    counter += 1
                    label = f"{label_prefix}_{counter:03d}"
                    self.capture_screenshot(label)
                    
                    # Wait for interval or until stopped
                    for _ in range(interval * 10):  # Check every 0.1s
                        if not self.is_capturing:
                            break
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Error in capture loop: {e}")
                    time.sleep(1)
        
        self.capture_thread = threading.Thread(target=capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info(f"Started periodic capture every {interval}s")
    
    def stop_periodic_capture(self):
        """Stop periodic screenshot capture."""
        if self.is_capturing:
            self.is_capturing = False
            if self.capture_thread:
                self.capture_thread.join(timeout=5)
            logger.info("Stopped periodic capture")
    
    def capture_dashboard_lifecycle(self, event: str):
        """Capture screenshot at specific dashboard lifecycle events.
        
        Args:
            event: Lifecycle event name (startup, loaded, error, etc.)
        """
        label = f"lifecycle_{event}"
        path = self.capture_screenshot(label)
        
        if path:
            logger.info(f"Captured {event} event: {path}")
    
    def get_session_summary(self) -> dict:
        """Get summary of current debug session.
        
        Returns:
            Dictionary with session information
        """
        screenshots = list(self.session_dir.glob("*.png"))
        
        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "screenshot_count": len(screenshots),
            "screenshots": [str(p) for p in screenshots],
            "duration_minutes": self._get_session_duration(),
            "is_capturing": self.is_capturing
        }
    
    def _get_session_duration(self) -> float:
        """Calculate session duration in minutes."""
        start_time = datetime.strptime(self.session_id, "%Y%m%d_%H%M%S")
        duration = datetime.now() - start_time
        return duration.total_seconds() / 60
    
    def cleanup_old_sessions(self, keep_days: int = 7):
        """Clean up old debug sessions.
        
        Args:
            keep_days: Number of days to keep sessions
        """
        try:
            cutoff = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            for session_dir in self.capture_dir.glob("session_*"):
                if session_dir.is_dir() and session_dir.stat().st_mtime < cutoff:
                    import shutil
                    shutil.rmtree(session_dir)
                    logger.info(f"Cleaned up old session: {session_dir}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")


# Global debug capture instance
_debug_capture: Optional[DebugCapture] = None


def get_debug_capture() -> DebugCapture:
    """Get the global debug capture instance."""
    global _debug_capture
    if _debug_capture is None:
        _debug_capture = DebugCapture()
    return _debug_capture


def capture_event(event: str):
    """Convenience function to capture lifecycle events."""
    get_debug_capture().capture_dashboard_lifecycle(event)


def capture_dashboard():
    """Convenience function to capture dashboard screenshot."""
    return get_debug_capture().capture_browser_window()


def start_debug_session():
    """Start a new debug capture session."""
    capture = get_debug_capture()
    capture.capture_dashboard_lifecycle("session_start")
    capture.start_periodic_capture(interval=30)
    return capture


def stop_debug_session():
    """Stop the current debug capture session."""
    capture = get_debug_capture()
    capture.stop_periodic_capture()
    capture.capture_dashboard_lifecycle("session_end")
    return capture.get_session_summary()