#!/usr/bin/env python3
"""
Health test performance benchmark script.

Runs comprehensive performance analysis of the health test suite and provides
optimization recommendations.
"""

import sys
import os
import time
import subprocess
import json
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.health.utils.performance import HealthTestPerformanceMonitor


def run_benchmark_suite() -> Dict:
    """Run comprehensive performance benchmark of health test suite."""
    results = {
        'timestamp': time.time(),
        'modules': {},
        'total_performance': {},
        'comparisons': {}
    }
    
    # Test modules to benchmark
    test_modules = [
        'tests/health/code_quality/',
        'tests/health/database/', 
        'tests/health/configuration/',
        'tests/health/integration/',
        'tests/health/documentation/',
        'tests/health/testing/',
    ]
    
    print("🏃 Running Health Test Performance Benchmark")
    print("=" * 60)
    
    for module in test_modules:
        print(f"\n📁 Benchmarking {module}...")
        module_name = module.split('/')[-2]
        
        # Run module tests and time them
        start_time = time.time()
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', module, 
                '-v', '--tb=short', '--disable-warnings', '--no-header'
            ], capture_output=True, text=True, timeout=120)
            
            duration = time.time() - start_time
            
            # Parse test count from output using more robust parsing
            test_count = 0
            
            # Try multiple parsing strategies
            output_lines = result.stdout.split('\n')
            
            # Strategy 1: Look for "X passed in Y seconds" pattern
            import re
            for line in output_lines:
                if 'passed' in line and 'in' in line and 's' in line:
                    # Match patterns like "5 passed in 2.34s" or "10 passed, 2 warnings in 1.23s"
                    match = re.search(r'(\d+)\s+passed', line)
                    if match:
                        test_count = int(match.group(1))
                        break
            
            # Strategy 2: Count individual test results if strategy 1 failed
            if test_count == 0:
                for line in output_lines:
                    if '::test_' in line and ('PASSED' in line or 'FAILED' in line or 'SKIPPED' in line):
                        test_count += 1
            
            # Strategy 3: Look for collected items count
            if test_count == 0:
                for line in output_lines:
                    if 'collected' in line and 'item' in line:
                        match = re.search(r'collected (\d+) item', line)
                        if match:
                            test_count = int(match.group(1))
                            break
            
            results['modules'][module_name] = {
                'duration': duration,
                'test_count': test_count,
                'avg_per_test': duration / test_count if test_count > 0 else 0,
                'status': 'success' if result.returncode == 0 else 'failed',
                'stdout_lines': len(result.stdout.split('\n')),
                'stderr_lines': len(result.stderr.split('\n'))
            }
            
            if test_count > 0:
                print(f"  ✅ {test_count} tests in {duration:.2f}s ({duration/test_count:.2f}s avg)")
            else:
                print(f"  ⚠️  Tests completed in {duration:.2f}s (count parsing failed)")
                # Try to extract test count from stderr for debugging
                if result.stderr:
                    print(f"      stderr: {result.stderr[:100]}...")
            
        except subprocess.TimeoutExpired:
            duration = 120.0
            results['modules'][module_name] = {
                'duration': duration,
                'test_count': 0,
                'avg_per_test': 0,
                'status': 'timeout',
                'stdout_lines': 0,
                'stderr_lines': 0
            }
            print(f"  ⏰ Timeout after {duration}s")
            
        except Exception as e:
            results['modules'][module_name] = {
                'error': str(e),
                'status': 'error'
            }
            print(f"  ❌ Error: {e}")
    
    # Calculate totals
    total_tests = sum(m.get('test_count', 0) for m in results['modules'].values())
    total_time = sum(m.get('duration', 0) for m in results['modules'].values())
    
    results['total_performance'] = {
        'total_tests': total_tests,
        'total_time': total_time,
        'avg_per_test': total_time / total_tests if total_tests > 0 else 0,
        'tests_per_second': total_tests / total_time if total_time > 0 else 0
    }
    
    return results


def analyze_and_recommend(results: Dict) -> List[str]:
    """Analyze results and provide optimization recommendations."""
    recommendations = []
    
    # Check module performance
    slow_modules = []
    for module, stats in results['modules'].items():
        if stats.get('avg_per_test', 0) > 2.0:
            slow_modules.append((module, stats['avg_per_test']))
    
    if slow_modules:
        recommendations.append(
            f"Slow modules detected: {', '.join(f'{m} ({avg:.1f}s/test)' for m, avg in slow_modules)}. "
            f"Consider reducing file scan scope with PENSIEVE_MAX_FILES_PER_TEST."
        )
    
    # Check total performance
    total_perf = results['total_performance']
    if total_perf['avg_per_test'] > 1.5:
        recommendations.append(
            f"Overall test performance is slow ({total_perf['avg_per_test']:.2f}s/test). "
            f"Consider parallelization with pytest-xdist."
        )
    
    # Check for timeouts
    timeout_modules = [m for m, stats in results['modules'].items() if stats.get('status') == 'timeout']
    if timeout_modules:
        recommendations.append(
            f"Timeout issues in: {', '.join(timeout_modules)}. "
            f"Increase timeout or optimize these modules."
        )
    
    return recommendations


def main():
    """Main benchmark execution."""
    print("AutoTaskTracker Health Test Performance Benchmark")
    print("Analyzing test suite performance and providing optimization recommendations...\n")
    
    # Run benchmarks
    results = run_benchmark_suite()
    
    # Analyze and display results
    print("\n📊 Performance Analysis")
    print("=" * 60)
    
    total = results['total_performance']
    print(f"Total Tests: {total['total_tests']}")
    print(f"Total Time: {total['total_time']:.2f}s")
    print(f"Average per Test: {total['avg_per_test']:.2f}s")
    print(f"Tests per Second: {total['tests_per_second']:.1f}")
    
    print("\n📁 Module Breakdown:")
    for module, stats in results['modules'].items():
        if stats.get('status') == 'success':
            print(f"  {module:15} {stats['test_count']:3d} tests  {stats['duration']:6.2f}s  {stats['avg_per_test']:5.2f}s/test")
        else:
            print(f"  {module:15} {stats.get('status', 'unknown'):>20}")
    
    # Recommendations
    recommendations = analyze_and_recommend(results)
    if recommendations:
        print("\n💡 Optimization Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("\n✅ Performance looks good! No optimization recommendations.")
    
    # Save detailed results to tests directory
    reports_dir = Path(__file__).parent.parent / "tests" / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "health_test_performance_report.json"
    
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Performance grade
    avg_per_test = total['avg_per_test']
    if avg_per_test < 0.5:
        grade = "A+ (Excellent)"
    elif avg_per_test < 1.0:
        grade = "A (Very Good)"
    elif avg_per_test < 2.0:
        grade = "B (Good)"
    elif avg_per_test < 3.0:
        grade = "C (Fair)"
    else:
        grade = "D (Needs Optimization)"
    
    print(f"\n🎯 Performance Grade: {grade}")
    print(f"   Average {avg_per_test:.2f}s per test")
    
    return results


if __name__ == "__main__":
    main()