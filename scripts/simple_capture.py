#!/usr/bin/env python3
"""
Simple screenshot capture service compatible with existing memos database.
This is a temporary solution until pensieve can be properly reinstalled.
"""

import sys
import os
import time
import logging
from datetime import datetime
from pathlib import Path
import hashlib
import subprocess

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleScreenCapture:
    """Simple screenshot capture service."""
    
    def __init__(self, interval=5, screenshots_dir=None):
        self.interval = interval
        self.screenshots_dir = Path(screenshots_dir or Path.home() / '.memos' / 'screenshots')
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseManager()
        self.running = False
        
    def capture_screenshot(self):
        """Capture a single screenshot using macOS screencapture."""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now()
            filename = f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshots_dir / filename
            
            # Capture screenshot using macOS screencapture
            result = subprocess.run([
                'screencapture', 
                '-x',  # Disable sound
                '-t', 'png',  # PNG format
                str(filepath)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Screenshot capture failed: {result.stderr}")
                return None
                
            # Get file info
            file_size = filepath.stat().st_size
            file_hash = self._calculate_hash(filepath)
            
            # Get active window title
            active_window = self._get_active_window()
            
            # Store in database
            entity_id = self._store_screenshot(filepath, file_size, file_hash, timestamp, active_window)
            
            logger.info(f"Screenshot captured: {filename} (Entity ID: {entity_id})")
            return entity_id
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None
            
    def _calculate_hash(self, filepath):
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
        
    def _get_active_window(self):
        """Get active window title using AppleScript."""
        try:
            result = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to get name of first application process whose frontmost is true'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                app_name = result.stdout.strip()
                
                # Try to get window title
                window_result = subprocess.run([
                    'osascript', '-e', 
                    f'tell application "{app_name}" to get name of front window'
                ], capture_output=True, text=True)
                
                if window_result.returncode == 0:
                    window_title = window_result.stdout.strip()
                    return f"{app_name} - {window_title}"
                else:
                    return app_name
            else:
                return "Unknown"
                
        except Exception as e:
            logger.debug(f"Error getting active window: {e}")
            return "Unknown"
            
    def _store_screenshot(self, filepath, file_size, file_hash, timestamp, active_window):
        """Store screenshot info in database."""
        try:
            with self.db.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                
                # Insert entity with correct schema
                cursor.execute("""
                    INSERT INTO entities 
                    (filepath, filename, size, file_created_at, file_last_modified_at, 
                     file_type, file_type_group, library_id, folder_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(filepath), 
                    filepath.name,
                    file_size, 
                    timestamp, 
                    timestamp,
                    'image/png',
                    'image',
                    1,  # Default library_id
                    1,  # Default folder_id
                    timestamp, 
                    timestamp
                ))
                
                entity_id = cursor.lastrowid
                
                # Insert active window metadata
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (entity_id, 'active_window', active_window, 'system', 'text', timestamp, timestamp))
                
                conn.commit()
                return entity_id
                
        except Exception as e:
            logger.error(f"Error storing screenshot: {e}")
            return None
            
    def start_capture_loop(self):
        """Start continuous screenshot capture."""
        logger.info(f"Starting screenshot capture every {self.interval} seconds")
        logger.info(f"Screenshots will be saved to: {self.screenshots_dir}")
        
        self.running = True
        try:
            while self.running:
                self.capture_screenshot()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Screenshot capture stopped by user")
        finally:
            self.running = False
            
    def stop(self):
        """Stop capture loop."""
        self.running = False
        
    def capture_single(self):
        """Capture a single screenshot for testing."""
        return self.capture_screenshot()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Screenshot Capture Service')
    parser.add_argument('--interval', type=int, default=5,
                       help='Screenshot interval in seconds (default: 5)')
    parser.add_argument('--single', action='store_true',
                       help='Capture single screenshot and exit')
    parser.add_argument('--dir', type=str,
                       help='Screenshots directory (default: ~/.memos/screenshots)')
    
    args = parser.parse_args()
    
    capture = SimpleScreenCapture(
        interval=args.interval,
        screenshots_dir=args.dir
    )
    
    if args.single:
        entity_id = capture.capture_single()
        if entity_id:
            print(f"Screenshot captured with entity ID: {entity_id}")
        else:
            print("Screenshot capture failed")
    else:
        capture.start_capture_loop()


if __name__ == '__main__':
    main()