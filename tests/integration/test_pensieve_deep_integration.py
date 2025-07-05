"""Comprehensive integration tests for Pensieve deep integration."""

import pytest
import time
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from autotasktracker.pensieve.api_client import get_pensieve_client, reset_pensieve_client
from autotasktracker.pensieve.config_reader import get_pensieve_config_reader
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.core.database import DatabaseManager
from autotasktracker.dashboards.base import BaseDashboard


class TestPensieveAPIClient:
    """Test Pensieve API client functionality."""
    
    def test_api_client_initialization(self):
        """Test API client can be initialized."""
        client = get_pensieve_client()
        assert client is not None
        assert client.base_url == "http://localhost:8839"
        assert client.timeout == 30
    
    def test_api_client_health_check(self):
        """Test API client health checking."""
        client = get_pensieve_client()
        
        # Health check should return boolean
        healthy = client.is_healthy()
        assert isinstance(healthy, bool)
        
        # If healthy, should be able to make requests
        if healthy:
            frames = client.get_frames(limit=1)
            assert isinstance(frames, list)
    
    def test_api_client_singleton_behavior(self):
        """Test API client singleton pattern."""
        client1 = get_pensieve_client()
        client2 = get_pensieve_client()
        assert client1 is client2
        
        # Reset and get new instance
        reset_pensieve_client()
        client3 = get_pensieve_client()
        assert client3 is not client1
    
    def test_api_client_error_handling(self):
        """Test API client handles errors gracefully."""
        client = get_pensieve_client()
        
        # Test with invalid frame ID
        frame = client.get_frame(999999)
        assert frame is None
        
        # Test OCR for non-existent frame
        ocr_text = client.get_ocr_result(999999)
        assert ocr_text is None
        
        # Test metadata for non-existent frame
        metadata = client.get_metadata(999999)
        assert isinstance(metadata, dict)
        assert len(metadata) == 0


class TestPensieveConfigReader:
    """Test Pensieve configuration synchronization."""
    
    def test_config_reader_initialization(self):
        """Test config reader can be initialized."""
        config_reader = get_pensieve_config_reader()
        assert config_reader is not None
        assert config_reader.memos_dir.exists()
    
    def test_memos_status_check(self):
        """Test memos service status checking."""
        config_reader = get_pensieve_config_reader()
        status = config_reader.get_memos_status()
        
        assert isinstance(status, dict)
        assert 'running' in status
        assert 'output' in status
        assert isinstance(status['running'], bool)
    
    def test_pensieve_config_reading(self):
        """Test Pensieve configuration reading."""
        config_reader = get_pensieve_config_reader()
        pensieve_config = config_reader.read_pensieve_config()
        
        assert pensieve_config is not None
        assert hasattr(pensieve_config, 'database_path')
        assert hasattr(pensieve_config, 'record_interval')
        assert hasattr(pensieve_config, 'api_port')
        
        # Validate config values
        assert isinstance(pensieve_config.record_interval, int)
        assert pensieve_config.record_interval > 0
        assert isinstance(pensieve_config.api_port, int)
        assert 1024 <= pensieve_config.api_port <= 65535
    
    def test_autotasktracker_config_sync(self):
        """Test AutoTaskTracker config synchronization."""
        config_reader = get_pensieve_config_reader()
        sync_config = config_reader.sync_autotasktracker_config()
        
        assert isinstance(sync_config, dict)
        assert 'DB_PATH' in sync_config
        assert 'SCREENSHOT_INTERVAL_SECONDS' in sync_config
        assert 'MEMOS_PORT' in sync_config
        assert 'PENSIEVE_API_URL' in sync_config
        
        # Validate sync values
        assert sync_config['SCREENSHOT_INTERVAL_SECONDS'] > 0
        assert sync_config['MEMOS_PORT'] > 1024
        assert 'localhost' in sync_config['PENSIEVE_API_URL']
    
    def test_pensieve_setup_validation(self):
        """Test Pensieve setup validation."""
        config_reader = get_pensieve_config_reader()
        validation = config_reader.validate_pensieve_setup()
        
        assert isinstance(validation, dict)
        assert 'valid' in validation
        assert 'issues' in validation
        assert 'warnings' in validation
        assert 'status' in validation
        
        assert isinstance(validation['valid'], bool)
        assert isinstance(validation['issues'], list)
        assert isinstance(validation['warnings'], list)


class TestPensieveHealthMonitor:
    """Test Pensieve health monitoring."""
    
    def test_pensieve_health_monitor_initialization(self):
        """Test Pensieve health monitor can be initialized."""
        monitor = get_health_monitor()
        assert monitor is not None
        assert monitor.check_interval > 0
    
    @pytest.mark.timeout(30)
    def test_health_check_functionality(self):
        """Test health check performs comprehensive checks."""
        monitor = get_health_monitor()
        
        # Perform health check
        start_time = time.time()
        status = monitor.check_health()
        check_time = time.time() - start_time
        
        # Validate health status
        assert hasattr(status, 'is_healthy')
        assert hasattr(status, 'api_responding')
        assert hasattr(status, 'service_running')
        assert hasattr(status, 'database_accessible')
        assert hasattr(status, 'response_time_ms')
        
        assert isinstance(status.is_healthy, bool)
        assert isinstance(status.response_time_ms, (int, float))
        assert check_time < 10  # Should complete within 10 seconds
    
    def test_health_summary_generation(self):
        """Test health summary generation."""
        monitor = get_health_monitor()
        summary = monitor.get_health_summary()
        
        assert isinstance(summary, dict)
        assert 'status' in summary
        assert 'components' in summary
        assert 'metrics' in summary
        
        # Validate summary structure
        assert summary['status'] in ['healthy', 'unhealthy', 'unknown']
        assert isinstance(summary['components'], dict)
        assert isinstance(summary['metrics'], dict)
    
    def test_health_caching(self):
        """Test health status caching behavior."""
        monitor = get_health_monitor()
        
        # First check
        start_time = time.time()
        is_healthy_1 = monitor.is_healthy(max_age_seconds=60)
        time_1 = time.time() - start_time
        
        # Second check (should use cache)
        start_time = time.time()
        is_healthy_2 = monitor.is_healthy(max_age_seconds=60)
        time_2 = time.time() - start_time
        
        # Results should be the same
        assert is_healthy_1 == is_healthy_2
        # Second check should be much faster (cached)
        assert time_2 < time_1 * 0.5


class TestDatabaseManagerIntegration:
    """Test DatabaseManager integration with Pensieve."""
    
    def test_database_manager_pensieve_integration(self):
        """Test DatabaseManager with Pensieve API integration."""
        # Test with API enabled
        db_api = DatabaseManager(use_pensieve_api=True)
        assert db_api.use_pensieve_api is True
        
        # Test with API disabled
        db_direct = DatabaseManager(use_pensieve_api=False)
        assert db_direct.use_pensieve_api is False
    
    def test_database_manager_api_methods(self):
        """Test DatabaseManager API-specific methods."""
        db = DatabaseManager(use_pensieve_api=True)
        
        # Test getting frames via API
        frames = db.get_frames_via_api(limit=5)
        assert isinstance(frames, list)
        
        # Test metadata operations
        metadata = db.get_frame_metadata_via_api(1)
        assert isinstance(metadata, dict)
        
        # Test storing metadata (should not fail)
        result = db.store_frame_metadata_via_api(1, 'test_key', 'test_value')
        assert isinstance(result, bool)
    
    def test_database_manager_fallback_behavior(self):
        """Test DatabaseManager graceful fallback with comprehensive validation."""
        # Create DB manager with API that might not be available
        db = DatabaseManager(use_pensieve_api=True)
        
        # Validate DatabaseManager initialization
        assert db is not None, "DatabaseManager should initialize successfully"
        assert hasattr(db, 'get_connection'), "DatabaseManager should have get_connection method"
        assert hasattr(db, 'use_pensieve_api'), "DatabaseManager should track API usage preference"
        assert isinstance(db.use_pensieve_api, bool), "API usage flag should be boolean"
        
        # Even if API is unavailable, basic operations should work
        try:
            connection = db.get_connection()
            
            # Validate connection functionality
            assert connection is not None, "Should get valid connection even with API fallback"
            assert hasattr(connection, 'execute'), "Connection should have execute method"
            assert hasattr(connection, 'cursor'), "Connection should have cursor method"
            
            # Test basic SQL operations work
            cursor = connection.cursor()
            assert cursor is not None, "Should get valid cursor"
            
            # Validate we can perform basic queries
            cursor.execute("SELECT 1 as test_value")
            result = cursor.fetchone()
            assert result is not None, "Should get query result"
            assert result[0] == 1, "Should get correct test value"
            
            # Test database schema accessibility
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 5")
            tables = cursor.fetchall()
            assert isinstance(tables, list), "Should get list of tables"
            # Tables might be empty in test environment, which is okay
            
            connection.close()
            
        except Exception as e:
            pytest.fail(f"DatabaseManager should handle API unavailability gracefully: {e}")
        
        # Test fallback behavior when explicitly using direct connection
        db_direct = DatabaseManager(use_pensieve_api=False)
        assert db_direct is not None, "Direct database manager should initialize"
        assert not db_direct.use_pensieve_api, "Should correctly set API usage to False"
        
        # Direct connection should work
        direct_conn = db_direct.get_connection()
        assert direct_conn is not None, "Direct connection should work"
        direct_conn.close()


