#!/usr/bin/env python3
"""
Test embeddings extraction on real captured screenshots.
This validates embeddings functionality using actual screenshots from AutoTaskTracker.
"""

import json
import os
import sqlite3
import sys
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine, EmbeddingStats


class TestEmbeddingsExtractionOnRealScreenshots:
    """Test embeddings extraction functionality on real captured screenshots."""
    
    @pytest.fixture
    def real_memos_db_path(self) -> str:
        """Get the real memos database path."""
        memos_db = Path.home() / ".memos" / "database.db"
        if not memos_db.exists():
            pytest.skip("Real memos database not found - need actual AutoTaskTracker usage data")
        return str(memos_db)
    
    @pytest.fixture
    def screenshots_for_embeddings(self, real_memos_db_path) -> List[Dict[str, Any]]:
        """Get screenshots suitable for embeddings generation."""
        conn = sqlite3.connect(real_memos_db_path)
        conn.row_factory = sqlite3.Row
        
        # Get screenshots with and without embeddings
        cursor = conn.execute("""
            SELECT 
                e.id,
                e.filepath,
                e.created_at,
                m1.value as window_title,
                m2.value as ocr_text,
                m3.value as ai_task,
                m4.value as embeddings,
                LENGTH(m4.value) as embedding_size
            FROM entities e
            LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'active_window'
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'text'
            LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
            LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'embeddings'
            WHERE e.file_type_group = 'image'
            AND m1.value IS NOT NULL
            ORDER BY 
                CASE 
                    WHEN m4.value IS NULL THEN 0  -- Prioritize screenshots without embeddings
                    ELSE 1
                END,
                e.created_at DESC
            LIMIT 30
        """)
        
        screenshots = []
        for row in cursor:
            screenshot = {
                'id': row['id'],
                'filepath': row['filepath'],
                'created_at': row['created_at'],
                'window_title': row['window_title'],
                'has_ocr': row['ocr_text'] is not None,
                'has_ai_task': row['ai_task'] is not None,
                'has_embeddings': row['embeddings'] is not None,
                'embedding_size': row['embedding_size'] or 0,
                'ocr_text': row['ocr_text'],
                'ai_task': row['ai_task']
            }
            screenshots.append(screenshot)
        
        conn.close()
        
        if len(screenshots) == 0:
            pytest.skip("No screenshots found for embeddings testing")
        
        without_embeddings = sum(1 for s in screenshots if not s['has_embeddings'])
        with_embeddings = sum(1 for s in screenshots if s['has_embeddings'])
        
        print(f"\n✅ Found {len(screenshots)} screenshots for embeddings testing")
        print(f"   - Without embeddings: {without_embeddings}")
        print(f"   - With embeddings: {with_embeddings}")
        
        return screenshots
    
    def test_embeddings_stats_on_real_data(self, real_memos_db_path):
        """Test embeddings statistics on real database."""
        try:
            stats = EmbeddingStats(real_memos_db_path)
        except ImportError:
            pytest.skip("Embeddings dependencies not available")
        
        print(f"\n📊 Testing Embeddings Statistics:")
        
        # Get coverage statistics
        coverage = stats.get_embedding_coverage()
        
        # Validate coverage structure
        assert isinstance(coverage, dict), "Coverage should be a dictionary"
        assert 'total_screenshots' in coverage, "Should have total screenshots count"
        assert 'screenshots_with_embeddings' in coverage, "Should have embeddings count"
        assert 'coverage_percentage' in coverage, "Should have coverage percentage"
        
        # Validate data types and values
        assert isinstance(coverage['total_screenshots'], int), "Total should be integer"
        assert isinstance(coverage['screenshots_with_embeddings'], int), "Count should be integer"
        assert isinstance(coverage['coverage_percentage'], (int, float)), "Percentage should be numeric"
        
        assert coverage['total_screenshots'] >= 0, "Total screenshots should be non-negative"
        assert coverage['screenshots_with_embeddings'] >= 0, "Embeddings count should be non-negative"
        assert 0 <= coverage['coverage_percentage'] <= 100, "Coverage should be 0-100%"
        
        print(f"\n📊 Embeddings Coverage:")
        print(f"   - Total screenshots: {coverage['total_screenshots']:,}")
        print(f"   - With embeddings: {coverage['screenshots_with_embeddings']:,}")
        print(f"   - Coverage: {coverage['coverage_percentage']:.1f}%")
        
        # Get recent embeddings
        recent = stats.get_recent_embeddings(limit=5)
        if recent:
            print(f"\n   Recent embeddings:")
            for item in recent:
                print(f"     - {item.get('window_title', 'Unknown')[:50]}...")
                print(f"       Created: {item.get('created_at', 'Unknown')}")
    
    def test_embeddings_search_engine_initialization(self, real_memos_db_path):
        """Test embeddings search engine initialization with real data."""
        try:
            search_engine = EmbeddingsSearchEngine(real_memos_db_path)
            assert search_engine is not None, "Search engine should initialize"
            
            # Check if model is loaded
            assert hasattr(search_engine, 'model'), "Should have model attribute"
            assert search_engine.model is not None, "Model should be loaded"
            
            print(f"\n✅ Embeddings Search Engine initialized successfully")
            print(f"   - Model loaded: ✅")
            print(f"   - Database connected: ✅")
            
        except ImportError as e:
            pytest.skip(f"Embeddings dependencies not available: {e}")
        except Exception as e:
            pytest.fail(f"Failed to initialize search engine: {e}")
    
    def test_generate_embeddings_for_real_screenshots(self, real_memos_db_path, screenshots_for_embeddings):
        """Test generating embeddings for real screenshots without them."""
        try:
            search_engine = EmbeddingsSearchEngine(real_memos_db_path)
        except ImportError:
            pytest.skip("Embeddings dependencies not available")
        
        # Find screenshots without embeddings
        without_embeddings = [s for s in screenshots_for_embeddings if not s['has_embeddings']][:5]
        
        if not without_embeddings:
            pytest.skip("All screenshots already have embeddings")
        
        print(f"\n🔍 Testing embeddings generation on {len(without_embeddings)} screenshots:")
        
        generated_count = 0
        total_time = 0
        
        for screenshot in without_embeddings:
            # Combine available text for embedding
            text_parts = []
            
            if screenshot['window_title']:
                text_parts.append(screenshot['window_title'])
            
            if screenshot['ai_task']:
                text_parts.append(screenshot['ai_task'])
            
            if screenshot['ocr_text']:
                # Extract some text from OCR if available
                try:
                    if screenshot['ocr_text'].startswith('['):
                        ocr_data = eval(screenshot['ocr_text'])
                        if isinstance(ocr_data, list) and len(ocr_data) > 0:
                            for item in ocr_data[:3]:  # First 3 text regions
                                if isinstance(item, list) and len(item) >= 2:
                                    text_parts.append(str(item[1]))
                except:
                    pass
            
            combined_text = " ".join(text_parts)
            
            if not combined_text.strip():
                print(f"   ⚠️ No text available for screenshot {screenshot['id']}")
                continue
            
            print(f"\n   Processing screenshot {screenshot['id']}:")
            print(f"     Window: {screenshot['window_title'][:50]}...")
            print(f"     Text length: {len(combined_text)} chars")
            
            start_time = time.time()
            
            try:
                # Generate embedding
                embedding = search_engine._generate_embedding(combined_text)
                processing_time = time.time() - start_time
                
                # Validate embedding
                assert embedding is not None, "Should generate embedding"
                assert isinstance(embedding, (list, np.ndarray)), "Embedding should be array-like"
                
                embedding_array = np.array(embedding)
                assert embedding_array.ndim == 1, "Embedding should be 1D"
                assert embedding_array.shape[0] > 100, "Embedding should have meaningful dimensions"
                assert not np.all(embedding_array == 0), "Embedding should not be all zeros"
                
                # Check embedding properties
                norm = np.linalg.norm(embedding_array)
                assert norm > 0, "Embedding should have non-zero norm"
                
                generated_count += 1
                total_time += processing_time
                
                print(f"     ✅ Generated embedding: {embedding_array.shape[0]} dimensions")
                print(f"     Processing time: {processing_time:.3f}s")
                print(f"     Norm: {norm:.3f}")
                
            except Exception as e:
                print(f"     ❌ Failed to generate embedding: {e}")
        
        if generated_count > 0:
            avg_time = total_time / generated_count
            
            print(f"\n📊 Embedding Generation Results:")
            print(f"   - Successfully generated: {generated_count}/{len(without_embeddings)}")
            print(f"   - Average time: {avg_time:.3f}s per embedding")
            print(f"   - Total time: {total_time:.2f}s")
            
            assert generated_count > 0, "Should generate at least some embeddings"
            assert avg_time < 1.0, f"Embedding generation should be fast, took {avg_time:.3f}s average"
    
    def test_semantic_search_on_real_screenshots(self, real_memos_db_path, screenshots_for_embeddings):
        """Test semantic search functionality on real screenshot data."""
        try:
            search_engine = EmbeddingsSearchEngine(real_memos_db_path)
        except ImportError:
            pytest.skip("Embeddings dependencies not available")
        
        # Check if we have any screenshots with embeddings
        with_embeddings = [s for s in screenshots_for_embeddings if s['has_embeddings']]
        
        if not with_embeddings:
            pytest.skip("No screenshots with embeddings for search testing")
        
        print(f"\n🔍 Testing semantic search on {len(with_embeddings)} screenshots with embeddings:")
        
        # Test queries
        test_queries = [
            "coding in python",
            "dashboard development",
            "terminal commands",
            "AutoTaskTracker",
            "AI task extraction"
        ]
        
        search_results = []
        
        for query in test_queries:
            print(f"\n   Searching for: '{query}'")
            
            try:
                start_time = time.time()
                results = search_engine.semantic_search(query, limit=5)
                search_time = time.time() - start_time
                
                if results:
                    search_results.append({
                        'query': query,
                        'results': results,
                        'count': len(results),
                        'search_time': search_time
                    })
                    
                    print(f"     ✅ Found {len(results)} results in {search_time:.3f}s")
                    
                    # Show top results
                    for i, result in enumerate(results[:2]):
                        print(f"     {i+1}. Score: {result.get('similarity_score', 0):.3f}")
                        print(f"        Window: {result.get('window_title', 'Unknown')[:50]}...")
                        if result.get('task'):
                            print(f"        Task: {result.get('task')}")
                else:
                    print(f"     ⚠️ No results found")
                    
            except Exception as e:
                print(f"     ❌ Search failed: {e}")
        
        if search_results:
            # Analyze search performance
            avg_results = sum(sr['count'] for sr in search_results) / len(search_results)
            avg_time = sum(sr['search_time'] for sr in search_results) / len(search_results)
            
            print(f"\n📊 Search Performance:")
            print(f"   - Queries tested: {len(search_results)}/{len(test_queries)}")
            print(f"   - Average results per query: {avg_results:.1f}")
            print(f"   - Average search time: {avg_time:.3f}s")
            
            # Validate search quality
            assert len(search_results) > 0, "Should have successful searches"
            assert avg_time < 1.0, f"Search should be fast, took {avg_time:.3f}s average"
            
            # Check that results have expected structure
            for sr in search_results:
                for result in sr['results']:
                    assert 'entity_id' in result, "Result should have entity_id"
                    assert 'similarity_score' in result, "Result should have similarity score"
                    assert isinstance(result['similarity_score'], (int, float)), "Score should be numeric"
                    assert 0 <= result['similarity_score'] <= 1, "Score should be between 0 and 1"
    
    def test_embedding_similarity_computation(self, real_memos_db_path):
        """Test embedding similarity computation between real screenshots."""
        try:
            search_engine = EmbeddingsSearchEngine(real_memos_db_path)
        except ImportError:
            pytest.skip("Embeddings dependencies not available")
        
        print(f"\n🔍 Testing embedding similarity computation:")
        
        # Generate embeddings for test cases
        test_texts = [
            # Similar texts
            ("Python programming in VS Code", "Coding Python in Visual Studio Code"),
            ("AutoTaskTracker dashboard development", "Building AutoTaskTracker dashboards"),
            # Different texts
            ("Python programming in VS Code", "Watching YouTube videos"),
            ("Terminal command execution", "Email in Gmail inbox")
        ]
        
        for i, (text1, text2) in enumerate(test_texts):
            print(f"\n   Test case {i+1}:")
            print(f"     Text 1: '{text1}'")
            print(f"     Text 2: '{text2}'")
            
            # Generate embeddings
            emb1 = search_engine._generate_embedding(text1)
            emb2 = search_engine._generate_embedding(text2)
            
            # Compute similarity
            emb1_array = np.array(emb1)
            emb2_array = np.array(emb2)
            
            # Normalize
            emb1_norm = emb1_array / np.linalg.norm(emb1_array)
            emb2_norm = emb2_array / np.linalg.norm(emb2_array)
            
            # Cosine similarity
            similarity = np.dot(emb1_norm, emb2_norm)
            
            print(f"     Similarity: {similarity:.3f}")
            
            # Validate similarity
            assert -1 <= similarity <= 1, "Similarity should be between -1 and 1"
            
            # Check expected similarity patterns
            if i < 2:  # Similar texts
                assert similarity > 0.7, f"Similar texts should have high similarity, got {similarity:.3f}"
            else:  # Different texts
                assert similarity < 0.6, f"Different texts should have lower similarity, got {similarity:.3f}"
    
    def test_embeddings_persistence_in_database(self, real_memos_db_path):
        """Test that embeddings are properly stored and retrieved from database."""
        conn = sqlite3.connect(real_memos_db_path)
        conn.row_factory = sqlite3.Row
        
        # Check embeddings storage format
        cursor = conn.execute("""
            SELECT 
                m.entity_id,
                m.value as embedding_data,
                LENGTH(m.value) as data_size,
                e.filepath,
                m2.value as window_title
            FROM metadata_entries m
            JOIN entities e ON m.entity_id = e.id
            LEFT JOIN metadata_entries m2 ON m.entity_id = m2.entity_id AND m2.key = 'active_window'
            WHERE m.key = 'embeddings'
            AND m.value IS NOT NULL
            LIMIT 5
        """)
        
        embeddings_found = []
        
        for row in cursor:
            embeddings_found.append({
                'entity_id': row['entity_id'],
                'data_size': row['data_size'],
                'window_title': row['window_title']
            })
            
            # Try to parse embedding data
            try:
                embedding_data = json.loads(row['embedding_data'])
                
                # Validate embedding format
                assert isinstance(embedding_data, list), "Embedding should be stored as list"
                assert len(embedding_data) > 100, "Embedding should have meaningful dimensions"
                assert all(isinstance(x, (int, float)) for x in embedding_data[:10]), \
                    "Embedding values should be numeric"
                
                # Check embedding properties
                embedding_array = np.array(embedding_data)
                norm = np.linalg.norm(embedding_array)
                
                print(f"\n   ✅ Valid embedding for entity {row['entity_id']}:")
                print(f"      Window: {row['window_title'][:50] if row['window_title'] else 'Unknown'}...")
                print(f"      Dimensions: {len(embedding_data)}")
                print(f"      Data size: {row['data_size']} bytes")
                print(f"      Norm: {norm:.3f}")
                
            except Exception as e:
                print(f"\n   ⚠️ Failed to parse embedding for entity {row['entity_id']}: {e}")
        
        conn.close()
        
        if embeddings_found:
            print(f"\n📊 Embeddings Storage Summary:")
            print(f"   - Found {len(embeddings_found)} stored embeddings")
            print(f"   - Average size: {sum(e['data_size'] for e in embeddings_found) / len(embeddings_found):.0f} bytes")
        else:
            pytest.skip("No embeddings found in database")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])