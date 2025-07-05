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
                {"tasks": 'Task A', "category": 'Cat1', 'confidence': 0.5, 'features_used': ['Window Title']},
                {"tasks": 'Task B', "category": 'Cat1', 'confidence': 0.5, 'features_used': ['Window Title']},
                {"tasks": 'Task A', "category": 'Cat2', 'confidence': 0.5, 'features_used': ['Window Title']}
            ],
            'enhanced': [
                {"tasks": 'Enhanced Task A', "category": 'Cat1', 'confidence': 0.8, 'features_used': ['Window Title', 'OCR']},
                {"tasks": 'Enhanced Task B', "category": 'Cat1', 'confidence': 0.9, 'features_used': ['Window Title', 'OCR', 'VLM']},
                {"tasks": 'Enhanced Task C', "category": 'Cat3', 'confidence': 0.7, 'features_used': ['Window Title', 'OCR']}
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
            'pipeline_b': [{"tasks": 'Task', "category": 'Cat', 'confidence': 0.7, 'features_used': ['Feature']}]
        })
        assert 'pipeline_b' in mixed_comparison
        assert 'pipeline_a' not in mixed_comparison  # Empty results filtered out
    
    def test_calculate_improvement_metrics(self):
        """Test improvement metrics calculation with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Comparison between baseline and enhanced results
        - Business rules: Improvement thresholds and statistical analysis
        - Realistic data: Real-world confidence score scenarios
        - Integration: Mathematical consistency across metrics
        """
        # Realistic scenario: ML pipeline improvements
        baseline_results = [
            {'confidence': 0.5},  # Basic OCR result
            {'confidence': 0.4},  # Low confidence window title match
            {'confidence': 0.6},  # Moderate confidence result
            {'confidence': 0.3},  # Very low confidence  
            {'confidence': 0.5}   # Another basic result
        ]
        
        enhanced_results = [
            {'confidence': 0.8},  # +0.3 improvement (VLM enhanced)
            {'confidence': 0.4},  # 0.0 no change (same result)
            {'confidence': 0.5},  # -0.1 degradation (edge case)
            {'confidence': 0.7},  # +0.4 improvement (semantic search)
            {'confidence': 0.9}   # +0.4 improvement (multi-modal)
        ]
        
        # State changes: Calculate before and after metrics
        baseline_mean = np.mean([r['confidence'] for r in baseline_results])
        enhanced_mean = np.mean([r['confidence'] for r in enhanced_results])
        
        improvements = ComparisonMetrics.calculate_improvement_metrics(baseline_results, enhanced_results)
        
        # Business rules: Validate improvement measurement accuracy
        expected_keys = ['mean_improvement', 'median_improvement', 'std_improvement',
                        'positive_improvements', 'negative_improvements', 'no_change',
                        'improvement_ratio', 'max_improvement', 'min_improvement']
        for key in expected_keys:
            assert key in improvements, f"Missing metric: {key}"
        
        # Realistic data: Verify mathematical correctness
        improvement_values = [0.3, 0.0, -0.1, 0.4, 0.4]
        
        assert abs(improvements['mean_improvement'] - np.mean(improvement_values)) < 0.001
        assert abs(improvements['median_improvement'] - np.median(improvement_values)) < 0.001
        assert abs(improvements['std_improvement'] - np.std(improvement_values)) < 0.001
        
        # Business rules: Improvement categorization
        assert improvements['positive_improvements'] == 3, "Should count 3 positive improvements"
        assert improvements['negative_improvements'] == 1, "Should count 1 degradation"
        assert improvements['no_change'] == 1, "Should count 1 unchanged result"
        assert improvements['improvement_ratio'] == 0.6, "Should show 60% improvement rate"
        assert improvements['max_improvement'] == 0.4, "Maximum improvement should be 0.4"
        assert abs(improvements['min_improvement'] - (-0.1)) < 0.001, "Minimum should be -0.1"
        
        # Integration: Verify metric consistency
        total_classified = (improvements['positive_improvements'] + 
                          improvements['negative_improvements'] + 
                          improvements['no_change'])
        assert total_classified == len(baseline_results), "All results should be classified"
        
        # Validate overall improvement direction
        overall_improvement = enhanced_mean - baseline_mean
        assert overall_improvement > 0, "Enhanced results should have higher mean confidence"
        assert abs(improvements['mean_improvement'] - overall_improvement) < 0.001, "Mean improvement should match overall change"
    
    def test_calculate_improvement_metrics_edge_cases(self):
        """Test improvement metrics edge cases with comprehensive validation.
        
        Enhanced test validates:
        - Error handling: Invalid input scenarios and graceful degradation
        - Boundary conditions: Empty data, single data points, extreme values
        - Business rules: Edge case metric calculations and consistency
        """
        # Error handling: Test mismatched lengths
        baseline = [{'confidence': 0.5}]
        enhanced = [{'confidence': 0.8}, {'confidence': 0.9}]
        
        error_result = ComparisonMetrics.calculate_improvement_metrics(baseline, enhanced)
        assert 'error' in error_result, "Should return error for mismatched lengths"
        assert 'Result sets must have same length' in error_result['error']
        
        # Boundary conditions: Test empty lists
        empty_result = ComparisonMetrics.calculate_improvement_metrics([], [])
        assert empty_result == {}, "Empty inputs should return empty result"
        
        # Boundary conditions: Test single comparison
        single_baseline = [{'confidence': 0.5}]
        single_enhanced = [{'confidence': 0.8}]
        
        single_result = ComparisonMetrics.calculate_improvement_metrics(single_baseline, single_enhanced)
        assert abs(single_result['mean_improvement'] - 0.3) < 0.001, "Single improvement should be 0.3"
        assert single_result['positive_improvements'] == 1, "Should count 1 positive improvement"
        assert single_result['negative_improvements'] == 0, "Should count 0 negative improvements"
        assert single_result['improvement_ratio'] == 1.0, "Should show 100% improvement"
        assert single_result['median_improvement'] == 0.3, "Median of single value should equal the value"
        assert single_result['std_improvement'] == 0.0, "Standard deviation of single value should be 0"
        
        # Business rules: Test complete degradation scenario
        degradation_baseline = [{'confidence': 0.8}, {'confidence': 0.9}]
        degradation_enhanced = [{'confidence': 0.7}, {'confidence': 0.8}]
        
        degradation_result = ComparisonMetrics.calculate_improvement_metrics(
            degradation_baseline, degradation_enhanced
        )
        assert degradation_result['improvement_ratio'] == 0.0, "Should show 0% improvement"
        assert degradation_result['positive_improvements'] == 0, "Should count 0 positive improvements"
        assert degradation_result['negative_improvements'] == 2, "Should count 2 degradations"
        assert degradation_result['mean_improvement'] < 0, "Mean improvement should be negative"
        assert degradation_result['max_improvement'] < 0, "Even max should be negative in degradation"
        
        # Boundary conditions: Test extreme improvement scenario
        extreme_baseline = [{'confidence': 0.1}, {'confidence': 0.2}]
        extreme_enhanced = [{'confidence': 0.9}, {'confidence': 1.0}]
        
        extreme_result = ComparisonMetrics.calculate_improvement_metrics(extreme_baseline, extreme_enhanced)
        assert extreme_result['improvement_ratio'] == 1.0, "Should show 100% improvement"
        assert extreme_result['mean_improvement'] == 0.8, "Should show large mean improvement"
        assert extreme_result['min_improvement'] == 0.8, "All improvements should be substantial"
        
        # Business rules: Test perfect baseline scenario
        perfect_baseline = [{'confidence': 1.0}, {'confidence': 1.0}]
        worse_enhanced = [{'confidence': 0.9}, {'confidence': 0.8}]
        
        perfect_result = ComparisonMetrics.calculate_improvement_metrics(perfect_baseline, worse_enhanced)
        assert perfect_result['improvement_ratio'] == 0.0, "Perfect baseline should show no improvement"
        assert perfect_result['max_improvement'] < 0, "All changes should be degradations"


