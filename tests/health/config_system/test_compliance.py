"""
Configuration compliance health tests.

Tests production file compliance, hardcoded value detection, and proper config usage
by delegating to the original comprehensive test methods.
"""

import pytest
from .base_config_tests import BaseConfigTests


class TestConfigCompliance(BaseConfigTests):
    """Configuration compliance and production usage tests."""
    
    def test_production_files_use_config_no_hardcoded_values(self):
        """Scan ALL production files for hardcoded values that should use config."""
        # Delegate to original test method with 100% functionality
        return super().test_production_files_use_config_no_hardcoded_values()
        
    def test_dashboard_files_use_config_ports_exclusively(self):
        """Test that dashboard files use config for port management."""
        # Delegate to original test method with 100% functionality
        return super().test_dashboard_files_use_config_ports_exclusively()
        
    def test_api_client_files_use_config_urls_exclusively(self):
        """Test that API client files use config for URL management."""
        # Delegate to original test method with 100% functionality
        return super().test_api_client_files_use_config_urls_exclusively()
        
    def test_compliance_category_summary(self):
        """Run all compliance tests and provide summary."""
        results = self.run_category_tests('compliance')
        
        failed_tests = [name for name, result in results.items() if result.startswith('FAILED')]
        
        if failed_tests:
            pytest.fail(f"""
Configuration Compliance Test Summary:
❌ {len(failed_tests)} failed tests: {failed_tests}
✅ {len(results) - len(failed_tests)} passed tests

All tests use original implementation for 100% functionality preservation.
""")
        else:
            print(f"✅ All {len(results)} compliance tests passed")
            
    @pytest.mark.parametrize("test_name", [
        'test_production_files_use_config_no_hardcoded_values',
        'test_dashboard_files_use_config_ports_exclusively',
        'test_api_client_files_use_config_urls_exclusively'
    ])
    def test_individual_compliance_methods(self, test_name):
        """Parameterized test to run each compliance test individually."""
        self.run_original_test(test_name)