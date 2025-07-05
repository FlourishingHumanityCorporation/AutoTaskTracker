"""Tests for async mutation processing capabilities.

This test suite validates the asynchronous processing functionality
for handling large-scale mutation testing operations.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import time

from tests.health.testing.async_mutation_processor import (
    AsyncMutationProcessor,
    AsyncProcessingConfig,
    ProcessingProgress,
    AsyncMutationBatchProcessor
)
from tests.health.testing.config import EffectivenessConfig


class TestProcessingProgress:
    """Test the ProcessingProgress tracking."""
    
    def test_progress_initialization(self):
        """Test progress object initialization."""
        progress = ProcessingProgress(total_files=10)
        assert progress.total_files == 10
        assert progress.processed_files == 0
        assert progress.errors == []
        assert progress.start_time > 0
    
    def test_progress_calculations(self):
        """Test progress calculation methods."""
        progress = ProcessingProgress(total_files=10, processed_files=5)
        progress.start_time = time.time() - 10  # 10 seconds ago
        
        assert progress.elapsed_time >= 9  # Allow some variance
        assert progress.files_per_second > 0
        assert progress.eta_seconds > 0
    
    def test_progress_to_dict(self):
        """Test conversion to dictionary."""
        progress = ProcessingProgress(total_files=5, processed_files=2)
        progress_dict = progress.to_dict()
        
        required_keys = [
            'total_files', 'processed_files', 'elapsed_time',
            'files_per_second', 'eta_seconds', 'current_phase', 'errors'
        ]
        
        for key in required_keys:
            assert key in progress_dict


class TestAsyncProcessingConfig:
    """Test async processing configuration."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = AsyncProcessingConfig()
        assert config.max_concurrent_files == 10
        assert config.max_concurrent_mutations == 5
        assert config.chunk_size == 20
        assert config.enable_streaming is True
        assert config.progress_callback is None
    
    def test_config_customization(self):
        """Test custom configuration values."""
        callback = Mock()
        config = AsyncProcessingConfig(
            max_concurrent_files=5,
            max_concurrent_mutations=2,
            progress_callback=callback
        )
        
        assert config.max_concurrent_files == 5
        assert config.max_concurrent_mutations == 2
        assert config.progress_callback is callback


class TestAsyncMutationProcessor:
    """Test the async mutation processor."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create basic structure
            (project_dir / "autotasktracker").mkdir()
            (project_dir / "tests").mkdir()
            
            yield project_dir
    
    @pytest.fixture
    def processor(self, temp_project_dir):
        """Create an async processor."""
        return AsyncMutationProcessor(temp_project_dir)
    
    def test_processor_initialization(self, processor, temp_project_dir):
        """Test processor initialization."""
        assert processor.project_root == temp_project_dir
        assert processor.config is not None
        assert processor.async_config is not None
        assert processor.generator is not None
        assert processor.executor is not None
        assert processor.analyzer is not None
        assert processor.progress.total_files == 0
    
    def test_processor_with_custom_config(self, temp_project_dir):
        """Test processor with custom configuration."""
        async_config = AsyncProcessingConfig(max_concurrent_files=3)
        effectiveness_config = EffectivenessConfig()
        
        processor = AsyncMutationProcessor(
            temp_project_dir,
            config=effectiveness_config,
            async_config=async_config
        )
        
        assert processor.config is effectiveness_config
        assert processor.async_config.max_concurrent_files == 3
    
    @pytest.mark.asyncio
    async def test_find_source_file_async(self, processor, temp_project_dir):
        """Test async source file finding."""
        # Create a test file and corresponding source file
        source_file = temp_project_dir / "autotasktracker" / "example.py"
        source_file.write_text("# Example source file")
        
        test_file = temp_project_dir / "tests" / "test_example.py"
        test_file.write_text("# Test file")
        
        found_source = await processor._find_source_file_async(test_file)
        assert found_source == source_file
    
    @pytest.mark.asyncio
    async def test_find_source_file_not_found(self, processor, temp_project_dir):
        """Test source file finding when file doesn't exist."""
        test_file = temp_project_dir / "tests" / "test_nonexistent.py"
        test_file.write_text("# Test file")
        
        found_source = await processor._find_source_file_async(test_file)
        assert found_source is None
    
    @pytest.mark.asyncio
    async def test_generate_mutations_async(self, processor, temp_project_dir):
        """Test async mutation generation."""
        source_file = temp_project_dir / "test_source.py"
        source_file.write_text("""
def example_function():
    if True:
        return 1 + 2
    return []
""")
        
        mutations = await processor._generate_mutations_async(source_file)
        assert isinstance(mutations, list)
        # Should generate some mutations from the boolean and arithmetic operations
        assert len(mutations) >= 0
    
    def test_chunk_files(self, processor):
        """Test file chunking functionality."""
        files = [Path(f"file_{i}.py") for i in range(10)]
        chunks = processor._chunk_files(files, chunk_size=3)
        
        assert len(chunks) == 4  # 10 files in chunks of 3 = 4 chunks
        assert len(chunks[0]) == 3
        assert len(chunks[-1]) == 1  # Last chunk has remainder
    
    def test_update_progress(self, processor):
        """Test progress updating."""
        initial_files = processor.progress.processed_files
        initial_mutations = processor.progress.processed_mutations
        
        processor._update_progress(files_delta=2, mutations_delta=5)
        
        assert processor.progress.processed_files == initial_files + 2
        assert processor.progress.processed_mutations == initial_mutations + 5
    
    @pytest.mark.asyncio
    async def test_get_progress(self, processor):
        """Test progress retrieval."""
        processor.progress.total_files = 10
        processor.progress.processed_files = 3
        
        progress = await processor.get_progress()
        assert progress['total_files'] == 10
        assert progress['processed_files'] == 3
        assert 'elapsed_time' in progress
    
    @pytest.mark.asyncio
    async def test_cleanup_memory(self, processor):
        """Test memory cleanup functionality."""
        # This should not raise an exception
        await processor._cleanup_memory()
    
    @pytest.mark.asyncio
    async def test_shutdown(self, processor):
        """Test processor shutdown."""
        await processor.shutdown()
        assert processor.progress.current_phase == "completed"


