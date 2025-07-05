"""
Webhook server for true real-time processing integration with Pensieve.

This module provides webhook endpoints that Pensieve can call directly
when events occur, enabling sub-second response times for task extraction
and dashboard updates.
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

from autotasktracker.pensieve.event_processor import get_event_processor, PensieveEvent
from autotasktracker.pensieve.cache_manager import get_cache_manager
# DatabaseManager import moved to avoid circular dependency

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    """Webhook payload from Pensieve."""
    event_type: str
    entity_id: int
    timestamp: str
    data: Dict[str, Any]
    source: str = "pensieve_webhook"


class EventType(Enum):
    """Enhanced granular event types."""
    # Entity events
    ENTITY_CREATED = "entity.created"
    ENTITY_UPDATED = "entity.updated" 
    ENTITY_DELETED = "entity.deleted"
    ENTITY_PROCESSED = "entity.processed"
    
    # Processing events
    OCR_COMPLETED = "processing.ocr_completed"
    VLM_COMPLETED = "processing.vlm_completed"
    AI_ANALYSIS_COMPLETED = "processing.ai_analysis_completed"
    TASK_EXTRACTED = "processing.task_extracted"
    
    # System events
    SYSTEM_STATUS_CHANGED = "system.status_changed"
    ERROR_OCCURRED = "system.error_occurred"
    PERFORMANCE_ALERT = "system.performance_alert"
    
    # Dashboard events
    DASHBOARD_REFRESH_NEEDED = "dashboard.refresh_needed"
    CACHE_INVALIDATED = "dashboard.cache_invalidated"
    
    # Custom events
    CUSTOM_EVENT = "custom.event"


@dataclass
class EventFilter:
    """Filter criteria for event subscriptions."""
    entity_ids: Optional[List[int]] = None
    source_filters: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    categories: Optional[List[str]] = None
    time_window_seconds: Optional[int] = None


@dataclass
class Subscription:
    """Event subscription with enhanced filtering."""
    id: str
    event_types: List[EventType]
    handler: Callable[[PensieveEvent], None]
    filters: EventFilter
    created_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    active: bool = True


@dataclass
class WebhookStats:
    """Enhanced webhook processing statistics."""
    requests_received: int = 0
    requests_processed: int = 0
    requests_failed: int = 0
    last_request_time: Optional[datetime] = None
    average_processing_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    
    # Enhanced statistics
    events_by_type: Optional[Dict[str, int]] = None
    active_subscriptions: int = 0
    filtered_events: int = 0
    
    def __post_init__(self):
        if self.events_by_type is None:
            self.events_by_type = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'requests_received': self.requests_received,
            'requests_processed': self.requests_processed,
            'requests_failed': self.requests_failed,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'average_processing_time_ms': self.average_processing_time_ms,
            'uptime_seconds': self.uptime_seconds,
            'events_by_type': dict(self.events_by_type) if self.events_by_type else {},
            'active_subscriptions': self.active_subscriptions,
            'filtered_events': self.filtered_events
        }


class WebhookServer:
    """High-performance webhook server for real-time Pensieve integration."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8840):
        """Initialize webhook server.
        
        Args:
            host: Server host address
            port: Server port
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="AutoTaskTracker Webhook Server")
        self.stats = WebhookStats()
        self.start_time = time.time()
        
        # Components
        self.event_processor = get_event_processor()
        self.cache_manager = get_cache_manager()
        # DatabaseManager import moved to avoid circular dependency
        try:
            from autotasktracker.core.database import DatabaseManager
            self.db_manager = DatabaseManager(use_pensieve_api=True)
        except ImportError:
            logger.warning("DatabaseManager not available in webhook server")
            self.db_manager = None
        
        # Threading for background processing
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="WebhookProcessor")
        
        # Enhanced subscription management
        self.subscriptions: Dict[str, Subscription] = {}
        self.handlers: Dict[str, List[Callable[[PensieveEvent], None]]] = {}  # Keep for backward compatibility
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"Webhook server initialized on {host}:{port}")
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "uptime_seconds": time.time() - self.start_time,
                "stats": self.stats.to_dict()
            }
        
        @self.app.post("/webhook/entity/created")
        async def entity_created(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle entity created webhook."""
            return await self._process_webhook(payload, "entity_created", background_tasks)
        
        @self.app.post("/webhook/entity/updated")
        async def entity_updated(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle entity updated webhook."""
            return await self._process_webhook(payload, "entity_updated", background_tasks)
        
        @self.app.post("/webhook/entity/processed")
        async def entity_processed(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle entity processed webhook (OCR/VLM completed)."""
            return await self._process_webhook(payload, "entity_processed", background_tasks)
        
        @self.app.post("/webhook/metadata/updated")
        async def metadata_updated(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle metadata updated webhook."""
            return await self._process_webhook(payload, "metadata_updated", background_tasks)
        
        @self.app.post("/webhook/generic")
        async def generic_webhook(request: Request, background_tasks: BackgroundTasks):
            """Generic webhook endpoint for any Pensieve event."""
            try:
                data = await request.json()
                payload = WebhookPayload(**data)
                return await self._process_webhook(payload, "generic", background_tasks)
            except Exception as e:
                logger.error(f"Failed to parse generic webhook: {e}")
                raise HTTPException(status_code=400, detail="Invalid payload")
        
        @self.app.get("/stats")
        async def get_stats():
            """Get webhook processing statistics."""
            self.stats.uptime_seconds = time.time() - self.start_time
            return self.stats.to_dict()
        
        @self.app.get("/handlers")
        async def get_handlers():
            """Get registered webhook handlers."""
            return {
                event_type: len(handlers) 
                for event_type, handlers in self.handlers.items()
            }
        
        @self.app.post("/webhook/autotask/tag")
        async def autotask_tag_event(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle AutoTaskTracker tagging events."""
            return await self._process_webhook(payload, "autotask_tag", background_tasks)
        
        @self.app.post("/webhook/autotask/task_extracted")
        async def autotask_task_extracted(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle task extraction completion events."""
            return await self._process_webhook(payload, "autotask_task_extracted", background_tasks)
        
        @self.app.post("/webhook/autotask/dashboard_update")
        async def autotask_dashboard_update(payload: WebhookPayload, background_tasks: BackgroundTasks):
            """Handle dashboard update events."""
            return await self._process_webhook(payload, "autotask_dashboard_update", background_tasks)
        
        @self.app.get("/webhook/endpoints")
        async def list_webhook_endpoints():
            """List all available webhook endpoints."""
            return {
                "pensieve_webhooks": [
                    "/webhook/entity/created",
                    "/webhook/entity/updated", 
                    "/webhook/entity/processed",
                    "/webhook/metadata/updated",
                    "/webhook/generic"
                ],
                "autotask_webhooks": [
                    "/webhook/autotask/tag",
                    "/webhook/autotask/task_extracted",
                    "/webhook/autotask/dashboard_update"
                ],
                "utility_endpoints": [
                    "/health",
                    "/stats",
                    "/handlers",
                    "/webhook/endpoints"
                ]
            }
    
    async def _process_webhook(self, payload: WebhookPayload, event_type: str, 
                              background_tasks: BackgroundTasks) -> JSONResponse:
        """Process incoming webhook."""
        start_time = time.time()
        self.stats.requests_received += 1
        self.stats.last_request_time = datetime.now()
        
        try:
            # Create Pensieve event
            event = PensieveEvent(
                event_type=event_type,
                entity_id=payload.entity_id,
                timestamp=datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00') if payload.timestamp.endswith('Z') else payload.timestamp),
                data=payload.data,
                source="webhook"
            )
            
            # Process in background for fast response
            background_tasks.add_task(self._handle_webhook_event, event)
            
            # Update stats
            processing_time = (time.time() - start_time) * 1000
            self._update_processing_time(processing_time)
            self.stats.requests_processed += 1
            
            return JSONResponse(
                content={
                    "status": "accepted",
                    "event_type": event_type,
                    "entity_id": payload.entity_id,
                    "processing_time_ms": processing_time
                },
                status_code=202  # Accepted for processing
            )
            
        except Exception as e:
            self.stats.requests_failed += 1
            logger.error(f"Webhook processing failed: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def _handle_webhook_event(self, event: PensieveEvent):
        """Handle webhook event in background."""
        try:
            # Invalidate relevant caches immediately
            self._invalidate_caches(event)
            
            # Call registered handlers
            handlers = self.handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Handler failed for {event.event_type}: {e}")
            
            # Default processing based on event type
            if event.event_type in ['entity_created', 'entity_processed']:
                self._handle_entity_event(event)
            elif event.event_type == 'metadata_updated':
                self._handle_metadata_event(event)
            
        except Exception as e:
            logger.error(f"Background webhook processing failed: {e}")
    
    def _invalidate_caches(self, event: PensieveEvent):
        """Invalidate relevant caches for the event."""
        entity_id = event.entity_id
        
        # Invalidate entity-specific caches
        self.cache_manager.invalidate_pattern(f"entity_{entity_id}*")
        
        # Invalidate general caches that might include this entity
        self.cache_manager.invalidate_pattern("fetch_tasks_*")
        self.cache_manager.invalidate_pattern("entities_*")
        self.cache_manager.invalidate_pattern("task_groups_*")
        
        logger.debug(f"Invalidated caches for entity {entity_id}")
    
    def _handle_entity_event(self, event: PensieveEvent):
        """Handle entity creation/processing events."""
        entity_id = event.entity_id
        
        # Trigger task extraction for processed entities
        if event.event_type == 'entity_processed':
            # Use the event processor's task extraction
            try:
                self.event_processor._trigger_task_extraction(entity_id)
                logger.info(f"Triggered task extraction for entity {entity_id} via webhook")
            except Exception as e:
                logger.error(f"Task extraction failed for entity {entity_id}: {e}")
        
        # Pre-warm caches for the new entity
        self._prewarm_entity_cache(entity_id)
    
    def _handle_metadata_event(self, event: PensieveEvent):
        """Handle metadata update events."""
        entity_id = event.entity_id
        
        # Invalidate metadata-specific caches
        self.cache_manager.invalidate_pattern(f"metadata_{entity_id}*")
        
        # Check if this is task extraction metadata
        if 'extracted_tasks' in event.data:
            logger.info(f"Task extraction metadata updated for entity {entity_id}")
            # Could trigger dashboard notifications here
    
    def _prewarm_entity_cache(self, entity_id: int):
        """Pre-warm caches for an entity."""
        try:
            # Fetch entity data to cache it
            from autotasktracker.pensieve import get_pensieve_client
            client = get_pensieve_client()
            
            entity = client.get_entity(entity_id)
            if entity:
                # Cache entity data
                cache_key = f"entity_{entity_id}"
                self.cache_manager.set(cache_key, entity, ttl=3600)
                
                # Cache metadata
                metadata = client.get_entity_metadata(entity_id)
                if metadata:
                    self.cache_manager.set(f"metadata_{entity_id}", metadata, ttl=1800)
                
                logger.debug(f"Pre-warmed cache for entity {entity_id}")
                
        except Exception as e:
            logger.warning(f"Cache pre-warming failed for entity {entity_id}: {e}")
    
    def _update_processing_time(self, processing_time_ms: float):
        """Update average processing time."""
        if self.stats.requests_processed == 0:
            self.stats.average_processing_time_ms = processing_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.average_processing_time_ms = (
                alpha * processing_time_ms + 
                (1 - alpha) * self.stats.average_processing_time_ms
            )
    
    def register_handler(self, event_type: str, handler: Callable[[PensieveEvent], None]):
        """Register a webhook event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered webhook handler for {event_type}")
    
    def unregister_handler(self, event_type: str, handler: Callable[[PensieveEvent], None]):
        """Unregister a webhook event handler."""
        if event_type in self.handlers:
            try:
                self.handlers[event_type].remove(handler)
                if not self.handlers[event_type]:
                    del self.handlers[event_type]
                logger.info(f"Unregistered webhook handler for {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for {event_type}")
    
    def subscribe(self, 
                  event_types: List[EventType], 
                  handler: Callable[[PensieveEvent], None],
                  filters: Optional[EventFilter] = None) -> str:
        """Subscribe to events with enhanced filtering.
        
        Args:
            event_types: List of event types to subscribe to
            handler: Handler function to call when events match
            filters: Optional event filters
            
        Returns:
            Subscription ID for management
        """
        subscription_id = str(uuid.uuid4())
        
        subscription = Subscription(
            id=subscription_id,
            event_types=event_types,
            handler=handler,
            filters=filters or EventFilter(),
            created_at=datetime.now()
        )
        
        self.subscriptions[subscription_id] = subscription
        self.stats.active_subscriptions = len(self.subscriptions)
        
        event_names = [et.value for et in event_types]
        logger.info(f"Created subscription {subscription_id[:8]} for events: {event_names}")
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was found and removed
        """
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            self.stats.active_subscriptions = len(self.subscriptions)
            logger.info(f"Removed subscription {subscription_id[:8]}")
            return True
        else:
            logger.warning(f"Subscription {subscription_id[:8]} not found")
            return False
    
    def update_subscription(self, subscription_id: str, 
                           event_types: Optional[List[EventType]] = None,
                           filters: Optional[EventFilter] = None,
                           active: Optional[bool] = None) -> bool:
        """Update an existing subscription.
        
        Args:
            subscription_id: ID of subscription to update
            event_types: New event types (optional)
            filters: New filters (optional)
            active: New active status (optional)
            
        Returns:
            True if subscription was updated
        """
        if subscription_id not in self.subscriptions:
            logger.warning(f"Subscription {subscription_id[:8]} not found for update")
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        if event_types is not None:
            subscription.event_types = event_types
        if filters is not None:
            subscription.filters = filters
        if active is not None:
            subscription.active = active
        
        logger.info(f"Updated subscription {subscription_id[:8]}")
        return True
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get detailed subscription statistics."""
        stats = {
            'total_subscriptions': len(self.subscriptions),
            'active_subscriptions': sum(1 for s in self.subscriptions.values() if s.active),
            'inactive_subscriptions': sum(1 for s in self.subscriptions.values() if not s.active),
            'event_type_counts': defaultdict(int),
            'subscription_details': []
        }
        
        for subscription in self.subscriptions.values():
            for event_type in subscription.event_types:
                stats['event_type_counts'][event_type.value] += 1
            
            stats['subscription_details'].append({
                'id': subscription.id[:8],
                'event_types': [et.value for et in subscription.event_types],
                'trigger_count': subscription.trigger_count,
                'last_triggered': subscription.last_triggered,
                'active': subscription.active,
                'created_at': subscription.created_at
            })
        
        return stats
    
    def _matches_filters(self, event: PensieveEvent, filters: EventFilter) -> bool:
        """Check if an event matches subscription filters."""
        # Entity ID filter
        if filters.entity_ids is not None:
            if event.entity_id not in filters.entity_ids:
                return False
        
        # Source filter
        if filters.source_filters is not None:
            if not any(source in event.source for source in filters.source_filters):
                return False
        
        # Confidence filter
        if filters.min_confidence is not None:
            event_confidence = event.metadata.get('confidence', 0.0)
            if event_confidence < filters.min_confidence:
                return False
        
        # Category filter
        if filters.categories is not None:
            event_category = event.metadata.get('category')
            if event_category not in filters.categories:
                return False
        
        # Time window filter
        if filters.time_window_seconds is not None:
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            time_diff = (datetime.now() - event_time).total_seconds()
            if time_diff > filters.time_window_seconds:
                return False
        
        return True
    
    def _trigger_subscriptions(self, event: PensieveEvent, event_type: EventType):
        """Trigger matching subscriptions for an event."""
        matched_subscriptions = 0
        
        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue
            
            # Check if event type matches
            if event_type not in subscription.event_types:
                continue
            
            # Check filters
            if not self._matches_filters(event, subscription.filters):
                self.stats.filtered_events += 1
                continue
            
            # Trigger the handler
            try:
                subscription.handler(event)
                subscription.last_triggered = datetime.now()
                subscription.trigger_count += 1
                matched_subscriptions += 1
                
            except Exception as e:
                logger.error(f"Subscription {subscription.id[:8]} handler failed: {e}")
        
        if matched_subscriptions > 0:
            logger.debug(f"Triggered {matched_subscriptions} subscriptions for {event_type.value}")
    
    def start_server(self, background: bool = False):
        """Start the webhook server.
        
        Args:
            background: If True, start in background thread
        """
        config = uvicorn.Config(
            self.app, 
            host=self.host, 
            port=self.port,
            log_level="info",
            access_log=True
        )
        
        if background:
            server_thread = threading.Thread(
                target=self._run_server,
                args=(config,),
                daemon=True,
                name="WebhookServer"
            )
            server_thread.start()
            logger.info(f"Webhook server started in background on {self.host}:{self.port}")
        else:
            self._run_server(config)
    
    def _run_server(self, config):
        """Run the server with the given config."""
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
    
    def stop_server(self):
        """Stop the webhook server."""
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("Webhook server stopped")
    
    def get_webhook_urls(self) -> Dict[str, str]:
        """Get webhook URLs for Pensieve configuration.
        
        Returns:
            Dictionary of event types to webhook URLs
        """
        base_url = f"http://{self.host}:{self.port}"
        return {
            "entity_created": f"{base_url}/webhook/entity/created",
            "entity_updated": f"{base_url}/webhook/entity/updated",
            "entity_processed": f"{base_url}/webhook/entity/processed",
            "metadata_updated": f"{base_url}/webhook/metadata/updated",
            "generic": f"{base_url}/webhook/generic"
        }


# Global webhook server instance
_global_webhook_server: Optional[WebhookServer] = None


def get_webhook_server(host: str = "127.0.0.1", port: int = 8840) -> WebhookServer:
    """Get global webhook server instance."""
    global _global_webhook_server
    if _global_webhook_server is None:
        _global_webhook_server = WebhookServer(host, port)
    return _global_webhook_server


def start_webhook_server(host: str = "127.0.0.1", port: int = 8840, background: bool = True) -> WebhookServer:
    """Start the global webhook server.
    
    Args:
        host: Server host
        port: Server port
        background: Run in background thread
        
    Returns:
        WebhookServer instance
    """
    server = get_webhook_server(host, port)
    server.start_server(background=background)
    return server


def stop_webhook_server():
    """Stop the global webhook server."""
    global _global_webhook_server
    if _global_webhook_server:
        _global_webhook_server.stop_server()
        _global_webhook_server = None


# Dashboard integration for webhook monitoring
def create_webhook_dashboard_component():
    """Create Streamlit component for webhook monitoring."""
    try:
        import streamlit as st
        
        server = get_webhook_server()
        stats = server.stats
        
        st.subheader("🔗 Webhook Processing")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Requests Received", stats.requests_received)
        
        with col2:
            st.metric("Success Rate", 
                     f"{(stats.requests_processed / max(stats.requests_received, 1) * 100):.1f}%")
        
        with col3:
            st.metric("Avg Processing Time", 
                     f"{stats.average_processing_time_ms:.1f}ms")
        
        # Webhook URLs
        if st.button("Show Webhook URLs"):
            urls = server.get_webhook_urls()
            st.json(urls)
        
        # Server status
        if stats.requests_received > 0:
            st.success(f"✅ Webhook server active - Last request: {stats.last_request_time}")
        else:
            st.info("⏳ Webhook server ready - No requests received")
            
    except ImportError:
        logger.warning("Streamlit not available for webhook dashboard")


# Example usage
if __name__ == "__main__":
    # Start webhook server
    server = start_webhook_server(port=8840)
    
    # Register example handlers
    def log_entity_webhook(event: PensieveEvent):
        print(f"Webhook: {event.event_type} for entity {event.entity_id}")
    
    server.register_handler("entity_processed", log_entity_webhook)
    
    print(f"Webhook server started on http://127.0.0.1:8840")
    print("Webhook URLs:")
    for event_type, url in server.get_webhook_urls().items():
        print(f"  {event_type}: {url}")
    
    # Keep server running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_webhook_server()
        print("Webhook server stopped")