"""
Common test helper functions and utilities.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def safe_read_file(file_path: Path, max_size: int = 1024 * 1024) -> str:
    """Safely read file content with size limits to prevent hanging."""
    try:
        # Check file size first
        if file_path.stat().st_size > max_size:
            return ""  # Skip large files
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Also limit by line count to prevent hanging on very long lines
        lines = content.split('\n')
        if len(lines) > 10000:  # Max 10k lines
            content = '\n'.join(lines[:10000])
            
        return content
    except (OSError, UnicodeDecodeError, MemoryError):
        return ""  # Return empty string on any read error


def parse_python_file(file_path: Path) -> Optional[ast.AST]:
    """Safely parse a Python file, returning None if parsing fails."""
    try:
        content = safe_read_file(file_path)
        if not content:
            return None
        return ast.parse(content)
    except SyntaxError:
        logger.debug(f"Syntax error parsing {file_path}")
        return None
    except Exception as e:
        logger.debug(f"Error parsing {file_path}: {e}")
        return None


def extract_functions(tree: ast.AST) -> List[ast.FunctionDef]:
    """Extract all function definitions from an AST."""
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node)
    return functions


def extract_classes(tree: ast.AST) -> List[ast.ClassDef]:
    """Extract all class definitions from an AST."""
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node)
    return classes


def extract_imports(tree: ast.AST) -> Dict[str, List[str]]:
    """Extract all imports from an AST."""
    imports = {
        'standard': [],  # import module
        'from': []       # from module import name
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports['standard'].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports['from'].append(f"from {module} import {alias.name}")
    
    return imports


def find_pattern_in_file(file_path: Path, patterns: List[str], case_sensitive: bool = True) -> List[Dict[str, Any]]:
    """Find regex patterns in a file and return matches with line numbers."""
    content = safe_read_file(file_path)
    if not content:
        return []
    
    matches = []
    lines = content.split('\n')
    
    for pattern in patterns:
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for line_num, line in enumerate(lines, 1):
            match = re.search(pattern, line, flags)
            if match:
                matches.append({
                    'pattern': pattern,
                    'line': line_num,
                    'match': match.group(0),
                    'context': line.strip()
                })
    
    return matches


def count_lines_of_code(file_path: Path, exclude_comments: bool = True, exclude_docstrings: bool = True) -> int:
    """Count lines of code in a Python file."""
    content = safe_read_file(file_path)
    if not content:
        return 0
    
    lines = content.split('\n')
    count = 0
    
    in_multiline_string = False
    string_delimiter = None
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
        
        # Skip comments if requested
        if exclude_comments and stripped.startswith('#'):
            continue
        
        # Handle multiline strings (docstrings)
        if exclude_docstrings:
            # Check for start of multiline string
            if not in_multiline_string:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    string_delimiter = stripped[:3]
                    in_multiline_string = True
                    if stripped.endswith(string_delimiter) and len(stripped) > 3:
                        in_multiline_string = False
                    continue
            else:
                # In multiline string, check for end
                if string_delimiter in stripped:
                    in_multiline_string = False
                continue
        
        count += 1
    
    return count


def analyze_complexity(tree: ast.AST) -> Dict[str, int]:
    """Analyze basic complexity metrics of a Python AST."""
    metrics = {
        'functions': 0,
        'classes': 0,
        'if_statements': 0,
        'loops': 0,
        'try_blocks': 0
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            metrics['functions'] += 1
        elif isinstance(node, ast.ClassDef):
            metrics['classes'] += 1
        elif isinstance(node, ast.If):
            metrics['if_statements'] += 1
        elif isinstance(node, (ast.For, ast.While)):
            metrics['loops'] += 1
        elif isinstance(node, ast.Try):
            metrics['try_blocks'] += 1
    
    return metrics


def check_file_health(file_path: Path) -> Dict[str, Any]:
    """Perform basic health checks on a file."""
    health = {
        'readable': False,
        'parseable': False,
        'size_kb': 0,
        'line_count': 0,
        'loc': 0,
        'complexity': {}
    }
    
    try:
        # Check if file is readable
        content = safe_read_file(file_path)
        if content:
            health['readable'] = True
            health['size_kb'] = len(content.encode('utf-8')) / 1024
            health['line_count'] = len(content.split('\n'))
            health['loc'] = count_lines_of_code(file_path)
        
        # Check if file is parseable
        tree = parse_python_file(file_path)
        if tree:
            health['parseable'] = True
            health['complexity'] = analyze_complexity(tree)
    
    except Exception as e:
        logger.debug(f"Error checking health of {file_path}: {e}")
    
    return health