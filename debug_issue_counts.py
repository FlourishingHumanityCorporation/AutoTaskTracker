#!/usr/bin/env python3
"""
Debug script to compare issue detection between original and refactored health tests.
"""

import os
import sys
from pathlib import Path

# Set up environment
os.environ['PENSIEVE_MAX_FILES'] = '20'  # Smaller for focused debugging
sys.path.insert(0, str(Path(__file__).parent))

def compare_n_plus_one_detection():
    """Compare N+1 query detection between original and refactored versions."""
    print("🔍 N+1 QUERY DETECTION COMPARISON")
    print("="*40)
    
    from tests.health.test_pensieve_integration_health import TestPensieveIntegrationHealth, analyze_file_for_n_plus_one
    from tests.health.test_database_health import TestDatabaseHealth
    from tests.health.analyzers.database_analyzer import DatabaseAnalyzer
    
    # Setup both test instances
    original = TestPensieveIntegrationHealth()
    original.setup_class()
    
    refactored = TestDatabaseHealth()
    refactored.setup_class()
    
    print(f"Files to analyze - Original: {len(original.python_files)}, Refactored: {len(refactored.python_files)}")
    
    # Find common files
    common_files = []
    for orig_file in original.python_files:
        for refact_file in refactored.python_files:
            if orig_file == refact_file:
                common_files.append(orig_file)
                break
    
    print(f"Common files: {len(common_files)}")
    
    # Test a specific file that had many issues
    test_file = None
    for f in common_files:
        if 'event_processor.py' in str(f):
            test_file = f
            break
    
    if not test_file:
        test_file = common_files[0]  # Use first common file
    
    print(f"\nTesting file: {test_file.name}")
    
    # Original analyzer
    original_issues = analyze_file_for_n_plus_one(test_file)
    print(f"Original analyzer found: {len(original_issues)} issues")
    
    # Refactored analyzer
    db_analyzer = DatabaseAnalyzer(original.project_root)
    refactored_issues = db_analyzer.analyze_n_plus_one_patterns(test_file)
    print(f"Refactored analyzer found: {len(refactored_issues)} issues")
    
    # Show details if different
    if len(original_issues) != len(refactored_issues):
        print("\n❌ DISCREPANCY FOUND!")
        print("\nOriginal issues (first 3):")
        for i, issue in enumerate(original_issues[:3]):
            print(f"  {i+1}. Line {issue['line']}: {issue['code'][:60]}...")
        
        print("\nRefactored issues (first 3):")
        for i, issue in enumerate(refactored_issues[:3]):
            print(f"  {i+1}. Line {issue['line']}: {issue['code'][:60]}...")
    else:
        print("✅ Issue counts match!")
    
    return len(original_issues), len(refactored_issues)

def compare_error_handling_detection():
    """Compare error handling detection."""
    print("\n🔍 ERROR HANDLING DETECTION COMPARISON")
    print("="*40)
    
    from tests.health.test_pensieve_integration_health import analyze_file_for_error_handling
    from tests.health.analyzers.error_analyzer import ErrorAnalyzer
    
    # Use the same file as before
    project_root = Path(__file__).parent
    test_files = list(project_root.glob("autotasktracker/**/*.py"))[:5]  # First 5 files
    
    total_original = 0
    total_refactored = 0
    
    error_analyzer = ErrorAnalyzer(project_root)
    
    for test_file in test_files:
        original_issues = analyze_file_for_error_handling(test_file)
        refactored_issues = error_analyzer.analyze_error_patterns(test_file)
        
        total_original += len(original_issues)
        total_refactored += len(refactored_issues)
        
        if len(original_issues) != len(refactored_issues):
            print(f"❌ {test_file.name}: Original={len(original_issues)}, Refactored={len(refactored_issues)}")
    
    print(f"\nTotal error issues - Original: {total_original}, Refactored: {total_refactored}")
    return total_original, total_refactored

def main():
    """Main comparison function."""
    print("🔍 HEALTH TEST ISSUE DETECTION COMPARISON")
    print("="*50)
    
    # Compare N+1 detection
    orig_n1, refact_n1 = compare_n_plus_one_detection()
    
    # Compare error handling
    orig_err, refact_err = compare_error_handling_detection()
    
    print("\n📊 SUMMARY")
    print("="*20)
    print(f"N+1 Queries    - Original: {orig_n1:3d}, Refactored: {refact_n1:3d}")
    print(f"Error Handling - Original: {orig_err:3d}, Refactored: {refact_err:3d}")
    
    total_orig = orig_n1 + orig_err
    total_refact = refact_n1 + refact_err
    
    print(f"TOTAL ISSUES   - Original: {total_orig:3d}, Refactored: {total_refact:3d}")
    
    if total_orig != total_refact:
        print(f"\n❌ ISSUE COUNT DISCREPANCY: Difference of {abs(total_orig - total_refact)} issues")
        print("   This needs investigation and fixing!")
    else:
        print("\n✅ Issue counts are equivalent!")

if __name__ == "__main__":
    main()