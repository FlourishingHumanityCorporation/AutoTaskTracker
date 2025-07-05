"""
Configuration Change Event System for AutoTaskTracker.

This module provides real-time configuration change notifications, event-driven
updates, and reactive configuration management for dynamic system behavior.
"""

import logging
import asyncio
import threading
import json
from typing import Dict, Any, List, Callable, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class ConfigEventType(Enum):
    """Types of configuration events."""
    CONFIG_LOADED = "config_loaded"
    CONFIG_RELOADED = "config_reloaded"
    CONFIG_CHANGED = "config_changed"
    FEATURE_ENABLED = "feature_enabled"
    FEATURE_DISABLED = "feature_disabled"
    PENSIEVE_INTEGRATION_CHANGED = "pensieve_integration_changed"
    PORT_CHANGED = "port_changed"
    DATABASE_CHANGED = "database_changed"
    AI_CONFIG_CHANGED = "ai_config_changed"


@dataclass
class ConfigEvent:
    """Configuration change event."""
    event_type: ConfigEventType
    key: str
    old_value: Any = None
    new_value: Any = None
    source: str = "system"
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return {
            'event_type': self.event_type.value,
            'key': self.key,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigEvent':
        """Create event from dictionary."""
        return cls(
            event_type=ConfigEventType(data['event_type']),
            key=data['key'],
            old_value=data.get('old_value'),
            new_value=data.get('new_value'),
            source=data.get('source', 'system'),
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


class ConfigEventHandler:
    """Base class for configuration event handlers."""
    
    def handle_event(self, event: ConfigEvent) -> bool:
        """Handle a configuration event.
        
        Args:
            event: The configuration event
            
        Returns:
            bool: True if event was handled successfully
        """
        raise NotImplementedError
    
    def can_handle(self, event: ConfigEvent) -> bool:
        """Check if this handler can process the event.
        
        Args:
            event: The configuration event
            
        Returns:
            bool: True if this handler can process the event
        """
        return True


class PortChangeHandler(ConfigEventHandler):
    """Handler for port configuration changes."""
    
    def handle_event(self, event: ConfigEvent) -> bool:
        """Handle port change events."""
        if event.event_type == ConfigEventType.PORT_CHANGED:
            logger.info(f"Port changed: {event.key} from {event.old_value} to {event.new_value}")
            # Could trigger dashboard restarts, proxy updates, etc.
            return True
        return False
    
    def can_handle(self, event: ConfigEvent) -> bool:
        """Check if this is a port-related event."""
        return event.event_type == ConfigEventType.PORT_CHANGED or 'port' in event.key.lower()


class FeatureToggleHandler(ConfigEventHandler):
    """Handler for feature toggle changes."""
    
    def handle_event(self, event: ConfigEvent) -> bool:
        """Handle feature toggle events."""
        if event.event_type in [ConfigEventType.FEATURE_ENABLED, ConfigEventType.FEATURE_DISABLED]:
            feature_name = event.key
            enabled = event.event_type == ConfigEventType.FEATURE_ENABLED
            
            logger.info(f"Feature {'enabled' if enabled else 'disabled'}: {feature_name}")
            
            # Apply feature-specific actions
            if feature_name == 'vlm_processing':
                self._handle_vlm_toggle(enabled)
            elif feature_name == 'real_time_processing':
                self._handle_realtime_toggle(enabled)
            elif feature_name == 'notifications':
                self._handle_notifications_toggle(enabled)
            
            return True
        return False
    
    def _handle_vlm_toggle(self, enabled: bool):
        """Handle VLM processing toggle."""
        if enabled:
            logger.info("Starting VLM processing services")
            # Could start VLM workers, warm up models, etc.
        else:
            logger.info("Stopping VLM processing services")
            # Could stop VLM workers, release model memory, etc.
    
    def _handle_realtime_toggle(self, enabled: bool):
        """Handle real-time processing toggle."""
        if enabled:
            logger.info("Enabling real-time processing")
            # Could start WebSocket connections, streaming APIs, etc.
        else:
            logger.info("Disabling real-time processing")
            # Could stop streaming, switch to polling, etc.
    
    def _handle_notifications_toggle(self, enabled: bool):
        """Handle notifications toggle."""
        if enabled:
            logger.info("Enabling notifications")
        else:
            logger.info("Disabling notifications")


class PensieveIntegrationHandler(ConfigEventHandler):
    """Handler for Pensieve integration changes."""
    
    def handle_event(self, event: ConfigEvent) -> bool:
        """Handle Pensieve integration events."""
        if event.event_type == ConfigEventType.PENSIEVE_INTEGRATION_CHANGED:
            logger.info(f"Pensieve integration changed: {event.key}")
            
            if event.key == 'api_enabled':
                self._handle_api_toggle(event.new_value)
            elif event.key == 'backend_type':
                self._handle_backend_change(event.old_value, event.new_value)
            
            return True
        return False
    
    def _handle_api_toggle(self, enabled: bool):
        """Handle Pensieve API enable/disable."""
        if enabled:
            logger.info("Pensieve API enabled - switching to API-first mode")
            # Could reinitialize API clients, clear direct DB connections
        else:
            logger.info("Pensieve API disabled - falling back to direct DB access")
            # Could close API connections, reinitialize direct DB access


class ConfigEventBus:
    """Event bus for configuration change notifications."""
    
    def __init__(self):
        self._handlers: List[ConfigEventHandler] = []
        self._event_queue = Queue()
        self._processing_thread: Optional[threading.Thread] = None
        self._running = False
        self._async_handlers: List[Callable] = []
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self.register_handler(PortChangeHandler())
        self.register_handler(FeatureToggleHandler())
        self.register_handler(PensieveIntegrationHandler())
    
    def register_handler(self, handler: ConfigEventHandler):
        """Register a configuration event handler."""
        self._handlers.append(handler)
        logger.debug(f"Registered config event handler: {handler.__class__.__name__}")
    
    def register_async_handler(self, handler: Callable):
        """Register an async configuration event handler."""
        self._async_handlers.append(handler)
        logger.debug(f"Registered async config event handler: {handler.__name__}")
    
    def emit_event(self, event: ConfigEvent):
        """Emit a configuration event."""
        self._event_queue.put(event)
        logger.debug(f"Emitted config event: {event.event_type.value} - {event.key}")
    
    def emit_config_change(self, key: str, old_value: Any, new_value: Any, source: str = "system"):
        """Emit a configuration change event."""
        event = ConfigEvent(
            event_type=ConfigEventType.CONFIG_CHANGED,
            key=key,
            old_value=old_value,
            new_value=new_value,
            source=source
        )
        self.emit_event(event)
    
    def emit_feature_toggle(self, feature: str, enabled: bool, source: str = "system"):
        """Emit a feature toggle event."""
        event_type = ConfigEventType.FEATURE_ENABLED if enabled else ConfigEventType.FEATURE_DISABLED
        event = ConfigEvent(
            event_type=event_type,
            key=feature,
            new_value=enabled,
            source=source
        )
        self.emit_event(event)
    
    def emit_port_change(self, service: str, old_port: int, new_port: int, source: str = "system"):
        """Emit a port change event."""
        event = ConfigEvent(
            event_type=ConfigEventType.PORT_CHANGED,
            key=f"{service}_port",
            old_value=old_port,
            new_value=new_port,
            source=source
        )
        self.emit_event(event)
    
    def start_processing(self):
        """Start event processing in background thread."""
        if self._running:
            return
        
        self._running = True
        self._processing_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processing_thread.start()
        logger.info("Started configuration event processing")
    
    def stop_processing(self):
        """Stop event processing."""
        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=5)
        logger.info("Stopped configuration event processing")
    
    def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1)
                self._handle_event(event)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing configuration event: {e}")
    
    def _handle_event(self, event: ConfigEvent):
        """Handle a single event with all registered handlers."""
        handled = False
        
        # Process with sync handlers
        for handler in self._handlers:
            try:
                if handler.can_handle(event):
                    result = handler.handle_event(event)
                    if result:
                        handled = True
            except Exception as e:
                logger.error(f"Error in config event handler {handler.__class__.__name__}: {e}")
        
        # Process with async handlers
        if self._async_handlers:
            asyncio.run(self._handle_async_event(event))
        
        if not handled:
            logger.debug(f"No handler found for config event: {event.event_type.value}")
    
    async def _handle_async_event(self, event: ConfigEvent):
        """Handle event with async handlers."""
        for handler in self._async_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in async config event handler: {e}")
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent event history."""
        # This would be implemented with persistent storage in production
        return []


# Global event bus instance
_config_event_bus = None

def get_config_event_bus() -> ConfigEventBus:
    """Get the global configuration event bus."""
    global _config_event_bus
    if _config_event_bus is None:
        _config_event_bus = ConfigEventBus()
    return _config_event_bus

def start_config_event_system():
    """Start the configuration event system."""
    bus = get_config_event_bus()
    bus.start_processing()

def stop_config_event_system():
    """Stop the configuration event system."""
    bus = get_config_event_bus()
    bus.stop_processing()

def emit_config_event(event_type: str, key: str, old_value: Any = None, new_value: Any = None, source: str = "system"):
    """Emit a configuration event."""
    bus = get_config_event_bus()
    event = ConfigEvent(
        event_type=ConfigEventType(event_type),
        key=key,
        old_value=old_value,
        new_value=new_value,
        source=source
    )
    bus.emit_event(event)