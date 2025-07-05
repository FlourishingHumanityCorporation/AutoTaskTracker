#!/usr/bin/env python3
"""
Health Test Optimization Script

Implements the performance optimization options mentioned in CLAUDE.md:
- PENSIEVE_MAX_FILES_PER_TEST environment variable
- Parallel execution options
- Performance monitoring and recommendations
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HealthTestOptimizer:
    """Health test performance optimizer."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.default_optimizations = {
            'max_files_per_test': 30,
            'parallel_workers': 'auto',
            'fail_fast': True,
            'short_traceback': True,
            'timeout_seconds': 60
        }
    
    def run_optimized_tests(self, 
                           test_path: str = "tests/health/",
                           max_files: Optional[int] = None,
                           parallel: bool = True,
                           fail_fast: bool = True,
                           verbose: bool = False) -> Dict:
        """Run health tests with optimizations applied."""
        
        # Set up environment variables
        env = os.environ.copy()
        
        if max_files is not None:
            env['PENSIEVE_MAX_FILES_PER_TEST'] = str(max_files)
            print(f"🔧 Setting max files per test: {max_files}")
        
        # Build pytest command
        cmd = [sys.executable, '-m', 'pytest', test_path]
        
        # Add optimization flags
        if fail_fast:
            cmd.append('-x')  # Stop on first failure
            
        if not verbose:
            cmd.append('--tb=short')  # Short traceback
        else:
            cmd.append('-v')  # Verbose output
            
        # Add parallel execution if available
        if parallel:
            try:
                # Check if pytest-xdist is available
                import xdist
                cmd.extend(['-n', 'auto'])
                print("🚀 Enabling parallel execution")
            except ImportError:
                print("⚠️  pytest-xdist not available, running sequentially")
                print("   Install with: pip install pytest-xdist")
        
        # Disable warnings for cleaner output
        cmd.append('--disable-warnings')
        
        print(f"🏃 Running: {' '.join(cmd)}")
        print(f"📁 Test path: {test_path}")
        
        # Run tests with timing
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd, 
                env=env,
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse results
            results = self._parse_test_results(result, duration)
            
            return results
            
        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'duration': 300,
                'error': 'Tests exceeded 5 minute timeout'
            }
        
        except Exception as e:
            return {
                'status': 'error', 
                'error': str(e),
                'duration': time.time() - start_time
            }
    
    def _parse_test_results(self, result: subprocess.CompletedProcess, duration: float) -> Dict:
        """Parse pytest results."""
        import re
        
        test_count = 0
        passed = 0
        failed = 0
        errors = 0
        
        # Parse output for test counts
        output = result.stdout + result.stderr
        
        # Look for summary line like "5 passed, 2 failed in 10.23s"
        summary_match = re.search(r'(\d+)\s+passed', output)
        if summary_match:
            passed = int(summary_match.group(1))
            test_count += passed
        
        failed_match = re.search(r'(\d+)\s+failed', output)
        if failed_match:
            failed = int(failed_match.group(1))
            test_count += failed
        
        error_match = re.search(r'(\d+)\s+error', output)
        if error_match:
            errors = int(error_match.group(1))
            test_count += errors
        
        # If no summary found, count individual test results
        if test_count == 0:
            test_lines = [line for line in output.split('\n') if '::test_' in line]
            test_count = len(test_lines)
            passed = len([line for line in test_lines if 'PASSED' in line])
            failed = len([line for line in test_lines if 'FAILED' in line])
            errors = len([line for line in test_lines if 'ERROR' in line])
        
        return {
            'status': 'success' if result.returncode == 0 else 'failed',
            'duration': duration,
            'test_count': test_count,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'avg_per_test': duration / test_count if test_count > 0 else 0,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    
    def benchmark_optimization_levels(self) -> Dict:
        """Benchmark different optimization levels."""
        print("🔬 Benchmarking Health Test Optimization Levels")
        print("=" * 60)
        
        # Test configurations to benchmark
        configs = [
            {'name': 'Baseline', 'max_files': None, 'parallel': False, 'fail_fast': False},
            {'name': 'Fast Files', 'max_files': 30, 'parallel': False, 'fail_fast': False},
            {'name': 'Parallel', 'max_files': None, 'parallel': True, 'fail_fast': False},
            {'name': 'Fail Fast', 'max_files': None, 'parallel': False, 'fail_fast': True},
            {'name': 'Optimized', 'max_files': 30, 'parallel': True, 'fail_fast': True},
        ]
        
        # Use a smaller test set for benchmarking
        test_path = "tests/health/code_quality/"
        
        results = {}
        
        for config in configs:
            print(f"\n📊 Testing {config['name']} configuration...")
            
            result = self.run_optimized_tests(
                test_path=test_path,
                max_files=config['max_files'],
                parallel=config['parallel'],
                fail_fast=config['fail_fast'],
                verbose=False
            )
            
            results[config['name']] = result
            
            if result['status'] == 'success':
                print(f"   ✅ {result['test_count']} tests in {result['duration']:.1f}s "
                      f"({result['avg_per_test']:.2f}s avg)")
            else:
                print(f"   ❌ {result['status']}: {result.get('error', 'Unknown error')}")
        
        return results
    
    def generate_recommendations(self, benchmark_results: Dict) -> List[str]:
        """Generate optimization recommendations based on benchmark results."""
        recommendations = []
        
        # Find fastest configuration
        successful_configs = {name: r for name, r in benchmark_results.items() 
                            if r['status'] == 'success'}
        
        if not successful_configs:
            recommendations.append("⚠️  No configurations completed successfully")
            return recommendations
        
        fastest_config = min(successful_configs.items(), key=lambda x: x[1]['duration'])
        baseline = benchmark_results.get('Baseline')
        
        if fastest_config[0] != 'Baseline' and baseline and baseline['status'] == 'success':
            speedup = baseline['duration'] / fastest_config[1]['duration']
            recommendations.append(
                f"🚀 Best configuration: {fastest_config[0]} "
                f"({speedup:.1f}x faster than baseline)"
            )
        
        # Specific recommendations
        if 'Optimized' in successful_configs:
            optimized = successful_configs['Optimized']
            if optimized['avg_per_test'] < 1.0:
                recommendations.append("✅ Optimized configuration achieves <1s per test")
            else:
                recommendations.append(f"⚠️  Optimized config still slow ({optimized['avg_per_test']:.1f}s/test)")
        
        # Environment variable recommendations
        if fastest_config[0] in ['Fast Files', 'Optimized']:
            recommendations.append(
                "🔧 Set PENSIEVE_MAX_FILES_PER_TEST=30 for faster execution"
            )
        
        # Parallel execution recommendations
        if 'Parallel' in successful_configs:
            parallel = successful_configs['Parallel']
            if baseline and baseline['status'] == 'success':
                parallel_speedup = baseline['duration'] / parallel['duration']
                if parallel_speedup > 1.2:
                    recommendations.append(
                        f"🚀 Parallel execution provides {parallel_speedup:.1f}x speedup"
                    )
        
        return recommendations
    
    def save_optimization_profile(self, profile_name: str = "default"):
        """Save optimization settings as environment profile."""
        profile_path = self.project_root / f".env.{profile_name}"
        
        with open(profile_path, 'w') as f:
            f.write("# Health Test Optimization Profile\n")
            f.write(f"# Generated by health_test_optimizer.py\n\n")
            f.write(f"PENSIEVE_MAX_FILES_PER_TEST={self.default_optimizations['max_files_per_test']}\n")
            f.write(f"PENSIEVE_TEST_TIMEOUT={self.default_optimizations['timeout_seconds']}\n")
            f.write("\n# Usage:\n")
            f.write(f"# source .env.{profile_name}\n")
            f.write("# pytest tests/health/ -x --tb=short\n")
            f.write("# pytest tests/health/ -n auto  # if pytest-xdist is installed\n")
        
        print(f"💾 Optimization profile saved to {profile_path}")
        print(f"   Use with: source .env.{profile_name}")


def main():
    """Main optimizer execution."""
    parser = argparse.ArgumentParser(description="Health Test Performance Optimizer")
    parser.add_argument('--benchmark', action='store_true', 
                       help='Run optimization benchmark')
    parser.add_argument('--test-path', default='tests/health/',
                       help='Path to tests to run (default: tests/health/)')
    parser.add_argument('--max-files', type=int, default=30,
                       help='Max files per test (default: 30)')
    parser.add_argument('--no-parallel', action='store_true',
                       help='Disable parallel execution')
    parser.add_argument('--no-fail-fast', action='store_true', 
                       help='Disable fail-fast mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--save-profile', type=str,
                       help='Save optimization settings as profile')
    
    args = parser.parse_args()
    
    optimizer = HealthTestOptimizer()
    
    if args.benchmark:
        print("AutoTaskTracker Health Test Optimization Benchmark")
        print("Running comprehensive optimization analysis...\n")
        
        # Run benchmark
        results = optimizer.benchmark_optimization_levels()
        
        # Display results
        print("\n📊 Benchmark Results")
        print("=" * 60)
        print(f"{'Configuration':<12} {'Duration':<10} {'Tests':<7} {'Avg/Test':<10} {'Status'}")
        print("-" * 60)
        
        for name, result in results.items():
            if result['status'] == 'success':
                print(f"{name:<12} {result['duration']:<10.1f} {result['test_count']:<7} "
                      f"{result['avg_per_test']:<10.2f} {'✅'}")
            else:
                print(f"{name:<12} {'--':<10} {'--':<7} {'--':<10} {'❌'}")
        
        # Generate recommendations
        recommendations = optimizer.generate_recommendations(results)
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
    else:
        print("AutoTaskTracker Health Test Optimizer")
        print("Running optimized health tests...\n")
        
        # Run optimized tests
        result = optimizer.run_optimized_tests(
            test_path=args.test_path,
            max_files=args.max_files,
            parallel=not args.no_parallel,
            fail_fast=not args.no_fail_fast,
            verbose=args.verbose
        )
        
        # Display results
        print(f"\n📊 Results")
        print("=" * 40)
        print(f"Status: {result['status']}")
        print(f"Duration: {result['duration']:.2f}s")
        
        if result['status'] == 'success':
            print(f"Tests: {result['test_count']} ({result['passed']} passed)")
            if result['failed'] > 0:
                print(f"Failed: {result['failed']}")
            if result['errors'] > 0:
                print(f"Errors: {result['errors']}")
            print(f"Average: {result['avg_per_test']:.2f}s per test")
            
            # Performance grade
            avg = result['avg_per_test']
            if avg < 0.5:
                grade = "A+ (Excellent)"
            elif avg < 1.0:
                grade = "A (Very Good)" 
            elif avg < 2.0:
                grade = "B (Good)"
            else:
                grade = "C (Needs Optimization)"
            
            print(f"Grade: {grade}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Save profile if requested
    if args.save_profile:
        optimizer.save_optimization_profile(args.save_profile)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())