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
        """Test OCR confidence scores maintain proper precision with comprehensive validation."""
        import time
        
        start_time = time.time()
        enhancer = OCREnhancer()
        
        # Validate enhancer initialization
        assert isinstance(enhancer, OCREnhancer), "Should create valid OCREnhancer instance"
        assert hasattr(enhancer, 'parse_ocr_json'), "Enhancer should have parse_ocr_json method"
        assert callable(enhancer.parse_ocr_json), "parse_ocr_json should be callable"
        
        # Test multiple precision scenarios
        precision_test_cases = [
            (0.8765432109876543, "High precision floating point"),
            (0.123456789, "Medium precision floating point"),
            (0.999999999999999, "Near-maximum precision"),
            (0.000000000000001, "Near-minimum precision"),
            (0.5, "Exact half precision"),
            (1.0, "Maximum confidence"),
            (0.0, "Minimum confidence")
        ]
        
        processing_times = []
        
        for original_confidence, test_description in precision_test_cases:
            # Mock OCR result with specific precision confidence
            mock_ocr_data = {
                "results": [
                    {
                        "text": f"Test text for {test_description}",
                        "confidence": original_confidence,
                        "bbox": [0, 0, 100, 20]
                    }
                ]
            }
            
            # Validate input data structure
            assert isinstance(mock_ocr_data, dict), "OCR data should be dictionary"
            assert "results" in mock_ocr_data, "OCR data should have results key"
            assert isinstance(mock_ocr_data["results"], list), "Results should be list"
            assert len(mock_ocr_data["results"]) == 1, "Should have exactly one result"
            
            # Test JSON serialization and parsing
            json_data = json.dumps(mock_ocr_data)
            assert isinstance(json_data, str), "JSON dump should produce string"
            assert len(json_data) > 0, "JSON string should not be empty"
            assert '"confidence"' in json_data, "JSON should contain confidence field"
            
            # Parse OCR data with performance measurement
            parse_start = time.time()
            results = enhancer.parse_ocr_json(json_data)
            parse_time = time.time() - parse_start
            processing_times.append(parse_time)
            
            # Validate parsing results
            assert results is not None, f"Should successfully parse OCR data for {test_description}"
            assert isinstance(results, list), f"Results should be list for {test_description}"
            assert len(results) == 1, f"Should have exactly one result for {test_description}"
            assert parse_time < 0.1, f"Parsing should be fast for {test_description}, took {parse_time:.3f}s"
            
            result = results[0]
            
            # Validate result object structure
            assert hasattr(result, 'confidence'), f"Result should have confidence attribute for {test_description}"
            assert hasattr(result, 'text'), f"Result should have text attribute for {test_description}"
            assert hasattr(result, 'bbox'), f"Result should have bbox attribute for {test_description}"
            
            # Validate confidence precision - core business logic
            confidence = result.confidence
            assert isinstance(confidence, (int, float)), f"Confidence should be numeric for {test_description}"
            assert 0.0 <= confidence <= 1.0, f"Confidence should be in valid range [0,1] for {test_description}"
            
            # Precision validation - should be rounded to 4 decimal places
            confidence_str = f"{confidence:.6f}"
            decimal_part = confidence_str.split('.')[1].rstrip('0')
            assert len(decimal_part) <= 4, f"Confidence should be rounded to ≤4 decimal places for {test_description}, got {len(decimal_part)} places"
            
            # Validate precision bounds
            if original_confidence <= 1.0:
                # Should not exceed original precision inappropriately
                precision_diff = abs(confidence - original_confidence)
                assert precision_diff <= 0.0001, f"Precision drift should be minimal for {test_description}"
            
            # Validate text preservation
            assert isinstance(result.text, str), f"Text should be string for {test_description}"
            assert len(result.text) > 0, f"Text should not be empty for {test_description}"
            assert "Test text" in result.text, f"Text content should be preserved for {test_description}"
            
            # Validate bbox preservation
            assert isinstance(result.bbox, (list, tuple)), f"Bbox should be list/tuple for {test_description}"
            assert len(result.bbox) == 4, f"Bbox should have 4 coordinates for {test_description}"
            assert all(isinstance(coord, (int, float)) for coord in result.bbox), f"Bbox coordinates should be numeric for {test_description}"
        
        # Test edge cases for precision handling
        edge_case_confidences = [
            ("NaN", float('nan')),
            ("Infinity", float('inf')),
            ("Negative infinity", float('-inf')),
            ("Very small number", 1e-15),
            ("Very large number", 1e15)
        ]
        
        for case_name, edge_confidence in edge_case_confidences:
            mock_edge_data = {
                "results": [
                    {
                        "text": f"Edge case: {case_name}",
                        "confidence": edge_confidence,
                        "bbox": [0, 0, 100, 20]
                    }
                ]
            }
            
            try:
                edge_json = json.dumps(mock_edge_data)
                edge_results = enhancer.parse_ocr_json(edge_json)
                
                if edge_results and len(edge_results) > 0:
                    edge_confidence_result = edge_results[0].confidence
                    
                    # Should handle edge cases gracefully
                    assert isinstance(edge_confidence_result, (int, float)), f"Should handle {case_name} as numeric"
                    if not (np.isnan(edge_confidence_result) or np.isinf(edge_confidence_result)):
                        assert 0.0 <= edge_confidence_result <= 1.0, f"Should clamp {case_name} to valid range"
                        
            except (ValueError, OverflowError, json.JSONEncodeError) as e:
                # Acceptable to raise errors for invalid edge cases
                assert any(word in str(e).lower() for word in ['value', 'overflow', 'json', 'confidence']), \
                    f"Should raise appropriate error for {case_name}: {e}"
        
        # Performance validation
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            assert avg_processing_time < 0.05, f"Average OCR parsing should be very fast, was {avg_processing_time:.3f}s"
        
        # Test malformed JSON handling
        malformed_cases = [
            ('{"results": [{"text": "test", "confidence":}]}', "Incomplete JSON"),
            ('{"results": [{"text": "test", "confidence": "invalid"}]}', "String confidence"),
            ('{"results": [{"confidence": 0.5}]}', "Missing text field"),
            ('{"malformed": true}', "Missing results field"),
            ('', "Empty string"),
            ('not json at all', "Invalid JSON")
        ]
        
        for malformed_json, error_description in malformed_cases:
            try:
                error_results = enhancer.parse_ocr_json(malformed_json)
                # If no exception, should handle gracefully
                assert error_results is None or len(error_results) == 0, f"Should handle {error_description} gracefully"
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
                # Expected for malformed data
                assert len(str(e)) > 0, f"Should provide meaningful error message for {error_description}"
        
        total_test_time = time.time() - start_time
        assert total_test_time < 1.0, f"Complete precision test should be efficient, took {total_test_time:.3f}s"
    
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
                    "ocr_result": 'test',
                    'active_window': 'test.txt',
                    'embedding': json.dumps([0.15, 0.25, 0.35])  # Similar to query
                },
                {
                    'id': 2,
                    'filepath': '/test2.png', 
                    'created_at': '2024-01-01 11:00:00',
                    "ocr_result": 'test2',
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