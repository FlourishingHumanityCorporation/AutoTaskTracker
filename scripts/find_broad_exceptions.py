#!/usr/bin/env python3
"""Find and report all broad exception handlers in the codebase."""

import re
from pathlib import Path
from typing import List, Tuple

def find_broad_exceptions(root_path: Path) -> List[Tuple[Path, int, str]]:
    """Find all instances of broad exception handlers."""
    broad_exceptions = []
    
    # Pattern to find broad exceptions
    patterns = [
        r'except\s+Exception\s*:',
        r'except\s+Exception\s+as\s+\w+\s*:',
        r'except\s*:'  # Bare except
    ]
    
    for py_file in root_path.rglob('*.py'):
        # Skip deprecated and test files for now
        if 'deprecated' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        # Get context (previous line)
                        context = lines[i-2] if i > 1 else ""
                        broad_exceptions.append((py_file, i, line.strip()))
                        break
                        
        except (OSError, UnicodeDecodeError):
            continue
            
    return broad_exceptions

def main():
    """Main function to find and report broad exceptions."""
    # Focus on the testing module first
    test_health_path = Path('tests/health/testing')
    
    if not test_health_path.exists():
        print(f"Path {test_health_path} does not exist")
        return
        
    exceptions = find_broad_exceptions(test_health_path)
    
    # Group by file
    by_file = {}
    for file_path, line_num, line in exceptions:
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append((line_num, line))
    
    # Report
    print(f"Found {len(exceptions)} broad exception handlers in {len(by_file)} files\n")
    
    for file_path, occurrences in by_file.items():
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path
        print(f"\n{rel_path}:")
        for line_num, line in sorted(occurrences):
            print(f"  Line {line_num}: {line}")
    
    print(f"\nTotal files with broad exceptions: {len(by_file)}")
    print(f"Total broad exceptions: {len(exceptions)}")

if __name__ == "__main__":
    main()