"""Automated import fixer for AutoTaskTracker health tests.

Finds import issues and provides automated fixes to optimize imports
throughout the codebase.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ImportFixer:
    """Automated import optimization and fixing."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.package_root = self.project_root / "autotasktracker"
        
        # Track fixes made
        self.fixes_applied = []
        self.backup_files = {}
        
        # Known barrel exports
        self.barrel_exports = {
            'autotasktracker.core': [
                'DatabaseManager', 'get_default_db_manager',
                'ActivityCategorizer', 'categorize_activity', 
                'extract_task_summary', 'extract_window_title',
                'TaskExtractor', 'TimeTracker', 'VLMErrorHandler',
                'ConfigManager', 'PensieveSchemaAdapter'
            ],
            'autotasktracker.ai': [
                'VLMTaskExtractor', 'extract_vlm_enhanced_task', 'VLMProcessor',
                'OCREnhancer', 'create_ocr_enhancer', 'EmbeddingsSearchEngine',
                'EmbeddingStats', 'AIEnhancedTaskExtractor', 'SensitiveDataFilter'
            ],
            'autotasktracker.dashboards': [
                'task_board_main', 'analytics_main', 'timetracker_main', 'launcher_main',
                'BaseDashboard', 'DashboardCache', 'NotificationManager',
                'format_datetime', 'safe_divide', 'get_color_palette', 'DashboardTemplate',
                'TaskRepository', 'ScreenshotRepository', 'TaskModel', 'ScreenshotModel'
            ]
        }
        
        # Factory function mappings
        self.factory_mappings = {
            'DatabaseManager': 'create_database_manager',
            'ActivityCategorizer': 'create_activity_categorizer',
            'TaskExtractor': 'create_task_extractor',
            'TimeTracker': 'create_time_tracker',
            'EmbeddingsSearch': 'create_embeddings_search',
            'VLMProcessor': 'create_vlm_processor',
            'PerformanceAnalyzer': 'create_performance_analyzer',
            'PensieveAPIClient': 'create_pensieve_api_client'
        }
    
    def find_fixable_issues(self) -> Dict[str, List[Dict]]:
        """Find all import issues that can be automatically fixed."""
        issues = {
            'relative_imports': [],
            'barrel_export_opportunities': [],
            'direct_database_imports': [],
            'factory_opportunities': [],
            'consolidation_opportunities': [],
            'syntax_errors': []
        }
        
        for py_file in self._find_python_files():
            file_issues = self._analyze_file_for_fixes(py_file)
            
            for issue_type, file_issues_list in file_issues.items():
                issues[issue_type].extend(file_issues_list)
        
        return issues
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Scan autotasktracker package
        if self.package_root.exists():
            python_files.extend(self.package_root.rglob("*.py"))
        
        # Scan scripts directory
        scripts_root = self.project_root / "scripts"
        if scripts_root.exists():
            python_files.extend(scripts_root.rglob("*.py"))
        
        return [f for f in python_files if not self._should_skip_file(f)]
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', 'venv', '.venv', 'build', 'dist', '.pytest_cache',
            'test_', '_test.py', 'conftest.py'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_file_for_fixes(self, file_path: Path) -> Dict[str, List[Dict]]:
        """Analyze a file for fixable import issues."""
        issues = defaultdict(list)
        relative_path = str(file_path.relative_to(self.project_root))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            # Track imports from same modules for consolidation
            module_imports = defaultdict(list)
            
            # Analyze each import
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self._analyze_import_from_for_fixes(node, relative_path, issues, content)
                    
                    # Track for consolidation
                    if node.module and node.module.startswith('autotasktracker.'):
                        module_imports[node.module].extend([alias.name for alias in node.names])
                        
            # Check for consolidation opportunities
            for module, imports in module_imports.items():
                if len(imports) >= 3:  # Multiple imports from same module
                    issues['consolidation_opportunities'].append({
                        'file': relative_path,
                        'module': module,
                        'imports': imports,
                        'count': len(imports)
                    })
                    
        except SyntaxError as e:
            issues['syntax_errors'].append({
                'file': relative_path,
                'error': str(e),
                'line': getattr(e, 'lineno', 'unknown')
            })
        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")
            
        return dict(issues)
    
    def _analyze_import_from_for_fixes(self, node: ast.ImportFrom, file_path: str, issues: Dict, content: str):
        """Analyze a 'from X import Y' statement for fixes."""
        if not node.module:
            return
            
        module = node.module
        line_no = node.lineno
        
        # Check for relative imports (CLAUDE.md violation)
        if node.level > 0:
            issues['relative_imports'].append({
                'file': file_path,
                'line': line_no,
                'current': f"from {'.' * node.level}{module} import",
                'suggested': self._suggest_absolute_import(module, file_path, node.level),
                'names': [alias.name for alias in node.names]
            })
        
        # Check for barrel export opportunities
        if module.startswith('autotasktracker.'):
            barrel_fix = self._suggest_barrel_export_fix(module, node.names, file_path, line_no)
            if barrel_fix:
                issues['barrel_export_opportunities'].append(barrel_fix)
        
        # Check for direct database imports that should use barrel exports
        if module == 'autotasktracker.core.database':
            imported_names = [alias.name for alias in node.names]
            if any(name in self.barrel_exports['autotasktracker.core'] for name in imported_names):
                issues['direct_database_imports'].append({
                    'file': file_path,
                    'line': line_no,
                    'current': f"from {module} import {', '.join(imported_names)}",
                    'suggested': f"from autotasktracker.core import {', '.join(imported_names)}",
                    'names': imported_names
                })
        
        # Check for factory opportunities
        for alias in node.names:
            if alias.name in self.factory_mappings:
                # Check if class is being instantiated in the file
                if f"{alias.name}(" in content:
                    issues['factory_opportunities'].append({
                        'file': file_path,
                        'line': line_no,
                        'class': alias.name,
                        'factory': self.factory_mappings[alias.name],
                        'suggestion': f"Consider using {self.factory_mappings[alias.name]}() factory"
                    })
    
    def _suggest_absolute_import(self, module: str, file_path: str, level: int) -> str:
        """Suggest absolute import to replace relative import."""
        file_parts = Path(file_path).parts
        
        # Calculate absolute module path
        if file_path.startswith('autotasktracker/'):
            # Package file
            package_parts = file_parts[:-1]  # Remove filename
            if level <= len(package_parts):
                base_parts = package_parts[:-level] if level > 0 else package_parts
                if module:
                    absolute_module = '.'.join(base_parts + tuple(module.split('.')))
                else:
                    absolute_module = '.'.join(base_parts)
                return f"from {absolute_module} import"
        
        return f"# TODO: Fix relative import manually"
    
    def _suggest_barrel_export_fix(self, module: str, names: List[ast.alias], file_path: str, line_no: int) -> Optional[Dict]:
        """Suggest using barrel exports if available."""
        for barrel_module, exports in self.barrel_exports.items():
            if module.startswith(barrel_module + '.'):
                imported_names = [alias.name for alias in names]
                if all(name in exports for name in imported_names):
                    return {
                        'file': file_path,
                        'line': line_no,
                        'current': f"from {module} import {', '.join(imported_names)}",
                        'suggested': f"from {barrel_module} import {', '.join(imported_names)}",
                        'barrel_module': barrel_module,
                        'imports': imported_names
                    }
        return None
    
    def apply_safe_fixes(self, issues: Dict[str, List[Dict]], dry_run: bool = True) -> Dict[str, Any]:
        """Apply safe automated fixes."""
        if dry_run:
            return self._simulate_fixes(issues)
        
        fixes_applied = {
            'barrel_export_opportunities': 0,
            'direct_database_imports': 0,
            'consolidation_opportunities': 0,
            'errors': []
        }
        
        # Apply barrel export fixes (safest)
        for fix in issues.get('barrel_export_opportunities', []):
            try:
                if self._apply_barrel_export_fix(fix):
                    fixes_applied['barrel_export_opportunities'] += 1
            except Exception as e:
                fixes_applied['errors'].append(f"Barrel export fix failed: {e}")
        
        # Apply direct database import fixes
        for fix in issues.get('direct_database_imports', []):
            try:
                if self._apply_direct_import_fix(fix):
                    fixes_applied['direct_database_imports'] += 1
            except Exception as e:
                fixes_applied['errors'].append(f"Direct import fix failed: {e}")
        
        return fixes_applied
    
    def _simulate_fixes(self, issues: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Simulate applying fixes without modifying files."""
        simulation = {
            'total_fixable_issues': 0,
            'safe_fixes': [],
            'risky_fixes': [],
            'unfixable_issues': []
        }
        
        # Categorize fixes by safety
        safe_fix_types = ['barrel_export_opportunities', 'direct_database_imports']
        risky_fix_types = ['relative_imports', 'consolidation_opportunities']
        
        for fix_type, fix_list in issues.items():
            simulation['total_fixable_issues'] += len(fix_list)
            
            if fix_type in safe_fix_types:
                simulation['safe_fixes'].extend([
                    {
                        'type': fix_type,
                        'file': fix['file'],
                        'description': f"Replace with: {fix['suggested']}"
                    }
                    for fix in fix_list
                ])
            elif fix_type in risky_fix_types:
                simulation['risky_fixes'].extend([
                    {
                        'type': fix_type,
                        'file': fix['file'],
                        'description': f"Manual review needed: {fix.get('current', 'complex fix')}"
                    }
                    for fix in fix_list
                ])
            else:
                simulation['unfixable_issues'].extend(fix_list)
        
        return simulation
    
    def _apply_barrel_export_fix(self, fix: Dict) -> bool:
        """Apply a barrel export fix."""
        file_path = Path(self.project_root / fix['file'])
        
        if not file_path.exists():
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup original
        if str(file_path) not in self.backup_files:
            self.backup_files[str(file_path)] = content
        
        # Replace the import
        new_content = content.replace(fix['current'], fix['suggested'])
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.fixes_applied.append({
                'type': 'barrel_export',
                'file': fix['file'],
                'change': f"{fix['current']} -> {fix['suggested']}"
            })
            
            logger.info(f"Applied barrel export fix to {fix['file']}")
            return True
        
        return False
    
    def _apply_direct_import_fix(self, fix: Dict) -> bool:
        """Apply a direct import fix."""
        file_path = Path(self.project_root / fix['file'])
        
        if not file_path.exists():
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup original
        if str(file_path) not in self.backup_files:
            self.backup_files[str(file_path)] = content
        
        # Replace the import
        new_content = content.replace(fix['current'], fix['suggested'])
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.fixes_applied.append({
                'type': 'direct_import',
                'file': fix['file'],
                'change': f"{fix['current']} -> {fix['suggested']}"
            })
            
            logger.info(f"Applied direct import fix to {fix['file']}")
            return True
        
        return False
    
    def rollback_all_fixes(self) -> int:
        """Rollback all applied fixes."""
        rollback_count = 0
        
        for file_path, original_content in self.backup_files.items():
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                rollback_count += 1
                logger.info(f"Rolled back fixes in {file_path}")
            except Exception as e:
                logger.error(f"Failed to rollback {file_path}: {e}")
        
        self.backup_files.clear()
        self.fixes_applied.clear()
        
        return rollback_count
    
    def validate_syntax_after_fixes(self) -> List[Dict]:
        """Validate that all fixed files still have valid syntax."""
        syntax_errors = []
        
        for fix in self.fixes_applied:
            file_path = Path(self.project_root / fix['file'])
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                ast.parse(content, filename=str(file_path))
                
            except SyntaxError as e:
                syntax_errors.append({
                    'file': fix['file'],
                    'error': str(e),
                    'line': getattr(e, 'lineno', 'unknown'),
                    'fix_applied': fix
                })
        
        return syntax_errors
    
    def generate_fix_report(self, issues: Dict[str, List[Dict]]) -> str:
        """Generate a comprehensive report of fixable issues."""
        report = ["# Import System Fix Report\\n"]
        
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        report.append(f"**Total Issues Found**: {total_issues}\\n")
        
        for issue_type, issue_list in issues.items():
            if not issue_list:
                continue
                
            report.append(f"## {issue_type.replace('_', ' ').title()} ({len(issue_list)} issues)\\n")
            
            for issue in issue_list[:3]:  # Show first 3 issues
                report.append(f"- **{issue['file']}**")
                if 'suggested' in issue:
                    report.append(f"  - Fix: `{issue['suggested']}`")
                elif 'factory' in issue:
                    report.append(f"  - Suggestion: Use `{issue['factory']}()` factory")
                report.append("")
            
            if len(issue_list) > 3:
                report.append(f"... and {len(issue_list) - 3} more\\n")
        
        return "\\n".join(report)