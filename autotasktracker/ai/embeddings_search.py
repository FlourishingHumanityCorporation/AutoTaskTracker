"""
Embeddings-based semantic search for AutoTaskTracker.
Leverages Pensieve's embedding generation to enable semantic task search and grouping.
"""
import json
import logging
import sqlite3
from typing import List, Dict, Tuple, Optional, Union
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from autotasktracker.core.database import DatabaseManager

logger = logging.getLogger(__name__)


class EmbeddingsSearchEngine:
    """Semantic search engine using embeddings from Pensieve."""
    
    def __init__(self, db_manager_or_path: Union[str, DatabaseManager]):
        # Accept either DatabaseManager instance or path for backward compatibility
        if isinstance(db_manager_or_path, str):
            self.db_manager = DatabaseManager(db_manager_or_path)
        elif isinstance(db_manager_or_path, DatabaseManager):
            self.db_manager = db_manager_or_path
        else:
            # Default to standard database location
            self.db_manager = DatabaseManager()
        self.embedding_dim = 768  # Jina embeddings dimension
    
    def _get_connection(self):
        """Get database connection context manager from DatabaseManager."""
        return self.db_manager.get_connection(readonly=True)
    
    def _parse_embedding(self, embedding_str: str) -> Optional[np.ndarray]:
        """Parse embedding string to numpy array."""
        if not embedding_str:
            return None
        
        try:
            # Embeddings might be stored as JSON array or space-separated values
            if embedding_str.startswith('['):
                embedding = np.array(json.loads(embedding_str))
            else:
                embedding = np.array([round(float(x), 8) for x in embedding_str.split()])
            
            if len(embedding) != self.embedding_dim:
                logger.warning(f"Unexpected embedding dimension: {len(embedding)}")
                return None
                
            return embedding
        except Exception as e:
            logger.error(f"Error parsing embedding: {e}")
            return None
    
    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity with precision control
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return round(float(similarity), 8)
    
    def get_embedding_for_entity(self, entity_id: int) -> Optional[np.ndarray]:
        """Get embedding for a specific entity."""
        query = """
        SELECT value 
        FROM metadata_entries 
        WHERE entity_id = ? AND "key" = 'embedding'
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (entity_id,))
                result = cursor.fetchone()
                
                if result:
                    return self._parse_embedding(result['value'])
                return None
        except sqlite3.Error as e:
            logger.error(f"Error fetching embedding: {e}")
            return None
    
    def semantic_search(self, query_entity_id: int, limit: int = 10, 
                       similarity_threshold: float = 0.7,
                       time_window_hours: Optional[int] = None) -> List[Dict]:
        """
        Find semantically similar activities to a given entity.
        
        Args:
            query_entity_id: The entity ID to search similar items for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            time_window_hours: Optional time window to search within
            
        Returns:
            List of similar activities with similarity scores
        """
        # Get query embedding
        query_embedding = self.get_embedding_for_entity(query_entity_id)
        if query_embedding is None:
            logger.warning(f"No embedding found for entity {query_entity_id}")
            return []
        
        # Build query with optional time filter
        base_query = """
        SELECT 
            e.id,
            e.filepath,
            e.filename,
            datetime(e.created_at, 'localtime') as created_at,
            me_ocr.value as ocr_text,
            me_window.value as active_window,
            me_embed.value as embedding
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id 
            AND me_ocr."key" = 'ocr_result'
        LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id 
            AND me_window."key" = 'active_window'
        LEFT JOIN metadata_entries me_embed ON e.id = me_embed.entity_id 
            AND me_embed."key" = 'embedding'
        WHERE e.file_type_group = 'image' 
            AND me_embed.value IS NOT NULL
            AND e.id != ?
        """
        
        params = [query_entity_id]
        
        if time_window_hours:
            cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).isoformat()
            base_query += " AND datetime(e.created_at, 'localtime') >= ?"
            params.append(cutoff_time)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(base_query, params)
                
                results = []
                for row in cursor.fetchall():
                    # Parse candidate embedding
                    candidate_embedding = self._parse_embedding(row['embedding'])
                    if candidate_embedding is None:
                        continue
                    
                    # Calculate similarity
                    similarity = self.cosine_similarity(query_embedding, candidate_embedding)
                    
                    if similarity >= similarity_threshold:
                        results.append({
                            'id': row['id'],
                            'filepath': row['filepath'],
                            'created_at': row['created_at'],
                            "ocr_result": row["ocr_result"],
                            'active_window': row['active_window'],
                            'similarity_score': round(float(similarity), 6)
                        })
                
                # Sort by similarity score
                results.sort(key=lambda x: x['similarity_score'], reverse=True)
                
                return results[:limit]
                
        except sqlite3.Error as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def find_similar_task_groups(self, min_group_size: int = 3,
                               similarity_threshold: float = 0.8,
                               time_window_hours: int = 24) -> List[List[Dict]]:
        """
        Find groups of similar tasks based on embeddings.
        
        Args:
            min_group_size: Minimum number of tasks to form a group
            similarity_threshold: Minimum similarity for grouping
            time_window_hours: Time window to search within
            
        Returns:
            List of task groups, each group is a list of similar tasks
        """
        # Get all entities with embeddings in time window
        cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).isoformat()
        
        query = """
        SELECT 
            e.id,
            e.filepath,
            datetime(e.created_at, 'localtime') as created_at,
            me_ocr.value as ocr_text,
            me_window.value as active_window,
            me_embed.value as embedding
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id 
            AND me_ocr."key" = 'ocr_result'
        LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id 
            AND me_window."key" = 'active_window'
        LEFT JOIN metadata_entries me_embed ON e.id = me_embed.entity_id 
            AND me_embed."key" = 'embedding'
        WHERE e.file_type_group = 'image' 
            AND me_embed.value IS NOT NULL
            AND datetime(e.created_at, 'localtime') >= ?
        ORDER BY e.created_at DESC
        """
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[cutoff_time])
                
                if df.empty:
                    return []
                
                # Parse all embeddings
                embeddings = []
                valid_indices = []
                
                for idx, row in df.iterrows():
                    embedding = self._parse_embedding(row['embedding'])
                    if embedding is not None:
                        embeddings.append(embedding)
                        valid_indices.append(idx)
                
                if not embeddings:
                    return []
                
                # Calculate similarity matrix
                embeddings_array = np.array(embeddings)
                valid_df = df.iloc[valid_indices].reset_index(drop=True)
                
                # Normalize embeddings for cosine similarity
                norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
                normalized_embeddings = embeddings_array / norms
                
                # Calculate similarity matrix
                similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
                
                # Group similar tasks
                groups = []
                used_indices = set()
                
                for i in range(len(valid_df)):
                    if i in used_indices:
                        continue
                    
                    # Find all items similar to this one
                    similar_indices = np.where(similarity_matrix[i] >= similarity_threshold)[0]
                    
                    # Remove already used indices
                    similar_indices = [idx for idx in similar_indices if idx not in used_indices]
                    
                    if len(similar_indices) >= min_group_size:
                        group = []
                        for idx in similar_indices:
                            group.append({
                                'id': valid_df.iloc[idx]['id'],
                                'filepath': valid_df.iloc[idx]['filepath'],
                                'created_at': valid_df.iloc[idx]['created_at'],
                                "ocr_result": valid_df.iloc[idx]["ocr_result"],
                                'active_window': valid_df.iloc[idx]['active_window'],
                                'similarity_to_first': round(float(similarity_matrix[i][idx]), 6)
                            })
                            used_indices.add(idx)
                        
                        groups.append(group)
                
                return groups
                
        except Exception as e:
            logger.error(f"Error finding similar task groups: {e}")
            return []
    
    def get_task_context(self, entity_id: int, context_size: int = 5) -> List[Dict]:
        """
        Get contextually similar tasks around a given task.
        Useful for understanding what the user was working on.
        
        Args:
            entity_id: The entity to get context for
            context_size: Number of similar items to retrieve
            
        Returns:
            List of contextually similar tasks
        """
        return self.semantic_search(
            entity_id, 
            limit=context_size,
            similarity_threshold=0.6,
            time_window_hours=4  # Look within 4 hour window for context
        )


class EmbeddingStats:
    """Statistics and analytics for embeddings."""
    
    def __init__(self, db_manager_or_path: Union[str, DatabaseManager]):
        if isinstance(db_manager_or_path, str):
            self.db_manager = DatabaseManager(db_manager_or_path)
        elif isinstance(db_manager_or_path, DatabaseManager):
            self.db_manager = db_manager_or_path
        else:
            self.db_manager = DatabaseManager()
    
    def get_embedding_coverage(self) -> Dict[str, any]:
        """Get statistics about embedding coverage in the database."""
        query = """
        SELECT 
            COUNT(DISTINCT e.id) as total_entities,
            COUNT(DISTINCT me.entity_id) as entities_with_embeddings,
            MIN(datetime(e.created_at, 'localtime')) as earliest_entity,
            MAX(datetime(e.created_at, 'localtime')) as latest_entity
        FROM entities e
        LEFT JOIN metadata_entries me ON e.id = me.entity_id 
            AND me."key" = 'embedding'
        WHERE e.file_type_group = 'image'
        """
        
        try:
            with self.db_manager.get_connection(readonly=True) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                
                if result:
                    total = result['total_entities']
                    with_embeddings = result['entities_with_embeddings'] or 0
                    
                    return {
                        'total_screenshots': total,
                        'screenshots_with_embeddings': with_embeddings,
                        'coverage_percentage': (with_embeddings / total * 100) if total > 0 else 0,
                        'earliest_screenshot': result['earliest_entity'],
                        'latest_screenshot': result['latest_entity']
                    }
                return {}
                
        except sqlite3.Error as e:
            logger.error(f"Error getting embedding stats: {e}")
            return {}