import logging
logger = logging.getLogger(__name__)

"""
🚨 CODEBASE HEALTH CHECKER 🚨

This test suite checks for common codebase issues that hurt maintainability:

🏗️  ORGANIZATION ISSUES:
   - Root directory clutter (files in wrong places)
   - Duplicate/legacy files (*_improved.py, *_v2.py)
   - Proper file organization
   - Documentation quality and structure

🔧 CODE QUALITY ISSUES:
   - Bare except clauses (dangerous error handling)
   - sys.path hacks (improper imports)
   - Direct database connections (should use DatabaseManager)
   - Print statements vs proper logging

📊 CRITICAL TESTS (must pass for production):
   - test_root_directory_clutter ← 🚨 ORGANIZATION
   - test_bare_except_clauses ← 🚨 ERROR HANDLING  
   - test_no_sys_path_hacks ← 🚨 IMPORTS
   - test_database_connection_patterns ← 🚨 DATABASE

Run: pytest tests/test_codebase_health.py -v
"""

import os
import re
import ast
from pathlib import Path
import pytest


class TestCodebaseHealth:
    """Tests for common codebase issues"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
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
    
    def test_no_duplicate_improved_files(self):
        """Test that there are no 'improved' or 'v2' files"""
        python_files = self.get_python_files()
        problematic_files = []
        
        patterns = [
            r'.*_improved\.py$',
            r'.*_enhanced\.py$',
            r'.*enhanced.*\.py$',     # Files with "enhanced" anywhere in name
            r'.*_v\d+\.py$',
            r'.*_new\.py$',
            r'.*_old\.py$',
            r'.*_temp\.py$',
            r'.*_backup\.py$',
            r'.*_copy\.py$',
            r'.*_test\d+\.py$',  # test1.py, test2.py etc
            r'.*_final\.py$',
            r'.*_fixed\.py$'
        ]
        
        # Also check for legacy folders/files
        legacy_indicators = ['legacy', 'old', 'deprecated', 'archive']
        
        for file_path in python_files:
            filename = file_path.name
            filepath_str = str(file_path).lower()
            
            # Check for problematic file names
            for pattern in patterns:
                if re.match(pattern, filename, re.IGNORECASE):
                    # Allow enhanced files in development folder
                    if '/development/' not in filepath_str:
                        # Allow legitimate component files like enhanced_search.py
                        if filename == 'enhanced_search.py' and '/pensieve/' in filepath_str:
                            continue
                        problematic_files.append(str(file_path))
                    break
            
            # Check for legacy folders (except if it's explicitly named 'legacy' or in scripts/archive)
            for indicator in legacy_indicators:
                if indicator in filepath_str:
                    # Allow the 'legacy' folder and scripts/archive folder
                    if indicator == 'legacy' and '/legacy/' in filepath_str:
                        continue
                    if indicator == 'archive' and '/scripts/archive/' in filepath_str:
                        continue
                    if indicator in ['old', 'deprecated'] and f'/{indicator}/' in filepath_str:
                        problematic_files.append(f"{file_path} (in '{indicator}' folder)")
        
        assert not problematic_files, f"Found files with redundant naming: {problematic_files}"
    
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
    
    def test_no_duplicate_functions(self):
        """Test for duplicate function definitions across files"""
        function_locations = {}
        duplicates = []
        
        # Focus on key functions that should not be duplicated
        key_functions = [
            'categorize_activity',
            'extract_task_info',
            'get_db_connection',
            'extract_window_title'
        ]
        
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        
        for file_path in python_files:
            # Skip test files and legacy
            if 'test' in str(file_path) or 'legacy' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name in key_functions:
                            if node.name not in function_locations:
                                function_locations[node.name] = []
                            function_locations[node.name].append(str(file_path))
            except:
                # Skip files that can't be parsed
                pass
        
        # Check for duplicates
        for func_name, locations in function_locations.items():
            if len(locations) > 1:
                # Allow if one is in __init__.py (re-export)
                non_init = [loc for loc in locations if '__init__.py' not in loc]
                if len(non_init) > 1:
                    duplicates.append(f"{func_name}: {non_init}")
        
        assert not duplicates, f"Found duplicate functions: {duplicates}"
    
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
            print(f"Import suggestions: {import_issues}")
    
    def test_no_hardcoded_paths(self):
        """Test that there are no hardcoded absolute paths"""
        python_files = self.get_python_files()
        files_with_hardcoded_paths = []
        
        # Patterns that indicate hardcoded paths
        patterns = [
            r'/Users/\w+/',
            r'C:\\Users\\',
            r'/home/\w+/',
            r'~/CodeProjects/'  # Specific user paths
        ]
        
        for file_path in python_files:
            # Skip test files for hardcoded path check
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            for pattern in patterns:
                if re.search(pattern, content):
                    # Allow in comments and docstrings
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.search(pattern, line) and not line.strip().startswith('#'):
                            # Check if it's in a docstring
                            in_docstring = False
                            if i > 0 and (lines[i-1].strip().startswith('"""') or lines[i-1].strip().startswith("'''")):
                                in_docstring = True
                            if not in_docstring:
                                files_with_hardcoded_paths.append(f"{file_path}:{i+1}")
                                break
        
        assert not files_with_hardcoded_paths, f"Found hardcoded paths in: {files_with_hardcoded_paths}"
    
    def test_no_debug_code(self):
        """Test that there's no debug code left in production files"""
        python_files = [f for f in self.get_python_files() if 'test' not in str(f)]
        debug_code_found = []
        
        debug_patterns = [
            r'print\s*\(\s*["\']debug',
            r'breakpoint\(\)',
            r'import\s+pdb',
            r'pdb\.set_trace',
            r'import\s+ipdb',
            r'console\.log',  # JavaScript debug
            r'debugger;',     # JavaScript debug
        ]
        
        for file_path in python_files:
            content = file_path.read_text()
            for pattern in debug_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    debug_code_found.append(f"{file_path}: {pattern}")
        
        assert not debug_code_found, f"Found debug code: {debug_code_found}"
    
    def test_no_todos_or_fixmes(self):
        """Test for TODO/FIXME comments that need attention"""
        python_files = self.get_python_files()
        todos_found = []
        
        patterns = [
            r'#\s*TODO',
            r'#\s*FIXME',
            r'#\s*HACK',
            r'#\s*XXX',
        ]
        
        for file_path in python_files:
            content = file_path.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        todos_found.append(f"{file_path}:{i+1}: {line.strip()}")
        
        # We'll just warn, not fail for TODOs
        if todos_found:
            print(f"\nFound {len(todos_found)} TODO/FIXME comments:")
            for todo in todos_found[:5]:  # Show first 5
                print(f"  {todo}")
            if len(todos_found) > 5:
                print(f"  ... and {len(todos_found) - 5} more")
    
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
                    print(f"\nPotentially unused imports in {file_path}: {unused}")
                    
            except:
                # Skip files that can't be parsed
                pass
    
    def test_file_permissions(self):
        """Test that Python files have correct permissions"""
        python_files = self.get_python_files()
        permission_issues = []
        
        for file_path in python_files:
            # Check if file is executable when it shouldn't be
            if os.access(file_path, os.X_OK):
                # Only main entry points should be executable
                if file_path.name not in ['autotasktracker.py', 'autotask.py', 'setup.py']:
                    permission_issues.append(f"{file_path}: Executable bit set")
        
        assert not permission_issues, f"Found permission issues: {permission_issues}"
    
    def test_no_large_files(self):
        """Test that there are no accidentally committed large files"""
        max_size_kb = 100  # 100KB max for Python files
        large_files = []
        
        for file_path in self.get_python_files():
            size_kb = file_path.stat().st_size / 1024
            if size_kb > max_size_kb:
                large_files.append(f"{file_path}: {size_kb:.1f}KB")
        
        assert not large_files, f"Found large files: {large_files}"
    
    def test_consistent_line_endings(self):
        """Test that files use consistent line endings"""
        python_files = self.get_python_files()
        mixed_endings = []
        
        for file_path in python_files:
            content = file_path.read_bytes()
            has_crlf = b'\r\n' in content
            has_lf = b'\n' in content and not has_crlf
            
            if has_crlf and has_lf:
                mixed_endings.append(str(file_path))
        
        assert not mixed_endings, f"Found files with mixed line endings: {mixed_endings}"
    
    def test_no_merge_conflicts(self):
        """Test that there are no merge conflict markers"""
        all_files = self.get_python_files()
        merge_conflicts = []
        
        conflict_markers = [
            '<' + '<<<<< ',  # Split to avoid matching self, with space
            '=' + '===== ',  # With space to avoid matching decoration lines
            '>' + '>>>>> '   # With space for consistency
        ]
        
        for file_path in all_files:
            content = file_path.read_text()
            for marker in conflict_markers:
                if marker in content:
                    merge_conflicts.append(str(file_path))
                    break
        
        assert not merge_conflicts, f"Found merge conflict markers in: {merge_conflicts}"
    
    def test_legacy_folder_awareness(self):
        """Test to identify legacy folders that might need cleanup"""
        python_files = self.get_python_files()
        legacy_files = []
        
        for file_path in python_files:
            if '/legacy/' in str(file_path):
                legacy_files.append(str(file_path))
        
        # We'll just warn about legacy files, not fail the test
        if legacy_files:
            print(f"\n⚠️  Found {len(legacy_files)} files in legacy folder:")
            for file in legacy_files[:5]:  # Show first 5
                print(f"  {file}")
            if len(legacy_files) > 5:
                print(f"  ... and {len(legacy_files) - 5} more")
            print("  Consider removing these if they're no longer needed.")
    
    def test_root_directory_clutter(self):
        """🚨 CRITICAL: Test for messy root directory with too many loose files 🚨
        
        A clean root directory is essential for project maintainability!
        Only core project files should be in the root directory.
        """
        root_files = []
        allowed_root_files = {
            # Core project files
            'README.md', 'LICENSE', 'requirements.txt', 'requirements-dev.txt',
            'setup.py', 'setup.cfg', 'pyproject.toml', '.gitignore', '.env',
            'Dockerfile', 'docker-compose.yml', 'Makefile',
            # Project-specific allowed files
            'autotasktracker.py',  # Main entry point
            'CLAUDE.md', 'QUICKSTART.md',  # Documentation
            # Dashboard wrapper files (entry points)
            'run_task_board.py', 'run_analytics.py', 'run_timetracker.py',
            'run_notifications.py', 'run_vlm_monitor.py',
            # Build/deployment
            'setup.sh'
        }
        
        # Get all files in root (not directories)
        for item in self.project_root.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                if item.name not in allowed_root_files:
                    root_files.append(str(item))
        
        # Categorize problematic files with clear messaging
        documentation_files = []
        migration_scripts = []
        debug_files = []
        ai_files = []
        loose_python_files = []
        other_files = []
        
        for file_path in root_files:
            filename = Path(file_path).name.lower()
            
            # Categorize problematic files
            if filename.endswith('.md') and filename not in ['readme.md', 'claude.md', 'quickstart.md']:
                documentation_files.append(file_path)
            elif any(word in filename for word in ['migrate', 'migration']):
                migration_scripts.append(file_path)
            elif any(word in filename for word in ['debug', 'test_', 'temp', 'analysis', 'results']):
                debug_files.append(file_path)
            elif filename.startswith('ai_') or 'ai_' in filename:
                ai_files.append(file_path)
            elif filename.endswith('.py'):
                loose_python_files.append(file_path)
            else:
                other_files.append(file_path)
        
        # Build comprehensive error message
        issues_found = []
        
        if documentation_files:
            issues_found.append(f"\n🚨 DOCUMENTATION CLUTTER ({len(documentation_files)} files):")
            for f in documentation_files:
                issues_found.append(f"  ❌ {Path(f).name} → Move to docs/")
                
        if migration_scripts:
            issues_found.append(f"\n🚨 MIGRATION SCRIPTS ({len(migration_scripts)} files):")
            for f in migration_scripts:
                issues_found.append(f"  ❌ {Path(f).name} → Move to scripts/")
                
        if debug_files:
            issues_found.append(f"\n🚨 DEBUG/TEST FILES ({len(debug_files)} files):")
            for f in debug_files:
                issues_found.append(f"  ❌ {Path(f).name} → Move to tests/ or DELETE")
                
        if ai_files:
            issues_found.append(f"\n🚨 AI SCRIPTS ({len(ai_files)} files):")
            for f in ai_files:
                issues_found.append(f"  ❌ {Path(f).name} → Move to scripts/ or examples/")
                
        if loose_python_files:
            issues_found.append(f"\n🚨 LOOSE PYTHON FILES ({len(loose_python_files)} files):")
            for f in loose_python_files:
                issues_found.append(f"  ❌ {Path(f).name} → Move to scripts/ or organize into proper module")
                
        if other_files:
            issues_found.append(f"\n🚨 OTHER CLUTTER ({len(other_files)} files):")
            for f in other_files:
                issues_found.append(f"  ❌ {Path(f).name} → Review and organize properly")
        
        if issues_found:
            error_message = f"""
🚨🚨🚨 ROOT DIRECTORY CLUTTER DETECTED 🚨🚨🚨

Your project root is messy! This makes the project harder to navigate and maintain.

ISSUES FOUND: {''.join(issues_found)}

✅ ALLOWED ROOT FILES ONLY:
  - Core: README.md, LICENSE, requirements.txt, .gitignore
  - Project: autotasktracker.py (main entry), CLAUDE.md, QUICKSTART.md
  - Build: setup.sh, Dockerfile, Makefile

🔧 QUICK FIX COMMANDS:
  # Move documentation
  mv *.md docs/ (except README.md, CLAUDE.md, QUICKSTART.md)
  
  # Move scripts
  mv *_cli.py scripts/
  mv migrate*.py scripts/
  
  # Clean up test files
  rm test_*.json test_*.csv debug_*.py
  
  # Move AI files
  mv AI_*.md docs/
  mv ai_*.py examples/

This test will PASS once root directory is properly organized!
"""
            raise AssertionError(error_message)
    
    def test_redundant_documentation(self):
        """Test for redundant or outdated documentation files"""
        doc_files = []
        
        # Check for multiple README files
        readme_files = list(self.project_root.glob("README*.md"))
        if len(readme_files) > 1:
            for readme in readme_files[1:]:  # Keep the first one
                doc_files.append(f"{readme} (multiple README files)")
        
        # Check for redundant documentation
        redundant_patterns = [
            ('AI_FEATURES.md', 'README_AI.md'),  # Likely duplicates
            ('PROJECT_STRUCTURE.md', 'docs/'),   # Structure docs should be in docs/
        ]
        
        for file1, file2 in redundant_patterns:
            path1 = self.project_root / file1
            if isinstance(file2, str) and file2.endswith('/'):
                # Check if directory exists
                path2 = self.project_root / file2
                if path1.exists() and path2.exists():
                    doc_files.append(f"{path1} (redundant - info should be in {file2})")
            else:
                path2 = self.project_root / file2
                if path1.exists() and path2.exists():
                    doc_files.append(f"{path1} and {path2} (likely duplicates)")
        
        # Flag excessive analysis/planning docs in root
        analysis_files = list(self.project_root.glob("*ANALYSIS*.md"))
        analysis_files.extend(list(self.project_root.glob("*DASHBOARD*.md")))
        analysis_files.extend(list(self.project_root.glob("VLM_*.md")))
        
        if len(analysis_files) > 2:  # Allow 1-2 but flag if excessive
            for analysis in analysis_files[2:]:
                doc_files.append(f"{analysis} (move analysis docs to docs/)")
        
        # We'll warn but not fail for documentation issues
        if doc_files:
            print(f"\n⚠️  Found {len(doc_files)} documentation organization issues:")
            for doc in doc_files[:5]:
                print(f"  {doc}")
            if len(doc_files) > 5:
                print(f"  ... and {len(doc_files) - 5} more")
    
    def test_stray_log_files(self):
        """Test for log files that shouldn't be committed"""
        log_files = []
        log_patterns = ['*.log', '*.logs', '*.out', '*.err']
        
        for pattern in log_patterns:
            log_files.extend(list(self.project_root.glob(pattern)))
            log_files.extend(list(self.project_root.glob(f"**/{pattern}")))
        
        # Filter out logs in acceptable locations
        problematic_logs = []
        for log_file in log_files:
            # Allow logs in .git, venv, __pycache__, .logs directories
            if not any(part in str(log_file) for part in ['.git', 'venv', '__pycache__', '.logs', 'logs/']):
                problematic_logs.append(str(log_file))
        
        assert not problematic_logs, f"Found log files that should not be committed: {problematic_logs}"
    
    def test_no_duplicate_modules(self):
        """Test for duplicate modules that provide similar functionality"""
        python_files = self.get_python_files()
        module_conflicts = []
        
        # Check for common duplicate patterns
        duplicate_patterns = [
            ('vlm_integration', 'VLM/Visual Language Model functionality'),
            ('task_extractor', 'Task extraction functionality'),
            ('database', 'Database connection/management'),
            ('config', 'Configuration management'),
        ]
        
        for pattern, description in duplicate_patterns:
            matching_files = [f for f in python_files if pattern in f.name.lower()]
            if len(matching_files) > 1:
                # Allow one in core and possibly one in ai, but flag if more
                locations = set()
                for f in matching_files:
                    parts = str(f).split('/')
                    if 'autotasktracker' in parts:
                        idx = parts.index('autotasktracker')
                        if idx + 1 < len(parts):
                            locations.add(parts[idx + 1])
                
                if len(locations) > 2 or ('core' in locations and 'ai' in locations and len(matching_files) > 2):
                    module_conflicts.append(f"{description}: {[str(f) for f in matching_files]}")
        
        assert not module_conflicts, f"Found duplicate modules: {module_conflicts}"
    
    def test_print_statements_vs_logging(self):
        """Test that code uses logging instead of print statements"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        files_with_prints = []
        
        for file_path in python_files:
            # Skip test files and __main__ blocks
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Look for print statements (but not in comments or main blocks)
                if ('print(' in line and 
                    not line.strip().startswith('#') and 
                    'if __name__' not in ''.join(lines[max(0, i-5):i+1])):
                    files_with_prints.append(f"{file_path}:{i+1}")
                    break
        
        # Just warn for now since some prints might be intentional
        if files_with_prints:
            print(f"\n⚠️  Found print statements (consider using logging): {len(files_with_prints)} files")
            for item in files_with_prints[:3]:
                print(f"  {item}")
            if len(files_with_prints) > 3:
                print(f"  ... and {len(files_with_prints) - 3} more")
    
    def test_bare_except_clauses(self):
        """Test for dangerous bare except clauses"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        bare_except_files = []
        
        for file_path in python_files:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Look for bare except: clauses
                if stripped == 'except:' or stripped.startswith('except:'):
                    bare_except_files.append(f"{file_path}:{i+1}")
        
        assert not bare_except_files, f"Found dangerous bare except clauses: {bare_except_files}"
    
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
            print(f"\n⚠️  Found import style issues: {len(import_issues)} files")
            for issue in import_issues[:3]:
                print(f"  {issue}")
    
    def test_long_functions_and_files(self):
        """Test for overly long functions and files that might need refactoring"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        long_items = []
        
        for file_path in python_files:
            # Skip test files for this check
            if 'test' in str(file_path):
                continue
                
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Check file length
            if len(lines) > 600:
                long_items.append(f"{file_path}: {len(lines)} lines (consider splitting)")
            
            # Check for very long functions (basic heuristic)
            in_function = False
            function_start = 0
            function_name = ""
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('def ') and not stripped.startswith('def __'):
                    if in_function and i - function_start > 100:
                        long_items.append(f"{file_path}:{function_start} function '{function_name}' is {i - function_start} lines")
                    
                    in_function = True
                    function_start = i
                    function_name = stripped.split('(')[0].replace('def ', '')
                elif stripped.startswith('class '):
                    in_function = False
                elif not stripped and in_function:
                    # End of function on double newline or class
                    continue
        
        # Just warn about long items
        if long_items:
            print(f"\n⚠️  Found {len(long_items)} long files/functions that might need refactoring:")
            for item in long_items[:3]:
                print(f"  {item}")
            if len(long_items) > 3:
                print(f"  ... and {len(long_items) - 3} more")
    
    def test_database_connection_patterns(self):
        """Test for proper database connection management"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        db_issues = []
        
        for file_path in python_files:
            content = file_path.read_text()
            
            # Look for direct sqlite3.connect calls (should use DatabaseManager)
            if 'sqlite3.connect' in content and 'database.py' not in str(file_path):
                db_issues.append(f"{file_path}: Direct sqlite3.connect (use DatabaseManager)")
            
            # Look for hardcoded database paths
            db_path_patterns = ['.memos/database.db', '/Users/paulrohde/AutoTaskTracker.memos/', 'database.db']
            for pattern in db_path_patterns:
                # Exclude config files and pensieve modules which legitimately interface with memos defaults
                if (pattern in content and 
                    'config.py' not in str(file_path) and 
                    'pensieve/' not in str(file_path)):
                    db_issues.append(f"{file_path}: Hardcoded DB path '{pattern}' (use config)")
                    break
        
        assert not db_issues, f"Found database connection issues: {db_issues}"
    
    def test_streamlit_anti_patterns(self):
        """Test for Streamlit anti-patterns and code duplication"""
        streamlit_files = []
        for file_path in self.get_python_files():
            content = file_path.read_text()
            if 'streamlit' in content and 'st.' in content:
                streamlit_files.append(file_path)
        
        if len(streamlit_files) < 2:
            return  # No point checking with so few files
        
        anti_patterns = []
        
        # Check for repeated st.set_page_config patterns
        page_configs = []
        for file_path in streamlit_files:
            content = file_path.read_text()
            if 'st.set_page_config(' in content:
                page_configs.append(str(file_path))
        
        if len(page_configs) > 3:
            anti_patterns.append(f"Repeated st.set_page_config in {len(page_configs)} files (consider shared function)")
        
        # Check for st.cache usage (deprecated)
        cache_usage = []
        for file_path in streamlit_files:
            content = file_path.read_text()
            if '@st.cache' in content and '@st.cache_data' not in content:
                cache_usage.append(str(file_path))
        
        if cache_usage:
            anti_patterns.append(f"Deprecated @st.cache usage: {cache_usage}")
        
        # Just warn about Streamlit anti-patterns
        if anti_patterns:
            print(f"\n⚠️  Found Streamlit anti-patterns:")
            for pattern in anti_patterns:
                print(f"  {pattern}")
    
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
            print(f"\n⚠️  Potential circular imports detected:")
            for cycle in potential_cycles[:3]:
                print(f"  {cycle}")
    
    def test_naming_conventions(self):
        """Test for consistent naming conventions"""
        python_files = [f for f in self.get_python_files() if 'autotasktracker' in str(f)]
        naming_issues = []
        
        for file_path in python_files:
            filename = file_path.name
            
            # Python files should be snake_case
            if filename.endswith('.py'):
                base_name = filename[:-3]
                if any(c.isupper() for c in base_name) and '_' not in base_name:
                    # Might be camelCase
                    naming_issues.append(f"{file_path}: filename should be snake_case")
            
            # Check for inconsistent function/class naming in content
            content = file_path.read_text()
            lines = content.split('\n')
            
            for line in lines:
                stripped = line.strip()
                # Check class names (should be PascalCase)
                if stripped.startswith('class ') and '(' in stripped:
                    class_name = stripped.split('(')[0].replace('class ', '').strip()
                    if '_' in class_name or class_name.islower():
                        naming_issues.append(f"{file_path}: class '{class_name}' should be PascalCase")
                        break
        
        # Just warn about naming issues
        if naming_issues:
            print(f"\n⚠️  Found naming convention issues:")
            for issue in naming_issues[:3]:
                print(f"  {issue}")
            if len(naming_issues) > 3:
                print(f"  ... and {len(naming_issues) - 3} more")
    
    def test_incomplete_refactoring(self):
        """Test for incomplete refactoring - find old files that should be removed after refactoring"""
        refactoring_issues = []
        
        # Check for pairs of original and refactored files
        dashboard_dir = self.package_dir / "dashboards"
        if dashboard_dir.exists():
            dashboard_files = list(dashboard_dir.glob("*.py"))
            
            # Find files with _refactored suffix
            refactored_files = [f for f in dashboard_files if "_refactored.py" in f.name]
            
            for refactored_file in refactored_files:
                # Check if original file still exists
                original_name = refactored_file.name.replace("_refactored.py", ".py")
                original_file = dashboard_dir / original_name
                
                if original_file.exists():
                    # Check if both files have similar sizes (indicating duplication)
                    refactored_size = refactored_file.stat().st_size
                    original_size = original_file.stat().st_size
                    
                    refactoring_issues.append({
                        'original': str(original_file),
                        'refactored': str(refactored_file),
                        'original_size': original_size,
                        'refactored_size': refactored_size,
                        'message': f"Both original and refactored versions exist for {original_name}"
                    })
        
        # Check for legacy files that might need cleanup
        legacy_patterns = [
            "*_old.py",
            "*_backup.py",
            "*_deprecated.py",
            "*_legacy.py",
            "*.bak",
            "*_temp.py"
        ]
        
        for pattern in legacy_patterns:
            legacy_files = list(self.project_root.glob(f"**/{pattern}"))
            for legacy_file in legacy_files:
                if 'venv' not in str(legacy_file) and '__pycache__' not in str(legacy_file):
                    refactoring_issues.append({
                        'file': str(legacy_file),
                        'message': f"Legacy file pattern detected: {legacy_file.name}"
                    })
        
        # Check scripts directory for duplicate functionality
        scripts_dir = self.project_root / "scripts"
        if scripts_dir.exists():
            # Group scripts by similar names
            script_groups = {}
            for script in scripts_dir.glob("*.py"):
                # Extract base name (e.g., "vlm_processor" from "vlm_processor.py")
                base_name = script.stem
                
                # Check for similar scripts (e.g., vlm_processor, vlm_processing_service, vlm_manager)
                for key in script_groups:
                    if key in base_name or base_name in key:
                        script_groups[key].append(script)
                        break
                else:
                    script_groups[base_name] = [script]
            
            # Flag groups with multiple similar scripts
            for base, scripts in script_groups.items():
                if len(scripts) > 1:
                    refactoring_issues.append({
                        'scripts': [str(s) for s in scripts],
                        'message': f"Multiple scripts with similar names found: {base}"
                    })
        
        # Generate detailed report
        if refactoring_issues:
            print("\n🚨 INCOMPLETE REFACTORING DETECTED 🚨")
            print(f"Found {len(refactoring_issues)} issues that need cleanup:\n")
            
            # Group by type
            dashboard_issues = [i for i in refactoring_issues if 'original' in i]
            legacy_issues = [i for i in refactoring_issues if 'file' in i]
            script_issues = [i for i in refactoring_issues if 'scripts' in i]
            
            if dashboard_issues:
                print("📊 Dashboard Refactoring Issues:")
                for issue in dashboard_issues:
                    print(f"  - {issue['message']}")
                    print(f"    Original: {issue['original_size']} bytes")
                    print(f"    Refactored: {issue['refactored_size']} bytes")
                print()
            
            if legacy_issues:
                print("🗑️  Legacy Files to Remove:")
                for issue in legacy_issues:
                    print(f"  - {issue['file']}")
                print()
            
            if script_issues:
                print("📜 Duplicate Scripts:")
                for issue in script_issues:
                    print(f"  - {issue['message']}")
                    for script in issue['scripts']:
                        print(f"    • {script}")
                print()
        
        assert not refactoring_issues, f"Found {len(refactoring_issues)} incomplete refactoring issues"


