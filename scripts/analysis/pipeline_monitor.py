#!/usr/bin/env python3
"""
Pipeline monitoring script to ensure task processing stays active.
"""

import sys
import os
import time
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.core.database import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / '.memos' / 'logs' / 'pipeline_monitor.log')
    ]
)
logger = logging.getLogger(__name__)


class PipelineMonitor:
    """Monitor and maintain the AutoTaskTracker pipeline."""
    
    def __init__(self, check_interval=300):  # 5 minutes
        self.db = DatabaseManager()
        self.check_interval = check_interval
        self.running = False
        
    def start(self):
        """Start monitoring the pipeline."""
        logger.info("Starting Pipeline Monitor")
        self.running = True
        
        try:
            while self.running:
                self._check_pipeline_health()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Pipeline Monitor stopped by user")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        
    def _check_pipeline_health(self):
        """Check if the pipeline is processing data."""
        try:
            status = self._get_processing_status()
            
            # Check if processing is stalled
            if status['recent_processed'] == 0 and status['unprocessed_entities'] > 0:
                logger.warning(f"Processing stalled: {status['unprocessed_entities']} unprocessed entities")
                self._restart_task_processor()
                
            # Check if dashboards are running
            dashboard_status = self._check_dashboard_status()
            if not dashboard_status['task_board_running']:
                logger.warning("Task board dashboard not running")
                self._restart_dashboard('task_board')
                
            # Log status
            logger.info(f"Pipeline health: {status['processed_entities']}/{status['total_entities']} processed "
                       f"({status['processing_percentage']:.1f}%), "
                       f"{status['recent_processed']} processed in last hour")
                       
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
    def _get_processing_status(self):
        """Get current processing status from database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total entities
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities = cursor.fetchone()[0]
            
            # Processed entities
            cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM metadata_entries WHERE key = 'tasks'")
            processed_entities = cursor.fetchone()[0]
            
            # Recent processing (last hour)
            cursor.execute("""
                SELECT COUNT(*) FROM metadata_entries 
                WHERE key = 'tasks' AND created_at >= datetime('now', '-1 hour')
            """)
            recent_processed = cursor.fetchone()[0]
            
            return {
                'total_entities': total_entities,
                'processed_entities': processed_entities,
                'unprocessed_entities': total_entities - processed_entities,
                'processing_percentage': (processed_entities / total_entities * 100) if total_entities > 0 else 0,
                'recent_processed': recent_processed
            }
            
    def _check_dashboard_status(self):
        """Check if key dashboards are running."""
        import socket
        
        def is_port_open(port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('localhost', port))
                    return result == 0
            except Exception:
                return False
                
        return {
            'task_board_running': is_port_open(8502),
            'analytics_running': is_port_open(8503)
        }
        
    def _restart_task_processor(self):
        """Restart the task processor if it's stalled."""
        try:
            logger.info("Attempting to restart task processor...")
            
            # Run a single batch
            result = subprocess.run([
                sys.executable, 
                'scripts/task_processor.py', 
                '--batch-size', '10'
            ], 
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            capture_output=True, 
            text=True, 
            timeout=60
            )
            
            if result.returncode == 0:
                logger.info("Task processor batch completed successfully")
            else:
                logger.error(f"Task processor failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Task processor batch timed out")
        except Exception as e:
            logger.error(f"Failed to restart task processor: {e}")
            
    def _restart_dashboard(self, dashboard_name):
        """Restart a specific dashboard."""
        try:
            logger.info(f"Attempting to restart {dashboard_name} dashboard...")
            
            subprocess.run([
                sys.executable, 
                '-m', 
                'autotasktracker.dashboards.launcher',
                'start',
                '--dashboard',
                dashboard_name
            ],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            timeout=30
            )
            
            logger.info(f"{dashboard_name} dashboard restart initiated")
            
        except Exception as e:
            logger.error(f"Failed to restart {dashboard_name} dashboard: {e}")
            
    def get_health_report(self):
        """Generate a health report."""
        try:
            status = self._get_processing_status()
            dashboard_status = self._check_dashboard_status()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'processing': status,
                'dashboards': dashboard_status,
                'health_score': self._calculate_health_score(status, dashboard_status)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            return None
            
    def _calculate_health_score(self, processing_status, dashboard_status):
        """Calculate overall pipeline health score (0-100)."""
        score = 0
        
        # Processing health (70% of score)
        if processing_status['total_entities'] > 0:
            processing_score = min(processing_status['processing_percentage'], 100) * 0.7
            score += processing_score
            
        # Dashboard health (30% of score)
        dashboard_score = 0
        if dashboard_status['task_board_running']:
            dashboard_score += 20
        if dashboard_status['analytics_running']:
            dashboard_score += 10
            
        score += dashboard_score
        
        return min(score, 100)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AutoTaskTracker Pipeline Monitor')
    parser.add_argument('--interval', type=int, default=300,
                       help='Check interval in seconds (default: 300)')
    parser.add_argument('--health', action='store_true',
                       help='Show health report and exit')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as background daemon')
    
    args = parser.parse_args()
    
    monitor = PipelineMonitor(check_interval=args.interval)
    
    if args.health:
        report = monitor.get_health_report()
        if report:
            print(f"\n🔍 AutoTaskTracker Pipeline Health Report")
            print(f"{'='*50}")
            print(f"Timestamp: {report['timestamp']}")
            print(f"Health Score: {report['health_score']:.1f}/100")
            print(f"\n📊 Processing Status:")
            print(f"  Total entities: {report['processing']['total_entities']}")
            print(f"  Processed: {report['processing']['processed_entities']} ({report['processing']['processing_percentage']:.1f}%)")
            print(f"  Unprocessed: {report['processing']['unprocessed_entities']}")
            print(f"  Recent (1h): {report['processing']['recent_processed']}")
            print(f"\n🌐 Dashboard Status:")
            print(f"  Task Board: {'🟢 Running' if report['dashboards']['task_board_running'] else '🔴 Stopped'}")
            print(f"  Analytics: {'🟢 Running' if report['dashboards']['analytics_running'] else '🔴 Stopped'}")
        return
    
    if args.daemon:
        logger.info("Daemon mode not yet implemented, running in foreground")
    
    monitor.start()


if __name__ == '__main__':
    main()