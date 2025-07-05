"""Async mutation processing for large-scale codebases.

This module provides asynchronous processing capabilities for mutation testing
to handle large codebases efficiently without blocking.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, AsyncGenerator
import multiprocessing as mp

from .mutation_generator import MutationGenerator
from .mutation_executor import MutationExecutor
from .mutation_analyzer import MutationAnalyzer, TestEffectivenessReport
from .config import EffectivenessConfig
from .constants import MutationTestingLimits

logger = logging.getLogger(__name__)


@dataclass
class AsyncProcessingConfig:
    """Configuration for async mutation processing."""
    
    # Concurrency settings
    max_concurrent_files: int = 10
    max_concurrent_mutations: int = 5
    chunk_size: int = 20
    
    # Performance settings
    enable_streaming: bool = True
    progress_callback: Optional[Callable[[Dict], None]] = None
    
    # Memory management
    max_memory_usage_mb: int = 500
    cleanup_interval: int = 100  # Cleanup every N processed files


@dataclass
class ProcessingProgress:
    """Progress tracking for async processing."""
    
    total_files: int = 0
    processed_files: int = 0
    total_mutations: int = 0
    processed_mutations: int = 0
    start_time: float = 0.0
    current_phase: str = "initializing"
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.start_time == 0.0:
            self.start_time = time.time()
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def files_per_second(self) -> float:
        """Get processing rate in files per second."""
        if self.elapsed_time == 0:
            return 0.0
        return self.processed_files / self.elapsed_time
    
    @property
    def eta_seconds(self) -> float:
        """Estimate time to completion in seconds."""
        if self.files_per_second == 0:
            return float('inf')
        remaining_files = self.total_files - self.processed_files
        return remaining_files / self.files_per_second
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for progress callbacks."""
        return {
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'total_mutations': self.total_mutations,
            'processed_mutations': self.processed_mutations,
            'elapsed_time': self.elapsed_time,
            'files_per_second': self.files_per_second,
            'eta_seconds': self.eta_seconds,
            'current_phase': self.current_phase,
            'errors': self.errors.copy()
        }


