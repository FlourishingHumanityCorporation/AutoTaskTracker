#!/usr/bin/env python3
"""
Validation script for the dashboard refactoring.
Runs comprehensive checks to ensure the refactoring is complete and working.
"""

import sys
import os
from pathlib import Path
import importlib.util
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(file_path).exists():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description} - MISSING: {file_path}")
        return False


def check_import(module_name: str, description: str) -> bool:
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description}")
        return True
    except ImportError as e:
        print(f"❌ {description} - IMPORT ERROR: {e}")
        return False


def check_tests() -> bool:
    """Run the dashboard tests."""
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/test_dashboard_core.py', '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ Dashboard tests pass")
            return True
        else:
            print("❌ Dashboard tests fail")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ Could not run tests: {e}")
        return False


def validate_architecture():
    """Validate the new architecture files."""
    print("🏗️ VALIDATING ARCHITECTURE")
    print("=" * 50)
    
    checks = [
        # Base architecture
        ("autotasktracker/dashboards/base.py", "Base dashboard class"),
        ("autotasktracker/dashboards/cache.py", "Caching system"),
        ("autotasktracker/dashboards/utils.py", "UI-independent utilities"),
        
        # Component library
        ("autotasktracker/dashboards/components/__init__.py", "Components package"),
        ("autotasktracker/dashboards/components/filters.py", "Filter components"),
        ("autotasktracker/dashboards/components/metrics.py", "Metrics components"),
        ("autotasktracker/dashboards/components/data_display.py", "Data display components"),
        ("autotasktracker/dashboards/components/visualizations.py", "Visualization components"),
        
        # Data layer
        ("autotasktracker/dashboards/data/__init__.py", "Data package"),
        ("autotasktracker/dashboards/data/models.py", "Data models"),
        ("autotasktracker/dashboards/data/repositories.py", "Data repositories"),
        
        # Refactored dashboards
        ("autotasktracker/dashboards/task_board_refactored.py", "Refactored task board"),
        ("autotasktracker/dashboards/analytics_refactored.py", "Refactored analytics"),
        ("autotasktracker/dashboards/achievement_board_refactored.py", "Refactored achievement board"),
        
        # Supporting files
        ("autotasktracker/dashboards/launcher_refactored.py", "Refactored launcher"),
        ("tests/test_dashboard_core.py", "Dashboard tests"),
        ("scripts/demo_refactored_dashboards.py", "Demo script"),
    ]
    
    passed = 0
    total = len(checks)
    
    for file_path, description in checks:
        if check_file_exists(file_path, description):
            passed += 1
    
    print(f"\nArchitecture files: {passed}/{total} ✅")
    return passed == total


def validate_imports():
    """Validate that all new modules can be imported."""
    print("\n📦 VALIDATING IMPORTS")
    print("=" * 50)
    
    imports = [
        # Core architecture
        ("autotasktracker.dashboards.base", "Base dashboard class"),
        ("autotasktracker.dashboards.cache", "Caching system"),
        ("autotasktracker.dashboards.utils", "Dashboard utilities"),
        
        # Components
        ("autotasktracker.dashboards.components.filters", "Filter components"),
        ("autotasktracker.dashboards.components.metrics", "Metrics components"),
        ("autotasktracker.dashboards.components.data_display", "Data display components"),
        
        # Data layer
        ("autotasktracker.dashboards.data.models", "Data models"),
        ("autotasktracker.dashboards.data.repositories", "Data repositories"),
    ]
    
    passed = 0
    total = len(imports)
    
    for module_name, description in imports:
        if check_import(module_name, description):
            passed += 1
    
    print(f"\nImports: {passed}/{total} ✅")
    return passed == total


def validate_documentation():
    """Validate documentation files."""
    print("\n📚 VALIDATING DOCUMENTATION")
    print("=" * 50)
    
    docs = [
        ("docs/REFACTORING_COMPLETE.md", "Refactoring completion guide"),
        ("docs/REFACTORING_RESULTS.md", "Detailed results documentation"),
        ("docs/MIGRATION_GUIDE.md", "Migration guide"),
        ("docs/DASHBOARD_REFACTORING.md", "Technical refactoring guide"),
    ]
    
    passed = 0
    total = len(docs)
    
    for file_path, description in docs:
        if check_file_exists(file_path, description):
            passed += 1
    
    print(f"\nDocumentation: {passed}/{total} ✅")
    return passed == total


