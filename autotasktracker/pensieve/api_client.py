"""Pensieve REST API client for proper integration with memos service."""

import requests
import logging
import time
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class PensieveFrame:
    """Represents a screenshot frame from Pensieve."""
    id: int
    filepath: str
    timestamp: str
    created_at: str
    processed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PensieveAPIError(Exception):
    """Exception raised for Pensieve API errors."""
    status_code: int
    message: str
    endpoint: str


class PensieveAPIClient:
    """Client for interacting with Pensieve/memos REST API."""
    
    def __init__(self, base_url: str = "http://localhost:8839", timeout: int = 30):
        """Initialize Pensieve API client.
        
        Args:
            base_url: Base URL for Pensieve service
            timeout: Request timeout in seconds
        """
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
    
    def get_frames(self, limit: int = 100, offset: int = 0, 
                   processed_only: bool = False) -> List[PensieveFrame]:
        """Get screenshot frames from Pensieve.
        
        Args:
            limit: Maximum number of frames to return
            offset: Number of frames to skip
            processed_only: Only return frames that have been processed
            
        Returns:
            List of PensieveFrame objects
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        if processed_only:
            params['processed'] = 'true'
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/frames",
                params=params
            )
            
            if response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint="/api/frames"
                )
            
            frames_data = response.json()
            frames = []
            
            for frame_data in frames_data:
                frames.append(PensieveFrame(
                    id=frame_data['id'],
                    filepath=frame_data['filepath'],
                    timestamp=frame_data['timestamp'],
                    created_at=frame_data['created_at'],
                    processed_at=frame_data.get('processed_at'),
                    metadata=frame_data.get('metadata', {})
                ))
            
            return frames
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get frames from Pensieve: {e}")
            raise PensieveAPIError(
                status_code=0,
                message=str(e),
                endpoint="/api/frames"
            )
    
    def get_frame(self, frame_id: int) -> Optional[PensieveFrame]:
        """Get a specific frame by ID.
        
        Args:
            frame_id: ID of the frame to retrieve
            
        Returns:
            PensieveFrame object or None if not found
        """
        try:
            response = self.session.get(f"{self.base_url}/api/frames/{frame_id}")
            
            if response.status_code == 404:
                return None
            elif response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint=f"/api/frames/{frame_id}"
                )
            
            frame_data = response.json()
            return PensieveFrame(
                id=frame_data['id'],
                filepath=frame_data['filepath'],
                timestamp=frame_data['timestamp'],
                created_at=frame_data['created_at'],
                processed_at=frame_data.get('processed_at'),
                metadata=frame_data.get('metadata', {})
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get frame {frame_id}: {e}")
            raise PensieveAPIError(
                status_code=0,
                message=str(e),
                endpoint=f"/api/frames/{frame_id}"
            )
    
    def get_ocr_result(self, frame_id: int) -> Optional[str]:
        """Get OCR text result for a frame.
        
        Args:
            frame_id: ID of the frame
            
        Returns:
            OCR text or None if not available
        """
        try:
            response = self.session.get(f"{self.base_url}/api/ocr/{frame_id}")
            
            if response.status_code == 404:
                return None
            elif response.status_code != 200:
                raise PensieveAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    endpoint=f"/api/ocr/{frame_id}"
                )
            
            result = response.json()
            return result.get('text')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get OCR for frame {frame_id}: {e}")
            return None
    
    def search_frames(self, query: str, limit: int = 50) -> List[PensieveFrame]:
        """Search frames using Pensieve's search capabilities.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching frames
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
            frames = []
            
            for result in search_results:
                frames.append(PensieveFrame(
                    id=result['id'],
                    filepath=result['filepath'],
                    timestamp=result['timestamp'],
                    created_at=result['created_at'],
                    processed_at=result.get('processed_at'),
                    metadata=result.get('metadata', {})
                ))
            
            return frames
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def store_metadata(self, frame_id: int, key: str, value: Any) -> bool:
        """Store metadata for a frame.
        
        Args:
            frame_id: ID of the frame
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/metadata",
                json={
                    'frame_id': frame_id,
                    'key': key,
                    'value': value
                }
            )
            
            return response.status_code in [200, 201]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to store metadata: {e}")
            return False
    
    def get_metadata(self, frame_id: int, key: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for a frame.
        
        Args:
            frame_id: ID of the frame
            key: Specific metadata key, or None for all metadata
            
        Returns:
            Dictionary of metadata
        """
        try:
            url = f"{self.base_url}/api/metadata/{frame_id}"
            if key:
                url += f"/{key}"
                
            response = self.session.get(url)
            
            if response.status_code == 404:
                return {}
            elif response.status_code != 200:
                logger.error(f"Failed to get metadata: {response.status_code}")
                return {}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get metadata: {e}")
            return {}
    
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