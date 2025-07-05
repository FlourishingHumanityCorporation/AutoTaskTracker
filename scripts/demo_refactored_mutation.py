#!/usr/bin/env python3
"""Demo script showing the refactored mutation testing system."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.health.testing.mutation_tester_refactored import RefactoredMutationTester
from tests.health.testing.config import EffectivenessConfig


def main():
    """Demonstrate the refactored mutation tester."""
    project_root = Path.cwd()
    
    # Create configuration
    config = EffectivenessConfig()
    config.mutation.max_mutations_per_file = 5
    config.mutation.timeout_seconds = 10
    
    # Create tester
    tester = RefactoredMutationTester(project_root, config)
    
    # Demo: analyze a test file
    test_file = project_root / "tests" / "unit" / "test_simple_intelligence.py"
    
    if not test_file.exists():
        print(f"Demo test file not found: {test_file}")
        return
    
    print("🧪 Refactored Mutation Testing Demo")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Test file: {test_file.relative_to(project_root)}")
    print()
    
    # Check components
    print("📦 Component Status:")
    print(f"  ✅ Generator: {type(tester.generator).__name__}")
    print(f"  ✅ Executor: {type(tester.executor).__name__}")
    print(f"  ✅ Analyzer: {type(tester.analyzer).__name__}")
    print()
    
    # Find source file
    source_file = tester._find_source_file(test_file)
    if source_file:
        print(f"📄 Found source file: {source_file.relative_to(project_root)}")
        
        # Generate mutations (without executing them)
        mutations = tester.generator.generate_mutations(source_file)
        print(f"🧬 Generated {len(mutations)} mutations:")
        
        for i, mutation in enumerate(mutations[:3], 1):  # Show first 3
            print(f"  {i}. {mutation['type']} at line {mutation['line'] + 1}")
            print(f"     Original: {mutation['original'].strip()}")
            print(f"     Mutated:  {mutation['mutated'].strip()}")
            print()
        
        if len(mutations) > 3:
            print(f"  ... and {len(mutations) - 3} more mutations")
    else:
        print("❌ No source file found for this test")
    
    print()
    print("🎯 Benefits of Refactoring:")
    print("  ✅ Separated concerns (generate/execute/analyze)")
    print("  ✅ Each component is focused and testable")
    print("  ✅ Easy to extend with new mutation types")
    print("  ✅ Better error handling and logging")
    print("  ✅ Reduced complexity (from 854 lines to ~400 total)")


if __name__ == "__main__":
    main()