"""Import pattern analyzer for AutoTaskTracker health tests.

Analyzes import patterns across the codebase to identify optimization opportunities
and enforce import best practices per CLAUDE.md guidelines.
"""

import ast
import os
import re
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ImportAnalyzer:
    """Analyzes import patterns and provides optimization recommendations."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.package_root = self.project_root / "autotasktracker"
        self.scripts_root = self.project_root / "scripts"
        
        # Import pattern tracking
        self.imports_by_file: Dict[str, List[Dict]] = {}
        self.import_frequency: Counter = Counter()
        self.issues_found = {
            'relative_imports': [],
            'direct_sqlite_usage': [],
            'sys_path_violations': [],
            'print_in_production': [],
            'missing_barrel_exports': [],
            'consolidation_opportunities': []
        }
    
    def analyze_codebase(self) -> Dict[str, Any]:
        """Run comprehensive import analysis on the entire codebase."""
        logger.info("Starting import analysis...")
        
        # Analyze Python files
        for py_file in self._find_python_files():
            try:
                self._analyze_file(py_file)
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
        
        results = {
            'files_analyzed': len(self.imports_by_file),
            'total_imports': sum(len(imports) for imports in self.imports_by_file.values()),
            'unique_imports': len(self.import_frequency),
            'issues': self.issues_found,
            'import_frequency': dict(self.import_frequency.most_common(20)),
            'optimization_suggestions': self._generate_suggestions()
        }
        
        logger.info(f"Analysis complete: {results['files_analyzed']} files, {results['total_imports']} imports")
        return results
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Scan autotasktracker package
        if self.package_root.exists():
            python_files.extend(self.package_root.rglob("*.py"))
        
        # Scan scripts directory
        if self.scripts_root.exists():
            python_files.extend(self.scripts_root.rglob("*.py"))
        
        # Add root level Python files
        python_files.extend(self.project_root.glob("*.py"))
        
        return [f for f in python_files if not self._should_skip_file(f)]
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped in analysis."""
        skip_patterns = [
            '__pycache__', '.git', 'venv', '.venv', 'build', 'dist', '.pytest_cache',
            'test_', '_test.py'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze imports in a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Could not read {file_path} - encoding issue")
            return
        
        # Parse AST
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return
        
        file_imports = []
        relative_path = str(file_path.relative_to(self.project_root))
        
        # Analyze imports and check for issues
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_info = self._extract_import_info(node, relative_path)
                if import_info:
                    file_imports.append(import_info)
                    self._check_import_issues(node, content, relative_path)
        
        self.imports_by_file[relative_path] = file_imports
        
        # Check for other issues in content
        self._check_content_issues(content, relative_path)
    
    def _extract_import_info(self, node: ast.AST, file_path: str) -> Optional[Dict]:
        """Extract import information from AST node."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.import_frequency[alias.name] += 1
                return {
                    'type': 'import',
                    'module': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno,
                    'file': file_path
                }
        
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            level = node.level
            
            for alias in node.names:
                full_import = f"{module}.{alias.name}" if module else alias.name
                self.import_frequency[full_import] += 1
                
                return {
                    'type': 'from_import',
                    'module': module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'level': level,
                    'line': node.lineno,
                    'file': file_path
                }
        
        return None
    
    def _check_import_issues(self, node: ast.AST, content: str, file_path: str) -> None:
        """Check for import-related issues."""
        if isinstance(node, ast.ImportFrom):
            # Check for relative imports (CLAUDE.md violation)
            if node.level > 0:
                self.issues_found['relative_imports'].append({
                    'file': file_path,
                    'line': node.lineno,
                    'import': f"{'.' * node.level}{node.module or ''}",
                    'severity': 'error'
                })
            
            # Check for direct sqlite3 usage
            if node.module == 'sqlite3':
                self.issues_found['direct_sqlite_usage'].append({
                    'file': file_path,
                    'line': node.lineno,
                    'recommendation': 'Use DatabaseManager from autotasktracker.core instead',
                    'severity': 'warning'
                })
            
            # Check for sys.path manipulation
            if node.module == 'sys' and any(alias.name == 'path' for alias in node.names):
                if 'sys.path.append' in content:
                    self.issues_found['sys_path_violations'].append({
                        'file': file_path,
                        'line': node.lineno,
                        'pattern': 'sys.path.append',
                        'recommendation': 'Use proper package imports or sys.path.insert for scripts',
                        'severity': 'error'
                    })
    
    def _check_content_issues(self, content: str, file_path: str) -> None:
        """Check for other issues in file content."""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for print statements in production code
            if (re.search(r'\bprint\s*\(', line) and 
                not file_path.startswith('tests/') and
                not file_path.startswith('scripts/') and
                not file_path.endswith('__main__.py')):
                
                self.issues_found['print_in_production'].append({
                    'file': file_path,
                    'line': i,
                    'content': line.strip(),
                    'recommendation': 'Use logging instead of print statements',
                    'severity': 'warning'
                })
    
    def _generate_suggestions(self) -> List[Dict]:
        """Generate optimization suggestions based on analysis."""
        suggestions = []
        
        # Suggest barrel exports for frequently imported modules
        frequent_modules = {}
        for file_path, imports in self.imports_by_file.items():
            for imp in imports:
                if imp['type'] == 'from_import' and imp['module']:
                    if imp['module'].startswith('autotasktracker.'):
                        parts = imp['module'].split('.')
                        if len(parts) >= 3:  # e.g., autotasktracker.core.database
                            base_module = '.'.join(parts[:3])
                            if base_module not in frequent_modules:
                                frequent_modules[base_module] = set()
                            frequent_modules[base_module].add(imp['name'])
        
        for module, imports in frequent_modules.items():
            if len(imports) >= 3:
                suggestions.append({
                    'type': 'barrel_export',
                    'module': module,
                    'imports': list(imports),
                    'benefit': f"Consolidate {len(imports)} imports from {module}",
                    'priority': 'medium'
                })
        
        # Suggest factory patterns for frequently instantiated classes
        class_usage = Counter()
        for imports in self.imports_by_file.values():
            for imp in imports:
                if imp['type'] == 'from_import' and imp['name']:
                    # Look for class-like names (PascalCase)
                    if imp['name'][0].isupper() and 'Manager' in imp['name']:
                        class_usage[imp['name']] += 1
        
        for class_name, usage_count in class_usage.most_common(5):
            if usage_count >= 3:
                suggestions.append({
                    'type': 'factory_pattern',
                    'class': class_name,
                    'usage_count': usage_count,
                    'benefit': f"Centralize {class_name} creation with factory function",
                    'priority': 'low'
                })
        
        return suggestions
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate an overall import health score."""
        total_files = len(self.imports_by_file)
        if total_files == 0:
            return {'score': 0, 'details': 'No files analyzed'}
        
        # Calculate penalty points
        penalties = 0
        max_penalties = total_files * 10
        
        # Issue penalties
        penalties += len(self.issues_found['relative_imports']) * 3
        penalties += len(self.issues_found['direct_sqlite_usage']) * 2
        penalties += len(self.issues_found['sys_path_violations']) * 3
        penalties += len(self.issues_found['print_in_production']) * 1
        
        # Calculate score (0-100)
        score = max(0, 100 - (penalties * 100 / max_penalties))
        
        return {
            'score': round(score, 1),
            'penalties': penalties,
            'max_penalties': max_penalties,
            'issue_summary': {
                issue_type: len(issues) 
                for issue_type, issues in self.issues_found.items()
            }
        }