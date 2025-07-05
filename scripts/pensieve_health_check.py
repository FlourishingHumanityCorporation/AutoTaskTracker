#!/usr/bin/env python3
"""
Pensieve Integration Health Check CLI

Run health checks on Pensieve integration patterns with various options.

Usage:
    python scripts/pensieve_health_check.py [options]

Options:
    --fix           Automatically fix simple issues
    --incremental   Only check changed files (git diff)
    --since COMMIT  Check files changed since specific commit
    --report FORMAT Generate report (console, json, html)
    --parallel N    Number of parallel workers (default: CPU count)
"""

import argparse
import os
import sys
import subprocess
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="Pensieve Integration Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full health check
  python scripts/pensieve_health_check.py
  
  # Auto-fix simple issues
  python scripts/pensieve_health_check.py --fix
  
  # Check only changed files in current branch
  python scripts/pensieve_health_check.py --incremental
  
  # Check files changed in last 3 commits
  python scripts/pensieve_health_check.py --since HEAD~3
  
  # Generate JSON report with auto-fix
  python scripts/pensieve_health_check.py --fix --report json
        """
    )
    
    parser.add_argument(
        '--fix', 
        action='store_true',
        help='Automatically fix simple issues (metadata keys, error logging)'
    )
    
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Only check files changed since last commit'
    )
    
    parser.add_argument(
        '--since',
        metavar='COMMIT',
        help='Check files changed since specific commit (e.g., HEAD~3, main)'
    )
    
    parser.add_argument(
        '--report',
        choices=['console', 'json', 'html'],
        default='console',
        help='Report format (default: console)'
    )
    
    parser.add_argument(
        '--parallel',
        type=int,
        metavar='N',
        help='Number of parallel workers (default: CPU count)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Set environment variables based on arguments
    if args.fix:
        os.environ['PENSIEVE_AUTO_FIX'] = '1'
        print("🔧 Auto-fix mode enabled")
    
    if args.incremental or args.since:
        os.environ['PENSIEVE_TEST_INCREMENTAL'] = '1'
        if args.since:
            os.environ['PENSIEVE_SINCE_COMMIT'] = args.since
        print(f"📝 Incremental mode: checking files changed since {args.since or 'HEAD~1'}")
    
    if args.parallel:
        os.environ['PENSIEVE_MAX_WORKERS'] = str(args.parallel)
    
    # Run the health test
    print("\n🏥 Running Pensieve Integration Health Check...\n")
    
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/health/test_pensieve_integration_health.py',
        '-v' if args.verbose else '-q',
        '--tb=short',
        '--timeout=300'
    ]
    
    if args.report == 'json':
        cmd.extend(['--json-report', '--json-report-file=pensieve_health_report.json'])
    
    # Run the test
    result = subprocess.run(cmd, capture_output=not args.verbose)
    
    # Process results based on report format
    if args.report == 'console':
        if result.returncode != 0 and not args.verbose:
            print(result.stdout.decode('utf-8'))
            print(result.stderr.decode('utf-8'))
    
    elif args.report == 'json':
        # Load and display summary
        try:
            with open('pensieve_health_summary.json', 'r') as f:
                summary = json.load(f)
            
            print("\n📊 Health Check Summary:")
            print(f"   Files Analyzed: {summary['files_analyzed']}")
            print(f"   Mode: {summary['mode']}")
            
            if summary.get('fixes_applied'):
                print(f"\n✅ Applied {len(summary['fixes_applied'])} fixes:")
                for fix in summary['fixes_applied'][:5]:
                    print(f"   - {fix}")
                if len(summary['fixes_applied']) > 5:
                    print(f"   ... and {len(summary['fixes_applied']) - 5} more")
        
        except FileNotFoundError:
            print("⚠️  No summary report generated")
    
    elif args.report == 'html':
        print("📄 HTML report generation not implemented yet")
        print("   Use --report json for now")
    
    # Show tips based on results
    if result.returncode != 0:
        print("\n💡 Tips:")
        if not args.fix:
            print("   - Run with --fix to automatically fix simple issues")
        print("   - Run with --incremental to check only changed files")
        print("   - Run with -v for verbose output")
        print("   - Check logs for detailed error information")
    else:
        print("\n✅ All health checks passed!")
    
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())