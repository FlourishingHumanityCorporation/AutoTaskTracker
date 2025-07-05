#!/usr/bin/env python3
"""
Precise comparison of original vs refactored health test results.
This script will identify exact discrepancies that need to be fixed.
"""

import os
import sys
import json
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import io

# Set up environment
os.environ['PENSIEVE_MAX_FILES'] = '50'
os.environ.pop('PENSIEVE_AUTO_FIX', None)
sys.path.insert(0, str(Path(__file__).parent))

def capture_test_output(test_func):
    """Capture both stdout and stderr from a test function."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            test_func()
        return {
            'status': 'PASS',
            'stdout': stdout_capture.getvalue(),
            'stderr': stderr_capture.getvalue(),
            'error': None
        }
    except Exception as e:
        return {
            'status': 'FAIL',
            'stdout': stdout_capture.getvalue(),
            'stderr': stderr_capture.getvalue(),
            'error': str(e)
        }

def extract_issue_counts(output_text):
    """Extract issue counts from test output."""
    import re
    counts = {}
    
    # Common patterns to look for
    patterns = {
        'n_plus_one': r'Found (\d+) potential N\+1 patterns',
        'error_handling': r'Found (\d+) error handling issues',
        'hardcoded_values': r'Found (\d+) hardcoded values',
        'bulk_operations': r'Found (\d+) files with potential bulk operation',
        'cache_management': r'Found (\d+) files using cache',
        'connection_pooling': r'Found (\d+) potential connection pooling',
        'missing_checks': r'Found (\d+) critical files without service',
        'inconsistent_keys': r'Found (\d+) inconsistent metadata key',
        'command_issues': r'Found (\d+) files with command issues',
        'transaction_issues': r'Found (\d+) functions with multiple write',
        'validation_issues': r'Found (\d+) file operations without validation',
        'retry_issues': r'Found (\d+) files with network operations',
        'index_issues': r'Found (\d+) queries that might benefit'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, output_text)
        if match:
            counts[key] = int(match.group(1))
    
    return counts

def run_original_tests():
    """Run all original tests and capture results."""
    print("🔍 Running Original Tests...")
    
    from tests.health.test_pensieve_integration_health import TestPensieveIntegrationHealth
    
    original = TestPensieveIntegrationHealth()
    original.setup_class()
    
    # Get all test methods
    import inspect
    test_methods = [name for name, method in inspect.getmembers(TestPensieveIntegrationHealth, inspect.isfunction) if name.startswith('test_')]
    
    results = {}
    
    for test_name in sorted(test_methods):
        print(f"  Running {test_name}...")
        test_method = getattr(original, test_name)
        result = capture_test_output(test_method)
        result['issue_counts'] = extract_issue_counts(result['stdout'])
        results[test_name] = result
    
    return results

def run_refactored_tests():
    """Run all refactored tests and capture results."""
    print("🔍 Running Refactored Tests...")
    
    test_modules = [
        ('tests.health.test_database_health', 'TestDatabaseHealth'),
        ('tests.health.test_integration_health', 'TestIntegrationHealth'),
        ('tests.health.test_error_health', 'TestErrorHealth'),
        ('tests.health.test_config_health', 'TestConfigHealth')
    ]
    
    results = {}
    
    for module_path, class_name in test_modules:
        print(f"  Running {class_name}...")
        
        import importlib
        module = importlib.import_module(module_path)
        test_class = getattr(module, class_name)
        
        # Get test methods
        import inspect
        test_methods = [name for name, method in inspect.getmembers(test_class, inspect.isfunction) if name.startswith('test_')]
        
        # Setup test instance
        test_instance = test_class()
        test_instance.setup_class()
        
        for test_name in sorted(test_methods):
            print(f"    Running {test_name}...")
            test_method = getattr(test_instance, test_name)
            result = capture_test_output(test_method)
            result['issue_counts'] = extract_issue_counts(result['stdout'])
            results[f"{class_name}.{test_name}"] = result
    
    # Also check standalone tests
    try:
        import tests.health.test_integration_health as integration_module
        standalone_tests = [name for name in dir(integration_module) if name.startswith('test_') and callable(getattr(integration_module, name))]
        
        for test_name in standalone_tests:
            print(f"    Running standalone {test_name}...")
            test_func = getattr(integration_module, test_name)
            result = capture_test_output(test_func)
            result['issue_counts'] = extract_issue_counts(result['stdout'])
            results[f"standalone.{test_name}"] = result
    except Exception as e:
        print(f"  Error running standalone tests: {e}")
    
    return results

def find_equivalent_tests(original_results, refactored_results):
    """Map original tests to their refactored equivalents."""
    mapping = {}
    
    # Direct mappings where names are the same
    for orig_name in original_results.keys():
        # Look for exact match in refactored
        for refact_name in refactored_results.keys():
            if orig_name in refact_name:
                mapping[orig_name] = refact_name
                break
    
    return mapping

def compare_results(original_results, refactored_results):
    """Compare results and identify discrepancies."""
    print("\n📊 DETAILED COMPARISON")
    print("="*50)
    
    mapping = find_equivalent_tests(original_results, refactored_results)
    
    discrepancies = []
    
    for orig_name, refact_name in mapping.items():
        orig = original_results[orig_name]
        refact = refactored_results[refact_name]
        
        print(f"\n🔍 {orig_name}:")
        print(f"  Original: {orig['status']}")
        print(f"  Refactored: {refact['status']} ({refact_name})")
        
        # Compare issue counts
        orig_counts = orig['issue_counts']
        refact_counts = refact['issue_counts']
        
        if orig_counts != refact_counts:
            print(f"  ❌ ISSUE COUNT MISMATCH:")
            all_keys = set(orig_counts.keys()) | set(refact_counts.keys())
            for key in sorted(all_keys):
                orig_val = orig_counts.get(key, 0)
                refact_val = refact_counts.get(key, 0)
                if orig_val != refact_val:
                    print(f"    {key}: Original={orig_val}, Refactored={refact_val}")
                    discrepancies.append({
                        'test': orig_name,
                        'issue_type': key,
                        'original': orig_val,
                        'refactored': refact_val,
                        'difference': abs(orig_val - refact_val)
                    })
        else:
            print(f"  ✅ Issue counts match")
        
        # Compare status
        if orig['status'] != refact['status']:
            print(f"  ❌ STATUS MISMATCH: {orig['status']} vs {refact['status']}")
            discrepancies.append({
                'test': orig_name,
                'issue_type': 'test_status',
                'original': orig['status'],
                'refactored': refact['status'],
                'difference': 'status_mismatch'
            })
    
    return discrepancies

def main():
    """Main comparison function."""
    print("🎯 EXACT HEALTH TEST COMPARISON")
    print("="*40)
    
    # Run both versions
    original_results = run_original_tests()
    refactored_results = run_refactored_tests()
    
    # Compare results
    discrepancies = compare_results(original_results, refactored_results)
    
    # Save detailed results
    results_data = {
        'original': original_results,
        'refactored': refactored_results,
        'discrepancies': discrepancies
    }
    
    with open('health_test_comparison.json', 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    
    # Summary
    print(f"\n📋 SUMMARY")
    print(f"="*20)
    print(f"Original tests: {len(original_results)}")
    print(f"Refactored tests: {len(refactored_results)}")
    print(f"Discrepancies found: {len(discrepancies)}")
    
    if discrepancies:
        print(f"\n❌ DISCREPANCIES TO FIX:")
        for disc in discrepancies[:10]:  # Show first 10
            print(f"  • {disc['test']}: {disc['issue_type']} ({disc['original']} → {disc['refactored']})")
        if len(discrepancies) > 10:
            print(f"  ... and {len(discrepancies) - 10} more")
    else:
        print(f"\n✅ NO DISCREPANCIES FOUND!")
    
    return discrepancies

if __name__ == "__main__":
    discrepancies = main()
    sys.exit(len(discrepancies))  # Exit with number of discrepancies