"""Enhanced vector search with pgvector support via Pensieve."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import json
from dataclasses import dataclass, asdict
import asyncio

from .postgresql_adapter import get_postgresql_adapter
from .api_client import get_pensieve_client
from .advanced_search import SearchQuery, SearchResult, get_advanced_search

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchQuery:
    """Enhanced search query with vector capabilities."""
    text: str
    use_semantic: bool = True
    use_keyword: bool = True
    similarity_threshold: float = 0.7
    max_results: int = 20
    date_range: Optional[Tuple[datetime, datetime]] = None
    categories: Optional[List[str]] = None
    vector_dimensions: int = 768
    search_radius: float = 0.3  # For neighborhood search


@dataclass
class VectorSearchResult(SearchResult):
    """Enhanced search result with vector similarity data."""
    vector_similarity_score: float = 0.0
    vector_distance: float = 1.0
    embedding_quality: str = "unknown"  # high, medium, low, unknown
    semantic_cluster: Optional[str] = None
    similar_activities: List[str] = None


class EnhancedVectorSearch:
    """Enhanced vector search with pgvector optimization."""
    
    def __init__(self):
        self.pg_adapter = get_postgresql_adapter()
        self.pensieve_client = get_pensieve_client()
        self.fallback_search = get_advanced_search()
        self.capabilities = self.pg_adapter.capabilities
        
        logger.info(f"Enhanced vector search initialized - Backend: {self.capabilities.performance_tier}")
    
    async def search(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Perform enhanced vector search with pgvector optimization."""
        
        if self.capabilities.performance_tier == 'pgvector':
            return await self._search_with_pgvector(query)
        elif self.capabilities.performance_tier == 'postgresql':
            return await self._search_with_postgresql(query)
        else:
            return await self._search_with_fallback(query)
    
    async def _search_with_pgvector(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search using pgvector native vector operations."""
        try:
            logger.info("Performing pgvector-optimized search")
            
            # Generate query embedding for semantic search
            query_embedding = await self._generate_query_embedding(query.text)
            
            if not query_embedding:
                logger.warning("Failed to generate query embedding, falling back")
                return await self._search_with_postgresql(query)
            
            # Perform vector similarity search via Pensieve API
            vector_results = await self._pgvector_similarity_search(
                query_embedding, 
                query.similarity_threshold,
                query.max_results,
                query.date_range,
                query.categories
            )
            
            # Enhance results with additional metadata
            enhanced_results = []
            for result in vector_results:
                enhanced_result = await self._enhance_vector_result(result, query_embedding)
                enhanced_results.append(enhanced_result)
            
            # Combine with keyword search if requested
            if query.use_keyword:
                keyword_results = await self._keyword_search_supplement(query, enhanced_results)
                enhanced_results = self._merge_search_results(enhanced_results, keyword_results)
            
            # Sort by combined relevance score
            enhanced_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.info(f"pgvector search returned {len(enhanced_results)} results")
            return enhanced_results[:query.max_results]
            
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return await self._search_with_postgresql(query)
    
    async def _search_with_postgresql(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search using PostgreSQL with manual vector operations."""
        try:
            logger.info("Performing PostgreSQL-optimized search")
            
            # Use enhanced database queries for better performance
            tasks = await self.pg_adapter.get_tasks_optimized(
                start_date=query.date_range[0] if query.date_range else datetime(2020, 1, 1),
                end_date=query.date_range[1] if query.date_range else datetime.now(),
                categories=query.categories,
                limit=query.max_results * 2  # Get more for filtering
            )
            
            # Generate query embedding for semantic comparison
            query_embedding = await self._generate_query_embedding(query.text)
            
            # Process and score results
            enhanced_results = []
            for task in tasks:
                result = await self._create_enhanced_result_from_task(task, query, query_embedding)
                if result and result.relevance_score >= query.similarity_threshold:
                    enhanced_results.append(result)
            
            # Sort and limit results
            enhanced_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.info(f"PostgreSQL search returned {len(enhanced_results)} results")
            return enhanced_results[:query.max_results]
            
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}")
            return await self._search_with_fallback(query)
    
    async def _search_with_fallback(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search using SQLite fallback with basic vector operations."""
        try:
            logger.info("Performing SQLite fallback search")
            
            # Convert to basic search query
            basic_query = SearchQuery(
                text=query.text,
                use_semantic=query.use_semantic,
                use_keyword=query.use_keyword,
                max_results=query.max_results
            )
            
            # Use existing advanced search
            basic_results = self.fallback_search.search(basic_query)
            
            # Convert to enhanced results
            enhanced_results = []
            for result in basic_results:
                enhanced_result = VectorSearchResult(
                    **asdict(result),
                    vector_similarity_score=result.relevance_score,
                    vector_distance=1.0 - result.relevance_score,
                    embedding_quality="low",
                    similar_activities=[]
                )
                enhanced_results.append(enhanced_result)
            
            logger.info(f"Fallback search returned {len(enhanced_results)} results")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"All search methods failed: {e}")
            return []
    
    async def _generate_query_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for search query."""
        try:
            # Try to use Pensieve's embedding service if available
            if self.pensieve_client and self.pensieve_client.is_healthy():
                # This would use Pensieve's embedding API when available
                # For now, use our existing embedding logic
                logger.debug("Pensieve embedding API not yet implemented, using fallback")
            
            # Fallback to basic embedding generation
            from ..ai.embeddings_search import generate_embedding
            embedding = generate_embedding(text)
            
            if embedding and len(embedding) == self.capabilities.vector_dimensions:
                return embedding
            
        except Exception as e:
            logger.debug(f"Failed to generate query embedding: {e}")
        
        return None
    
    async def _pgvector_similarity_search(
        self,
        query_embedding: List[float],
        threshold: float,
        limit: int,
        date_range: Optional[Tuple[datetime, datetime]],
        categories: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Perform native pgvector similarity search."""
        try:
            # This would use actual pgvector SQL queries via Pensieve API
            # For now, simulate with regular API calls
            
            search_params = {
                'vector_query': query_embedding,
                'similarity_threshold': threshold,
                'limit': limit
            }
            
            if date_range:
                search_params['start_date'] = date_range[0].isoformat()
                search_params['end_date'] = date_range[1].isoformat()
            
            if categories:
                search_params["category"] = categories
            
            # Make API call (this would be pgvector-specific endpoint)
            frames = self.pensieve_client.get_frames(limit=limit)
            
            # For each frame, get metadata and calculate similarity
            results = []
            for frame in frames:
                metadata = self.pensieve_client.get_metadata(frame.id)
                
                # Calculate vector similarity if embeddings exist
                if 'embeddings' in metadata:
                    try:
                        stored_embedding = json.loads(metadata['embeddings'])
                        similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                        
                        if similarity >= threshold:
                            results.append({
                                'frame': frame,
                                'metadata': metadata,
                                'vector_similarity': similarity,
                                'vector_distance': 1.0 - similarity
                            })
                    except Exception as e:
                        logger.debug(f"Failed to calculate similarity for frame {frame.id}: {e}")
            
            # Sort by similarity
            results.sort(key=lambda x: x['vector_similarity'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"pgvector similarity search failed: {e}")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            
            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, (similarity + 1) / 2))
            
        except Exception as e:
            logger.debug(f"Failed to calculate cosine similarity: {e}")
            return 0.0
    
    async def _enhance_vector_result(
        self, 
        result: Dict[str, Any], 
        query_embedding: List[float]
    ) -> VectorSearchResult:
        """Enhance a vector search result with additional metadata."""
        try:
            frame = result['frame']
            metadata = result['metadata']
            
            # Extract basic information
            window_title = metadata.get("active_window", 'Unknown')
            tasks = self._parse_tasks(metadata.get("tasks", []))
            category = metadata.get("category", 'Other')
            
            # Get OCR text
            ocr_text = self.pensieve_client.get_ocr_result(frame.id)
            
            # Calculate embedding quality
            embedding_quality = self._assess_embedding_quality(metadata.get('embeddings'))
            
            # Find similar activities (semantic clustering)
            similar_activities = await self._find_similar_activities(result['vector_similarity'], category)
            
            # Determine semantic cluster
            semantic_cluster = self._determine_semantic_cluster(tasks, category)
            
            # Create enhanced result
            enhanced_result = VectorSearchResult(
                entity_id=frame.id,
                window_title=window_title,
                timestamp=frame.created_at,
                relevance_score=result['vector_similarity'],
                search_method='pgvector',
                highlights=self._extract_highlights(ocr_text, window_title),
                extracted_tasks=[task['title'] for task in tasks],
                activity_category=category,
                vector_similarity_score=result['vector_similarity'],
                vector_distance=result['vector_distance'],
                embedding_quality=embedding_quality,
                semantic_cluster=semantic_cluster,
                similar_activities=similar_activities
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Failed to enhance vector result: {e}")
            return None
    
    async def _create_enhanced_result_from_task(
        self,
        task: Dict[str, Any],
        query: VectorSearchQuery,
        query_embedding: Optional[List[float]]
    ) -> Optional[VectorSearchResult]:
        """Create enhanced result from task data."""
        try:
            # Calculate relevance score
            relevance_score = self._calculate_task_relevance(task, query)
            
            # Calculate vector similarity if embeddings available
            vector_similarity = 0.0
            vector_distance = 1.0
            
            if query_embedding and 'embeddings' in task:
                try:
                    task_embedding = json.loads(task['embeddings'])
                    vector_similarity = self._calculate_cosine_similarity(query_embedding, task_embedding)
                    vector_distance = 1.0 - vector_similarity
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse embeddings for task: {e}")
            
            # Determine embedding quality
            embedding_quality = self._assess_embedding_quality(task.get('embeddings'))
            
            # Extract task information
            tasks = task.get("tasks", [])
            if isinstance(tasks, str):
                try:
                    tasks = json.loads(tasks)
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse tasks JSON, using string fallback: {e}")
                    tasks = [{'title': tasks, "category": 'Other'}]
            
            # Create enhanced result
            enhanced_result = VectorSearchResult(
                entity_id=task['id'],
                window_title=task.get("active_window", 'Unknown'),
                timestamp=task['timestamp'],
                relevance_score=max(relevance_score, vector_similarity),
                search_method='postgresql_enhanced',
                highlights=self._extract_highlights(task.get("ocr_result", ''), task.get("active_window", '')),
                extracted_tasks=[t.get('title', str(t)) if isinstance(t, dict) else str(t) for t in tasks],
                activity_category=task.get("category", 'Other'),
                vector_similarity_score=vector_similarity,
                vector_distance=vector_distance,
                embedding_quality=embedding_quality,
                semantic_cluster=self._determine_semantic_cluster(tasks, task.get("category", 'Other')),
                similar_activities=[]
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Failed to create enhanced result from task: {e}")
            return None
    
    def _calculate_task_relevance(self, task: Dict[str, Any], query: VectorSearchQuery) -> float:
        """Calculate relevance score for a task."""
        try:
            relevance = 0.0
            query_lower = query.text.lower()
            
            # Check window title
            window_title = task.get("active_window", '').lower()
            if query_lower in window_title:
                relevance += 0.3
            
            # Check tasks
            tasks = task.get("tasks", [])
            if isinstance(tasks, str):
                if query_lower in tasks.lower():
                    relevance += 0.4
            elif isinstance(tasks, list):
                for task_item in tasks:
                    task_text = str(task_item).lower()
                    if query_lower in task_text:
                        relevance += 0.4
                        break
            
            # Check OCR text
            ocr_text = task.get("ocr_result", '').lower()
            if query_lower in ocr_text:
                relevance += 0.2
            
            # Check category match
            if query.categories and task.get("category") in query.categories:
                relevance += 0.1
            
            return min(1.0, relevance)
            
        except Exception as e:
            logger.debug(f"Failed to calculate task relevance: {e}")
            return 0.0
    
    def _assess_embedding_quality(self, embeddings_data: Any) -> str:
        """Assess the quality of stored embeddings."""
        if not embeddings_data:
            return "unknown"
        
        try:
            if isinstance(embeddings_data, str):
                embeddings = json.loads(embeddings_data)
            else:
                embeddings = embeddings_data
            
            if not isinstance(embeddings, list) or len(embeddings) != self.capabilities.vector_dimensions:
                return "low"
            
            # Check if embeddings look reasonable
            embedding_array = np.array(embeddings)
            if np.all(embedding_array == 0) or np.any(np.isnan(embedding_array)):
                return "low"
            
            # Check variance (good embeddings should have some variance)
            variance = np.var(embedding_array)
            if variance > 0.01:
                return "high"
            elif variance > 0.001:
                return "medium"
            else:
                return "low"
                
        except Exception:
            return "unknown"
    
    async def _find_similar_activities(self, similarity_score: float, category: str) -> List[str]:
        """Find similar activities based on vector similarity."""
        try:
            # This would use pgvector's similarity search to find related activities
            # For now, return category-based suggestions
            category_activities = {
                'Development': ['Code Review', 'Testing', 'Documentation', 'Debugging'],
                'Communication': ['Email', 'Slack', 'Meeting', 'Video Call'],
                'Research': ['Web Search', 'Reading', 'Analysis', 'Investigation'],
                'Productivity': ['Planning', 'Task Management', 'Note Taking', 'Organization']
            }
            
            return category_activities.get(category, ['Related Activity', 'Similar Task'])[:3]
            
        except Exception:
            return []
    
    def _determine_semantic_cluster(self, tasks: List[Any], category: str) -> Optional[str]:
        """Determine semantic cluster for the activity."""
        try:
            # Simple clustering based on category and task content
            if category == 'Development':
                return 'software_development'
            elif category in ['Communication', 'Meeting']:
                return 'collaboration'
            elif category in ['Research', 'Reading']:
                return 'knowledge_work'
            elif category in ['Productivity', 'Planning']:
                return 'organization'
            else:
                return 'general_activity'
                
        except Exception:
            return None
    
    def _parse_tasks(self, tasks_data: Any) -> List[Dict[str, Any]]:
        """Parse task data safely."""
        try:
            if isinstance(tasks_data, str):
                tasks = json.loads(tasks_data)
            elif isinstance(tasks_data, list):
                tasks = tasks_data
            else:
                return []
            
            parsed_tasks = []
            for task in tasks:
                if isinstance(task, dict):
                    parsed_tasks.append(task)
                elif isinstance(task, str):
                    parsed_tasks.append({'title': task, "category": 'Other'})
            
            return parsed_tasks
            
        except Exception:
            return []
    
    def _extract_highlights(self, ocr_text: str, window_title: str) -> List[str]:
        """Extract text highlights."""
        highlights = []
        
        if window_title:
            highlights.append(f"Window: {window_title}")
        
        if ocr_text:
            # Extract first few meaningful words
            words = ocr_text.split()[:10]
            if words:
                highlights.append(" ".join(words) + "...")
        
        return highlights
    
    async def _keyword_search_supplement(
        self, 
        query: VectorSearchQuery, 
        vector_results: List[VectorSearchResult]
    ) -> List[VectorSearchResult]:
        """Supplement vector results with keyword search."""
        try:
            # Perform keyword search
            keyword_query = SearchQuery(
                text=query.text,
                use_semantic=False,
                use_keyword=True,
                max_results=query.max_results
            )
            
            keyword_results = self.fallback_search.search(keyword_query)
            
            # Convert to enhanced results
            enhanced_keyword_results = []
            for result in keyword_results:
                # Check if this result is already in vector results
                existing = any(vr.entity_id == result.entity_id for vr in vector_results)
                if not existing:
                    enhanced_result = VectorSearchResult(
                        **asdict(result),
                        vector_similarity_score=0.0,
                        vector_distance=1.0,
                        embedding_quality="unknown",
                        similar_activities=[]
                    )
                    enhanced_keyword_results.append(enhanced_result)
            
            return enhanced_keyword_results
            
        except Exception as e:
            logger.debug(f"Failed to supplement with keyword search: {e}")
            return []
    
    def _merge_search_results(
        self, 
        vector_results: List[VectorSearchResult], 
        keyword_results: List[VectorSearchResult]
    ) -> List[VectorSearchResult]:
        """Merge vector and keyword search results."""
        try:
            # Combine results, avoiding duplicates
            combined_results = vector_results.copy()
            
            for keyword_result in keyword_results:
                # Check if this result already exists
                existing = any(vr.entity_id == keyword_result.entity_id for vr in combined_results)
                if not existing:
                    combined_results.append(keyword_result)
            
            return combined_results
            
        except Exception as e:
            logger.debug(f"Failed to merge search results: {e}")
            return vector_results
    
    async def get_search_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for vector search."""
        try:
            # Run performance test
            test_query = VectorSearchQuery(
                text="test search performance",
                max_results=10
            )
            
            start_time = datetime.now()
            results = await self.search(test_query)
            search_time = (datetime.now() - start_time).total_seconds() * 1000
            
            pg_metrics = await self.pg_adapter.get_performance_metrics()
            
            return {
                'search_backend': self.capabilities.performance_tier,
                'sample_search_time_ms': round(search_time, 2),
                'results_returned': len(results),
                'vector_dimensions_supported': self.capabilities.vector_dimensions,
                'max_vectors_supported': self.capabilities.max_vectors,
                'postgresql_metrics': pg_metrics,
                'features': {
                    'pgvector_native': self.capabilities.pgvector_available,
                    'vector_similarity': True,
                    'semantic_clustering': True,
                    'hybrid_search': True
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get search performance metrics: {e}")
            return {
                'search_backend': 'unknown',
                'error': str(e)
            }


# Singleton instance
_enhanced_vector_search: Optional[EnhancedVectorSearch] = None


def get_enhanced_vector_search() -> EnhancedVectorSearch:
    """Get singleton enhanced vector search."""
    global _enhanced_vector_search
    if _enhanced_vector_search is None:
        _enhanced_vector_search = EnhancedVectorSearch()
    return _enhanced_vector_search


def reset_enhanced_vector_search():
    """Reset for testing."""
    global _enhanced_vector_search
    _enhanced_vector_search = None