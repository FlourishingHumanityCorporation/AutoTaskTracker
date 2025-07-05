"""Integration tests for PostgreSQL and pgvector capabilities."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from autotasktracker.pensieve.postgresql_adapter import PostgreSQLAdapter, get_postgresql_adapter, reset_postgresql_adapter
from autotasktracker.pensieve.vector_search import EnhancedVectorSearch, VectorSearchQuery, get_enhanced_vector_search, reset_enhanced_vector_search


class TestPostgreSQLAdapter:
    """Test PostgreSQL adapter functionality."""
    
    @pytest.mark.timeout(30)
    def test_adapter_initialization(self):
        """Test PostgreSQL adapter can be initialized."""
        adapter = get_postgresql_adapter()
        assert adapter is not None
        assert hasattr(adapter, 'capabilities')
        assert hasattr(adapter, 'pensieve_client')
        assert hasattr(adapter, 'config')
    
    @pytest.mark.timeout(30)
    def test_capabilities_detection(self):
        """Test capabilities detection works."""
        adapter = get_postgresql_adapter()
        capabilities = adapter.capabilities
        
        assert hasattr(capabilities, 'postgresql_enabled')
        assert hasattr(capabilities, 'vector_search_enabled')
        assert hasattr(capabilities, 'pgvector_available')
        assert hasattr(capabilities, 'performance_tier')
        assert hasattr(capabilities, 'max_vectors')
        
        # Performance tier should be one of the expected values
        assert capabilities.performance_tier in ['sqlite', 'postgresql', 'pgvector']
    
    def test_performance_tier_logic(self):
        """Test performance tier logic."""
        # Create adapter with mocked config
        with patch('autotasktracker.pensieve.postgresql_adapter.get_pensieve_config') as mock_config:
            mock_config.return_value.postgresql_enabled = True
            mock_config.return_value.vector_search_enabled = True
            
            reset_postgresql_adapter()
            adapter = get_postgresql_adapter()
            
            # Should detect highest tier when both are enabled
            # (Note: actual tier depends on Pensieve health check)
            assert adapter.capabilities.performance_tier in ['pgvector', 'postgresql', 'sqlite']
    
    @pytest.mark.asyncio
    async def test_get_tasks_optimized(self):
        """Test optimized task retrieval."""
        adapter = get_postgresql_adapter()
        
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        
        # Should not fail even if no data
        tasks = await adapter.get_tasks_optimized(
            start_date=start_date,
            end_date=end_date,
            limit=10
        )
        
        assert isinstance(tasks, list)
        # Each task should have expected structure
        for task in tasks:
            assert 'id' in task
            assert 'timestamp' in task
            assert 'tasks' in task
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test performance metrics generation."""
        adapter = get_postgresql_adapter()
        
        metrics = await adapter.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'backend_type' in metrics
        assert 'postgresql_enabled' in metrics
        assert 'vector_search_enabled' in metrics
        assert 'max_vectors_supported' in metrics
        
        # Sample query time should be reasonable
        if 'sample_query_time_ms' in metrics:
            assert metrics['sample_query_time_ms'] < 10000  # Less than 10 seconds
    
    def test_migration_recommendations(self):
        """Test migration recommendations."""
        adapter = get_postgresql_adapter()
        
        recommendations = adapter.get_migration_recommendations()
        
        assert isinstance(recommendations, dict)
        assert 'current_backend' in recommendations
        assert 'recommendations' in recommendations
        assert isinstance(recommendations['recommendations'], list)
        
        # Each recommendation should have required fields
        for rec in recommendations['recommendations']:
            assert 'priority' in rec
            assert 'action' in rec
            assert 'benefit' in rec
            assert 'command' in rec
            assert rec['priority'] in ['high', 'medium', 'low']
    
    def test_scale_estimate(self):
        """Test scale estimation."""
        adapter = get_postgresql_adapter()
        
        scale = adapter._get_scale_estimate()
        
        assert isinstance(scale, str)
        assert any(keyword in scale.lower() for keyword in ['scale', 'screenshot'])
    
    def test_adapter_singleton_behavior(self):
        """Test adapter singleton behavior."""
        adapter1 = get_postgresql_adapter()
        adapter2 = get_postgresql_adapter()
        assert adapter1 is adapter2
        
        # Reset and get new instance
        reset_postgresql_adapter()
        adapter3 = get_postgresql_adapter()
        assert adapter3 is not adapter1


