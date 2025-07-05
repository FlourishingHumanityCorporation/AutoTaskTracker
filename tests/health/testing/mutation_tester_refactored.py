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
        """Enhanced source file mapping with semantic understanding.
        
        Args:
            test_file: Path to the test file
            
        Returns:
            Path to corresponding source file, or None if not found
        """
        # Extract base name and apply semantic mapping
        test_name = test_file.stem
        source_names = self._get_source_name_candidates(test_name)
        
        # Search with improved path patterns
        for source_name in source_names:
            candidate = self._search_for_source_file(source_name, test_file)
            if candidate:
                logger.debug(f"Mapped {test_file.name} → {candidate.relative_to(self.project_root)}")
                return candidate
        
        # Fallback: try imports analysis
        source_from_imports = self._find_source_from_imports(test_file)
        if source_from_imports:
            return source_from_imports
        
        # Enhanced fallback: directory-based contextual search  
        contextual_result = self._contextual_search(test_file)
        if contextual_result:
            return contextual_result
        
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
    
    def _get_source_name_candidates(self, test_name: str) -> List[str]:
        """Generate semantic source name candidates for enhanced mapping."""
        candidates = []
        
        # Remove test_ prefix
        if test_name.startswith('test_'):
            base_name = test_name[5:]
        else:
            base_name = test_name
        
        # Add direct mapping
        candidates.append(base_name)
        
        # Semantic mappings for common patterns
        semantic_mappings = {
            'notification_system': ['notifications', 'notification_manager'],
            'dashboard_core': ['dashboard', 'base_dashboard', 'core'],
            'comparison_pipelines': ['pipeline_comparison', 'comparison', 'pipelines'],
            'time_tracking_accuracy': ['timetracker', 'time_tracker', 'time_tracking'],
            'parallel_analyzer': ['performance_analyzer', 'analyzer', 'parallel_analysis'],
            'task_board': ['task_board', 'dashboard', 'board'],
            'ai_task_extractor': ['task_extractor', 'ai_extractor', 'extractor'],
            'database_manager': ['database', 'db_manager', 'manager'],
            'vlm_processor': ['vlm', 'processor', 'vision_processor'],
            'embeddings_search': ['embeddings', 'search', 'embedding_generator']
        }
        
        # Add semantic alternatives
        if base_name in semantic_mappings:
            candidates.extend(semantic_mappings[base_name])
        
        # Add common transformations
        if '_' in base_name:
            # Remove underscores: task_board → taskboard
            candidates.append(base_name.replace('_', ''))
            # Take first part: task_board → task
            candidates.append(base_name.split('_')[0])
            # Take last part: task_board → board
            candidates.append(base_name.split('_')[-1])
        
        return candidates
    
    def _search_for_source_file(self, source_name: str, test_file: Path) -> Optional[Path]:
        """Search for source file with enhanced path patterns."""
        search_paths = [
            # Same directory as test
            test_file.parent / f"{source_name}.py",
            # Parent directory  
            test_file.parent.parent / f"{source_name}.py",
            # Module-specific directories based on test path
            *self._get_module_specific_paths(source_name, test_file),
            # Common autotasktracker locations
            self.project_root / "autotasktracker" / f"{source_name}.py",
            self.project_root / "autotasktracker" / "core" / f"{source_name}.py",
            self.project_root / "autotasktracker" / "ai" / f"{source_name}.py",
            self.project_root / "autotasktracker" / "pensieve" / f"{source_name}.py",
            self.project_root / "autotasktracker" / "dashboards" / f"{source_name}.py",
            self.project_root / "autotasktracker" / "utils" / f"{source_name}.py",
            # Scripts directories
            self.project_root / "scripts" / f"{source_name}.py",
            self.project_root / "scripts" / "ai" / f"{source_name}.py",
            self.project_root / "scripts" / "processing" / f"{source_name}.py",
        ]
        
        for candidate in search_paths:
            if candidate.exists() and candidate.is_file():
                return candidate
        
        return None
    
    def _get_module_specific_paths(self, source_name: str, test_file: Path) -> List[Path]:
        """Generate module-specific search paths based on test file location."""
        paths = []
        
        # Determine module from test path
        test_path_str = str(test_file)
        
        if 'dashboard' in test_path_str or 'ui' in test_path_str:
            paths.extend([
                self.project_root / "autotasktracker" / "dashboards" / f"{source_name}.py",
                self.project_root / "autotasktracker" / "dashboards" / "components" / f"{source_name}.py",
            ])
        
        if 'comparison' in test_path_str:
            paths.extend([
                self.project_root / "autotasktracker" / "comparison" / f"{source_name}.py",
                self.project_root / "autotasktracker" / "comparison" / "analysis" / f"{source_name}.py",
                self.project_root / "autotasktracker" / "comparison" / "dashboards" / f"{source_name}.py",
            ])
        
        if 'ai' in test_path_str or 'vlm' in test_path_str or 'embedding' in test_path_str:
            paths.extend([
                self.project_root / "autotasktracker" / "ai" / f"{source_name}.py",
                self.project_root / "scripts" / "ai" / f"{source_name}.py",
            ])
        
        if 'pensieve' in test_path_str:
            paths.extend([
                self.project_root / "autotasktracker" / "pensieve" / f"{source_name}.py",
            ])
        
        return paths
    
    def _contextual_search(self, test_file: Path) -> Optional[Path]:
        """Contextual search based on test file content and naming patterns."""
        try:
            content = test_file.read_text(encoding='utf-8')
            
            # Look for import patterns to infer source modules
            import_patterns = [
                r'from autotasktracker\.(\w+)\.(\w+) import',
                r'from autotasktracker\.(\w+) import (\w+)',
                r'import autotasktracker\.(\w+)\.(\w+)',
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if len(match) == 2:
                        module, name = match
                        candidate = self.project_root / "autotasktracker" / module / f"{name}.py"
                        if candidate.exists():
                            logger.debug(f"Found via contextual analysis: {candidate}")
                            return candidate
            
            # Look for class names in test content  
            class_pattern = r'class\s+Test(\w+)'
            class_matches = re.findall(class_pattern, content)
            for class_name in class_matches:
                # Convert TestTaskBoard → task_board
                source_name = re.sub(r'([A-Z])', r'_\1', class_name).lower().lstrip('_')
                candidate = self._search_for_source_file(source_name, test_file)
                if candidate:
                    return candidate
                    
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Contextual search failed for {test_file}: {e}")
        
        return None


# Backwards compatibility - alias to the original class name
SimpleMutationTester = RefactoredMutationTester