class TestComparisonMetricsIntegration:
    """Test integration scenarios for comparison metrics."""
    
    def test_real_world_pipeline_comparison_scenario(self):
        """Test a realistic pipeline comparison scenario."""
        # Simulate real pipeline comparison data
        basic_pipeline_results = [
            {"tasks": 'Browse web', "category": 'Browser', 'confidence': 0.5, 'features_used': ['Window Title']},
            {"tasks": 'Edit document', "category": 'Productivity', 'confidence': 0.5, 'features_used': ['Window Title']},
            {"tasks": 'Code review', "category": 'Development', 'confidence': 0.5, 'features_used': ['Window Title']},
            {"tasks": 'Browse web', "category": 'Browser', 'confidence': 0.5, 'features_used': ['Window Title']},
        ]
        
        ai_enhanced_results = [
            {"tasks": 'Research documentation', "category": 'Browser', 'confidence': 0.85, 'features_used': ['Window Title', 'OCR', 'VLM']},
            {"tasks": 'Write technical report', "category": 'Productivity', 'confidence': 0.92, 'features_used': ['Window Title', 'OCR', 'Semantic Search']},
            {"tasks": 'Review Python code', "category": 'Development', 'confidence': 0.88, 'features_used': ['Window Title', 'OCR', 'VLM', 'Layout Analysis']},
            {"tasks": 'Study API documentation', "category": 'Browser', 'confidence': 0.79, 'features_used': ['Window Title', 'OCR', 'VLM']},
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
        """Test metrics statistical properties with comprehensive validation.
        
        Enhanced test validates:
        - Business rules: Statistical relationships and mathematical properties
        - Realistic data: Representative confidence and diversity scenarios
        - Integration: Cross-metric consistency and mathematical soundness
        """
        # Generate test data with known properties for reproducible tests
        np.random.seed(42)
        
        # Business rules: Test variance relationships
        # High variance confidence scores (erratic ML pipeline)
        high_variance_confidences = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6]
        high_var_metrics = ComparisonMetrics.calculate_confidence_metrics(high_variance_confidences)
        
        # Low variance confidence scores (stable ML pipeline)
        low_variance_confidences = [0.48, 0.52, 0.49, 0.51, 0.47, 0.53, 0.50, 0.49]
        low_var_metrics = ComparisonMetrics.calculate_confidence_metrics(low_variance_confidences)
        
        # Business rules: Variance should correlate with standard deviation
        assert high_var_metrics['std'] > low_var_metrics['std'], "High variance data should have higher std dev"
        assert high_var_metrics['std'] > 0.2, "High variance should be substantial"
        assert low_var_metrics['std'] < 0.05, "Low variance should be minimal"
        
        # Realistic data: Test confidence distribution properties
        # High variance should have wider confidence distribution
        high_var_range = high_var_metrics['max'] - high_var_metrics['min']
        low_var_range = low_var_metrics['max'] - low_var_metrics['min']
        assert high_var_range > low_var_range, "High variance should have wider range"
        
        # Test confidence ratios make sense for different distributions
        assert high_var_metrics['high_confidence_ratio'] > 0, "High variance data should have some high confidence"
        assert high_var_metrics['low_confidence_ratio'] > 0, "High variance data should have some low confidence"
        
        # Integration: Test diversity entropy properties
        # Maximum diversity (all unique tasks)
        max_diversity_items = ['Code Review', 'Documentation', 'Testing', 'Debugging']
        max_div_metrics = ComparisonMetrics.calculate_diversity_metrics(max_diversity_items)
        
        # Minimum diversity (repetitive tasks)
        min_diversity_items = ['Email', 'Email', 'Email', 'Email']
        min_div_metrics = ComparisonMetrics.calculate_diversity_metrics(min_diversity_items)
        
        # Business rules: Entropy relationships
        assert max_div_metrics['entropy'] > min_div_metrics['entropy'], "Unique tasks should have higher entropy"
        assert max_div_metrics['diversity_ratio'] > min_div_metrics['diversity_ratio'], "Unique tasks should have higher diversity ratio"
        assert min_div_metrics['entropy'] == 0.0, "Identical items should have zero entropy"
        assert max_div_metrics['diversity_ratio'] == 1.0, "All unique items should have diversity ratio of 1.0"
        assert min_div_metrics['diversity_ratio'] == 0.25, "4 identical items should have diversity ratio of 1/4"
        
        # Integration: Mathematical soundness checks
        # Entropy should be bounded by log2(unique_items)
        max_possible_entropy = np.log2(max_div_metrics['unique_items'])
        assert max_div_metrics['entropy'] <= max_possible_entropy + 0.001, "Entropy should not exceed theoretical maximum"
        
        # Test with realistic intermediate diversity
        mixed_diversity_items = ['Code', 'Code', 'Meeting', 'Email', 'Email', 'Email']
        mixed_div_metrics = ComparisonMetrics.calculate_diversity_metrics(mixed_diversity_items)
        
        # Should be between extremes
        assert min_div_metrics['entropy'] < mixed_div_metrics['entropy'] < max_div_metrics['entropy'], "Mixed diversity should be between extremes"
        assert min_div_metrics['diversity_ratio'] < mixed_div_metrics['diversity_ratio'] < max_div_metrics['diversity_ratio'], "Mixed diversity ratio should be between extremes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])