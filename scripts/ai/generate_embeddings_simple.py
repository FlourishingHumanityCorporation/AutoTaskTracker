#!/usr/bin/env python3
"""
Generate embeddings for semantic search functionality.
Simple version that works with the current database structure.
"""
import sys
import os
import logging
import json
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.core.database import DatabaseManager

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for task descriptions."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.db_path = os.path.expanduser("~/.memos/database.db")
        
        if EMBEDDINGS_AVAILABLE:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
        else:
            self.model = None
            self.embedding_dim = 0
    
    def get_unembedded_tasks(self, limit: int = 1000) -> List[Dict]:
        """Get tasks that don't have embeddings yet."""
        db = DatabaseManager(self.db_path)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    e.id,
                    m_task.value as task,
                    m_window.value as window_title,
                    m_cat.value as category
                FROM entities e
                JOIN metadata_entries m_task ON e.id = m_task.entity_id AND m_task.key = 'tasks'
                LEFT JOIN metadata_entries m_window ON e.id = m_window.entity_id AND m_window.key = 'active_window'
                LEFT JOIN metadata_entries m_cat ON e.id = m_cat.entity_id AND m_cat.key = 'category'
                LEFT JOIN metadata_entries m_emb ON e.id = m_emb.entity_id AND m_emb.key = 'task_embedding'
                WHERE m_emb.id IS NULL
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (limit,))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    "tasks": row[1],
                    "active_window": row[2],
                    'category': row[3]
                })
            
            return tasks
    
    def generate_embeddings(self, tasks: List[Dict]) -> Dict[int, List[float]]:
        """Generate embeddings for a list of tasks."""
        if not self.model:
            logger.error("Embedding model not available")
            return {}
        
        # Create text representations for embedding
        texts = []
        task_ids = []
        
        for task in tasks:
            # Combine task and category for richer embedding
            text = f"{task["tasks"]} ({task['category']})"
            texts.append(text)
            task_ids.append(task['id'])
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} tasks...")
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Create mapping
        embedding_map = {}
        for task_id, embedding in zip(task_ids, embeddings):
            embedding_map[task_id] = embedding.tolist()
        
        return embedding_map
    
    def save_embeddings(self, embeddings: Dict[int, List[float]]) -> int:
        """Save embeddings to database."""
        db = DatabaseManager(self.db_path)
        
        saved = 0
        with db.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            for entity_id, embedding in embeddings.items():
                try:
                    cursor.execute("""
                        INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, data_type, created_at, updated_at)
                        VALUES (?, 'task_embedding', ?, 'embedding_generator', 'json', datetime('now'), datetime('now'))
                    """, (entity_id, json.dumps(embedding)))
                    saved += 1
                except Exception as e:
                    # Already exists or other error
                    logger.debug(f"Error saving embedding for entity {entity_id}: {e}")
            
            conn.commit()
            logger.info(f"Saved {saved} embeddings")
        
        return saved
    
    def process_batch(self, batch_size: int = 100) -> int:
        """Process a batch of tasks."""
        tasks = self.get_unembedded_tasks(batch_size)
        
        if not tasks:
            logger.info("No tasks need embeddings")
            return 0
        
        logger.info(f"Found {len(tasks)} tasks without embeddings")
        
        # Generate embeddings
        embeddings = self.generate_embeddings(tasks)
        
        # Save to database
        saved = self.save_embeddings(embeddings)
        
        return saved
    
    def find_similar_tasks(self, query: str, limit: int = 10):
        """Find tasks similar to a query."""
        if not self.model:
            logger.error("Embedding model not available")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]
        
        # Get all embeddings from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    e.id,
                    m_task.value as task,
                    m_emb.value as embedding
                FROM entities e
                JOIN metadata_entries m_task ON e.id = m_task.entity_id AND m_task.key = 'tasks'
                JOIN metadata_entries m_emb ON e.id = m_emb.entity_id AND m_emb.key = 'task_embedding'
                ORDER BY e.created_at DESC
                LIMIT 1000
            """)
            
            # Calculate similarities
            similarities = []
            for entity_id, task, embedding_json in cursor.fetchall():
                embedding = json.loads(embedding_json)
                
                # Cosine similarity
                import numpy as np
                similarity = np.dot(query_embedding, embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                )
                
                similarities.append((entity_id, task, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[2], reverse=True)
            
            # Return top results
            results = []
            for entity_id, task, similarity in similarities[:limit]:
                results.append({
                    'id': entity_id,
                    "tasks": task,
                    'similarity': float(similarity)
                })
            
            return results
            
        finally:
            conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate embeddings for tasks')
    parser.add_argument('--batch', type=int, default=100,
                        help='Batch size for processing (default: 100)')
    parser.add_argument('--all', action='store_true',
                        help='Process all unembedded tasks')
    parser.add_argument('--search', type=str,
                        help='Search for similar tasks')
    
    args = parser.parse_args()
    
    if not EMBEDDINGS_AVAILABLE:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        return
    
    generator = EmbeddingGenerator()
    
    if args.search:
        # Search for similar tasks
        results = generator.find_similar_tasks(args.search)
        
        print(f"\n=== Similar tasks to '{args.search}' ===")
        for result in results:
            print(f"[{result['similarity']:.3f}] {result["tasks"]}")
    
    elif args.all:
        # Process all unembedded tasks
        total = 0
        while True:
            processed = generator.process_batch(args.batch)
            if processed == 0:
                break
            total += processed
            logger.info(f"Total processed: {total}")
        
        logger.info(f"Finished. Total embeddings generated: {total}")
    
    else:
        # Process single batch
        processed = generator.process_batch(args.batch)
        logger.info(f"Processed {processed} tasks")


if __name__ == "__main__":
    main()