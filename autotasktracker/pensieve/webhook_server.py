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

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

from autotasktracker.pensieve.event_processor import get_event_processor, PensieveEvent
from autotasktracker.pensieve.cache_manager import get_cache_manager
from autotasktracker.core import DatabaseManager

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    """Webhook payload from Pensieve."""
    event_type: str
    entity_id: int
    timestamp: str
    data: Dict[str, Any]
    source: str = "pensieve_webhook"


@dataclass
class WebhookStats:
    """Webhook processing statistics."""
    requests_received: int = 0
    requests_processed: int = 0
    requests_failed: int = 0
    last_request_time: Optional[datetime] = None
    average_processing_time_ms: float = 0.0
    uptime_seconds: float = 0.0


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
        self.db_manager = DatabaseManager(use_pensieve_api=True)
        
        # Threading for background processing
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="WebhookProcessor")
        
        # Request handlers
        self.handlers: Dict[str, List[Callable[[PensieveEvent], None]]] = {}
        
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
                "stats": asdict(self.stats)
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
            return asdict(self.stats)
        
        @self.app.get("/handlers")
        async def get_handlers():
            """Get registered webhook handlers."""
            return {
                event_type: len(handlers) 
                for event_type, handlers in self.handlers.items()
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