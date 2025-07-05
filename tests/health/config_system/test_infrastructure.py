"""
Configuration infrastructure health tests.

Tests pytest fixtures, test infrastructure, and complex testing scenarios
by delegating to the original comprehensive test methods.
"""

import pytest
from .base_config_tests import BaseConfigTests


class TestConfigInfrastructure(BaseConfigTests):
    """Configuration infrastructure and testing framework tests."""
    
    def test_pytest_fixture_integration_comprehensive(self):
        """Test comprehensive pytest fixture integration with config."""
        # Delegate to original test method with 100% functionality
        return super().test_pytest_fixture_integration_comprehensive()
        
    def test_test_discovery_import_path_validation_comprehensive(self):
        """Comprehensive test discovery and import path validation."""
        # Delegate to original test method with 100% functionality
        return super().test_test_discovery_import_path_validation_comprehensive()
        
    def test_test_database_separation_and_test_config_validation(self):
        """Test database separation and comprehensive test config validation."""
        # Delegate to original test method with 100% functionality
        return super().test_test_database_separation_and_test_config_validation()
        
    def test_conftest_and_test_infrastructure_config_integration(self):
        """Test conftest and test infrastructure config integration."""
        # Delegate to original test method with 100% functionality
        return super().test_conftest_and_test_infrastructure_config_integration()
        
    def test_infrastructure_category_summary(self):
        """Run all infrastructure tests and provide summary."""
        results = self.run_category_tests('infrastructure')
        
        failed_tests = [name for name, result in results.items() if result.startswith('FAILED')]
        
        if failed_tests:
            pytest.fail(f"""
Configuration Infrastructure Test Summary:
❌ {len(failed_tests)} failed tests: {failed_tests}
✅ {len(results) - len(failed_tests)} passed tests

All tests use original implementation for 100% functionality preservation.
""")
        else:
            print(f"✅ All {len(results)} infrastructure tests passed")
            
    @pytest.mark.parametrize("test_name", [
        'test_pytest_fixture_integration_comprehensive',
        'test_test_discovery_import_path_validation_comprehensive',
        'test_test_database_separation_and_test_config_validation',
        'test_conftest_and_test_infrastructure_config_integration'
    ])
    def test_individual_infrastructure_methods(self, test_name):
        """Parameterized test to run each infrastructure test individually."""
        self.run_original_test(test_name)