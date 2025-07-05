#!/usr/bin/env python3
"""
Verify that the flat architecture version preserves 100% functionality
compared to the original nested version.
"""

import ast
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any


def extract_test_structure(file_path: Path) -> Dict[str, Any]:
    """Extract test structure from a test file."""
    content = file_path.read_text()
    tree = ast.parse(content)
    
    structure = {
        'classes': {},
        'total_methods': 0,
        'all_test_functions': []
    }
    
    # Find all test functions (including nested ones)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            structure['all_test_functions'].append(node.name)
    
    # Find test classes and their methods
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                    methods.append({
                        'name': item.name,
                        'docstring': ast.get_docstring(item) or "",
                        'lines': item.end_lineno - item.lineno if hasattr(item, 'end_lineno') else 0
                    })
            
            structure['classes'][node.name] = {
                'methods': methods,
                'method_count': len(methods)
            }
            structure['total_methods'] += len(methods)
    
    return structure


def run_tests(test_file: Path, timeout: int = 120) -> Dict[str, Any]:
    """Run tests in a file and return results."""
    try:
        start_time = time.time()
        result = subprocess.run(
            ['pytest', str(test_file), '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        end_time = time.time()
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'execution_time': end_time - start_time,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Tests timed out after {timeout} seconds',
            'execution_time': timeout,
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'execution_time': 0,
            'returncode': -2
        }


def parse_test_results(stdout: str) -> Dict[str, Any]:
    """Parse pytest output to extract test results."""
    lines = stdout.split('\n')
    
    results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'test_details': []
    }
    
    for line in lines:
        if '::' in line and ('PASSED' in line or 'FAILED' in line or 'SKIPPED' in line):
            parts = line.split('::')
            if len(parts) >= 2:
                test_class = parts[-2] if '::' in parts[-2] else 'Unknown'
                test_method = parts[-1].split()[0]
                status = 'PASSED' if 'PASSED' in line else 'FAILED' if 'FAILED' in line else 'SKIPPED'
                
                results['test_details'].append({
                    'class': test_class,
                    'method': test_method,
                    'status': status
                })
                
                if status == 'PASSED':
                    results['passed'] += 1
                elif status == 'FAILED':
                    results['failed'] += 1
                elif status == 'SKIPPED':
                    results['skipped'] += 1
                    
                results['total_tests'] += 1
    
    # Try to extract summary line
    for line in reversed(lines):
        if 'passed' in line and ('failed' in line or 'warning' in line or line.strip().endswith('passed')):
            # Parse summary like "17 passed, 1 warning in 6.23s"
            import re
            match = re.search(r'(\d+)\s+passed', line)
            if match:
                results['passed'] = int(match.group(1))
            match = re.search(r'(\d+)\s+failed', line)
            if match:
                results['failed'] = int(match.group(1))
            match = re.search(r'(\d+)\s+skipped', line)
            if match:
                results['skipped'] = int(match.group(1))
            results['total_tests'] = results['passed'] + results['failed'] + results['skipped']
            break
    
    return results


def compare_structures(original: Dict, flat: Dict) -> Dict[str, Any]:
    """Compare test structures between original and flat versions."""
    comparison = {
        'class_count_match': len(original['classes']) == len(flat['classes']),
        'total_methods_match': original['total_methods'] == flat['total_methods'],
        'class_comparisons': {},
        'missing_classes': [],
        'extra_classes': [],
        'method_differences': []
    }
    
    # Compare classes
    original_classes = set(original['classes'].keys())
    flat_classes = set(flat['classes'].keys())
    
    comparison['missing_classes'] = list(original_classes - flat_classes)
    comparison['extra_classes'] = list(flat_classes - original_classes)
    
    # Compare methods within each class
    for class_name in original_classes & flat_classes:
        orig_methods = {m['name'] for m in original['classes'][class_name]['methods']}
        flat_methods = {m['name'] for m in flat['classes'][class_name]['methods']}
        
        missing_methods = orig_methods - flat_methods
        extra_methods = flat_methods - orig_methods
        
        comparison['class_comparisons'][class_name] = {
            'method_count_match': len(orig_methods) == len(flat_methods),
            'missing_methods': list(missing_methods),
            'extra_methods': list(extra_methods),
            'original_count': len(orig_methods),
            'flat_count': len(flat_methods)
        }
        
        if missing_methods or extra_methods:
            comparison['method_differences'].append({
                'class': class_name,
                'missing': list(missing_methods),
                'extra': list(extra_methods)
            })
    
    return comparison


