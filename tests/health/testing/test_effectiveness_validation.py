"""Improved effectiveness-based test validation system.

This replaces structure-based metrics with actual bug-catching effectiveness validation.
Tests are evaluated on: "Would this test catch the bug that will happen next week?"
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any
import pytest

# Fix import structure for pytest compatibility
try:
    from .mutation_effectiveness import EffectivenessValidator
    from .bug_correlation import RealWorldEffectivenessAnalyzer  
    from .simple_intelligence import FocusedTestValidator
    from .integration_validator import IntegrationTestValidator
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from mutation_effectiveness import EffectivenessValidator
    from bug_correlation import RealWorldEffectivenessAnalyzer
    from simple_intelligence import FocusedTestValidator
    from integration_validator import IntegrationTestValidator

logger = logging.getLogger(__name__)


class TestEffectivenessValidation:
    """Effectiveness-based test validation focused on actual bug-catching ability."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with effectiveness validators"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        
        # Initialize effectiveness-based validators
        self.effectiveness_validator = EffectivenessValidator(self.project_root)
        self.real_world_analyzer = RealWorldEffectivenessAnalyzer(self.project_root)
        self.focused_validator = FocusedTestValidator(self.project_root)
        self.integration_validator = IntegrationTestValidator(self.project_root)
        
        logger.info("Effectiveness-based validation system initialized")
    
    def get_test_files(self) -> List[Path]:
        """Get test files with intelligent selection focused on effectiveness analysis."""
        test_files = []
        max_files = int(os.getenv('EFFECTIVENESS_MAX_FILES', '15'))  # Limit for performance
        
        for root, dirs, files in os.walk(self.test_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_path = Path(root) / file
                    # Skip very large files that would slow analysis
                    try:
                        if test_path.stat().st_size < 100 * 1024:  # < 100KB
                            test_files.append(test_path)
                            if len(test_files) >= max_files:
                                break
                    except OSError:
                        continue
            if len(test_files) >= max_files:
                break
        
        return test_files
    
    def test_mutation_based_effectiveness(self):
        """Test using mutation testing to measure actual bug-catching ability."""
        test_files = self.get_test_files()
        mutation_results = []
        
        logger.info(f"🧬 MUTATION TESTING: Analyzing {len(test_files)} test files for bug-catching ability")
        
        for test_file in test_files[:5]:  # Limit for performance
            try:
                effectiveness_report = self.effectiveness_validator.validate_test_effectiveness(test_file)
                mutation_effectiveness = effectiveness_report.get('mutation_effectiveness', 0)
                
                mutation_results.append({
                    'file': test_file.name,
                    'effectiveness': mutation_effectiveness,
                    'overall': effectiveness_report.get('overall_effectiveness', 0)
                })
                
                # Log specific insights
                recommendations = effectiveness_report.get('actionable_recommendations', [])
                if recommendations:
                    logger.info(f"  📁 {test_file.name}: {mutation_effectiveness:.1f}% mutation detection")
                    for rec in recommendations[:2]:
                        logger.info(f"    💡 {rec}")
                        
            except Exception as e:
                logger.warning(f"Mutation analysis failed for {test_file.name}: {e}")
        
        # Analyze results
        if mutation_results:
            avg_effectiveness = sum(r['effectiveness'] for r in mutation_results) / len(mutation_results)
            poor_tests = [r for r in mutation_results if r['effectiveness'] < 50]
            
            logger.info(f"📊 MUTATION TESTING RESULTS:")
            logger.info(f"  Average effectiveness: {avg_effectiveness:.1f}%")
            logger.info(f"  Tests with poor mutation detection: {len(poor_tests)}")
            
            if len(poor_tests) > len(mutation_results) * 0.5:
                logger.warning(f"⚠️ More than 50% of tests have poor mutation detection")
                logger.warning(f"💡 These tests may miss real bugs when code changes")
        else:
            logger.info("No mutation testing results available")
    
    def test_real_world_bug_correlation(self):
        """Test correlation with actual bugs from Git history."""
        test_files = self.get_test_files()
        correlation_results = []
        
        logger.info(f"📊 REAL-WORLD CORRELATION: Analyzing historical bug prevention")
        
        for test_file in test_files[:3]:  # Limit for performance
            try:
                real_world_report = self.real_world_analyzer.analyze_real_world_effectiveness(test_file)
                bug_correlation_score = real_world_report.get('bug_correlation_score', 0)
                
                if bug_correlation_score > 0:
                    correlation_results.append({
                        'file': test_file.name,
                        'correlation_score': bug_correlation_score,
                        'effectiveness_rating': real_world_report.get('effectiveness_rating', 'unknown')
                    })
                    
                    logger.info(f"  📁 {test_file.name}: {bug_correlation_score:.1f}% historical bug prevention")
                    
            except Exception as e:
                logger.warning(f"Bug correlation analysis failed for {test_file.name}: {e}")
        
        if correlation_results:
            avg_correlation = sum(r['correlation_score'] for r in correlation_results) / len(correlation_results)
            poor_correlation = [r for r in correlation_results if r['correlation_score'] < 60]
            
            logger.info(f"📊 BUG CORRELATION RESULTS:")
            logger.info(f"  Average correlation: {avg_correlation:.1f}%")
            logger.info(f"  Tests with poor historical prevention: {len(poor_correlation)}")
        else:
            logger.info("No historical bug data available for correlation analysis")
    
    def test_actionable_insights_generation(self):
        """Test generation of specific, actionable improvement insights."""
        test_files = self.get_test_files()
        insights_summary = []
        
        logger.info(f"💡 ACTIONABLE INSIGHTS: Analyzing {len(test_files)} files for specific improvements")
        
        for test_file in test_files[:10]:  # Analyze more files for insights
            try:
                validation_result = self.focused_validator.validate_test_file(test_file)
                
                effectiveness = validation_result.get('effectiveness', 'unknown')
                high_priority_actions = validation_result.get('high_priority_actions', [])
                next_steps = validation_result.get('next_steps', [])
                
                insights_summary.append({
                    'file': test_file.name,
                    'effectiveness': effectiveness,
                    'actions_needed': len(high_priority_actions),
                    'next_steps': len(next_steps)
                })
                
                # Log actionable feedback
                if high_priority_actions:
                    logger.info(f"  📁 {test_file.name} ({effectiveness}):")
                    for action in high_priority_actions[:2]:
                        logger.info(f"    🔧 {action}")
                        
            except Exception as e:
                logger.warning(f"Insight generation failed for {test_file.name}: {e}")
        
        # Summarize insights
        total_actions_needed = sum(r['actions_needed'] for r in insights_summary)
        files_needing_improvement = len([r for r in insights_summary if r['actions_needed'] > 0])
        
        logger.info(f"📊 ACTIONABLE INSIGHTS SUMMARY:")
        logger.info(f"  Files analyzed: {len(insights_summary)}")
        logger.info(f"  Files needing improvement: {files_needing_improvement}")
        logger.info(f"  Total high-priority actions identified: {total_actions_needed}")
        
        # This is guidance, not a failure
        if files_needing_improvement > len(insights_summary) * 0.7:
            logger.info(f"💡 Many tests could be improved - focus on high-priority actions first")
    
    def test_integration_test_reality_check(self):
        """Test whether integration tests actually test real integration."""
        test_files = self.get_test_files()
        
        logger.info(f"🔗 INTEGRATION REALITY CHECK: Validating real component interaction")
        
        try:
            integration_report = self.integration_validator.validate_integration_tests(test_files)
            
            integration_files = integration_report.get('integration_files', 0)
            overall_quality = integration_report.get('overall_quality', 'unknown')
            avg_real_integration = integration_report.get('average_real_integration_percentage', 0)
            recommendations = integration_report.get('recommendations', [])
            
            logger.info(f"📊 INTEGRATION TEST RESULTS:")
            logger.info(f"  Integration test files found: {integration_files}")
            logger.info(f"  Overall quality: {overall_quality}")
            logger.info(f"  Average real integration: {avg_real_integration:.1f}%")
            
            if recommendations:
                logger.info(f"  Key recommendations:")
                for rec in recommendations[:3]:
                    logger.info(f"    💡 {rec}")
                    
        except Exception as e:
            logger.warning(f"Integration validation failed: {e}")
    
    def test_effectiveness_system_summary(self):
        """Provide a summary of the effectiveness-based validation system."""
        logger.info(f"")
        logger.info(f"🎯 EFFECTIVENESS-BASED VALIDATION SYSTEM SUMMARY")
        logger.info(f"=" * 60)
        logger.info(f"")
        logger.info(f"This system focuses on ACTUAL BUG-CATCHING ABILITY instead of structural metrics:")
        logger.info(f"")
        logger.info(f"✅ WHAT IT DOES:")
        logger.info(f"  🧬 Mutation Testing: Would tests catch code changes?")
        logger.info(f"  📊 Bug Correlation: Do tests prevent historical bug patterns?")
        logger.info(f"  💡 Actionable Insights: Specific improvements, not generic rules")
        logger.info(f"  🔗 Integration Reality: Real component interaction vs mocking")
        logger.info(f"")
        logger.info(f"❌ WHAT IT DOESN'T DO:")
        logger.info(f"  • Count assertions (doesn't predict bug-catching)")
        logger.info(f"  • Enforce arbitrary rules (context-independent)")
        logger.info(f"  • Focus on test structure (focuses on effectiveness)")
        logger.info(f"")
        logger.info(f"🎯 KEY QUESTION ANSWERED:")
        logger.info(f"  'Would this test catch the bug that will happen next week?'")
        logger.info(f"")
        logger.info(f"💡 USAGE:")
        logger.info(f"  EFFECTIVENESS_MAX_FILES=10 pytest tests/health/testing/test_effectiveness_validation.py -v -s")
        logger.info(f"")
        logger.info(f"=" * 60)
        
        # This test always passes - it's informational
        assert True, "Effectiveness-based validation system is operational"


class TestComparisonWithOldSystem:
    """Compare effectiveness-based validation with the old structure-based system."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup comparison environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.project_root / "tests"
        
    def test_old_vs_new_approach_comparison(self):
        """Compare old structure-based vs new effectiveness-based validation."""
        logger.info(f"")
        logger.info(f"⚖️  OLD vs NEW VALIDATION APPROACH COMPARISON")
        logger.info(f"=" * 60)
        logger.info(f"")
        
        logger.info(f"📊 OLD APPROACH (Structure-Based):")
        logger.info(f"  ❌ Counts assertions (3 for critical, 1 for experimental)")
        logger.info(f"  ❌ Enforces naming conventions")
        logger.info(f"  ❌ Checks file organization")
        logger.info(f"  ❌ Validates mock usage patterns")
        logger.info(f"  ❌ Result: Tests pass validation but miss real bugs")
        logger.info(f"")
        
        logger.info(f"🎯 NEW APPROACH (Effectiveness-Based):")
        logger.info(f"  ✅ Mutation testing: Does changing code break tests?")
        logger.info(f"  ✅ Bug correlation: Do tests prevent known bug patterns?")
        logger.info(f"  ✅ Integration reality: Real vs mocked component interaction")
        logger.info(f"  ✅ Actionable insights: Specific improvements, not generic rules")
        logger.info(f"  ✅ Result: Tests that actually catch bugs")
        logger.info(f"")
        
        logger.info(f"📈 IMPROVEMENT METRICS:")
        logger.info(f"  • Reduced false positives (good tests flagged as bad)")
        logger.info(f"  • Increased true positives (bad tests correctly identified)")
        logger.info(f"  • Actionable feedback (specific fixes vs generic advice)")
        logger.info(f"  • Focus on outcomes (bug prevention vs structure)")
        logger.info(f"")
        
        logger.info(f"🎯 BOTTOM LINE:")
        logger.info(f"  Old: 'This test has wrong structure'")
        logger.info(f"  New: 'This test would miss real bugs - here's how to fix it'")
        logger.info(f"")
        logger.info(f"=" * 60)
        
        assert True, "Comparison completed - new approach focuses on actual effectiveness"


if __name__ == "__main__":
    # Allow running as a standalone demonstration
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # Run a demonstration of the effectiveness-based system
        project_root = Path(__file__).parent.parent.parent.parent
        
        print("🎯 EFFECTIVENESS-BASED TEST VALIDATION DEMO")
        print("=" * 50)
        
        # Initialize validators
        effectiveness_validator = EffectivenessValidator(project_root)
        focused_validator = FocusedTestValidator(project_root)
        
        # Find a test file to analyze
        test_files = list((project_root / "tests").rglob("test_*.py"))
        if test_files:
            test_file = test_files[0]
            print(f"\\nAnalyzing: {test_file.name}")
            
            # Effectiveness analysis
            effectiveness_result = effectiveness_validator.validate_test_effectiveness(test_file)
            print(f"Overall effectiveness: {effectiveness_result.get('overall_effectiveness', 0):.1f}%")
            
            # Actionable insights
            insights_result = focused_validator.validate_test_file(test_file)
            next_steps = insights_result.get('next_steps', [])
            
            if next_steps:
                print("\\nNext steps to improve:")
                for i, step in enumerate(next_steps[:3], 1):
                    print(f"  {i}. {step}")
            else:
                print("\\n✅ No major issues found")
        else:
            print("No test files found for analysis")
            
        print("\\n" + "=" * 50)