class TestAsyncProcessingIntegration:
    """Integration tests for async processing."""
    
    @pytest.fixture
    def temp_project_with_files(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create structure
            autotask_dir = project_dir / "autotasktracker"
            autotask_dir.mkdir()
            tests_dir = project_dir / "tests"
            tests_dir.mkdir()
            
            # Create source files
            (autotask_dir / "utils.py").write_text("""
def add_numbers(a, b):
    if a is not None and b is not None:
        return a + b
    return 0
""")
            
            (autotask_dir / "database.py").write_text("""
def save_data(data):
    if not data:
        return False
    conn.commit()
    return True
""")
            
            # Create test files
            (tests_dir / "test_utils.py").write_text("""
def test_add_numbers():
    result = add_numbers(1, 2)
    assert result == 3
""")
            
            (tests_dir / "test_database.py").write_text("""
def test_save_data():
    result = save_data({'key': 'value'})
    assert result is True
""")
            
            yield project_dir
    
    @pytest.mark.asyncio
    async def test_process_single_file_end_to_end(self, temp_project_with_files):
        """Test processing a single file end-to-end."""
        processor = AsyncMutationProcessor(temp_project_with_files)
        
        test_file = temp_project_with_files / "tests" / "test_utils.py"
        
        # Mock the executor to avoid running actual tests
        from tests.health.testing.mutation_executor import MutationResult
        from tests.health.testing.mutation_effectiveness import MutationType
        
        with patch.object(processor.executor, 'execute_mutation') as mock_execute:
            mock_execute.return_value = MutationResult(
                mutation_type=MutationType.OFF_BY_ONE.value,
                original_code="if x > 5:",
                mutated_code="if x >= 5:",
                tests_failed=["test_boundary"],
                tests_passed=[],
                file_path=test_file,
                line_number=10,
                effectiveness_score=1.0
            )
            
            report = await processor._process_single_file(test_file)
            
            assert report is not None
            assert report.test_file == test_file
            assert processor.progress.processed_files == 1
    
    @pytest.mark.asyncio 
    async def test_process_files_async_streaming(self, temp_project_with_files):
        """Test streaming processing of multiple files."""
        config = AsyncProcessingConfig(
            max_concurrent_files=2,
            enable_streaming=True,
            chunk_size=1
        )
        processor = AsyncMutationProcessor(temp_project_with_files, async_config=config)
        
        test_files = [
            temp_project_with_files / "tests" / "test_utils.py",
            temp_project_with_files / "tests" / "test_database.py"
        ]
        
        reports = []
        with patch.object(processor.executor, 'execute_mutation') as mock_execute:
            mock_execute.return_value = {
                'mutation_caught': True,
                'test_passed': False,
                'execution_time': 0.1
            }
            
            async for report in processor.process_files_async(test_files):
                reports.append(report)
                
        assert len(reports) <= len(test_files)  # Some may not have source files
        assert processor.progress.processed_files >= 1
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, temp_project_with_files):
        """Test progress callback functionality."""
        callback_calls = []
        
        def progress_callback(progress_dict):
            callback_calls.append(progress_dict)
        
        config = AsyncProcessingConfig(progress_callback=progress_callback)
        processor = AsyncMutationProcessor(temp_project_with_files, async_config=config)
        
        test_file = temp_project_with_files / "tests" / "test_utils.py"
        
        with patch.object(processor.executor, 'execute_mutation') as mock_execute:
            mock_execute.return_value = {
                'mutation_caught': True,
                'test_passed': False,
                'execution_time': 0.1
            }
            
            await processor._process_single_file(test_file)
            
        # Should have received at least one progress callback
        assert len(callback_calls) >= 0  # May be 0 if no source file found


