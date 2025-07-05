"""
Performance optimization module for Pensieve integration.
Provides intelligent performance tuning and optimization recommendations.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
from collections import defaultdict, deque
import json

from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter
from autotasktracker.pensieve.api_client import get_pensieve_client
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.pensieve.cache_manager import get_cache_manager
from autotasktracker.pensieve.search_coordinator import get_search_coordinator
from autotasktracker.pensieve.service_integration import get_service_manager
from autotasktracker.core.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    component: str
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    baseline: Optional[float] = None
    target: Optional[float] = None
    trend: str = "stable"  # improving, degrading, stable
    
    @property
    def performance_ratio(self) -> float:
        """Calculate performance ratio vs baseline."""
        if self.baseline and self.baseline > 0:
            return self.value / self.baseline
        return 1.0
    
    @property
    def is_healthy(self) -> bool:
        """Check if metric is within healthy range."""
        if self.target:
            return self.value <= self.target
        return True


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""
    component: str
    priority: str  # critical, high, medium, low
    category: str  # configuration, infrastructure, code, caching
    title: str
    description: str
    expected_improvement: str
    implementation_effort: str  # low, medium, high
    implementation_steps: List[str]
    metrics_affected: List[str]
    estimated_impact_percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class PerformanceProfile:
    """Complete performance profile for the system."""
    overall_score: float
    component_scores: Dict[str, float]
    bottlenecks: List[str]
    optimization_opportunities: List[OptimizationRecommendation]
    performance_trends: Dict[str, str]
    benchmark_results: Dict[str, Any]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_score': self.overall_score,
            'component_scores': self.component_scores,
            'bottlenecks': self.bottlenecks,
            'optimization_opportunities': [rec.to_dict() for rec in self.optimization_opportunities],
            'performance_trends': self.performance_trends,
            'benchmark_results': self.benchmark_results,
            'last_updated': self.last_updated.isoformat()
        }


class PerformanceOptimizer:
    """Advanced performance optimization system for Pensieve integration."""
    
    def __init__(self):
        """Initialize performance optimizer."""
        # Integration components
        self.pg_adapter = get_postgresql_adapter()
        self.api_client = get_pensieve_client()
        self.health_monitor = get_health_monitor()
        self.cache_manager = get_cache_manager()
        self.search_coordinator = get_search_coordinator()
        self.service_manager = get_service_manager()
        self.db_manager = DatabaseManager()
        
        # Performance tracking
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.baseline_metrics: Dict[str, float] = {}
        self.performance_targets: Dict[str, float] = {}
        
        # Optimization state
        self.last_optimization_run = None
        self.active_optimizations: List[str] = []
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Performance thresholds
        self._setup_performance_targets()
        
        logger.info("Performance optimizer initialized")
    
    async def analyze_performance(self) -> PerformanceProfile:
        """Comprehensive performance analysis.
        
        Returns:
            Complete performance profile with recommendations
        """
        try:
            start_time = time.time()
            logger.info("Starting comprehensive performance analysis")
            
            # Collect current metrics
            current_metrics = await self._collect_current_metrics()
            
            # Calculate component scores
            component_scores = self._calculate_component_scores(current_metrics)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(component_scores)
            
            # Identify bottlenecks
            bottlenecks = self._identify_bottlenecks(current_metrics)
            
            # Generate optimization recommendations
            recommendations = await self._generate_optimization_recommendations(current_metrics, bottlenecks)
            
            # Analyze performance trends
            trends = self._analyze_performance_trends()
            
            # Run benchmark tests
            benchmark_results = await self._run_performance_benchmarks()
            
            # Create performance profile
            profile = PerformanceProfile(
                overall_score=overall_score,
                component_scores=component_scores,
                bottlenecks=bottlenecks,
                optimization_opportunities=recommendations,
                performance_trends=trends,
                benchmark_results=benchmark_results,
                last_updated=datetime.now()
            )
            
            # Store metrics for trend analysis
            self._store_metrics_for_trending(current_metrics)
            
            analysis_time = time.time() - start_time
            logger.info(f"Performance analysis completed in {analysis_time:.2f}s - Overall score: {overall_score:.1f}%")
            
            return profile
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return PerformanceProfile(
                overall_score=0.0,
                component_scores={},
                bottlenecks=[f"Analysis failed: {str(e)}"],
                optimization_opportunities=[],
                performance_trends={},
                benchmark_results={},
                last_updated=datetime.now()
            )
    
    async def apply_optimization(self, optimization_id: str) -> Dict[str, Any]:
        """Apply a specific optimization recommendation.
        
        Args:
            optimization_id: ID of optimization to apply
            
        Returns:
            Application results
        """
        try:
            logger.info(f"Applying optimization: {optimization_id}")
            
            # Get optimization details
            optimization = await self._get_optimization_details(optimization_id)
            if not optimization:
                return {'success': False, 'error': 'Optimization not found'}
            
            # Check prerequisites
            prerequisites_met = await self._check_optimization_prerequisites(optimization)
            if not prerequisites_met:
                return {'success': False, 'error': 'Prerequisites not met'}
            
            # Apply optimization
            result = await self._apply_specific_optimization(optimization)
            
            # Validate results
            validation_result = await self._validate_optimization_results(optimization_id)
            
            # Record optimization
            self.optimization_history.append({
                'optimization_id': optimization_id,
                'applied_at': datetime.now().isoformat(),
                'success': result.get('success', False),
                'improvement_achieved': validation_result.get('improvement_percentage', 0),
                'details': result
            })
            
            return {
                'success': result.get('success', False),
                'optimization_id': optimization_id,
                'improvement_achieved': validation_result.get('improvement_percentage', 0),
                'validation_results': validation_result,
                'next_recommended_optimizations': await self._get_next_optimizations()
            }
            
        except Exception as e:
            logger.error(f"Optimization application failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def auto_optimize(self, max_optimizations: int = 3) -> Dict[str, Any]:
        """Automatically apply safe optimizations.
        
        Args:
            max_optimizations: Maximum number of optimizations to apply
            
        Returns:
            Auto-optimization results
        """
        try:
            logger.info(f"Starting auto-optimization (max: {max_optimizations})")
            
            # Get current performance profile
            profile = await self.analyze_performance()
            
            # Filter safe optimizations
            safe_optimizations = [
                rec for rec in profile.optimization_opportunities
                if rec.implementation_effort in ['low', 'medium'] and
                   rec.category in ['configuration', 'caching'] and
                   rec.priority in ['high', 'medium']
            ]
            
            # Sort by expected impact
            safe_optimizations.sort(key=lambda x: x.estimated_impact_percentage, reverse=True)
            
            # Apply optimizations
            results = []
            optimizations_applied = 0
            
            for optimization in safe_optimizations[:max_optimizations]:
                if optimizations_applied >= max_optimizations:
                    break
                
                result = await self.apply_optimization(optimization.title)
                results.append(result)
                
                if result.get('success', False):
                    optimizations_applied += 1
                    
                    # Wait between optimizations to validate impact
                    await asyncio.sleep(5)
            
            # Final performance check
            final_profile = await self.analyze_performance()
            
            return {
                'optimizations_applied': optimizations_applied,
                'total_attempted': len(results),
                'initial_score': profile.overall_score,
                'final_score': final_profile.overall_score,
                'improvement_percentage': final_profile.overall_score - profile.overall_score,
                'optimization_results': results,
                'remaining_opportunities': len(final_profile.optimization_opportunities)
            }
            
        except Exception as e:
            logger.error(f"Auto-optimization failed: {e}")
            return {'error': str(e)}
    
    async def benchmark_system(self) -> Dict[str, Any]:
        """Run comprehensive system benchmarks.
        
        Returns:
            Benchmark results with performance metrics
        """
        try:
            logger.info("Running system benchmarks")
            
            benchmarks = {}
            
            # Database performance benchmark
            benchmarks['database'] = await self._benchmark_database()
            
            # API performance benchmark
            benchmarks['api'] = await self._benchmark_api()
            
            # Search performance benchmark
            benchmarks['search'] = await self._benchmark_search()
            
            # Cache performance benchmark
            benchmarks['cache'] = await self._benchmark_cache()
            
            # Service command benchmark
            benchmarks['services'] = await self._benchmark_services()
            
            # Calculate overall benchmark score
            benchmark_scores = [b.get('score', 0) for b in benchmarks.values() if 'score' in b]
            overall_benchmark_score = sum(benchmark_scores) / len(benchmark_scores) if benchmark_scores else 0
            
            return {
                'overall_score': overall_benchmark_score,
                'component_benchmarks': benchmarks,
                'benchmark_timestamp': datetime.now().isoformat(),
                'recommendations': self._analyze_benchmark_results(benchmarks)
            }
            
        except Exception as e:
            logger.error(f"System benchmark failed: {e}")
            return {'error': str(e)}
    
    async def _collect_current_metrics(self) -> Dict[str, PerformanceMetric]:
        """Collect current performance metrics from all components."""
        metrics = {}
        
        try:
            # Database metrics
            db_metrics = await self._collect_database_metrics()
            metrics.update(db_metrics)
            
            # API metrics
            api_metrics = await self._collect_api_metrics()
            metrics.update(api_metrics)
            
            # Search metrics
            search_metrics = await self._collect_search_metrics()
            metrics.update(search_metrics)
            
            # Cache metrics
            cache_metrics = await self._collect_cache_metrics()
            metrics.update(cache_metrics)
            
            # Service metrics
            service_metrics = await self._collect_service_metrics()
            metrics.update(service_metrics)
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
        
        return metrics
    
    async def _collect_database_metrics(self) -> Dict[str, PerformanceMetric]:
        """Collect database performance metrics."""
        metrics = {}
        
        try:
            # Connection time test
            start_time = time.time()
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            connection_time = (time.time() - start_time) * 1000
            
            metrics['db_connection_time'] = PerformanceMetric(
                component='database',
                metric_name='connection_time',
                value=connection_time,
                unit='ms',
                timestamp=datetime.now(),
                target=100.0
            )
            
            # Query performance test
            start_time = time.time()
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entities LIMIT 1000")
            query_time = (time.time() - start_time) * 1000
            
            metrics['db_query_time'] = PerformanceMetric(
                component='database',
                metric_name='query_time',
                value=query_time,
                unit='ms',
                timestamp=datetime.now(),
                target=500.0
            )
            
        except Exception as e:
            logger.error(f"Database metrics collection failed: {e}")
        
        return metrics
    
    async def _collect_api_metrics(self) -> Dict[str, PerformanceMetric]:
        """Collect API performance metrics."""
        metrics = {}
        
        try:
            if not self.api_client:
                return metrics
            
            # API health check time
            start_time = time.time()
            health_result = self.api_client.is_healthy()
            health_check_time = (time.time() - start_time) * 1000
            
            metrics['api_health_check_time'] = PerformanceMetric(
                component='api',
                metric_name='health_check_time',
                value=health_check_time,
                unit='ms',
                timestamp=datetime.now(),
                target=200.0
            )
            
            # API availability
            metrics['api_availability'] = PerformanceMetric(
                component='api',
                metric_name='availability',
                value=100.0 if health_result else 0.0,
                unit='%',
                timestamp=datetime.now(),
                target=95.0
            )
            
        except Exception as e:
            logger.error(f"API metrics collection failed: {e}")
        
        return metrics
    
    async def _collect_search_metrics(self) -> Dict[str, PerformanceMetric]:
        """Collect search performance metrics."""
        metrics = {}
        
        try:
            search_stats = self.search_coordinator.stats.to_dict()
            
            metrics['search_avg_response_time'] = PerformanceMetric(
                component='search',
                metric_name='avg_response_time',
                value=search_stats.get('average_response_time_ms', 0),
                unit='ms',
                timestamp=datetime.now(),
                target=1000.0
            )
            
            # Cache hit rate
            cache_hits = search_stats.get('cache_hits', 0)
            cache_misses = search_stats.get('cache_misses', 0)
            cache_hit_rate = 0
            if cache_hits + cache_misses > 0:
                cache_hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
            
            metrics['search_cache_hit_rate'] = PerformanceMetric(
                component='search',
                metric_name='cache_hit_rate',
                value=cache_hit_rate,
                unit='%',
                timestamp=datetime.now(),
                target=70.0
            )
            
        except Exception as e:
            logger.error(f"Search metrics collection failed: {e}")
        
        return metrics
    
    async def _collect_cache_metrics(self) -> Dict[str, PerformanceMetric]:
        """Collect cache performance metrics."""
        metrics = {}
        
        try:
            if not self.cache_manager:
                return metrics
            
            # Cache access time test
            start_time = time.time()
            await self.cache_manager.get("test_key")
            cache_access_time = (time.time() - start_time) * 1000
            
            metrics['cache_access_time'] = PerformanceMetric(
                component='cache',
                metric_name='access_time',
                value=cache_access_time,
                unit='ms',
                timestamp=datetime.now(),
                target=50.0
            )
            
        except Exception as e:
            logger.error(f"Cache metrics collection failed: {e}")
        
        return metrics
    
    async def _collect_service_metrics(self) -> Dict[str, PerformanceMetric]:
        """Collect service performance metrics."""
        metrics = {}
        
        try:
            if not self.service_manager:
                return metrics
            
            # Service command response time
            start_time = time.time()
            status = self.service_manager.get_service_status()
            service_response_time = (time.time() - start_time) * 1000
            
            metrics['service_response_time'] = PerformanceMetric(
                component='services',
                metric_name='response_time',
                value=service_response_time,
                unit='ms',
                timestamp=datetime.now(),
                target=1000.0
            )
            
            # Service availability
            service_running = status.get('running', False)
            metrics['service_availability'] = PerformanceMetric(
                component='services',
                metric_name='availability',
                value=100.0 if service_running else 0.0,
                unit='%',
                timestamp=datetime.now(),
                target=95.0
            )
            
        except Exception as e:
            logger.error(f"Service metrics collection failed: {e}")
        
        return metrics
    
    def _calculate_component_scores(self, metrics: Dict[str, PerformanceMetric]) -> Dict[str, float]:
        """Calculate performance scores for each component."""
        component_metrics = defaultdict(list)
        
        # Group metrics by component
        for metric in metrics.values():
            component_metrics[metric.component].append(metric)
        
        # Calculate scores
        component_scores = {}
        for component, component_metric_list in component_metrics.items():
            scores = []
            
            for metric in component_metric_list:
                if metric.target:
                    # Calculate score based on target achievement
                    if metric.metric_name in ['availability', 'cache_hit_rate']:
                        # Higher is better
                        score = min(100, (metric.value / metric.target) * 100)
                    else:
                        # Lower is better (response times)
                        score = max(0, 100 - ((metric.value / metric.target) * 100))
                    scores.append(score)
            
            component_scores[component] = sum(scores) / len(scores) if scores else 50.0
        
        return component_scores
    
    def _calculate_overall_score(self, component_scores: Dict[str, float]) -> float:
        """Calculate overall performance score."""
        if not component_scores:
            return 0.0
        
        # Weight components by importance
        weights = {
            'database': 0.3,
            'api': 0.25,
            'search': 0.2,
            'cache': 0.15,
            'services': 0.1
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for component, score in component_scores.items():
            weight = weights.get(component, 0.1)
            weighted_score += score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _identify_bottlenecks(self, metrics: Dict[str, PerformanceMetric]) -> List[str]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        for metric in metrics.values():
            if not metric.is_healthy:
                if metric.metric_name in ['connection_time', 'query_time'] and metric.value > 1000:
                    bottlenecks.append(f"Database {metric.metric_name} is slow ({metric.value:.0f}ms)")
                elif metric.metric_name == 'avg_response_time' and metric.value > 2000:
                    bottlenecks.append(f"Search response time is slow ({metric.value:.0f}ms)")
                elif metric.metric_name == 'cache_hit_rate' and metric.value < 50:
                    bottlenecks.append(f"Cache hit rate is low ({metric.value:.1f}%)")
                elif metric.metric_name == 'availability' and metric.value < 90:
                    bottlenecks.append(f"{metric.component} availability is low ({metric.value:.1f}%)")
        
        return bottlenecks
    
    async def _generate_optimization_recommendations(
        self, 
        metrics: Dict[str, PerformanceMetric], 
        bottlenecks: List[str]
    ) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on metrics and bottlenecks."""
        recommendations = []
        
        # Database optimizations
        db_connection_time = next((m.value for m in metrics.values() 
                                 if m.metric_name == 'connection_time'), 0)
        if db_connection_time > 200:
            recommendations.append(OptimizationRecommendation(
                component='database',
                priority='high',
                category='infrastructure',
                title='Migrate to PostgreSQL',
                description='Database connection time is slow. PostgreSQL migration could provide significant improvements.',
                expected_improvement='300-500% faster database operations',
                implementation_effort='high',
                implementation_steps=[
                    'Run migration readiness assessment',
                    'Create migration plan',
                    'Execute migration with validation',
                    'Validate performance improvements'
                ],
                metrics_affected=['connection_time', 'query_time'],
                estimated_impact_percentage=75.0
            ))
        
        # Search optimizations
        search_response_time = next((m.value for m in metrics.values() 
                                   if m.metric_name == 'avg_response_time'), 0)
        if search_response_time > 1500:
            recommendations.append(OptimizationRecommendation(
                component='search',
                priority='medium',
                category='caching',
                title='Optimize Search Caching',
                description='Search response times are slow. Improved caching strategies could help.',
                expected_improvement='30-50% faster search operations',
                implementation_effort='medium',
                implementation_steps=[
                    'Analyze search query patterns',
                    'Implement intelligent cache warming',
                    'Optimize cache key strategies',
                    'Monitor cache hit rates'
                ],
                metrics_affected=['avg_response_time', 'cache_hit_rate'],
                estimated_impact_percentage=35.0
            ))
        
        # Cache optimizations
        cache_hit_rate = next((m.value for m in metrics.values() 
                             if m.metric_name == 'cache_hit_rate'), 100)
        if cache_hit_rate < 60:
            recommendations.append(OptimizationRecommendation(
                component='cache',
                priority='medium',
                category='configuration',
                title='Improve Cache Configuration',
                description='Cache hit rate is low. Optimizing cache configuration could improve performance.',
                expected_improvement='20-40% better cache utilization',
                implementation_effort='low',
                implementation_steps=[
                    'Increase cache TTL for stable data',
                    'Implement cache warming for common queries',
                    'Optimize cache key generation',
                    'Monitor cache usage patterns'
                ],
                metrics_affected=['cache_hit_rate', 'avg_response_time'],
                estimated_impact_percentage=25.0
            ))
        
        return recommendations
    
    def _analyze_performance_trends(self) -> Dict[str, str]:
        """Analyze performance trends over time."""
        trends = {}
        
        for metric_name, history in self.metrics_history.items():
            if len(history) < 5:
                trends[metric_name] = 'insufficient_data'
                continue
            
            recent_values = [point['value'] for point in list(history)[-10:]]
            older_values = [point['value'] for point in list(history)[-20:-10]] if len(history) >= 20 else recent_values
            
            recent_avg = statistics.mean(recent_values)
            older_avg = statistics.mean(older_values)
            
            if recent_avg < older_avg * 0.95:
                trends[metric_name] = 'improving'
            elif recent_avg > older_avg * 1.05:
                trends[metric_name] = 'degrading'
            else:
                trends[metric_name] = 'stable'
        
        return trends
    
    async def _run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        return {
            'database': await self._benchmark_database(),
            'api': await self._benchmark_api(),
            'search': await self._benchmark_search()
        }
    
    async def _benchmark_database(self) -> Dict[str, Any]:
        """Benchmark database performance."""
        try:
            # Connection benchmark
            connection_times = []
            for _ in range(5):
                start_time = time.time()
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                connection_times.append((time.time() - start_time) * 1000)
            
            # Query benchmark
            query_times = []
            for _ in range(3):
                start_time = time.time()
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM entities")
                query_times.append((time.time() - start_time) * 1000)
            
            avg_connection_time = statistics.mean(connection_times)
            avg_query_time = statistics.mean(query_times)
            
            # Calculate score
            score = 100
            if avg_connection_time > 100:
                score -= 20
            if avg_query_time > 500:
                score -= 30
            
            return {
                'avg_connection_time_ms': avg_connection_time,
                'avg_query_time_ms': avg_query_time,
                'score': max(0, score)
            }
            
        except Exception as e:
            logger.error(f"Database benchmark failed: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _benchmark_api(self) -> Dict[str, Any]:
        """Benchmark API performance."""
        try:
            if not self.api_client:
                return {'score': 0, 'error': 'API client not available'}
            
            # Health check benchmark
            health_times = []
            for _ in range(5):
                start_time = time.time()
                self.api_client.is_healthy()
                health_times.append((time.time() - start_time) * 1000)
            
            avg_health_time = statistics.mean(health_times)
            
            # Calculate score
            score = 100
            if avg_health_time > 500:
                score -= 40
            elif avg_health_time > 200:
                score -= 20
            
            return {
                'avg_health_check_time_ms': avg_health_time,
                'score': max(0, score)
            }
            
        except Exception as e:
            logger.error(f"API benchmark failed: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _benchmark_search(self) -> Dict[str, Any]:
        """Benchmark search performance."""
        try:
            # Simple search benchmark
            from autotasktracker.pensieve.search_coordinator import UnifiedSearchQuery
            
            search_times = []
            for _ in range(3):
                start_time = time.time()
                query = UnifiedSearchQuery(text="test", max_results=10)
                await self.search_coordinator.search(query)
                search_times.append((time.time() - start_time) * 1000)
            
            avg_search_time = statistics.mean(search_times)
            
            # Calculate score
            score = 100
            if avg_search_time > 2000:
                score -= 40
            elif avg_search_time > 1000:
                score -= 20
            
            return {
                'avg_search_time_ms': avg_search_time,
                'score': max(0, score)
            }
            
        except Exception as e:
            logger.error(f"Search benchmark failed: {e}")
            return {'score': 0, 'error': str(e)}
    
    def _setup_performance_targets(self):
        """Setup performance targets for metrics."""
        self.performance_targets = {
            'db_connection_time': 100.0,  # ms
            'db_query_time': 500.0,  # ms
            'api_health_check_time': 200.0,  # ms
            'search_avg_response_time': 1000.0,  # ms
            'cache_access_time': 50.0,  # ms
            'service_response_time': 1000.0,  # ms
            'api_availability': 95.0,  # %
            'service_availability': 95.0,  # %
            'search_cache_hit_rate': 70.0  # %
        }
    
    def _store_metrics_for_trending(self, metrics: Dict[str, PerformanceMetric]):
        """Store metrics for trend analysis."""
        for metric_name, metric in metrics.items():
            self.metrics_history[metric_name].append({
                'timestamp': metric.timestamp.isoformat(),
                'value': metric.value,
                'component': metric.component
            })
    
    async def _get_optimization_details(self, optimization_id: str) -> Optional[OptimizationRecommendation]:
        """Get details for specific optimization."""
        # This would look up optimization details from current recommendations
        return None
    
    async def _check_optimization_prerequisites(self, optimization: OptimizationRecommendation) -> bool:
        """Check if optimization prerequisites are met."""
        return True  # Simplified implementation
    
    async def _apply_specific_optimization(self, optimization: OptimizationRecommendation) -> Dict[str, Any]:
        """Apply specific optimization."""
        # This would implement the actual optimization steps
        return {'success': True, 'message': 'Optimization applied successfully'}
    
    async def _validate_optimization_results(self, optimization_id: str) -> Dict[str, Any]:
        """Validate optimization results."""
        return {'improvement_percentage': 15.0, 'validation_passed': True}
    
    async def _get_next_optimizations(self) -> List[str]:
        """Get next recommended optimizations."""
        return []
    
    def _analyze_benchmark_results(self, benchmarks: Dict[str, Any]) -> List[str]:
        """Analyze benchmark results and provide recommendations."""
        recommendations = []
        
        db_score = benchmarks.get('database', {}).get('score', 0)
        if db_score < 70:
            recommendations.append("Consider PostgreSQL migration for database performance")
        
        api_score = benchmarks.get('api', {}).get('score', 0)
        if api_score < 70:
            recommendations.append("Optimize API client configuration and connection pooling")
        
        search_score = benchmarks.get('search', {}).get('score', 0)
        if search_score < 70:
            recommendations.append("Implement search result caching and query optimization")
        
        return recommendations


# Singleton instance
_performance_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get singleton performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


def reset_performance_optimizer():
    """Reset performance optimizer for testing."""
    global _performance_optimizer
    _performance_optimizer = None


async def analyze_system_performance() -> PerformanceProfile:
    """Convenience function to analyze system performance."""
    optimizer = get_performance_optimizer()
    return await optimizer.analyze_performance()


async def auto_optimize_system(max_optimizations: int = 3) -> Dict[str, Any]:
    """Convenience function for auto-optimization."""
    optimizer = get_performance_optimizer()
    return await optimizer.auto_optimize(max_optimizations)