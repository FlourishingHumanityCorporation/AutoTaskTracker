#!/usr/bin/env python3
"""
Simple webhook demo to generate data for dashboard viewing.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.pensieve.webhook_server import WebhookServer, EventType

def main():
    print("🎯 Starting simple webhook health demo...")
    
    # Create a webhook server instance (simulates the actual webhook server)
    server = WebhookServer("127.0.0.1", 8842)
    
    # Add some test subscriptions
    def demo_handler(event):
        print(f"Demo handler: {event.event_type} for entity {event.entity_id}")
    
    # Create test subscriptions
    sub1 = server.subscribe([EventType.ENTITY_CREATED, EventType.ENTITY_UPDATED], demo_handler)
    sub2 = server.subscribe([EventType.OCR_COMPLETED], demo_handler)
    
    print(f"✅ Created subscriptions: {sub1[:8]}, {sub2[:8]}")
    
    # Simulate some webhook activity
    server.stats.requests_received = 45
    server.stats.requests_processed = 42
    server.stats.requests_failed = 3
    server.stats.last_request_time = datetime.now()
    server.stats.average_processing_time_ms = 85.4
    
    # Add some event type data
    server.stats.events_by_type = {
        "entity_created": 15,
        "entity_updated": 12,
        "entity_processed": 8,
        "ocr_completed": 10
    }
    
    print(f"📊 Simulated webhook activity:")
    print(f"   Requests: {server.stats.requests_received} received, {server.stats.requests_processed} processed")
    print(f"   Subscriptions: {len(server.subscriptions)} active")
    print(f"   Event types: {server.stats.events_by_type}")
    
    # Store the server instance globally so the dashboard can access it
    global _demo_webhook_server
    _demo_webhook_server = server
    
    print("\n🚀 Demo webhook server ready!")
    print("📊 Now open the analytics dashboard to see webhook health monitoring:")
    print("   http://localhost:8503")
    print("   Go to 'System Performance & Integration Health' → 'Webhook Health' tab")
    print("\n⏰ Demo server stats are available for dashboard viewing...")
    
    return server

# Global instance for dashboard access
_demo_webhook_server = None

def get_demo_webhook_server():
    """Get the demo webhook server instance."""
    return _demo_webhook_server

if __name__ == "__main__":
    server = main()
    
    try:
        print("Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped")