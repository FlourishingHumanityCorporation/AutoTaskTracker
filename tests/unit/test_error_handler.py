"""
Comprehensive tests for Error Handler module.

Tests cover all error handling functionality including:
- VLMErrorHandler: error recording, statistics, history
- VLMMetrics: latency recording, counters, statistics
- HealthMonitor: health check registration, alerts
- Decorators: error handling and latency measurement
- Thread safety and concurrent access
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
from datetime import datetime, timedelta
from collections import deque
import logging

from autotasktracker.core.error_handler import (
    VLMErrorHandler, VLMMetrics, HealthMonitor,
    vlm_error_handler, measure_latency,
    get_error_handler, get_metrics, get_health_monitor
)


class TestVLMErrorHandler:
    """Test the VLMErrorHandler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a VLMErrorHandler instance."""
        from pathlib import Path
        with patch('pathlib.Path.home', return_value=Path('/home/test')):
            with patch('pathlib.Path.mkdir'):
                handler = VLMErrorHandler(max_error_history=10)
                return handler
    
    def test_error_handler_initialization(self, error_handler):
        """Test error handler initialization."""
        assert error_handler.max_error_history == 10
        assert isinstance(error_handler.error_history, deque)
        assert error_handler.error_history.maxlen == 10
        assert isinstance(error_handler.error_counts, dict)
        assert isinstance(error_handler.error_lock, type(threading.Lock()))
        assert isinstance(error_handler.logger, logging.Logger)
    
    def test_record_error(self, error_handler):
        """Test error recording functionality."""
        # Record a test error
        test_error = ValueError("Test error message")
        context = {"operation": "test_op", "file": "test.png"}
        
        with patch.object(error_handler.logger, 'error') as mock_logger:
            error_handler.record_error(test_error, context)
        
        # Verify error was recorded
        assert len(error_handler.error_history) == 1
        assert error_handler.error_counts['ValueError'] == 1
        
        # Check error record structure
        error_record = error_handler.error_history[0]
        assert error_record['error_type'] == 'ValueError'
        assert error_record['error_message'] == 'Test error message'
        assert error_record['context'] == context
        assert 'timestamp' in error_record
        assert 'traceback' in error_record
        
        # Verify logging
        assert mock_logger.call_count == 3
    
    def test_error_history_limit(self, error_handler):
        """Test that error history respects max limit."""
        # Record more errors than max_error_history
        for i in range(15):
            error = Exception(f"Error {i}")
            error_handler.record_error(error, {"index": i})
        
        # Should only keep last 10 errors
        assert len(error_handler.error_history) == 10
        # First error should be Error 5 (0-4 were dropped)
        assert error_handler.error_history[0]['context']['index'] == 5
        assert error_handler.error_history[-1]['context']['index'] == 14
    
    def test_get_error_stats(self, error_handler):
        """Test error statistics calculation."""
        # Record various errors
        error_handler.record_error(ValueError("val1"), {})
        error_handler.record_error(ValueError("val2"), {})
        error_handler.record_error(TypeError("type1"), {})
        error_handler.record_error(RuntimeError("runtime1"), {})
        
        stats = error_handler.get_error_stats()
        
        assert stats['total_errors'] == 4
        assert stats['error_types']['ValueError'] == 2
        assert stats['error_types']['TypeError'] == 1
        assert stats['error_types']['RuntimeError'] == 1
        assert stats['most_common_error'] == 'ValueError'
        assert 'recent_errors_1h' in stats
        assert 'recent_error_rate' in stats
    
    def test_get_recent_errors(self, error_handler):
        """Test retrieving recent errors."""
        # Record 5 errors
        for i in range(5):
            error_handler.record_error(Exception(f"Error {i}"), {"index": i})
        
        # Get last 3
        recent = error_handler.get_recent_errors(limit=3)
        assert len(recent) == 3
        assert recent[0]['context']['index'] == 2
        assert recent[2]['context']['index'] == 4
        
        # Get all
        all_errors = error_handler.get_recent_errors(limit=10)
        assert len(all_errors) == 5
    
    def test_thread_safety(self, error_handler):
        """Test thread safety of error recording."""
        errors_to_record = 100
        threads = []
        
        def record_errors(thread_id):
            for i in range(10):
                error_handler.record_error(
                    Exception(f"Thread {thread_id} Error {i}"),
                    {"thread": thread_id, "index": i}
                )
        
        # Start multiple threads
        for i in range(10):
            thread = threading.Thread(target=record_errors, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all errors were recorded (limited by max_error_history)
        assert len(error_handler.error_history) == error_handler.max_error_history
        assert sum(error_handler.error_counts.values()) == errors_to_record


class TestVLMMetrics:
    """Test the VLMMetrics class."""
    
    @pytest.fixture
    def metrics(self):
        """Create a VLMMetrics instance."""
        return VLMMetrics()
    
    def test_metrics_initialization(self, metrics):
        """Test metrics initialization."""
        assert isinstance(metrics.metrics, dict)
        assert isinstance(metrics.counters, dict)
        assert isinstance(metrics.lock, type(threading.Lock()))
    
    def test_record_latency(self, metrics):
        """Test latency recording."""
        # Record some latencies
        metrics.record_latency('process_image', 100.5)
        metrics.record_latency('process_image', 150.2)
        metrics.record_latency('process_image', 120.8)
        
        assert len(metrics.metrics['process_image_latency']) == 3
        
        # Check data structure
        first_record = metrics.metrics['process_image_latency'][0]
        assert 'timestamp' in first_record
        assert first_record['value'] == 100.5
    
    def test_latency_limit(self, metrics):
        """Test that latency history is limited to 1000 entries."""
        # Record more than 1000 latencies
        for i in range(1100):
            metrics.record_latency('test_op', float(i))
        
        # Should only keep last 1000
        assert len(metrics.metrics['test_op_latency']) == 1000
        # First value should be 100 (0-99 were dropped)
        assert metrics.metrics['test_op_latency'][0]['value'] == 100.0
    
    def test_increment_counter(self, metrics):
        """Test counter incrementing."""
        metrics.increment_counter('api_calls')
        metrics.increment_counter('api_calls')
        metrics.increment_counter('errors')
        
        assert metrics.counters['api_calls'] == 2
        assert metrics.counters['errors'] == 1
    
    def test_get_metrics_summary(self, metrics):
        """Test metrics summary calculation."""
        # Record various metrics
        latencies = [100, 200, 150, 300, 250, 180, 220, 190, 210, 240]
        for latency in latencies:
            metrics.record_latency('api_call', latency)
        
        metrics.increment_counter('success')
        metrics.increment_counter('success')
        metrics.increment_counter('failure')
        
        summary = metrics.get_metrics_summary()
        
        # Check counters
        assert summary['counters']['success'] == 2
        assert summary['counters']['failure'] == 1
        
        # Check latency statistics
        api_stats = summary['api_call_latency']
        assert api_stats['count'] == 10
        assert api_stats['avg'] == sum(latencies) / len(latencies)
        assert api_stats['min'] == 100
        assert api_stats['max'] == 300
        assert 'p95' in api_stats
    
    def test_thread_safety_metrics(self, metrics):
        """Test thread safety of metrics recording."""
        threads = []
        
        def record_metrics(thread_id):
            for i in range(100):
                metrics.record_latency('operation', float(thread_id * 100 + i))
                metrics.increment_counter(f'thread_{thread_id}')
        
        # Start multiple threads
        for i in range(5):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify metrics
        assert len(metrics.metrics['operation_latency']) == 500
        for i in range(5):
            assert metrics.counters[f'thread_{i}'] == 100


class TestHealthMonitor:
    """Test the HealthMonitor class."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create a HealthMonitor instance."""
        return HealthMonitor()
    
    def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization."""
        assert isinstance(health_monitor.health_checks, dict)
        assert isinstance(health_monitor.alerts, deque)
        assert health_monitor.alerts.maxlen == 100
        assert isinstance(health_monitor.lock, type(threading.Lock()))
    
    def test_register_health_check(self, health_monitor):
        """Test registering health check functions."""
        def check_service():
            return True
        
        health_monitor.register_health_check('service', check_service, alert_threshold=5)
        
        assert 'service' in health_monitor.health_checks
        check_info = health_monitor.health_checks['service']
        assert check_info['func'] == check_service
        assert check_info['failures'] == 0
        assert check_info['alert_threshold'] == 5
        assert check_info['status'] == 'unknown'
    
    def test_run_health_checks_success(self, health_monitor):
        """Test running health checks that succeed."""
        # Register healthy checks
        health_monitor.register_health_check('check1', lambda: True)
        health_monitor.register_health_check('check2', lambda: True)
        
        results = health_monitor.run_health_checks()
        
        assert results['check1'] == 'healthy'
        assert results['check2'] == 'healthy'
        assert health_monitor.health_checks['check1']['failures'] == 0
        assert health_monitor.health_checks['check2']['failures'] == 0
    
    def test_run_health_checks_failure(self, health_monitor):
        """Test running health checks that fail."""
        # Register failing check
        health_monitor.register_health_check('failing', lambda: False, alert_threshold=2)
        
        # First failure
        results = health_monitor.run_health_checks()
        assert results['failing'] == 'unhealthy'
        assert health_monitor.health_checks['failing']['failures'] == 1
        assert len(health_monitor.alerts) == 0  # No alert yet
        
        # Second failure - should trigger alert
        with patch('logging.getLogger') as mock_logger:
            mock_logger.return_value.warning = Mock()
            results = health_monitor.run_health_checks()
            
        assert health_monitor.health_checks['failing']['failures'] == 2
        assert len(health_monitor.alerts) == 1
        assert health_monitor.alerts[0]['source'] == 'failing'
    
    def test_health_check_exception(self, health_monitor):
        """Test health check that raises exception."""
        def failing_check():
            raise RuntimeError("Check failed")
        
        health_monitor.register_health_check('error_check', failing_check)
        
        with patch('logging.getLogger') as mock_logger:
            mock_logger.return_value.warning = Mock()
            results = health_monitor.run_health_checks()
        
        assert 'error: Check failed' in results['error_check']
        assert health_monitor.health_checks['error_check']['status'] == 'error'
        assert len(health_monitor.alerts) == 1
    
    def test_get_recent_alerts(self, health_monitor):
        """Test retrieving recent alerts."""
        # Generate some alerts
        for i in range(5):
            health_monitor._generate_alert(f'source_{i}', f'Alert {i}')
        
        recent = health_monitor.get_recent_alerts(limit=3)
        assert len(recent) == 3
        assert recent[0]['message'] == 'Alert 2'
        assert recent[2]['message'] == 'Alert 4'


class TestDecorators:
    """Test the decorator functions."""
    
    def test_vlm_error_handler_decorator(self):
        """Test the vlm_error_handler decorator."""
        # Get the global handler
        handler = get_error_handler()
        
        # Clear any existing errors
        handler.error_history.clear()
        handler.error_counts.clear()
        
        @vlm_error_handler(context={'operation': 'test'})
        def failing_function(x):
            if x < 0:
                raise ValueError("Negative value")
            return x * 2
        
        # Test successful call
        result = failing_function(5)
        assert result == 10
        
        # Test failing call
        with pytest.raises(ValueError):
            failing_function(-1)
        
        # Check error was recorded
        assert len(handler.error_history) == 1
        assert handler.error_counts['ValueError'] == 1
        error_record = handler.error_history[0]
        assert error_record['context']['operation'] == 'test'
        assert error_record['context']['function'] == 'failing_function'
    
    def test_measure_latency_decorator(self):
        """Test the measure_latency decorator."""
        # Get the global metrics
        metrics = get_metrics()
        
        # Clear existing metrics
        metrics.metrics.clear()
        metrics.counters.clear()
        
        @measure_latency('test_operation')
        def timed_function(delay=0):
            if delay < 0:
                raise RuntimeError("Invalid delay")
            time.sleep(delay)
            return "done"
        
        # Test successful call
        result = timed_function(0.01)
        assert result == "done"
        
        # Check metrics
        assert metrics.counters['test_operation_success'] == 1
        assert len(metrics.metrics['test_operation_latency']) == 1
        assert metrics.metrics['test_operation_latency'][0]['value'] >= 10  # At least 10ms
        
        # Test failing call
        with pytest.raises(RuntimeError):
            timed_function(-1)
        
        assert metrics.counters['test_operation_error'] == 1
        assert len(metrics.metrics['test_operation_latency']) == 2  # Still recorded


class TestGlobalInstances:
    """Test the global instance getters."""
    
    def test_get_error_handler(self):
        """Test getting global error handler."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2  # Should be same instance
        assert isinstance(handler1, VLMErrorHandler)
    
    def test_get_metrics(self):
        """Test getting global metrics."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        assert metrics1 is metrics2  # Should be same instance
        assert isinstance(metrics1, VLMMetrics)
    
    def test_get_health_monitor(self):
        """Test getting global health monitor."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        assert monitor1 is monitor2  # Should be same instance
        assert isinstance(monitor1, HealthMonitor)


