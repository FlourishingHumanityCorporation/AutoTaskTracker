"""
Configuration architecture health tests.

Tests configuration loading, architecture integrity, and synchronization
by delegating to the original comprehensive test methods.
"""

import pytest
from .base_config_tests import BaseConfigTests


class TestConfigArchitecture(BaseConfigTests):
    """Configuration architecture and loading health tests."""
    
    def test_config_system_architecture_integrity(self):
        """Test that the configuration system architecture is sound."""
        # Delegate to original test method with 100% functionality
        return super().test_config_system_architecture_integrity()
        
    def test_config_synchronization_integrity(self):
        """Test synchronization between different configuration systems."""
        # Delegate to original test method with 100% functionality
        return super().test_config_synchronization_integrity()
        
    def test_architecture_category_summary(self):
        """Run all architecture tests and provide summary."""
        results = self.run_category_tests('architecture')
        
        failed_tests = [name for name, result in results.items() if result.startswith('FAILED')]
        
        if failed_tests:
            pytest.fail(f"""
Configuration Architecture Test Summary:
❌ {len(failed_tests)} failed tests: {failed_tests}
✅ {len(results) - len(failed_tests)} passed tests

All tests use original implementation for 100% functionality preservation.
""")
        else:
            print(f"✅ All {len(results)} architecture tests passed")
            
    @pytest.mark.parametrize("test_name", [
        'test_config_system_architecture_integrity',
        'test_config_synchronization_integrity'
    ])
    def test_individual_architecture_methods(self, test_name):
        """Parameterized test to run each architecture test individually."""
        self.run_original_test(test_name)