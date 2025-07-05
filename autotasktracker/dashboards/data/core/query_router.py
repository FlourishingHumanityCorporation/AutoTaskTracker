"""Query routing system for API and database execution strategy."""

import logging
from typing import Optional, Any, Tuple
import pandas as pd
from autotasktracker.pensieve.api_client import PensieveAPIClient
from autotasktracker.dashboards.data.core.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class QueryRouter:
    """Routes queries to appropriate API endpoints or database."""
    
    def __init__(self, api_client: Optional[PensieveAPIClient], circuit_breaker: CircuitBreaker):
        self.api_client = api_client
        self.circuit_breaker = circuit_breaker
    
    def can_route_to_api(self, query: str) -> bool:
        """Check if query can be routed to API."""
        return (
            self.api_client is not None and
            self.api_client.is_healthy() and
            not self.circuit_breaker.is_any_circuit_open() and
            self._is_data_query(query)
        )
    
    def execute_api_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute query via Pensieve API with intelligent endpoint routing."""
        if not self.can_route_to_api(query):
            return None
            
        try:
            # Smart endpoint routing based on query type and available endpoints
            result = self._route_query_to_available_endpoints(query, params)
            
            # Reset circuit breaker on success
            if result is not None:
                self.circuit_breaker.record_success()
            
            return result
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"API connection failed: {e}")
            self.circuit_breaker.record_failure(error_message=str(e))
            return None
        except Exception as e:
            logger.debug(f"Unexpected API query routing error: {e}")
            self.circuit_breaker.record_failure(error_message=str(e))
            return None
    
    def _is_data_query(self, query: str) -> bool:
        """Check if query is a data retrieval query suitable for API."""
        query_lower = query.lower().strip()
        
        # Check for data retrieval patterns
        data_patterns = [
            'select', 'with', 'from entities', 'from metadata_entries',
            'join', 'where', 'order by', 'limit'
        ]
        
        # Must be a SELECT query or CTE
        if not (query_lower.startswith('select') or query_lower.startswith('with')):
            return False
        
        # Should contain data-related keywords
        return any(pattern in query_lower for pattern in data_patterns)
    
    def _route_query_to_available_endpoints(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Route queries to available Pensieve API endpoints based on current availability."""
        try:
            query_type = self._determine_query_type(query, params)
            
            if query_type == 'search':
                return self._execute_search_query(query, params)
            elif query_type == 'entity_listing':
                return self._execute_entity_listing_query(query, params)
            elif query_type == 'entity_specific':
                return self._execute_entity_specific_query(query, params)
            
            # Cannot route this query to available endpoints
            return None
            
        except (KeyError, ValueError) as e:
            logger.debug(f"Query routing parameter error: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected query routing error: {e}")
            return None
    
    def _determine_query_type(self, query: str, params: tuple) -> Optional[str]:
        """Determine the type of query for routing decisions."""
        query_lower = query.lower()
        
        # Available endpoints based on our testing:
        # ✅ /api/search - Text search
        # ✅ /api/entities/{id} - Get specific entity  
        # ✅ /api/libraries/1/folders/1/entities - Entities in folder
        # ✅ /api/config - Configuration
        
        # Check for search queries
        if any(keyword in query_lower for keyword in ['search', 'like', 'match']):
            return 'search'
        
        # Check for entity listing queries
        if any(keyword in query_lower for keyword in ['entities', 'screenshots']) and 'limit' in query_lower:
            return 'entity_listing'
        
        # Check for entity-specific queries
        if 'entity_id' in query_lower or any(p for p in params if isinstance(p, int) and p > 0):
            return 'entity_specific'
        
        return None
    
    def _execute_search_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute search queries using /api/search endpoint."""
        try:
            search_term, limit = self._extract_search_parameters(params)
            
            # Use the API client's search functionality
            entities = self.api_client.search_entities(search_term, limit=limit)
            
            if not entities:
                return pd.DataFrame()
            
            return self._convert_entities_to_dataframe(entities)
            
        except (AttributeError, ConnectionError) as e:
            logger.debug(f"Search query API error: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected search query error: {e}")
            return None
    
    def _extract_search_parameters(self, params: tuple) -> Tuple[str, int]:
        """Extract search term and limit from query parameters."""
        search_term = None
        limit = 100
        
        if params:
            for param in params:
                if isinstance(param, str) and len(param) > 2:
                    search_term = param.strip('%')  # Remove SQL wildcards
                    break
                elif isinstance(param, int) and param > 0 and param < 1000:
                    limit = param
        
        if not search_term:
            search_term = "screenshot"  # Default search term
        
        return search_term, limit
    
    def _convert_entities_to_dataframe(self, entities) -> pd.DataFrame:
        """Convert API entities to DataFrame format matching database schema."""
        data = []
        for entity in entities:
            data.append({
                'id': entity.id,
                'filepath': entity.filepath,
                'filename': entity.filename,
                'created_at': entity.created_at,
                'file_created_at': entity.file_created_at,
                'last_scan_at': entity.last_scan_at,
                'file_type_group': entity.file_type_group
            })
        
        return pd.DataFrame(data)
    
    def _execute_entity_listing_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute entity listing queries using /api/libraries/1/folders/1/entities."""
        try:
            # Use the working entities endpoint through API client
            entities = self.api_client.get_entities(limit=100)
            
            if not entities:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for entity in entities:
                data.append({
                    'id': entity.id,
                    'filepath': entity.filepath,
                    'filename': entity.filename,
                    'created_at': entity.created_at,
                    'file_created_at': entity.file_created_at,
                    'last_scan_at': entity.last_scan_at,
                    'file_type_group': entity.file_type_group
                })
            
            df = pd.DataFrame(data)
            
            # Apply basic filtering based on query parameters
            if params:
                limit = next((p for p in params if isinstance(p, int) and p > 0), None)
                if limit:
                    df = df.head(limit)
            
            return df
            
        except Exception as e:
            logger.debug(f"Entity listing query execution failed: {e}")
            return None
    
    def _execute_entity_specific_query(self, query: str, params: tuple) -> Optional[pd.DataFrame]:
        """Execute entity-specific queries using /api/entities/{id}."""
        try:
            # Extract entity ID from parameters
            entity_id = None
            for param in params:
                if isinstance(param, int) and param > 0:
                    entity_id = param
                    break
            
            if not entity_id:
                return None
            
            # Get specific entity
            entity = self.api_client.get_entity(entity_id)
            if not entity:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = [{
                'id': entity.id,
                'filepath': entity.filepath,
                'filename': entity.filename,
                'created_at': entity.created_at,
                'file_created_at': entity.file_created_at,
                'last_scan_at': entity.last_scan_at,
                'file_type_group': entity.file_type_group
            }]
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.debug(f"Entity-specific query execution failed: {e}")
            return None