#!/usr/bin/env python3
"""Debug script to test event processor with detailed logging."""

import time
import logging
from datetime import datetime
from autotasktracker.pensieve.event_processor import get_event_processor
from autotasktracker.core.database import DatabaseManager

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_event_processing():
    """Debug event processing with detailed logging."""
    logger.info("🔍 Debugging event processor...")
    
    # Get the global event processor
    processor = get_event_processor()
    
    # Set a specific last_processed_id
    processor.last_processed_id = 3450
    logger.info(f"Set last_processed_id to {processor.last_processed_id}")
    
    # Test database detection directly first
    logger.info("🔍 Testing database detection directly...")
    events = processor._detect_database_changes()
    logger.info(f"Direct database detection found {len(events)} events")
    
    if events:
        for event in events[:3]:
            logger.info(f"  Event: {event.event_type}, Entity: {event.entity_id}, Time: {event.timestamp}")
    
    # Test the full _get_new_events method
    logger.info("🔍 Testing full _get_new_events method...")
    all_events = processor._get_new_events()
    logger.info(f"Full event detection found {len(all_events)} events")
    
    # Now test the processing loop manually
    logger.info("🔍 Testing manual event processing...")
    for event in all_events[:2]:  # Process first 2 events
        try:
            logger.info(f"Processing event: {event.event_type} for entity {event.entity_id}")
            processor._process_event(event)
            processor.events_processed += 1
            processor.last_event_time = datetime.now()
            logger.info(f"✅ Successfully processed event {event.entity_id}")
        except Exception as e:
            logger.error(f"❌ Failed to process event {event.entity_id}: {e}")
            processor.events_failed += 1
    
    # Check final stats
    stats = processor.get_statistics()
    logger.info(f"Final stats: {stats}")

if __name__ == "__main__":
    debug_event_processing()