"""
Webhook client for real-time dashboard integration with Pensieve webhook server.
Provides seamless integration between Pensieve events and dashboard updates.
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional, Set
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict, deque
import websockets
import requests
from urllib.parse import urljoin

from autotasktracker.pensieve.webhook_server import EventType, WebhookStats
from autotasktracker.pensieve.event_processor import PensieveEvent, get_event_processor
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class WebhookSubscription:
    """Webhook subscription configuration."""
    event_types: List[EventType]
    callback_url: str
    filters: Dict[str, Any]
    retry_count: int = 3
    timeout_seconds: int = 30
    active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class WebhookClientStats:
    """Webhook client statistics."""
    subscriptions_active: int = 0
    events_received: int = 0
    events_processed: int = 0
    events_failed: int = 0
    last_event_time: Optional[datetime] = None
    connection_uptime_seconds: float = 0.0
    average_response_time_ms: float = 0.0
    dashboard_updates_sent: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'subscriptions_active': self.subscriptions_active,
            'events_received': self.events_received,
            'events_processed': self.events_processed,
            'events_failed': self.events_failed,
            'last_event_time': self.last_event_time.isoformat() if self.last_event_time else None,
            'connection_uptime_seconds': self.connection_uptime_seconds,
            'average_response_time_ms': self.average_response_time_ms,
            'dashboard_updates_sent': self.dashboard_updates_sent
        }


class WebhookClient:
    """High-performance webhook client for real-time dashboard integration."""
    
    def __init__(self, webhook_server_url: str = "http://127.0.0.1:8840"):
        """Initialize webhook client.
        
        Args:
            webhook_server_url: Base URL of the webhook server
        """
        self.webhook_server_url = webhook_server_url.rstrip('/')
        self.subscriptions: Dict[str, WebhookSubscription] = {}
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.stats = WebhookClientStats()
        self.start_time = time.time()
        
        # Real-time event queue for dashboard updates
        self.event_queue = deque(maxlen=1000)  # Keep last 1000 events
        self.dashboard_callbacks: List[Callable[[PensieveEvent], None]] = []
        
        # Connection management
        self.websocket_client = None
        self.websocket_task = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Integration components
        self.event_processor = get_event_processor()
        self.health_monitor = get_health_monitor()
        
        logger.info(f"Webhook client initialized - Server: {self.webhook_server_url}")
    
    async def start(self):
        """Start the webhook client with real-time connections."""
        try:
            # Test webhook server connectivity
            if not await self._test_webhook_server():
                logger.warning("Webhook server not available, running in polling mode")
                await self._start_polling_mode()
                return
            
            # Start WebSocket connection for real-time events
            await self._start_websocket_connection()
            
            # Register default dashboard event handlers
            self._setup_dashboard_integration()
            
            logger.info("Webhook client started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start webhook client: {e}")
            # Fallback to event processor polling
            await self._start_fallback_mode()
    
    async def stop(self):
        """Stop the webhook client gracefully."""
        try:
            self.is_connected = False
            
            if self.websocket_task:
                self.websocket_task.cancel()
                await self.websocket_task
            
            if self.websocket_client:
                await self.websocket_client.close()
            
            logger.info("Webhook client stopped")
            
        except Exception as e:
            logger.error(f"Error stopping webhook client: {e}")
    
    def register_dashboard_callback(self, callback: Callable[[PensieveEvent], None]):
        """Register a callback for dashboard updates.
        
        Args:
            callback: Function to call when events occur
        """
        self.dashboard_callbacks.append(callback)
        logger.debug(f"Registered dashboard callback: {callback.__name__}")
    
    def register_event_handler(self, event_type: EventType, handler: Callable[[PensieveEvent], None]):
        """Register an event handler for specific event types.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered event handler for {event_type.value}")
    
    async def subscribe_to_events(
        self, 
        event_types: List[EventType], 
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Subscribe to specific event types with optional filters.
        
        Args:
            event_types: List of event types to subscribe to
            filters: Optional filters for events
            
        Returns:
            Subscription ID
        """
        try:
            subscription_id = f"sub_{int(time.time())}_{len(self.subscriptions)}"
            
            subscription = WebhookSubscription(
                event_types=event_types,
                callback_url=f"{self.webhook_server_url}/webhook/client_callback",
                filters=filters or {}
            )
            
            self.subscriptions[subscription_id] = subscription
            self.stats.subscriptions_active = len([s for s in self.subscriptions.values() if s.active])
            
            # Send subscription to webhook server
            await self._send_subscription(subscription_id, subscription)
            
            logger.info(f"Subscribed to events: {[et.value for et in event_types]}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")
            raise
    
    async def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events from the queue.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent event dictionaries
        """
        events = list(self.event_queue)[-limit:]
        return [
            {
                'event_type': event.event_type,
                'entity_id': event.entity_id,
                'timestamp': event.timestamp.isoformat(),
                'data': event.data,
                'source': event.source
            }
            for event in events
        ]
    
    async def trigger_dashboard_refresh(self, entity_id: Optional[int] = None):
        """Trigger a dashboard refresh event.
        
        Args:
            entity_id: Optional specific entity ID to refresh
        """
        try:
            refresh_event = PensieveEvent(
                event_type=EventType.DASHBOARD_REFRESH_NEEDED.value,
                entity_id=entity_id or 0,
                timestamp=datetime.now(),
                data={'refresh_type': 'manual', 'entity_id': entity_id},
                source='webhook_client'
            )
            
            await self._process_event(refresh_event)
            self.stats.dashboard_updates_sent += 1
            
            logger.debug(f"Triggered dashboard refresh for entity {entity_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger dashboard refresh: {e}")
    
    async def get_client_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics.
        
        Returns:
            Dictionary of client statistics
        """
        self.stats.connection_uptime_seconds = time.time() - self.start_time
        
        # Get webhook server stats if available
        server_stats = await self._get_server_stats()
        
        return {
            'client_stats': self.stats.to_dict(),
            'server_stats': server_stats,
            'connection_status': {
                'is_connected': self.is_connected,
                'reconnect_attempts': self.reconnect_attempts,
                'subscriptions_count': len(self.subscriptions),
                'event_handlers_count': sum(len(handlers) for handlers in self.event_handlers.values()),
                'dashboard_callbacks_count': len(self.dashboard_callbacks)
            },
            'integration_health': {
                'webhook_server_available': await self._test_webhook_server(),
                'event_processor_healthy': self.event_processor is not None,
                'health_monitor_active': self.health_monitor.is_monitoring_active()
            }
        }
    
    async def _test_webhook_server(self) -> bool:
        """Test if webhook server is available."""
        try:
            response = requests.get(f"{self.webhook_server_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Webhook server test failed: {e}")
            return False
    
    async def _start_websocket_connection(self):
        """Start WebSocket connection for real-time events."""
        try:
            ws_url = self.webhook_server_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url += '/ws/events'
            
            self.websocket_client = await websockets.connect(ws_url)
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # Start WebSocket message handling task
            self.websocket_task = asyncio.create_task(self._handle_websocket_messages())
            
            logger.info(f"WebSocket connection established: {ws_url}")
            
        except Exception as e:
            logger.warning(f"WebSocket connection failed: {e}")
            await self._start_polling_mode()
    
    async def _handle_websocket_messages(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket_client:
                try:
                    event_data = json.loads(message)
                    event = PensieveEvent(
                        event_type=event_data['event_type'],
                        entity_id=event_data['entity_id'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        data=event_data['data'],
                        source=event_data.get('source', 'webhook_server')
                    )
                    
                    await self._process_event(event)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket event: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
            await self._attempt_reconnect()
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            await self._attempt_reconnect()
    
    async def _attempt_reconnect(self):
        """Attempt to reconnect to WebSocket server."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached, switching to polling mode")
            await self._start_polling_mode()
            return
        
        self.reconnect_attempts += 1
        backoff_time = min(2 ** self.reconnect_attempts, 60)  # Exponential backoff
        
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {backoff_time}s")
        await asyncio.sleep(backoff_time)
        
        try:
            await self._start_websocket_connection()
        except Exception as e:
            logger.error(f"Reconnection attempt {self.reconnect_attempts} failed: {e}")
            await self._attempt_reconnect()
    
    async def _start_polling_mode(self):
        """Start polling mode as fallback when WebSocket unavailable."""
        logger.info("Starting polling mode for event updates")
        
        async def poll_events():
            while True:
                try:
                    # Poll for new events from event processor
                    if self.event_processor:
                        recent_events = await self.event_processor.get_recent_events(limit=10)
                        for event in recent_events:
                            await self._process_event(event)
                    
                    # Poll interval - adjust based on requirements
                    await asyncio.sleep(5)  # Poll every 5 seconds
                    
                except Exception as e:
                    logger.error(f"Error in polling mode: {e}")
                    await asyncio.sleep(10)  # Longer wait on error
        
        # Start polling task
        asyncio.create_task(poll_events())
    
    async def _start_fallback_mode(self):
        """Start in fallback mode without real-time capabilities."""
        logger.info("Starting in fallback mode - limited real-time capabilities")
        
        # Setup basic event handlers without real-time updates
        self._setup_dashboard_integration()
    
    def _setup_dashboard_integration(self):
        """Setup integration with dashboard components."""
        try:
            # Register for key event types that affect dashboards
            key_events = [
                EventType.ENTITY_CREATED,
                EventType.ENTITY_UPDATED,
                EventType.TASK_EXTRACTED,
                EventType.OCR_COMPLETED,
                EventType.VLM_COMPLETED
            ]
            
            for event_type in key_events:
                self.register_event_handler(event_type, self._handle_dashboard_event)
            
            logger.debug("Dashboard integration setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup dashboard integration: {e}")
    
    async def _process_event(self, event: PensieveEvent):
        """Process an incoming event.
        
        Args:
            event: The event to process
        """
        try:
            start_time = time.time()
            
            # Update statistics
            self.stats.events_received += 1
            self.stats.last_event_time = datetime.now()
            
            # Add to event queue for dashboard access
            self.event_queue.append(event)
            
            # Call registered event handlers
            event_type = EventType(event.event_type) if hasattr(EventType, event.event_type) else EventType.CUSTOM_EVENT
            handlers = self.event_handlers.get(event_type, [])
            
            for handler in handlers:
                try:
                    await handler(event) if asyncio.iscoroutinefunction(handler) else handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")
                    self.stats.events_failed += 1
            
            # Call dashboard callbacks
            for callback in self.dashboard_callbacks:
                try:
                    await callback(event) if asyncio.iscoroutinefunction(callback) else callback(event)
                except Exception as e:
                    logger.error(f"Dashboard callback failed: {e}")
            
            # Update processing statistics
            processing_time = (time.time() - start_time) * 1000
            self.stats.average_response_time_ms = (
                (self.stats.average_response_time_ms * self.stats.events_processed + processing_time) /
                (self.stats.events_processed + 1)
            )
            self.stats.events_processed += 1
            
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            self.stats.events_failed += 1
    
    async def _handle_dashboard_event(self, event: PensieveEvent):
        """Handle events that affect dashboard displays.
        
        Args:
            event: The dashboard-relevant event
        """
        try:
            # Trigger dashboard refresh based on event type
            if event.event_type in [
                EventType.ENTITY_CREATED.value,
                EventType.ENTITY_UPDATED.value,
                EventType.TASK_EXTRACTED.value
            ]:
                # Invalidate relevant caches
                if hasattr(self, 'cache_manager'):
                    await self.cache_manager.invalidate_pattern(f"entity_{event.entity_id}*")
                
                # Trigger refresh event
                await self.trigger_dashboard_refresh(event.entity_id)
            
            self.stats.dashboard_updates_sent += 1
            
        except Exception as e:
            logger.error(f"Failed to handle dashboard event: {e}")
    
    async def _send_subscription(self, subscription_id: str, subscription: WebhookSubscription):
        """Send subscription request to webhook server.
        
        Args:
            subscription_id: Unique subscription identifier
            subscription: Subscription configuration
        """
        try:
            subscription_data = {
                'subscription_id': subscription_id,
                'event_types': [et.value for et in subscription.event_types],
                'callback_url': subscription.callback_url,
                'filters': subscription.filters,
                'timeout_seconds': subscription.timeout_seconds
            }
            
            response = requests.post(
                f"{self.webhook_server_url}/subscriptions",
                json=subscription_data,
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"Subscription failed: {response.status_code}")
            
            logger.info(f"Subscription {subscription_id} sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send subscription: {e}")
            raise
    
    async def _get_server_stats(self) -> Optional[Dict[str, Any]]:
        """Get statistics from webhook server.
        
        Returns:
            Server statistics or None if unavailable
        """
        try:
            response = requests.get(f"{self.webhook_server_url}/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Failed to get server stats: {e}")
        return None


