"""
Test floating point precision fixes in AI modules.

Tests to verify that floating point calculations are properly rounded
to avoid precision drift in similarity calculations, confidence scores,
and other numerical computations.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
import json

from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine
from autotasktracker.ai.sensitive_filter import SensitiveDataFilter
from autotasktracker.ai.ocr_enhancement import OCREnhancer


class TestFloatingPointPrecision:
    """Test floating point precision in AI calculations."""
    
    def test_cosine_similarity_precision(self):
        """Test cosine similarity returns properly rounded values."""
        # Create embeddings engine with mock database
        with patch('autotasktracker.ai.embeddings_search.DatabaseManager'):
            engine = EmbeddingsSearchEngine("test.db")
        
        # Test with known vectors that should produce precise results
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        vec3 = np.array([1.0, 0.0, 0.0])  # Same as vec1
        
        # Orthogonal vectors should have similarity of 0
        similarity_orthogonal = engine.cosine_similarity(vec1, vec2)
        assert similarity_orthogonal == 0.0
        assert isinstance(similarity_orthogonal, float)
        
        # Identical vectors should have similarity of 1
        similarity_identical = engine.cosine_similarity(vec1, vec3)
        assert similarity_identical == 1.0
        assert isinstance(similarity_identical, float)
        
        # Test precision with floating point numbers
        vec4 = np.array([0.33333333333333, 0.66666666666666, 0.0])
        vec5 = np.array([0.66666666666666, 0.33333333333333, 0.0])
        
        similarity_precise = engine.cosine_similarity(vec4, vec5)
        # Should be rounded to 8 decimal places
        assert len(str(similarity_precise).split('.')[-1]) <= 8
        
    def test_embedding_parsing_precision(self):
        """Test embedding parsing maintains proper precision."""
        with patch('autotasktracker.ai.embeddings_search.DatabaseManager'):
            engine = EmbeddingsSearchEngine("test.db")
        
        # Test with space-separated values that could have precision issues (768 dimensions)
        embedding_str = " ".join([f"0.{i:06d}" for i in range(768)])
        parsed = engine._parse_embedding(embedding_str)
        
        assert parsed is not None
        # Values should be rounded to 8 decimal places
        for val in parsed:
            # Convert to string to check decimal places
            val_str = f"{val:.10f}"
            # Should not have more than 8 significant decimal places
            decimal_part = val_str.split('.')[1].rstrip('0')
            assert len(decimal_part) <= 8
    
    def test_sensitivity_score_precision(self):
        """Test sensitivity score calculation precision."""
        filter_obj = SensitiveDataFilter()
        
        # Test with text that would produce fractional scores
        test_text = "email@test.com and phone 555-1234"
        window_title = "Banking Application"
        
        score = filter_obj.calculate_sensitivity_score(test_text, window_title)
        
        # Score should be rounded to 4 decimal places
        assert isinstance(score, float)
        score_str = f"{score:.6f}"
        decimal_part = score_str.split('.')[1].rstrip('0')
        assert len(decimal_part) <= 4
        
        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0
    
    def test_ocr_confidence_precision(self):
        """Test OCR confidence scores maintain proper precision."""
        enhancer = OCREnhancer()
        
        # Mock OCR result with high-precision confidence
        mock_ocr_data = {
            "results": [
                {
                    "text": "Test text",
                    "confidence": 0.8765432109876543,
                    "bbox": [0, 0, 100, 20]
                }
            ]
        }
        
        results = enhancer.parse_ocr_json(json.dumps(mock_ocr_data))
        
        assert len(results) == 1
        # Confidence should be rounded to 4 decimal places
        confidence = results[0].confidence
        confidence_str = f"{confidence:.6f}"
        decimal_part = confidence_str.split('.')[1].rstrip('0')
        assert len(decimal_part) <= 4
    
    def test_similarity_matrix_precision(self):
        """Test similarity matrix calculations maintain precision."""
        with patch('autotasktracker.ai.embeddings_search.DatabaseManager'):
            engine = EmbeddingsSearchEngine("test.db")
        
        # Create test embeddings with potential precision issues
        embeddings = np.array([
            [0.1111111111111111, 0.2222222222222222, 0.3333333333333333],
            [0.4444444444444444, 0.5555555555555555, 0.6666666666666666],
            [0.7777777777777777, 0.8888888888888888, 0.9999999999999999]
        ])
        
        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        
        # Calculate similarity matrix
        similarity_matrix = np.dot(normalized, normalized.T)
        
        # All values should maintain reasonable precision
        for i in range(similarity_matrix.shape[0]):
            for j in range(similarity_matrix.shape[1]):
                val = similarity_matrix[i, j]
                # Check that we don't have extreme precision drift
                assert -1.0001 <= val <= 1.0001  # Allow tiny floating point errors
                
                # When rounded properly, diagonal should be 1.0
                if i == j:
                    rounded_val = round(float(val), 6)
                    assert abs(rounded_val - 1.0) < 1e-6
    
    def test_similarity_search_result_precision(self):
        """Test similarity search results have consistent precision."""
        with patch('autotasktracker.ai.embeddings_search.DatabaseManager') as mock_db:
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_db.return_value.get_connection.return_value = mock_conn
            
            # Mock embedding fetch
            engine = EmbeddingsSearchEngine("test.db")
            query_embedding = np.array([0.1, 0.2, 0.3])
            
            # Mock the query embedding fetch
            engine.get_embedding_for_entity = Mock(return_value=query_embedding)
            
            # Mock database results with embeddings
            mock_cursor.fetchall.return_value = [
                {
                    'id': 1,
                    'filepath': '/test1.png',
                    'created_at': '2024-01-01 10:00:00',
                    'ocr_text': 'test',
                    'active_window': 'test.txt',
                    'embedding': json.dumps([0.15, 0.25, 0.35])  # Similar to query
                },
                {
                    'id': 2,
                    'filepath': '/test2.png', 
                    'created_at': '2024-01-01 11:00:00',
                    'ocr_text': 'test2',
                    'active_window': 'test2.txt',
                    'embedding': json.dumps([0.9, 0.1, 0.1])  # Different from query
                }
            ]
            
            results = engine.semantic_search(query_entity_id=999, limit=10, similarity_threshold=0.1)
            
            # Check that all similarity scores are properly rounded
            for result in results:
                similarity = result['similarity_score']
                assert isinstance(similarity, float)
                
                # Should be rounded to 6 decimal places
                similarity_str = f"{similarity:.8f}"
                decimal_part = similarity_str.split('.')[1].rstrip('0')
                assert len(decimal_part) <= 6
                
                # Should be in valid range
                assert 0.0 <= similarity <= 1.0
    
    def test_precision_consistency_across_methods(self):
        """Test that precision is consistent across different calculation methods."""
        with patch('autotasktracker.ai.embeddings_search.DatabaseManager'):
            engine = EmbeddingsSearchEngine("test.db")
        
        # Create identical vectors
        vec1 = np.array([0.577350269189626, 0.577350269189626, 0.577350269189626])
        vec2 = np.array([0.577350269189626, 0.577350269189626, 0.577350269189626])
        
        # Calculate similarity using the engine method
        similarity1 = engine.cosine_similarity(vec1, vec2)
        
        # Calculate similarity manually with same precision
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        manual_similarity = round(float(np.dot(vec1, vec2) / (norm1 * norm2)), 8)
        
        # Should be identical due to consistent rounding
        assert similarity1 == manual_similarity
        assert similarity1 == 1.0  # Should be exactly 1.0 for identical vectors
    
    def test_edge_case_precision_handling(self):
        """Test precision handling in edge cases."""
        with patch('autotasktracker.ai.embeddings_search.DatabaseManager'):
            engine = EmbeddingsSearchEngine("test.db")
        
        # Test with very small numbers that could cause precision issues
        vec1 = np.array([1e-10, 1e-9, 1e-8])
        vec2 = np.array([1e-8, 1e-9, 1e-10])
        
        similarity = engine.cosine_similarity(vec1, vec2)
        
        # Should handle small numbers gracefully
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        
        # Test with zero vectors
        zero_vec = np.array([0.0, 0.0, 0.0])
        non_zero_vec = np.array([1.0, 1.0, 1.0])
        
        similarity_zero = engine.cosine_similarity(zero_vec, non_zero_vec)
        assert similarity_zero == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])