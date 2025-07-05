"""
Real-time event integration system for Pensieve.
Provides WebSocket and webhook integration for live updates.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import requests
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from autotasktracker.pensieve.api_client import get_pensieve_client
from autotasktracker.pensieve.config_sync import get_synced_config

logger = logging.getLogger(__name__)


@dataclass
class PensieveEvent:
    """Represents a Pensieve event."""
    event_type: str
    entity_id: int
    timestamp: str
    data: Dict[str, Any]
    source: str = "pensieve"


class EventHandler:
    """Base class for Pensieve event handlers."""
    
    def __init__(self, event_types: List[str]):
        self.event_types = event_types
        self.enabled = True
    
    async def handle_event(self, event: PensieveEvent) -> None:
        """Handle a Pensieve event."""
        if not self.enabled or event.event_type not in self.event_types:
            return
        
        try:
            await self._process_event(event)
        except Exception as e:
            logger.error(f"Error handling event {event.event_type}: {e}")
    
    async def _process_event(self, event: PensieveEvent) -> None:
        """Override this method to process specific events."""
        raise NotImplementedError


class ScreenshotEventHandler(EventHandler):
    """Handles new screenshot events for immediate processing."""
    
    def __init__(self):
        super().__init__(["screenshot.created", "entity.created"])
        self.task_extractor = None
        self.dashboard_notifier = None
    
    def set_task_extractor(self, extractor):
        """Set task extractor for immediate processing."""
        self.task_extractor = extractor
    
    def set_dashboard_notifier(self, notifier):
        """Set dashboard notifier for real-time updates."""
        self.dashboard_notifier = notifier
    
    async def _process_event(self, event: PensieveEvent) -> None:
        """Process new screenshot events."""
        entity_id = event.entity_id
        logger.info(f"Processing new screenshot entity: {entity_id}")
        
        try:
            # Get screenshot data from Pensieve
            api_client = get_pensieve_client()
            entity = api_client.get_entity(entity_id)
            
            if not entity:
                logger.warning(f"Could not retrieve entity {entity_id}")
                return
            
            # Extract OCR text
            metadata = api_client.get_entity_metadata(entity_id)
            ocr_text = metadata.get('ocr_result', '')
            
            if not ocr_text:
                logger.debug(f"No OCR text available for entity {entity_id}")
                return
            
            # Extract tasks immediately if extractor is available
            if self.task_extractor:
                tasks = await self._extract_tasks_async(ocr_text)
                if tasks:
                    # Store tasks back to Pensieve
                    api_client.store_entity_metadata(entity_id, 'tasks', json.dumps(tasks))
                    api_client.store_entity_metadata(entity_id, 'processed_at', datetime.now().isoformat())
                    
                    logger.info(f"Extracted {len(tasks)} tasks from entity {entity_id}")
                    
                    # Notify dashboards of new tasks
                    if self.dashboard_notifier:
                        await self.dashboard_notifier.notify_new_tasks(entity_id, tasks)
                        
        except Exception as e:
            logger.error(f"Failed to process screenshot event for entity {entity_id}: {e}")
    
    async def _extract_tasks_async(self, ocr_text: str) -> List[Dict[str, Any]]:
        """Extract tasks asynchronously."""
        if not self.task_extractor:
            return []
        
        try:
            # Run task extraction in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            tasks = await loop.run_in_executor(None, self.task_extractor.extract_tasks, ocr_text)
            return tasks or []
        except Exception as e:
            logger.error(f"Task extraction failed: {e}")
            return []


class MetadataEventHandler(EventHandler):
    """Handles metadata update events."""
    
    def __init__(self):
        super().__init__(["metadata.updated", "metadata.created"])
        self.cache_manager = None
    
    def set_cache_manager(self, cache_manager):
        """Set cache manager for invalidation."""
        self.cache_manager = cache_manager
    
    async def _process_event(self, event: PensieveEvent) -> None:
        """Process metadata update events."""
        entity_id = event.entity_id
        
        # Invalidate cache for this entity
        if self.cache_manager:
            self.cache_manager.invalidate_entity(entity_id)
            logger.debug(f"Invalidated cache for entity {entity_id}")
        
        # Log metadata update
        metadata_key = event.data.get('key', 'unknown')
        logger.info(f"Metadata updated for entity {entity_id}: {metadata_key}")


class DashboardNotifier:
    """Notifies dashboards of real-time updates."""
    
    def __init__(self):
        self.websocket_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.webhook_urls: List[str] = []
        self.server = None
        self.server_task = None
    
    async def start_websocket_server(self, port: int = 8841):
        """Start WebSocket server for dashboard notifications."""
        try:
            self.server = await websockets.serve(
                self._handle_websocket_connection,
                "localhost",
                port
            )
            logger.info(f"Dashboard WebSocket server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def stop_websocket_server(self):
        """Stop WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Dashboard WebSocket server stopped")
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle new WebSocket connection from dashboard."""
        self.websocket_clients.add(websocket)
        logger.info(f"Dashboard connected via WebSocket: {websocket.remote_address}")
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "Real-time updates enabled",
                "timestamp": datetime.now().isoformat()
            }))
            
            # Keep connection alive
            await websocket.wait_closed()
        except (ConnectionClosedError, ConnectionClosedOK) as e:
            logger.debug(f"WebSocket connection closed normally: {type(e).__name__}")
        finally:
            self.websocket_clients.discard(websocket)
            logger.info("Dashboard disconnected from WebSocket")
    
    async def notify_new_tasks(self, entity_id: int, tasks: List[Dict[str, Any]]):
        """Notify dashboards of new tasks."""
        notification = {
            "type": "new_tasks",
            "entity_id": entity_id,
            "tasks": tasks,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_notification(notification)
    
    async def notify_entity_update(self, entity_id: int, update_type: str, data: Dict[str, Any]):
        """Notify dashboards of entity updates."""
        notification = {
            "type": "entity_update",
            "entity_id": entity_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_notification(notification)
    
    async def _broadcast_notification(self, notification: Dict[str, Any]):
        """Broadcast notification to all connected clients."""
        message = json.dumps(notification)
        
        # Send to WebSocket clients
        disconnected_clients = set()
        for client in self.websocket_clients:
            try:
                await client.send(message)
            except (ConnectionClosedError, ConnectionClosedOK):
                disconnected_clients.add(client)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket notification: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected_clients
        
        # Send to webhook URLs
        for webhook_url in self.webhook_urls:
            try:
                requests.post(webhook_url, json=notification, timeout=5)
            except Exception as e:
                logger.warning(f"Failed to send webhook notification to {webhook_url}: {e}")
    
    def add_webhook_url(self, url: str):
        """Add webhook URL for notifications."""
        if url not in self.webhook_urls:
            self.webhook_urls.append(url)
            logger.info(f"Added webhook URL: {url}")


class PensieveEventIntegrator:
    """Main class for Pensieve real-time event integration."""
    
    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.dashboard_notifier = DashboardNotifier()
        self.websocket_client = None
        self.polling_task = None
        self.running = False
        
        # Initialize default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default event handlers."""
        # Screenshot handler
        screenshot_handler = ScreenshotEventHandler()
        screenshot_handler.set_dashboard_notifier(self.dashboard_notifier)
        self.register_handler(screenshot_handler)
        
        # Metadata handler
        metadata_handler = MetadataEventHandler()
        # Set cache manager if available
        try:
            from autotasktracker.pensieve.cache_manager import get_cache_manager
            metadata_handler.set_cache_manager(get_cache_manager())
        except Exception as e:
            logger.debug(f"Cache manager not available for metadata handler: {e}")
        self.register_handler(metadata_handler)
    
    def register_handler(self, handler: EventHandler):
        """Register an event handler."""
        for event_type in handler.event_types:
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(handler)
            logger.info(f"Registered handler for event type: {event_type}")
    
    def set_task_extractor(self, extractor):
        """Set task extractor for screenshot processing."""
        for handlers in self.handlers.values():
            for handler in handlers:
                if isinstance(handler, ScreenshotEventHandler):
                    handler.set_task_extractor(extractor)
    
    async def start_integration(self):
        """Start real-time event integration."""
        if self.running:
            logger.warning("Event integration already running")
            return
        
        self.running = True
        logger.info("Starting Pensieve event integration")
        
        # Start dashboard notification server
        await self.dashboard_notifier.start_websocket_server()
        
        # Try WebSocket connection first, fallback to polling
        try:
            await self._start_websocket_integration()
        except Exception as e:
            logger.warning(f"WebSocket integration failed: {e}")
            logger.info("Falling back to polling mode")
            await self._start_polling_integration()
    
    async def stop_integration(self):
        """Stop real-time event integration."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping Pensieve event integration")
        
        # Stop WebSocket client
        if self.websocket_client:
            await self.websocket_client.close()
        
        # Stop polling task
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                logger.debug("Polling task cancelled successfully")
        
        # Stop dashboard server
        await self.dashboard_notifier.stop_websocket_server()
    
    async def _start_websocket_integration(self):
        """Start WebSocket integration with Pensieve."""
        config = get_synced_config()
        ws_url = config.api_base_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
        
        logger.info(f"Connecting to Pensieve WebSocket: {ws_url}")
        
        while self.running:
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.websocket_client = websocket
                    logger.info("Connected to Pensieve WebSocket")
                    
                    async for message in websocket:
                        if not self.running:
                            break
                        
                        try:
                            event_data = json.loads(message)
                            event = PensieveEvent(
                                event_type=event_data.get('type', 'unknown'),
                                entity_id=event_data.get('entity_id', 0),
                                timestamp=event_data.get('timestamp', datetime.now().isoformat()),
                                data=event_data.get('data', {}),
                                source="websocket"
                            )
                            
                            await self._process_event(event)
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid WebSocket message: {e}")
                        except Exception as e:
                            logger.error(f"Error processing WebSocket event: {e}")
            
            except (ConnectionClosedError, ConnectionClosedOK):
                if self.running:
                    logger.warning("WebSocket connection lost, reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
            except Exception as e:
                if self.running:
                    logger.error(f"WebSocket error: {e}")
                    await asyncio.sleep(10)
    
    async def _start_polling_integration(self):
        """Start polling-based integration as fallback."""
        logger.info("Starting polling-based event integration")
        
        last_check = time.time()
        api_client = get_pensieve_client()
        
        while self.running:
            try:
                # Check for new entities since last check
                current_time = time.time()
                
                if api_client.is_healthy():
                    # Get recent entities (polling simulation)
                    entities = api_client.get_entities(limit=10)
                    
                    for entity in entities:
                        # Simple time-based check for "new" entities
                        entity_time = datetime.fromisoformat(entity.created_at.replace('Z', '+00:00'))
                        if entity_time.timestamp() > last_check:
                            # Create synthetic event
                            event = PensieveEvent(
                                event_type="entity.created",
                                entity_id=entity.id,
                                timestamp=entity.created_at,
                                data={"filepath": entity.filepath},
                                source="polling"
                            )
                            
                            await self._process_event(event)
                
                last_check = current_time
                await asyncio.sleep(10)  # Poll every 10 seconds
                
            except Exception as e:
                logger.error(f"Polling integration error: {e}")
                await asyncio.sleep(30)  # Longer delay on error
    
    async def _process_event(self, event: PensieveEvent):
        """Process an event through registered handlers."""
        logger.debug(f"Processing event: {event.event_type} for entity {event.entity_id}")
        
        handlers = self.handlers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers registered for event type: {event.event_type}")
            return
        
        # Process event through all registered handlers
        for handler in handlers:
            try:
                await handler.handle_event(event)
            except Exception as e:
                logger.error(f"Handler {handler.__class__.__name__} failed: {e}")


# Global instance
_event_integrator: Optional[PensieveEventIntegrator] = None


def get_event_integrator() -> PensieveEventIntegrator:
    """Get global event integrator instance."""
    global _event_integrator
    if _event_integrator is None:
        _event_integrator = PensieveEventIntegrator()
    return _event_integrator


def start_event_integration():
    """Start event integration in background thread."""
    integrator = get_event_integrator()
    
    def run_integration():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(integrator.start_integration())
        except Exception as e:
            logger.error(f"Event integration thread failed: {e}")
        finally:
            loop.close()
    
    integration_thread = threading.Thread(target=run_integration, daemon=True)
    integration_thread.start()
    logger.info("Started event integration in background thread")


def reset_event_integrator():
    """Reset event integrator (useful for testing)."""
    global _event_integrator
    if _event_integrator and _event_integrator.running:
        # Note: Can't await in sync function, would need proper shutdown
        logger.warning("Event integrator reset while running")
    _event_integrator = None