"""
Comprehensive tests for comparison metrics module.

Tests cover all metrics functionality including:
- Confidence metrics calculation
- Diversity metrics for tasks and categories
- Feature usage metrics
- Pipeline comparison analysis
- Improvement metrics between baselines
- Cross-pipeline analysis
"""
import pytest
import numpy as np
from collections import Counter

from autotasktracker.comparison.analysis.metrics import ComparisonMetrics


class TestComparisonMetrics:
    """Test the ComparisonMetrics class."""
    
    def test_calculate_confidence_metrics_with_valid_data(self):
        """Test confidence metrics calculation with valid confidence scores."""
        confidences = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.95]
        
        metrics = ComparisonMetrics.calculate_confidence_metrics(confidences)
        
        # Validate all expected metrics are present
        expected_keys = ['mean', 'median', 'std', 'min', 'max', 
                        'high_confidence_ratio', 'medium_confidence_ratio', 'low_confidence_ratio']
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"
        
        # Validate calculated values
        assert abs(metrics['mean'] - np.mean(confidences)) < 0.001
        assert abs(metrics['median'] - np.median(confidences)) < 0.001
        assert abs(metrics['std'] - np.std(confidences)) < 0.001
        assert metrics['min'] == 0.1
        assert metrics['max'] == 0.95
        
        # Validate confidence ratio calculations
        high_count = sum(1 for c in confidences if c >= 0.8)  # 0.9, 0.8, 0.95 = 3
        medium_count = sum(1 for c in confidences if 0.6 <= c < 0.8)  # 0.7, 0.6 = 2
        low_count = sum(1 for c in confidences if c < 0.6)  # 0.5, 0.4, 0.3, 0.2, 0.1 = 5
        
        assert metrics['high_confidence_ratio'] == high_count / len(confidences)
        assert metrics['medium_confidence_ratio'] == medium_count / len(confidences)
        assert metrics['low_confidence_ratio'] == low_count / len(confidences)
        
        # Validate ratios sum to 1
        total_ratio = (metrics['high_confidence_ratio'] + 
                      metrics['medium_confidence_ratio'] + 
                      metrics['low_confidence_ratio'])
        assert abs(total_ratio - 1.0) < 0.001
    
    def test_calculate_confidence_metrics_edge_cases(self):
        """Test confidence metrics with edge cases."""
        # Test empty list
        empty_metrics = ComparisonMetrics.calculate_confidence_metrics([])
        assert empty_metrics == {}
        
        # Test single value
        single_metrics = ComparisonMetrics.calculate_confidence_metrics([0.7])
        assert single_metrics['mean'] == 0.7
        assert single_metrics['median'] == 0.7
        assert single_metrics['std'] == 0.0
        assert single_metrics['min'] == 0.7
        assert single_metrics['max'] == 0.7
        assert single_metrics['medium_confidence_ratio'] == 1.0
        assert single_metrics['high_confidence_ratio'] == 0.0
        assert single_metrics['low_confidence_ratio'] == 0.0
        
        # Test all same values
        same_metrics = ComparisonMetrics.calculate_confidence_metrics([0.5, 0.5, 0.5, 0.5])
        assert same_metrics['mean'] == 0.5
        assert same_metrics['std'] == 0.0
        assert same_metrics['low_confidence_ratio'] == 1.0
        
        # Test extreme values
        extreme_metrics = ComparisonMetrics.calculate_confidence_metrics([0.0, 1.0])
        assert extreme_metrics['min'] == 0.0
        assert extreme_metrics['max'] == 1.0
        assert extreme_metrics['mean'] == 0.5
    
    def test_calculate_diversity_metrics_with_varied_data(self):
        """Test diversity metrics calculation with varied task data."""
        tasks = [
            'Code review', 'Code review', 'Code review',  # 3 instances
            'Write documentation', 'Write documentation',  # 2 instances
            'Debug application',  # 1 instance
            'Team meeting',  # 1 instance
            'Email communication'  # 1 instance
        ]
        
        metrics = ComparisonMetrics.calculate_diversity_metrics(tasks)
        
        # Validate structure
        expected_keys = ['total_items', 'unique_items', 'diversity_ratio', 
                        'entropy', 'most_common', 'distribution']
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"
        
        # Validate basic counts
        assert metrics['total_items'] == 8
        assert metrics['unique_items'] == 5
        assert metrics['diversity_ratio'] == 5/8
        
        # Validate distribution
        expected_distribution = {
            'Code review': 3,
            'Write documentation': 2,
            'Debug application': 1,
            'Team meeting': 1,
            'Email communication': 1
        }
        assert metrics['distribution'] == expected_distribution
        
        # Validate most_common format
        assert isinstance(metrics['most_common'], list)
        assert len(metrics['most_common']) <= 5
        assert metrics['most_common'][0] == ('Code review', 3)
        
        # Validate entropy calculation
        frequencies = [3, 2, 1, 1, 1]
        total = 8
        probabilities = [f/total for f in frequencies]
        expected_entropy = -sum(p * np.log2(p) for p in probabilities)
        assert abs(metrics['entropy'] - expected_entropy) < 0.001
    
    def test_calculate_diversity_metrics_edge_cases(self):
        """Test diversity metrics with edge cases."""
        # Test empty list
        empty_metrics = ComparisonMetrics.calculate_diversity_metrics([])
        assert empty_metrics == {}
        
        # Test single item
        single_metrics = ComparisonMetrics.calculate_diversity_metrics(['Task A'])
        assert single_metrics['total_items'] == 1
        assert single_metrics['unique_items'] == 1
        assert single_metrics['diversity_ratio'] == 1.0
        assert single_metrics['entropy'] == 0.0  # No diversity = 0 entropy
        
        # Test all same items
        same_metrics = ComparisonMetrics.calculate_diversity_metrics(['Task', 'Task', 'Task'])
        assert same_metrics['unique_items'] == 1
        assert same_metrics['diversity_ratio'] == 1/3
        assert same_metrics['entropy'] == 0.0
        
        # Test maximum diversity (all unique)
        unique_metrics = ComparisonMetrics.calculate_diversity_metrics(['A', 'B', 'C', 'D'])
        assert unique_metrics['diversity_ratio'] == 1.0
        expected_entropy = -4 * (0.25 * np.log2(0.25))  # Maximum entropy for 4 items
        assert abs(unique_metrics['entropy'] - expected_entropy) < 0.001
    
    def test_calculate_feature_usage_metrics(self):
        """Test feature usage metrics calculation."""
        feature_lists = [
            ['Window Title', 'OCR Text'],
            ['Window Title', 'OCR Text', 'VLM Analysis'],
            ['Window Title'],
            ['Window Title', 'OCR Text', 'VLM Analysis', 'Semantic Search'],
            ['Window Title', 'Layout Analysis']
        ]
        
        metrics = ComparisonMetrics.calculate_feature_usage_metrics(feature_lists)
        
        # Validate structure
        expected_keys = ['total_feature_usages', 'unique_features', 
                        'average_features_per_pipeline', 'feature_frequency', 'most_used_features']
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"
        
        # Calculate expected values
        all_features = []
        for features in feature_lists:
            all_features.extend(features)
        
        expected_total = len(all_features)  # 12 total feature usages
        expected_unique = len(set(all_features))  # 5 unique features
        expected_avg = expected_total / len(feature_lists)  # 12/5 = 2.4
        
        assert metrics['total_feature_usages'] == expected_total
        assert metrics['unique_features'] == expected_unique
        assert abs(metrics['average_features_per_pipeline'] - expected_avg) < 0.001
        
        # Validate frequency counting
        expected_frequency = Counter(all_features)
        assert metrics['feature_frequency'] == dict(expected_frequency)
        
        # Validate most used features
        assert metrics['most_used_features'] == expected_frequency.most_common(10)
    
    def test_calculate_feature_usage_metrics_edge_cases(self):
        """Test feature usage metrics with edge cases."""
        # Test empty list
        empty_metrics = ComparisonMetrics.calculate_feature_usage_metrics([])
        assert empty_metrics == {}
        
        # Test single pipeline with single feature
        single_metrics = ComparisonMetrics.calculate_feature_usage_metrics([['Feature A']])
        assert single_metrics['total_feature_usages'] == 1
        assert single_metrics['unique_features'] == 1
        assert single_metrics['average_features_per_pipeline'] == 1.0
        
        # Test empty feature lists
        empty_features_metrics = ComparisonMetrics.calculate_feature_usage_metrics([[], [], []])
        assert empty_features_metrics['total_feature_usages'] == 0
        assert empty_features_metrics['unique_features'] == 0
        assert empty_features_metrics['average_features_per_pipeline'] == 0.0
    
    def test_compare_pipelines_comprehensive(self):
        """Test comprehensive pipeline comparison."""
        pipeline_results = {
            'basic': [
                {"tasks": 'Task A', 'category': 'Cat1', 'confidence': 0.5, 'features_used': ['Window Title']},
                {"tasks": 'Task B', 'category': 'Cat1', 'confidence': 0.5, 'features_used': ['Window Title']},
                {"tasks": 'Task A', 'category': 'Cat2', 'confidence': 0.5, 'features_used': ['Window Title']}
            ],
            'enhanced': [
                {"tasks": 'Enhanced Task A', 'category': 'Cat1', 'confidence': 0.8, 'features_used': ['Window Title', 'OCR']},
                {"tasks": 'Enhanced Task B', 'category': 'Cat1', 'confidence': 0.9, 'features_used': ['Window Title', 'OCR', 'VLM']},
                {"tasks": 'Enhanced Task C', 'category': 'Cat3', 'confidence': 0.7, 'features_used': ['Window Title', 'OCR']}
            ]
        }
        
        comparison = ComparisonMetrics.compare_pipelines(pipeline_results)
        
        # Validate structure
        assert 'basic' in comparison
        assert 'enhanced' in comparison
        assert 'cross_pipeline' in comparison
        
        # Validate individual pipeline metrics
        for pipeline_name in ['basic', 'enhanced']:
            pipeline_metrics = comparison[pipeline_name]
            assert 'confidence_metrics' in pipeline_metrics
            assert 'task_diversity' in pipeline_metrics
            assert 'category_diversity' in pipeline_metrics
            assert 'feature_usage' in pipeline_metrics
        
        # Validate cross-pipeline comparisons
        cross_pipeline = comparison['cross_pipeline']
        assert 'confidence_ranking' in cross_pipeline
        assert 'diversity_ranking' in cross_pipeline
        
        # Enhanced should rank higher in confidence
        assert cross_pipeline['confidence_ranking'][0] == 'enhanced'
        assert cross_pipeline['confidence_ranking'][1] == 'basic'
        
        # Enhanced should rank higher in diversity (more unique tasks)
        assert cross_pipeline['diversity_ranking'][0] == 'enhanced'
    
    def test_compare_pipelines_edge_cases(self):
        """Test pipeline comparison with edge cases."""
        # Test empty pipeline results
        empty_comparison = ComparisonMetrics.compare_pipelines({})
        assert 'cross_pipeline' in empty_comparison
        assert empty_comparison['cross_pipeline']['confidence_ranking'] == []
        
        # Test pipeline with no results
        mixed_comparison = ComparisonMetrics.compare_pipelines({
            'pipeline_a': [],
            'pipeline_b': [{"tasks": 'Task', 'category': 'Cat', 'confidence': 0.7, 'features_used': ['Feature']}]
        })
        assert 'pipeline_b' in mixed_comparison
        assert 'pipeline_a' not in mixed_comparison  # Empty results filtered out
    
    def test_calculate_improvement_metrics(self):
        """Test improvement metrics calculation between baseline and enhanced results."""
        baseline_results = [
            {'confidence': 0.5},
            {'confidence': 0.4},
            {'confidence': 0.6},
            {'confidence': 0.3},
            {'confidence': 0.5}
        ]
        
        enhanced_results = [
            {'confidence': 0.8},  # +0.3 improvement
            {'confidence': 0.4},  # 0.0 no change
            {'confidence': 0.5},  # -0.1 degradation
            {'confidence': 0.7},  # +0.4 improvement
            {'confidence': 0.9}   # +0.4 improvement
        ]
        
        improvements = ComparisonMetrics.calculate_improvement_metrics(baseline_results, enhanced_results)
        
        # Validate structure
        expected_keys = ['mean_improvement', 'median_improvement', 'std_improvement',
                        'positive_improvements', 'negative_improvements', 'no_change',
                        'improvement_ratio', 'max_improvement', 'min_improvement']
        for key in expected_keys:
            assert key in improvements, f"Missing metric: {key}"
        
        # Calculate expected values
        improvement_values = [0.3, 0.0, -0.1, 0.4, 0.4]
        
        assert abs(improvements['mean_improvement'] - np.mean(improvement_values)) < 0.001
        assert abs(improvements['median_improvement'] - np.median(improvement_values)) < 0.001
        assert abs(improvements['std_improvement'] - np.std(improvement_values)) < 0.001
        
        assert improvements['positive_improvements'] == 3  # 0.3, 0.4, 0.4
        assert improvements['negative_improvements'] == 1   # -0.1
        assert improvements['no_change'] == 1              # 0.0
        assert improvements['improvement_ratio'] == 3/5    # 60% improved
        assert improvements['max_improvement'] == 0.4
        assert abs(improvements['min_improvement'] - (-0.1)) < 0.001  # Handle floating point precision
    
    def test_calculate_improvement_metrics_edge_cases(self):
        """Test improvement metrics with edge cases."""
        # Test mismatched lengths
        baseline = [{'confidence': 0.5}]
        enhanced = [{'confidence': 0.8}, {'confidence': 0.9}]
        
        error_result = ComparisonMetrics.calculate_improvement_metrics(baseline, enhanced)
        assert 'error' in error_result
        assert 'Result sets must have same length' in error_result['error']
        
        # Test empty lists
        empty_result = ComparisonMetrics.calculate_improvement_metrics([], [])
        assert empty_result == {}
        
        # Test single comparison
        single_baseline = [{'confidence': 0.5}]
        single_enhanced = [{'confidence': 0.8}]
        
        single_result = ComparisonMetrics.calculate_improvement_metrics(single_baseline, single_enhanced)
        assert abs(single_result['mean_improvement'] - 0.3) < 0.001
        assert single_result['positive_improvements'] == 1
        assert single_result['negative_improvements'] == 0
        assert single_result['improvement_ratio'] == 1.0
        
        # Test no improvements
        no_improvement_baseline = [{'confidence': 0.8}, {'confidence': 0.9}]
        no_improvement_enhanced = [{'confidence': 0.7}, {'confidence': 0.8}]
        
        no_improvement_result = ComparisonMetrics.calculate_improvement_metrics(
            no_improvement_baseline, no_improvement_enhanced
        )
        assert no_improvement_result['improvement_ratio'] == 0.0
        assert no_improvement_result['positive_improvements'] == 0
        assert no_improvement_result['negative_improvements'] == 2