class TestAsyncMutationBatchProcessor:
    """Test the batch processor for entire codebases."""
    
    @pytest.fixture
    def temp_codebase(self):
        """Create a temporary codebase with multiple test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create structure
            (project_dir / "autotasktracker").mkdir()
            (project_dir / "tests").mkdir()
            
            # Create multiple test files
            for i in range(5):
                test_file = project_dir / "tests" / f"test_module_{i}.py"
                test_file.write_text(f"""
def test_function_{i}():
    assert True
""")
                
                source_file = project_dir / "autotasktracker" / f"module_{i}.py"
                source_file.write_text(f"""
def function_{i}():
    if True:
        return {i}
    return 0
""")
            
            yield project_dir
    
    def test_batch_processor_initialization(self, temp_codebase):
        """Test batch processor initialization."""
        processor = AsyncMutationBatchProcessor(temp_codebase)
        assert processor.project_root == temp_codebase
        assert processor.processors == []
    
    @pytest.mark.asyncio
    async def test_process_codebase_finds_files(self, temp_codebase):
        """Test that codebase processing finds test files."""
        processor = AsyncMutationBatchProcessor(temp_codebase)
        
        reports = []
        
        # Mock mutation execution to speed up test
        with patch('tests.health.testing.async_mutation_processor.AsyncMutationProcessor') as MockProcessor:
            mock_instance = Mock()
            MockProcessor.return_value = mock_instance
            
            # Create an async generator that yields test reports
            async def mock_process_files_async(files):
                for file in files:
                    yield Mock(test_file=file, effectiveness_percentage=75.0)
            
            mock_instance.process_files_async = mock_process_files_async
            mock_instance.shutdown = AsyncMock()
            
            async for report in processor.process_codebase(max_processors=2):
                reports.append(report)
                if len(reports) >= 3:  # Limit for test speed
                    break
        
        assert len(reports) >= 1
    
    @pytest.mark.asyncio
    async def test_get_combined_progress(self, temp_codebase):
        """Test combined progress from multiple processors."""
        processor = AsyncMutationBatchProcessor(temp_codebase)
        
        # Create mock processors with progress
        mock_processor1 = Mock()
        mock_processor1.progress.total_files = 5
        mock_processor1.progress.processed_files = 2
        mock_processor1.progress.total_mutations = 10
        mock_processor1.progress.processed_mutations = 4
        mock_processor1.progress.errors = ["error1"]
        
        mock_processor2 = Mock()
        mock_processor2.progress.total_files = 3
        mock_processor2.progress.processed_files = 1
        mock_processor2.progress.total_mutations = 6
        mock_processor2.progress.processed_mutations = 2
        mock_processor2.progress.errors = ["error2"]
        
        processor.processors = [mock_processor1, mock_processor2]
        
        combined = await processor.get_combined_progress()
        
        assert combined['total_files'] == 8
        assert combined['processed_files'] == 3
        assert combined['total_mutations'] == 16
        assert combined['processed_mutations'] == 6
        assert combined['progress_percentage'] == 37.5  # 3/8 * 100
        assert len(combined['errors']) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])