"""Import validation system for AutoTaskTracker health tests.

Validates import patterns, checks for issues, and ensures
imports work correctly after optimizations.
"""

import ast
import subprocess
import sys
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


class ImportValidator:
    """Validates import patterns and functionality."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.package_root = self.project_root / "autotasktracker"
        
        # Validation results
        self.validation_results = {
            'syntax_valid': [],
            'syntax_errors': [],
            'import_errors': [],
            'circular_imports': [],
            'missing_modules': [],
            'barrel_export_issues': []
        }
    
    def validate_all_imports(self) -> Dict[str, Any]:
        """Run comprehensive import validation."""
        logger.info("Starting import validation...")
        
        # Check syntax of all Python files
        self._validate_syntax()
        
        # Check for circular imports
        self._check_circular_imports()
        
        # Validate barrel exports work
        self._validate_barrel_exports()
        
        # Check key imports work
        self._validate_key_imports()
        
        return {
            'total_files_checked': len(self.validation_results['syntax_valid']) + len(self.validation_results['syntax_errors']),
            'syntax_errors': self.validation_results['syntax_errors'],
            'import_errors': self.validation_results['import_errors'],
            'circular_imports': self.validation_results['circular_imports'],
            'issues': self.validation_results,
            'overall_status': self._get_overall_status()
        }
    
    def _validate_syntax(self):
        """Check syntax of all Python files."""
        for py_file in self._find_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                ast.parse(content, filename=str(py_file))
                self.validation_results['syntax_valid'].append(str(py_file.relative_to(self.project_root)))
                
            except SyntaxError as e:
                self.validation_results['syntax_errors'].append({
                    'file': str(py_file.relative_to(self.project_root)),
                    'error': str(e),
                    'line': getattr(e, 'lineno', 'unknown')
                })
            except Exception as e:
                logger.warning(f"Could not validate {py_file}: {e}")
    
    def _check_circular_imports(self):
        """Check for circular import dependencies."""
        # This is a simplified check - a full circular import detector would be more complex
        import_graph = {}
        
        for py_file in self._find_python_files():
            if py_file.name == '__init__.py':
                continue
                
            try:
                imports = self._extract_imports_from_file(py_file)
                module_name = self._file_to_module_name(py_file)
                import_graph[module_name] = imports
            except Exception as e:
                logger.debug(f"Could not extract imports from {py_file}: {e}")
        
        # Simple cycle detection
        for module, imports in import_graph.items():
            for imported_module in imports:
                if imported_module in import_graph:
                    if module in import_graph[imported_module]:
                        self.validation_results['circular_imports'].append({
                            'module1': module,
                            'module2': imported_module,
                            'type': 'direct_circular'
                        })
    
    def _validate_barrel_exports(self):
        """Validate that barrel exports work correctly."""
        barrel_modules = [
            'autotasktracker.core',
            'autotasktracker.ai', 
            'autotasktracker.dashboards'
        ]
        
        for module_name in barrel_modules:
            try:
                # Try to import the module
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    self.validation_results['missing_modules'].append(module_name)
                    continue
                
                # Check if __init__.py exists and has __all__
                init_file = self.project_root / module_name.replace('.', '/') / '__init__.py'
                if init_file.exists():
                    with open(init_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if '__all__' not in content:
                        self.validation_results['barrel_export_issues'].append({
                            'module': module_name,
                            'issue': 'Missing __all__ in __init__.py'
                        })
                
            except Exception as e:
                self.validation_results['import_errors'].append({
                    'module': module_name,
                    'error': str(e),
                    'type': 'barrel_export_validation'
                })
    
    def _validate_key_imports(self):
        """Validate that key imports work correctly."""
        key_imports = [
            ('autotasktracker', 'DatabaseManager'),
            ('autotasktracker.core', 'DatabaseManager'),
            ('autotasktracker.ai', 'VLMProcessor'),
            ('autotasktracker.factories', 'create_database_manager'),
            ('autotasktracker.interfaces', 'AbstractDatabaseManager')
        ]
        
        for module_name, import_name in key_imports:
            try:
                # Try the import
                module = importlib.import_module(module_name)
                if not hasattr(module, import_name):
                    self.validation_results['import_errors'].append({
                        'module': module_name,
                        'import': import_name,
                        'error': f'{import_name} not found in {module_name}',
                        'type': 'missing_attribute'
                    })
                    
            except ImportError as e:
                self.validation_results['import_errors'].append({
                    'module': module_name,
                    'import': import_name,
                    'error': str(e),
                    'type': 'import_error'
                })
            except Exception as e:
                self.validation_results['import_errors'].append({
                    'module': module_name,
                    'import': import_name,
                    'error': str(e),
                    'type': 'validation_error'
                })
    
    def _extract_imports_from_file(self, file_path: Path) -> List[str]:
        """Extract import module names from a file."""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith('autotasktracker.'):
                            imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('autotasktracker.'):
                        imports.append(node.module)
        
        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")
        
        return imports
    
    def _file_to_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        relative_path = file_path.relative_to(self.project_root)
        
        # Remove .py extension
        if relative_path.suffix == '.py':
            relative_path = relative_path.with_suffix('')
        
        # Convert path to module name
        parts = relative_path.parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        
        return '.'.join(parts)
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Scan autotasktracker package
        if self.package_root.exists():
            python_files.extend(self.package_root.rglob("*.py"))
        
        # Skip test files for this validation
        return [f for f in python_files if not self._should_skip_file(f)]
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', 'venv', '.venv', 'test_'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _get_overall_status(self) -> str:
        """Get overall validation status."""
        if self.validation_results['syntax_errors']:
            return 'critical'
        elif self.validation_results['import_errors']:
            return 'warning'
        elif self.validation_results['circular_imports']:
            return 'warning'
        else:
            return 'healthy'
    
    def test_import_performance(self) -> Dict[str, float]:
        """Test import performance for key modules."""
        import time
        
        performance_results = {}
        
        test_imports = [
            'autotasktracker',
            'autotasktracker.core',
            'autotasktracker.ai',
            'autotasktracker.dashboards',
            'autotasktracker.factories',
            'autotasktracker.interfaces'
        ]
        
        for module_name in test_imports:
            try:
                start_time = time.time()
                
                # Clear any existing import
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                importlib.import_module(module_name)
                
                end_time = time.time()
                performance_results[module_name] = (end_time - start_time) * 1000  # Convert to ms
                
            except Exception as e:
                performance_results[module_name] = -1  # Error indicator
                logger.warning(f"Could not test import performance for {module_name}: {e}")
        
        return performance_results
    
    def validate_imports_after_fixes(self, fixed_files: List[str]) -> Dict[str, Any]:
        """Validate imports work correctly after applying fixes."""
        validation_results = {
            'syntax_errors': [],
            'import_errors': [],
            'successful_validations': 0
        }
        
        for file_path in fixed_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            # Check syntax
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                ast.parse(content, filename=str(full_path))
                validation_results['successful_validations'] += 1
                
            except SyntaxError as e:
                validation_results['syntax_errors'].append({
                    'file': file_path,
                    'error': str(e),
                    'line': getattr(e, 'lineno', 'unknown')
                })
            
            # Test if it's importable (for package files)
            if file_path.endswith('__init__.py'):
                module_name = file_path.replace('/', '.').replace('__init__.py', '').rstrip('.')
                try:
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    importlib.import_module(module_name)
                except ImportError as e:
                    validation_results['import_errors'].append({
                        'module': module_name,
                        'error': str(e)
                    })
        
        return validation_results
    
    def check_import_consistency(self) -> Dict[str, Any]:
        """Check for import consistency across the codebase."""
        consistency_issues = {
            'mixed_import_styles': [],
            'inconsistent_aliases': [],
            'deprecated_imports': []
        }
        
        # Track how each module is imported
        import_patterns = {}
        
        for py_file in self._find_python_files():
            try:
                imports = self._analyze_file_imports(py_file)
                
                for imp in imports:
                    module = imp.get('module')
                    if module and module.startswith('autotasktracker.'):
                        if module not in import_patterns:
                            import_patterns[module] = {
                                'direct_imports': [],
                                'from_imports': [],
                                'aliases': set()
                            }
                        
                        if imp['type'] == 'import':
                            import_patterns[module]['direct_imports'].append(py_file)
                        else:
                            import_patterns[module]['from_imports'].append(py_file)
                        
                        if imp.get('alias'):
                            import_patterns[module]['aliases'].add(imp['alias'])
            
            except Exception as e:
                logger.debug(f"Could not analyze imports in {py_file}: {e}")
        
        # Check for inconsistencies
        for module, patterns in import_patterns.items():
            # Mixed import styles
            if patterns['direct_imports'] and patterns['from_imports']:
                consistency_issues['mixed_import_styles'].append({
                    'module': module,
                    'direct_import_files': [str(f.relative_to(self.project_root)) for f in patterns['direct_imports'][:3]],
                    'from_import_files': [str(f.relative_to(self.project_root)) for f in patterns['from_imports'][:3]]
                })
            
            # Multiple aliases for same module
            if len(patterns['aliases']) > 1:
                consistency_issues['inconsistent_aliases'].append({
                    'module': module,
                    'aliases': list(patterns['aliases'])
                })
        
        return consistency_issues
    
    def _analyze_file_imports(self, file_path: Path) -> List[Dict]:
        """Analyze imports in a single file."""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': node.module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
        
        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")
        
        return imports