class AsyncMutationProcessor:
    """Async processor for mutation testing at scale."""
    
    def __init__(self, 
                 project_root: Path,
                 config: Optional[EffectivenessConfig] = None,
                 async_config: Optional[AsyncProcessingConfig] = None):
        self.project_root = project_root
        self.config = config or EffectivenessConfig()
        self.async_config = async_config or AsyncProcessingConfig()
        
        # Initialize components
        self.generator = MutationGenerator()
        self.executor = MutationExecutor(project_root, self.config)
        self.analyzer = MutationAnalyzer()
        
        # Progress tracking
        self.progress = ProcessingProgress()
        
        # Resource management
        self._semaphore_files = asyncio.Semaphore(self.async_config.max_concurrent_files)
        self._semaphore_mutations = asyncio.Semaphore(self.async_config.max_concurrent_mutations)
        self._executor_pool = ThreadPoolExecutor(max_workers=mp.cpu_count())
    
    async def process_files_async(self, 
                                  test_files: List[Path],
                                  source_files: Optional[List[Path]] = None) -> AsyncGenerator[TestEffectivenessReport, None]:
        """Process multiple test files asynchronously.
        
        Args:
            test_files: List of test files to analyze
            source_files: Optional list of corresponding source files
            
        Yields:
            TestEffectivenessReport for each processed file
        """
        self.progress.total_files = len(test_files)
        self.progress.current_phase = "processing_files"
        
        logger.info(f"Starting async processing of {len(test_files)} test files")
        
        if self.async_config.enable_streaming:
            # Process files in chunks for memory efficiency
            for chunk in self._chunk_files(test_files, self.async_config.chunk_size):
                async for report in self._process_file_chunk(chunk):
                    yield report
                    
                    # Memory cleanup
                    if self.progress.processed_files % self.async_config.cleanup_interval == 0:
                        await self._cleanup_memory()
        else:
            # Process all files and return results at once
            tasks = [self._process_single_file(test_file) for test_file in test_files]
            for completed_task in asyncio.as_completed(tasks):
                report = await completed_task
                if report:
                    yield report
    
    async def _process_file_chunk(self, chunk: List[Path]) -> AsyncGenerator[TestEffectivenessReport, None]:
        """Process a chunk of files concurrently."""
        tasks = [self._process_single_file(test_file) for test_file in chunk]
        
        for completed_task in asyncio.as_completed(tasks):
            try:
                report = await completed_task
                if report:
                    yield report
            except Exception as e:
                logger.error(f"Error processing file chunk: {e}")
                self.progress.errors.append(str(e))
    
    async def _process_single_file(self, test_file: Path) -> Optional[TestEffectivenessReport]:
        """Process a single test file with async coordination."""
        async with self._semaphore_files:
            try:
                self.progress.current_phase = f"processing_{test_file.name}"
                
                # Find source file
                source_file = await self._find_source_file_async(test_file)
                if not source_file:
                    logger.warning(f"No source file found for {test_file}")
                    self._update_progress(files_delta=1)
                    return None
                
                # Generate mutations
                mutations = await self._generate_mutations_async(source_file)
                if not mutations:
                    logger.info(f"No mutations generated for {source_file}")
                    self._update_progress(files_delta=1)
                    return self.analyzer.analyze_results(test_file, source_file, [])
                
                self.progress.total_mutations += len(mutations)
                
                # Execute mutations asynchronously
                results = await self._execute_mutations_async(test_file, source_file, mutations)
                
                # Analyze results
                report = self.analyzer.analyze_results(test_file, source_file, results)
                
                self._update_progress(files_delta=1, mutations_delta=len(mutations))
                
                # Progress callback
                if self.async_config.progress_callback:
                    self.async_config.progress_callback(self.progress.to_dict())
                
                return report
                
            except Exception as e:
                logger.error(f"Error processing {test_file}: {e}")
                self.progress.errors.append(f"{test_file}: {e}")
                self._update_progress(files_delta=1)
                return None
    
    async def _generate_mutations_async(self, source_file: Path) -> List[Dict]:
        """Generate mutations asynchronously."""
        loop = asyncio.get_event_loop()
        
        # Run mutation generation in thread pool to avoid blocking
        return await loop.run_in_executor(
            self._executor_pool,
            self.generator.generate_mutations,
            source_file
        )
    
    async def _execute_mutations_async(self, 
                                       test_file: Path, 
                                       source_file: Path, 
                                       mutations: List[Dict]) -> List[Dict]:
        """Execute mutations asynchronously with concurrency control."""
        async def execute_single_mutation(mutation: Dict) -> Optional[Dict]:
            async with self._semaphore_mutations:
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        self._executor_pool,
                        self.executor.execute_mutation,
                        test_file,
                        source_file,
                        mutation
                    )
                    self._update_progress(mutations_delta=1)
                    return result
                except Exception as e:
                    logger.error(f"Error executing mutation {mutation.get('type', 'unknown')}: {e}")
                    self.progress.errors.append(f"Mutation {mutation.get('type', 'unknown')}: {e}")
                    self._update_progress(mutations_delta=1)
                    return None
        
        # Execute mutations concurrently
        tasks = [execute_single_mutation(mutation) for mutation in mutations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        return [result for result in results if result is not None and not isinstance(result, Exception)]
    
    async def _find_source_file_async(self, test_file: Path) -> Optional[Path]:
        """Find corresponding source file asynchronously."""
        loop = asyncio.get_event_loop()
        
        # This could be enhanced with async file system operations
        return await loop.run_in_executor(
            self._executor_pool,
            self._find_source_file_sync,
            test_file
        )
    
    def _find_source_file_sync(self, test_file: Path) -> Optional[Path]:
        """Synchronous source file finding (placeholder for now)."""
        # This is a simplified version - could use the RefactoredMutationTester logic
        test_name = test_file.stem
        if test_name.startswith('test_'):
            source_name = test_name[5:] + '.py'
        else:
            source_name = test_name + '.py'
        
        # Search in common locations
        search_paths = [
            self.project_root / "autotasktracker" / source_name,
            self.project_root / "autotasktracker" / "core" / source_name,
            self.project_root / "autotasktracker" / "ai" / source_name,
            self.project_root / "autotasktracker" / "dashboards" / source_name,
        ]
        
        for candidate in search_paths:
            if candidate.exists():
                return candidate
        
        return None
    
    def _chunk_files(self, files: List[Path], chunk_size: int) -> List[List[Path]]:
        """Split files into chunks for processing."""
        return [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]
    
    def _update_progress(self, files_delta: int = 0, mutations_delta: int = 0):
        """Update processing progress."""
        self.progress.processed_files += files_delta
        self.progress.processed_mutations += mutations_delta
    
    async def _cleanup_memory(self):
        """Perform memory cleanup operations."""
        # Force garbage collection
        import gc
        gc.collect()
        
        # Log memory usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.debug(f"Memory usage: {memory_mb:.1f} MB")
            
            if memory_mb > self.async_config.max_memory_usage_mb:
                logger.warning(f"High memory usage: {memory_mb:.1f} MB")
        except ImportError:
            pass  # psutil not available
    
    async def get_progress(self) -> Dict[str, Any]:
        """Get current processing progress."""
        return self.progress.to_dict()
    
    async def shutdown(self):
        """Shutdown the async processor and cleanup resources."""
        logger.info("Shutting down async mutation processor")
        self._executor_pool.shutdown(wait=True)
        self.progress.current_phase = "completed"


class AsyncMutationBatchProcessor:
    """Batch processor for processing entire codebases asynchronously."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.processors: List[AsyncMutationProcessor] = []
    
    async def process_codebase(self, 
                               test_pattern: str = "test_*.py",
                               max_processors: int = 4) -> AsyncGenerator[TestEffectivenessReport, None]:
        """Process entire codebase with multiple async processors.
        
        Args:
            test_pattern: Glob pattern for test files
            max_processors: Maximum number of concurrent processors
            
        Yields:
            TestEffectivenessReport for each processed test file
        """
        # Find all test files
        test_files = list(self.project_root.rglob(test_pattern))
        logger.info(f"Found {len(test_files)} test files matching pattern '{test_pattern}'")
        
        if not test_files:
            logger.warning("No test files found")
            return
        
        # Split files across processors
        chunk_size = max(1, len(test_files) // max_processors)
        file_chunks = [test_files[i:i + chunk_size] for i in range(0, len(test_files), chunk_size)]
        
        # Create processors for each chunk
        processors = []
        for i, chunk in enumerate(file_chunks):
            config = AsyncProcessingConfig(
                max_concurrent_files=min(5, len(chunk)),
                max_concurrent_mutations=3
            )
            processor = AsyncMutationProcessor(
                self.project_root,
                async_config=config
            )
            processors.append((processor, chunk))
        
        self.processors = [p[0] for p in processors]
        
        try:
            # Process all chunks concurrently
            async def process_chunk(processor_chunk_pair):
                processor, chunk = processor_chunk_pair
                async for report in processor.process_files_async(chunk):
                    yield report
            
            # Create async generators for each processor
            generators = [process_chunk(pc) for pc in processors]
            
            # Merge results from all generators
            pending = {asyncio.create_task(gen.__anext__()): gen for gen in generators}
            
            while pending:
                done, pending_futures = await asyncio.wait(
                    pending.keys(), 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    try:
                        report = await task
                        yield report
                        
                        # Schedule next item from the same generator
                        generator = pending.pop(task)
                        next_task = asyncio.create_task(generator.__anext__())
                        pending[next_task] = generator
                        
                    except StopAsyncIteration:
                        # Generator exhausted
                        pending.pop(task, None)
                    except Exception as e:
                        logger.error(f"Error in batch processing: {e}")
                        pending.pop(task, None)
        
        finally:
            # Cleanup all processors
            await self._shutdown_processors()
    
    async def _shutdown_processors(self):
        """Shutdown all processors."""
        for processor in self.processors:
            await processor.shutdown()
        self.processors.clear()
    
    async def get_combined_progress(self) -> Dict[str, Any]:
        """Get combined progress from all processors."""
        if not self.processors:
            return {'total_files': 0, 'processed_files': 0, 'errors': []}
        
        # Aggregate progress from all processors
        total_files = sum(p.progress.total_files for p in self.processors)
        processed_files = sum(p.progress.processed_files for p in self.processors)
        total_mutations = sum(p.progress.total_mutations for p in self.processors)
        processed_mutations = sum(p.progress.processed_mutations for p in self.processors)
        all_errors = []
        for p in self.processors:
            all_errors.extend(p.progress.errors)
        
        return {
            'total_files': total_files,
            'processed_files': processed_files,
            'total_mutations': total_mutations,
            'processed_mutations': processed_mutations,
            'progress_percentage': (processed_files / total_files * 100) if total_files > 0 else 0,
            'errors': all_errors
        }