class TestBaseDashboardIntegration:
    """Test BaseDashboard integration with Pensieve health monitoring."""
    
    def test_base_dashboard_initialization(self):
        """Test BaseDashboard initializes with health monitoring."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.sidebar'), \
             patch('streamlit.session_state', {}):
            
            dashboard = BaseDashboard("Test Dashboard", "🧪")
            
            # Should inherit from HealthAwareMixin
            assert hasattr(dashboard, '_health_monitor')
            assert hasattr(dashboard, 'is_pensieve_available')
            assert hasattr(dashboard, 'get_health_status')
    
    def test_base_dashboard_database_manager(self):
        """Test BaseDashboard creates DatabaseManager with proper integration."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.sidebar'), \
             patch('streamlit.session_state', {}):
            
            dashboard = BaseDashboard("Test Dashboard", "🧪")
            
            # Should create DatabaseManager with API integration
            db_manager = dashboard.db_manager
            assert isinstance(db_manager, DatabaseManager)
            assert hasattr(db_manager, 'use_pensieve_api')
    
    def test_base_dashboard_health_status_display(self):
        """Test BaseDashboard health status display with comprehensive validation."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.sidebar') as mock_sidebar, \
             patch('streamlit.session_state', {}), \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.warning') as mock_warning:
            
            # Test dashboard initialization
            dashboard = BaseDashboard("Test Dashboard", "🧪")
            
            # Validate dashboard was created properly
            assert dashboard is not None, "Dashboard should initialize successfully"
            assert hasattr(dashboard, 'show_health_status'), "Dashboard should have health status method"
            assert hasattr(dashboard, 'title'), "Dashboard should have title attribute"
            assert dashboard.title == "Test Dashboard", "Dashboard title should be set correctly"
            
            # Health status should be displayed
            dashboard.show_health_status()
            
            # Validate UI interaction patterns
            assert mock_sidebar.called, "Should use sidebar for health status display"
            
            # Validate health status calls one of the status methods
            status_called = mock_success.called or mock_error.called or mock_warning.called
            assert status_called, "Health status should display some status (success/error/warning)"
            
            # Test the health status display handles different states
            total_status_calls = mock_success.call_count + mock_error.call_count + mock_warning.call_count
            assert total_status_calls > 0, "Should make at least one status display call"
            assert total_status_calls <= 10, "Should not spam with excessive status calls"
            
            # Validate dashboard maintains state properly
            assert hasattr(dashboard, 'db'), "Dashboard should have database connection"
            assert dashboard.db is not None, "Database connection should be initialized"


class TestEndToEndIntegration:
    """Test complete end-to-end integration scenarios."""
    
    def test_complete_pipeline_integration(self):
        """Test complete pipeline from config to dashboard."""
        # 1. Config reader should work
        config_reader = get_pensieve_config_reader()
        pensieve_config = config_reader.read_pensieve_config()
        assert pensieve_config is not None
        
        # 2. API client should be able to connect
        client = get_pensieve_client()
        healthy = client.is_healthy()
        # Note: This might be False in CI environments
        assert isinstance(healthy, bool)
        
        # 3. Health monitor should provide status
        monitor = get_health_monitor()
        summary = monitor.get_health_summary()
        assert summary['status'] in ['healthy', 'unhealthy', 'unknown']
        
        # 4. DatabaseManager should handle both modes
        db_api = DatabaseManager(use_pensieve_api=True)
        db_direct = DatabaseManager(use_pensieve_api=False)
        
        assert db_api.use_pensieve_api is True
        assert db_direct.use_pensieve_api is False
    
    def test_performance_characteristics(self):
        """Test performance characteristics of integration."""
        # Health check should be fast
        monitor = get_health_monitor()
        
        start_time = time.time()
        status = monitor.check_health()
        check_time = time.time() - start_time
        
        # Health check should complete within reasonable time
        assert check_time < 5.0, f"Health check took {check_time:.2f}s, should be < 5s"
        
        # API client operations should be fast
        client = get_pensieve_client()
        
        start_time = time.time()
        healthy = client.is_healthy()
        health_time = time.time() - start_time
        
        # Health check should be very fast
        assert health_time < 2.0, f"API health check took {health_time:.2f}s, should be < 2s"
    
    def test_error_resilience(self):
        """Test system resilience to various error conditions."""
        # Test with unavailable API
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            client = get_pensieve_client()
            # Should handle gracefully
            healthy = client.is_healthy()
            assert healthy is False
            
            frames = client.get_frames(limit=1)
            assert isinstance(frames, list)
            assert len(frames) == 0
        
        # Test DatabaseManager fallback
        db = DatabaseManager(use_pensieve_api=True)
        # Should not raise exceptions even if API is unavailable
        try:
            frames = db.get_frames_via_api(limit=1)
            assert isinstance(frames, list)
        except Exception as e:
            pytest.fail(f"DatabaseManager should handle API errors gracefully: {e}")


@pytest.fixture(autouse=True)
def reset_clients():
    """Reset singleton clients before each test."""
    reset_pensieve_client()
    yield
    reset_pensieve_client()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])