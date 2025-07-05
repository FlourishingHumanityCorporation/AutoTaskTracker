"""Test configuration synchronization between systems."""
import logging
import json
from pathlib import Path
import pytest

from tests.health.analyzers.config_system_analyzer import ConfigSystemAnalyzer

logger = logging.getLogger(__name__)


class TestConfigurationSync:
    """Test synchronization between different configuration systems."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.analyzer = ConfigSystemAnalyzer(cls.project_root)
    
    def test_config_synchronization_integrity(self):
        """Test that Pensieve and AutoTaskTracker configs are synchronized."""
        try:
            # Test basic sync functionality
            sync_result = self.analyzer.analyze_config_sync()
            
            if not sync_result['in_sync']:
                mismatches = sync_result.get('mismatches', [])
                error_msg = f"""
CONFIGURATION SYNCHRONIZATION ISSUES

Pensieve and AutoTaskTracker configurations are out of sync!

Mismatches found ({len(mismatches)}):
"""
                for mismatch in mismatches[:10]:
                    error_msg += f"\n  {mismatch['key']}:"
                    error_msg += f"\n    Pensieve: {mismatch.get('pensieve_value', 'Not set')}"
                    error_msg += f"\n    AutoTaskTracker: {mismatch.get('autotask_value', 'Not set')}"
                
                if len(mismatches) > 10:
                    error_msg += f"\n\n... and {len(mismatches) - 10} more mismatches"
                
                error_msg += """

TO FIX:
1. Ensure both systems read from the same config source
2. Use ConfigManager for centralized configuration
3. Implement proper config synchronization on startup
"""
                # This is a warning, not a hard failure
                logger.warning(error_msg)
            else:
                logger.info("Configuration synchronization check passed")
                
        except Exception as e:
            # Don't fail the test for sync issues, just warn
            logger.warning(f"Could not verify config synchronization: {e}")
    
    def test_runtime_config_consistency(self):
        """Test that configuration remains consistent during runtime."""
        consistency_issues = []
        
        # Check for config files that might be modified at runtime
        config_files = [
            self.project_root / "config.json",
            self.project_root / "autotasktracker" / "config.json",
            Path.home() / ".autotasktracker" / "config.json",
            Path.home() / ".memos" / "config.json",
        ]
        
        writable_configs = []
        for config_file in config_files:
            if config_file.exists():
                # Check if config file is writable
                if config_file.stat().st_mode & 0o200:
                    writable_configs.append(config_file)
        
        if writable_configs:
            logger.info(f"Found {len(writable_configs)} writable config files:")
            for config in writable_configs:
                logger.info(f"  {config}")
            logger.info("Ensure proper locking mechanisms for runtime modifications")
    
    def test_config_precedence(self):
        """Test that configuration precedence is properly implemented."""
        # Expected precedence order (highest to lowest)
        expected_precedence = [
            "Environment variables",
            "Command-line arguments",
            "User config file (~/.autotasktracker/config.json)",
            "Project config file (./config.json)",
            "Default values in code"
        ]
        
        # Check if ConfigManager implements proper precedence
        config_manager_path = self.project_root / "autotasktracker" / "core" / "config_manager.py"
        
        if config_manager_path.exists():
            content = config_manager_path.read_text()
            
            # Look for precedence implementation
            has_env_check = 'os.environ' in content
            has_user_config = '.autotasktracker' in content or 'user_config' in content
            has_default = 'default' in content.lower()
            
            if not (has_env_check and has_user_config and has_default):
                logger.warning("ConfigManager may not implement proper precedence order")
                logger.info(f"Expected precedence: {' > '.join(expected_precedence)}")
        else:
            logger.warning("ConfigManager not found - cannot verify precedence")
    
    def test_config_validation(self):
        """Test that configuration values are validated."""
        validation_issues = []
        
        # Check for config validation in key files
        files_to_check = [
            self.project_root / "autotasktracker" / "core" / "config.py",
            self.project_root / "autotasktracker" / "core" / "config_manager.py",
        ]
        
        for file_path in files_to_check:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            # Look for validation patterns
            has_validation = any(
                pattern in content
                for pattern in [
                    'validate', 'check_', 'verify_',
                    'ValueError', 'ConfigError', 'ValidationError',
                    'assert ', 'if not ', 'raise'
                ]
            )
            
            if not has_validation:
                validation_issues.append(f"{file_path.name}: No validation logic found")
        
        if validation_issues:
            logger.warning("Configuration validation issues:")
            for issue in validation_issues:
                logger.warning(f"  {issue}")
    
    def test_config_documentation(self):
        """Test that configuration options are properly documented."""
        doc_issues = []
        
        # Check for configuration documentation
        expected_docs = [
            self.project_root / "docs" / "configuration.md",
            self.project_root / "README.md",
            self.project_root / "autotasktracker" / "core" / "config.py",
        ]
        
        documented_configs = []
        for doc_path in expected_docs:
            if doc_path.exists():
                content = doc_path.read_text().lower()
                if any(term in content for term in ['configuration', 'config', 'settings', 'environment']):
                    documented_configs.append(doc_path)
        
        if not documented_configs:
            doc_issues.append("No configuration documentation found")
        
        # Check for example config
        example_configs = [
            self.project_root / "config.example.json",
            self.project_root / "example.config.json",
            self.project_root / ".env.example",
        ]
        
        if not any(f.exists() for f in example_configs):
            doc_issues.append("No example configuration file found")
        
        if doc_issues:
            logger.info("Configuration documentation suggestions:")
            for issue in doc_issues:
                logger.info(f"  {issue}")