#!/usr/bin/env python3
"""Test runner for mutation effectiveness unit tests.

This script runs all the comprehensive unit tests for the mutation effectiveness
implementation and provides a detailed report of test coverage and results.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any
import json
import time

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class MutationTestRunner:
    """Comprehensive test runner for mutation effectiveness modules."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests" / "unit"
        self.results = {}
        
    def run_all_mutation_tests(self) -> Dict[str, Any]:
        """Run all mutation effectiveness related unit tests."""
        test_files = [
            "test_mutation_effectiveness.py",
            "test_mutation_config.py", 
            "test_shared_utilities.py",
            "test_simple_intelligence.py"
        ]
        
        overall_results = {
            "timestamp": time.time(),
            "total_files": len(test_files),
            "test_results": {},
            "summary": {},
            "recommendations": []
        }
        
        print("🧪 Running comprehensive mutation effectiveness unit tests...")
        print("=" * 70)
        
        for test_file in test_files:
            print(f"\n📋 Running {test_file}...")
            result = self._run_single_test_file(test_file)
            overall_results["test_results"][test_file] = result
            
            # Print immediate feedback
            if result["success"]:
                print(f"   ✅ {result['tests_passed']} tests passed, {result['tests_failed']} failed")
            else:
                print(f"   ❌ Test file failed to run: {result.get('error', 'Unknown error')}")
        
        # Generate summary
        overall_results["summary"] = self._generate_summary(overall_results["test_results"])
        overall_results["recommendations"] = self._generate_recommendations(overall_results)
        
        return overall_results
    
    def _run_single_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a single test file and capture results."""
        test_path = self.test_dir / test_file
        
        if not test_path.exists():
            return {
                "success": False,
                "error": f"Test file not found: {test_path}",
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 0
            }
        
        try:
            start_time = time.time()
            
            # Run pytest with detailed output
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_path),
                "-v", "--tb=short", "--no-header",
                "--json-report", "--json-report-file=/tmp/pytest_report.json"
            ], 
            capture_output=True, 
            text=True, 
            cwd=self.project_root,
            timeout=300  # 5 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse pytest output
            tests_passed = result.stdout.count(" PASSED")
            tests_failed = result.stdout.count(" FAILED")
            tests_errors = result.stdout.count(" ERROR")
            
            return {
                "success": result.returncode == 0,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed + tests_errors,
                "execution_time": execution_time,
                "output": result.stdout,
                "errors": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out (5 minutes)",
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 300
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 0
            }
    
    def _generate_summary(self, test_results: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate overall test summary."""
        total_passed = sum(r["tests_passed"] for r in test_results.values())
        total_failed = sum(r["tests_failed"] for r in test_results.values())
        total_time = sum(r["execution_time"] for r in test_results.values())
        
        successful_files = sum(1 for r in test_results.values() if r["success"])
        total_files = len(test_results)
        
        return {
            "total_tests_passed": total_passed,
            "total_tests_failed": total_failed,
            "total_execution_time": total_time,
            "successful_test_files": successful_files,
            "total_test_files": total_files,
            "success_rate": (total_passed / (total_passed + total_failed)) * 100 if (total_passed + total_failed) > 0 else 0,
            "file_success_rate": (successful_files / total_files) * 100 if total_files > 0 else 0
        }
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        summary = results["summary"]
        
        if summary["file_success_rate"] < 100:
            recommendations.append(
                "🔧 Some test files failed to run - check dependencies and imports"
            )
        
        if summary["success_rate"] < 95:
            recommendations.append(
                "⚠️  Test success rate below 95% - review failing tests"
            )
        
        if summary["total_execution_time"] > 60:
            recommendations.append(
                "⏱️  Tests taking over 60 seconds - consider optimization"
            )
        
        # Check for specific module issues
        for test_file, result in results["test_results"].items():
            if not result["success"]:
                if "import" in result.get("errors", "").lower():
                    recommendations.append(
                        f"📦 Import issues in {test_file} - check module dependencies"
                    )
                elif result["tests_failed"] > result["tests_passed"]:
                    recommendations.append(
                        f"🐛 Many test failures in {test_file} - review implementation"
                    )
        
        if not recommendations:
            recommendations.append("✨ All tests passing - excellent test coverage!")
        
        return recommendations
    
    def print_detailed_report(self, results: Dict[str, Any]) -> None:
        """Print a detailed test report."""
        print("\n" + "=" * 70)
        print("📊 MUTATION EFFECTIVENESS TEST REPORT")
        print("=" * 70)
        
        summary = results["summary"]
        
        print(f"\n📈 OVERALL SUMMARY:")
        print(f"   Total Tests: {summary['total_tests_passed'] + summary['total_tests_failed']}")
        print(f"   Passed: {summary['total_tests_passed']} ✅")
        print(f"   Failed: {summary['total_tests_failed']} ❌")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Execution Time: {summary['total_execution_time']:.2f}s")
        
        print(f"\n📁 FILE BREAKDOWN:")
        for test_file, result in results["test_results"].items():
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {test_file}")
            print(f"      Passed: {result['tests_passed']}, Failed: {result['tests_failed']}")
            print(f"      Time: {result['execution_time']:.2f}s")
            
            if not result["success"] and result.get("error"):
                print(f"      Error: {result['error']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "=" * 70)
    
    def save_report(self, results: Dict[str, Any], output_file: Path) -> None:
        """Save test results to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"📄 Test report saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save report: {e}")


def main():
    """Main execution function."""
    project_root = Path(__file__).parent.parent.parent
    runner = MutationTestRunner(project_root)
    
    print("🚀 Starting mutation effectiveness unit test suite...")
    
    # Run all tests
    results = runner.run_all_mutation_tests()
    
    # Print detailed report
    runner.print_detailed_report(results)
    
    # Save report
    report_file = project_root / "test_reports" / f"mutation_tests_{int(time.time())}.json"
    report_file.parent.mkdir(exist_ok=True)
    runner.save_report(results, report_file)
    
    # Determine exit code
    summary = results["summary"]
    if summary["file_success_rate"] == 100 and summary["success_rate"] >= 95:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n⚠️  Some tests failed - check the report above")
        return 1


if __name__ == "__main__":
    sys.exit(main())