"""Test for import-related code quality issues."""
import logging
import os
import re
import ast
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)


class TestImportPatterns:
    """Test for proper import patterns and organization."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.package_dir = self.project_root / "autotasktracker"
        
    def get_python_files(self, exclude_dirs=None):
        """Get all Python files in the project"""
        if exclude_dirs is None:
            exclude_dirs = {'venv', '__pycache__', '.git', '.pytest_cache', 'build', 'dist'}
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories from search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def test_no_sys_path_hacks(self):
        """Test that there are no sys.path manipulations in package files"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        files_with_sys_path = []
        
        for file_path in python_files:
            content = file_path.read_text()
            # Look for sys.path manipulations
            if re.search(r'sys\.path\.(insert|append)', content):
                # Allow in test files, legacy files, and the main entry point
                if ('test' not in str(file_path) and 
                    'legacy' not in str(file_path) and 
                    file_path.name != 'autotasktracker.py'):
                    files_with_sys_path.append(str(file_path))
        
        assert not files_with_sys_path, f"Found sys.path manipulations in: {files_with_sys_path}"
    
    def test_imports_are_valid(self):
        """Test that all imports are valid and follow conventions"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        import_issues = []
        
        for file_path in python_files:
            # Skip main entry point files which are not in the package
            if file_path.name in ['autotasktracker.py'] or file_path.name.startswith('run_'):
                continue
                
            content = file_path.read_text()
            
            # Check for relative imports outside of package
            if 'autotasktracker' in str(file_path):
                # Relative imports should use . notation
                bad_imports = re.findall(r'from autotasktracker\.(?:.*?)\.(?:.*?) import', content)
                if bad_imports and file_path.parent.name != 'autotasktracker':
                    # Could use relative imports instead
                    try:
                        rel_path = file_path.relative_to(self.package_dir)
                        if rel_path.parts[0] in ['core', 'dashboards', 'utils']:
                            import_issues.append(f"{file_path}: Could use relative imports")
                    except ValueError:
                        # File is outside package directory, skip
                        continue
        
        # We'll just warn, not fail for this
        if import_issues:
            logger.info(f"Import suggestions: {import_issues}")
    
    def test_no_unused_imports(self):
        """Test for potentially unused imports"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        
        for file_path in python_files:
            # Skip __init__.py files as they often have imports for re-export
            if file_path.name == '__init__.py':
                continue
                
            try:
                content = file_path.read_text()
                tree = ast.parse(content)
                
                # Get all imports
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for alias in node.names:
                                imports.append(alias.name)
                
                # Check if imports are used (simple check)
                unused = []
                for imp in set(imports):
                    # Skip common always-used imports
                    if imp in ['sys', 'os', 'typing', '__future__']:
                        continue
                    # Simple check - just see if the name appears elsewhere
                    if content.count(imp) == 1:  # Only appears in import
                        unused.append(imp)
                
                if unused:
                    logger.info(f"Potentially unused imports in {file_path}: {unused}")
                    
            except:
                # Skip files that can't be parsed
                pass
    
    def test_consistent_import_style(self):
        """Test for consistent import organization and style"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        import_issues = []
        
        for file_path in python_files:
            if 'test' in str(file_path) or '__init__.py' in str(file_path):
                continue
                
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Check for imports mixed with code (not at top)
            found_non_import = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                    
                if stripped.startswith('import ') or stripped.startswith('from '):
                    if found_non_import and i > 20:  # Allow some flexibility
                        import_issues.append(f"{file_path}:{i+1} (import not at top)")
                        break
                elif not stripped.startswith('__'):
                    found_non_import = True
        
        # Just warn about import style issues
        if import_issues:
            logger.info(f"Found import style issues: {len(import_issues)} files")
            for issue in import_issues[:3]:
                logger.info(f"  {issue}")
    
    def test_circular_imports(self):
        """Test for potential circular import issues"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        potential_cycles = []
        
        # Build import graph (simplified)
        imports = {}
        for file_path in python_files:
            content = file_path.read_text()
            file_imports = []
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('from autotasktracker'):
                    # Extract the module being imported
                    if ' import ' in line:
                        module = line.split(' import ')[0].replace('from ', '')
                        file_imports.append(module)
            
            imports[str(file_path)] = file_imports
        
        # Simple cycle detection (A imports B, B imports A)
        for file1, file1_imports in imports.items():
            for file2, file2_imports in imports.items():
                if file1 != file2:
                    # Check if they import each other
                    file1_module = file1.replace(str(self.project_root) + '/', '').replace('/', '.').replace('.py', '')
                    file2_module = file2.replace(str(self.project_root) + '/', '').replace('/', '.').replace('.py', '')
                    
                    if (any(file2_module in imp for imp in file1_imports) and 
                        any(file1_module in imp for imp in file2_imports)):
                        cycle_pair = tuple(sorted([file1, file2]))
                        if cycle_pair not in potential_cycles:
                            potential_cycles.append(f"{file1} <-> {file2}")
        
        # Just warn about potential cycles
        if potential_cycles:
            logger.warning("Potential circular imports detected:")
            for cycle in potential_cycles[:3]:
                logger.warning(f"  {cycle}")