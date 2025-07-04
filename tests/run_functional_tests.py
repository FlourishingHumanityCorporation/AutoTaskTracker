#!/usr/bin/env python3
"""
Comprehensive test runner for AutoTaskTracker functional tests.
This script runs the new real functional tests and provides detailed reporting.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Test categories and their files
TEST_CATEGORIES = {
    'ocr': {
        'name': 'OCR Processing',
        'file': 'test_real_ocr_processing.py',
        'description': 'Real OCR using Tesseract on actual images',
        'requirements': ['tesseract', 'PIL'],
        'timeout': 60
    },
    'database': {
        'name': 'Database Workflows', 
        'file': 'test_real_database_workflows.py',
        'description': 'Real SQLite operations with actual data',
        'requirements': ['sqlite3'],
        'timeout': 30
    },
    'ai': {
        'name': 'AI Processing',
        'file': 'test_real_ai_processing.py', 
        'description': 'Real AI models and inference',
        'requirements': ['autotasktracker.ai'],
        'timeout': 120
    },
    'pipeline': {
        'name': 'Full Pipeline Integration',
        'file': 'test_full_pipeline_integration.py',
        'description': 'End-to-end workflows with real components', 
        'requirements': ['memos', 'sqlite3'],
        'timeout': 180
    }
}


def check_requirements() -> Dict[str, Dict[str, Any]]:
    """Check if test requirements are available."""
    results = {}
    
    # Check Python packages
    packages_to_check = [
        ('tesseract', ['tesseract', '--version']),
        ('sqlite3', [sys.executable, '-c', 'import sqlite3']),
        ('PIL', [sys.executable, '-c', 'from PIL import Image']),
        ('memos', [sys.executable, '-c', 'import memos']),
    ]
    
    for package, check_cmd in packages_to_check:
        try:
            result = subprocess.run(
                check_cmd,
                capture_output=True, 
                text=True, 
                timeout=10
            )
            results[package] = {
                'available': result.returncode == 0,
                'version': result.stdout.strip() if result.returncode == 0 else None,
                'error': result.stderr.strip() if result.returncode != 0 else None
            }
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            results[package] = {
                'available': False,
                'version': None,
                'error': str(e)
            }
    
    # Check test assets
    assets_dir = REPO_ROOT / "tests" / "assets"
    results['test_assets'] = {
        'available': assets_dir.exists(),
        'files': list(assets_dir.glob('*.png')) if assets_dir.exists() else [],
        'error': None if assets_dir.exists() else 'Assets directory not found'
    }
    
    # Check virtual environment
    venv_python = REPO_ROOT / "venv" / "bin" / "python"
    results['venv'] = {
        'available': venv_python.exists(),
        'path': str(venv_python) if venv_python.exists() else None,
        'error': None if venv_python.exists() else 'Virtual environment not found'
    }
    
    return results


def run_test_category(category: str, verbose: bool = False, capture_output: bool = True) -> Dict[str, Any]:
    """Run tests for a specific category."""
    if category not in TEST_CATEGORIES:
        return {'success': False, 'error': f'Unknown category: {category}'}
    
    test_info = TEST_CATEGORIES[category]
    test_file = REPO_ROOT / "tests" / "functional" / test_info['file']
    
    if not test_file.exists():
        return {'success': False, 'error': f'Test file not found: {test_file}'}
    
    # Build pytest command
    cmd = [
        sys.executable, '-m', 'pytest', 
        str(test_file),
        '-v' if verbose else '-q',
        '--tb=short',
        '-x'  # Stop on first failure
    ]
    
    if not capture_output:
        cmd.append('-s')  # Don't capture output
    
    print(f"\n🧪 Running {test_info['name']} tests...")
    print(f"📝 {test_info['description']}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=test_info['timeout'],
            cwd=REPO_ROOT
        )
        
        duration = time.time() - start_time
        
        return {
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout if capture_output else '',
            'stderr': result.stderr if capture_output else '',
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            'success': False,
            'duration': duration,
            'error': f'Test timed out after {test_info["timeout"]} seconds',
            'returncode': -1
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            'success': False, 
            'duration': duration,
            'error': str(e),
            'returncode': -1
        }


def print_requirements_report(requirements: Dict[str, Dict[str, Any]]):
    """Print a requirements check report."""
    print("\n📋 Requirements Check")
    print("=" * 50)
    
    for req, info in requirements.items():
        status = "✅" if info['available'] else "❌"
        print(f"{status} {req.ljust(15)}", end="")
        
        if info['available']:
            if info.get('version'):
                print(f" - {info['version']}")
            elif info.get('files'):
                print(f" - {len(info['files'])} files")
            else:
                print(" - Available")
        else:
            print(f" - {info.get('error', 'Not available')}")


def print_test_summary(results: Dict[str, Dict[str, Any]]):
    """Print a test results summary."""
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r['success'])
    total_time = sum(r.get('duration', 0) for r in results.values())
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Total Time: {total_time:.1f}s")
    print()
    
    for category, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        duration = result.get('duration', 0)
        test_name = TEST_CATEGORIES[category]['name']
        
        print(f"{status} {test_name.ljust(25)} ({duration:.1f}s)")
        
        if not result['success']:
            if result.get('error'):
                print(f"     Error: {result['error']}")
            elif result.get('stderr'):
                print(f"     Error: {result['stderr'][:100]}...")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run AutoTaskTracker functional tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  ocr       - OCR processing with real images
  database  - Database operations with real data
  ai        - AI processing with real models  
  pipeline  - Full pipeline integration tests
  
Examples:
  python tests/run_functional_tests.py                    # Run all tests
  python tests/run_functional_tests.py --category ocr     # Run only OCR tests
  python tests/run_functional_tests.py --verbose          # Detailed output
  python tests/run_functional_tests.py --check-only       # Just check requirements
        """
    )
    
    parser.add_argument(
        '--category', '-c',
        choices=list(TEST_CATEGORIES.keys()),
        help='Run only tests for specific category'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose test output'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true', 
        help='Only check requirements, do not run tests'
    )
    
    parser.add_argument(
        '--no-capture',
        action='store_true',
        help='Do not capture test output (useful for debugging)'
    )
    
    args = parser.parse_args()
    
    print("🔬 AutoTaskTracker Functional Test Runner")
    print("=" * 50)
    
    # Check requirements
    requirements = check_requirements()
    print_requirements_report(requirements)
    
    if args.check_only:
        return 0
    
    # Determine which tests to run
    if args.category:
        categories_to_run = [args.category]
    else:
        categories_to_run = list(TEST_CATEGORIES.keys())
    
    # Run tests
    results = {}
    
    for category in categories_to_run:
        result = run_test_category(
            category, 
            verbose=args.verbose,
            capture_output=not args.no_capture
        )
        results[category] = result
        
        # Print immediate result
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        duration = result.get('duration', 0)
        print(f"{status} {TEST_CATEGORIES[category]['name']} ({duration:.1f}s)")
        
        if not result['success'] and not args.no_capture:
            if result.get('error'):
                print(f"   Error: {result['error']}")
            elif result.get('stderr'):
                # Show first few lines of stderr
                stderr_lines = result['stderr'].strip().split('\n')[:5]
                for line in stderr_lines:
                    print(f"   {line}")
                if len(result['stderr'].split('\n')) > 5:
                    print(f"   ... (use --verbose for full output)")
    
    # Print summary
    print_test_summary(results)
    
    # Return appropriate exit code
    all_passed = all(r['success'] for r in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())