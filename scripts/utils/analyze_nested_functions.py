#!/usr/bin/env python3
"""
Analyze nested function structure in test_config_system_health.py
to understand what needs to be flattened.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple


def analyze_nested_structure(file_path: Path) -> Dict:
    """Analyze the nested function structure in the test file."""
    content = file_path.read_text()
    tree = ast.parse(content)
    
    analysis = {
        'total_functions': 0,
        'class_methods': [],
        'all_test_functions': [],
        'nested_functions': {},
        'function_calls': {},
        'complex_methods': {}
    }
    
    # Find ALL functions that start with test_ (including nested ones)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            analysis['all_test_functions'].append(node.name)
    
    # Find the main test class
    test_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith('TestConfig'):
            test_class = node
            break
    
    if not test_class:
        return analysis
    
    # Analyze each method in the test class
    for method in test_class.body:
        if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
            analysis['class_methods'].append(method.name)
            
            # Find nested functions within this method
            nested_funcs = []
            function_calls = []
            
            for node in ast.walk(method):
                if isinstance(node, ast.FunctionDef) and node != method:
                    nested_funcs.append(node.name)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id.startswith('test_'):
                        function_calls.append(node.func.id)
            
            # Store info for all methods (even without nested functions)
            method_lines = method.end_lineno - method.lineno if hasattr(method, 'end_lineno') else 0
            analysis['complex_methods'][method.name] = {
                'lines': method_lines,
                'nested_count': len(nested_funcs),
                'docstring': ast.get_docstring(method) or "",
                'nested_functions': nested_funcs
            }
            
            if nested_funcs:
                analysis['nested_functions'][method.name] = nested_funcs
                analysis['function_calls'][method.name] = function_calls
    
    analysis['total_functions'] = len(analysis['class_methods'])
    return analysis


def generate_flat_method_mapping(analysis: Dict) -> List[Dict]:
    """Generate mapping for converting nested functions to flat methods."""
    flat_methods = []
    
    for parent_method, nested_funcs in analysis['nested_functions'].items():
        parent_info = analysis['complex_methods'][parent_method]
        
        # Create entry for parent method (potentially simplified)
        flat_methods.append({
            'original_name': parent_method,
            'new_name': parent_method,
            'type': 'coordinator',
            'description': f"Coordinates {len(nested_funcs)} sub-tests",
            'complexity': parent_info['lines']
        })
        
        # Create entries for each nested function
        for nested_func in nested_funcs:
            flat_name = f"{parent_method}_{nested_func}".replace('test_test_', 'test_')
            
            flat_methods.append({
                'original_name': nested_func,
                'new_name': flat_name,
                'type': 'extracted',
                'parent': parent_method,
                'description': f"Extracted from {parent_method}",
                'complexity': 'medium'
            })
    
    return flat_methods


def main():
    """Main analysis function."""
    file_path = Path("tests/health/test_config_system_health.py")
    
    print("🔍 NESTED FUNCTION STRUCTURE ANALYSIS")
    print("=" * 50)
    
    analysis = analyze_nested_structure(file_path)
    
    print(f"📊 SUMMARY:")
    print(f"   Total class methods: {analysis['total_functions']}")
    print(f"   Methods with nested functions: {len(analysis['nested_functions'])}")
    print(f"   Total nested functions: {sum(len(funcs) for funcs in analysis['nested_functions'].values())}")
    print()
    
    print("📋 COMPLEX METHODS (with nested functions):")
    for method_name, nested_funcs in analysis['nested_functions'].items():
        complexity = analysis['complex_methods'][method_name]
        print(f"   🔸 {method_name}:")
        print(f"     • Lines: {complexity['lines']}")
        print(f"     • Nested functions: {len(nested_funcs)}")
        print(f"     • Functions: {', '.join(nested_funcs)}")
        if complexity['docstring']:
            doc_preview = complexity['docstring'][:100].replace('\n', ' ')
            print(f"     • Description: {doc_preview}...")
        print()
    
    print("🏗️ FLAT ARCHITECTURE MAPPING:")
    flat_mapping = generate_flat_method_mapping(analysis)
    
    coordinators = [m for m in flat_mapping if m['type'] == 'coordinator']
    extracted = [m for m in flat_mapping if m['type'] == 'extracted']
    
    print(f"   Coordinator methods: {len(coordinators)}")
    print(f"   Extracted methods: {len(extracted)}")
    print(f"   Total flat methods: {len(flat_mapping)}")
    print()
    
    print("📝 DETAILED FLAT METHOD LIST:")
    for method in flat_mapping:
        symbol = "🎯" if method['type'] == 'coordinator' else "📤"
        print(f"   {symbol} {method['new_name']}")
        print(f"     • Type: {method['type']}")
        print(f"     • {method['description']}")
        if 'parent' in method:
            print(f"     • Parent: {method['parent']}")
        print()
    
    print("=" * 50)
    print("✅ Analysis complete. Ready for flat architecture rewrite.")
    
    return analysis, flat_mapping


if __name__ == "__main__":
    analysis, mapping = main()