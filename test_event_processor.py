#!/usr/bin/env python3
"""Test script to check event processor functionality."""

import time
import logging
from autotasktracker.pensieve.event_processor import get_event_processor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_event_processor():
    """Test event processor to see if it processes events correctly."""
    logger.info("Testing event processor...")
    
    # Get the global event processor
    processor = get_event_processor()
    
    # Check initial status
    stats = processor.get_statistics()
    logger.info(f"Initial status: {stats}")
    
    # Start the processor
    if not processor.running:
        logger.info("Starting event processor...")
        processor.start_processing()
    
    # Set a higher last_processed_id to see recent events
    processor.last_processed_id = 3450  # Set to before recent entities
    logger.info(f"Set last_processed_id to {processor.last_processed_id}")
    
    # Wait for some processing
    logger.info("Waiting 10 seconds for event processing...")
    time.sleep(10)
    
    # Check status again
    stats = processor.get_statistics()
    logger.info(f"Final status: {stats}")
    
    if stats['events_processed'] > 0:
        logger.info("✅ Event processor is working!")
    else:
        logger.warning("⚠️ Event processor processed no events")
    
    # Stop the processor
    processor.stop_processing()
    logger.info("Stopped event processor")

if __name__ == "__main__":
    test_event_processor()