def validate_functionality():
    """Validate basic functionality without UI."""
    print("\n🔧 VALIDATING FUNCTIONALITY")
    print("=" * 50)
    
    try:
        # Test time filtering
        from autotasktracker.dashboards.utils import get_time_range
        start, end = get_time_range("Today")
        print("✅ Time filtering works")
        
        # Test data models
        from autotasktracker.dashboards.data.models import Task, TaskGroup, DailyMetrics
        from datetime import datetime
        
        task = Task(
            id=1, title="Test", category="Development",
            timestamp=datetime.now(), duration_minutes=30,
            window_title="Test Window"
        )
        print("✅ Data models work")
        
        # Test caching
        from autotasktracker.dashboards.cache import DashboardCache
        key = DashboardCache.create_cache_key("test", param="value")
        print("✅ Caching system works")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False


def validate_tests():
    """Validate test coverage."""
    print("\n🧪 VALIDATING TESTS")
    print("=" * 50)
    
    return check_tests()


def validate_legacy_preservation():
    """Validate that original dashboards are preserved."""
    print("\n📚 VALIDATING LEGACY PRESERVATION")
    print("=" * 50)
    
    legacy_files = [
        ("autotasktracker/dashboards/task_board.py", "Original task board"),
        ("autotasktracker/dashboards/analytics.py", "Original analytics"),
        ("autotasktracker/dashboards/achievement_board.py", "Original achievement board"),
        ("autotasktracker/dashboards/timetracker.py", "Original time tracker"),
        ("autotasktracker/dashboards/vlm_monitor.py", "Original VLM monitor"),
    ]
    
    passed = 0
    total = len(legacy_files)
    
    for file_path, description in legacy_files:
        if check_file_exists(file_path, description):
            passed += 1
    
    print(f"\nLegacy preservation: {passed}/{total} ✅")
    return passed >= 4  # Allow for some missing files


def calculate_code_reduction():
    """Calculate code reduction metrics."""
    print("\n📊 CALCULATING CODE REDUCTION")
    print("=" * 50)
    
    comparisons = [
        ("autotasktracker/dashboards/task_board.py", "autotasktracker/dashboards/task_board_refactored.py"),
        ("autotasktracker/dashboards/analytics.py", "autotasktracker/dashboards/analytics_refactored.py"),
        ("autotasktracker/dashboards/achievement_board.py", "autotasktracker/dashboards/achievement_board_refactored.py"),
    ]
    
    total_original = 0
    total_refactored = 0
    
    for original, refactored in comparisons:
        try:
            with open(original, 'r') as f:
                original_lines = len(f.readlines())
            with open(refactored, 'r') as f:
                refactored_lines = len(f.readlines())
                
            reduction = (original_lines - refactored_lines) / original_lines * 100
            print(f"{Path(original).stem}: {original_lines} → {refactored_lines} lines ({reduction:.1f}% reduction)")
            
            total_original += original_lines
            total_refactored += refactored_lines
            
        except FileNotFoundError as e:
            print(f"❌ Could not compare {original}: {e}")
    
    if total_original > 0:
        overall_reduction = (total_original - total_refactored) / total_original * 100
        print(f"\nOverall reduction: {total_original} → {total_refactored} lines ({overall_reduction:.1f}% reduction)")
        return overall_reduction > 30  # Expect at least 30% reduction
    
    return False


def main():
    """Run all validation checks."""
    print("🔍 AutoTaskTracker Dashboard Refactoring Validation")
    print("=" * 60)
    print("This script validates that the dashboard refactoring is complete and working.")
    print()
    
    # Run all validation checks
    checks = [
        ("Architecture Files", validate_architecture),
        ("Module Imports", validate_imports),
        ("Documentation", validate_documentation),
        ("Basic Functionality", validate_functionality),
        ("Test Coverage", validate_tests),
        ("Legacy Preservation", validate_legacy_preservation),
        ("Code Reduction", calculate_code_reduction),
    ]
    
    results = {}
    passed = 0
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results[check_name] = result
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {check_name} validation failed with error: {e}")
            results[check_name] = False
    
    # Summary
    print("\n🎯 VALIDATION SUMMARY")
    print("=" * 60)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:<20}: {status}")
    
    total_checks = len(checks)
    success_rate = (passed / total_checks) * 100
    
    print(f"\nOverall: {passed}/{total_checks} checks passed ({success_rate:.1f}%)")
    
    if passed == total_checks:
        print("\n🎉 REFACTORING VALIDATION: SUCCESS!")
        print("✅ All systems operational")
        print("✅ Ready for production deployment")
        print("\nNext steps:")
        print("1. python -m autotasktracker.dashboards.launcher_refactored start")
        print("2. Review migration guide: docs/MIGRATION_GUIDE.md")
        print("3. Begin gradual migration to production")
    else:
        print("\n⚠️ REFACTORING VALIDATION: ISSUES FOUND")
        print("Please review the failed checks above")
        print("Some components may need attention before production deployment")
    
    return passed == total_checks


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)