#!/usr/bin/env python3
"""Real-world demonstration of effectiveness-based validation on AutoTaskTracker tests.

This script demonstrates the effectiveness validation system by analyzing actual 
test files from the AutoTaskTracker codebase and providing actionable insights.
"""

import logging
import sys
from pathlib import Path
from typing import List, Dict
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from tests.health.testing import EffectivenessValidator, ConfigManager, EffectivenessConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Increase verbosity for debugging
    format='%(levelname)s - %(message)s'
)

def create_fast_config() -> EffectivenessConfig:
    """Create a configuration optimized for fast demonstration."""
    config = EffectivenessConfig()
    
    # Reduce mutations but keep reasonable timeout for AutoTaskTracker tests
    config.mutation.max_mutations_per_file = 5  # Test parallel with more mutations
    config.mutation.timeout_seconds = 45  # AutoTaskTracker tests need more time
    config.analysis.max_files_per_test = 5
    config.analysis.max_analysis_time_seconds = 120  # Extended for complex tests
    config.enable_parallel_execution = True  # Enable parallel mutation testing
    config.max_worker_threads = 3  # Use 3 parallel workers
    
    return config

def find_representative_test_files(project_root: Path) -> List[Path]:
    """Find representative test files for analysis."""
    test_files = []
    
    # Look for test files that have corresponding source files
    patterns = [
        "test_comparison_metrics.py",         # Tests autotasktracker.comparison.analysis.metrics
        "test_time_tracker.py",              # Tests autotasktracker.core.time_tracker
        "test_task_extractor.py",            # Tests autotasktracker.core.task_extractor
        "test_categorizer.py"                # Tests autotasktracker.core.categorizer
    ]
    
    for pattern in patterns:
        for test_file in project_root.rglob(pattern):
            if test_file.exists() and test_file.stat().st_size < 50 * 1024:  # < 50KB
                test_files.append(test_file)
                break  # Only take first match of each pattern
    
    return test_files[:3]  # Limit to 3 files for demo

def analyze_test_file(validator: EffectivenessValidator, test_file: Path) -> Dict:
    """Analyze a single test file with timeout protection."""
    print(f"\n🔍 Analyzing: {test_file.name}")
    start_time = time.time()
    
    try:
        result = validator.validate_test_effectiveness(test_file)
        analysis_time = time.time() - start_time
        
        print(f"   ⏱️  Analysis time: {analysis_time:.1f}s")
        return result
        
    except Exception as e:
        print(f"   ❌ Analysis failed: {str(e)[:100]}...")
        return {
            'test_file': test_file.name,
            'mutation_effectiveness': 0.0,
            'overall_effectiveness': 0.0,
            'actionable_recommendations': [f"Analysis failed: {e}"],
            'analysis_errors': [str(e)]
        }

def print_effectiveness_summary(result: Dict):
    """Print a concise effectiveness summary."""
    test_file = result['test_file']
    mutation_eff = result['mutation_effectiveness']
    overall_eff = result['overall_effectiveness']
    
    print(f"   📊 Mutation effectiveness: {mutation_eff:.1f}%")
    print(f"   📊 Overall effectiveness: {overall_eff:.1f}%")
    
    # Show effectiveness interpretation
    if overall_eff >= 70:
        print(f"   ✅ EFFECTIVE: Good bug-catching ability")
    elif overall_eff >= 50:
        print(f"   ⚠️  MODERATE: Some bugs may slip through")
    else:
        print(f"   🚨 NEEDS WORK: Significant gaps in test coverage")
    
    # Show top recommendation
    recs = result.get('actionable_recommendations', [])
    if recs:
        print(f"   💡 Key insight: {recs[0][:80]}...")
    
    # Show analysis issues if any
    errors = result.get('analysis_errors', [])
    if errors:
        print(f"   ⚠️  Note: {len(errors)} analysis component(s) had issues")

def main():
    """Run real-world effectiveness validation demo."""
    project_root = Path.cwd()
    
    print("🧬 REAL-WORLD EFFECTIVENESS VALIDATION DEMO")
    print("=" * 60)
    print("\nThis demo analyzes actual AutoTaskTracker test files using")
    print("effectiveness-based validation (mutation testing + analysis).")
    print("\nKey question: 'Would these tests catch real bugs?'")
    
    # Initialize with fast configuration
    config = create_fast_config()
    validator = EffectivenessValidator(project_root)
    # Override with fast config
    validator.config = config
    validator.mutation_tester.config = config
    
    print(f"\n⚙️  Configuration: {config.mutation.max_mutations_per_file} mutations, {config.mutation.timeout_seconds}s timeout")
    
    # Find test files to analyze
    test_files = find_representative_test_files(project_root)
    
    if not test_files:
        print("\n❌ No suitable test files found for analysis")
        return
    
    print(f"\n📁 Found {len(test_files)} test files to analyze")
    
    # Analyze each test file
    results = []
    total_start = time.time()
    
    for test_file in test_files:
        result = analyze_test_file(validator, test_file)
        results.append(result)
        print_effectiveness_summary(result)
    
    total_time = time.time() - total_start
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 SUMMARY")
    print(f"   ⏱️  Total analysis time: {total_time:.1f}s")
    print(f"   📁 Files analyzed: {len(results)}")
    
    if results:
        avg_mutation = sum(r['mutation_effectiveness'] for r in results) / len(results)
        avg_overall = sum(r['overall_effectiveness'] for r in results) / len(results)
        
        print(f"   📊 Average mutation effectiveness: {avg_mutation:.1f}%")
        print(f"   📊 Average overall effectiveness: {avg_overall:.1f}%")
        
        # Count issues
        files_with_errors = sum(1 for r in results if r.get('analysis_errors'))
        effective_tests = sum(1 for r in results if r['overall_effectiveness'] >= 70)
        
        print(f"   ✅ Effective tests: {effective_tests}/{len(results)}")
        if files_with_errors:
            print(f"   ⚠️  Files with analysis issues: {files_with_errors}")
    
    print(f"\n💡 This demonstrates effectiveness-based validation:")
    print(f"   • Focuses on actual bug-catching ability")
    print(f"   • Provides specific, actionable feedback") 
    print(f"   • Uses real code mutations to test test quality")
    print(f"   • Complements traditional structural metrics")
    
    print(f"\n🚀 To run full analysis: EFFECTIVENESS_MAX_FILES=10 pytest tests/health/testing/test_effectiveness_validation.py -v -s")

if __name__ == "__main__":
    main()