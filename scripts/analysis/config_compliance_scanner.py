#!/usr/bin/env python3
"""
Config Compliance Scanner for AutoTaskTracker.

Scans the codebase for hardcoded values that should use config instead.
Prevents future config compliance violations.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Hardcoded patterns that should use config
HARDCODED_PATTERNS = {
    'direct_sqlite': {
        'pattern': r'sqlite3\.connect\(',
        'description': 'Direct SQLite connections',
        'should_use': 'DatabaseManager().get_connection() or DatabaseManager()'
    },
    'ports': {
        'pattern': r'\b(?:8502|8503|8504|8505|8506|8507|8508|8509|8510|8839|8840|11434)\b',
        'description': 'Hardcoded port numbers',
        'should_use': 'config.TASK_BOARD_PORT, config.ANALYTICS_PORT, etc.'
    },
    'localhost_urls': {
        'pattern': r'http://localhost:\d+',
        'description': 'Hardcoded localhost URLs',
        'should_use': 'config.get_service_url() or f"http://{config.SERVER_HOST}:{port}"'
    },
    'database_paths': {
        'pattern': r'~?/\.memos/database\.db',
        'description': 'Hardcoded database paths',
        'should_use': 'config.get_db_path()'
    },
    'temp_paths': {
        'pattern': r'/tmp/[a-zA-Z_]\w*\.db',
        'description': 'Hardcoded temp database paths',
        'should_use': 'Use environment variables or config'
    },
    'memos_paths': {
        'pattern': r'~?/\.memos/',
        'description': 'Hardcoded memos directory paths',
        'should_use': 'config.memos_dir or config paths'
    }
}

# Files to exclude from scanning
EXCLUDED_PATTERNS = [
    # Test files are allowed to have hardcoded values for testing
    r'test_.*\.py$',
    r'.*_test\.py$',
    r'/tests/',
    # Config file itself defines the defaults
    r'/config\.py$',
    # Documentation and examples
    r'\.md$',
    r'/docs/',
    r'/examples/',
    # Cache and temp files
    r'__pycache__',
    r'\.pyc$',
    r'\.git/',
    # Migration scripts may reference hardcoded paths
    r'migrate.*\.py$',
    # DatabaseManager itself is allowed to use sqlite3.connect
    r'/database\.py$'
]

# Files that require config import
REQUIRED_CONFIG_IMPORTS = [
    'from autotasktracker.config import get_config',
    'from autotasktracker.config import config',
    'import autotasktracker.config',
    'get_config'
]

def should_exclude_file(file_path: Path) -> bool:
    """Check if file should be excluded from scanning."""
    file_str = str(file_path)
    return any(re.search(pattern, file_str) for pattern in EXCLUDED_PATTERNS)

def has_config_import(content: str) -> bool:
    """Check if file imports config properly."""
    return any(imp in content for imp in REQUIRED_CONFIG_IMPORTS)

def scan_file_for_violations(file_path: Path) -> List[Dict[str, str]]:
    """Scan a single file for config violations."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return violations
    
    # Check for hardcoded patterns
    for pattern_name, pattern_info in HARDCODED_PATTERNS.items():
        matches = re.findall(pattern_info['pattern'], content)
        if matches:
            # Skip if file properly imports config (might be in comments/strings)
            if has_config_import(content):
                # Special case: migration commands in comments are OK
                if pattern_name == 'memos_paths' and 'migration' in content.lower():
                    continue
                # Dashboard files must use config, no exceptions
                if 'dashboards/' in str(file_path):
                    violations.append({
                        'file': str(file_path.relative_to(project_root)),
                        'pattern': pattern_name,
                        'matches': matches,
                        'description': pattern_info['description'],
                        'should_use': pattern_info['should_use'],
                        'severity': 'error'
                    })
                else:
                    continue
            else:
                violations.append({
                    'file': str(file_path.relative_to(project_root)),
                    'pattern': pattern_name,
                    'matches': matches,
                    'description': pattern_info['description'],
                    'should_use': pattern_info['should_use'],
                    'severity': 'error'
                })
    
    return violations

