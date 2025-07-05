"""
Configuration security health tests.

Tests environment variable security, hardening, and isolation
by delegating to the original comprehensive test methods.
"""

import pytest
from .base_config_tests import BaseConfigTests


class TestConfigSecurity(BaseConfigTests):
    """Configuration security and environment handling tests."""
    
    def test_environment_variable_security_audit(self):
        """Audit environment variable handling for security and correctness."""
        # Delegate to original test method with 100% functionality
        return super().test_environment_variable_security_audit()
        
    def test_config_security_hardening(self):
        """Test configuration security hardening measures."""
        # Delegate to original test method with 100% functionality
        return super().test_config_security_hardening()
        
    def test_environment_variable_override_works_in_production(self):
        """Test that environment variable overrides work correctly in production scenarios."""
        # Delegate to original test method with 100% functionality
        return super().test_environment_variable_override_works_in_production()
        
    def test_config_test_environment_isolation_complete(self):
        """Test that test environment configuration is properly isolated."""
        # Delegate to original test method with 100% functionality
        return super().test_config_test_environment_isolation_complete()
        
    def test_security_category_summary(self):
        """Run all security tests and provide summary."""
        results = self.run_category_tests('security')
        
        failed_tests = [name for name, result in results.items() if result.startswith('FAILED')]
        
        if failed_tests:
            pytest.fail(f"""
Configuration Security Test Summary:
❌ {len(failed_tests)} failed tests: {failed_tests}
✅ {len(results) - len(failed_tests)} passed tests

All tests use original implementation for 100% functionality preservation.
""")
        else:
            print(f"✅ All {len(results)} security tests passed")
            
    @pytest.mark.parametrize("test_name", [
        'test_environment_variable_security_audit',
        'test_config_security_hardening', 
        'test_environment_variable_override_works_in_production',
        'test_config_test_environment_isolation_complete'
    ])
    def test_individual_security_methods(self, test_name):
        """Parameterized test to run each security test individually."""
        self.run_original_test(test_name)