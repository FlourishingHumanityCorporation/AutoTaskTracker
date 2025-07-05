"""
Configuration loading health tests.

Tests configuration system architecture integrity, loading performance,
and environment variable handling using extracted analyzers.
"""

import os
import time
from pathlib import Path
import pytest
import logging

from tests.health.analyzers.config_system_analyzer import ConfigSystemAnalyzer

logger = logging.getLogger(__name__)


class TestConfigLoadingHealth:
    """Configuration loading and architecture health checks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.analyzer = ConfigSystemAnalyzer(cls.project_root)
        
    def test_config_system_architecture_integrity(self):
        """Test that the configuration system architecture is sound."""
        results = self.analyzer.analyze_architecture_integrity()
        
        # Main config validation
        assert results['main_config_valid'], "Main config should load successfully"
        assert 'DB_PATH' in results['config_attributes'], "Config missing critical DB_PATH attribute"
        assert 'get_db_path' in results['config_attributes'], "Config missing get_db_path method"
        
        # Performance validation
        assert results['load_time_ms'] < 5000, f"Config loading too slow: {results['load_time_ms']:.1f}ms"
        
        # Error validation
        if results['errors']:
            error_msg = f"""
🚨 CONFIGURATION ARCHITECTURE ISSUES 🚨

Found {len(results['errors'])} architecture issues:

{chr(10).join(f'  ❌ {error}' for error in results['errors'])}

✅ REQUIREMENTS:
  - Main config must be Config instance
  - Must have DB_PATH and get_db_path attributes
  - Pensieve config must load within 2 seconds
  - No critical attribute missing

📊 CURRENT STATUS:
  - Main config valid: {results['main_config_valid']}
  - Pensieve config valid: {results['pensieve_config_valid']}
  - Load time: {results['load_time_ms']:.1f}ms
  - Config attributes: {len(results['config_attributes'])}
"""
            raise AssertionError(error_msg)
            
    def test_environment_variable_security_audit(self):
        """Audit environment variable handling for security and correctness."""
        results = self.analyzer.analyze_environment_variable_security()
        
        # Security issue validation
        if results['security_issues']:
            error_msg = f"""
🚨 ENVIRONMENT VARIABLE SECURITY ISSUES 🚨

Found {len(results['security_issues'])} security issues:

{chr(10).join(f'  ❌ {issue}' for issue in results['security_issues'])}

🔒 SECURITY CONCERNS:
"""
            if results['sensitive_patterns']:
                error_msg += "\n  Sensitive environment variables detected:\n"
                for pattern in results['sensitive_patterns']:
                    error_msg += f"    • {pattern['var']}: {pattern['masked_value']} (length: {pattern['length']})\n"
                    
            error_msg += """
✅ SECURITY REQUIREMENTS:
  - No sensitive data in environment variables
  - Proper validation of environment variables
  - No config loading errors from env vars
  - Environment isolation in tests

💡 RECOMMENDATIONS:
  - Use secure secrets management
  - Validate all environment variables
  - Use environment-specific configs
  - Implement proper error handling
"""
            raise AssertionError(error_msg)
            
        # Validation results check
        failed_validations = [
            var for var, result in results['validation_results'].items()
            if result.startswith('error:')
        ]
        
        if failed_validations:
            error_msg = f"""
🚨 ENVIRONMENT VARIABLE VALIDATION FAILURES 🚨

{len(failed_validations)} environment variables failed validation:

{chr(10).join(f'  ❌ {var}: {results["validation_results"][var]}' for var in failed_validations)}

✅ All environment variables must be validated properly
"""
            raise AssertionError(error_msg)
            
    def test_config_performance_and_reliability(self):
        """Test configuration system performance and reliability."""
        results = self.analyzer.analyze_performance_reliability()
        
        # Performance validation
        avg_time = results['load_times']['average_ms']
        max_time = results['load_times']['max_ms']
        reliability = results['reliability_score']
        
        performance_issues = []
        
        if avg_time > 100:
            performance_issues.append(f"Slow average load time: {avg_time:.1f}ms (should be <100ms)")
            
        if max_time > 500:
            performance_issues.append(f"Inconsistent load times: max {max_time:.1f}ms (should be <500ms)")
            
        if reliability < 80:
            performance_issues.append(f"Low reliability score: {reliability} (should be ≥80)")
            
        if results['performance_issues']:
            performance_issues.extend(results['performance_issues'])
            
        if performance_issues:
            error_msg = f"""
