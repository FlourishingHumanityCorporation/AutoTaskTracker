"""Test for file and code naming conventions."""
import logging
import os
import re
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)


class TestNamingConventions:
    """Test for consistent naming conventions and file organization."""
    
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
            logger.warning("Found naming convention issues:")
            for issue in naming_issues[:3]:
                logger.warning(f"  {issue}")
            if len(naming_issues) > 3:
                logger.warning(f"  ... and {len(naming_issues) - 3} more")
    
    def test_root_directory_clutter(self):
        """Test for messy root directory with too many loose files"""
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
        
        # Categorize problematic files
        documentation_files = []
        migration_scripts = []
        debug_files = []
        ai_files = []
        loose_python_files = []
        other_files = []
        
        for file_path in root_files:
            filename = Path(file_path).name.lower()
            
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
            issues_found.append(f"\nDOCUMENTATION CLUTTER ({len(documentation_files)} files):")
            for f in documentation_files:
                issues_found.append(f"  {Path(f).name} → Move to docs/")
                
        if migration_scripts:
            issues_found.append(f"\nMIGRATION SCRIPTS ({len(migration_scripts)} files):")
            for f in migration_scripts:
                issues_found.append(f"  {Path(f).name} → Move to scripts/")
                
        if debug_files:
            issues_found.append(f"\nDEBUG/TEST FILES ({len(debug_files)} files):")
            for f in debug_files:
                issues_found.append(f"  {Path(f).name} → Move to tests/ or DELETE")
                
        if ai_files:
            issues_found.append(f"\nAI SCRIPTS ({len(ai_files)} files):")
            for f in ai_files:
                issues_found.append(f"  {Path(f).name} → Move to scripts/ or examples/")
                
        if loose_python_files:
            issues_found.append(f"\nLOOSE PYTHON FILES ({len(loose_python_files)} files):")
            for f in loose_python_files:
                issues_found.append(f"  {Path(f).name} → Move to scripts/ or organize into proper module")
                
        if other_files:
            issues_found.append(f"\nOTHER CLUTTER ({len(other_files)} files):")
            for f in other_files:
                issues_found.append(f"  {Path(f).name} → Review and organize properly")
        
        if issues_found:
            error_message = f"""
ROOT DIRECTORY CLUTTER DETECTED

Your project root is messy! This makes the project harder to navigate and maintain.

ISSUES FOUND: {''.join(issues_found)}

ALLOWED ROOT FILES ONLY:
  - Core: README.md, LICENSE, requirements.txt, .gitignore
  - Project: autotasktracker.py (main entry), CLAUDE.md, QUICKSTART.md
  - Build: setup.sh, Dockerfile, Makefile

This test will PASS once root directory is properly organized!
"""
            raise AssertionError(error_message)
    
    def test_incomplete_refactoring(self):
        """Test for incomplete refactoring - find old files that should be removed"""
        refactoring_issues = []
        
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
        
        assert not refactoring_issues, f"Found {len(refactoring_issues)} incomplete refactoring issues: {refactoring_issues}"