def scan_codebase() -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Scan entire codebase for config violations."""
    hardcoded_violations = []
    missing_import_violations = []
    
    # Find all Python files in autotasktracker/ and scripts/
    python_files = []
    for pattern in ['autotasktracker/**/*.py', 'scripts/**/*.py']:
        python_files.extend(project_root.glob(pattern))
    
    # Filter out excluded files
    python_files = [f for f in python_files if not should_exclude_file(f)]
    
    for file_path in python_files:
        violations = scan_file_for_violations(file_path)
        hardcoded_violations.extend(violations)
        
        # Check for missing config imports in dashboard files
        if 'dashboards/' in str(file_path) and file_path.suffix == '.py':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for port usage without config import
                has_port_usage = re.search(r'\bport\s*[=:]', content, re.IGNORECASE)
                has_config = has_config_import(content)
                
                if has_port_usage and not has_config:
                    missing_import_violations.append({
                        'file': str(file_path.relative_to(project_root)),
                        'issue': 'Dashboard file uses ports but missing config import',
                        'should_add': 'from autotasktracker.config import get_config'
                    })
            except (UnicodeDecodeError, PermissionError):
                continue
    
    return hardcoded_violations, missing_import_violations

def generate_fix_suggestions(violations: List[Dict[str, str]]) -> List[str]:
    """Generate fix suggestions for violations."""
    suggestions = []
    
    # Group violations by file
    by_file = {}
    for violation in violations:
        file_path = violation['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(violation)
    
    for file_path, file_violations in by_file.items():
        suggestions.append(f"\n🔧 Fix {file_path}:")
        
        # Check if needs config import
        port_violations = [v for v in file_violations if v['pattern'] == 'ports']
        url_violations = [v for v in file_violations if v['pattern'] == 'localhost_urls']
        
        if port_violations or url_violations:
            suggestions.append("  1. Add config import:")
            suggestions.append("     from autotasktracker.config import get_config")
            suggestions.append("")
            
        for violation in file_violations:
            matches_str = ', '.join(str(m) for m in violation['matches'])
            suggestions.append(f"  2. Replace {violation['description']}: {matches_str}")
            suggestions.append(f"     Use: {violation['should_use']}")
            suggestions.append("")
    
    return suggestions

def main():
    parser = argparse.ArgumentParser(description='Scan for config compliance violations')
    parser.add_argument('--fix', action='store_true', help='Generate fix suggestions')
    parser.add_argument('--ci', action='store_true', help='CI mode - exit 1 if violations found')
    parser.add_argument('--quiet', action='store_true', help='Only show violations count')
    
    args = parser.parse_args()
    
    print("🔍 Scanning codebase for config compliance violations...")
    
    hardcoded_violations, missing_import_violations = scan_codebase()
    total_violations = len(hardcoded_violations) + len(missing_import_violations)
    
    if args.quiet:
        print(f"Found {total_violations} violations")
        return 1 if total_violations > 0 and args.ci else 0
    
    if hardcoded_violations:
        print(f"\n🚨 HARDCODED VALUE VIOLATIONS ({len(hardcoded_violations)}):")
        for violation in hardcoded_violations:
            matches_str = ', '.join(str(m) for m in violation['matches'])
            print(f"  ❌ {violation['file']}: {violation['description']} - {matches_str}")
            print(f"     Should use: {violation['should_use']}")
    
    if missing_import_violations:
        print(f"\n🚨 MISSING CONFIG IMPORT VIOLATIONS ({len(missing_import_violations)}):")
        for violation in missing_import_violations:
            print(f"  ❌ {violation['file']}: {violation['issue']}")
            print(f"     Should add: {violation['should_add']}")
    
    if total_violations == 0:
        print("\n✅ No config compliance violations found!")
        return 0
    
    print(f"\n📊 SUMMARY: {total_violations} violations found")
    
    if args.fix:
        suggestions = generate_fix_suggestions(hardcoded_violations)
        if suggestions:
            print("\n🔧 FIX SUGGESTIONS:")
            for suggestion in suggestions:
                print(suggestion)
    
    if args.ci:
        print(f"\n💥 CI FAILURE: {total_violations} config compliance violations must be fixed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())