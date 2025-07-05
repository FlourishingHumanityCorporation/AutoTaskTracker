#!/usr/bin/env python3
"""
Webhook Health Test Script

Tests the webhook server health monitoring and generates sample data
for dashboard validation.
"""

import sys
import os
import time
import requests
import json
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.pensieve.webhook_server import WebhookServer, WebhookPayload, EventType
import threading


class WebhookHealthTester:
    """Test webhook server health monitoring capabilities."""
    
    def __init__(self, webhook_host: str = "127.0.0.1", webhook_port: int = 8840):
        self.webhook_host = webhook_host
        self.webhook_port = webhook_port
        self.base_url = f"http://{webhook_host}:{webhook_port}"
        self.server = None
        self.server_thread = None
    
    def start_test_webhook_server(self):
        """Start a test webhook server for monitoring."""
        print("🚀 Starting test webhook server...")
        
        self.server = WebhookServer(self.webhook_host, self.webhook_port)
        
        # Register some test handlers
        def test_handler(event):
            print(f"Test handler received: {event.event_type} for entity {event.entity_id}")
        
        self.server.register_handler("entity_created", test_handler)
        self.server.register_handler("entity_updated", test_handler)
        
        # Create test subscriptions
        subscription_id = self.server.subscribe(
            event_types=[EventType.ENTITY_CREATED, EventType.ENTITY_UPDATED],
            handler=test_handler
        )
        
        print(f"✅ Created test subscription: {subscription_id[:8]}")
        
        # Start server in background thread
        def run_server():
            import uvicorn
            uvicorn.run(self.server.app, host=self.webhook_host, port=self.webhook_port, log_level="warning")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        print(f"📡 Webhook server running on {self.base_url}")
        
        return self.server
    
    def test_webhook_endpoints(self):
        """Test webhook endpoints and generate activity."""
        print("\n🧪 Testing webhook endpoints...")
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Health endpoint responding")
                health_data = response.json()
                print(f"   Uptime: {health_data.get('uptime_seconds', 0):.1f}s")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health endpoint error: {e}")
        
        # Test stats endpoint
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=5)
            if response.status_code == 200:
                print("✅ Stats endpoint responding")
                stats = response.json()
                print(f"   Requests received: {stats.get('requests_received', 0)}")
                print(f"   Active subscriptions: {stats.get('active_subscriptions', 0)}")
            else:
                print(f"❌ Stats endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Stats endpoint error: {e}")
        
        # Generate test webhook events
        print("\n📡 Generating test webhook events...")
        
        test_events = [
            {
                "endpoint": "/webhook/entity/created",
                "payload": {
                    "event_type": "entity_created",
                    "entity_id": 1001,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"filepath": "/test/screenshot1.png", "source": "test"}
                }
            },
            {
                "endpoint": "/webhook/entity/updated", 
                "payload": {
                    "event_type": "entity_updated",
                    "entity_id": 1001,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"metadata_updated": True, "source": "test"}
                }
            },
            {
                "endpoint": "/webhook/entity/processed",
                "payload": {
                    "event_type": "entity_processed",
                    "entity_id": 1002,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"ocr_completed": True, "source": "test"}
                }
            }
        ]
        
        for i, event in enumerate(test_events, 1):
            try:
                response = requests.post(
                    f"{self.base_url}{event['endpoint']}",
                    json=event["payload"],
                    timeout=5
                )
                
                if response.status_code == 202:
                    print(f"✅ Event {i}: {event['payload']['event_type']} accepted")
                else:
                    print(f"❌ Event {i}: Failed ({response.status_code})")
                    
            except Exception as e:
                print(f"❌ Event {i}: Error - {e}")
            
            time.sleep(0.5)  # Small delay between events
    
    def get_webhook_stats(self) -> Dict[str, Any]:
        """Get current webhook server statistics."""
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Stats request failed: {response.status_code}"}
        except Exception as e:
            return {"error": f"Stats request error: {e}"}
    
    def generate_activity_load(self, duration_seconds: int = 30, events_per_second: int = 2):
        """Generate sustained webhook activity for testing dashboard."""
        print(f"\n⚡ Generating {events_per_second} events/sec for {duration_seconds}s...")
        
        start_time = time.time()
        event_count = 0
        
        while time.time() - start_time < duration_seconds:
            # Generate different types of events
            entity_id = 2000 + (event_count % 100)
            event_types = ["entity_created", "entity_updated", "entity_processed", "metadata_updated"]
            event_type = event_types[event_count % len(event_types)]
            
            payload = {
                "event_type": event_type,
                "entity_id": entity_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "test_event": True,
                    "event_number": event_count,
                    "source": "load_test"
                }
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/webhook/generic",
                    json=payload,
                    timeout=2
                )
                
                if response.status_code == 202:
                    event_count += 1
                    if event_count % 10 == 0:
                        print(f"   Generated {event_count} events...")
                
            except Exception as e:
                print(f"   Event {event_count} failed: {e}")
            
            # Control rate
            time.sleep(1.0 / events_per_second)
        
        print(f"✅ Generated {event_count} events in {duration_seconds}s")
        return event_count
    
    def print_summary_report(self):
        """Print a summary report of webhook server status."""
        print("\n📊 Webhook Server Summary Report")
        print("=" * 50)
        
        stats = self.get_webhook_stats()
        
        if "error" in stats:
            print(f"❌ Error getting stats: {stats['error']}")
            return
        
        print(f"Uptime: {stats.get('uptime_seconds', 0):.1f} seconds")
        print(f"Requests received: {stats.get('requests_received', 0)}")
        print(f"Requests processed: {stats.get('requests_processed', 0)}")
        print(f"Requests failed: {stats.get('requests_failed', 0)}")
        print(f"Active subscriptions: {stats.get('active_subscriptions', 0)}")
        print(f"Average processing time: {stats.get('average_processing_time_ms', 0):.1f}ms")
        
        if stats.get('events_by_type'):
            print("\nEvent types received:")
            for event_type, count in stats['events_by_type'].items():
                print(f"  {event_type}: {count}")
        
        # Calculate success rate
        received = stats.get('requests_received', 0)
        processed = stats.get('requests_processed', 0)
        if received > 0:
            success_rate = (processed / received) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")


def main():
    """Main test execution."""
    print("AutoTaskTracker Webhook Health Monitoring Test")
    print("=" * 50)
    
    tester = WebhookHealthTester()
    
    try:
        # Start test server
        server = tester.start_test_webhook_server()
        
        # Basic endpoint tests
        tester.test_webhook_endpoints()
        
        # Generate some load
        tester.generate_activity_load(duration_seconds=15, events_per_second=3)
        
        # Print summary
        tester.print_summary_report()
        
        print(f"\n💡 To view webhook health in dashboard:")
        print(f"   1. Start analytics dashboard: python autotasktracker.py analytics")
        print(f"   2. Go to 'System Performance & Integration Health' section")
        print(f"   3. Click on 'Webhook Health' tab")
        print(f"\n🔗 Direct webhook server access:")
        print(f"   Health: {tester.base_url}/health")
        print(f"   Stats: {tester.base_url}/stats")
        print(f"   Endpoints: {tester.base_url}/webhook/endpoints")
        
        print(f"\n⏰ Server will continue running for dashboard testing...")
        print(f"   Press Ctrl+C to stop")
        
        # Keep server running for dashboard testing
        try:
            while True:
                time.sleep(10)
                # Generate occasional events to keep dashboard interesting
                tester.generate_activity_load(duration_seconds=5, events_per_second=1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping webhook server...")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())