#!/usr/bin/env python3
"""
Simple health test performance comparison.
"""

import time
import subprocess
import sys

def time_command(cmd, description):
    """Time a command and return duration."""
    print(f"🧪 Testing {description}...")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start
    
    # Count tests
    test_count = 0
    if 'passed' in result.stdout:
        for line in result.stdout.split('\n'):
            if ' passed' in line and ('failed' in line or 'error' in line or line.endswith('passed')):
                try:
                    # Extract number before 'passed'
                    parts = line.split(' passed')[0].split()
                    for part in reversed(parts):
                        if part.isdigit():
                            test_count = int(part)
                            break
                except:
                    pass
                break
    
    print(f"   {test_count} tests in {duration:.2f}s ({duration/test_count:.3f}s per test)" if test_count > 0 else f"   {duration:.2f}s")
    return duration, test_count

def main():
    print("⚡ Health Test Performance Comparison")
    print("=" * 50)
    
    # Test individual modules
    modules = [
        ("code_quality", ["python", "-m", "pytest", "tests/health/code_quality/", "-x", "--tb=no", "-q"]),
        ("database", ["python", "-m", "pytest", "tests/health/database/", "-x", "--tb=no", "-q"]),
        ("integration", ["python", "-m", "pytest", "tests/health/integration/", "-x", "--tb=no", "-q"]),
        ("error_health", ["python", "-m", "pytest", "tests/health/test_error_health.py", "-x", "--tb=no", "-q"]),
    ]
    
    total_time = 0
    total_tests = 0
    
    for name, cmd in modules:
        try:
            duration, test_count = time_command(cmd, name)
            total_time += duration
            total_tests += test_count
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n📊 Summary:")
    print(f"Total: {total_tests} tests in {total_time:.2f}s")
    print(f"Average: {total_time/total_tests:.3f}s per test" if total_tests > 0 else "No tests completed")
    
    # Performance grade
    if total_tests > 0:
        avg = total_time / total_tests
        if avg < 1.0:
            grade = "🟢 Excellent"
        elif avg < 2.0:
            grade = "🟡 Good"
        else:
            grade = "🔴 Needs optimization"
        print(f"Grade: {grade}")

if __name__ == "__main__":
    main()