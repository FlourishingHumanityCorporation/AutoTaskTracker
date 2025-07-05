#!/usr/bin/env python3
"""Comprehensive import test for AutoTaskTracker."""

import sys
import importlib
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_module_import(module_name):
    """Test importing a single module."""
    try:
        importlib.import_module(module_name)
        return True, None
    except Exception as e:
        return False, str(e)

def find_python_modules(root_path):
    """Find all Python modules in the project."""
    modules = []
    root = Path(root_path)
    
    for py_file in root.rglob("*.py"):
        # Skip test files, setup.py, and this file
        if (py_file.name.startswith("test_") or 
            py_file.name == "setup.py" or
            py_file == Path(__file__) or
            "__pycache__" in str(py_file)):
            continue
            
        # Convert file path to module path
        relative_path = py_file.relative_to(root.parent)
        module_path = str(relative_path.with_suffix("")).replace("/", ".")
        
        # Skip if it's a script (not in a package)
        if not module_path.startswith("autotasktracker."):
            continue
            
        modules.append(module_path)
    
    return sorted(modules)

def main():
    """Run import tests."""
    print("Testing AutoTaskTracker imports...\n")
    
    # Find all modules
    project_root = Path(__file__).parent / "autotasktracker"
    modules = find_python_modules(project_root)
    
    print(f"Found {len(modules)} modules to test\n")
    
    failed_imports = []
    
    for module in modules:
        success, error = test_module_import(module)
        if success:
            print(f"✓ {module}")
        else:
            print(f"✗ {module}: {error}")
            failed_imports.append((module, error))
    
    print(f"\n{'='*60}")
    print(f"Import Test Summary:")
    print(f"{'='*60}")
    print(f"Total modules: {len(modules)}")
    print(f"Successful imports: {len(modules) - len(failed_imports)}")
    print(f"Failed imports: {len(failed_imports)}")
    
    if failed_imports:
        print(f"\nFailed imports:")
        for module, error in failed_imports:
            print(f"  - {module}: {error}")
        return 1
    else:
        print("\nAll imports successful!")
        return 0

if __name__ == "__main__":
    sys.exit(main())