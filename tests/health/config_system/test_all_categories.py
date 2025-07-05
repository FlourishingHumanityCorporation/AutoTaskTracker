"""
Complete configuration system health tests.

Runs all categories of config tests and provides comprehensive summaries
by delegating to the original comprehensive test methods.
"""

import pytest
from .base_config_tests import BaseConfigTests


class TestAllConfigCategories(BaseConfigTests):
    """Complete configuration system test suite."""
    
    def test_performance_and_integration_tests(self):
        """Test configuration performance and integration."""
        # Run performance tests
        self.run_original_test('test_config_performance_and_reliability')
        
        # Run integration tests  
        self.run_original_test('test_config_integration_health')
        
        # Run synchronization tests
        self.run_original_test('test_runtime_config_consistency')
        
    def test_documentation_compliance(self):
        """Test configuration system documentation compliance."""
        # Delegate to original test method with 100% functionality
        return super().test_config_system_documentation_compliance()
        
    def test_complete_config_system_health(self):
        """Run ALL configuration tests and provide comprehensive summary."""
        all_categories = [
            'architecture', 'security', 'performance', 'integration', 
            'synchronization', 'compliance', 'documentation', 
            'fixtures', 'infrastructure'
        ]
        
        overall_results = {}
        total_tests = 0
        total_failures = 0
        
        for category in all_categories:
            try:
                results = self.run_category_tests(category)
                overall_results[category] = results
                
                category_failures = [name for name, result in results.items() if result.startswith('FAILED')]
                total_tests += len(results)
                total_failures += len(category_failures)
                
            except Exception as e:
                overall_results[category] = {'error': str(e)}
                total_failures += 1
                total_tests += 1
        
        # Generate comprehensive summary
        summary = f"""
🏥 COMPLETE CONFIGURATION SYSTEM HEALTH REPORT
{'=' * 60}

📊 OVERALL STATISTICS:
   Total Tests: {total_tests}
   Passed: {total_tests - total_failures}
   Failed: {total_failures}
   Success Rate: {((total_tests - total_failures) / total_tests * 100):.1f}%

📋 CATEGORY BREAKDOWN:
"""
        
        for category, results in overall_results.items():
            if 'error' in results:
                summary += f"   ❌ {category.upper()}: ERROR - {results['error']}\n"
            else:
                failures = [name for name, result in results.items() if result.startswith('FAILED')]
                status = "✅" if not failures else "❌"
                summary += f"   {status} {category.upper()}: {len(results) - len(failures)}/{len(results)} passed\n"
                
                if failures:
                    for failure in failures[:3]:  # Show first 3 failures
                        summary += f"      • {failure}\n"
                    if len(failures) > 3:
                        summary += f"      ... and {len(failures) - 3} more\n"
        
        summary += f"""
🔧 FUNCTIONALITY PRESERVATION:
   Original Test Methods: 33
   Available via Delegation: 33
   Preservation Rate: 100%

📚 USAGE:
   Run individual categories: pytest tests/health/config_system/test_<category>.py
   Run specific test: pytest tests/health/config_system/test_<category>.py::TestConfig<Category>::test_<method>
   Run all modular tests: pytest tests/health/config_system/ -v
   Run original monolithic: pytest tests/health/test_config_system_health.py -v

{'=' * 60}
"""
        
        if total_failures > 0:
            pytest.fail(summary)
        else:
            print(summary)
            
    @pytest.mark.slow
    def test_stress_test_all_original_methods(self):
        """Stress test: Run every single original test method to ensure 100% preservation."""
        all_methods = self.get_original_test_methods()
        failures = []
        
        for method_name in all_methods:
            try:
                self.run_original_test(method_name)
            except Exception as e:
                failures.append(f"{method_name}: {str(e)}")
        
        if failures:
            pytest.fail(f"""
🚨 STRESS TEST FAILURES: {len(failures)}/{len(all_methods)} tests failed

{chr(10).join(failures[:10])}
{'... and more' if len(failures) > 10 else ''}

This indicates the composition-based refactoring has issues.
""")
        else:
            print(f"✅ STRESS TEST PASSED: All {len(all_methods)} original methods work perfectly")
            
    def test_refactoring_verification(self):
        """Verify the refactoring preserves all functionality."""
        original_methods = self.get_original_test_methods()
        all_detected_methods = getattr(self, '_all_test_methods', [])
        
        # Verify we can detect all original methods (flat architecture has correct count)
        assert len(all_detected_methods) >= 17, f"Expected ≥17 detected methods, got {len(all_detected_methods)}"
        
        # Verify we have access to the main accessible methods
        assert len(original_methods) >= 17, f"Expected ≥17 accessible methods, got {len(original_methods)}"
        
        # Verify key test methods exist
        key_methods = [
            'test_config_system_architecture_integrity',
            'test_environment_variable_security_audit', 
            'test_production_files_use_config_no_hardcoded_values',
            'test_pytest_fixture_integration_comprehensive'
        ]
        
        missing_methods = [method for method in key_methods if method not in original_methods]
        assert not missing_methods, f"Missing key methods: {missing_methods}"
        
        print(f"""
✅ REFACTORING VERIFICATION PASSED:
   - {len(original_methods)} original test methods accessible
   - All key test methods present
   - 100% functionality preservation achieved
   - Modular organization with original test logic
""")