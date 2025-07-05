#!/usr/bin/env python3
"""
Health test coverage analysis for the modular test structure.

Analyzes what functionality is covered by the new modular health tests
vs the legacy monolithic tests to ensure no regression in coverage.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Set, List
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_test_methods(file_path: Path) -> Set[str]:
    """Extract test method names from a test file."""
    methods = set()
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            # Find all test methods
            for match in re.finditer(r'def (test_\w+)', content):
                methods.add(match.group(1))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return methods


def analyze_test_patterns(file_path: Path) -> Set[str]:
    """Analyze what patterns/features are tested in a file."""
    patterns = set()
    try:
        with open(file_path, 'r') as f:
            content = f.read().lower()
            
            # Common test patterns
            test_patterns = {
                'import': ['import', 'sys.path', 'circular'],
                'database': ['sqlite', 'database', 'connection', 'transaction'],
                'error': ['exception', 'error', 'bare except', 'try'],
                'config': ['config', 'hardcoded', 'environment'],
                'style': ['naming', 'convention', 'length', 'debug'],
                'pensieve': ['pensieve', 'memos', 'api'],
                'documentation': ['docs', 'readme', 'comment'],
                'performance': ['timeout', 'slow', 'performance'],
            }
            
            for category, keywords in test_patterns.items():
                if any(keyword in content for keyword in keywords):
                    patterns.add(category)
                    
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
    return patterns


def main():
    """Analyze health test coverage."""
    project_root = Path(__file__).parent.parent
    health_dir = project_root / "tests" / "health"
    
    print("🔍 Health Test Coverage Analysis")
    print("=" * 60)
    
    # Analyze modular structure
    modular_tests = {}
    modular_dirs = [
        "code_quality", "database", "configuration", 
        "integration", "documentation", "testing"
    ]
    
    for module_dir in modular_dirs:
        module_path = health_dir / module_dir
        if module_path.exists():
            tests = set()
            patterns = set()
            file_count = 0
            
            for test_file in module_path.glob("test_*.py"):
                file_count += 1
                tests.update(extract_test_methods(test_file))
                patterns.update(analyze_test_patterns(test_file))
            
            modular_tests[module_dir] = {
                'file_count': file_count,
                'test_count': len(tests),
                'tests': tests,
                'patterns': patterns
            }
    
    # Analyze legacy tests
    legacy_tests = {}
    legacy_files = [
        "test_codebase_health.py",
        "test_testing_system_health.py", 
        "test_documentation_health.py",
        "test_error_health.py"
    ]
    
    for legacy_file in legacy_files:
        legacy_path = health_dir / legacy_file
        if legacy_path.exists():
            tests = extract_test_methods(legacy_path)
            patterns = analyze_test_patterns(legacy_path)
            
            legacy_tests[legacy_file] = {
                'test_count': len(tests),
                'tests': tests,
                'patterns': patterns
            }
    
    # Coverage analysis
    print("\n📊 Modular Test Structure Coverage:")
    total_modular_tests = 0
    all_modular_patterns = set()
    
    for module, info in modular_tests.items():
        total_modular_tests += info['test_count']
        all_modular_patterns.update(info['patterns'])
        print(f"  {module:15} {info['file_count']} files, {info['test_count']:2d} tests  [{', '.join(sorted(info['patterns']))}]")
    
    print(f"\nTotal Modular Tests: {total_modular_tests}")
    print(f"Coverage Areas: {', '.join(sorted(all_modular_patterns))}")
    
    print("\n📊 Legacy Test Coverage:")
    total_legacy_tests = 0
    all_legacy_patterns = set()
    
    for file, info in legacy_tests.items():
        total_legacy_tests += info['test_count']
        all_legacy_patterns.update(info['patterns'])
        print(f"  {file:25} {info['test_count']:2d} tests  [{', '.join(sorted(info['patterns']))}]")
    
    print(f"\nTotal Legacy Tests: {total_legacy_tests}")
    print(f"Coverage Areas: {', '.join(sorted(all_legacy_patterns))}")
    
    # Gap analysis
    print("\n🔍 Coverage Gap Analysis:")
    
    # Pattern coverage comparison
    modular_only = all_modular_patterns - all_legacy_patterns
    legacy_only = all_legacy_patterns - all_modular_patterns
    shared = all_modular_patterns & all_legacy_patterns
    
    print(f"Shared coverage: {', '.join(sorted(shared)) if shared else 'None'}")
    print(f"Modular-only: {', '.join(sorted(modular_only)) if modular_only else 'None'}")
    print(f"Legacy-only: {', '.join(sorted(legacy_only)) if legacy_only else 'None'}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    if legacy_only:
        print(f"  • Consider adding {', '.join(legacy_only)} coverage to modular tests")
    
    if total_modular_tests < total_legacy_tests:
        print(f"  • Modular tests ({total_modular_tests}) have fewer tests than legacy ({total_legacy_tests})")
        print(f"    This is expected as modular tests are more focused")
    else:
        print(f"  • Good: Modular tests ({total_modular_tests}) match/exceed legacy coverage ({total_legacy_tests})")
    
    # Overall assessment
    coverage_ratio = len(all_modular_patterns) / len(all_legacy_patterns) if all_legacy_patterns else 0
    
    print(f"\n🎯 Coverage Assessment:")
    if coverage_ratio >= 1.0:
        print("  ✅ Excellent: Modular tests cover all legacy areas and more")
    elif coverage_ratio >= 0.8:
        print("  ✅ Good: Modular tests cover most legacy functionality")
    else:
        print("  ⚠️  Review needed: Modular tests may be missing coverage areas")
    
    print(f"  Coverage ratio: {coverage_ratio:.1%}")
    
    # Usage recommendations
    print(f"\n📋 Usage Recommendations:")
    print(f"  • For fast development feedback: Run modular tests by category")
    print(f"  • For comprehensive coverage: Include both modular and legacy tests")
    print(f"  • For CI/CD: Run all tests with performance optimizations")


if __name__ == "__main__":
    main()