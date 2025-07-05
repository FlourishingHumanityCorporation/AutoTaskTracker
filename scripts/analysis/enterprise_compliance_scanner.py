#!/usr/bin/env python3
"""
Enterprise-Grade Compliance Scanner for AutoTaskTracker.

Comprehensive scanning for code quality, architecture compliance, and security issues.
This is the authoritative scanner for production readiness.
"""

import os
import re
import sys
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Set, Any
import argparse
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class ComplianceViolation:
    def __init__(self, file_path: str, line_number: int, violation_type: str, 
                 description: str, fix_suggestion: str, severity: str = "error"):
        self.file_path = file_path
        self.line_number = line_number
        self.violation_type = violation_type
        self.description = description
        self.fix_suggestion = fix_suggestion
        self.severity = severity

class EnterpriseComplianceScanner:
    def __init__(self):
        self.violations = []
        self.excluded_patterns = [
            r'test_.*\.py$', r'.*_test\.py$', r'/tests/', r'__pycache__',
            r'\.pyc$', r'\.git/', r'\.md$', r'/docs/', r'/examples/'
        ]
        
        # Architecture compliance rules
        self.compliance_rules = {
            'database_access': {
                'pattern': r'sqlite3\.connect\(',
                'description': 'Direct SQLite connections violate DatabaseManager pattern',
                'fix': 'Use DatabaseManager().get_connection() instead',
                'severity': 'critical',
                'allowed_files': ['/database.py']
            },
            'config_hardcoding': {
                'patterns': [
                    r'\b(?:8502|8503|8504|8505|8506|8507|8508|8509|8510|8839|8840|11434)\b',
                    r'http://localhost:\d+',
                    r'~?/\.memos/database\.db',
                    r'~?/\.memos/'
                ],
                'description': 'Hardcoded configuration values',
                'fix': 'Use config.get_service_url(), config.get_db_path(), etc.',
                'severity': 'error'
            },
            'print_statements': {
                'pattern': r'\bprint\s*\(',
                'description': 'Print statements in production code',
                'fix': 'Use logging.getLogger(__name__).info() instead',
                'severity': 'warning',
                'allowed_files': ['/main.py', '/cli.py', '/debug.py']
            },
            'bare_except': {
                'pattern': r'except\s*:',
                'description': 'Bare except clauses hide errors',
                'fix': 'Specify exception types: except ValueError:',
                'severity': 'error'
            },
            'sys_path_hacks': {
                'pattern': r'sys\.path\.(append|insert)',
                'description': 'sys.path manipulation indicates import issues',
                'fix': 'Use proper package imports or PYTHONPATH',
                'severity': 'warning'
            }
        }

    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from scanning."""
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in self.excluded_patterns)

    def scan_file(self, file_path: Path) -> List[ComplianceViolation]:
        """Scan a single file for compliance violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, PermissionError):
            return violations

        relative_path = str(file_path.relative_to(project_root))
        
        for rule_name, rule in self.compliance_rules.items():
            # Check if file is allowed for this rule
            if 'allowed_files' in rule:
                if any(allowed in relative_path for allowed in rule['allowed_files']):
                    continue
            
            patterns = rule.get('patterns', [rule.get('pattern')])
            for pattern in patterns:
                if not pattern:
                    continue
                    
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        violations.append(ComplianceViolation(
                            file_path=relative_path,
                            line_number=line_num,
                            violation_type=rule_name,
                            description=rule['description'],
                            fix_suggestion=rule['fix'],
                            severity=rule['severity']
                        ))
        
        return violations

    def scan_architecture_patterns(self) -> List[ComplianceViolation]:
        """Scan for architectural anti-patterns."""
        violations = []
        
        # Find Python files
        python_files = []
        for pattern in ['autotasktracker/**/*.py', 'scripts/**/*.py']:
            python_files.extend(project_root.glob(pattern))
        
        # Filter excluded files
        python_files = [f for f in python_files if not self.should_exclude_file(f)]
        
        for file_path in python_files:
            violations.extend(self.scan_file(file_path))
        
        return violations

    def check_import_quality(self) -> List[ComplianceViolation]:
        """Check for import quality issues."""
        violations = []
        
        # Find files with problematic import patterns
        python_files = list(project_root.glob('autotasktracker/**/*.py'))
        python_files = [f for f in python_files if not self.should_exclude_file(f)]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for circular import risks
                if 'from autotasktracker import' in content and 'from autotasktracker.' in content:
                    violations.append(ComplianceViolation(
                        file_path=str(file_path.relative_to(project_root)),
                        line_number=1,
                        violation_type='import_quality',
                        description='Mixed import styles may cause circular imports',
                        fix_suggestion='Use consistent import style',
                        severity='warning'
                    ))
                    
                # Check for wildcard imports
                if re.search(r'from .* import \*', content):
                    violations.append(ComplianceViolation(
                        file_path=str(file_path.relative_to(project_root)),
                        line_number=1,
                        violation_type='import_quality',
                        description='Wildcard imports pollute namespace',
                        fix_suggestion='Import specific names',
                        severity='warning'
                    ))
                    
            except Exception:
                continue
        
        return violations

    def check_database_consistency(self) -> List[ComplianceViolation]:
        """Check for database access consistency."""
        violations = []
        
        # Find all files that access database
        python_files = list(project_root.glob('scripts/**/*.py'))
        python_files = [f for f in python_files if not self.should_exclude_file(f)]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Files that use DatabaseManager should not also use sqlite3.connect
                if 'DatabaseManager' in content and 'sqlite3.connect' in content:
                    violations.append(ComplianceViolation(
                        file_path=str(file_path.relative_to(project_root)),
                        line_number=1,
                        violation_type='database_consistency',
                        description='Mixed database access patterns (DatabaseManager + sqlite3)',
                        fix_suggestion='Use only DatabaseManager for database access',
                        severity='error'
                    ))
                    
            except Exception:
                continue
        
        return violations

    def generate_report(self, output_format='text') -> str:
        """Generate compliance report."""
        all_violations = []
        
        # Run all checks
        all_violations.extend(self.scan_architecture_patterns())
        all_violations.extend(self.check_import_quality())
        all_violations.extend(self.check_database_consistency())
        
        # Group by severity
        critical = [v for v in all_violations if v.severity == 'critical']
        errors = [v for v in all_violations if v.severity == 'error']
        warnings = [v for v in all_violations if v.severity == 'warning']
        
        if output_format == 'json':
            return json.dumps({
                'scan_time': datetime.now().isoformat(),
                'total_violations': len(all_violations),
                'critical': len(critical),
                'errors': len(errors),
                'warnings': len(warnings),
                'violations': [
                    {
                        'file': v.file_path,
                        'line': v.line_number,
                        'type': v.violation_type,
                        'description': v.description,
                        'fix': v.fix_suggestion,
                        'severity': v.severity
                    } for v in all_violations
                ]
            }, indent=2)
        
        # Text format
        report = []
        report.append(f"🔍 Enterprise Compliance Scan Results")
        report.append(f"📊 Total: {len(all_violations)} violations")
        report.append(f"🚨 Critical: {len(critical)}")
        report.append(f"❌ Errors: {len(errors)}")
        report.append(f"⚠️  Warnings: {len(warnings)}")
        report.append("")
        
        if critical:
            report.append("🚨 CRITICAL VIOLATIONS:")
            for v in critical:
                report.append(f"  {v.file_path}:{v.line_number} - {v.description}")
                report.append(f"    Fix: {v.fix_suggestion}")
            report.append("")
        
        if errors:
            report.append("❌ ERROR VIOLATIONS:")
            for v in errors:
                report.append(f"  {v.file_path}:{v.line_number} - {v.description}")
                report.append(f"    Fix: {v.fix_suggestion}")
            report.append("")
        
        if warnings:
            report.append("⚠️  WARNING VIOLATIONS:")
            for v in warnings[:10]:  # Limit warnings shown
                report.append(f"  {v.file_path}:{v.line_number} - {v.description}")
            if len(warnings) > 10:
                report.append(f"  ... and {len(warnings) - 10} more warnings")
            report.append("")
        
        if len(all_violations) == 0:
            report.append("✅ No compliance violations found!")
        
        return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser(description='Enterprise compliance scanner')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='Output format')
    parser.add_argument('--output', help='Output file (default: stdout)')
    parser.add_argument('--ci', action='store_true', 
                        help='CI mode - exit 1 if critical/error violations found')
    
    args = parser.parse_args()
    
    scanner = EnterpriseComplianceScanner()
    report = scanner.generate_report(args.format)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)
    
    # CI mode exit codes
    if args.ci:
        violations = []
        violations.extend(scanner.scan_architecture_patterns())
        violations.extend(scanner.check_import_quality())
        violations.extend(scanner.check_database_consistency())
        
        critical_errors = [v for v in violations if v.severity in ['critical', 'error']]
        if critical_errors:
            print(f"\n💥 CI FAILURE: {len(critical_errors)} critical/error violations")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())