🚨 CONFIGURATION PERFORMANCE ISSUES 🚨

Found {len(performance_issues)} performance issues:

{chr(10).join(f'  ❌ {issue}' for issue in performance_issues)}

📊 PERFORMANCE METRICS:
  - Average load time: {avg_time:.1f}ms
  - Min load time: {results['load_times']['min_ms']:.1f}ms
  - Max load time: {max_time:.1f}ms
  - Reliability score: {reliability}/100

💾 MEMORY USAGE:
  - First load current: {results['memory_usage'].get('first_load', {}).get('current_kb', 0):.1f}KB
  - First load peak: {results['memory_usage'].get('first_load', {}).get('peak_kb', 0):.1f}KB

✅ PERFORMANCE REQUIREMENTS:
  - Average load time <100ms
  - Max load time <500ms
  - Reliability score ≥80
  - Consistent performance across loads

💡 OPTIMIZATION TIPS:
  - Cache configuration objects
  - Lazy load expensive operations
  - Minimize I/O during config loading
  - Use efficient data structures
"""
            raise AssertionError(error_msg)
            
    def test_config_integration_health(self):
        """Test configuration integration with dependent systems."""
        results = self.analyzer.analyze_config_integration()
        
        integration_failures = []
        
        if not results['database_integration']:
            integration_failures.append("Database integration failed")
            
        if not results['api_integration']:
            integration_failures.append("API integration failed")
            
        if not results['service_integration']:
            integration_failures.append("Service integration failed")
            
        if integration_failures or results['integration_issues']:
            error_msg = f"""
🚨 CONFIGURATION INTEGRATION FAILURES 🚨

Integration status:
  - Database: {'✅' if results['database_integration'] else '❌'}
  - API: {'✅' if results['api_integration'] else '❌'}
  - Service: {'✅' if results['service_integration'] else '❌'}

"""
            if results['integration_issues']:
                error_msg += f"Integration issues found:\n"
                error_msg += chr(10).join(f'  ❌ {issue}' for issue in results['integration_issues'])
                error_msg += "\n"
                
            error_msg += """
✅ INTEGRATION REQUIREMENTS:
  - Database manager must use config paths
  - API client must use config URLs
  - Service integration must be functional
  - All integrations must handle config changes

🔧 TROUBLESHOOTING:
  - Check database file permissions
  - Verify API endpoint configuration
  - Ensure Pensieve service is accessible
  - Validate configuration synchronization
"""
            raise AssertionError(error_msg)
            
    def test_config_security_hardening(self):
        """Test configuration security hardening measures."""
        results = self.analyzer.analyze_security_hardening()
        
        security_score = results['security_score']
        
        if security_score < 80 or results['insecure_patterns']:
            error_msg = f"""
🚨 CONFIGURATION SECURITY ISSUES 🚨

Security Score: {security_score}/100 (should be ≥80)

"""
            if results['insecure_patterns']:
                error_msg += f"Insecure patterns found:\n"
                for pattern in results['insecure_patterns']:
                    if 'error' in pattern:
                        error_msg += f"  ❌ {pattern['error']}\n"
                    else:
                        error_msg += f"  ❌ {pattern['file']}: {pattern['pattern']} ({pattern['matches']} matches)\n"
                error_msg += "\n"
                
            if results['recommendations']:
                error_msg += f"Security recommendations:\n"
                error_msg += chr(10).join(f'  💡 {rec}' for rec in results['recommendations'])
                error_msg += "\n"
                
            error_msg += """
✅ SECURITY REQUIREMENTS:
  - No hardcoded passwords, secrets, or tokens
  - Use environment variables for sensitive data
  - Implement proper secrets management
  - Validate all configuration inputs
  - Use secure defaults

🔒 BEST PRACTICES:
  - Move secrets to environment variables
  - Use configuration validation schemas
  - Implement runtime security checks
  - Regular security audits
  - Secure configuration file permissions
"""
            raise AssertionError(error_msg)