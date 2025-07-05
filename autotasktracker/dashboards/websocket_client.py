"""
WebSocket client for real-time dashboard updates.
from autotasktracker.core import DatabaseManager
Replaces polling-based refresh with true WebSocket event listening.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Callable, Dict, Any, Optional, Set
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK, InvalidURI
import streamlit as st

logger = logging.getLogger(__name__)


class DashboardWebSocketClient:
    """WebSocket client for receiving real-time dashboard updates."""
    
    def __init__(self, dashboard_id: str, host: str = "localhost", port: int = 8841):
        """Initialize WebSocket client.
        
        Args:
            dashboard_id: Unique identifier for this dashboard
            host: WebSocket server host
            port: WebSocket server port
        """
        self.dashboard_id = dashboard_id
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Event handlers
        self.event_handlers: Dict[str, Set[Callable]] = {
            'new_tasks': set(),
            'entity_update': set(),
            'connected': set(),
            'disconnected': set(),
            'error': set()
        }
        
        # Background tasks
        self.client_task: Optional[asyncio.Task] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        
        # Metrics
        self.last_ping = None
        self.messages_received = 0
        self.connection_start_time = None
        
    def start(self) -> bool:
        """Start WebSocket client in background thread.
        
        Returns:
            True if client started successfully, False otherwise
        """
        if self.connected or self.loop_thread:
            logger.warning(f"WebSocket client {self.dashboard_id} already running")
            return True
            
        try:
            # Start event loop in background thread
            self.loop_thread = threading.Thread(
                target=self._run_event_loop,
                name=f"WebSocket-{self.dashboard_id}",
                daemon=True
            )
            self.loop_thread.start()
            
            # Wait a moment for connection
            time.sleep(0.5)
            
            logger.info(f"WebSocket client {self.dashboard_id} started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket client {self.dashboard_id}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect WebSocket client (alias for stop)."""
        self.stop()
    
    def stop(self):
        """Stop WebSocket client and cleanup resources."""
        try:
            if self.client_task and not self.client_task.done():
                self.client_task.cancel()
            
            if self.websocket and not self.websocket.closed:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.close(),
                    self.event_loop
                ).result(timeout=2.0)
            
            self.connected = False
            logger.info(f"WebSocket client {self.dashboard_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping WebSocket client {self.dashboard_id}: {e}")
    
    def _run_event_loop(self):
        """Run event loop in background thread."""
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        
        try:
            self.event_loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            logger.error(f"Event loop error for {self.dashboard_id}: {e}")
        finally:
            self.event_loop.close()
    
    async def _connect_and_listen(self):
        """Connect to WebSocket server and listen for events."""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Connecting WebSocket client {self.dashboard_id} to {self.uri}")
                
                async with websockets.connect(
                    self.uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                ) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    self.reconnect_attempts = 0
                    self.connection_start_time = datetime.now()
                    
                    logger.info(f"WebSocket client {self.dashboard_id} connected successfully")
                    await self._trigger_event('connected', {'dashboard_id': self.dashboard_id})
                    
                    # Listen for messages
                    async for message in websocket:
                        await self._handle_message(message)
                        
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                logger.info(f"WebSocket {self.dashboard_id} connection closed: {type(e).__name__}")
                break
                
            except (ConnectionRefusedError, InvalidURI, OSError) as e:
                self.reconnect_attempts += 1
                logger.warning(
                    f"WebSocket {self.dashboard_id} connection failed "
                    f"(attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}): {e}"
                )
                
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    wait_time = min(2 ** self.reconnect_attempts, 30)  # Exponential backoff
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket {self.dashboard_id}: {e}")
                break
        
        # Connection ended
        self.connected = False
        await self._trigger_event('disconnected', {'dashboard_id': self.dashboard_id})
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            event_type = data.get('type', 'unknown')
            
            self.messages_received += 1
            self.last_ping = datetime.now()
            
            logger.debug(f"WebSocket {self.dashboard_id} received {event_type} event")
            
            # Trigger registered event handlers
            await self._trigger_event(event_type, data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in WebSocket message for {self.dashboard_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message for {self.dashboard_id}: {e}")
            await self._trigger_event('error', {'error': str(e)})
    
    async def _trigger_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger event handlers for given event type."""
        handlers = self.event_handlers.get(event_type, set())
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    # Run sync handler in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler, data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def add_event_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Add event handler for specific event type.
        
        Args:
            event_type: Type of event ('new_tasks', 'entity_update', etc.)
            handler: Function to call when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = set()
        
        self.event_handlers[event_type].add(handler)
        logger.debug(f"Added {event_type} handler to WebSocket client {self.dashboard_id}")
    
    def remove_event_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Remove event handler."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].discard(handler)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and metrics."""
        uptime = None
        if self.connection_start_time and self.connected:
            uptime = (datetime.now() - self.connection_start_time).total_seconds()
        
        return {
            'connected': self.connected,
            'dashboard_id': self.dashboard_id,
            'uri': self.uri,
            'messages_received': self.messages_received,
            'last_ping': self.last_ping.isoformat() if self.last_ping else None,
            'uptime_seconds': uptime,
            'reconnect_attempts': self.reconnect_attempts
        }


class StreamlitWebSocketMixin:
    """Mixin for Streamlit dashboards to add WebSocket event handling."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket_client: Optional[DashboardWebSocketClient] = None
        self._setup_websocket_client()
    
    def _setup_websocket_client(self):
        """Setup WebSocket client for real-time updates."""
        dashboard_id = getattr(self, 'dashboard_id', self.__class__.__name__)
        
        # Initialize WebSocket client
        self.websocket_client = DashboardWebSocketClient(dashboard_id)
        
        # Register event handlers
        self.websocket_client.add_event_handler('new_tasks', self._handle_new_tasks)
        self.websocket_client.add_event_handler('entity_update', self._handle_entity_update)
        self.websocket_client.add_event_handler('connected', self._handle_websocket_connected)
        self.websocket_client.add_event_handler('disconnected', self._handle_websocket_disconnected)
        
        # Start client
        self.websocket_client.start()
    
    def _handle_new_tasks(self, data: Dict[str, Any]):
        """Handle new tasks event from WebSocket."""
        logger.info(f"Dashboard {self.websocket_client.dashboard_id} received new tasks")
        
        # Trigger Streamlit rerun for real-time update
        if 'st' in globals():
            st.rerun()
    
    def _handle_entity_update(self, data: Dict[str, Any]):
        """Handle entity update event from WebSocket."""
        entity_id = data.get('entity_id')
        update_type = data.get('update_type', 'unknown')
        
        logger.info(f"Dashboard {self.websocket_client.dashboard_id} received entity update: {entity_id} ({update_type})")
        
        # Trigger Streamlit rerun for real-time update
        if 'st' in globals():
            st.rerun()
    
    def _handle_websocket_connected(self, data: Dict[str, Any]):
        """Handle WebSocket connection established."""
        logger.info(f"Dashboard {self.websocket_client.dashboard_id} WebSocket connected")
        
        # Store connection status in session state
        if hasattr(st, 'session_state'):
            st.session_state.websocket_connected = True
            st.session_state.websocket_status = "Connected"
    
    def _handle_websocket_disconnected(self, data: Dict[str, Any]):
        """Handle WebSocket connection lost."""
        logger.warning(f"Dashboard {self.websocket_client.dashboard_id} WebSocket disconnected")
        
        # Store connection status in session state
        if hasattr(st, 'session_state'):
            st.session_state.websocket_connected = False
            st.session_state.websocket_status = "Disconnected"
    
    def get_websocket_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status for display."""
        if not self.websocket_client:
            return {'connected': False, 'status': 'Not initialized'}
        
        return self.websocket_client.get_connection_status()
    
    def cleanup_websocket(self):
        """Cleanup WebSocket client resources."""
        if self.websocket_client:
            self.websocket_client.stop()
            self.websocket_client = None


def get_websocket_client_for_dashboard(dashboard_id: str) -> DashboardWebSocketClient:
    """Get or create WebSocket client for dashboard.
    
    Args:
        dashboard_id: Unique dashboard identifier
        
    Returns:
        WebSocket client instance
    """
    # Use session state to persist client across reruns
    if hasattr(st, 'session_state'):
        client_key = f"websocket_client_{dashboard_id}"
        
        if client_key not in st.session_state:
            st.session_state[client_key] = DashboardWebSocketClient(dashboard_id)
            st.session_state[client_key].start()
        
        return st.session_state[client_key]
    else:
        # Fallback for non-Streamlit environments
        return DashboardWebSocketClient(dashboard_id)