"""Refactored mutation testing system with separated concerns.

This module provides a clean, focused interface for mutation testing by
composing specialized modules for generation, execution, and analysis.
"""

import logging
import re
from pathlib import Path
from typing import Optional, List

from .config import EffectivenessConfig
from .mutation_generator import MutationGenerator
from .mutation_executor import MutationExecutor
from .mutation_analyzer import MutationAnalyzer, TestEffectivenessReport

logger = logging.getLogger(__name__)


class RefactoredMutationTester:
    """Clean, focused mutation tester using composition pattern.
    
    This class orchestrates mutation testing by delegating to specialized
    components, making it easier to maintain and test.
    """
    
    def __init__(self, project_root: Path, config: Optional[EffectivenessConfig] = None):
        self.project_root = project_root
        self.config = config or EffectivenessConfig()
        
        # Compose with specialized components
        self.generator = MutationGenerator(
            max_mutations_per_file=self.config.mutation.max_mutations_per_file
        )
        self.executor = MutationExecutor(project_root, self.config)
        self.analyzer = MutationAnalyzer()
    
    def analyze_test_effectiveness(self, test_file: Path) -> TestEffectivenessReport:
        """Analyze test effectiveness using mutation testing.
        
        Args:
            test_file: Path to the test file to analyze
            
        Returns:
            TestEffectivenessReport with effectiveness metrics and recommendations
        """
        logger.info(f"Starting mutation testing for {test_file}")
        
        # Find corresponding source file
        source_file = self._find_source_file(test_file)
        if not source_file:
            return self.analyzer.analyze_results(test_file, None, [])
        
        # Generate mutations
        mutations = self.generator.generate_mutations(source_file)
        if not mutations:
            return self.analyzer.analyze_results(
                test_file, source_file, [],
            )
        
        logger.info(f"Generated {len(mutations)} mutations for {source_file}")
        
        # Execute mutations
        results = []
        for i, mutation in enumerate(mutations, 1):
            logger.debug(f"Testing mutation {i}/{len(mutations)}: {mutation['type']}")
            result = self.executor.execute_mutation(test_file, source_file, mutation)
            if result:
                results.append(result)
        
        logger.info(f"Executed {len(results)}/{len(mutations)} mutations successfully")
        
        # Analyze results
        return self.analyzer.analyze_results(test_file, source_file, results)
    
    def _find_source_file(self, test_file: Path) -> Optional[Path]:
        """Find the source file corresponding to a test file.
        
        Args:
            test_file: Path to the test file
            
        Returns:
            Path to corresponding source file, or None if not found
        """
        # Common test file naming patterns
        test_name = test_file.stem
        
        # Remove test_ prefix
        if test_name.startswith('test_'):
            source_name = test_name[5:]  # Remove 'test_'
        else:
            source_name = test_name
        
        # Look for source file in common locations
        search_paths = [
            # Same directory as test
            test_file.parent / f"{source_name}.py",
            # Parent directory
            test_file.parent.parent / f"{source_name}.py",
            # autotasktracker directory
            self.project_root / "autotasktracker" / f"{source_name}.py",
            # Core module
            self.project_root / "autotasktracker" / "core" / f"{source_name}.py",
            # AI module
            self.project_root / "autotasktracker" / "ai" / f"{source_name}.py",
            # Scripts directory
            self.project_root / "scripts" / f"{source_name}.py",
        ]
        
        for candidate in search_paths:
            if candidate.exists() and candidate.is_file():
                logger.debug(f"Found source file: {candidate}")
                return candidate
        
        # Try to find source file by analyzing test imports
        source_from_imports = self._find_source_from_imports(test_file)
        if source_from_imports:
            return source_from_imports
        
        logger.warning(f"Could not find source file for test {test_file}")
        return None
    
    def _find_source_from_imports(self, test_file: Path) -> Optional[Path]:
        """Find source file by analyzing imports in the test file."""
        try:
            content = test_file.read_text(encoding='utf-8')
            
            # Look for imports like: from autotasktracker.core.database import DatabaseManager
            import_pattern = r'from\s+(autotasktracker\.[.\w]+)\s+import'
            matches = re.findall(import_pattern, content)
            
            for module_path in matches:
                # Convert module path to file path
                parts = module_path.split('.')
                file_path = self.project_root / Path(*parts[1:]).with_suffix('.py')
                
                if file_path.exists():
                    logger.debug(f"Found source file from imports: {file_path}")
                    return file_path
            
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Could not analyze imports in {test_file}: {e}")
        
        return None


# Backwards compatibility - alias to the original class name
SimpleMutationTester = RefactoredMutationTester