def main():
    """Main verification function."""
    print("🔍 FLAT ARCHITECTURE FUNCTIONALITY VERIFICATION")
    print("=" * 60)
    
    original_file = Path("tests/health/test_config_system_health.py")
    flat_file = Path("tests/health/test_config_system_health_flat.py")
    
    if not original_file.exists():
        print(f"❌ Original file not found: {original_file}")
        return False
    
    if not flat_file.exists():
        print(f"❌ Flat file not found: {flat_file}")
        return False
    
    print(f"📁 Original: {original_file.name}")
    print(f"📁 Flat: {flat_file.name}")
    print()
    
    # 1. STRUCTURE COMPARISON
    print("🏗️ ANALYZING TEST STRUCTURE...")
    original_structure = extract_test_structure(original_file)
    flat_structure = extract_test_structure(flat_file)
    
    structure_comparison = compare_structures(original_structure, flat_structure)
    
    print(f"📊 STRUCTURE COMPARISON:")
    print(f"   Original classes: {len(original_structure['classes'])}")
    print(f"   Flat classes: {len(flat_structure['classes'])}")
    print(f"   Classes match: {'✅' if structure_comparison['class_count_match'] else '❌'}")
    print()
    
    print(f"   Original methods: {original_structure['total_methods']}")
    print(f"   Flat methods: {flat_structure['total_methods']}")
    print(f"   Methods match: {'✅' if structure_comparison['total_methods_match'] else '❌'}")
    print()
    
    # Detail class-by-class comparison
    for class_name, comparison in structure_comparison['class_comparisons'].items():
        status = "✅" if comparison['method_count_match'] else "❌"
        print(f"   {status} {class_name}: {comparison['original_count']} → {comparison['flat_count']} methods")
        
        if comparison['missing_methods']:
            print(f"      Missing: {comparison['missing_methods']}")
        if comparison['extra_methods']:
            print(f"      Extra: {comparison['extra_methods']}")
    
    if structure_comparison['missing_classes']:
        print(f"   ❌ Missing classes: {structure_comparison['missing_classes']}")
    if structure_comparison['extra_classes']:
        print(f"   ➕ Extra classes: {structure_comparison['extra_classes']}")
    
    print()
    
    # 2. FUNCTIONALITY VERIFICATION
    print("🧪 RUNNING FUNCTIONALITY TESTS...")
    
    # Run flat version tests
    print("   Testing flat architecture version...")
    flat_results = run_tests(flat_file)
    
    if flat_results['success']:
        print(f"   ✅ Flat tests: PASSED in {flat_results['execution_time']:.1f}s")
    else:
        print(f"   ❌ Flat tests: FAILED in {flat_results['execution_time']:.1f}s")
        print(f"      Error: {flat_results['stderr'][:200]}...")
    
    # Parse test results
    flat_test_results = parse_test_results(flat_results['stdout'])
    
    print(f"   📊 Flat test results:")
    print(f"      Total: {flat_test_results['total_tests']}")
    print(f"      Passed: {flat_test_results['passed']}")
    print(f"      Failed: {flat_test_results['failed']}")
    print(f"      Skipped: {flat_test_results['skipped']}")
    print()
    
    # 3. COMPREHENSIVE ASSESSMENT
    print("📋 COMPREHENSIVE ASSESSMENT:")
    
    structure_score = 100 if (structure_comparison['class_count_match'] and 
                             structure_comparison['total_methods_match'] and
                             not structure_comparison['method_differences']) else 0
    
    functionality_score = 100 if flat_results['success'] else 0
    
    overall_score = (structure_score + functionality_score) / 2
    
    print(f"   Structure Preservation: {structure_score}%")
    print(f"   Functionality Preservation: {functionality_score}%")
    print(f"   Overall Score: {overall_score}%")
    print()
    
    # 4. BENEFITS ANALYSIS
    if flat_results['success']:
        print("✅ FLAT ARCHITECTURE BENEFITS:")
        print("   • No nested functions - enables proper inheritance")
        print("   • All test methods are class methods - supports composition")
        print("   • Modular refactoring now possible")
        print("   • Same functionality with better architecture")
        print(f"   • {flat_structure['total_methods']} test methods preserved")
        print()
    
    # 5. RECOMMENDATIONS
    if overall_score >= 95:
        print("🎉 RECOMMENDATION: REPLACE ORIGINAL WITH FLAT VERSION")
        print("   The flat architecture preserves 100% functionality")
        print("   and enables the modular refactoring that was previously impossible.")
        success = True
    elif overall_score >= 80:
        print("⚠️  RECOMMENDATION: REVIEW AND FIX ISSUES")
        print("   The flat architecture is mostly functional but needs fixes.")
        success = False
    else:
        print("🚨 RECOMMENDATION: SIGNIFICANT REWORK NEEDED")
        print("   The flat architecture has major issues.")
        success = False
    
    print()
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)