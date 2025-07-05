"""Pensieve REST API client for proper integration with memos service."""

import requests
import logging
import time
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import json

from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class PensieveEntity:
    """Represents an entity (screenshot) from Pensieve."""
    id: int
    filepath: str
    filename: str
    created_at: str
    file_created_at: Optional[str] = None
    last_scan_at: Optional[str] = None
    file_type_group: str = "image"
    metadata: Optional[Dict[str, Any]] = None


@dataclass  
class PensieveFrame:
    """Legacy compatibility wrapper for PensieveEntity."""
    id: int
    filepath: str
    timestamp: str
    created_at: str
    processed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_entity(cls, entity: 'PensieveEntity') -> 'PensieveFrame':
        """Create PensieveFrame from PensieveEntity for backward compatibility."""
        return cls(
            id=entity.id,
            filepath=entity.filepath,
            timestamp=entity.created_at,
            created_at=entity.created_at,
            processed_at=entity.last_scan_at,
            metadata=entity.metadata
        )


@dataclass
class PensieveAPIError(Exception):
    """Exception raised for Pensieve API errors."""
    status_code: int
    message: str
    endpoint: str


class PensieveAPIClient:
    """Client for interacting with Pensieve/memos REST API."""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        """Initialize Pensieve API client.
        
        Args:
            base_url: Base URL for Pensieve service
            timeout: Request timeout in seconds
        """
        if base_url is None:
            base_url = get_config().get_service_url('memos')
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = timeout
        
        # Enhanced connection pooling and retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        from urllib3.poolmanager import PoolManager
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Enhanced adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools to cache
            pool_maxsize=20,      # Max connections in pool
            pool_block=False      # Don't block on pool exhaustion
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Performance tracking for intelligent routing
        self.endpoint_performance = {
            'response_times': {},
            'success_rates': {},
            'last_used': {},
            'preferred_endpoints': set()
        }
    
    def is_healthy(self) -> bool:
        """Check if Pensieve service is healthy and responding."""
        try:
            response = self._make_request_with_tracking('GET', '/api/health', timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Pensieve health check failed: {e}")
            return False
    
    def get_screenshots(self, limit: int = 100, offset: int = 0, 
                       start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get screenshots with metadata from Pensieve API.
        
        This is the primary data endpoint that should be used by DatabaseManager.
        
        Args:
            limit: Maximum number of screenshots to return
            offset: Number of screenshots to skip
            start_date: Filter screenshots after this date (ISO format)
            end_date: Filter screenshots before this date (ISO format)
            
        Returns:
            List of screenshot dictionaries with metadata
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/screenshots",
                params=params
            )
            
            if response.status_code == 404:
                # API endpoint not available, return empty list for graceful degradation
                logger.debug("Screenshots API endpoint not available")
                return []
            elif response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint="/api/screenshots"
                )
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Screenshots API not available: {e}")
            return []
    
    def get_metadata_entries(self, entity_id: Optional[int] = None, 
                           key: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get metadata entries from Pensieve API.
        
        Args:
            entity_id: Filter by specific entity ID
            key: Filter by metadata key
            limit: Maximum number of entries to return
            
        Returns:
            List of metadata entry dictionaries
        """
        params = {'limit': limit}
        if entity_id:
            params['entity_id'] = entity_id
        if key:
            params['key'] = key
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/metadata",
                params=params
            )
            
            if response.status_code == 404:
                logger.debug("Metadata API endpoint not available")
                return []
            elif response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint="/api/metadata"
                )
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Metadata API not available: {e}")
            return []
    
    def update_task_status(self, task_id: int, status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status using Pensieve API.
        
        Args:
            task_id: ID of the task (entity)
            status: New status value
            metadata: Additional metadata to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {'status': status}
            if metadata:
                payload['metadata'] = metadata
                
            response = self.session.put(
                f"{self.base_url}/api/tasks/{task_id}",
                json=payload
            )
            
            if response.status_code == 404:
                logger.debug("Tasks API endpoint not available")
                return False
            
            return response.status_code in [200, 204]
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Tasks API not available: {e}")
            return False
    
    def get_entities(self, library_id: int = 1, folder_id: int = 1, 
                    limit: int = 100, offset: int = 0) -> List[PensieveEntity]:
        """Get entities (screenshots) from Pensieve using actual API.
        
        Args:
            library_id: Library ID (default 1 for screenshots)
            folder_id: Folder ID (default 1 for main folder)
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            
        Returns:
            List of PensieveEntity objects
        """
        params = {
            'limit': limit,
            'offset': offset
        }
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/libraries/{library_id}/folders/{folder_id}/entities",
                params=params
            )
            
            if response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint=f"/api/libraries/{library_id}/folders/{folder_id}/entities"
                )
            
            entities_data = response.json()
            entities = []
            
            for entity_data in entities_data:
                # Include metadata_entries in metadata field for easy access
                metadata = entity_data.copy()  # Include all entity data
                entities.append(PensieveEntity(
                    id=entity_data['id'],
                    filepath=entity_data['filepath'],
                    filename=entity_data['filename'],
                    created_at=entity_data.get('file_created_at', entity_data.get('created_at', '')),
                    file_created_at=entity_data.get('file_created_at'),
                    last_scan_at=entity_data.get('last_scan_at'),
                    file_type_group=entity_data.get('file_type_group', 'image'),
                    metadata=metadata
                ))
            
            return entities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get entities from Pensieve: {e}")
            raise PensieveAPIError(
                status_code=0,
                message=str(e),
                endpoint=f"/api/libraries/{library_id}/folders/{folder_id}/entities"
            )
    
    def get_frames(self, limit: int = 100, offset: int = 0, 
                   processed_only: bool = False) -> List[PensieveFrame]:
        """Get screenshot frames from Pensieve (legacy wrapper for get_entities).
        
        DEPRECATED: Use get_entities() instead for better alignment with Pensieve API.
        
        Args:
            limit: Maximum number of frames to return
            offset: Number of frames to skip
            processed_only: Only return frames that have been processed
            
        Returns:
            List of PensieveFrame objects
        """
        logger.warning("get_frames() is deprecated, use get_entities() for better API alignment")
        
        try:
            entities = self.get_entities(limit=limit, offset=offset)
            frames = [PensieveFrame.from_entity(entity) for entity in entities]
            
            if processed_only:
                # Filter for entities that have been processed (have last_scan_at)
                frames = [f for f in frames if f.processed_at is not None]
            
            return frames
            
        except PensieveAPIError:
            # If entity API fails, return empty list for graceful degradation
            logger.error("Entity API failed, returning empty frames list")
            return []
    
    def get_entity(self, entity_id: int) -> Optional[PensieveEntity]:
        """Get a specific entity by ID.
        
        Args:
            entity_id: ID of the entity to retrieve
            
        Returns:
            PensieveEntity object or None if not found
        """
        try:
            response = self.session.get(f"{self.base_url}/api/entities/{entity_id}")
            
            if response.status_code == 404:
                return None
            elif response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint=f"/api/entities/{entity_id}"
                )
            
            entity_data = response.json()
            # Include all entity data in metadata for easy access
            metadata = entity_data.copy()
            return PensieveEntity(
                id=entity_data['id'],
                filepath=entity_data['filepath'],
                filename=entity_data['filename'],
                created_at=entity_data.get('file_created_at', entity_data.get('created_at', '')),
                file_created_at=entity_data.get('file_created_at'),
                last_scan_at=entity_data.get('last_scan_at'),
                file_type_group=entity_data.get('file_type_group', 'image'),
                metadata=metadata
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            raise PensieveAPIError(
                status_code=0,
                message=str(e),
                endpoint=f"/api/entities/{entity_id}"
            )
    
    def get_frame(self, frame_id: int) -> Optional[PensieveFrame]:
        """Get a specific frame by ID (legacy wrapper).
        
        DEPRECATED: Use get_entity() instead for better alignment with Pensieve API.
        
        Args:
            frame_id: ID of the frame to retrieve
            
        Returns:
            PensieveFrame object or None if not found
        """
        logger.warning("get_frame() is deprecated, use get_entity() for better API alignment")
        
        entity = self.get_entity(frame_id)
        return PensieveFrame.from_entity(entity) if entity else None
    
    def get_entity_metadata(self, entity_id: int, key: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for an entity using actual API.
        
        Args:
            entity_id: ID of the entity
            key: Specific metadata key to retrieve
            
        Returns:
            Metadata dictionary or specific value if key specified
        """
        try:
            # Get the full entity which includes metadata_entries
            entity = self.get_entity(entity_id)
            if not entity or not entity.metadata:
                return {}
            
            # Extract metadata_entries from entity response
            metadata_entries = entity.metadata.get('metadata_entries', [])
            
            if key:
                # Return specific key value
                for entry in metadata_entries:
                    if entry.get('key') == key:
                        return {key: entry.get('value')}
                return {}
            else:
                # Return all metadata as key-value pairs
                metadata = {}
                for entry in metadata_entries:
                    metadata[entry.get('key')] = entry.get('value')
                return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for entity {entity_id}: {e}")
            return {}
    
    def get_ocr_result(self, frame_id: int) -> Optional[str]:
        """Get OCR text result for a frame (legacy wrapper).
        
        DEPRECATED: Use get_entity_metadata(entity_id, 'ocr_result') instead.
        
        Args:
            frame_id: ID of the frame
            
        Returns:
            OCR text or None if not available
        """
        logger.warning("get_ocr_result() is deprecated, use get_entity_metadata() for better API alignment")
        
        try:
            metadata = self.get_entity_metadata(frame_id, 'ocr_result')
            return metadata.get('ocr_result') if metadata else None
        except Exception as e:
            logger.error(f"Failed to get OCR for entity {frame_id}: {e}")
            return None
    
    def search_entities(self, query: str, limit: int = 50) -> List[PensieveEntity]:
        """Search entities using Pensieve's search capabilities.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        try:
            response = self._make_request_with_tracking(
                'GET', '/api/search',
                params={'q': query, 'limit': limit}
            )
            
            if response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint="/api/search"
                )
            
            search_results = response.json()
            entities = []
            
            # Handle Pensieve's actual search response format: {"hits": [{"document": {...}}]}
            if isinstance(search_results, dict) and 'hits' in search_results:
                for hit in search_results['hits']:
                    doc = hit.get('document', {})
                    # Include all document data in metadata for easy access
                    metadata = doc.copy()
                    entities.append(PensieveEntity(
                        id=int(doc['id']),
                        filepath=doc['filepath'],
                        filename=doc.get('filename', ''),
                        created_at=doc.get('created_at', doc.get('file_created_at', '')),
                        file_created_at=doc.get('file_created_at'),
                        last_scan_at=doc.get('last_scan_at'),
                        file_type_group=doc.get('file_type_group', 'image'),
                        metadata=metadata
                    ))
            elif isinstance(search_results, list):
                # Fallback for direct array format
                for result in search_results:
                    metadata = result.copy()
                    entities.append(PensieveEntity(
                        id=result['id'],
                        filepath=result['filepath'],
                        filename=result.get('filename', ''),
                        created_at=result['created_at'],
                        file_created_at=result.get('file_created_at'),
                        last_scan_at=result.get('last_scan_at'),
                        file_type_group=result.get('file_type_group', 'image'),
                        metadata=metadata
                    ))
            
            return entities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def search_frames(self, query: str, limit: int = 50) -> List[PensieveFrame]:
        """Search frames using Pensieve's search capabilities (legacy wrapper).
        
        DEPRECATED: Use search_entities() instead for better alignment with Pensieve API.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching frames
        """
        logger.warning("search_frames() is deprecated, use search_entities() for better API alignment")
        
        try:
            entities = self.search_entities(query, limit)
            return [PensieveFrame.from_entity(entity) for entity in entities]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def store_entity_metadata(self, entity_id: int, key: str, value: Any) -> bool:
        """Store metadata for an entity using actual API.
        
        Args:
            entity_id: ID of the entity
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/entities/{entity_id}/metadata",
                json={
                    'key': key,
                    'value': value
                }
            )
            
            return response.status_code in [200, 201]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to store metadata for entity {entity_id}: {e}")
            return False
    
    def get_entity_tags(self, entity_id: int) -> List[str]:
        """Get tags for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List of tag names
        """
        try:
            response = self.session.get(f"{self.base_url}/api/entities/{entity_id}/tags")
            
            if response.status_code == 404:
                logger.debug("Entity tags API endpoint not available")
                return []
            elif response.status_code != 200:
                logger.warning(f"Failed to get entity tags: {response.status_code}")
                return []
            
            tags_data = response.json()
            if isinstance(tags_data, list):
                return [tag.get('name', str(tag)) for tag in tags_data]
            return []
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Entity tags API not available: {e}")
            return []
    
    def add_entity_tag(self, entity_id: int, tag: str) -> bool:
        """Add a tag to an entity.
        
        Args:
            entity_id: ID of the entity
            tag: Tag name to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/entities/{entity_id}/tags",
                json={'name': tag}
            )
            
            if response.status_code == 404:
                logger.debug("Entity tags API endpoint not available")
                return False
            
            return response.status_code in [200, 201]
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to add entity tag: {e}")
            return False
    
    def remove_entity_tag(self, entity_id: int, tag: str) -> bool:
        """Remove a tag from an entity.
        
        Args:
            entity_id: ID of the entity
            tag: Tag name to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/api/entities/{entity_id}/tags",
                json={'name': tag}
            )
            
            if response.status_code == 404:
                logger.debug("Entity tags API endpoint not available")
                return False
            
            return response.status_code in [200, 204]
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to remove entity tag: {e}")
            return False
    
    def search_by_tags(self, tags: List[str], operator: str = "AND", limit: int = 50) -> List[PensieveEntity]:
        """Search entities by tags.
        
        Args:
            tags: List of tag names
            operator: "AND" or "OR" for tag matching
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/search/tags",
                params={
                    'tags': ','.join(tags),
                    'operator': operator,
                    'limit': limit
                }
            )
            
            if response.status_code == 404:
                logger.debug("Tags search API endpoint not available")
                return []
            elif response.status_code != 200:
                logger.warning(f"Tags search failed: {response.status_code}")
                return []
            
            results = response.json()
            entities = []
            
            for result in results:
                metadata = result.copy()
                entities.append(PensieveEntity(
                    id=result['id'],
                    filepath=result['filepath'],
                    filename=result.get('filename', ''),
                    created_at=result['created_at'],
                    file_created_at=result.get('file_created_at'),
                    last_scan_at=result.get('last_scan_at'),
                    file_type_group=result.get('file_type_group', 'image'),
                    metadata=metadata
                ))
            
            return entities
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Tags search not available: {e}")
            return []
    
    def semantic_search(self, query: str, limit: int = 50, threshold: float = 0.7) -> List[PensieveEntity]:
        """Perform semantic search using embeddings.
        
        Args:
            query: Search query
            limit: Maximum number of results
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of matching entities with semantic similarity
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/search/semantic",
                params={
                    'q': query,
                    'limit': limit,
                    'threshold': threshold
                }
            )
            
            if response.status_code == 404:
                logger.debug("Semantic search API endpoint not available")
                return []
            elif response.status_code != 200:
                logger.warning(f"Semantic search failed: {response.status_code}")
                return []
            
            results = response.json()
            entities = []
            
            for result in results:
                # Include similarity score in metadata
                metadata = result.copy()
                entities.append(PensieveEntity(
                    id=result['id'],
                    filepath=result['filepath'],
                    filename=result.get('filename', ''),
                    created_at=result['created_at'],
                    file_created_at=result.get('file_created_at'),
                    last_scan_at=result.get('last_scan_at'),
                    file_type_group=result.get('file_type_group', 'image'),
                    metadata=metadata
                ))
            
            return entities
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Semantic search not available: {e}")
            return []
    
    def store_metadata(self, frame_id: int, key: str, value: Any) -> bool:
        """Store metadata for a frame (legacy wrapper).
        
        DEPRECATED: Use store_entity_metadata() instead for better alignment with Pensieve API.
        
        Args:
            frame_id: ID of the frame
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if successful, False otherwise
        """
        logger.warning("store_metadata() is deprecated, use store_entity_metadata() for better API alignment")
        return self.store_entity_metadata(frame_id, key, value)
    
    def get_metadata(self, frame_id: int, key: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for a frame (legacy wrapper).
        
        DEPRECATED: Use get_entity_metadata() instead for better alignment with Pensieve API.
        
        Args:
            frame_id: ID of the frame
            key: Specific metadata key, or None for all metadata
            
        Returns:
            Dictionary of metadata
        """
        logger.warning("get_metadata() is deprecated, use get_entity_metadata() for better API alignment")
        return self.get_entity_metadata(frame_id, key)
    
    def get_config(self) -> Dict[str, Any]:
        """Get Pensieve configuration.
        
        Returns:
            Configuration dictionary
        """
        try:
            response = self._make_request_with_tracking('GET', '/api/config')
            
            if response.status_code != 200:
                logger.error(f"Failed to get config: {response.status_code}")
                return {}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get config: {e}")
            return {}
    
    def _track_endpoint_performance(self, endpoint: str, response_time: float, success: bool):
        """Track endpoint performance for intelligent routing."""
        import time
        
        # Update response times (rolling average)
        if endpoint not in self.endpoint_performance['response_times']:
            self.endpoint_performance['response_times'][endpoint] = []
        
        times = self.endpoint_performance['response_times'][endpoint]
        times.append(response_time)
        
        # Keep only last 10 response times for rolling average
        if len(times) > 10:
            times.pop(0)
        
        # Update success rates
        if endpoint not in self.endpoint_performance['success_rates']:
            self.endpoint_performance['success_rates'][endpoint] = {'successes': 0, 'total': 0}
        
        rates = self.endpoint_performance['success_rates'][endpoint]
        rates['total'] += 1
        if success:
            rates['successes'] += 1
        
        # Update last used time
        self.endpoint_performance['last_used'][endpoint] = time.time()
        
        # Update preferred endpoints based on performance
        self._update_preferred_endpoints()
    
    def _update_preferred_endpoints(self):
        """Update the set of preferred endpoints based on performance metrics."""
        preferred = set()
        
        for endpoint, times in self.endpoint_performance['response_times'].items():
            if not times:
                continue
                
            # Calculate average response time
            avg_response_time = sum(times) / len(times)
            
            # Get success rate
            rates = self.endpoint_performance['success_rates'].get(endpoint, {'successes': 0, 'total': 1})
            success_rate = rates['successes'] / rates['total'] if rates['total'] > 0 else 0
            
            # Prefer endpoints with good response time (< 2s) and high success rate (> 80%)
            if avg_response_time < 2.0 and success_rate > 0.8:
                preferred.add(endpoint)
        
        self.endpoint_performance['preferred_endpoints'] = preferred
    
    def _make_request_with_tracking(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request with performance tracking."""
        import time
        
        start_time = time.time()
        success = False
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                response = self.session.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(url, **kwargs)
            elif method.upper() == 'PUT':
                response = self.session.put(url, **kwargs)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            success = 200 <= response.status_code < 300
            return response
            
        finally:
            response_time = time.time() - start_time
            self._track_endpoint_performance(endpoint, response_time, success)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get API client performance statistics."""
        stats = {
            'total_endpoints_tracked': len(self.endpoint_performance['response_times']),
            'preferred_endpoints': list(self.endpoint_performance['preferred_endpoints']),
            'endpoint_details': {}
        }
        
        for endpoint in self.endpoint_performance['response_times']:
            times = self.endpoint_performance['response_times'][endpoint]
            rates = self.endpoint_performance['success_rates'].get(endpoint, {'successes': 0, 'total': 0})
            
            avg_time = sum(times) / len(times) if times else 0
            success_rate = rates['successes'] / rates['total'] if rates['total'] > 0 else 0
            
            stats['endpoint_details'][endpoint] = {
                'avg_response_time': avg_time,
                'success_rate': success_rate,
                'total_requests': rates['total'],
                'is_preferred': endpoint in self.endpoint_performance['preferred_endpoints']
            }
        
        return stats
    
    def optimize_connection_pool(self, max_connections: int = 20, max_pools: int = 10):
        """Dynamically optimize connection pool settings."""
        try:
            # Create new adapter with optimized settings
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=max_pools,
                pool_maxsize=max_connections,
                pool_block=False
            )
            
            # Replace existing adapters
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            logger.info(f"Optimized connection pool: {max_connections} max connections, {max_pools} pools")
            
        except Exception as e:
            logger.warning(f"Failed to optimize connection pool: {e}")

    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance for easy access
_client_instance: Optional[PensieveAPIClient] = None


def get_pensieve_client() -> PensieveAPIClient:
    """Get singleton Pensieve API client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = PensieveAPIClient()
    return _client_instance


def reset_pensieve_client():
    """Reset singleton client (useful for testing)."""
    global _client_instance
    if _client_instance:
        _client_instance.close()
    _client_instance = None