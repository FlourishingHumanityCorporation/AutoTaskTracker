"""
Metrics for comparing pipeline performance.
"""
from typing import Dict, List, Any
from collections import Counter
import numpy as np


class ComparisonMetrics:
    """Metrics for comparing pipeline performance."""
    
    @staticmethod
    def calculate_confidence_metrics(confidences: List[float]) -> Dict[str, float]:
        """Calculate confidence-related metrics."""
        if not confidences:
            return {}
        
        return {
            'mean': np.mean(confidences),
            'median': np.median(confidences),
            'std': np.std(confidences),
            'min': np.min(confidences),
            'max': np.max(confidences),
            'high_confidence_ratio': sum(1 for c in confidences if c >= 0.8) / len(confidences),
            'medium_confidence_ratio': sum(1 for c in confidences if 0.6 <= c < 0.8) / len(confidences),
            'low_confidence_ratio': sum(1 for c in confidences if c < 0.6) / len(confidences)
        }
    
    @staticmethod
    def calculate_diversity_metrics(items: List[str]) -> Dict[str, Any]:
        """Calculate diversity metrics for tasks or categories."""
        if not items:
            return {}
        
        counter = Counter(items)
        unique_count = len(counter)
        total_count = len(items)
        
        # Calculate entropy
        frequencies = list(counter.values())
        probabilities = [f / total_count for f in frequencies]
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
        
        return {
            'total_items': total_count,
            'unique_items': unique_count,
            'diversity_ratio': unique_count / total_count,
            'entropy': entropy,
            'most_common': counter.most_common(5),
            'distribution': dict(counter)
        }
    
    @staticmethod
    def calculate_feature_usage_metrics(feature_lists: List[List[str]]) -> Dict[str, Any]:
        """Calculate metrics for feature usage across pipelines."""
        if not feature_lists:
            return {}
        
        all_features = []
        for features in feature_lists:
            all_features.extend(features)
        
        feature_counter = Counter(all_features)
        total_usage = len(feature_lists)
        
        return {
            'total_feature_usages': len(all_features),
            'unique_features': len(feature_counter),
            'average_features_per_pipeline': len(all_features) / total_usage,
            'feature_frequency': dict(feature_counter),
            'most_used_features': feature_counter.most_common(10)
        }
    
    @staticmethod
    def compare_pipelines(pipeline_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Compare multiple pipelines across various metrics."""
        comparison = {}
        
        for pipeline_name, results in pipeline_results.items():
            if not results:
                continue
            
            confidences = [r['confidence'] for r in results]
            tasks = [r["tasks"] for r in results]
            categories = [r["category"] for r in results]
            features = [r['features_used'] for r in results]
            
            comparison[pipeline_name] = {
                'confidence_metrics': ComparisonMetrics.calculate_confidence_metrics(confidences),
                'task_diversity': ComparisonMetrics.calculate_diversity_metrics(tasks),
                'category_diversity': ComparisonMetrics.calculate_diversity_metrics(categories),
                'feature_usage': ComparisonMetrics.calculate_feature_usage_metrics(features)
            }
        
        # Add cross-pipeline comparisons
        comparison['cross_pipeline'] = {
            'confidence_ranking': sorted(
                pipeline_results.keys(),
                key=lambda p: np.mean([r['confidence'] for r in pipeline_results[p]]) if pipeline_results[p] else 0,
                reverse=True
            ),
            'diversity_ranking': sorted(
                pipeline_results.keys(),
                key=lambda p: len(set(r["tasks"] for r in pipeline_results[p])) if pipeline_results[p] else 0,
                reverse=True
            )
        }
        
        return comparison
    
    @staticmethod
    def calculate_improvement_metrics(baseline_results: List[Dict[str, Any]], 
                                    enhanced_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate improvement metrics between two sets of results."""
        if len(baseline_results) != len(enhanced_results):
            return {'error': 'Result sets must have same length'}
        
        improvements = []
        for baseline, enhanced in zip(baseline_results, enhanced_results):
            improvement = enhanced['confidence'] - baseline['confidence']
            improvements.append(improvement)
        
        if not improvements:
            return {}
        
        return {
            'mean_improvement': np.mean(improvements),
            'median_improvement': np.median(improvements),
            'std_improvement': np.std(improvements),
            'positive_improvements': sum(1 for imp in improvements if imp > 0),
            'negative_improvements': sum(1 for imp in improvements if imp < 0),
            'no_change': sum(1 for imp in improvements if imp == 0),
            'improvement_ratio': sum(1 for imp in improvements if imp > 0) / len(improvements),
            'max_improvement': max(improvements),
            'min_improvement': min(improvements)
        }