if __name__ == "__main__":
    # Run tests
    test = TestCodebaseHealth()
    # Manually set up the test environment
    test.project_root = Path(__file__).parent.parent
    test.package_dir = test.project_root / "autotasktracker"
    
    print("Running codebase health checks...\n")
    
    # Run each test
    tests = [
        ("Duplicate/improved files", test.test_no_duplicate_improved_files),
        ("sys.path hacks", test.test_no_sys_path_hacks),
        ("Duplicate functions", test.test_no_duplicate_functions),
        ("Import validity", test.test_imports_are_valid),
        ("Hardcoded paths", test.test_no_hardcoded_paths),
        ("Debug code", test.test_no_debug_code),
        ("TODOs/FIXMEs", test.test_no_todos_or_fixmes),
        ("Unused imports", test.test_no_unused_imports),
        ("File permissions", test.test_file_permissions),
        ("Large files", test.test_no_large_files),
        ("Line endings", test.test_consistent_line_endings),
        ("Merge conflicts", test.test_no_merge_conflicts),
        ("Legacy folder awareness", test.test_legacy_folder_awareness),
        ("Root directory clutter", test.test_root_directory_clutter),
        ("Redundant documentation", test.test_redundant_documentation),
        ("Stray log files", test.test_stray_log_files),
        ("Duplicate modules", test.test_no_duplicate_modules),
        ("Print vs logging", test.test_print_statements_vs_logging),
        ("Bare except clauses", test.test_bare_except_clauses),
        ("Import style", test.test_consistent_import_style),
        ("Long functions/files", test.test_long_functions_and_files),
        ("Database patterns", test.test_database_connection_patterns),
        ("Streamlit anti-patterns", test.test_streamlit_anti_patterns),
        ("Circular imports", test.test_circular_imports),
        ("Naming conventions", test.test_naming_conventions),
        ("Incomplete refactoring", test.test_incomplete_refactoring),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {test_name}: Error - {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed}")
    print(f"{'='*50}")
    
    if failed > 0:
        exit(1)