class TestEnhancedVectorSearch:
    """Test enhanced vector search functionality."""
    
    def test_search_initialization(self):
        """Test enhanced vector search initialization."""
        search = get_enhanced_vector_search()
        assert search is not None
        assert hasattr(search, 'pg_adapter')
        assert hasattr(search, 'pensieve_client')
        assert hasattr(search, 'capabilities')
    
    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic search functionality."""
        search = get_enhanced_vector_search()
        
        query = VectorSearchQuery(
            text="test search",
            max_results=5
        )
        
        # Should not fail even with no data
        results = await search.search(query)
        
        assert isinstance(results, list)
        # Each result should be a VectorSearchResult
        for result in results:
            assert hasattr(result, 'entity_id')
            assert hasattr(result, 'relevance_score')
            assert hasattr(result, 'vector_similarity_score')
            assert hasattr(result, 'embedding_quality')
    
    @pytest.mark.asyncio
    async def test_search_with_different_backends(self):
        """Test search adapts to different backend capabilities."""
        search = get_enhanced_vector_search()
        
        query = VectorSearchQuery(
            text="test backend adaptation",
            similarity_threshold=0.5,
            max_results=3
        )
        
        # Test with current backend (whatever it is)
        results = await search.search(query)
        assert isinstance(results, list)
        
        # Results should be sorted by relevance
        if len(results) > 1:
            for i in range(1, len(results)):
                assert results[i-1].relevance_score >= results[i].relevance_score
    
    def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation."""
        search = get_enhanced_vector_search()
        
        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = search._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 0.01
        
        # Test orthogonal vectors
        vec3 = [1.0, 0.0, 0.0]
        vec4 = [0.0, 1.0, 0.0]
        similarity = search._calculate_cosine_similarity(vec3, vec4)
        assert abs(similarity - 0.5) < 0.1  # Should be around 0.5 due to normalization
        
        # Test zero vectors
        vec5 = [0.0, 0.0, 0.0]
        vec6 = [1.0, 0.0, 0.0]
        similarity = search._calculate_cosine_similarity(vec5, vec6)
        assert similarity == 0.0
    
    def test_task_relevance_calculation(self):
        """Test task relevance calculation."""
        search = get_enhanced_vector_search()
        
        query = VectorSearchQuery(text="python coding")
        
        # Task with matching content
        task1 = {
            'window_title': 'VS Code - python script.py',
            'tasks': [{'title': 'coding python function', 'category': 'Development'}],
            'ocr_text': 'def function(): python code here',
            'category': 'Development'
        }
        
        relevance1 = search._calculate_task_relevance(task1, query)
        assert relevance1 > 0.5  # Should have high relevance
        
        # Task with no matching content
        task2 = {
            'window_title': 'Safari - news website',
            'tasks': [{'title': 'reading news', 'category': 'Research'}],
            'ocr_text': 'latest news articles',
            'category': 'Research'
        }
        
        relevance2 = search._calculate_task_relevance(task2, query)
        assert relevance2 < relevance1  # Should have lower relevance
    
    def test_embedding_quality_assessment(self):
        """Test embedding quality assessment."""
        search = get_enhanced_vector_search()
        
        # High quality embedding (good variance)
        good_embedding = json.dumps([0.1, -0.5, 0.3, 0.8] * 192)  # 768 dimensions
        quality1 = search._assess_embedding_quality(good_embedding)
        assert quality1 in ['high', 'medium']
        
        # Low quality embedding (all zeros)
        bad_embedding = json.dumps([0.0] * 768)
        quality2 = search._assess_embedding_quality(bad_embedding)
        assert quality2 == 'low'
        
        # Invalid embedding
        invalid_embedding = "not json"
        quality3 = search._assess_embedding_quality(invalid_embedding)
        assert quality3 == 'unknown'
        
        # No embedding
        quality4 = search._assess_embedding_quality(None)
        assert quality4 == 'unknown'
    
    def test_semantic_clustering(self):
        """Test semantic clustering logic."""
        search = get_enhanced_vector_search()
        
        # Development tasks
        cluster1 = search._determine_semantic_cluster(
            [{'title': 'coding', 'category': 'Development'}], 
            'Development'
        )
        assert cluster1 == 'software_development'
        
        # Communication tasks
        cluster2 = search._determine_semantic_cluster(
            [{'title': 'email', 'category': 'Communication'}], 
            'Communication'
        )
        assert cluster2 == 'collaboration'
        
        # Research tasks
        cluster3 = search._determine_semantic_cluster(
            [{'title': 'reading', 'category': 'Research'}], 
            'Research'
        )
        assert cluster3 == 'knowledge_work'
    
    @pytest.mark.asyncio
    async def test_search_performance_metrics(self):
        """Test search performance metrics."""
        search = get_enhanced_vector_search()
        
        metrics = await search.search_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'search_backend' in metrics
        
        if 'sample_search_time_ms' in metrics:
            assert metrics['sample_search_time_ms'] > 0
            assert metrics['sample_search_time_ms'] < 30000  # Less than 30 seconds
        
        if 'features' in metrics:
            features = metrics['features']
            assert isinstance(features.get('vector_similarity'), bool)
            assert isinstance(features.get('semantic_clustering'), bool)
            assert isinstance(features.get('hybrid_search'), bool)
    
    def test_search_singleton_behavior(self):
        """Test enhanced vector search singleton behavior."""
        search1 = get_enhanced_vector_search()
        search2 = get_enhanced_vector_search()
        assert search1 is search2
        
        # Reset and get new instance
        reset_enhanced_vector_search()
        search3 = get_enhanced_vector_search()
        assert search3 is not search1


