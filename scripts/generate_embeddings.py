#!/usr/bin/env python3
"""
Generate embeddings for existing screenshots in the Memos database.
This enables semantic search and similarity features.
"""
import os
import sys
import sqlite3
import json
import logging
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.expanduser("~/.memos/database.db")
        self.model_name = "jinaai/jina-embeddings-v2-base-en"
        self.model = None
        
    def init_model(self):
        """Initialize the embedding model."""
        logger.info(f"Loading embedding model: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.info("Installing sentence-transformers...")
            os.system(f"{sys.executable} -m pip install sentence-transformers")
            self.model = SentenceTransformer(self.model_name)
    
    def get_unprocessed_screenshots(self, limit=None):
        """Get screenshots without embeddings."""
        query = """
        SELECT e.id, e.filepath, 
               me_ocr.value as ocr_text,
               me_window.value as active_window
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr."key" = 'ocr_result'
        LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id AND me_window."key" = 'active_window'
        LEFT JOIN metadata_entries me_emb ON e.id = me_emb.entity_id AND me_emb."key" = 'embedding'
        WHERE e.file_type_group = 'image' 
        AND me_emb.value IS NULL
        AND (me_ocr.value IS NOT NULL OR me_window.value IS NOT NULL)
        ORDER BY e.created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def extract_text_for_embedding(self, ocr_text, window_title):
        """Extract relevant text for embedding generation."""
        texts = []
        
        # Add window title
        if window_title:
            texts.append(f"Window: {window_title}")
        
        # Extract text from OCR
        if ocr_text:
            try:
                # Parse OCR JSON
                if isinstance(ocr_text, str):
                    ocr_data = json.loads(ocr_text)
                else:
                    ocr_data = ocr_text
                
                # Extract text content
                if isinstance(ocr_data, list):
                    for item in ocr_data[:10]:  # Limit to first 10 items
                        if isinstance(item, list) and len(item) >= 2:
                            text = item[1]
                            confidence = item[2] if len(item) > 2 else 0
                            if confidence > 0.7:  # Only high confidence text
                                texts.append(text.strip())
                
            except Exception as e:
                logger.debug(f"Failed to parse OCR: {e}")
        
        # Combine texts
        combined_text = " | ".join(texts)
        
        # Limit length
        if len(combined_text) > 512:
            combined_text = combined_text[:512]
        
        return combined_text
    
    def generate_embedding(self, text):
        """Generate embedding for text."""
        if not text or not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def save_embedding(self, entity_id, embedding):
        """Save embedding to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if metadata entry exists
            cursor.execute(
                'SELECT id FROM metadata_entries WHERE entity_id = ? AND "key" = \'embedding\'',
                (entity_id,)
            )
            existing = cursor.fetchone()
            
            embedding_json = json.dumps(embedding)
            
            if existing:
                # Update existing
                cursor.execute(
                    "UPDATE metadata_entries SET value = ?, updated_at = ? WHERE id = ?",
                    (embedding_json, datetime.now().isoformat(), existing[0])
                )
            else:
                # Insert new
                cursor.execute(
                    "INSERT INTO metadata_entries (entity_id, key, value, source_type, data_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (entity_id, 'embedding', embedding_json, 'ai_computed', 'vector', datetime.now().isoformat(), datetime.now().isoformat())
                )
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def process_screenshots(self, limit=None):
        """Process screenshots and generate embeddings."""
        # Initialize model
        if not self.model:
            self.init_model()
        
        # Get unprocessed screenshots
        screenshots = self.get_unprocessed_screenshots(limit)
        
        if not screenshots:
            logger.info("No unprocessed screenshots found")
            return
        
        logger.info(f"Found {len(screenshots)} screenshots to process")
        
        # Process each screenshot
        success_count = 0
        for screenshot in tqdm(screenshots, desc="Generating embeddings"):
            # Extract text
            text = self.extract_text_for_embedding(
                screenshot['ocr_text'],
                screenshot['active_window']
            )
            
            if not text:
                continue
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            
            if embedding:
                # Save to database
                if self.save_embedding(screenshot['id'], embedding):
                    success_count += 1
        
        logger.info(f"Successfully generated {success_count} embeddings")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate embeddings for AutoTaskTracker screenshots")
    parser.add_argument('--limit', type=int, help='Limit number of screenshots to process')
    parser.add_argument('--db', help='Path to database file')
    args = parser.parse_args()
    
    # Create generator
    generator = EmbeddingGenerator(args.db)
    
    # Process screenshots
    generator.process_screenshots(args.limit)


if __name__ == "__main__":
    main()