class TestComparisonMetricsIntegration:
    """Test integration scenarios for comparison metrics."""
    
    def test_real_world_pipeline_comparison_scenario(self):
        """Test a realistic pipeline comparison scenario."""
        # Simulate real pipeline comparison data
        basic_pipeline_results = [
            {"tasks": 'Browse web', 'category': 'Browser', 'confidence': 0.5, 'features_used': ['Window Title']},
            {"tasks": 'Edit document', 'category': 'Productivity', 'confidence': 0.5, 'features_used': ['Window Title']},
            {"tasks": 'Code review', 'category': 'Development', 'confidence': 0.5, 'features_used': ['Window Title']},
            {"tasks": 'Browse web', 'category': 'Browser', 'confidence': 0.5, 'features_used': ['Window Title']},
        ]
        
        ai_enhanced_results = [
            {"tasks": 'Research documentation', 'category': 'Browser', 'confidence': 0.85, 'features_used': ['Window Title', 'OCR', 'VLM']},
            {"tasks": 'Write technical report', 'category': 'Productivity', 'confidence': 0.92, 'features_used': ['Window Title', 'OCR', 'Semantic Search']},
            {"tasks": 'Review Python code', 'category': 'Development', 'confidence': 0.88, 'features_used': ['Window Title', 'OCR', 'VLM', 'Layout Analysis']},
            {"tasks": 'Study API documentation', 'category': 'Browser', 'confidence': 0.79, 'features_used': ['Window Title', 'OCR', 'VLM']},
        ]
        
        pipeline_results = {
            'basic': basic_pipeline_results,
            'ai_enhanced': ai_enhanced_results
        }
        
        # Run comprehensive comparison
        comparison = ComparisonMetrics.compare_pipelines(pipeline_results)
        
        # Validate that AI enhanced performs better
        assert comparison['cross_pipeline']['confidence_ranking'][0] == 'ai_enhanced'
        
        # AI enhanced should have higher diversity (more specific tasks)
        ai_task_diversity = comparison['ai_enhanced']['task_diversity']
        basic_task_diversity = comparison['basic']['task_diversity']
        
        assert ai_task_diversity['unique_items'] >= basic_task_diversity['unique_items']
        assert ai_task_diversity['entropy'] >= basic_task_diversity['entropy']
        
        # AI enhanced should use more features
        ai_feature_usage = comparison['ai_enhanced']['feature_usage']
        basic_feature_usage = comparison['basic']['feature_usage']
        
        assert ai_feature_usage['average_features_per_pipeline'] > basic_feature_usage['average_features_per_pipeline']
        assert ai_feature_usage['unique_features'] > basic_feature_usage['unique_features']
        
        # Calculate improvements
        improvements = ComparisonMetrics.calculate_improvement_metrics(
            basic_pipeline_results, ai_enhanced_results
        )
        
        # Should show significant improvements
        assert improvements['improvement_ratio'] == 1.0  # All improved
        assert improvements['mean_improvement'] > 0.3   # Substantial improvement
        assert improvements['min_improvement'] > 0.2    # Even worst case is good
    
    def test_metrics_statistical_properties(self):
        """Test that metrics have expected statistical properties."""
        # Generate test data with known properties
        np.random.seed(42)  # For reproducible tests
        
        # High variance confidence scores
        high_variance_confidences = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6]
        high_var_metrics = ComparisonMetrics.calculate_confidence_metrics(high_variance_confidences)
        
        # Low variance confidence scores
        low_variance_confidences = [0.48, 0.52, 0.49, 0.51, 0.47, 0.53, 0.50, 0.49]
        low_var_metrics = ComparisonMetrics.calculate_confidence_metrics(low_variance_confidences)
        
        # High variance should have higher standard deviation
        assert high_var_metrics['std'] > low_var_metrics['std']
        
        # Test diversity with known entropy properties
        # Maximum diversity (all unique)
        max_diversity_items = ['A', 'B', 'C', 'D']
        max_div_metrics = ComparisonMetrics.calculate_diversity_metrics(max_diversity_items)
        
        # Minimum diversity (all same)
        min_diversity_items = ['A', 'A', 'A', 'A']
        min_div_metrics = ComparisonMetrics.calculate_diversity_metrics(min_diversity_items)
        
        # Maximum diversity should have higher entropy
        assert max_div_metrics['entropy'] > min_div_metrics['entropy']
        assert max_div_metrics['diversity_ratio'] > min_div_metrics['diversity_ratio']
        assert min_div_metrics['entropy'] == 0.0  # No diversity = 0 entropy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])