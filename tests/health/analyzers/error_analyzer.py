"""
Error handling pattern analyzer for health tests.

Analyzes code for proper error handling patterns including:
- Bare except clauses
- Print statements in error handlers
- Silent exception handling
- Retry logic implementation
- File operation validation
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingAnalyzer:
    """Analyzer for error handling patterns."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def analyze_error_patterns(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """Analyze file for error handling issues."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            in_except_block = False
            except_start_line = 0
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                
                # Track except blocks
                if re.match(r'except\s*:', stripped):
                    issues.append((i, "bare_except", stripped))
                    in_except_block = True
                    except_start_line = i
                elif re.match(r'except\s+\w+', stripped):
                    in_except_block = True
                    except_start_line = i
                elif in_except_block and not line.startswith((' ', '\t')):
                    in_except_block = False
                
                # Check for issues in except blocks
                if in_except_block:
                    if 'print(' in line and 'Error' in line:
                        issues.append((i, "print_in_except", stripped))
                    elif stripped == 'pass':
                        issues.append((i, "silent_pass", stripped))
        
        except Exception as e:
            logger.warning(f"Error analyzing error patterns in {file_path}: {e}")
        
        return issues
    
    def analyze_retry_logic(self, file_path: Path) -> List[Dict]:
        """Analyze retry logic implementation."""
        retry_issues = []
        
        # Look for retry implementations
        retry_patterns = [
            r'@retry',
            r'retry\(',
            r'exponential_backoff',
            r'with.*retry',
            r'max_retries',
            r'retry_count',
        ]
        
        # Look for places that SHOULD have retry logic
        needs_retry_patterns = [
            (r'requests\.(get|post|put)', 'HTTP requests'),
            (r'ollama.*api', 'Ollama API calls'),
            (r'vlm.*call', 'VLM processing'),
            (r'session\.(get|post)', 'Session requests'),
            (r'\.connect\(.*timeout', 'Network connections'),
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if file has retry logic
            has_retry = any(re.search(pattern, content) for pattern in retry_patterns)
            
            # Check if file needs retry logic
            for pattern, description in needs_retry_patterns:
                if re.search(pattern, content) and not has_retry:
                    retry_issues.append({
                        'file': file_path,
                        'reason': description,
                        'has_retry': False
                    })
                    
        except Exception as e:
            logger.warning(f"Error analyzing retry logic in {file_path}: {e}")
        
        return retry_issues
    
    def analyze_file_operations(self, file_path: Path) -> List[Dict]:
        """Analyze file operations for proper validation."""
        validation_issues = []
        
        # Patterns for file operations that need validation
        file_operations = [
            (r'\bopen\s*\(\s*([^,\)]+)', 'file open', True),
            (r'Image\.open\s*\(\s*([^,\)]+)', 'image open', True),
            (r'pd\.read_csv\s*\(\s*([^,\)]+)', 'CSV read', True),
            (r'Path\s*\(\s*([^)]+)\)\.read_text', 'file read', True),
            (r'\.write\s*\([^)]+\)', 'file write', False),
            (r'os\.remove\s*\(\s*([^)]+)\)', 'file delete', True),
            (r'shutil\.rmtree\s*\(\s*([^)]+)\)', 'directory delete', True),
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the file with AST for better accuracy
            try:
                tree = ast.parse(content)
            except:
                return validation_issues
                
            # Find all function definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_start = node.lineno
                    func_end = node.end_lineno if hasattr(node, 'end_lineno') else func_start + 20
                    func_lines = content.split('\n')[func_start-1:func_end]
                    func_content = '\n'.join(func_lines)
                    
                    for pattern, operation, needs_validation in file_operations:
                        matches = list(re.finditer(pattern, func_content))
                        for match in matches:
                            if not needs_validation:
                                continue
                                
                            # Check if the file path is a literal or variable
                            file_arg = match.group(1) if match.lastindex else ''
                            
                            # Skip if it's a hardcoded safe path
                            if any(safe in file_arg for safe in ['/dev/null', 'sys.stdout', 'sys.stderr']):
                                continue
                            
                            # Get context around the operation
                            match_line = func_content[:match.start()].count('\n')
                            context_start = max(0, match_line - 10)
                            context_end = min(len(func_lines), match_line + 5)
                            context = '\n'.join(func_lines[context_start:context_end])
                            
                            # Check for validation patterns
                            validation_patterns = [
                                r'os\.path\.exists',
                                r'Path\(.*\)\.exists',
                                r'\.exists\(\)',
                                r'os\.access',
                                r'try:',
                                r'if\s+.*exists',
                                r'isfile',
                                r'is_file',
                                r'pathlib',
                                r'with\s+suppress',
                            ]
                            
                            has_validation = any(re.search(vp, context, re.IGNORECASE) for vp in validation_patterns)
                            
                            # Also check if it's wrapped in a try block
                            if 'try:' in context and match_line > context.find('try:'):
                                has_validation = True
                            
                            if not has_validation:
                                validation_issues.append({
                                    'file': file_path,
                                    'line': func_start + match_line,
                                    'function': node.name,
                                    'operation': operation,
                                    'code': match.group(0).strip()
                                })
                        
        except Exception as e:
            logger.warning(f"Error analyzing file operations in {file_path}: {e}")
        
        return validation_issues


def analyze_file_for_error_handling(file_path: Path) -> List[Tuple[int, str, str]]:
    """Analyze a single file for error handling issues."""
    analyzer = ErrorHandlingAnalyzer(file_path.parent)
    return analyzer.analyze_error_patterns(file_path)