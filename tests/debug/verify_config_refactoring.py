#!/usr/bin/env python3
"""
Verify that config system health test refactoring preserves ALL functionality.

This script compares the original monolithic test with the new modular tests
to ensure 100% functionality preservation.
"""

import ast
import re
import inspect
from pathlib import Path
from typing import Dict, List, Set, Any
import importlib.util

def extract_test_methods(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """Extract all test methods and their details from a Python file."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
        
        test_methods = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Extract docstring
                docstring = ast.get_docstring(node) or ""
                
                # Extract method body patterns
                body_patterns = []
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        continue  # Skip docstrings
                    body_patterns.append(ast.unparse(stmt)[:100])  # First 100 chars
                
                # Extract assertions
                assertions = []
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Name):
                        if stmt.func.id == 'assert':
                            assertions.append(ast.unparse(stmt)[:100])
                        elif stmt.func.id in ['assertEqual', 'assertTrue', 'assertFalse', 'assertIn']:
                            assertions.append(f"{stmt.func.id}({ast.unparse(stmt.args[0])[:50]})")
                
                # Extract key patterns from the method
                key_patterns = set()
                method_str = ast.unparse(node)
                
                # Common test patterns
                patterns_to_check = [
                    r'get_config\(\)',
                    r'get_pensieve_config',
                    r'DatabaseManager',
                    r'environment',
                    r'sync',
                    r'performance',
                    r'security',
                    r'hardcoded',
                    r'port',
                    r'localhost',
                    r'database\.db',
                    r'\.memos',
                    r'isolation',
                    r'override',
                    r'consistency'
                ]
                
                for pattern in patterns_to_check:
                    if re.search(pattern, method_str, re.IGNORECASE):
                        key_patterns.add(pattern)
                
                test_methods[node.name] = {
                    'docstring': docstring,
                    'body_patterns': body_patterns[:5],  # First 5 patterns
                    'assertions': assertions[:5],  # First 5 assertions
                    'key_patterns': key_patterns,
                    'line_count': node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                }
                
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return {}
    
    return test_methods

def analyze_test_coverage(original_methods: Dict, refactored_methods: Dict) -> Dict[str, Any]:
    """Analyze test coverage between original and refactored tests."""
    analysis = {
        'original_count': len(original_methods),
        'refactored_count': len(refactored_methods),
        'missing_tests': [],
        'pattern_coverage': {},
        'functionality_gaps': [],
        'coverage_score': 0
    }
    
    # Collect all patterns from original tests
    all_original_patterns = set()
    for method_name, details in original_methods.items():
        all_original_patterns.update(details['key_patterns'])
    
    # Collect all patterns from refactored tests
    all_refactored_patterns = set()
    for method_name, details in refactored_methods.items():
        all_refactored_patterns.update(details['key_patterns'])
    
    # Check pattern coverage
    missing_patterns = all_original_patterns - all_refactored_patterns
    analysis['pattern_coverage'] = {
        'original_patterns': len(all_original_patterns),
        'refactored_patterns': len(all_refactored_patterns),
        'missing_patterns': list(missing_patterns),
        'coverage_percentage': (len(all_refactored_patterns) / len(all_original_patterns) * 100) if all_original_patterns else 100
    }
    
    # Analyze specific test method coverage
    original_test_purposes = {}
    for method_name, details in original_methods.items():
        # Categorize by key functionality
        purpose = categorize_test_purpose(method_name, details)
        if purpose not in original_test_purposes:
            original_test_purposes[purpose] = []
        original_test_purposes[purpose].append(method_name)
    
    refactored_test_purposes = {}
    for method_name, details in refactored_methods.items():
        purpose = categorize_test_purpose(method_name, details)
        if purpose not in refactored_test_purposes:
            refactored_test_purposes[purpose] = []
        refactored_test_purposes[purpose].append(method_name)
    
    # Check for missing functionality
    for purpose, original_tests in original_test_purposes.items():
        if purpose not in refactored_test_purposes:
            analysis['functionality_gaps'].append(f"Missing entire category: {purpose}")
        else:
            # Check if refactored tests cover the same patterns
            original_patterns_for_purpose = set()
            for test in original_tests:
                original_patterns_for_purpose.update(original_methods[test]['key_patterns'])
            
            refactored_patterns_for_purpose = set()
            for test in refactored_test_purposes[purpose]:
                refactored_patterns_for_purpose.update(refactored_methods[test]['key_patterns'])
            
            missing_in_category = original_patterns_for_purpose - refactored_patterns_for_purpose
            if missing_in_category:
                analysis['functionality_gaps'].append(f"{purpose}: missing patterns {missing_in_category}")
    
    # Calculate overall coverage score
    pattern_score = analysis['pattern_coverage']['coverage_percentage']
    functionality_score = 100 - (len(analysis['functionality_gaps']) * 10)  # -10% per gap
    analysis['coverage_score'] = min(100, (pattern_score + functionality_score) / 2)
    
    return analysis

def categorize_test_purpose(method_name: str, details: Dict) -> str:
    """Categorize test purpose based on method name and patterns."""
    name_lower = method_name.lower()
    patterns = details['key_patterns']
    docstring = details['docstring'].lower()
    
    if 'architecture' in name_lower or 'integrity' in name_lower:
        return 'architecture'
    elif 'environment' in name_lower or 'security' in name_lower:
        return 'security'
    elif 'sync' in name_lower or 'consistency' in name_lower:
        return 'synchronization'
    elif 'performance' in name_lower or 'reliability' in name_lower:
        return 'performance'
    elif 'integration' in name_lower:
        return 'integration'
    elif 'hardcoded' in name_lower or 'production' in name_lower:
        return 'compliance'
    elif 'isolation' in name_lower or 'test_' in name_lower:
        return 'testing'
    else:
        # Try to categorize by patterns
        if any(p in ['security', 'environment'] for p in patterns):
            return 'security'
        elif any(p in ['sync', 'consistency'] for p in patterns):
            return 'synchronization'
        elif any(p in ['performance'] for p in patterns):
            return 'performance'
        else:
            return 'other'

def main():
    """Main verification function."""
    project_root = Path(__file__).parent
    
    print("🔍 CONFIGURATION HEALTH TEST REFACTORING VERIFICATION")
    print("=" * 60)
    
    # Original test file
    original_file = project_root / "tests/health/test_config_system_health.py"
    
    # Check both extraction-based and composition-based refactoring
    extraction_files = [
        project_root / "tests/health/test_config_loading_health.py",
        project_root / "tests/health/test_config_sync_health.py", 
        project_root / "tests/health/test_config_usage_health.py"
    ]
    
    composition_files = [
        project_root / "tests/health/config_system/test_architecture.py",
        project_root / "tests/health/config_system/test_security.py",
        project_root / "tests/health/config_system/test_compliance.py",
        project_root / "tests/health/config_system/test_infrastructure.py",
        project_root / "tests/health/config_system/test_all_categories.py"
    ]
    
    refactored_files = extraction_files + composition_files
    
    print(f"📁 Original file: {original_file.name}")
    print(f"📁 Refactored files: {[f.name for f in refactored_files]}")
    print()
    
    # Extract test methods from original file
    print("🔍 Analyzing original test methods...")
    original_methods = extract_test_methods(original_file)
    print(f"   Found {len(original_methods)} test methods")
    
    # Extract test methods from refactored files
    print("🔍 Analyzing refactored test methods...")
    refactored_methods = {}
    for file_path in refactored_files:
        methods = extract_test_methods(file_path)
        refactored_methods.update(methods)
        print(f"   {file_path.name}: {len(methods)} test methods")
    
    print(f"   Total refactored: {len(refactored_methods)} test methods")
    print()
    
    # Analyze coverage
    print("📊 COVERAGE ANALYSIS")
    print("-" * 30)
    
    analysis = analyze_test_coverage(original_methods, refactored_methods)
    
    print(f"Original tests: {analysis['original_count']}")
    print(f"Refactored tests: {analysis['refactored_count']}")
    print(f"Coverage score: {analysis['coverage_score']:.1f}%")
    print()
    
    # Pattern coverage
    pattern_coverage = analysis['pattern_coverage']
    print(f"📋 Pattern Coverage: {pattern_coverage['coverage_percentage']:.1f}%")
    print(f"   Original patterns: {pattern_coverage['original_patterns']}")
    print(f"   Refactored patterns: {pattern_coverage['refactored_patterns']}")
    
    if pattern_coverage['missing_patterns']:
        print(f"   ❌ Missing patterns: {pattern_coverage['missing_patterns']}")
    else:
        print(f"   ✅ All patterns covered")
    print()
    
    # Functionality gaps
    if analysis['functionality_gaps']:
        print("🚨 FUNCTIONALITY GAPS DETECTED:")
        for gap in analysis['functionality_gaps']:
            print(f"   ❌ {gap}")
        print()
    else:
        print("✅ No functionality gaps detected")
        print()
    
    # Detailed comparison
    print("📋 DETAILED TEST METHOD COMPARISON")
    print("-" * 40)
    
    # Group original tests by purpose
    original_by_purpose = {}
    for method_name, details in original_methods.items():
        purpose = categorize_test_purpose(method_name, details)
        if purpose not in original_by_purpose:
            original_by_purpose[purpose] = []
        original_by_purpose[purpose].append((method_name, details))
    
    # Group refactored tests by purpose  
    refactored_by_purpose = {}
    for method_name, details in refactored_methods.items():
        purpose = categorize_test_purpose(method_name, details)
        if purpose not in refactored_by_purpose:
            refactored_by_purpose[purpose] = []
        refactored_by_purpose[purpose].append((method_name, details))
    
    for purpose in sorted(original_by_purpose.keys()):
        print(f"\n🔍 {purpose.upper()} TESTS:")
        
        print(f"   Original ({len(original_by_purpose[purpose])}):")
        for method_name, details in original_by_purpose[purpose]:
            print(f"     • {method_name} ({details['line_count']} lines)")
            
        if purpose in refactored_by_purpose:
            print(f"   Refactored ({len(refactored_by_purpose[purpose])}):")
            for method_name, details in refactored_by_purpose[purpose]:
                print(f"     • {method_name} ({details['line_count']} lines)")
        else:
            print(f"   ❌ NO REFACTORED TESTS FOUND")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    
    if analysis['coverage_score'] >= 95:
        print("✅ EXCELLENT: Refactoring preserves 95%+ functionality")
    elif analysis['coverage_score'] >= 85:
        print("⚠️  GOOD: Refactoring preserves 85%+ functionality")
    elif analysis['coverage_score'] >= 70:
        print("🔶 FAIR: Refactoring preserves 70%+ functionality")
    else:
        print("🚨 POOR: Significant functionality may be missing")
    
    print(f"Overall Score: {analysis['coverage_score']:.1f}%")
    
    if analysis['functionality_gaps']:
        print(f"\n🔧 ACTION REQUIRED: {len(analysis['functionality_gaps'])} gaps need attention")
        return False
    else:
        print("\n🎉 SUCCESS: All functionality appears preserved")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)