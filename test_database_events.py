#!/usr/bin/env python3
"""Test script to check database event detection."""

import logging
from autotasktracker.core.database import DatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_event_detection():
    """Test direct database event detection."""
    logger.info("Testing database event detection...")
    
    # Use direct database access (no API)
    db = DatabaseManager(use_pensieve_api=False)
    
    # Test from a specific point
    last_processed_id = 3450
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get entities newer than last processed ID
        cursor.execute(
            "SELECT id, filepath, filename, created_at, last_scan_at, file_type_group "
            "FROM entities WHERE id > ? ORDER BY id ASC LIMIT 20",
            (last_processed_id,)
        )
        
        new_entities = cursor.fetchall()
        
        logger.info(f"Found {len(new_entities)} entities newer than ID {last_processed_id}")
        
        for entity in new_entities[:5]:  # Show first 5
            logger.info(f"  ID: {entity['id']}, File: {entity['filename']}, "
                       f"Created: {entity['created_at']}, Scanned: {entity['last_scan_at']}")
        
        if new_entities:
            logger.info("✅ Database event detection is working!")
            return True
        else:
            logger.warning("⚠️ No new entities found")
            return False

if __name__ == "__main__":
    test_database_event_detection()