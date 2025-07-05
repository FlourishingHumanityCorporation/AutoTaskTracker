#!/usr/bin/env python3
"""Demonstration of Phase 1 Intelligence Enhancement features.

This script demonstrates the new context-aware validation and adaptive performance
capabilities added to the testing system health validation.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.health.testing.context_intelligence import TestingIntelligenceEngine, ValidationMode, ModuleImportance
from tests.health.testing.performance_manager import AdaptivePerformanceManager


def demo_validation_modes():
    """Demonstrate different validation modes."""
    print("🎯 PHASE 1: ADAPTIVE PERFORMANCE MODES")
    print("=" * 50)
    
    modes = [ValidationMode.FAST, ValidationMode.STANDARD, ValidationMode.COMPREHENSIVE]
    
    for mode in modes:
        os.environ['VALIDATION_MODE'] = mode.value
        intelligence = TestingIntelligenceEngine(project_root)
        performance = AdaptivePerformanceManager(intelligence)
        
        limits = performance._execution_limits
        print(f"\n🚀 {mode.value.upper()} MODE:")
        print(f"  ⏱️  Max time: {limits.max_execution_time}s")
        print(f"  📁 Max files: {limits.max_files}")
        print(f"  📄 File size limit: {limits.file_size_limit // 1024}KB")
        print(f"  🔧 Parallel: {'✅' if limits.enable_parallel else '❌'}")
        print(f"  💾 Caching: {'✅' if limits.enable_caching else '❌'}")


def demo_context_awareness():
    """Demonstrate context-aware validation."""
    print("\n\n🧠 PHASE 1: CONTEXT-AWARE INTELLIGENCE")
    print("=" * 50)
    
    intelligence = TestingIntelligenceEngine(project_root)
    
    # Sample test files to analyze
    test_files = [
        Path("tests/health/test_codebase_health.py"),
        Path("tests/integration/test_pensieve_critical_path.py"), 
        Path("tests/unit/test_dashboard_basic.py"),
        Path("tests/infrastructure/test_service_infrastructure.py")
    ]
    
    for test_file in test_files:
        if not test_file.exists():
            continue
            
        print(f"\n📁 {test_file.name}")
        
        # Analyze context
        context = intelligence.analyze_module_context(test_file)
        thresholds = intelligence.get_context_aware_thresholds(test_file)
        
        # Show importance classification
        importance_icons = {
            'critical': '🚨',
            'important': '⚠️',
            'standard': '📋', 
            'experimental': '🔬',
            'infrastructure': '🏗️'
        }
        
        icon = importance_icons.get(context.importance.value, '📄')
        
        print(f"  {icon} Importance: {context.importance.value}")
        print(f"  🎲 Complexity: {context.complexity_score:.2f}")
        print(f"  ⚡ Risk Level: {context.risk_level:.2f}")
        print(f"  🎯 Critical Path: {'✅' if context.is_critical_path else '❌'}")
        print(f"  📊 Min Assertions: {thresholds['minimum_assertions']}")
        print(f"  ⚠️  Error Testing: {'Required' if thresholds['requires_error_testing'] else 'Optional'}")
        print(f"  🔢 Boundary Testing: {'Required' if thresholds['requires_boundary_testing'] else 'Optional'}")


def demo_smart_file_selection():
    """Demonstrate smart file selection."""
    print("\n\n🎯 PHASE 1: SMART FILE SELECTION")
    print("=" * 50)
    
    intelligence = TestingIntelligenceEngine(project_root)
    
    # Get all test files
    all_test_files = []
    test_dir = project_root / "tests"
    for root, dirs, files in os.walk(test_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                all_test_files.append(Path(root) / file)
    
    print(f"📊 Found {len(all_test_files)} total test files")
    
    # Demonstrate smart selection
    selected_files = intelligence.get_smart_file_selection(all_test_files)
    
    print(f"🎯 Smart selection: {len(selected_files)} files")
    
    # Categorize by importance
    by_importance = {}
    for test_file in selected_files[:10]:  # Show first 10
        context = intelligence.analyze_module_context(test_file)
        importance = context.importance.value
        if importance not in by_importance:
            by_importance[importance] = []
        by_importance[importance].append(test_file.name)
    
    for importance, files in by_importance.items():
        icon = {
            'critical': '🚨',
            'important': '⚠️', 
            'standard': '📋',
            'experimental': '🔬',
            'infrastructure': '🏗️'
        }.get(importance, '📄')
        
        print(f"  {icon} {importance}: {len(files)} files")
        for file_name in files[:3]:  # Show first 3
            print(f"    • {file_name}")
        if len(files) > 3:
            print(f"    ... and {len(files) - 3} more")


def demo_intelligent_error_messages():
    """Demonstrate intelligent error messages."""
    print("\n\n💡 PHASE 1: INTELLIGENT ERROR MESSAGES")
    print("=" * 50)
    
    intelligence = TestingIntelligenceEngine(project_root)
    
    # Sample scenarios
    scenarios = [
        {
            'file': Path('tests/integration/test_database_critical.py'),
            'function': 'test_connection_failure',
            'issue': 'Insufficient assertions',
            'details': 'Has 1 assertion, requires 4 for critical module'
        },
        {
            'file': Path('tests/experimental/test_new_feature.py'),
            'function': 'test_basic_functionality', 
            'issue': 'Missing error testing',
            'details': 'No error conditions tested'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📄 Example: {scenario['file'].name}")
        
        message = intelligence.get_intelligent_error_message(
            scenario['file'],
            scenario['function'],
            scenario['issue'],
            scenario['details']
        )
        
        print(message)


def demo_performance_metrics():
    """Demonstrate performance monitoring."""
    print("\n\n📊 PHASE 1: PERFORMANCE MONITORING")
    print("=" * 50)
    
    intelligence = TestingIntelligenceEngine(project_root)
    performance = AdaptivePerformanceManager(intelligence)
    
    # Simulate some processing
    print("🔄 Simulating test processing...")
    
    for i in range(5):
        test_file = Path(f"tests/sample_test_{i}.py")
        should_process, reason = performance.should_process_file(test_file)
        print(f"  📁 {test_file.name}: {'✅' if should_process else '❌'} {reason if not should_process else 'OK'}")
        
        if should_process:
            performance.update_metrics(files_processed=1, tests_executed=3)
            time.sleep(0.1)  # Simulate processing time
    
    # Show performance summary
    print("\n📈 Performance Summary:")
    performance.log_performance_summary()


def main():
    """Run all demonstrations."""
    print("🚀 TESTING SYSTEM INTELLIGENCE - PHASE 1 DEMONSTRATION")
    print("🎯 Context-Aware Validation & Adaptive Performance")
    print("=" * 60)
    
    try:
        demo_validation_modes()
        demo_context_awareness()
        demo_smart_file_selection()
        demo_intelligent_error_messages()
        demo_performance_metrics()
        
        print("\n" + "=" * 60)
        print("✅ PHASE 1 IMPLEMENTATION COMPLETE!")
        print("🎯 Key Features Demonstrated:")
        print("  • Context-aware validation with module importance scoring")
        print("  • Adaptive performance modes (fast/standard/comprehensive)")
        print("  • Smart file selection based on importance and risk")
        print("  • Intelligent error messages with context and impact")
        print("  • Performance monitoring and optimization")
        print("\n🚀 Ready for Phase 2: Developer Experience Enhancement")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())