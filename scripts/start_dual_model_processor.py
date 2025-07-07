#!/usr/bin/env python3
"""
Start dual-model processing service for AutoTaskTracker.

This script starts the EventProcessor in background mode to continuously
process new screenshots with dual-model AI analysis.
"""

import sys
import os
import signal
import time
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from autotasktracker.pensieve.event_processor import get_event_processor
from autotasktracker.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'logs' / 'dual_model_processor.log')
    ]
)
logger = logging.getLogger(__name__)


class DualModelProcessingService:
    """Service to run dual-model processing continuously."""
    
    def __init__(self):
        self.config = get_config()
        self.event_processor = None
        self.running = False
        
    def start(self):
        """Start the dual-model processing service."""
        logger.info("Starting AutoTaskTracker Dual-Model Processing Service")
        
        # Check if dual-model is enabled
        if not self.config.ENABLE_DUAL_MODEL:
            logger.warning("Dual-model processing is disabled in configuration")
            logger.info("Set ENABLE_DUAL_MODEL=True in config or AUTOTASK_ENABLE_DUAL_MODEL=1 env var")
            return False
        
        try:
            # Initialize event processor (which includes dual-model processor)
            self.event_processor = get_event_processor()
            
            # Check if dual-model processor was initialized successfully
            stats = self.event_processor.get_statistics()
            if not stats.get('dual_model_enabled', False):
                logger.error("Dual-model processor failed to initialize")
                return False
            
            logger.info("✅ Dual-model processor initialized successfully")
            
            # Start event processing
            self.event_processor.start_processing()
            self.running = True
            
            logger.info("🚀 Dual-model processing service started")
            logger.info(f"📊 Poll interval: {self.event_processor.poll_interval}s")
            logger.info(f"🧠 VLM Model: {self.config.VLM_MODEL_NAME}")
            logger.info(f"🦙 Llama3 Model: {self.config.LLAMA3_MODEL_NAME}")
            
            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start dual-model processing service: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def stop(self):
        """Stop the dual-model processing service."""
        if not self.running:
            return
            
        logger.info("Stopping dual-model processing service...")
        self.running = False
        
        if self.event_processor:
            self.event_processor.stop_processing()
            
        logger.info("✅ Dual-model processing service stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def run_forever(self):
        """Run the service until interrupted."""
        if not self.start():
            return 1
        
        try:
            logger.info("Service running - press Ctrl+C to stop")
            
            # Main service loop
            while self.running:
                time.sleep(5)  # Check every 5 seconds
                
                # Print periodic status
                if hasattr(self, '_last_status_time'):
                    if time.time() - self._last_status_time > 300:  # Every 5 minutes
                        self._print_status()
                else:
                    self._last_status_time = time.time()
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
            
        return 0
    
    def _print_status(self):
        """Print service status."""
        if self.event_processor:
            stats = self.event_processor.get_statistics()
            logger.info(f"📊 Status: Events processed={stats['events_processed']}, "
                       f"Failed={stats['events_failed']}, "
                       f"Last processed ID={stats['last_processed_id']}")
            
            # Print dual-model status if available
            dual_status = stats.get('dual_model_status')
            if dual_status:
                logger.info(f"🧠 Dual-model: Session={dual_status.get('current_session_id', 'None')}, "
                           f"Screenshots={dual_status.get('session_screenshot_count', 0)}")
        
        self._last_status_time = time.time()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AutoTaskTracker Dual-Model Processing Service')
    parser.add_argument('--daemon', action='store_true', 
                       help='Run as daemon (background process)')
    parser.add_argument('--check', action='store_true',
                       help='Check configuration and exit')
    parser.add_argument('--poll-interval', type=float, default=1.0,
                       help='Polling interval in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    service = DualModelProcessingService()
    
    if args.check:
        # Configuration check mode
        config = get_config()
        print(f"Dual-model enabled: {config.ENABLE_DUAL_MODEL}")
        print(f"VLM model: {config.VLM_MODEL_NAME}")
        print(f"Llama3 model: {config.LLAMA3_MODEL_NAME}")
        print(f"Database URL: {config.get_database_url()}")
        
        # Test dual-model processor initialization
        try:
            from autotasktracker.ai.dual_model_processor import create_dual_model_processor
            processor = create_dual_model_processor()
            print("✅ Dual-model processor can be initialized")
            
            status = processor.get_session_status()
            print(f"Session timeout: {status['session_timeout_minutes']} minutes")
            
        except Exception as e:
            print(f"❌ Dual-model processor initialization failed: {e}")
            return 1
            
        return 0
    
    if args.daemon:
        # TODO: Implement proper daemon mode
        logger.warning("Daemon mode not yet implemented, running in foreground")
    
    # Set poll interval if specified
    if hasattr(service, 'event_processor') and service.event_processor:
        service.event_processor.poll_interval = args.poll_interval
    
    return service.run_forever()


if __name__ == "__main__":
    sys.exit(main())