class TestDefaultHealthChecks:
    """Test the default health check functions."""
    
    def test_ollama_health_check(self):
        """Test Ollama availability check."""
        from autotasktracker.core.error_handler import _check_ollama_available
        
        # Mock successful response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            assert _check_ollama_available() is True
            mock_get.assert_called_with('http://localhost:11434/api/tags', timeout=5)
        
        # Mock failed response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            assert _check_ollama_available() is False
        
        # Mock connection error
        import requests
        with patch('requests.get', side_effect=requests.RequestException("Connection failed")):
            assert _check_ollama_available() is False
    
    def test_database_health_check(self):
        """Test database availability check."""
        from autotasktracker.core.error_handler import _check_database_available
        
        # Mock successful connection
        with patch('autotasktracker.core.database.DatabaseManager') as mock_db:
            mock_instance = Mock()
            mock_instance.test_connection.return_value = True
            mock_db.return_value = mock_instance
            
            assert _check_database_available() is True
        
        # Mock failed connection
        with patch('autotasktracker.core.database.DatabaseManager') as mock_db:
            mock_instance = Mock()
            mock_instance.test_connection.return_value = False
            mock_db.return_value = mock_instance
            
            assert _check_database_available() is False
    
    def test_memory_health_check(self):
        """Test memory usage check."""
        from autotasktracker.core.error_handler import _check_memory_usage
        
        # Mock normal memory usage
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 60.0
            assert _check_memory_usage() is True
        
        # Mock high memory usage
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 95.0
            assert _check_memory_usage() is False
        
        # Test when psutil not available
        with patch.dict('sys.modules', {'psutil': None}):
            # Force ImportError
            with patch('builtins.__import__', side_effect=ImportError("No module named 'psutil'")):
                assert _check_memory_usage() is True  # Should return True if can't check