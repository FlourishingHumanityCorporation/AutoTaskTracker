#!/usr/bin/env python3
"""
Async Effectiveness Validator - Enhanced mutation testing with async processing.

This script demonstrates how to use AsyncMutationProcessor with EffectivenessValidator
for large-scale mutation testing with improved performance.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.health.testing.mutation_effectiveness import EffectivenessValidator
from tests.health.testing.async_mutation_processor import (
    AsyncMutationProcessor, 
    AsyncProcessingConfig,
    ProcessingProgress
)
from tests.health.testing.config import EffectivenessConfig

logger = logging.getLogger(__name__)


@dataclass
class AsyncValidationResult:
    """Result of async validation with performance metrics."""
    test_file: Path
    effectiveness_report: Dict[str, Any]
    processing_time: float
    error: Optional[str] = None


class AsyncEffectivenessValidator:
    """Enhanced EffectivenessValidator with async processing capabilities."""
    
    def __init__(self, project_root: Path, 
                 effectiveness_config: Optional[EffectivenessConfig] = None,
                 async_config: Optional[AsyncProcessingConfig] = None):
        self.project_root = project_root
        self.effectiveness_config = effectiveness_config or EffectivenessConfig()
        self.async_config = async_config or AsyncProcessingConfig(
            max_concurrent_files=4,
            enable_streaming=True,
            chunk_size=10,
            max_memory_usage_mb=512
        )
        
        # Initialize standard validator
        self.validator = EffectivenessValidator(project_root)
        
        # Initialize async processor
        self.async_processor = AsyncMutationProcessor(
            project_root, 
            async_config=self.async_config
        )
    
    async def validate_files_async(self, test_files: List[Path], 
                                 progress_callback: Optional[callable] = None) -> List[AsyncValidationResult]:
        """Validate multiple test files using async processing.
        
        Args:
            test_files: List of test files to validate
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of validation results with performance metrics
        """
        results = []
        
        logger.info(f"Starting async validation of {len(test_files)} test files")
        start_time = time.time()
        
        # Process files in chunks for better memory management
        file_chunks = self._chunk_files(test_files, self.async_config.chunk_size)
        
        for chunk_idx, chunk in enumerate(file_chunks):
            logger.info(f"Processing chunk {chunk_idx + 1}/{len(file_chunks)} ({len(chunk)} files)")
            
            chunk_results = await self._process_chunk_async(chunk, progress_callback)
            results.extend(chunk_results)
            
            # Optional: memory cleanup between chunks
            if chunk_idx < len(file_chunks) - 1:
                await self.async_processor._cleanup_memory()
        
        total_time = time.time() - start_time
        logger.info(f"Async validation completed in {total_time:.2f}s")
        
        return results
    
    async def _process_chunk_async(self, test_files: List[Path], 
                                 progress_callback: Optional[callable] = None) -> List[AsyncValidationResult]:
        """Process a chunk of test files asynchronously."""
        tasks = []
        
        for test_file in test_files:
            task = asyncio.create_task(
                self._validate_single_file_async(test_file),
                name=f"validate_{test_file.name}"
            )
            tasks.append(task)
        
        # Wait for all tasks with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                results.append(result)
                
                if progress_callback:
                    progress = (i + 1) / len(tasks) * 100
                    progress_callback(progress, result.test_file)
                    
            except Exception as e:
                logger.error(f"Task failed: {e}")
                # Create error result
                error_result = AsyncValidationResult(
                    test_file=test_files[i] if i < len(test_files) else Path("unknown"),
                    effectiveness_report={'error': str(e)},
                    processing_time=0.0,
                    error=str(e)
                )
                results.append(error_result)
        
        return results
    
    async def _validate_single_file_async(self, test_file: Path) -> AsyncValidationResult:
        """Validate a single test file asynchronously."""
        start_time = time.time()
        
        try:
            # Run validation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            effectiveness_report = await loop.run_in_executor(
                None,
                self.validator.validate_test_effectiveness,
                test_file
            )
            
            processing_time = time.time() - start_time
            
            return AsyncValidationResult(
                test_file=test_file,
                effectiveness_report=effectiveness_report,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Validation failed for {test_file}: {e}")
            
            return AsyncValidationResult(
                test_file=test_file,
                effectiveness_report={'error': str(e)},
                processing_time=processing_time,
                error=str(e)
            )
    
    def _chunk_files(self, files: List[Path], chunk_size: int) -> List[List[Path]]:
        """Split files into chunks for processing."""
        chunks = []
        for i in range(0, len(files), chunk_size):
            chunks.append(files[i:i + chunk_size])
        return chunks
    
    def generate_performance_report(self, results: List[AsyncValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not results:
            return {'error': 'No results to analyze'}
        
        successful_results = [r for r in results if r.error is None]
        failed_results = [r for r in results if r.error is not None]
        
        processing_times = [r.processing_time for r in successful_results]
        effectiveness_scores = [
            r.effectiveness_report.get('overall_effectiveness', 0.0) 
            for r in successful_results
        ]
        
        return {
            'summary': {
                'total_files': len(results),
                'successful': len(successful_results),
                'failed': len(failed_results),
                'success_rate': len(successful_results) / len(results) * 100
            },
            'performance': {
                'total_processing_time': sum(processing_times),
                'average_processing_time': sum(processing_times) / len(processing_times) if processing_times else 0,
                'min_processing_time': min(processing_times) if processing_times else 0,
                'max_processing_time': max(processing_times) if processing_times else 0
            },
            'effectiveness': {
                'average_effectiveness': sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0,
                'min_effectiveness': min(effectiveness_scores) if effectiveness_scores else 0,
                'max_effectiveness': max(effectiveness_scores) if effectiveness_scores else 0,
                'files_above_70_percent': len([s for s in effectiveness_scores if s >= 70])
            },
            'errors': [r.error for r in failed_results],
            'async_config': {
                'max_concurrent_files': self.async_config.max_concurrent_files,
                'chunk_size': self.async_config.chunk_size,
                'max_memory_usage_mb': self.async_config.max_memory_usage_mb
            }
        }


async def demo_async_validation():
    """Demonstrate async validation capabilities."""
    project_root = Path(__file__).parent.parent.parent
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Find some test files for demonstration
    test_files = list(project_root.glob("tests/**/test_*.py"))[:5]  # Limit for demo
    
    if not test_files:
        logger.warning("No test files found for demonstration")
        return
    
    logger.info(f"Found {len(test_files)} test files for async validation demo")
    
    # Create async validator with optimized config
    async_config = AsyncProcessingConfig(
        max_concurrent_files=2,  # Conservative for demo
        enable_streaming=True,
        chunk_size=3,
        max_memory_usage_mb=256
    )
    
    validator = AsyncEffectivenessValidator(
        project_root=project_root,
        async_config=async_config
    )
    
    # Progress callback
    def progress_callback(percent: float, current_file: Path):
        logger.info(f"Progress: {percent:.1f}% - Processing {current_file.name}")
    
    # Run async validation
    start_time = time.time()
    results = await validator.validate_files_async(test_files, progress_callback)
    total_time = time.time() - start_time
    
    # Generate and display report
    report = validator.generate_performance_report(results)
    
    print("\n" + "="*60)
    print("ASYNC EFFECTIVENESS VALIDATION REPORT")
    print("="*60)
    
    print(f"\nSummary:")
    print(f"  Total files: {report['summary']['total_files']}")
    print(f"  Successful: {report['summary']['successful']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  Success rate: {report['summary']['success_rate']:.1f}%")
    
    print(f"\nPerformance:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Average per file: {report['performance']['average_processing_time']:.2f}s")
    print(f"  Min/Max: {report['performance']['min_processing_time']:.2f}s / {report['performance']['max_processing_time']:.2f}s")
    
    print(f"\nEffectiveness:")
    print(f"  Average effectiveness: {report['effectiveness']['average_effectiveness']:.1f}%")
    print(f"  Files above 70%: {report['effectiveness']['files_above_70_percent']}")
    
    if report['errors']:
        print(f"\nErrors:")
        for error in report['errors'][:3]:  # Show first 3 errors
            print(f"  - {error}")
    
    print(f"\nAsync Configuration:")
    print(f"  Max concurrent files: {report['async_config']['max_concurrent_files']}")
    print(f"  Chunk size: {report['async_config']['chunk_size']}")
    print(f"  Memory limit: {report['async_config']['max_memory_usage_mb']}MB")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demo_async_validation())