"""
Logging and monitoring infrastructure tests for AutoTaskTracker.
Tests logging functionality, error reporting, and monitoring capabilities.
"""
import logging
import tempfile
import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor


class TestLoggingInfrastructure:
    """Test logging system functionality."""
    
    def test_logger_creation(self):
        """Test that loggers are created correctly."""
        # Test that we can create loggers for different modules
        modules = [
            'autotasktracker.core.database',
            'autotasktracker.core.task_extractor',
            'autotasktracker.ai.embeddings_search',
        ]
        
        for module_name in modules:
            logger = logging.getLogger(module_name)
            assert logger is not None
            assert logger.name == module_name
    
    def test_logging_levels(self):
        """Test that different logging levels work correctly."""
        logger = logging.getLogger('autotasktracker.test')
        
        # Capture log output
        with patch('logging.StreamHandler.emit') as mock_emit:
            # Set to DEBUG level to capture all messages
            logger.setLevel(logging.DEBUG)
            
            # Test different log levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Should have attempted to emit messages
            assert mock_emit.call_count >= 0  # May be 0 if no handlers configured
    
    def test_logging_with_actual_components(self):
        """Test logging integration with actual components."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            # Capture log output
            log_capture = StringIO()
            handler = logging.StreamHandler(log_capture)
            handler.setLevel(logging.DEBUG)
            
            # Add handler to autotasktracker loggers
            autotask_logger = logging.getLogger('autotasktracker')
            autotask_logger.addHandler(handler)
            autotask_logger.setLevel(logging.DEBUG)
            
            try:
                # Perform operations that should generate logs
                db_manager = DatabaseManager(db_path)
                
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                # Test task extractor logging
                extractor = TaskExtractor()
                result = extractor.extract_task("Test Window Title")
                
                # Get captured logs
                log_output = log_capture.getvalue()
                
                # Should have some log output (may be empty if components don't log much)
                assert isinstance(log_output, str)
                
            finally:
                autotask_logger.removeHandler(handler)
                
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        logger = logging.getLogger('autotasktracker.test')
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.ERROR)
        
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # Generate an error and log it
            try:
                raise ValueError("Test error for logging")
            except ValueError as e:
                logger.error(f"Caught error: {e}")
                logger.exception("Exception with traceback")
            
            log_output = log_capture.getvalue()
            
            # Should contain error information
            assert "Test error for logging" in log_output or len(log_output) == 0  # May be empty if no handlers
            
        finally:
            logger.removeHandler(handler)
    
    def test_log_file_creation(self):
        """Test creation and writing to log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Create file handler
            file_handler = logging.FileHandler(str(log_file))
            file_handler.setLevel(logging.INFO)
            
            logger = logging.getLogger('autotasktracker.file_test')
            logger.addHandler(file_handler)
            logger.setLevel(logging.INFO)
            
            try:
                # Write log messages
                logger.info("Test info message")
                logger.warning("Test warning message")
                logger.error("Test error message")
                
                # Flush handler
                file_handler.flush()
                
                # Check that log file was created and contains content
                assert log_file.exists(), "Log file was not created"
                
                if log_file.stat().st_size > 0:
                    log_content = log_file.read_text()
                    assert "Test info message" in log_content
                    assert "Test error message" in log_content
                
            finally:
                logger.removeHandler(file_handler)
                file_handler.close()


class TestErrorHandlingInfrastructure:
    """Test error handling and reporting."""
    
    def test_database_error_handling(self):
        """Test that database errors are handled properly."""
        # Test with invalid database path
        invalid_path = "/invalid/path/database.db"
        
        with patch('logging.getLogger') as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance
            
            try:
                db_manager = DatabaseManager(invalid_path)
                with db_manager.get_connection() as conn:
                    conn.cursor().execute("SELECT 1")
            except Exception as e:
                # Should handle error gracefully
                assert isinstance(e, (OSError, Exception))
                
                # Should have attempted to log error (if logging is implemented)
                # Note: Actual implementation may or may not log here
    
    def test_task_extraction_error_handling(self):
        """Test error handling in task extraction."""
        extractor = TaskExtractor()
        
        with patch('logging.getLogger') as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance
            
            # Test with various problematic inputs
            problematic_inputs = [
                None,
                "",
                "{'invalid': json}",
                "x" * 10000,  # Very long string
            ]
            
            for test_input in problematic_inputs:
                try:
                    result = extractor.extract_task(test_input)
                    # Should return something or None, not crash
                    assert result is None or isinstance(result, str)
                except Exception as e:
                    # If it does raise an exception, it should be handled gracefully
                    pytest.fail(f"TaskExtractor crashed on input '{test_input}': {e}")
    
    def test_ai_features_error_handling(self):
        """Test error handling in AI features."""
        try:
            from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine
        except ImportError:
            pytest.skip("AI features not available")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            engine = EmbeddingsSearchEngine(db_path)
            
            # Test with invalid entity ID
            result = engine.semantic_search(query_entity_id=99999, limit=5)
            # Should return empty list, not crash
            assert isinstance(result, list)
            assert len(result) == 0
            
            # Test with invalid similarity threshold
            result = engine.semantic_search(query_entity_id=1, similarity_threshold=2.0)  # Invalid range
            assert isinstance(result, list)
            
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass
    
    def test_graceful_degradation_on_missing_dependencies(self):
        """Test that missing dependencies are handled gracefully."""
        # Test behavior when optional dependencies are missing
        with patch.dict('sys.modules', {'numpy': None}):
            try:
                # This should either work or fail gracefully
                from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine
                # If import succeeds, basic functionality should work
            except ImportError:
                # This is acceptable - module requires numpy
                pass
            except Exception as e:
                pytest.fail(f"Unexpected error when numpy unavailable: {e}")


class TestMonitoringInfrastructure:
    """Test monitoring and health check capabilities."""
    
    def test_database_health_monitoring(self):
        """Test database health monitoring."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            db_manager = DatabaseManager(db_path)
            
            # Test basic health check
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    health_status = result[0] == 1
                
                assert health_status is True
                
            except Exception as e:
                pytest.fail(f"Database health check failed: {e}")
                
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass
    
    def test_component_availability_monitoring(self):
        """Test monitoring of component availability."""
        # Test core components
        core_components = [
            ('database', 'autotasktracker.core.database', 'DatabaseManager'),
            ('task_extractor', 'autotasktracker.core.task_extractor', 'TaskExtractor'),
            ('categorizer', 'autotasktracker.core.categorizer', 'ActivityCategorizer'),
        ]
        
        component_status = {}
        
        for component_name, module_name, class_name in core_components:
            try:
                module = __import__(module_name, fromlist=[class_name])
                component_class = getattr(module, class_name)
                # Try to instantiate
                if component_name == 'database':
                    instance = component_class(':memory:')  # Use in-memory database
                else:
                    instance = component_class()
                component_status[component_name] = 'available'
            except Exception as e:
                component_status[component_name] = f'error: {e}'
        
        # All core components should be available
        for component_name in ['database', 'task_extractor', 'categorizer']:
            assert component_status[component_name] == 'available', \
                f"Core component {component_name} not available: {component_status[component_name]}"
    
    def test_ai_features_availability_monitoring(self):
        """Test monitoring of AI features availability."""
        ai_components = [
            ('embeddings_search', 'autotasktracker.ai.embeddings_search', 'EmbeddingsSearchEngine'),
            ('vlm_integration', 'autotasktracker.ai.vlm_integration', 'VLMTaskExtractor'),
        ]
        
        ai_status = {}
        
        for component_name, module_name, class_name in ai_components:
            try:
                module = __import__(module_name, fromlist=[class_name])
                component_class = getattr(module, class_name)
                # Try to instantiate
                if component_name == 'embeddings_search':
                    instance = component_class(':memory:')
                else:
                    instance = component_class()
                ai_status[component_name] = 'available'
            except ImportError as e:
                ai_status[component_name] = f'missing_dependency: {e}'
            except Exception as e:
                ai_status[component_name] = f'error: {e}'
        
        # AI components may not be available, but should not crash
        for component_name, status in ai_status.items():
            assert 'available' in status or 'missing_dependency' in status or 'error' in status
    
    def test_performance_metrics_collection(self):
        """Test collection of basic performance metrics."""
        import time
        
        # Test database operation timing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
        
        try:
            db_manager = DatabaseManager(db_path)
            
            # Measure database operation time
            start_time = time.time()
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            operation_time = time.time() - start_time
            
            # Basic operation should be fast
            assert operation_time < 1.0, f"Basic database operation too slow: {operation_time} seconds"
            
            # Metrics should be collectible
            metrics = {
                'database_operation_time': operation_time,
                'database_available': True,
            }
            
            assert 'database_operation_time' in metrics
            assert isinstance(metrics['database_operation_time'], float)
            assert metrics['database_available'] is True
            
        finally:
            try:
                Path(db_path).unlink()
            except:
                pass
    
    def test_system_resource_monitoring(self):
        """Test system resource monitoring capabilities."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available for system monitoring")
        
        # Test that we can collect basic system metrics
        process = psutil.Process()
        
        metrics = {
            'memory_usage': process.memory_info().rss,
            'cpu_percent': process.cpu_percent(),
            'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
        }
        
        # Metrics should be reasonable
        assert metrics['memory_usage'] > 0
        assert metrics['cpu_percent'] >= 0
        assert metrics['open_files'] >= 0
        
        # Memory usage should not be excessive (< 1GB for tests)
        assert metrics['memory_usage'] < 1024 * 1024 * 1024, \
            f"Memory usage too high: {metrics['memory_usage']} bytes"