"""Advanced search integration with Pensieve's semantic capabilities."""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.health_monitor import is_pensieve_healthy

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result with relevance scoring."""
    entity_id: int
    filepath: str
    timestamp: datetime
    window_title: str
    ocr_text: Optional[str]
    extracted_tasks: List[str]
    activity_category: Optional[str]
    relevance_score: float
    search_method: str
    highlights: List[str] = None


@dataclass
class SearchQuery:
    """Represents a search query with multiple options."""
    text: str
    use_semantic: bool = True
    use_keyword: bool = True
    date_range: Optional[Tuple[datetime, datetime]] = None
    category_filter: Optional[str] = None
    min_relevance: float = 0.1
    max_results: int = 50


class PensieveAdvancedSearch:
    """Advanced search using Pensieve's semantic and traditional capabilities."""
    
    def __init__(self):
        """Initialize advanced search."""
        self.pensieve_client = get_pensieve_client()
        self._embedding_cache = {}
        self._search_stats = {
            'semantic_searches': 0,
            'keyword_searches': 0,
            'hybrid_searches': 0,
            'cache_hits': 0,
            'total_time': 0.0
        }
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform advanced search using multiple methods.
        
        Args:
            query: Search query with options
            
        Returns:
            List of search results ranked by relevance
        """
        start_time = time.time()
        
        try:
            # Check if Pensieve is available
            if not is_pensieve_healthy():
                logger.warning("Pensieve unavailable, using fallback search")
                return self._fallback_search(query)
            
            results = []
            
            # Method 1: Semantic search via Pensieve API
            if query.use_semantic:
                semantic_results = self._semantic_search(query)
                results.extend(semantic_results)
                self._search_stats['semantic_searches'] += 1
            
            # Method 2: Keyword search via Pensieve API
            if query.use_keyword:
                keyword_results = self._keyword_search(query)
                results.extend(keyword_results)
                self._search_stats['keyword_searches'] += 1
            
            # Method 3: Hybrid search (combine results)
            if query.use_semantic and query.use_keyword:
                results = self._merge_search_results(results)
                self._search_stats['hybrid_searches'] += 1
            
            # Post-process results
            results = self._post_process_results(results, query)
            
            # Update statistics
            search_time = time.time() - start_time
            self._search_stats['total_time'] += search_time
            
            logger.debug(f"Search completed in {search_time:.3f}s, {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return self._fallback_search(query)
    
    def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search using Pensieve's vector capabilities."""
        results = []
        
        try:
            # Use Pensieve's search API with semantic mode
            api_results = self.pensieve_client.search_frames(
                query=f"semantic:{query.text}",
                limit=query.max_results
            )
            
            for frame in api_results:
                # Get additional metadata
                metadata = self.pensieve_client.get_metadata(frame.id)
                ocr_text = self.pensieve_client.get_ocr_result(frame.id)
                
                # Extract relevant data
                window_title = metadata.get("active_window", '')
                extracted_tasks = metadata.get('extracted_tasks', {}).get("tasks", [])
                activity_category = metadata.get('activity_category', '')
                
                # Calculate relevance score (semantic similarity)
                relevance_score = self._calculate_semantic_relevance(
                    query.text, window_title, ocr_text, extracted_tasks
                )
                
                if relevance_score >= query.min_relevance:
                    result = SearchResult(
                        entity_id=frame.id,
                        filepath=frame.filepath,
                        timestamp=datetime.fromisoformat(frame.timestamp),
                        window_title=window_title,
                        ocr_text=ocr_text,
                        extracted_tasks=extracted_tasks,
                        activity_category=activity_category,
                        relevance_score=relevance_score,
                        search_method='semantic',
                        highlights=self._extract_highlights(query.text, window_title, ocr_text)
                    )
                    results.append(result)
        
        except PensieveAPIError as e:
            if "not found" not in e.message.lower():
                logger.error(f"Semantic search API error: {e.message}")
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
        
        return results
    
    def _keyword_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform keyword search using Pensieve's text search."""
        results = []
        
        try:
            # Use Pensieve's search API with keyword mode
            api_results = self.pensieve_client.search_frames(
                query=f"keyword:{query.text}",
                limit=query.max_results
            )
            
            # If keyword mode not supported, use default search
            if not api_results:
                api_results = self.pensieve_client.search_frames(
                    query=query.text,
                    limit=query.max_results
                )
            
            for frame in api_results:
                # Get additional metadata
                metadata = self.pensieve_client.get_metadata(frame.id)
                ocr_text = self.pensieve_client.get_ocr_result(frame.id)
                
                # Extract relevant data
                window_title = metadata.get("active_window", '')
                extracted_tasks = metadata.get('extracted_tasks', {}).get("tasks", [])
                activity_category = metadata.get('activity_category', '')
                
                # Calculate keyword relevance score
                relevance_score = self._calculate_keyword_relevance(
                    query.text, window_title, ocr_text, extracted_tasks
                )
                
                if relevance_score >= query.min_relevance:
                    result = SearchResult(
                        entity_id=frame.id,
                        filepath=frame.filepath,
                        timestamp=datetime.fromisoformat(frame.timestamp),
                        window_title=window_title,
                        ocr_text=ocr_text,
                        extracted_tasks=extracted_tasks,
                        activity_category=activity_category,
                        relevance_score=relevance_score,
                        search_method='keyword',
                        highlights=self._extract_highlights(query.text, window_title, ocr_text)
                    )
                    results.append(result)
        
        except PensieveAPIError as e:
            logger.error(f"Keyword search API error: {e.message}")
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
        
        return results
    
    def _fallback_search(self, query: SearchQuery) -> List[SearchResult]:
        """Fallback search when Pensieve API unavailable."""
        # This would use direct database access as fallback
        logger.info("Using fallback search (direct database)")
        
        try:
            from autotasktracker.core import DatabaseManager
            
            db = DatabaseManager(use_pensieve_api=False)
            with db.get_connection(readonly=True) as conn:
                cursor = conn.cursor()
                
                # Simple text search in database
                sql_query = """
                    SELECT DISTINCT e.id, e.filepath, e.created_at,
                           m1.value as window_title,
                           m2.value as extracted_tasks,
                           m3.value as activity_category
                    FROM entities e
                    LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = "active_window"
                    LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'extracted_tasks'
                    LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'activity_category'
                    WHERE (m1.value LIKE ? OR m2.value LIKE ?)
                    ORDER BY e.created_at DESC
                    LIMIT ?
                """
                
                search_term = f"%{query.text}%"
                cursor.execute(sql_query, (search_term, search_term, query.max_results))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    entity_id, filepath, created_at, window_title, extracted_tasks_json, activity_category = row
                    
                    # Parse extracted tasks
                    extracted_tasks = []
                    if extracted_tasks_json:
                        try:
                            import json
                            tasks_data = json.loads(extracted_tasks_json)
                            if isinstance(tasks_data, dict) and "tasks" in tasks_data:
                                extracted_tasks = tasks_data["tasks"]
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.debug(f"Failed to parse extracted tasks JSON: {e}")
                    
                    # Calculate simple relevance
                    relevance_score = self._calculate_keyword_relevance(
                        query.text, window_title or '', '', extracted_tasks
                    )
                    
                    if relevance_score >= query.min_relevance:
                        result = SearchResult(
                            entity_id=entity_id,
                            filepath=filepath or '',
                            timestamp=datetime.fromisoformat(created_at),
                            window_title=window_title or '',
                            ocr_text=None,  # Not available in fallback
                            extracted_tasks=extracted_tasks,
                            activity_category=activity_category,
                            relevance_score=relevance_score,
                            search_method='fallback_keyword',
                            highlights=self._extract_highlights(query.text, window_title or '', '')
                        )
                        results.append(result)
                
                return results
        
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    def _calculate_semantic_relevance(self, query: str, window_title: str, 
                                    ocr_text: Optional[str], tasks: List[str]) -> float:
        """Calculate semantic relevance score using embeddings."""
        # This would use actual semantic similarity if available
        # For now, use enhanced keyword matching as approximation
        
        query_lower = query.lower()
        combined_text = f"{window_title} {ocr_text or ''} {' '.join(tasks)}".lower()
        
        # Basic semantic approximation
        query_words = set(query_lower.split())
        text_words = set(combined_text.split())
        
        if not query_words:
            return 0.0
        
        # Jaccard similarity as semantic approximation
        intersection = len(query_words & text_words)
        union = len(query_words | text_words)
        
        base_score = intersection / union if union > 0 else 0.0
        
        # Boost for exact phrase matches
        if query_lower in combined_text:
            base_score += 0.3
        
        # Boost for task matches (higher semantic value)
        for task in tasks:
            if any(word in task.lower() for word in query_words):
                base_score += 0.2
        
        return min(base_score, 1.0)
    
    def _calculate_keyword_relevance(self, query: str, window_title: str,
                                   ocr_text: Optional[str], tasks: List[str]) -> float:
        """Calculate keyword-based relevance score."""
        query_lower = query.lower()
        
        # Combine all searchable text
        combined_text = f"{window_title} {ocr_text or ''} {' '.join(tasks)}".lower()
        
        if not query_lower or not combined_text:
            return 0.0
        
        score = 0.0
        
        # Exact match in window title (highest relevance)
        if query_lower in window_title.lower():
            score += 0.5
        
        # Exact match in tasks (high relevance)
        for task in tasks:
            if query_lower in task.lower():
                score += 0.3
                break
        
        # Exact match in OCR text (medium relevance)
        if ocr_text and query_lower in ocr_text.lower():
            score += 0.2
        
        # Word matches
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 2:  # Skip very short words
                if word in combined_text:
                    score += 0.1
        
        return min(score, 1.0)
    
    def _extract_highlights(self, query: str, window_title: str, 
                          ocr_text: Optional[str]) -> List[str]:
        """Extract highlighted text snippets around query matches."""
        highlights = []
        query_lower = query.lower()
        
        # Check window title
        if query_lower in window_title.lower():
            highlights.append(f"Title: ...{window_title}...")
        
        # Check OCR text
        if ocr_text and query_lower in ocr_text.lower():
            # Find the match and extract context
            text_lower = ocr_text.lower()
            match_index = text_lower.find(query_lower)
            if match_index != -1:
                start = max(0, match_index - 30)
                end = min(len(ocr_text), match_index + len(query) + 30)
                snippet = ocr_text[start:end]
                highlights.append(f"OCR: ...{snippet}...")
        
        return highlights[:3]  # Limit to 3 highlights
    
    def _merge_search_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Merge and deduplicate search results from multiple methods."""
        # Group by entity_id
        entity_results = {}
        
        for result in results:
            entity_id = result.entity_id
            
            if entity_id not in entity_results:
                entity_results[entity_id] = result
            else:
                # Merge results for same entity
                existing = entity_results[entity_id]
                
                # Use highest relevance score
                if result.relevance_score > existing.relevance_score:
                    existing.relevance_score = result.relevance_score
                
                # Combine search methods
                methods = existing.search_method.split('+')
                if result.search_method not in methods:
                    existing.search_method = '+'.join(methods + [result.search_method])
                
                # Merge highlights
                if result.highlights:
                    existing.highlights = (existing.highlights or []) + result.highlights
                    existing.highlights = list(set(existing.highlights))[:5]  # Dedupe and limit
        
        return list(entity_results.values())
    
    def _post_process_results(self, results: List[SearchResult], 
                            query: SearchQuery) -> List[SearchResult]:
        """Post-process search results."""
        # Apply filters
        filtered_results = []
        
        for result in results:
            # Date range filter
            if query.date_range:
                start_date, end_date = query.date_range
                if not (start_date <= result.timestamp <= end_date):
                    continue
            
            # Category filter
            if query.category_filter and result.activity_category != query.category_filter:
                continue
            
            # Relevance filter
            if result.relevance_score < query.min_relevance:
                continue
            
            filtered_results.append(result)
        
        # Sort by relevance score (descending)
        filtered_results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        # Limit results
        return filtered_results[:query.max_results]
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search statistics."""
        total_searches = (
            self._search_stats['semantic_searches'] + 
            self._search_stats['keyword_searches']
        )
        
        return {
            'total_searches': total_searches,
            'semantic_searches': self._search_stats['semantic_searches'],
            'keyword_searches': self._search_stats['keyword_searches'],
            'hybrid_searches': self._search_stats['hybrid_searches'],
            'cache_hits': self._search_stats['cache_hits'],
            'total_time': self._search_stats['total_time'],
            'avg_time_per_search': (
                self._search_stats['total_time'] / total_searches 
                if total_searches > 0 else 0.0
            )
        }
    
    def clear_cache(self):
        """Clear embedding cache."""
        self._embedding_cache.clear()
        logger.info("Search cache cleared")


# Global search instance
_global_search: Optional[PensieveAdvancedSearch] = None


def get_advanced_search() -> PensieveAdvancedSearch:
    """Get global advanced search instance."""
    global _global_search
    if _global_search is None:
        _global_search = PensieveAdvancedSearch()
    return _global_search


def search_with_pensieve(query_text: str, **kwargs) -> List[SearchResult]:
    """Convenience function for searching with Pensieve."""
    search_query = SearchQuery(text=query_text, **kwargs)
    search_engine = get_advanced_search()
    return search_engine.search(search_query)