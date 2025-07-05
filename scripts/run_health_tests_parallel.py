#!/usr/bin/env python3
"""
Parallel health test runner with optimized performance settings.

This script runs health tests in parallel using pytest-xdist with optimized
settings for CI/CD and local development.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
import multiprocessing


def get_optimal_worker_count():
    """Get optimal number of workers based on system resources."""
    cpu_count = multiprocessing.cpu_count()
    
    # Conservative approach: use up to 75% of CPUs
    # This leaves room for system processes and I/O
    optimal_workers = max(1, int(cpu_count * 0.75))
    
    # Cap at 4 workers to avoid overwhelming shared resources like file I/O
    return min(optimal_workers, 4)


def run_parallel_tests(test_path, workers=None, fast_mode=False, verbose=False):
    """Run health tests in parallel with optimized settings."""
    
    if workers is None:
        workers = get_optimal_worker_count()
    
    # Base command
    cmd = [sys.executable, '-m', 'pytest', str(test_path)]
    
    # Parallel execution
    if workers == 1:
        print(f"Running tests sequentially (1 worker)")
    else:
        cmd.extend(['-n', str(workers)])
        print(f"Running tests in parallel ({workers} workers)")
    
    # Performance optimizations
    if fast_mode:
        # Fast mode: reduce file scanning and use shorter timeouts
        env = os.environ.copy()
        env['PENSIEVE_MAX_FILES_PER_TEST'] = '20'
        env['PENSIEVE_TEST_TIMEOUT'] = '15'
        cmd.extend(['--tb=short', '--disable-warnings'])
        print("Fast mode enabled: reduced file scanning and timeouts")
    else:
        env = os.environ.copy()
        env['PENSIEVE_MAX_FILES_PER_TEST'] = '30'
    
    # Verbosity
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    # Additional optimizations
    cmd.extend([
        '--tb=short',           # Short traceback format
        '--no-header',          # No pytest header
        '--no-summary',         # No test summary (unless verbose)
        '--strict-markers',     # Ensure markers are defined
    ])
    
    print(f"Command: {' '.join(cmd)}")
    print(f"Environment: PENSIEVE_MAX_FILES_PER_TEST={env.get('PENSIEVE_MAX_FILES_PER_TEST')}")
    print("=" * 60)
    
    # Run tests
    try:
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 130


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run AutoTaskTracker health tests in parallel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run all health tests with auto worker count
  %(prog)s tests/health/database/       # Run specific module
  %(prog)s -w 2                         # Use 2 workers
  %(prog)s --fast                       # Fast mode (reduced file scanning)
  %(prog)s -v                           # Verbose output
  %(prog)s --sequential                 # Force sequential execution

Performance Tips:
  - Use --fast for CI/CD or quick feedback
  - Use -w 1 if experiencing resource contention
  - Set PENSIEVE_MAX_FILES_PER_TEST=10 for ultra-fast testing
        """
    )
    
    parser.add_argument(
        'test_path', 
        nargs='?', 
        default='tests/health/',
        help='Path to test directory or file (default: tests/health/)'
    )
    
    parser.add_argument(
        '-w', '--workers',
        type=int,
        help=f'Number of parallel workers (default: auto-detect, max {get_optimal_worker_count()})'
    )
    
    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Force sequential execution (same as -w 1)'
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Fast mode: reduce file scanning and timeouts'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate test path
    test_path = Path(args.test_path)
    if not test_path.exists():
        print(f"Error: Test path '{test_path}' does not exist")
        return 1
    
    # Determine worker count
    if args.sequential:
        workers = 1
    elif args.workers:
        workers = args.workers
    else:
        workers = get_optimal_worker_count()
    
    print("AutoTaskTracker Parallel Health Test Runner")
    print(f"Test path: {test_path}")
    print(f"System CPUs: {multiprocessing.cpu_count()}")
    
    # Run tests
    exit_code = run_parallel_tests(
        test_path=test_path,
        workers=workers,
        fast_mode=args.fast,
        verbose=args.verbose
    )
    
    # Results
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed (exit code: {exit_code})")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())