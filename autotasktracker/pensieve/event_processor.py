"""Real-time event-driven processing for Pensieve integration."""

import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass
from queue import Queue, Empty
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.core.task_extractor import get_task_extractor
from autotasktracker.core import ActivityCategorizer, DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class PensieveEvent:
    """Represents a Pensieve event."""
    event_type: str
    entity_id: int
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "pensieve"


class EventProcessor:
    """Processes Pensieve events in real-time."""
    
    def __init__(self, poll_interval: float = 1.0):
        """Initialize event processor.
        
        Args:
            poll_interval: Seconds between polling for new events
        """
        self.poll_interval = poll_interval
        self.running = False
        self.processor_thread: Optional[threading.Thread] = None
        
        # Event handling
        self.event_queue = Queue(maxsize=1000)
        self.event_handlers: Dict[str, List[Callable[[PensieveEvent], None]]] = {}
        self.last_processed_id = 0
        
        # Components
        self.pensieve_client = get_pensieve_client()
        self.health_monitor = get_health_monitor()
        self.task_extractor = get_task_extractor()
        self.categorizer = ActivityCategorizer()
        
        # Statistics
        self.events_processed = 0
        self.events_failed = 0
        self.last_event_time: Optional[datetime] = None
        
        # Setup HTTP session for SSE (if available)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def register_event_handler(self, event_type: str, handler: Callable[[PensieveEvent], None]):
        """Register an event handler for specific event types.
        
        Args:
            event_type: Type of event to handle (e.g., 'frame_added', 'frame_processed')
            handler: Function to call when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")
    
    def unregister_event_handler(self, event_type: str, handler: Callable[[PensieveEvent], None]):
        """Unregister an event handler.
        
        Args:
            event_type: Type of event
            handler: Handler function to remove
        """
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                if not self.event_handlers[event_type]:
                    del self.event_handlers[event_type]
                logger.info(f"Unregistered handler for event type: {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type}")
    
    def start_processing(self):
        """Start event processing in background thread."""
        if self.running:
            logger.warning("Event processor already running")
            return
        
        self.running = True
        self.processor_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="PensieveEventProcessor"
        )
        self.processor_thread.start()
        logger.info(f"Started Pensieve event processing (poll interval: {self.poll_interval}s)")
    
    def stop_processing(self):
        """Stop event processing."""
        if not self.running:
            return
        
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        
        logger.info("Stopped Pensieve event processing")
    
    def _processing_loop(self):
        """Main processing loop for events."""
        while self.running:
            try:
                # Check if Pensieve is healthy
                if not self.health_monitor.is_healthy(max_age_seconds=30):
                    logger.debug("Pensieve unhealthy, skipping event check")
                    time.sleep(self.poll_interval * 2)  # Wait longer when unhealthy
                    continue
                
                # Try to get events via different methods
                events = self._get_new_events()
                
                for event in events:
                    try:
                        self._process_event(event)
                        self.events_processed += 1
                        self.last_event_time = datetime.now()
                    except Exception as e:
                        logger.error(f"Failed to process event {event.entity_id}: {e}")
                        self.events_failed += 1
                
                # Sleep between polls
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                time.sleep(self.poll_interval * 2)  # Wait longer on error
    
    def _get_new_events(self) -> List[PensieveEvent]:
        """Get new events from Pensieve using multiple detection methods."""
        events = []
        
        try:
            # Method 1: Try Server-Sent Events (SSE) if available
            events = self._try_sse_events()
            if events:
                return events
            
            # Method 2: Database-based change detection (most reliable)
            events = self._detect_database_changes()
            if events:
                return events
            
            # Method 3: Fallback to API polling
            events = self._poll_for_new_entities()
            
        except Exception as e:
            logger.debug(f"Error getting events: {e}")
        
        return events
    
    def _try_sse_events(self) -> List[PensieveEvent]:
        """Try to get events via Server-Sent Events (if Pensieve supports it)."""
        try:
            # Check if Pensieve has SSE endpoint
            response = self.session.get(
                f"{self.pensieve_client.base_url}/api/events/stream",
                timeout=1,
                stream=True
            )
            
            if response.status_code == 200:
                # Parse SSE stream
                for line in response.iter_lines(decode_unicode=True):
                    if not self.running:
                        break
                    
                    if line.startswith('data: '):
                        try:
                            event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                            event = PensieveEvent(
                                event_type=event_data.get('type', 'unknown'),
                                entity_id=event_data.get('entity_id', 0),
                                timestamp=datetime.fromisoformat(event_data.get('timestamp', datetime.now().isoformat())),
                                data=event_data.get('data', {}),
                                source='pensieve_sse'
                            )
                            return [event]
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.debug(f"Failed to parse SSE event: {e}")
            
        except requests.exceptions.RequestException as e:
            # SSE not available, fallback to polling
            logger.debug(f"SSE not available, falling back to polling: {e}")
        
        return []
    
    def _detect_database_changes(self) -> List[PensieveEvent]:
        """Detect changes by monitoring database directly (most reliable method)."""
        events = []
        
        try:
            # DatabaseManager import moved to avoid circular dependency
            
            # Use direct database access for change detection
            db = DatabaseManager(use_pensieve_api=False)  # Direct SQLite for speed
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get entities newer than last processed ID
                cursor.execute(
                    "SELECT id, filepath, filename, created_at, last_scan_at, file_type_group "
                    "FROM entities WHERE id > ? ORDER BY id ASC LIMIT 20",
                    (self.last_processed_id,)
                )
                
                new_entities = cursor.fetchall()
                
                for entity in new_entities:
                    entity_id = entity['id']
                    
                    # Determine event type based on scan status
                    if entity['last_scan_at']:
                        event_type = 'entity_processed'
                        timestamp = entity['last_scan_at']
                    else:
                        event_type = 'entity_added'
                        timestamp = entity['created_at']
                    
                    # Create event
                    event = PensieveEvent(
                        event_type=event_type,
                        entity_id=entity_id,
                        timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00') if timestamp.endswith('Z') else timestamp),
                        data={
                            'filepath': entity['filepath'],
                            'filename': entity['filename'],
                            'file_type_group': entity['file_type_group'],
                            'last_scan_at': entity['last_scan_at']
                        },
                        source='database_monitor'
                    )
                    events.append(event)
                    
                    # Update last processed ID
                    if entity_id > self.last_processed_id:
                        self.last_processed_id = entity_id
                
                # Also check for recently processed entities (scan status changed)
                if not events:  # Only if no new entities found
                    cursor.execute(
                        "SELECT id, filepath, filename, created_at, last_scan_at, file_type_group "
                        "FROM entities WHERE last_scan_at > datetime('now', '-30 seconds') "
                        "AND id <= ? ORDER BY last_scan_at DESC LIMIT 10",
                        (self.last_processed_id,)
                    )
                    
                    recently_processed = cursor.fetchall()
                    
                    for entity in recently_processed:
                        event = PensieveEvent(
                            event_type='entity_processed',
                            entity_id=entity['id'],
                            timestamp=datetime.fromisoformat(entity['last_scan_at'].replace('Z', '+00:00') if entity['last_scan_at'].endswith('Z') else entity['last_scan_at']),
                            data={
                                'filepath': entity['filepath'],
                                'filename': entity['filename'],
                                'file_type_group': entity['file_type_group'],
                                'last_scan_at': entity['last_scan_at']
                            },
                            source='database_monitor'
                        )
                        events.append(event)
                
        except Exception as e:
            logger.debug(f"Database change detection failed: {e}")
        
        return events
    
    def _poll_for_new_entities(self) -> List[PensieveEvent]:
        """Poll for new entities via corrected API."""
        events = []
        
        try:
            # Get recent entities using corrected API
            entities = self.pensieve_client.get_entities(limit=10)
            
            for entity in entities:
                # Check if this is a new entity
                if entity.id > self.last_processed_id:
                    # Determine event type based on processing status
                    event_type = 'entity_processed' if entity.last_scan_at else 'entity_added'
                    
                    # Create entity event
                    event = PensieveEvent(
                        event_type=event_type,
                        entity_id=entity.id,
                        timestamp=datetime.fromisoformat(entity.created_at),
                        data={
                            'filepath': entity.filepath,
                            'filename': entity.filename,
                            'file_type_group': entity.file_type_group,
                            'last_scan_at': entity.last_scan_at,
                            'metadata': entity.metadata or {}
                        },
                        source='pensieve_poll'
                    )
                    events.append(event)
                    
                    # Update last processed ID
                    if entity.id > self.last_processed_id:
                        self.last_processed_id = entity.id
            
        except PensieveAPIError as e:
            logger.debug(f"API error while polling: {e.message}")
        except Exception as e:
            logger.debug(f"Error while polling for entities: {e}")
        
        return events
    
    def _poll_for_new_frames(self) -> List[PensieveEvent]:
        """Legacy wrapper for backward compatibility."""
        logger.warning("_poll_for_new_frames is deprecated, using _poll_for_new_entities")
        return self._poll_for_new_entities()
    
    def _process_event(self, event: PensieveEvent):
        """Process a single event."""
        logger.debug(f"Processing event: {event.event_type} for entity {event.entity_id}")
        
        # Call registered handlers
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler failed for event {event.event_type}: {e}")
        
        # Built-in processing based on event type
        if event.event_type in ['frame_added', 'entity_added']:
            self._handle_entity_added(event)
        elif event.event_type in ['frame_processed', 'entity_processed']:
            self._handle_entity_processed(event)
    
    def _handle_entity_added(self, event: PensieveEvent):
        """Handle new entity added event."""
        entity_id = event.entity_id
        
        # Check if entity needs processing
        metadata = self.pensieve_client.get_entity_metadata(entity_id)
        
        # If no task extraction yet, trigger it
        if 'extracted_tasks' not in metadata:
            self._trigger_task_extraction(entity_id)
    
    def _handle_entity_processed(self, event: PensieveEvent):
        """Handle entity processed event (OCR completed)."""
        entity_id = event.entity_id
        
        # Trigger task extraction now that OCR is available
        self._trigger_task_extraction(entity_id)
    
    # Legacy method names for backward compatibility
    def _handle_frame_added(self, event: PensieveEvent):
        """Legacy wrapper for _handle_entity_added."""
        logger.warning("_handle_frame_added is deprecated, using _handle_entity_added")
        self._handle_entity_added(event)
    
    def _handle_frame_processed(self, event: PensieveEvent):
        """Legacy wrapper for _handle_entity_processed."""
        logger.warning("_handle_frame_processed is deprecated, using _handle_entity_processed")
        self._handle_entity_processed(event)
    
    def _trigger_task_extraction(self, entity_id: int):
        """Trigger task extraction for a frame."""
        try:
            # Get window title and OCR text using corrected API
            metadata = self.pensieve_client.get_entity_metadata(entity_id)
            window_title = metadata.get("active_window", '')
            
            # Extract OCR result from metadata
            ocr_metadata = self.pensieve_client.get_entity_metadata(entity_id, 'ocr_result')
            ocr_text = ''
            if ocr_metadata and 'ocr_result' in ocr_metadata:
                ocr_result = ocr_metadata['ocr_result']
                if isinstance(ocr_result, list):
                    # Extract text from OCR result format: [{"rec_txt": "text", ...}, ...]
                    ocr_texts = [item.get('rec_txt', '') for item in ocr_result if isinstance(item, dict)]
                    ocr_text = ' '.join(ocr_texts)
                else:
                    ocr_text = str(ocr_result)
            
            if not window_title and not ocr_text:
                logger.debug(f"No data to extract tasks from for entity {entity_id}")
                return
            
            # Extract task (returns single string, not list)
            task = self.task_extractor.extract_task(window_title, ocr_text)
            
            if task:
                # Store extracted task using corrected API
                self.pensieve_client.store_entity_metadata(entity_id, 'extracted_tasks', {
                    "tasks": [task],  # Wrap single task in list for consistency
                    'extracted_at': datetime.now().isoformat(),
                    'method': 'event_driven',
                    'source': 'realtime_processor'
                })
                
                # Categorize activity
                category = self.categorizer.categorize(window_title, ocr_text)
                if category:
                    self.pensieve_client.store_entity_metadata(entity_id, 'activity_category', category)
                
                logger.info(f"Real-time processed entity {entity_id}: task extracted - {task}")
        
        except Exception as e:
            logger.error(f"Failed to extract tasks for entity {entity_id}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'running': self.running,
            'events_processed': self.events_processed,
            'events_failed': self.events_failed,
            'last_event_time': self.last_event_time.isoformat() if self.last_event_time else None,
            'last_processed_id': self.last_processed_id,
            'registered_handlers': {
                event_type: len(handlers) 
                for event_type, handlers in self.event_handlers.items()
            },
            'poll_interval': self.poll_interval
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start_processing()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_processing()


# Global event processor instance
_global_processor: Optional[EventProcessor] = None


def get_event_processor() -> EventProcessor:
    """Get global event processor instance."""
    global _global_processor
    if _global_processor is None:
        _global_processor = EventProcessor()
    return _global_processor


def start_event_processing():
    """Start global event processing."""
    processor = get_event_processor()
    processor.start_processing()
    return processor


def stop_event_processing():
    """Stop global event processing."""
    global _global_processor
    if _global_processor:
        _global_processor.stop_processing()


# Example event handlers
def log_entity_added(event: PensieveEvent):
    """Example handler that logs new entities."""
    logger.info(f"New entity added: {event.entity_id} at {event.timestamp}")

def log_frame_added(event: PensieveEvent):
    """Legacy handler that logs new frames."""
    logger.warning("log_frame_added is deprecated, use log_entity_added")
    log_entity_added(event)


def notify_dashboard_update(event: PensieveEvent):
    """Example handler that could notify dashboards of updates."""
    # This could trigger Streamlit rerun or update caches
    logger.debug(f"Dashboard notification: {event.event_type} for {event.entity_id}")


# Auto-start event processing when module is imported (optional)
if __name__ == "__main__":
    # Demo usage
    processor = EventProcessor(poll_interval=2.0)
    processor.register_event_handler('frame_added', log_frame_added)
    processor.register_event_handler('frame_processed', log_frame_added)
    
    try:
        processor.start_processing()
        print("Event processor started. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            stats = processor.get_statistics()
            print(f"Processed: {stats['events_processed']}, Failed: {stats['events_failed']}")
            
    except KeyboardInterrupt:
        print("Stopping event processor...")
        processor.stop_processing()
        print("Event processor stopped.")