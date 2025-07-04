#!/usr/bin/env python3
"""
Test runner that provides clear visibility on testing status.
Shows what's working, what's skipped, and why.
"""

import subprocess
import sys
from pathlib import Path

def run_test_suite():
    """Run the test suite with clear reporting on functionality."""
    
    print("🧪 AutoTaskTracker Test Suite Runner")
    print("=" * 50)
    
    # Core tests that should always pass
    core_tests = [
        ("Health Tests", "tests/health/", "Core system health checks"),
        ("Unit Tests", "tests/unit/test_dashboard_core.py", "Dashboard core functionality"),
        ("Infrastructure Tests", "tests/infrastructure/", "Service infrastructure"),
    ]
    
    # Integration tests that may skip in some environments
    integration_tests = [
        ("AI Features", "tests/integration/test_ai_features_integration.py", "AI/ML functionality"),
        ("Basic Pensieve", "tests/unit/test_basic_functionality.py", "Screenshot capture basic tests"),
        ("Pensieve Critical", "tests/integration/test_pensieve_critical_path.py", "Core Pensieve functionality"),
    ]
    
    # E2E tests that require full environment
    e2e_tests = [
        ("E2E Complete Journey", "tests/e2e/test_complete_user_journey.py", "Full user workflow"),
        ("E2E Headless", "tests/e2e/test_headless_environment.py", "Browser automation tests"),
        ("Pensieve E2E", "tests/integration/test_pensieve_end_to_end.py", "Complete pipeline test"),
    ]
    
    results = {
        "core_passed": 0,
        "core_total": len(core_tests),
        "integration_passed": 0,
        "integration_skipped": 0,
        "integration_total": len(integration_tests),
        "e2e_passed": 0,
        "e2e_skipped": 0,
        "e2e_total": len(e2e_tests),
        "failures": []
    }
    
    def run_test_group(name, tests, timeout=30):
        """Run a group of tests and return results."""
        print(f"\n📊 {name}")
        print("-" * 30)
        
        passed = 0
        skipped = 0
        failed = 0
        
        for test_name, test_path, description in tests:
            print(f"  Running: {test_name}")
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", test_path, "-v", "--tb=short", f"--timeout={timeout}"],
                    capture_output=True,
                    text=True,
                    timeout=timeout + 10
                )
                
                if result.returncode == 0:
                    if "skipped" in result.stdout.lower():
                        print(f"    ⚠️  SKIPPED - {description}")
                        skipped += 1
                    else:
                        print(f"    ✅ PASSED - {description}")
                        passed += 1
                else:
                    print(f"    ❌ FAILED - {description}")
                    failed += 1
                    results["failures"].append(f"{test_name}: {description}")
                    
            except subprocess.TimeoutExpired:
                print(f"    ⏰ TIMEOUT - {description} (hanging test)")
                failed += 1
                results["failures"].append(f"{test_name}: Timeout - hanging test")
            except Exception as e:
                print(f"    💥 ERROR - {description}: {e}")
                failed += 1
                results["failures"].append(f"{test_name}: Error - {e}")
        
        return passed, skipped, failed
    
    # Run core tests
    p, s, f = run_test_group("CORE FUNCTIONALITY", core_tests, 60)
    results["core_passed"] = p
    if f > 0:
        print("🚨 CRITICAL: Core functionality tests failed!")
        return results
    
    # Run integration tests
    p, s, f = run_test_group("INTEGRATION TESTS", integration_tests, 45)
    results["integration_passed"] = p
    results["integration_skipped"] = s
    
    # Run E2E tests
    p, s, f = run_test_group("END-TO-END TESTS", e2e_tests, 90)
    results["e2e_passed"] = p
    results["e2e_skipped"] = s
    
    return results

def print_summary(results):
    """Print a clear summary of test results."""
    print("\n" + "=" * 50)
    print("🎯 TEST SUITE SUMMARY")
    print("=" * 50)
    
    # Core functionality
    core_status = "✅ FULLY FUNCTIONAL" if results["core_passed"] == results["core_total"] else "❌ BROKEN"
    print(f"Core System: {core_status}")
    print(f"  Passed: {results['core_passed']}/{results['core_total']}")
    
    # Integration functionality
    integration_functional = results["integration_passed"]
    integration_total = results["integration_total"]
    integration_percentage = (integration_functional / integration_total * 100) if integration_total > 0 else 0
    
    if integration_percentage == 100:
        integration_status = "✅ FULLY FUNCTIONAL"
    elif integration_percentage >= 75:
        integration_status = "🟡 MOSTLY FUNCTIONAL"
    elif integration_percentage >= 50:
        integration_status = "⚠️ PARTIALLY FUNCTIONAL"
    else:
        integration_status = "❌ LIMITED FUNCTIONALITY"
    
    print(f"Integration Features: {integration_status}")
    print(f"  Passed: {integration_functional}/{integration_total}")
    if results["integration_skipped"] > 0:
        print(f"  Skipped: {results['integration_skipped']} (environment limitations)")
    
    # E2E functionality
    e2e_functional = results["e2e_passed"]
    e2e_total = results["e2e_total"]
    e2e_percentage = (e2e_functional / e2e_total * 100) if e2e_total > 0 else 0
    
    if e2e_percentage == 100:
        e2e_status = "✅ FULLY TESTED"
    elif e2e_percentage >= 50:
        e2e_status = "🟡 PARTIALLY TESTED"
    else:
        e2e_status = "⚠️ LIMITED E2E COVERAGE"
    
    print(f"End-to-End Testing: {e2e_status}")
    print(f"  Passed: {e2e_functional}/{e2e_total}")
    if results["e2e_skipped"] > 0:
        print(f"  Skipped: {results['e2e_skipped']} (requires full environment)")
    
    # Overall status
    print("\n🏆 OVERALL SYSTEM STATUS:")
    if results["core_passed"] == results["core_total"]:
        if integration_percentage >= 75:
            print("  System is PRODUCTION READY ✅")
        else:
            print("  System is FUNCTIONAL with some limitations ⚠️")
    else:
        print("  System has CRITICAL ISSUES ❌")
    
    # Failures
    if results["failures"]:
        print(f"\n💥 FAILURES ({len(results['failures'])}):")
        for failure in results["failures"]:
            print(f"  • {failure}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if results["integration_skipped"] > 0:
        print("  • Some integration tests skipped - full functionality requires complete environment")
    if results["e2e_skipped"] > 0:
        print("  • E2E tests skipped - browser automation and screen capture not available")
    if len(results["failures"]) > 0:
        print("  • Address failures above for full system reliability")
    else:
        print("  • All available tests passing - system health is good!")

if __name__ == "__main__":
    results = run_test_suite()
    print_summary(results)
    
    # Exit with appropriate code
    if results["core_passed"] < results["core_total"]:
        sys.exit(1)  # Critical failure
    elif len(results["failures"]) > 0:
        sys.exit(2)  # Some failures
    else:
        sys.exit(0)  # Success