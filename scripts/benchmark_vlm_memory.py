#!/usr/bin/env python3
"""
VLM Memory Benchmark Script
Measures memory usage patterns for AutoTaskTracker VLM processing to establish baselines for dual-model implementation.
"""
import sys
import os
import gc
import time
import json
import logging
import tracemalloc
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.config import get_config
from autotasktracker.ai.vlm_processor import SmartVLMProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VLMMemoryBenchmark:
    """Benchmarks VLM memory usage for AutoTaskTracker."""
    
    def __init__(self):
        """Initialize benchmark with configuration."""
        self.config = get_config()
        self.processor = None
        self.test_images = []
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {},
            'baseline_memory': {},
            'processing_memory': {},
            'cache_memory': {},
            'peak_memory': {},
            'recommendations': []
        }
        
    def create_test_images(self, count: int = 5) -> List[str]:
        """Create test images for memory benchmarking."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            test_images = []
            
            for i in range(count):
                # Create images of different sizes to test memory scaling
                sizes = [(400, 300), (800, 600), (1200, 900), (1600, 1200), (1920, 1080)]
                width, height = sizes[i % len(sizes)]
                
                # Create test image
                img = Image.new('RGB', (width, height), color='white')
                draw = ImageDraw.Draw(img)
                
                # Add varying content
                draw.text((20, 20), f"Memory Test Image {i+1}", fill='black')
                draw.text((20, 50), f"Size: {width}x{height}", fill='black')
                draw.text((20, 80), f"Testing VLM memory usage patterns", fill='blue')
                
                # Add some visual complexity
                for j in range(10):
                    x1, y1 = j * 50, j * 30
                    x2, y2 = x1 + 100, y1 + 50
                    draw.rectangle([x1, y1, x2, y2], outline='red', width=2)
                    draw.text((x1 + 10, y1 + 10), f"Element {j}", fill='red')
                
                # Save to temp file
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                img.save(temp_file.name)
                test_images.append(temp_file.name)
                logger.info(f"Created test image {i+1}: {width}x{height} -> {temp_file.name}")
            
            self.test_images = test_images
            return test_images
            
        except Exception as e:
            logger.error(f"Failed to create test images: {e}")
            return []
    
    def get_system_memory_info(self) -> Dict:
        """Get system memory information."""
        try:
            import psutil
            
            # System memory
            system_memory = psutil.virtual_memory()
            
            # Process memory
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'system_total_gb': system_memory.total / (1024**3),
                'system_available_gb': system_memory.available / (1024**3),
                'system_used_percent': system_memory.percent,
                'process_rss_mb': process_memory.rss / (1024**2),
                'process_vms_mb': process_memory.vms / (1024**2),
            }
        except ImportError:
            logger.warning("psutil not available for detailed memory info")
            return {'error': 'psutil_not_available'}
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {'error': str(e)}
    
    def measure_baseline_memory(self) -> Dict:
        """Measure baseline memory usage before VLM processing."""
        logger.info("Measuring baseline memory usage...")
        
        # Force garbage collection
        gc.collect()
        
        # Start memory tracing
        tracemalloc.start()
        
        # Get baseline measurements
        baseline = {
            'system_info': self.get_system_memory_info(),
            'tracemalloc_start': tracemalloc.get_traced_memory(),
        }
        
        # Initialize VLM processor (but don't process anything yet)
        logger.info("Initializing VLM processor...")
        self.processor = SmartVLMProcessor()
        
        # Measure after initialization
        gc.collect()
        baseline.update({
            'post_init_system': self.get_system_memory_info(),
            'post_init_tracemalloc': tracemalloc.get_traced_memory(),
            'processor_cache_stats': self.processor.get_cache_stats(),
        })
        
        logger.info(f"Baseline memory - Process RSS: {baseline['post_init_system'].get('process_rss_mb', 0):.1f}MB")
        
        return baseline
    
    def measure_single_image_processing(self, image_path: str) -> Dict:
        """Measure memory usage for processing a single image."""
        logger.info(f"Processing single image: {image_path}")
        
        # Memory before processing
        gc.collect()
        memory_before = {
            'system': self.get_system_memory_info(),
            'tracemalloc': tracemalloc.get_traced_memory(),
            'cache_stats': self.processor.get_cache_stats()
        }
        
        # Process image
        start_time = time.time()
        try:
            result = self.processor.process_image(
                image_path=image_path,
                window_title="Memory Benchmark Test",
                priority="normal"
            )
            processing_time = time.time() - start_time
            success = result is not None
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            processing_time = time.time() - start_time
            success = False
            result = None
        
        # Memory after processing
        gc.collect()
        memory_after = {
            'system': self.get_system_memory_info(),
            'tracemalloc': tracemalloc.get_traced_memory(),
            'cache_stats': self.processor.get_cache_stats()
        }
        
        # Calculate memory delta
        memory_delta = {}
        if 'process_rss_mb' in memory_before['system'] and 'process_rss_mb' in memory_after['system']:
            memory_delta['rss_mb'] = memory_after['system']['process_rss_mb'] - memory_before['system']['process_rss_mb']
        
        if memory_before['tracemalloc'] and memory_after['tracemalloc']:
            memory_delta['traced_mb'] = (memory_after['tracemalloc'][0] - memory_before['tracemalloc'][0]) / (1024**2)
        
        return {
            'image_path': image_path,
            'processing_time': processing_time,
            'success': success,
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_delta': memory_delta,
            'result_size': len(str(result)) if result else 0
        }
    
    def measure_batch_processing(self, image_paths: List[str]) -> Dict:
        """Measure memory usage for batch processing."""
        logger.info(f"Batch processing {len(image_paths)} images...")
        
        # Memory before batch
        gc.collect()
        memory_before = {
            'system': self.get_system_memory_info(),
            'tracemalloc': tracemalloc.get_traced_memory(),
            'cache_stats': self.processor.get_cache_stats()
        }
        
        # Process batch
        start_time = time.time()
        try:
            # Create task objects for batch processing
            tasks = [{'filepath': path, 'active_window': f'Test Window {i}'} 
                    for i, path in enumerate(image_paths)]
            
            results = self.processor.batch_process(tasks, max_concurrent=2)
            processing_time = time.time() - start_time
            success_count = len([r for r in results.values() if r is not None])
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            processing_time = time.time() - start_time
            success_count = 0
            results = {}
        
        # Memory after batch
        gc.collect()
        memory_after = {
            'system': self.get_system_memory_info(),
            'tracemalloc': tracemalloc.get_traced_memory(),
            'cache_stats': self.processor.get_cache_stats()
        }
        
        # Calculate memory delta
        memory_delta = {}
        if 'process_rss_mb' in memory_before['system'] and 'process_rss_mb' in memory_after['system']:
            memory_delta['rss_mb'] = memory_after['system']['process_rss_mb'] - memory_before['system']['process_rss_mb']
        
        if memory_before['tracemalloc'] and memory_after['tracemalloc']:
            memory_delta['traced_mb'] = (memory_after['tracemalloc'][0] - memory_before['tracemalloc'][0]) / (1024**2)
        
        return {
            'image_count': len(image_paths),
            'success_count': success_count,
            'total_processing_time': processing_time,
            'avg_processing_time': processing_time / len(image_paths) if image_paths else 0,
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_delta': memory_delta,
            'cache_efficiency': len(results) / len(image_paths) if image_paths else 0
        }
    
    def measure_cache_memory_scaling(self) -> Dict:
        """Measure how memory scales with cache usage."""
        logger.info("Measuring cache memory scaling...")
        
        cache_measurements = []
        
        # Process images one by one and measure cache growth
        for i, image_path in enumerate(self.test_images):
            # Process image
            self.processor.process_image(image_path, f"Cache Test {i}")
            
            # Measure cache state
            gc.collect()
            cache_stats = self.processor.get_cache_stats()
            system_memory = self.get_system_memory_info()
            traced_memory = tracemalloc.get_traced_memory()
            
            cache_measurements.append({
                'image_number': i + 1,
                'cache_stats': cache_stats,
                'system_memory_mb': system_memory.get('process_rss_mb', 0),
                'traced_memory_mb': traced_memory[0] / (1024**2) if traced_memory else 0
            })
            
            logger.info(f"Cache measurement {i+1}: "
                       f"Cache items: {cache_stats.get('image_cache_items', 0)}, "
                       f"Cache size: {cache_stats.get('image_cache_size_mb', 0):.1f}MB")
        
        return {
            'measurements': cache_measurements,
            'final_cache_stats': self.processor.get_cache_stats()
        }
    
    def run_memory_stress_test(self) -> Dict:
        """Run stress test to find memory limits."""
        logger.info("Running memory stress test...")
        
        stress_results = {
            'max_concurrent_images': 0,
            'peak_memory_mb': 0,
            'memory_limit_reached': False,
            'error_encountered': None
        }
        
        try:
            # Try processing multiple images simultaneously
            concurrent_count = 1
            max_attempts = 10
            
            while concurrent_count <= max_attempts:
                logger.info(f"Testing concurrent processing: {concurrent_count} images")
                
                # Use same images multiple times to simulate concurrent load
                test_paths = (self.test_images * ((concurrent_count // len(self.test_images)) + 1))[:concurrent_count]
                
                gc.collect()
                memory_before = self.get_system_memory_info()
                
                try:
                    # Create tasks for concurrent processing
                    tasks = [{'filepath': path, 'active_window': f'Stress Test {i}'} 
                            for i, path in enumerate(test_paths)]
                    
                    start_time = time.time()
                    results = self.processor.batch_process(tasks, max_concurrent=min(3, concurrent_count))
                    processing_time = time.time() - start_time
                    
                    gc.collect()
                    memory_after = self.get_system_memory_info()
                    
                    peak_memory = memory_after.get('process_rss_mb', 0)
                    stress_results['max_concurrent_images'] = concurrent_count
                    stress_results['peak_memory_mb'] = max(stress_results['peak_memory_mb'], peak_memory)
                    
                    logger.info(f"Concurrent {concurrent_count}: "
                               f"Peak memory: {peak_memory:.1f}MB, "
                               f"Time: {processing_time:.1f}s")
                    
                    # Check if we're approaching memory limits (e.g., > 4GB)
                    if peak_memory > 4000:
                        stress_results['memory_limit_reached'] = True
                        logger.warning(f"Memory limit approached at {concurrent_count} concurrent images")
                        break
                    
                    concurrent_count += 2
                    
                except Exception as e:
                    logger.error(f"Stress test failed at {concurrent_count} concurrent: {e}")
                    stress_results['error_encountered'] = str(e)
                    break
            
        except Exception as e:
            logger.error(f"Stress test error: {e}")
            stress_results['error_encountered'] = str(e)
        
        return stress_results
    
    def analyze_dual_model_feasibility(self) -> Dict:
        """Analyze feasibility of dual-model processing based on memory measurements."""
        logger.info("Analyzing dual-model feasibility...")
        
        current_peak = self.results.get('peak_memory', {}).get('peak_memory_mb', 0)
        system_total = self.results.get('baseline_memory', {}).get('system_info', {}).get('system_total_gb', 0) * 1024
        
        analysis = {
            'current_peak_mb': current_peak,
            'system_total_mb': system_total,
            'current_usage_percent': (current_peak / system_total * 100) if system_total > 0 else 0,
            'estimated_dual_model_mb': current_peak * 2.2,  # Conservative estimate
            'dual_model_feasible': False,
            'recommendations': []
        }
        
        estimated_dual = analysis['estimated_dual_model_mb']
        
        if estimated_dual < system_total * 0.7:  # Less than 70% of system memory
            analysis['dual_model_feasible'] = True
            analysis['recommendations'].append("Dual-model processing appears feasible with current memory")
        elif estimated_dual < system_total * 0.9:  # Between 70-90%
            analysis['dual_model_feasible'] = True
            analysis['recommendations'].append("Dual-model processing possible but requires memory optimization")
            analysis['recommendations'].append("Consider reducing cache sizes and concurrent processing")
        else:
            analysis['dual_model_feasible'] = False
            analysis['recommendations'].append("Dual-model processing may cause memory issues")
            analysis['recommendations'].append("Consider sequential processing or hardware upgrade")
        
        # Model-specific recommendations
        if current_peak > 2000:  # > 2GB
            analysis['recommendations'].append("Consider reducing VLM cache size from 100MB to 50MB")
        
        if len(self.test_images) > 3:
            analysis['recommendations'].append("Limit concurrent processing to 2-3 images maximum")
        
        return analysis
    
    def run_complete_benchmark(self) -> Dict:
        """Run complete memory benchmark."""
        logger.info("Starting complete VLM memory benchmark...")
        
        try:
            # Create test images
            if not self.create_test_images(5):
                raise Exception("Failed to create test images")
            
            # Measure baseline
            self.results['baseline_memory'] = self.measure_baseline_memory()
            
            # Single image processing
            logger.info("Testing single image processing...")
            single_results = []
            for image_path in self.test_images[:3]:  # Test first 3 images
                single_result = self.measure_single_image_processing(image_path)
                single_results.append(single_result)
            
            self.results['single_image_processing'] = single_results
            
            # Batch processing
            logger.info("Testing batch processing...")
            self.results['batch_processing'] = self.measure_batch_processing(self.test_images)
            
            # Cache scaling
            logger.info("Testing cache memory scaling...")
            # Clear caches first
            self.processor.clear_caches()
            self.results['cache_scaling'] = self.measure_cache_memory_scaling()
            
            # Memory stress test
            logger.info("Running memory stress test...")
            self.results['stress_test'] = self.run_memory_stress_test()
            
            # Dual-model feasibility analysis
            self.results['dual_model_analysis'] = self.analyze_dual_model_feasibility()
            
            # Final recommendations
            self.generate_recommendations()
            
            logger.info("Memory benchmark completed successfully")
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            self.results['error'] = str(e)
        finally:
            self.cleanup()
        
        return self.results
    
    def generate_recommendations(self):
        """Generate final recommendations based on all measurements."""
        recommendations = []
        
        # Get key metrics
        peak_memory = self.results.get('stress_test', {}).get('peak_memory_mb', 0)
        cache_efficiency = self.results.get('batch_processing', {}).get('cache_efficiency', 0)
        dual_feasible = self.results.get('dual_model_analysis', {}).get('dual_model_feasible', False)
        
        # Memory recommendations
        if peak_memory > 3000:  # > 3GB
            recommendations.append("HIGH PRIORITY: Reduce memory usage before dual-model implementation")
            recommendations.append("Decrease VLM cache size from 100MB to 25MB")
            recommendations.append("Limit concurrent processing to 1-2 images")
        elif peak_memory > 1500:  # > 1.5GB
            recommendations.append("MEDIUM PRIORITY: Optimize memory usage")
            recommendations.append("Reduce VLM cache size to 50MB")
            recommendations.append("Monitor memory during dual-model implementation")
        else:
            recommendations.append("Current memory usage is acceptable")
        
        # Cache recommendations
        if cache_efficiency < 0.8:
            recommendations.append("Improve cache efficiency - current hit rate is low")
        
        # Dual-model recommendations
        if dual_feasible:
            recommendations.append("✓ Dual-model processing appears feasible")
            recommendations.append("Implement sequential model processing (not parallel)")
            recommendations.append("Monitor memory usage during Phase 2 implementation")
        else:
            recommendations.append("⚠ Dual-model processing may cause memory issues")
            recommendations.append("Consider hardware upgrade or alternative architecture")
        
        # Implementation strategy
        recommendations.append("Phase 1: Implement temperature configuration (DONE)")
        recommendations.append("Phase 2: Test single model optimization before dual-model")
        recommendations.append("Phase 3: Implement dual-model with memory monitoring")
        
        self.results['final_recommendations'] = recommendations
    
    def cleanup(self):
        """Clean up test resources."""
        # Clean up test images
        for image_path in self.test_images:
            try:
                if os.path.exists(image_path):
                    os.unlink(image_path)
                    logger.debug(f"Cleaned up test image: {image_path}")
            except Exception as e:
                logger.error(f"Failed to clean up {image_path}: {e}")
        
        # Stop memory tracing
        try:
            tracemalloc.stop()
        except Exception:
            pass
        
        logger.info("Cleanup completed")


def main():
    """Main benchmark function."""
    benchmark = VLMMemoryBenchmark()
    
    try:
        # Run complete benchmark
        results = benchmark.run_complete_benchmark()
        
        # Print summary
        print("\n" + "="*60)
        print("VLM MEMORY BENCHMARK RESULTS")
        print("="*60)
        print(f"Timestamp: {results['timestamp']}")
        
        # System info
        baseline = results.get('baseline_memory', {})
        system_info = baseline.get('system_info', {})
        if system_info:
            print(f"System Memory: {system_info.get('system_total_gb', 0):.1f}GB total")
            print(f"Available Memory: {system_info.get('system_available_gb', 0):.1f}GB")
        
        # Peak memory usage
        stress_test = results.get('stress_test', {})
        if stress_test:
            print(f"Peak Memory Usage: {stress_test.get('peak_memory_mb', 0):.1f}MB")
            print(f"Max Concurrent Images: {stress_test.get('max_concurrent_images', 0)}")
        
        # Dual-model feasibility
        dual_analysis = results.get('dual_model_analysis', {})
        if dual_analysis:
            feasible = "✓ FEASIBLE" if dual_analysis.get('dual_model_feasible') else "⚠ RISKY"
            print(f"Dual-Model Feasibility: {feasible}")
            estimated_mb = dual_analysis.get('estimated_dual_model_mb', 0)
            print(f"Estimated Dual-Model Memory: {estimated_mb:.1f}MB")
        
        print()
        
        # Recommendations
        recommendations = results.get('final_recommendations', [])
        if recommendations:
            print("KEY RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i:2d}. {rec}")
        
        # Save results
        results_file = Path("vlm_memory_benchmark.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {results_file}")
        
        # Return exit code based on dual-model feasibility
        if dual_analysis.get('dual_model_feasible', False):
            return 0  # Success
        else:
            return 1  # Warning - might work but risky
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        print(f"BENCHMARK FAILED: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)