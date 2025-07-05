"""
Unified search coordinator for integrated Pensieve search capabilities.
Orchestrates streaming search, vector search, and traditional search with intelligent routing.
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator, Union, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json

from autotasktracker.pensieve.advanced_search import (
    get_advanced_search, SearchQuery, SearchResult, AdvancedSearch
)
from autotasktracker.pensieve.vector_search import (
    get_enhanced_vector_search, VectorSearchQuery, VectorSearchResult, EnhancedVectorSearch
)
from autotasktracker.pensieve.api_client import get_pensieve_client
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter
from autotasktracker.pensieve.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


@dataclass
class UnifiedSearchQuery:
    """Unified search query supporting all search modes."""
    text: str
    search_modes: List[str] = None  # text, semantic, vector, hybrid, streaming
    max_results: int = 50
    time_range: Optional[Tuple[datetime, datetime]] = None
    categories: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    
    # Advanced options
    use_streaming: bool = False
    streaming_batch_size: int = 20
    semantic_threshold: float = 0.7
    vector_similarity_threshold: float = 0.7
    include_highlights: bool = True
    include_metadata: bool = True
    
    # Performance options
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    max_concurrent_searches: int = 3
    timeout_seconds: int = 30
    
    def __post_init__(self):
        if self.search_modes is None:
            self.search_modes = ['hybrid']


@dataclass
class UnifiedSearchResult:
    """Unified search result combining all search capabilities."""
    entity_id: int
    relevance_score: float
    search_method: str
    window_title: str
    timestamp: datetime
    
    # Content
    highlights: List[str]
    extracted_tasks: List[str]
    activity_category: str
    
    # Advanced features
    vector_similarity_score: Optional[float] = None
    semantic_cluster: Optional[str] = None
    similar_activities: List[str] = None
    confidence_metrics: Dict[str, float] = None
    
    # Metadata
    source_info: Dict[str, Any] = None
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    
    def __post_init__(self):
        if self.confidence_metrics is None:
            self.confidence_metrics = {}
        if self.source_info is None:
            self.source_info = {}
        if self.similar_activities is None:
            self.similar_activities = []


@dataclass
class SearchCoordinatorStats:
    """Search coordinator performance statistics."""
    total_searches: int = 0
    streaming_searches: int = 0
    vector_searches: int = 0
    hybrid_searches: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_response_time_ms: float = 0.0
    peak_concurrent_searches: int = 0
    current_active_searches: int = 0
    
    # Performance breakdown
    search_method_usage: Dict[str, int] = None
    performance_by_method: Dict[str, float] = None
    error_rates: Dict[str, float] = None
    
    def __post_init__(self):
        if self.search_method_usage is None:
            self.search_method_usage = defaultdict(int)
        if self.performance_by_method is None:
            self.performance_by_method = defaultdict(float)
        if self.error_rates is None:
            self.error_rates = defaultdict(float)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_searches': self.total_searches,
            'streaming_searches': self.streaming_searches,
            'vector_searches': self.vector_searches,
            'hybrid_searches': self.hybrid_searches,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'average_response_time_ms': self.average_response_time_ms,
            'peak_concurrent_searches': self.peak_concurrent_searches,
            'current_active_searches': self.current_active_searches,
            'search_method_usage': dict(self.search_method_usage),
            'performance_by_method': dict(self.performance_by_method),
            'error_rates': dict(self.error_rates)
        }


class UnifiedSearchCoordinator:
    """Orchestrates all search capabilities with intelligent routing and optimization."""
    
    def __init__(self):
        """Initialize unified search coordinator."""
        # Search engines
        self.advanced_search = get_advanced_search()
        self.vector_search = get_enhanced_vector_search()
        self.api_client = get_pensieve_client()
        
        # Infrastructure
        self.pg_adapter = get_postgresql_adapter()
        self.health_monitor = get_health_monitor()
        self.cache_manager = get_cache_manager()
        
        # Statistics and monitoring
        self.stats = SearchCoordinatorStats()
        self.active_searches: Dict[str, datetime] = {}
        self.search_history: deque = deque(maxlen=1000)
        
        # Performance optimization
        self.method_performance_scores: Dict[str, float] = {
            'text': 0.8,
            'semantic': 0.7,
            'vector': 0.9,
            'hybrid': 0.85,
            'streaming': 0.75
        }
        
        # Concurrency control
        self._search_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent searches
        self._streaming_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent streaming searches
        
        logger.info("Unified search coordinator initialized")
    
    async def search(self, query: UnifiedSearchQuery) -> List[UnifiedSearchResult]:
        """Execute unified search with intelligent routing.
        
        Args:
            query: Unified search query
            
        Returns:
            List of unified search results
        """
        search_id = f"search_{int(time.time() * 1000)}_{id(query)}"
        start_time = time.time()
        
        try:
            async with self._search_semaphore:
                self.active_searches[search_id] = datetime.now()
                self.stats.current_active_searches = len(self.active_searches)
                self.stats.peak_concurrent_searches = max(
                    self.stats.peak_concurrent_searches, 
                    self.stats.current_active_searches
                )
                
                logger.info(f"Starting unified search: {search_id} - modes: {query.search_modes}")
                
                # Check cache first
                cache_key = self._generate_cache_key(query)
                cached_results = None
                
                if query.enable_caching and not query.use_streaming:
                    cached_results = await self._get_cached_results(cache_key)
                    if cached_results:
                        self.stats.cache_hits += 1
                        logger.debug(f"Cache hit for search: {search_id}")
                        return self._process_cached_results(cached_results)
                
                self.stats.cache_misses += 1
                
                # Route search based on query characteristics
                search_method = self._determine_optimal_search_method(query)
                
                # Execute search
                results = await self._execute_search(query, search_method, search_id)
                
                # Post-process results
                unified_results = await self._unify_search_results(results, query, search_method)
                
                # Cache results if appropriate
                if query.enable_caching and not query.use_streaming and len(unified_results) > 0:
                    await self._cache_results(cache_key, unified_results, query.cache_ttl_seconds)
                
                # Update statistics
                response_time = (time.time() - start_time) * 1000
                self._update_search_statistics(search_method, response_time, len(unified_results))
                
                logger.info(f"Search completed: {search_id} - {len(unified_results)} results in {response_time:.1f}ms")
                return unified_results
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._update_error_statistics(search_method if 'search_method' in locals() else 'unknown', response_time)
            logger.error(f"Search failed: {search_id} - {e}")
            return []
            
        finally:
            self.active_searches.pop(search_id, None)
            self.stats.current_active_searches = len(self.active_searches)
    
    async def search_stream(
        self, 
        query: UnifiedSearchQuery
    ) -> AsyncGenerator[List[UnifiedSearchResult], None]:
        """Execute streaming search for large result sets.
        
        Args:
            query: Unified search query with streaming enabled
            
        Yields:
            Batches of unified search results
        """
        search_id = f"stream_{int(time.time() * 1000)}_{id(query)}"
        start_time = time.time()
        total_results = 0
        
        try:
            async with self._streaming_semaphore:
                self.active_searches[search_id] = datetime.now()
                self.stats.streaming_searches += 1
                
                logger.info(f"Starting streaming search: {search_id} - batch_size: {query.streaming_batch_size}")
                
                # Force streaming mode
                query.use_streaming = True
                
                # Determine optimal streaming method
                streaming_method = self._determine_streaming_method(query)
                
                # Execute streaming search
                async for batch in self._execute_streaming_search(query, streaming_method, search_id):
                    if batch:
                        # Process batch
                        unified_batch = await self._unify_search_results(batch, query, streaming_method)
                        total_results += len(unified_batch)
                        yield unified_batch
                
                # Update statistics
                response_time = (time.time() - start_time) * 1000
                self._update_search_statistics(f"{streaming_method}_streaming", response_time, total_results)
                
                logger.info(f"Streaming search completed: {search_id} - {total_results} total results in {response_time:.1f}ms")
                
        except Exception as e:
            logger.error(f"Streaming search failed: {search_id} - {e}")
            yield []
            
        finally:
            self.active_searches.pop(search_id, None)
            self.stats.current_active_searches = len(self.active_searches)
    
    async def search_with_aggregation(
        self, 
        query: UnifiedSearchQuery,
        aggregation_type: str = 'category'
    ) -> Dict[str, List[UnifiedSearchResult]]:
        """Search with result aggregation by specified criteria.
        
        Args:
            query: Unified search query
            aggregation_type: Type of aggregation (category, time, similarity)
            
        Returns:
            Aggregated search results
        """
        try:
            # Get search results
            results = await self.search(query)
            
            # Aggregate results
            aggregated = self._aggregate_results(results, aggregation_type)
            
            logger.info(f"Search aggregation completed: {len(aggregated)} groups, {aggregation_type} aggregation")
            return aggregated
            
        except Exception as e:
            logger.error(f"Search aggregation failed: {e}")
            return {}
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            limit: Maximum suggestions to return
            
        Returns:
            List of search suggestions
        """
        try:
            suggestions = []
            
            # Get suggestions from search history
            history_suggestions = self._get_history_suggestions(partial_query, limit // 2)
            suggestions.extend(history_suggestions)
            
            # Get semantic suggestions if vector search available
            if self.pg_adapter.capabilities.vector_search_enabled:
                semantic_suggestions = await self._get_semantic_suggestions(partial_query, limit // 2)
                suggestions.extend(semantic_suggestions)
            
            # Deduplicate and rank suggestions
            unique_suggestions = self._rank_suggestions(suggestions, partial_query)
            
            return unique_suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Search suggestions failed: {e}")
            return []
    
    async def analyze_search_performance(self) -> Dict[str, Any]:
        """Analyze search performance and provide optimization recommendations.
        
        Returns:
            Comprehensive performance analysis
        """
        try:
            analysis = {
                'current_stats': self.stats.to_dict(),
                'performance_analysis': {},
                'bottlenecks': [],
                'recommendations': [],
                'method_efficiency': {}
            }
            
            # Analyze method performance
            for method, score in self.method_performance_scores.items():
                usage_count = self.stats.search_method_usage.get(method, 0)
                avg_time = self.stats.performance_by_method.get(method, 0)
                error_rate = self.stats.error_rates.get(method, 0)
                
                efficiency = score * (1 - error_rate) * (1000 / max(avg_time, 1))
                analysis['method_efficiency'][method] = {
                    'efficiency_score': round(efficiency, 2),
                    'usage_count': usage_count,
                    'avg_response_time_ms': round(avg_time, 1),
                    'error_rate_percentage': round(error_rate * 100, 1)
                }
            
            # Identify bottlenecks
            if self.stats.average_response_time_ms > 2000:
                analysis['bottlenecks'].append("High average response time detected")
            
            if self.stats.peak_concurrent_searches > 8:
                analysis['bottlenecks'].append("High concurrency may be causing contention")
            
            cache_hit_rate = self.stats.cache_hits / max(self.stats.cache_hits + self.stats.cache_misses, 1)
            if cache_hit_rate < 0.3:
                analysis['bottlenecks'].append("Low cache hit rate affecting performance")
            
            # Generate recommendations
            recommendations = []
            
            # Cache optimization
            if cache_hit_rate < 0.5:
                recommendations.append({
                    'priority': 'high',
                    'category': 'caching',
                    'description': 'Improve cache hit rate through better cache key strategies',
                    'expected_improvement': '20-40% faster response times'
                })
            
            # Method optimization
            inefficient_methods = [
                method for method, data in analysis['method_efficiency'].items()
                if data['efficiency_score'] < 50 and data['usage_count'] > 10
            ]
            
            if inefficient_methods:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'method_optimization',
                    'description': f'Optimize or reduce usage of inefficient methods: {", ".join(inefficient_methods)}',
                    'expected_improvement': '15-30% performance gain'
                })
            
            # Infrastructure recommendations
            if self.pg_adapter.capabilities.performance_tier == 'sqlite':
                recommendations.append({
                    'priority': 'high',
                    'category': 'infrastructure',
                    'description': 'Migrate to PostgreSQL for significant search performance improvements',
                    'expected_improvement': '200-400% faster search operations'
                })
            
            analysis['recommendations'] = recommendations
            
            return analysis
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {'error': str(e)}
    
    def _determine_optimal_search_method(self, query: UnifiedSearchQuery) -> str:
        """Determine optimal search method based on query characteristics."""
        # If specific methods requested, choose the best available
        if query.search_modes:
            for method in query.search_modes:
                if method == 'vector' and self.pg_adapter.capabilities.vector_search_enabled:
                    return 'vector'
                elif method == 'streaming' and query.max_results > 100:
                    return 'streaming'
                elif method == 'hybrid':
                    return 'hybrid'
                elif method == 'semantic':
                    return 'semantic'
                elif method == 'text':
                    return 'text'
        
        # Intelligent method selection based on query characteristics
        if query.max_results > 100:
            return 'streaming'
        elif len(query.text.split()) > 5 and self.pg_adapter.capabilities.vector_search_enabled:
            return 'vector'
        elif query.semantic_threshold < 0.8:
            return 'hybrid'
        else:
            return 'text'
    
    def _determine_streaming_method(self, query: UnifiedSearchQuery) -> str:
        """Determine optimal streaming method."""
        if self.pg_adapter.capabilities.pgvector_available:
            return 'vector'
        elif self.pg_adapter.capabilities.postgresql_enabled:
            return 'hybrid'
        else:
            return 'text'
    
    async def _execute_search(
        self, 
        query: UnifiedSearchQuery, 
        method: str, 
        search_id: str
    ) -> List[Union[SearchResult, VectorSearchResult]]:
        """Execute search using specified method."""
        try:
            if method == 'vector':
                vector_query = VectorSearchQuery(
                    text=query.text,
                    similarity_threshold=query.vector_similarity_threshold,
                    max_results=query.max_results,
                    date_range=query.time_range,
                    categories=query.categories
                )
                return await self.vector_search.search(vector_query)
                
            elif method == 'streaming':
                return await self._execute_streaming_search_batch(query, 'text', search_id)
                
            else:  # text, semantic, hybrid
                search_query = SearchQuery(
                    query=query.text,
                    search_type=method,
                    time_range=query.time_range,
                    entity_types=query.entity_types,
                    categories=query.categories,
                    limit=query.max_results,
                    semantic_threshold=query.semantic_threshold
                )
                return await self.advanced_search.search(search_query)
                
        except Exception as e:
            logger.error(f"Search execution failed: {method} - {e}")
            return []
    
    async def _execute_streaming_search(
        self, 
        query: UnifiedSearchQuery, 
        method: str, 
        search_id: str
    ) -> AsyncGenerator[List[Union[SearchResult, VectorSearchResult]], None]:
        """Execute streaming search."""
        try:
            if method == 'vector':
                # Use vector search streaming if available
                vector_query = VectorSearchQuery(
                    text=query.text,
                    similarity_threshold=query.vector_similarity_threshold,
                    max_results=query.max_results,
                    date_range=query.time_range,
                    categories=query.categories
                )
                
                # Simulate streaming by batching results
                all_results = await self.vector_search.search(vector_query)
                for i in range(0, len(all_results), query.streaming_batch_size):
                    batch = all_results[i:i + query.streaming_batch_size]
                    yield batch
                    await asyncio.sleep(0.01)  # Small delay for responsiveness
                    
            else:
                # Use advanced search streaming
                search_query = SearchQuery(
                    query=query.text,
                    search_type=method,
                    time_range=query.time_range,
                    entity_types=query.entity_types,
                    categories=query.categories,
                    limit=query.max_results,
                    semantic_threshold=query.semantic_threshold
                )
                
                # Use streaming capability from advanced search
                async for batch in self.advanced_search.search_stream(search_query, query.streaming_batch_size):
                    yield batch
                    
        except Exception as e:
            logger.error(f"Streaming search execution failed: {method} - {e}")
            yield []
    
    async def _execute_streaming_search_batch(
        self, 
        query: UnifiedSearchQuery, 
        method: str, 
        search_id: str
    ) -> List[Union[SearchResult, VectorSearchResult]]:
        """Execute streaming search and return first batch."""
        async for batch in self._execute_streaming_search(query, method, search_id):
            return batch
        return []
    
    async def _unify_search_results(
        self, 
        results: List[Union[SearchResult, VectorSearchResult]], 
        query: UnifiedSearchQuery,
        method: str
    ) -> List[UnifiedSearchResult]:
        """Convert search engine results to unified format."""
        unified_results = []
        
        for result in results:
            try:
                # Extract common fields
                unified_result = UnifiedSearchResult(
                    entity_id=result.entity_id,
                    relevance_score=result.relevance_score,
                    search_method=method,
                    window_title=result.window_title,
                    timestamp=result.timestamp,
                    highlights=result.highlights if query.include_highlights else [],
                    extracted_tasks=result.extracted_tasks,
                    activity_category=result.activity_category
                )
                
                # Add vector-specific fields if available
                if isinstance(result, VectorSearchResult):
                    unified_result.vector_similarity_score = result.vector_similarity_score
                    unified_result.semantic_cluster = result.semantic_cluster
                    unified_result.similar_activities = result.similar_activities or []
                
                # Add confidence metrics
                unified_result.confidence_metrics = {
                    'relevance': result.relevance_score,
                    'method_confidence': self.method_performance_scores.get(method, 0.5)
                }
                
                # Add metadata if requested
                if query.include_metadata:
                    unified_result.source_info = {
                        'search_method': method,
                        'query_text': query.text,
                        'timestamp': datetime.now().isoformat()
                    }
                
                unified_results.append(unified_result)
                
            except Exception as e:
                logger.warning(f"Failed to unify search result: {e}")
                continue
        
        return unified_results
    
    def _generate_cache_key(self, query: UnifiedSearchQuery) -> str:
        """Generate cache key for search query."""
        key_data = {
            'text': query.text,
            'modes': sorted(query.search_modes),
            'max_results': query.max_results,
            'categories': sorted(query.categories) if query.categories else None,
            'time_range': [t.isoformat() for t in query.time_range] if query.time_range else None,
            'semantic_threshold': query.semantic_threshold,
            'vector_threshold': query.vector_similarity_threshold
        }
        
        import hashlib
        key_string = json.dumps(key_data, sort_keys=True)
        return f"search_{hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()}"
    
    async def _get_cached_results(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        try:
            if self.cache_manager:
                return await self.cache_manager.get(cache_key)
        except Exception as e:
            logger.debug(f"Cache get failed: {e}")
        return None
    
    async def _cache_results(self, cache_key: str, results: List[UnifiedSearchResult], ttl: int):
        """Cache search results."""
        try:
            if self.cache_manager:
                # Convert to dict for caching
                cache_data = [asdict(result) for result in results]
                await self.cache_manager.set(cache_key, cache_data, ttl)
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")
    
    def _process_cached_results(self, cached_data: List[Dict[str, Any]]) -> List[UnifiedSearchResult]:
        """Process cached results back to unified format."""
        results = []
        for data in cached_data:
            try:
                # Convert datetime strings back to datetime objects
                if 'timestamp' in data and isinstance(data['timestamp'], str):
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                
                result = UnifiedSearchResult(**data)
                result.cache_hit = True
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to process cached result: {e}")
                continue
        
        return results
    
    def _aggregate_results(
        self, 
        results: List[UnifiedSearchResult], 
        aggregation_type: str
    ) -> Dict[str, List[UnifiedSearchResult]]:
        """Aggregate search results by specified criteria."""
        aggregated = defaultdict(list)
        
        for result in results:
            if aggregation_type == 'category':
                key = result.activity_category
            elif aggregation_type == 'time':
                # Group by hour
                key = result.timestamp.strftime('%Y-%m-%d %H:00')
            elif aggregation_type == 'similarity':
                # Group by similarity score ranges
                score = result.relevance_score
                if score >= 0.8:
                    key = 'high_relevance'
                elif score >= 0.6:
                    key = 'medium_relevance'
                else:
                    key = 'low_relevance'
            elif aggregation_type == 'method':
                key = result.search_method
            else:
                key = 'all'
            
            aggregated[key].append(result)
        
        return dict(aggregated)
    
    def _get_history_suggestions(self, partial_query: str, limit: int) -> List[Dict[str, Any]]:
        """Get suggestions from search history."""
        suggestions = []
        
        # Extract recent queries from history
        recent_queries = set()
        for record in list(self.search_history)[-100:]:  # Last 100 searches
            if 'query' in record:
                recent_queries.add(record['query'])
        
        # Find matching queries
        partial_lower = partial_query.lower()
        for query in recent_queries:
            if partial_lower in query.lower() and query != partial_query:
                suggestions.append({
                    'text': query,
                    'type': 'history',
                    'score': 0.5
                })
                
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    async def _get_semantic_suggestions(self, partial_query: str, limit: int) -> List[Dict[str, Any]]:
        """Get semantic suggestions using vector search."""
        try:
            # Use vector search to find similar content
            vector_query = VectorSearchQuery(
                text=partial_query,
                max_results=limit,
                similarity_threshold=0.5
            )
            
            results = await self.vector_search.search(vector_query)
            
            suggestions = []
            for result in results:
                # Extract meaningful terms from window titles and tasks
                terms = []
                if result.window_title:
                    terms.extend(result.window_title.split())
                terms.extend(result.extracted_tasks)
                
                # Filter and rank terms
                meaningful_terms = [
                    term for term in terms 
                    if len(term) > 3 and term.isalpha() and term.lower() not in partial_query.lower()
                ]
                
                for term in meaningful_terms[:2]:  # Max 2 terms per result
                    suggestions.append({
                        'text': f"{partial_query} {term}",
                        'type': 'semantic',
                        'score': result.relevance_score * 0.7
                    })
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.debug(f"Semantic suggestions failed: {e}")
            return []
    
    def _rank_suggestions(
        self, 
        suggestions: List[Dict[str, Any]], 
        partial_query: str
    ) -> List[Dict[str, Any]]:
        """Rank and deduplicate suggestions."""
        # Remove duplicates
        seen = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            text = suggestion['text']
            if text not in seen:
                seen.add(text)
                unique_suggestions.append(suggestion)
        
        # Sort by score
        unique_suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return unique_suggestions
    
    def _update_search_statistics(self, method: str, response_time_ms: float, result_count: int):
        """Update search performance statistics."""
        self.stats.total_searches += 1
        self.stats.search_method_usage[method] += 1
        
        # Update average response time
        total_time = self.stats.average_response_time_ms * (self.stats.total_searches - 1) + response_time_ms
        self.stats.average_response_time_ms = total_time / self.stats.total_searches
        
        # Update method-specific performance
        method_searches = self.stats.search_method_usage[method]
        existing_avg = self.stats.performance_by_method[method]
        new_avg = (existing_avg * (method_searches - 1) + response_time_ms) / method_searches
        self.stats.performance_by_method[method] = new_avg
        
        # Record search in history
        self.search_history.append({
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'response_time_ms': response_time_ms,
            'result_count': result_count
        })
    
    def _update_error_statistics(self, method: str, response_time_ms: float):
        """Update error statistics."""
        total_searches = self.stats.search_method_usage[method] + 1
        current_errors = self.stats.error_rates.get(method, 0) * (total_searches - 1)
        self.stats.error_rates[method] = (current_errors + 1) / total_searches


# Singleton instance
_search_coordinator: Optional[UnifiedSearchCoordinator] = None


def get_search_coordinator() -> UnifiedSearchCoordinator:
    """Get singleton search coordinator instance."""
    global _search_coordinator
    if _search_coordinator is None:
        _search_coordinator = UnifiedSearchCoordinator()
    return _search_coordinator


def reset_search_coordinator():
    """Reset search coordinator for testing."""
    global _search_coordinator
    _search_coordinator = None


async def unified_search(query: str, **kwargs) -> List[UnifiedSearchResult]:
    """Convenience function for unified search."""
    coordinator = get_search_coordinator()
    search_query = UnifiedSearchQuery(text=query, **kwargs)
    return await coordinator.search(search_query)


async def streaming_search(query: str, batch_size: int = 20, **kwargs) -> AsyncGenerator[List[UnifiedSearchResult], None]:
    """Convenience function for streaming search."""
    coordinator = get_search_coordinator()
    search_query = UnifiedSearchQuery(
        text=query, 
        use_streaming=True, 
        streaming_batch_size=batch_size,
        **kwargs
    )
    async for batch in coordinator.search_stream(search_query):
        yield batch