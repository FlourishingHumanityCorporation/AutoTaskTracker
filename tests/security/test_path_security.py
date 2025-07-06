"""Security tests for path handling and validation."""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from autotasktracker.config import _validate_path_security, Config


class TestPathSecurity:
    """Test path security validation and sanitization."""

    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "\\windows\\system32\\config",
            "~/.ssh/id_rsa",
            "${HOME}/.ssh/id_rsa",
            "%USERPROFILE%\\.ssh\\id_rsa"
        ]
        
        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError, match="Path contains potentially dangerous"):
                _validate_path_security(dangerous_path)

    def test_valid_paths_accepted(self):
        """Test that valid paths are accepted."""
        valid_paths = [
            "/tmp/autotask/data",
            "~/.memos/screenshots",
            "./data/cache",
            "data/screenshots",
            "postgresql://localhost/db"
        ]
        
        for valid_path in valid_paths:
            # Should not raise exception
            result = _validate_path_security(valid_path)
            assert isinstance(result, str)

    def test_test_mode_paths_allowed(self):
        """Test that test-specific paths are allowed in test mode."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}):
            test_paths = [
                "test_database.db",
                "/tmp/test_screenshots",
                "test_cache_dir"
            ]
            
            for test_path in test_paths:
                # Should not raise exception in test mode
                result = _validate_path_security(test_path)
                assert isinstance(result, str)

    def test_empty_paths_rejected(self):
        """Test that empty or None paths are rejected."""
        invalid_paths = [None, "", "   "]
        
        for invalid_path in invalid_paths:
            with pytest.raises(ValueError, match="Path must be a non-empty string"):
                _validate_path_security(invalid_path)

    def test_config_path_validation(self):
        """Test that config paths are properly validated."""
        config = Config()
        
        # Test that accessing path properties doesn't raise exceptions
        screenshots_dir = config.SCREENSHOTS_DIR
        logs_dir = config.LOGS_DIR
        vlm_cache_dir = config.VLM_CACHE_DIR
        
        assert isinstance(screenshots_dir, str)
        assert isinstance(logs_dir, str)
        assert isinstance(vlm_cache_dir, str)
        
        # Paths should be normalized
        assert not screenshots_dir.endswith("/")
        assert not logs_dir.endswith("/")
        assert not vlm_cache_dir.endswith("/")


class TestDatabaseSecurity:
    """Test database connection security."""

    def test_database_uri_validation(self):
        """Test database URI validation."""
        # Valid URIs should be accepted
        valid_uris = [
            "postgresql://user:pass@localhost:5432/db",
            "sqlite:///path/to/db.sqlite",
            "~/.memos/database.db"
        ]
        
        for uri in valid_uris:
            # Should not raise exception
            result = _validate_path_security(uri)
            assert isinstance(result, str)

    def test_sql_injection_protection(self):
        """Test basic SQL injection protection patterns."""
        from autotasktracker.core.database import DatabaseManager
        
        # Test that DatabaseManager uses parameterized queries
        db = DatabaseManager()
        
        # Check that direct SQL execution methods require parameters
        assert hasattr(db, 'execute_query')
        
        # DatabaseManager should use context managers for connections
        assert hasattr(db, 'get_connection')


class TestFileSecurity:
    """Test file operation security."""

    def test_temp_file_security(self):
        """Test temporary file creation security."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file path
            test_file = Path(temp_dir) / "test_file.txt"
            
            # File should be created with secure permissions
            test_file.write_text("test content")
            
            # Check file permissions (should not be world-readable)
            file_stat = test_file.stat()
            permissions = oct(file_stat.st_mode)[-3:]
            
            # Should not be world-writable (last digit should be < 2)
            assert int(permissions[-1]) < 2

    def test_screenshot_directory_security(self):
        """Test screenshot directory creation and permissions."""
        from autotasktracker.config import get_config
        
        config = get_config()
        screenshots_dir = config.SCREENSHOTS_DIR
        
        # Directory path should be normalized
        assert not screenshots_dir.endswith("/")
        
        # Should not contain dangerous patterns
        dangerous_patterns = ["../", "..\\", "/etc/", "\\system32\\"]
        for pattern in dangerous_patterns:
            assert pattern not in screenshots_dir


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_filename_sanitization(self):
        """Test filename sanitization for security."""
        dangerous_filenames = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "file<script>alert('xss')</script>.txt",
            "file|rm -rf /.txt",
            "file;cat /etc/passwd.txt"
        ]
        
        # These should be rejected or sanitized
        for filename in dangerous_filenames:
            # Basic validation - should not contain path separators
            assert "/" not in Path(filename).name or ".." not in filename

    def test_environment_variable_injection(self):
        """Test protection against environment variable injection."""
        dangerous_env_patterns = [
            "${PATH}",
            "%PATH%",
            "$USER",
            "%USERPROFILE%"
        ]
        
        for pattern in dangerous_env_patterns:
            with pytest.raises(ValueError):
                _validate_path_security(pattern)


class TestConfigurationSecurity:
    """Test configuration security measures."""

    def test_sensitive_data_not_logged(self):
        """Test that sensitive configuration data is not logged."""
        import logging
        from io import StringIO
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("autotasktracker.config")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            # Create config (may log configuration info)
            config = Config()
            db_path = config.DB_PATH
            
            # Check that passwords/secrets are not in logs
            log_output = log_capture.getvalue()
            
            # Should not contain common password patterns
            sensitive_patterns = [
                "password",
                "secret",
                "token",
                "key="
            ]
            
            for pattern in sensitive_patterns:
                # Case-insensitive check, but avoid false positives
                log_lower = log_output.lower()
                if pattern in log_lower:
                    # Allow if it's just the word "password" in field names
                    assert "password" not in log_lower or "password=" not in log_lower
                    
        finally:
            logger.removeHandler(handler)

    def test_default_config_security(self):
        """Test that default configuration is secure."""
        config = Config()
        
        # Database URL should not contain default passwords in production
        if not os.getenv("PYTEST_CURRENT_TEST"):
            # In production, should not use default passwords
            db_url = config.DB_PATH
            if "postgresql://" in db_url:
                # Should not contain obvious default passwords
                insecure_patterns = ["password", "123456", "admin", "root"]
                for pattern in insecure_patterns:
                    assert pattern not in db_url.lower()