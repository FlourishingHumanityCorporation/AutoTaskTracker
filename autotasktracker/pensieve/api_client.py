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
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def is_healthy(self) -> bool:
        """Check if Pensieve service is healthy and responding."""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Pensieve health check failed: {e}")
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
            response = self.session.get(
                f"{self.base_url}/api/search",
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
            response = self.session.get(f"{self.base_url}/api/config")
            
            if response.status_code != 200:
                logger.error(f"Failed to get config: {response.status_code}")
                return {}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get config: {e}")
            return {}
    
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