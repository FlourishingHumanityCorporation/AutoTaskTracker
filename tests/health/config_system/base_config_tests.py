"""
Base configuration tests - imports and delegates to original test class.

This preserves 100% functionality by importing the original test class
and providing a clean interface for modular test organization.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import original test
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the original test class with all its functionality
from test_config_system_health import TestConfigSystemHealthAudit as OriginalConfigTests

class BaseConfigTests(OriginalConfigTests):
    """
    Base class that inherits ALL functionality from the original config tests.
    
    This ensures 100% compatibility while allowing modular organization.
    All original test methods are available and unchanged.
    """
    
    @classmethod
    def setup_class(cls):
        """Setup shared by all modular config tests."""
        # Call original setup if it exists
        if hasattr(super(), 'setup_class'):
            super().setup_class()
        
        # Store reference to ALL original test methods (including nested ones)
        import ast
        import inspect
        from pathlib import Path
        
        # Get source file of original test class
        source_file = Path(__file__).parent.parent / "test_config_system_health.py"
        content = source_file.read_text()
        tree = ast.parse(content)
        
        # Find all test methods including nested ones
        all_test_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                all_test_methods.append(node.name)
        
        # Store both accessible methods and all detected methods
        cls._accessible_methods = {
            name: getattr(cls, name) 
            for name in dir(cls) 
            if name.startswith('test_') and callable(getattr(cls, name))
        }
        cls._all_test_methods = all_test_methods
        cls._original_methods = cls._accessible_methods  # For backward compatibility
        
    def get_original_test_methods(self):
        """Get all original test methods for reference."""
        return self._original_methods.copy()
        
    def run_original_test(self, test_name: str):
        """
        Run an original test method by name.
        
        Args:
            test_name: Name of the test method (e.g., 'test_config_system_architecture_integrity')
        """
        if test_name in self._original_methods:
            return self._original_methods[test_name]()
        else:
            raise ValueError(f"Test method '{test_name}' not found in original tests")
            
    def get_tests_by_category(self, category: str) -> list:
        """
        Get original test methods categorized by functionality.
        
        Args:
            category: Category name ('architecture', 'security', 'sync', etc.)
            
        Returns:
            List of test method names in that category
        """
        categorized_tests = {
            'architecture': [
                'test_config_system_architecture_integrity',
                'test_config_synchronization_integrity'
            ],
            'security': [
                'test_environment_variable_security_audit',
                'test_config_security_hardening',
                'test_environment_variable_override_works_in_production',
                'test_config_test_environment_isolation_complete'
            ],
            'performance': [
                'test_config_performance_and_reliability'
            ],
            'integration': [
                'test_config_integration_health'
            ],
            'synchronization': [
                'test_runtime_config_consistency'
            ],
            'compliance': [
                'test_production_files_use_config_no_hardcoded_values',
                'test_dashboard_files_use_config_ports_exclusively',
                'test_api_client_files_use_config_urls_exclusively'
            ],
            'documentation': [
                'test_config_system_documentation_compliance'
            ],
            'fixtures': [
                'test_pytest_fixture_integration_comprehensive'
            ],
            'infrastructure': [
                'test_test_discovery_import_path_validation_comprehensive',
                'test_test_database_separation_and_test_config_validation',
                'test_conftest_and_test_infrastructure_config_integration'
            ]
        }
        
        return categorized_tests.get(category, [])
        
    def run_category_tests(self, category: str):
        """Run all tests in a specific category."""
        test_methods = self.get_tests_by_category(category)
        results = {}
        
        for test_name in test_methods:
            try:
                self.run_original_test(test_name)
                results[test_name] = "PASSED"
            except Exception as e:
                results[test_name] = f"FAILED: {str(e)}"
                
        return results