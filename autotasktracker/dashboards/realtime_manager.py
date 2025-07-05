"""Real-time manager for dashboard webhook integration."""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from autotasktracker.pensieve.webhook_server import get_webhook_server, start_webhook_server
from autotasktracker.dashboards.websocket_client import DashboardWebSocketClient
from autotasktracker.pensieve.event_processor import PensieveEvent

logger = logging.getLogger(__name__)


class RealTimeManager:
    """Manages real-time updates for dashboards via webhook integration."""
    
    def __init__(self, dashboard_id: str = "task_board"):
        """Initialize real-time manager.
        
        Args:
            dashboard_id: Unique identifier for the dashboard
        """
        self.dashboard_id = dashboard_id
        self.webhook_server: Optional[object] = None
        self.websocket_client: Optional[DashboardWebSocketClient] = None
        self.is_running = False
        self._lock = threading.Lock()
        
        # Event statistics
        self.events_received = 0
        self.last_event_time: Optional[datetime] = None
        
        # Event handlers
        self.event_handlers: Dict[str, Callable] = {}
    
    def start(self) -> bool:
        """Start real-time webhook integration.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        with self._lock:
            if self.is_running:
                logger.warning("Real-time manager already running")
                return True
            
            try:
                # Start webhook server
                self.webhook_server = start_webhook_server(
                    host="127.0.0.1", 
                    port=8840, 
                    background=True
                )
                
                # Register event handlers
                self._register_webhook_handlers()
                
                # Initialize WebSocket client
                self.websocket_client = DashboardWebSocketClient(
                    dashboard_id=self.dashboard_id,
                    host="localhost",
                    port=8841
                )
                
                self.is_running = True
                logger.info(f"Real-time manager started for dashboard {self.dashboard_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start real-time manager: {e}")
                return False
    
    def stop(self):
        """Stop real-time webhook integration."""
        with self._lock:
            if not self.is_running:
                return
            
            try:
                # Stop WebSocket client
                if self.websocket_client:
                    self.websocket_client.disconnect()
                    self.websocket_client = None
                
                # Note: We don't stop the webhook server as other dashboards might use it
                
                self.is_running = False
                logger.info("Real-time manager stopped")
                
            except Exception as e:
                logger.error(f"Error stopping real-time manager: {e}")
    
    def _register_webhook_handlers(self):
        """Register webhook event handlers."""
        if not self.webhook_server:
            return
        
        # Handler for new entity processing
        def handle_entity_processed(event: PensieveEvent):
            """Handle entity processed events."""
            self.events_received += 1
            self.last_event_time = datetime.now()
            
            logger.info(f"Entity {event.entity_id} processed - triggering dashboard update")
            
            # Trigger dashboard update
            self._trigger_dashboard_update({
                'event_type': 'entity_processed',
                'entity_id': event.entity_id,
                'timestamp': event.timestamp.isoformat(),
                'message': f"Screenshot {event.entity_id} processed"
            })
        
        # Handler for task extraction
        def handle_task_extracted(event: PensieveEvent):
            """Handle task extraction events."""
            self.events_received += 1
            self.last_event_time = datetime.now()
            
            logger.info(f"Tasks extracted for entity {event.entity_id}")
            
            # Trigger dashboard update with task info
            self._trigger_dashboard_update({
                'event_type': 'task_extracted',
                'entity_id': event.entity_id,
                'timestamp': event.timestamp.isoformat(),
                'message': f"New tasks extracted from screenshot {event.entity_id}"
            })
        
        # Register handlers with webhook server
        self.webhook_server.register_handler("entity_processed", handle_entity_processed)
        self.webhook_server.register_handler("task_extracted", handle_task_extracted)
        
        logger.info("Registered webhook handlers for real-time updates")
    
    def _trigger_dashboard_update(self, update_data: Dict[str, Any]):
        """Trigger dashboard update via WebSocket or session state."""
        try:
            # Try WebSocket first
            if self.websocket_client and self.websocket_client.connected:
                self.websocket_client.send_message({
                    'type': 'dashboard_update',
                    'data': update_data
                })
            else:
                # Fallback: Store in session-like cache for dashboard polling
                self._store_update_for_polling(update_data)
                
        except Exception as e:
            logger.error(f"Failed to trigger dashboard update: {e}")
    
    def _store_update_for_polling(self, update_data: Dict[str, Any]):
        """Store update data for dashboard polling fallback."""
        # This would integrate with Streamlit session state or a cache
        # For now, just log it
        logger.info(f"Stored update for polling: {update_data}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get real-time manager statistics."""
        return {
            'running': self.is_running,
            'events_received': self.events_received,
            'last_event_time': self.last_event_time.isoformat() if self.last_event_time else None,
            'webhook_server_running': self.webhook_server is not None,
            'websocket_connected': self.websocket_client.connected if self.websocket_client else False
        }
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register custom event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Callback function to handle the event
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered custom handler for event type: {event_type}")


# Global instance
_global_realtime_manager: Optional[RealTimeManager] = None


def get_realtime_manager(dashboard_id: str = "task_board") -> RealTimeManager:
    """Get global real-time manager instance."""
    global _global_realtime_manager
    if _global_realtime_manager is None:
        _global_realtime_manager = RealTimeManager(dashboard_id)
    return _global_realtime_manager


def start_realtime_integration(dashboard_id: str = "task_board") -> bool:
    """Start real-time integration for a dashboard.
    
    Args:
        dashboard_id: Dashboard identifier
        
    Returns:
        bool: True if started successfully
    """
    manager = get_realtime_manager(dashboard_id)
    return manager.start()


def stop_realtime_integration():
    """Stop real-time integration."""
    global _global_realtime_manager
    if _global_realtime_manager:
        _global_realtime_manager.stop()
        _global_realtime_manager = None