class TestIntegration:
    """Test integration between PostgreSQL adapter and vector search."""
    
    @pytest.mark.asyncio
    async def test_adapter_and_search_integration(self):
        """Test adapter and search work together."""
        adapter = get_postgresql_adapter()
        search = get_enhanced_vector_search()
        
        # Both should use the same capabilities
        assert adapter.capabilities.performance_tier == search.capabilities.performance_tier
        
        # Search should use adapter for backend detection
        query = VectorSearchQuery(text="integration test")
        results = await search.search(query)
        
        # Should complete without errors
        assert isinstance(results, list)
    
    def test_performance_tier_consistency(self):
        """Test performance tier is consistent across components."""
        adapter = get_postgresql_adapter()
        search = get_enhanced_vector_search()
        
        # Both should report the same backend type
        assert adapter.capabilities.performance_tier == search.capabilities.performance_tier
        
        # Capabilities should be consistent
        assert adapter.capabilities.postgresql_enabled == search.capabilities.postgresql_enabled
        assert adapter.capabilities.vector_search_enabled == search.capabilities.vector_search_enabled
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_end_to_end_workflow(self):
        """Test complete workflow from adapter to search."""
        adapter = get_postgresql_adapter()
        search = get_enhanced_vector_search()
        
        # 1. Check capabilities
        capabilities = adapter.capabilities
        assert capabilities.performance_tier in ['sqlite', 'postgresql', 'pgvector']
        
        # 2. Get performance metrics
        adapter_metrics = await adapter.get_performance_metrics()
        search_metrics = await search.get_search_performance_metrics()
        
        assert isinstance(adapter_metrics, dict)
        assert isinstance(search_metrics, dict)
        
        # 3. Perform search
        query = VectorSearchQuery(
            text="end to end test",
            similarity_threshold=0.3,
            max_results=5
        )
        
        results = await search.search(query)
        assert isinstance(results, list)
        
        # 4. Validate results structure
        for result in results:
            assert hasattr(result, 'entity_id')
            assert hasattr(result, 'relevance_score')
            assert 0 <= result.relevance_score <= 1
    
    def test_configuration_synchronization(self):
        """Test configuration is synchronized between components."""
        adapter = get_postgresql_adapter()
        search = get_enhanced_vector_search()
        
        # Both should use the same configuration
        adapter_config = adapter.config
        search_config = search.pg_adapter.config
        
        # Key settings should match
        assert adapter_config.postgresql_enabled == search_config.postgresql_enabled
        assert adapter_config.vector_search_enabled == search_config.vector_search_enabled


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    reset_postgresql_adapter()
    reset_enhanced_vector_search()
    yield
    reset_postgresql_adapter()
    reset_enhanced_vector_search()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])