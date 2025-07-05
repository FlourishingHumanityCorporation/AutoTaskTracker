"""
Database access pattern analyzer for health tests.

Analyzes code for proper database usage patterns including:
- Direct SQLite access detection
- Transaction management
- Connection pooling
- N+1 query patterns
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class DatabaseAccessAnalyzer:
    """Analyzer for database access patterns."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def analyze_sqlite_access(self, file_path: Path) -> List[str]:
        """Detect direct SQLite access to ANY database (should use DatabaseManager)."""
        violations = []
        
        # Patterns that indicate direct SQLite access
        sqlite_patterns = [
            r'sqlite3\.connect\s*\(',  # ANY sqlite3.connect usage
            r'conn\s*=\s*sqlite3\.connect',
            r'connection\s*=\s*sqlite3\.connect',
            r'db\s*=\s*sqlite3\.connect',
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Skip test files, tools, DatabaseManager, and certain legitimate low-level access
            skip_patterns = [
                ('tests/' in str(file_path) and 'test_' in file_path.name),  # Test files
                file_path.name == 'database.py',  # DatabaseManager itself
                '/tools/' in str(file_path),  # Development tools
                'inspector' in file_path.name,  # Database inspection tools
                'migration' in file_path.name,  # Database migration scripts
                'setup' in file_path.name,  # Setup scripts
            ]
            
            if any(skip_patterns):
                return violations
                
            for pattern in sqlite_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Find the actual line for better reporting
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(f"{file_path}:{i+1} - {line.strip()}")
                    break
                    
        except Exception as e:
            logger.warning(f"Error analyzing {file_path}: {e}")
        
        return violations
    
    def analyze_transaction_management(self, file_path: Path) -> List[Dict]:
        """Analyze functions for proper transaction management."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            # Parse with AST for better accuracy
            try:
                tree = ast.parse(content)
            except:
                return issues
                
            # Find functions with multiple DB operations
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_start = node.lineno
                    func_end = node.end_lineno if hasattr(node, 'end_lineno') else func_start + 50
                    func_lines = lines[func_start-1:func_end]
                    func_content = '\n'.join(func_lines)
                    
                    # Count database operations
                    db_ops = []
                    patterns = [
                        (r'store_metadata\s*\([^)]+\)', 'store_metadata'),
                        (r'\.execute\s*\([^)]+\)', 'execute'),
                        (r'\.executemany\s*\([^)]+\)', 'executemany'),
                        (r'INSERT\s+INTO', 'INSERT'),
                        (r'UPDATE\s+\w+\s+SET', 'UPDATE'),
                        (r'DELETE\s+FROM', 'DELETE'),
                    ]
                    
                    for pattern, op_type in patterns:
                        matches = list(re.finditer(pattern, func_content, re.IGNORECASE))
                        for match in matches:
                            line_offset = func_content[:match.start()].count('\n')
                            db_ops.append({
                                'type': op_type,
                                'line': func_start + line_offset,
                                'pos': match.start()
                            })
                    
                    # Check if multiple write operations without transaction
                    write_ops = [op for op in db_ops if op['type'] in ['store_metadata', 'INSERT', 'UPDATE', 'DELETE']]
                    
                    if len(write_ops) >= 2:
                        # Check if they're wrapped in a transaction
                        transaction_patterns = [
                            r'with\s+.*get_connection',
                            r'begin_transaction',
                            r'conn\.begin\(\)',
                            r'START\s+TRANSACTION',
                            r'BEGIN\s+TRANSACTION',
                            r'db\.transaction',
                            r'atomic\(',
                        ]
                        
                        has_transaction = any(re.search(p, func_content, re.IGNORECASE) for p in transaction_patterns)
                        
                        if not has_transaction:
                            issues.append({
                                'file': file_path,
                                'function': node.name,
                                'line': func_start,
                                'operations': len(write_ops),
                                'first_op': write_ops[0]
                            })
                        
        except Exception as e:
            logger.warning(f"Error analyzing transactions in {file_path}: {e}")
        
        return issues
    
    def analyze_connection_pooling(self, file_path: Path) -> List[Dict]:
        """Analyze connection pooling usage patterns."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Skip DatabaseManager itself
            if 'database.py' in str(file_path) and 'core' in str(file_path):
                return issues
                
            # Count instantiations in functions
            functions = re.findall(r'def\s+\w+[^:]+:.*?(?=\ndef|\nclass|\Z)', content, re.DOTALL)
            
            for func in functions:
                db_instantiations = len(re.findall(r'DatabaseManager\s*\(\)', func))
                if db_instantiations > 1:
                    func_name = re.search(r'def\s+(\w+)', func).group(1)
                    issues.append({
                        'file': file_path,
                        'function': func_name,
                        'count': db_instantiations,
                        'issue': 'Multiple DatabaseManager instances in function'
                    })
                    
        except Exception as e:
            logger.warning(f"Error analyzing connection pooling in {file_path}: {e}")
        
        return issues


def analyze_file_for_n_plus_one(file_path: Path) -> List[Dict]:
    """Analyze a single file for N+1 query patterns."""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if no database operations
        if not any(pattern in content for pattern in ['fetch', 'query', 'select', 'SELECT']):
            return issues
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return issues
        
        # Look for loops with database calls
        class LoopVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_loop = False
                self.loop_line = 0
                self.issues = []
            
            def visit_For(self, node):
                old_in_loop = self.in_loop
                old_loop_line = self.loop_line
                self.in_loop = True
                self.loop_line = node.lineno
                self.generic_visit(node)
                self.in_loop = old_in_loop
                self.loop_line = old_loop_line
            
            def visit_While(self, node):
                old_in_loop = self.in_loop
                old_loop_line = self.loop_line
                self.in_loop = True
                self.loop_line = node.lineno
                self.generic_visit(node)
                self.in_loop = old_in_loop
                self.loop_line = old_loop_line
            
            def visit_Call(self, node):
                if self.in_loop:
                    # Check if this is a database call
                    call_str = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                    db_patterns = ['fetch', 'query', 'get', 'select', 'execute']
                    
                    if any(pattern in call_str.lower() for pattern in db_patterns):
                        # Extract the actual line
                        lines = content.split('\n')
                        if node.lineno <= len(lines):
                            self.issues.append({
                                'line': node.lineno,
                                'loop_line': self.loop_line,
                                'code': lines[node.lineno - 1].strip()
                            })
                
                self.generic_visit(node)
        
        visitor = LoopVisitor()
        visitor.visit(tree)
        issues = visitor.issues
        
    except Exception:
        pass
    
    return issues


def analyze_bulk_operations(file_path: Path) -> List[str]:
    """Analyze file for bulk operation opportunities."""
    opportunities = []
    
    # Look for loops with database operations
    loop_db_patterns = [
        r'for\s+.*in.*:\s*\n.*store_metadata',
        r'for\s+.*in.*:\s*\n.*get_metadata',
        r'while.*:\s*\n.*fetch_tasks',
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in loop_db_patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                opportunities.append(str(file_path))
                break
                
    except Exception:
        pass
    
    return opportunities


def analyze_index_usage(file_path: Path) -> List[Dict]:
    """Analyze queries for index optimization opportunities."""
    issues = []
    
    # SQL patterns that might need indexes
    query_patterns = [
        # WHERE without entities.id (primary key)
        (r'WHERE\s+(?!e\.id|entity_id\s*=)[^;]+', 'WHERE clause on non-indexed column'),
        # ORDER BY without index
        (r'ORDER\s+BY\s+(?!e\.created_at|e\.id)[^;]+', 'ORDER BY on potentially non-indexed column'),
        # JOIN on non-foreign key
        (r'JOIN.*ON\s+(?!.*\.id\s*=)[^;]+', 'JOIN on potentially non-indexed column'),
        # GROUP BY
        (r'GROUP\s+BY\s+[^;]+', 'GROUP BY might benefit from index'),
        # LIKE queries
        (r'WHERE.*LIKE\s+["\']%', 'LIKE query with leading wildcard'),
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find SQL queries
        sql_queries = re.findall(r'"""[^"]*(?:SELECT|INSERT|UPDATE|DELETE)[^"]*"""', content, re.DOTALL)
        sql_queries.extend(re.findall(r"'''[^']*(?:SELECT|INSERT|UPDATE|DELETE)[^']*'''", content, re.DOTALL))
        sql_queries.extend(re.findall(r'"(?:SELECT|INSERT|UPDATE|DELETE)[^"]*"', content))
        
        for query in sql_queries:
            for pattern, description in query_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    line_no = content.find(query).count('\n') + 1
                    issues.append({
                        'file': file_path,
                        'line': line_no,
                        'issue': description,
                        'query': query[:100].replace('\n', ' ')
                    })
                    
    except Exception:
        pass
    
    return issues