# Singleton instance
_webhook_client: Optional[WebhookClient] = None


def get_webhook_client(webhook_server_url: str = "http://127.0.0.1:8840") -> WebhookClient:
    """Get singleton webhook client instance."""
    global _webhook_client
    if _webhook_client is None:
        _webhook_client = WebhookClient(webhook_server_url)
    return _webhook_client


def reset_webhook_client():
    """Reset webhook client for testing."""
    global _webhook_client
    _webhook_client = None


async def start_webhook_integration():
    """Start webhook integration for real-time dashboard updates."""
    try:
        client = get_webhook_client()
        await client.start()
        
        # Subscribe to key events for dashboard updates
        await client.subscribe_to_events([
            EventType.ENTITY_CREATED,
            EventType.ENTITY_UPDATED,
            EventType.TASK_EXTRACTED,
            EventType.OCR_COMPLETED,
            EventType.VLM_COMPLETED,
            EventType.DASHBOARD_REFRESH_NEEDED
        ])
        
        logger.info("Webhook integration started successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to start webhook integration: {e}")
        raise


async def stop_webhook_integration():
    """Stop webhook integration gracefully."""
    try:
        client = get_webhook_client()
        await client.stop()
        logger.info("Webhook integration stopped")
    except Exception as e:
        logger.error(f"Error stopping webhook integration: {e}")