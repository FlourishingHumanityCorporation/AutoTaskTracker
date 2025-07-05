"""
Enhanced search integration with Pensieve native capabilities.
Provides semantic search, advanced filtering, and intelligent result ranking.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveEntity, PensieveAPIError
from autotasktracker.pensieve.cache_manager import get_cache_manager
# DatabaseManager import moved to avoid circular dependency

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Enhanced search result with relevance scoring and context."""
    entity: PensieveEntity
    relevance_score: float
    match_type: str  # "text", "semantic", "metadata", "hybrid"
    matched_fields: List[str]
    context_snippet: str
    ai_extracted_tasks: List[Dict[str, Any]]
    category: Optional[str] = None
    confidence: float = 0.0


@dataclass
class SearchQuery:
    """Structured search query with advanced options."""
    query: str
    search_type: str = "hybrid"  # "text", "semantic", "hybrid"
    time_range: Optional[Tuple[datetime, datetime]] = None
    entity_types: List[str] = None
    categories: List[str] = None
    min_relevance: float = 0.0
    limit: int = 50
    include_tasks: bool = True
    semantic_threshold: float = 0.7


class PensieveEnhancedSearch:
    """Enhanced search system using Pensieve's native capabilities."""
    
    def __init__(self):
        self.api_client = get_pensieve_client()
        self.cache = get_cache_manager()
        self.db_manager = None  # Lazy load to avoid circular imports
        
        # Initialize tagging integration
        try:
            from autotasktracker.pensieve.tagging_integration import get_tag_manager
            self.tag_manager = get_tag_manager()
        except ImportError:
            logger.warning("Tagging integration not available")
            self.tag_manager = None
        
        # Search statistics
        self.stats = {
            'total_searches': 0,
            'api_searches': 0,
            'fallback_searches': 0,
            'tag_searches': 0,
            'semantic_searches': 0,
            'cache_hits': 0,
            'avg_response_time': 0.0
        }
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform enhanced search with multiple strategies.
        
        Args:
            query: Structured search query
            
        Returns:
            List of enhanced search results
        """
        start_time = time.time()
        self.stats['total_searches'] += 1
        
        try:
            # Try cache first for exact queries (only for smaller result sets)
            cache_key = self._generate_cache_key(query)
            if query.limit <= 50:  # Only cache smaller queries
                cached_results = self.cache.get(cache_key)
                if cached_results is not None:
                    self.stats['cache_hits'] += 1
                    logger.debug(f"Cache hit for search query: {query.query[:50]}")
                    return cached_results
            
            # For large result sets, suggest using streaming
            if query.limit > 100:
                logger.warning(f"Large result set requested ({query.limit}). Consider using search_stream() for better performance.")
            
            # Determine search strategy
            if query.search_type == "hybrid":
                results = await self._hybrid_search(query)
            elif query.search_type == "semantic":
                results = await self._semantic_search(query)
            else:
                results = await self._text_search(query)
            
            # Enhance results with AI data
            enhanced_results = await self._enhance_results(results, query)
            
            # Apply final filtering and ranking
            final_results = self._rank_and_filter_results(enhanced_results, query)
            
            # Cache results
            self.cache.set(cache_key, final_results, ttl=300)
            
            # Update statistics
            response_time = time.time() - start_time
            self.stats['avg_response_time'] = (
                (self.stats['avg_response_time'] * (self.stats['total_searches'] - 1) + response_time) 
                / self.stats['total_searches']
            )
            
            logger.info(f"Search completed: {len(final_results)} results in {response_time:.2f}s")
            return final_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_stream(self, query: SearchQuery, batch_size: int = 20):
        """
        Streaming search for large result sets.
        
        Yields batches of search results to avoid memory issues with large datasets.
        
        Args:
            query: Structured search query
            batch_size: Number of results per batch
            
        Yields:
            List[SearchResult]: Batches of search results
        """
        start_time = time.time()
        self.stats['total_searches'] += 1
        self.stats['streaming_searches'] = self.stats.get('streaming_searches', 0) + 1
        
        try:
            logger.info(f"Starting streaming search: {query.query[:50]} (batch_size={batch_size})")
            
            # Process in chunks to avoid memory issues
            offset = 0
            total_yielded = 0
            
            while total_yielded < query.limit:
                # Create chunk query
                chunk_limit = min(batch_size, query.limit - total_yielded)
                chunk_query = SearchQuery(
                    query=query.query,
                    search_type=query.search_type,
                    time_range=query.time_range,
                    entity_types=query.entity_types,
                    categories=query.categories,
                    min_relevance=query.min_relevance,
                    limit=chunk_limit,
                    include_tasks=query.include_tasks,
                    semantic_threshold=query.semantic_threshold
                )
                
                # Get chunk results with offset
                if query.search_type == "hybrid":
                    chunk_results = await self._hybrid_search_with_offset(chunk_query, offset)
                elif query.search_type == "semantic":
                    chunk_results = await self._semantic_search_with_offset(chunk_query, offset)
                else:
                    chunk_results = await self._text_search_with_offset(chunk_query, offset)
                
                if not chunk_results:
                    break  # No more results
                
                # Enhance and filter chunk
                enhanced_chunk = await self._enhance_results(chunk_results, chunk_query)
                filtered_chunk = self._rank_and_filter_results(enhanced_chunk, chunk_query)
                
                # Yield the batch
                yield filtered_chunk
                
                total_yielded += len(filtered_chunk)
                offset += batch_size
                
                # Break if we got fewer results than requested (no more data)
                if len(chunk_results) < chunk_limit:
                    break
                
                # Add small delay to prevent overwhelming the system
                import asyncio
                await asyncio.sleep(0.01)
            
            response_time = time.time() - start_time
            logger.info(f"Streaming search completed: {total_yielded} total results in {response_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Streaming search failed: {e}")
            yield []  # Yield empty list on error
    
    async def _hybrid_search_with_offset(self, query: SearchQuery, offset: int) -> List[PensieveEntity]:
        """Hybrid search with offset support for pagination."""
        results = []
        
        # Try Pensieve native search first
        try:
            if self.api_client.is_healthy():
                # Note: API client would need offset support
                api_results = self.api_client.search_entities(query.query, limit=query.limit)
                if api_results and offset < len(api_results):
                    results.extend(api_results[offset:offset + query.limit])
                    self.stats['api_searches'] += 1
                    logger.debug(f"Pensieve API search returned {len(results)} results (offset={offset})")
        except PensieveAPIError as e:
            logger.warning(f"Pensieve search API failed: {e.message}")
        
        # Fallback to enhanced SQLite search if needed
        if len(results) < query.limit // 2:
            fallback_results = await self._fallback_search_with_offset(query, offset)
            results.extend(fallback_results)
            self.stats['fallback_searches'] += 1
        
        return results
    
    async def _semantic_search_with_offset(self, query: SearchQuery, offset: int) -> List[PensieveEntity]:
        """Semantic search with offset support."""
        # For now, delegate to text search with offset
        return await self._text_search_with_offset(query, offset)
    
    async def _text_search_with_offset(self, query: SearchQuery, offset: int) -> List[PensieveEntity]:
        """Text search with offset support."""
        try:
            if self.api_client.is_healthy():
                # Get more results and slice for offset
                extended_limit = query.limit + offset
                results = self.api_client.search_entities(query.query, limit=extended_limit)
                self.stats['api_searches'] += 1
                
                if results and offset < len(results):
                    return results[offset:offset + query.limit]
                return []
        except PensieveAPIError as e:
            logger.warning(f"Pensieve text search failed: {e.message}")
        
        # Fallback to SQLite search with offset
        return await self._fallback_search_with_offset(query, offset)
    
    async def _fallback_search_with_offset(self, query: SearchQuery, offset: int) -> List[PensieveEntity]:
        """Database fallback search with offset support."""
        try:
            # Lazy load database manager to avoid circular imports
            from autotasktracker.core.database import DatabaseManager
            db_manager = DatabaseManager()
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build search query with LIMIT and OFFSET
                search_terms = query.query.split()
                where_conditions = []
                params = []
                
                for term in search_terms:
                    where_conditions.append("(me.value LIKE ? OR e.filepath LIKE ?)")
                    params.extend([f"%{term}%", f"%{term}%"])
                
                sql = f"""
                    SELECT DISTINCT e.id, e.filepath, e.filename, e.created_at, 
                           e.file_created_at, e.last_scan_at, e.file_type_group
                    FROM entities e
                    LEFT JOIN metadata_entries me ON e.id = me.entity_id
                    WHERE {' AND '.join(where_conditions) if where_conditions else '1=1'}
                    ORDER BY e.created_at DESC
                    LIMIT ? OFFSET ?
                """
                
                params.extend([query.limit, offset])
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    entity = PensieveEntity(
                        id=row[0],
                        filepath=row[1],
                        filename=row[2],
                        created_at=row[3],
                        file_created_at=row[4],
                        last_scan_at=row[5],
                        file_type_group=row[6] or "image"
                    )
                    results.append(entity)
                
                return results
                
        except Exception as e:
            logger.error(f"Fallback search with offset failed: {e}")
            return []
    
    async def search_by_tags(self, tags: List[str], operator: str = "AND", limit: int = 50) -> List[SearchResult]:
        """
        Search entities by tags using direct database integration.
        
        Args:
            tags: List of tag names to search for
            operator: "AND" or "OR" for tag matching
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        start_time = time.time()
        self.stats['total_searches'] += 1
        self.stats['tag_searches'] += 1
        
        try:
            # Try cache first
            cache_key = f"tag_search_{hash(tuple(sorted(tags)))}_{operator}_{limit}"
            cached_results = self.cache.get(cache_key)
            if cached_results:
                self.stats['cache_hits'] += 1
                return cached_results
            
            results = []
            
            # Use tag manager for direct database search
            if self.tag_manager:
                entities = self.tag_manager.search_entities_by_tags(tags, operator, limit)
                
                for entity_data in entities:
                    # Create PensieveEntity from database result
                    entity = PensieveEntity(
                        id=entity_data['id'],
                        filepath=entity_data['filepath'],
                        filename=entity_data.get('filename', ''),
                        created_at=entity_data['created_at'],
                        file_created_at=entity_data.get('file_created_at'),
                        last_scan_at=entity_data.get('last_scan_at'),
                        file_type_group=entity_data.get('file_type_group', 'image'),
                        metadata=entity_data
                    )
                    
                    # Calculate relevance based on tag matches
                    entity_tags = entity_data.get('tags', [])
                    matched_tags = set(tags) & set(entity_tags)
                    relevance = len(matched_tags) / len(tags) if tags else 0.0
                    
                    # Extract context from metadata
                    context_parts = []
                    if 'ocr_result' in entity_data:
                        ocr_text = str(entity_data['ocr_result'])[:100]
                        context_parts.append(f"OCR: {ocr_text}...")
                    if 'vlm_description' in entity_data:
                        vlm_desc = str(entity_data['vlm_description'])[:100]
                        context_parts.append(f"VLM: {vlm_desc}...")
                    
                    context_snippet = " | ".join(context_parts)
                    
                    result = SearchResult(
                        entity=entity,
                        relevance_score=relevance,
                        match_type="tags",
                        matched_fields=["tags"],
                        context_snippet=context_snippet,
                        ai_extracted_tasks=[],
                        category=None,
                        confidence=relevance
                    )
                    
                    results.append(result)
            
            # Cache results
            self.cache.set(cache_key, results, ttl=300)
            
            # Update stats
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            logger.info(f"Tag search completed: {len(results)} results for tags {tags} in {response_time:.3f}s")
            return results
            
        except Exception as e:
            logger.error(f"Tag search failed: {e}")
            return []
    
    async def semantic_search_enhanced(self, query: str, limit: int = 50, threshold: float = 0.7) -> List[SearchResult]:
        """
        Enhanced semantic search with fallback to vector database.
        
        Args:
            query: Search query
            limit: Maximum number of results  
            threshold: Similarity threshold
            
        Returns:
            List of semantic search results
        """
        start_time = time.time()
        self.stats['total_searches'] += 1
        self.stats['semantic_searches'] += 1
        
        try:
            # Try cache first
            cache_key = f"semantic_search_{hash(query)}_{limit}_{threshold}"
            cached_results = self.cache.get(cache_key)
            if cached_results:
                self.stats['cache_hits'] += 1
                return cached_results
            
            results = []
            
            # Try API-first approach
            try:
                self.stats['api_searches'] += 1
                api_entities = self.api_client.semantic_search(query, limit, threshold)
                
                for entity in api_entities:
                    # Extract similarity score from metadata
                    similarity = entity.metadata.get('similarity_score', threshold)
                    
                    result = SearchResult(
                        entity=entity,
                        relevance_score=similarity,
                        match_type="semantic",
                        matched_fields=["embeddings"],
                        context_snippet=f"Semantic match: {similarity:.3f}",
                        ai_extracted_tasks=[],
                        category=None,
                        confidence=similarity
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                logger.debug(f"API semantic search failed, using fallback: {e}")
                self.stats['fallback_searches'] += 1
                
                # Fallback to direct vector database query if available
                if self._has_vector_search():
                    results = await self._vector_search_fallback(query, limit, threshold)
            
            # Cache results
            self.cache.set(cache_key, results, ttl=600)  # Longer TTL for expensive operations
            
            # Update stats
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            logger.info(f"Semantic search completed: {len(results)} results for '{query}' in {response_time:.3f}s")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _has_vector_search(self) -> bool:
        """Check if vector search tables exist in database."""
        try:
            if not self.db_manager:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = None  # Will implement when needed
            
            # For now, assume vector search is available if we have the tables
            # This could be enhanced to actually check table existence
            return True
            
        except Exception:
            return False
    
    async def _vector_search_fallback(self, query: str, limit: int, threshold: float) -> List[SearchResult]:
        """Fallback vector search using direct database access."""
        # Placeholder for direct vector database search
        # This would require implementing vector similarity search against entities_vec_v2 tables
        logger.info("Vector search fallback not yet implemented")
        return []
    
    def _update_response_time(self, response_time: float):
        """Update average response time statistics."""
        current_avg = self.stats['avg_response_time']
        total_searches = self.stats['total_searches']
        
        if total_searches == 1:
            self.stats['avg_response_time'] = response_time
        else:
            self.stats['avg_response_time'] = (
                (current_avg * (total_searches - 1) + response_time) / total_searches
            )
    
    async def _hybrid_search(self, query: SearchQuery) -> List[PensieveEntity]:
        """Perform hybrid search combining text and semantic approaches."""
        results = []
        
        # Try Pensieve native search first
        try:
            if self.api_client.is_healthy():
                api_results = self.api_client.search_entities(query.query, limit=query.limit)
                if api_results:
                    results.extend(api_results)
                    self.stats['api_searches'] += 1
                    logger.debug(f"Pensieve API search returned {len(api_results)} results")
        except PensieveAPIError as e:
            logger.warning(f"Pensieve search API failed: {e.message}")
        
        # Fallback to enhanced SQLite search if needed
        if len(results) < query.limit // 2:
            fallback_results = await self._fallback_search(query)
            results.extend(fallback_results)
            self.stats['fallback_searches'] += 1
        
        return results
    
    async def _semantic_search(self, query: SearchQuery) -> List[PensieveEntity]:
        """Perform semantic search using embeddings."""
        # This would integrate with the vector search capabilities
        # For now, fallback to text search with semantic hints
        logger.info("Semantic search requested - using enhanced text search")
        return await self._text_search(query)
    
    async def _text_search(self, query: SearchQuery) -> List[PensieveEntity]:
        """Perform text-based search using Pensieve API."""
        try:
            if self.api_client.is_healthy():
                results = self.api_client.search_entities(query.query, limit=query.limit)
                self.stats['api_searches'] += 1
                return results
        except PensieveAPIError as e:
            logger.warning(f"Pensieve text search failed: {e.message}")
        
        # Fallback to SQLite search
        return await self._fallback_search(query)
    
    async def _fallback_search(self, query: SearchQuery) -> List[PensieveEntity]:
        """Fallback search using direct database access."""
        self.stats['fallback_searches'] += 1
        
        try:
            # Lazy load database manager to avoid circular imports
            if self.db_manager is None:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = DatabaseManager()
            
            # Use database manager for fallback search
            df = self.db_manager.search_activities(query.query, limit=query.limit)
            
            results = []
            for _, row in df.iterrows():
                # Convert DataFrame row to PensieveEntity
                entity = PensieveEntity(
                    id=row['id'],
                    filepath=row.get('filepath', ''),
                    filename=row.get('filename', ''),
                    created_at=row.get('created_at', ''),
                    file_created_at=row.get('file_created_at'),
                    last_scan_at=row.get('last_scan_at'),
                    file_type_group=row.get('file_type_group', 'image'),
                    metadata={
                        'ocr_result': row.get('ocr_text', ''),
                        'active_window': row.get('active_window', '')
                    }
                )
                results.append(entity)
            
            logger.debug(f"Fallback search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    async def _enhance_results(self, entities: List[PensieveEntity], query: SearchQuery) -> List[SearchResult]:
        """Enhance search results with AI data and relevance scoring."""
        enhanced_results = []
        
        for entity in entities:
            try:
                # Calculate relevance score
                relevance_score = self._calculate_relevance(entity, query.query)
                
                # Skip if below minimum relevance
                if relevance_score < query.min_relevance:
                    continue
                
                # Determine match type
                match_type = self._determine_match_type(entity, query.query)
                
                # Find matched fields
                matched_fields = self._find_matched_fields(entity, query.query)
                
                # Generate context snippet
                context_snippet = self._generate_context_snippet(entity, query.query)
                
                # Get AI-extracted tasks if requested
                ai_tasks = []
                category = None
                if query.include_tasks:
                    ai_tasks, category = await self._get_ai_data(entity.id)
                
                # Create enhanced result
                result = SearchResult(
                    entity=entity,
                    relevance_score=relevance_score,
                    match_type=match_type,
                    matched_fields=matched_fields,
                    context_snippet=context_snippet,
                    ai_extracted_tasks=ai_tasks,
                    category=category,
                    confidence=min(relevance_score, 1.0)
                )
                
                enhanced_results.append(result)
                
            except Exception as e:
                logger.warning(f"Failed to enhance result for entity {entity.id}: {e}")
                continue
        
        return enhanced_results
    
    def _calculate_relevance(self, entity: PensieveEntity, query: str) -> float:
        """Calculate relevance score for an entity."""
        score = 0.0
        query_lower = query.lower()
        
        # OCR text relevance (highest weight)
        ocr_text = entity.metadata.get('ocr_result', '').lower()
        if query_lower in ocr_text:
            score += 0.4
            # Bonus for exact phrase match
            if len(query.split()) > 1 and query_lower in ocr_text:
                score += 0.2
        
        # Window title relevance
        window_title = entity.metadata.get('active_window', '').lower()
        if query_lower in window_title:
            score += 0.3
        
        # Filename relevance
        if query_lower in entity.filename.lower():
            score += 0.2
        
        # Recency bonus (newer results get slight boost)
        try:
            created_time = datetime.fromisoformat(entity.created_at.replace('Z', '+00:00'))
            hours_old = (datetime.now() - created_time).total_seconds() / 3600
            if hours_old < 24:
                score += 0.1 * (1 - hours_old / 24)
        except Exception as e:
            logger.debug(f"Could not parse creation time for recency scoring: {e}")
        
        return min(score, 1.0)
    
    def _determine_match_type(self, entity: PensieveEntity, query: str) -> str:
        """Determine how the entity matched the query."""
        query_lower = query.lower()
        
        ocr_text = entity.metadata.get('ocr_result', '').lower()
        window_title = entity.metadata.get('active_window', '').lower()
        
        if query_lower in ocr_text and query_lower in window_title:
            return "hybrid"
        elif query_lower in ocr_text:
            return "text"
        elif query_lower in window_title:
            return "metadata"
        else:
            return "semantic"
    
    def _find_matched_fields(self, entity: PensieveEntity, query: str) -> List[str]:
        """Find which fields matched the query."""
        matched = []
        query_lower = query.lower()
        
        if query_lower in entity.metadata.get('ocr_result', '').lower():
            matched.append('ocr_text')
        
        if query_lower in entity.metadata.get('active_window', '').lower():
            matched.append('window_title')
        
        if query_lower in entity.filename.lower():
            matched.append('filename')
        
        return matched
    
    def _generate_context_snippet(self, entity: PensieveEntity, query: str, max_length: int = 200) -> str:
        """Generate context snippet showing query matches."""
        ocr_text = entity.metadata.get('ocr_result', '')
        query_lower = query.lower()
        
        if not ocr_text or query_lower not in ocr_text.lower():
            # Return window title or filename as fallback
            return entity.metadata.get('active_window', entity.filename)[:max_length]
        
        # Find query position in text
        text_lower = ocr_text.lower()
        query_pos = text_lower.find(query_lower)
        
        if query_pos == -1:
            return ocr_text[:max_length]
        
        # Extract context around the match
        start = max(0, query_pos - 50)
        end = min(len(ocr_text), query_pos + len(query) + 50)
        
        snippet = ocr_text[start:end].strip()
        
        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(ocr_text):
            snippet = snippet + "..."
        
        return snippet[:max_length]
    
    async def _get_ai_data(self, entity_id: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Get AI-extracted tasks and category for an entity."""
        try:
            # Try API first
            if self.api_client.is_healthy():
                metadata = self.api_client.get_entity_metadata(entity_id)
                
                # Extract tasks
                tasks_json = metadata.get('tasks', '[]')
                if isinstance(tasks_json, str):
                    import json
                    tasks = json.loads(tasks_json) if tasks_json else []
                else:
                    tasks = tasks_json or []
                
                # Extract category
                category = metadata.get('category')
                
                return tasks, category
        
        except Exception as e:
            logger.debug(f"Failed to get AI data via API for entity {entity_id}: {e}")
        
        # Fallback to database
        try:
            # Lazy load database manager to avoid circular imports
            if self.db_manager is None:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = DatabaseManager()
                
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT key, value FROM metadata_entries 
                    WHERE entity_id = ? AND key IN ('tasks', 'category')
                """, (entity_id,))
                
                metadata = dict(cursor.fetchall())
                
                # Extract tasks
                tasks_json = metadata.get('tasks', '[]')
                if tasks_json:
                    import json
                    tasks = json.loads(tasks_json)
                else:
                    tasks = []
                
                # Extract category
                category = metadata.get('category')
                
                return tasks, category
                
        except Exception as e:
            logger.debug(f"Failed to get AI data via database for entity {entity_id}: {e}")
            return [], None
    
    def _rank_and_filter_results(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Apply final ranking and filtering to results."""
        # Filter by time range
        if query.time_range:
            start_time, end_time = query.time_range
            filtered_results = []
            
            for result in results:
                try:
                    created_time = datetime.fromisoformat(result.entity.created_at.replace('Z', '+00:00'))
                    if start_time <= created_time <= end_time:
                        filtered_results.append(result)
                except Exception:
                    continue
            
            results = filtered_results
        
        # Filter by categories
        if query.categories:
            results = [r for r in results if r.category in query.categories]
        
        # Sort by relevance score (descending)
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        # Apply limit
        return results[:query.limit]
    
    def _generate_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for search query."""
        key_parts = [
            f"query:{query.query}",
            f"type:{query.search_type}",
            f"limit:{query.limit}",
            f"min_rel:{query.min_relevance}"
        ]
        
        if query.time_range:
            start, end = query.time_range
            key_parts.append(f"time:{start.isoformat()}:{end.isoformat()}")
        
        if query.categories:
            key_parts.append(f"cats:{','.join(sorted(query.categories))}")
        
        return "search_" + "_".join(key_parts)
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        try:
            # Lazy load database manager to avoid circular imports
            if self.db_manager is None:
                # DatabaseManager import moved to avoid circular dependency
                self.db_manager = DatabaseManager()
                
            # Simple suggestion based on common terms in OCR data
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT value FROM metadata_entries 
                    WHERE key = 'ocr_result' AND value LIKE ? 
                    LIMIT ?
                """, (f'%{partial_query}%', limit * 2))
                
                suggestions = set()
                for (text,) in cursor.fetchall():
                    # Extract words containing the partial query
                    words = text.lower().split()
                    for word in words:
                        if partial_query.lower() in word and len(word) > len(partial_query):
                            suggestions.add(word)
                            if len(suggestions) >= limit:
                                break
                
                return list(suggestions)[:limit]
                
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search performance statistics."""
        return {
            **self.stats,
            'api_health': self.api_client.is_healthy(),
            'cache_stats': self.cache.get_stats()
        }


# Global instance
_advanced_search: Optional[PensieveEnhancedSearch] = None


def get_advanced_search() -> PensieveEnhancedSearch:
    """Get global enhanced search instance."""
    global _advanced_search
    if _advanced_search is None:
        _advanced_search = PensieveEnhancedSearch()
    return _advanced_search


def reset_advanced_search():
    """Reset enhanced search instance (useful for testing)."""
    global _advanced_search
    _advanced_search = None