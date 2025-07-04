#!/usr/bin/env python3
"""
VLM Health Check and Auto-Recovery Script
Monitors VLM processing health and automatically recovers from issues
"""
import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from autotasktracker.core.database import DatabaseManager

# Setup logging
log_file = Path.home() / '.memos' / 'logs' / 'vlm_health_check.log'
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class VLMHealthMonitor:
    """Monitors and maintains VLM processing health."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.issues_found = []
        self.actions_taken = []
        
    def check_vlm_coverage(self, threshold_minutes=10, min_coverage=10.0):
        """Check if VLM coverage is adequate in recent time window."""
        query = f"""
        SELECT 
            (SELECT COUNT(*) FROM entities e 
             JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
             WHERE e.created_at >= datetime('now', '-{threshold_minutes} minutes')) as vlm_count,
            (SELECT COUNT(*) FROM entities 
             WHERE file_type_group = 'image' AND created_at >= datetime('now', '-{threshold_minutes} minutes')) as screenshot_count
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            
        if result and result['screenshot_count'] > 0:
            coverage = result['vlm_count'] / result['screenshot_count'] * 100
            if coverage < min_coverage:
                self.issues_found.append(f"Low VLM coverage: {coverage:.1f}% (target: {min_coverage}%)")
                return False, coverage
            return True, coverage
        
        return True, 0  # No screenshots to process
    
    def check_watch_service(self):
        """Check if memos watch service is running."""
        try:
            result = subprocess.run(['pgrep', '-f', 'memos watch'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                self.issues_found.append("Watch service not running")
                return False
            
            # Check if service is responsive by looking at recent log entries
            log_check = subprocess.run(
                ['tail', '-n', '20', str(Path.home() / '.memos' / 'logs' / 'watch.log')],
                capture_output=True, text=True
            )
            
            if 'ERROR' in log_check.stdout or 'Failed' in log_check.stdout:
                self.issues_found.append("Watch service showing errors")
                return False
                
            return True
        except Exception as e:
            self.issues_found.append(f"Could not check watch service: {e}")
            return False
    
    def check_ollama_health(self):
        """Check if Ollama is healthy and responsive."""
        try:
            # Basic health check
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:11434/api/tags'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                self.issues_found.append("Ollama not responding")
                return False
            
            # Test VLM model specifically
            test_start = time.time()
            test_result = subprocess.run([
                'curl', '-s', '-X', 'POST',
                'http://localhost:11434/api/generate',
                '-d', '{"model": "minicpm-v", "prompt": "test", "options": {"num_predict": 1}}'
            ], capture_output=True, text=True, timeout=30)
            
            test_duration = time.time() - test_start
            
            if test_result.returncode != 0:
                self.issues_found.append("minicpm-v model not responding")
                return False
            
            if test_duration > 20:
                self.issues_found.append(f"Ollama slow response: {test_duration:.1f}s")
                return False
                
            return True
            
        except subprocess.TimeoutExpired:
            self.issues_found.append("Ollama timeout")
            return False
        except Exception as e:
            self.issues_found.append(f"Ollama check failed: {e}")
            return False
    
    def check_processing_backlog(self):
        """Check if there's a large backlog of unprocessed screenshots."""
        query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN me.value IS NOT NULL THEN 1 END) as with_vlm
        FROM entities e
        LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
        WHERE e.file_type_group = 'image' 
        AND e.created_at >= datetime('now', '-1 hour')
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            
        if result and result['total'] > 0:
            backlog = result['total'] - result['with_vlm']
            backlog_pct = backlog / result['total'] * 100
            
            if backlog_pct > 80:
                self.issues_found.append(f"Large VLM backlog: {backlog} unprocessed ({backlog_pct:.0f}%)")
                return False
                
        return True
    
    def restart_watch_service(self):
        """Restart the memos watch service."""
        logger.info("Restarting watch service...")
        
        # Kill existing processes
        subprocess.run(['pkill', '-f', 'memos watch'], capture_output=True)
        time.sleep(2)
        
        # Start new instance
        env = os.environ.copy()
        venv_python = str(Path(__file__).parent.parent / 'venv' / 'bin' / 'python')
        memos_bin = str(Path(__file__).parent.parent / 'venv' / 'bin' / 'memos')
        
        process = subprocess.Popen(
            [memos_bin, 'watch'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        time.sleep(3)
        
        if process.poll() is None:
            self.actions_taken.append("Restarted watch service")
            logger.info("Watch service restarted successfully")
            return True
        else:
            logger.error("Failed to restart watch service")
            return False
    
    def optimize_processing_rate(self):
        """Dynamically adjust processing rate based on load."""
        # Check current processing rate
        ok, coverage = self.check_vlm_coverage(threshold_minutes=30)
        
        if coverage < 5:
            # Very low coverage - need aggressive settings
            logger.info("Applying aggressive VLM settings due to low coverage")
            
            # Run the optimizer in aggressive mode
            optimizer_path = Path(__file__).parent / 'vlm_optimizer.py'
            result = subprocess.run([
                sys.executable, str(optimizer_path), '--aggressive'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.actions_taken.append("Applied aggressive VLM settings")
                # Restart to apply new config
                self.restart_watch_service()
            else:
                logger.error(f"Failed to optimize settings: {result.stderr}")
    
    def send_alert(self, message):
        """Send alert about VLM issues (placeholder for notification system)."""
        # For now, just log critically
        logger.critical(f"ALERT: {message}")
        
        # Could integrate with:
        # - Email notifications
        # - Slack webhooks
        # - System notifications
        # - Dashboard alerts
    
    def run_health_check(self):
        """Run comprehensive health check and take corrective actions."""
        logger.info("Starting VLM health check...")
        
        # Reset tracking
        self.issues_found = []
        self.actions_taken = []
        
        # Run all checks
        checks = {
            'Watch Service': self.check_watch_service(),
            'Ollama Health': self.check_ollama_health(),
            'VLM Coverage': self.check_vlm_coverage()[0],
            'Processing Backlog': self.check_processing_backlog()
        }
        
        # Log results
        healthy = all(checks.values())
        status = "HEALTHY" if healthy else "UNHEALTHY"
        logger.info(f"Health check result: {status}")
        
        for check, result in checks.items():
            logger.info(f"  {check}: {'✅' if result else '❌'}")
        
        if self.issues_found:
            logger.warning(f"Issues found: {', '.join(self.issues_found)}")
        
        # Take corrective actions if needed
        if not healthy:
            logger.info("Taking corrective actions...")
            
            # Priority 1: Restart watch service if it's down
            if not checks['Watch Service']:
                self.restart_watch_service()
            
            # Priority 2: Check Ollama
            elif not checks['Ollama Health']:
                self.send_alert("Ollama service is unhealthy - manual intervention required")
            
            # Priority 3: Optimize if coverage is low
            elif not checks['VLM Coverage']:
                self.optimize_processing_rate()
            
            # Priority 4: Handle backlogs
            elif not checks['Processing Backlog']:
                logger.info("Large backlog detected - considering optimization")
                self.optimize_processing_rate()
        
        # Log actions taken
        if self.actions_taken:
            logger.info(f"Actions taken: {', '.join(self.actions_taken)}")
        
        # Return summary
        return {
            'healthy': healthy,
            'checks': checks,
            'issues': self.issues_found,
            'actions': self.actions_taken,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Main function for health check script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VLM Health Check and Recovery')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuously with periodic checks')
    parser.add_argument('--interval', type=int, default=300,
                       help='Check interval in seconds (default: 300)')
    parser.add_argument('--alert-only', action='store_true',
                       help='Only alert, do not take corrective actions')
    
    args = parser.parse_args()
    
    monitor = VLMHealthMonitor()
    
    if args.continuous:
        logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
        
        while True:
            try:
                result = monitor.run_health_check()
                
                # Sleep until next check
                time.sleep(args.interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(args.interval)
    else:
        # Single check
        result = monitor.run_health_check()
        
        # Exit with appropriate code
        sys.exit(0 if result['healthy'] else 1)


if __name__ == '__main__':
    main()