#!/usr/bin/env python3
"""
Monitor code complexity over time for technical debt tracking.

Tracks:
- Cyclomatic complexity
- Maintainability index  
- File sizes
- Function counts
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def run_radon_complexity() -> Dict[str, Any]:
    """Run radon complexity analysis."""
    try:
        # Run complexity analysis
        result = subprocess.run(
            ['radon', 'cc', 'autotasktracker/', '-j'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Radon CC failed: {result.stderr}")
            return {}
    except Exception as e:
        print(f"Error running radon cc: {e}")
        return {}


def run_radon_maintainability() -> Dict[str, Any]:
    """Run radon maintainability analysis."""
    try:
        result = subprocess.run(
            ['radon', 'mi', 'autotasktracker/', '-j'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Radon MI failed: {result.stderr}")
            return {}
    except Exception as e:
        print(f"Error running radon mi: {e}")
        return {}


def get_file_stats() -> Dict[str, Any]:
    """Get basic file statistics."""
    stats = {
        'total_files': 0,
        'total_lines': 0,
        'avg_file_size': 0,
        'largest_file': {'name': '', 'lines': 0}
    }
    
    try:
        for py_file in Path('autotasktracker').rglob('*.py'):
            with open(py_file, 'r') as f:
                lines = len(f.readlines())
                stats['total_files'] += 1
                stats['total_lines'] += lines
                
                if lines > stats['largest_file']['lines']:
                    stats['largest_file'] = {'name': str(py_file), 'lines': lines}
        
        if stats['total_files'] > 0:
            stats['avg_file_size'] = stats['total_lines'] / stats['total_files']
            
    except Exception as e:
        print(f"Error getting file stats: {e}")
    
    return stats


def calculate_complexity_summary(complexity_data: Dict) -> Dict[str, Any]:
    """Calculate summary statistics from complexity data."""
    summary = {
        'total_functions': 0,
        'high_complexity_functions': 0,
        'avg_complexity': 0,
        'max_complexity': 0,
        'complexity_distribution': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    }
    
    all_complexities = []
    
    for file_path, file_data in complexity_data.items():
        for item in file_data:
            if item['type'] in ['function', 'method']:
                complexity = item['complexity']
                all_complexities.append(complexity)
                summary['total_functions'] += 1
                
                if complexity > 10:  # High complexity threshold
                    summary['high_complexity_functions'] += 1
                
                # Categorize complexity
                if complexity <= 5:
                    summary['complexity_distribution']['A'] += 1
                elif complexity <= 10:
                    summary['complexity_distribution']['B'] += 1
                elif complexity <= 20:
                    summary['complexity_distribution']['C'] += 1
                elif complexity <= 30:
                    summary['complexity_distribution']['D'] += 1
                else:
                    summary['complexity_distribution']['F'] += 1
    
    if all_complexities:
        summary['avg_complexity'] = sum(all_complexities) / len(all_complexities)
        summary['max_complexity'] = max(all_complexities)
    
    return summary


def generate_complexity_report() -> Dict[str, Any]:
    """Generate comprehensive complexity report."""
    print("📊 Generating complexity report...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'complexity': run_radon_complexity(),
        'maintainability': run_radon_maintainability(),
        'file_stats': get_file_stats()
    }
    
    # Add summary statistics
    report['summary'] = calculate_complexity_summary(report['complexity'])
    
    return report


def save_report(report: Dict[str, Any]):
    """Save report to file."""
    reports_dir = Path('complexity-reports')
    reports_dir.mkdir(exist_ok=True)
    
    # Save timestamped report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = reports_dir / f'complexity_report_{timestamp}.json'
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Save as latest
    latest_file = reports_dir / 'latest_complexity.json'
    with open(latest_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Report saved to {report_file}")


def print_summary(report: Dict[str, Any]):
    """Print report summary."""
    summary = report['summary']
    file_stats = report['file_stats']
    
    print("\n📈 Complexity Summary")
    print("=" * 40)
    print(f"Total files: {file_stats['total_files']}")
    print(f"Total lines: {file_stats['total_lines']:,}")
    print(f"Average file size: {file_stats['avg_file_size']:.1f} lines")
    print(f"Largest file: {file_stats['largest_file']['name']} ({file_stats['largest_file']['lines']} lines)")
    
    print(f"\nTotal functions: {summary['total_functions']}")
    print(f"High complexity functions: {summary['high_complexity_functions']}")
    print(f"Average complexity: {summary['avg_complexity']:.2f}")
    print(f"Maximum complexity: {summary['max_complexity']}")
    
    print("\nComplexity Distribution:")
    for grade, count in summary['complexity_distribution'].items():
        percentage = (count / summary['total_functions'] * 100) if summary['total_functions'] > 0 else 0
        print(f"  {grade}: {count} functions ({percentage:.1f}%)")
    
    # Color-coded status
    if summary['high_complexity_functions'] > 20:
        print("\n🚨 Status: HIGH technical debt - many complex functions")
    elif summary['high_complexity_functions'] > 10:
        print("\n⚠️ Status: MEDIUM technical debt - some complex functions")
    else:
        print("\n✅ Status: LOW technical debt - complexity under control")


def install_radon_if_needed():
    """Install radon if not available."""
    try:
        subprocess.run(['radon', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing radon...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'radon'])


def main():
    """Main entry point."""
    install_radon_if_needed()
    report = generate_complexity_report()
    save_report(report)
    print_summary(report)
    
    print(f"\n💡 Next steps:")
    print(f"- Review functions with complexity > 10")
    print(f"- Set up CI gates for complexity limits")
    print(f"- Run monthly to track technical debt trends")


if __name__ == "__main__":
    main()