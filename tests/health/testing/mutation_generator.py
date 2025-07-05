"""Mutation generation module - extracts mutation creation logic from SimpleMutationTester.

This module is responsible for generating various types of mutations for testing.
"""

import ast
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum

from .shared_utilities import CompiledPatterns
from .constants import MutationTestingLimits

logger = logging.getLogger(__name__)


class MutationType(Enum):
    """Types of mutations that represent common bugs."""
    OFF_BY_ONE = "off_by_one"          # >, < become >=, <=
    BOOLEAN_FLIP = "boolean_flip"       # True/False flip
    OPERATOR_CHANGE = "operator_change" # +, -, *, / changes
    CONDITION_FLIP = "condition_flip"   # and/or flip
    RETURN_VALUE = "return_value"       # None, 0, empty returns
    RANGE_BOUNDARY = "range_boundary"   # range(n) -> range(n+1)
    EXCEPTION_HANDLING = "exception_handling"  # except: -> specific exceptions
    
    # New enhanced mutation types for AutoTaskTracker
    NULL_CHECK = "null_check"           # Remove None checks
    STRING_EMPTY = "string_empty"       # "" -> "test", strip() removal
    LIST_EMPTY = "list_empty"           # [] -> [item], empty checks
    DATABASE_TRANSACTION = "db_transaction"  # commit() removal, rollback() changes
    TIMEOUT_VALUE = "timeout_value"     # timeout values changes
    RETRY_COUNT = "retry_count"         # max_retries changes
    LOG_LEVEL = "log_level"            # DEBUG -> ERROR level changes
    CONFIG_VALUE = "config_value"       # Default config value changes
    ASYNC_AWAIT = "async_await"         # Remove await keywords
    PENSIEVE_API = "pensieve_api"       # API fallback logic changes


class MutationGenerator:
    """Generates mutations for source files to test effectiveness."""
    
    def __init__(self, max_mutations_per_file: Optional[int] = None):
        limits = MutationTestingLimits()
        self.max_mutations_per_file = max_mutations_per_file or limits.MAX_MUTATIONS_PER_FILE
        
    def generate_mutations(self, source_file: Path) -> List[Dict]:
        """Generate smart mutations based on code patterns in source file.
        
        Args:
            source_file: Path to the source file to mutate
            
        Returns:
            List of mutation dictionaries with keys:
            - type: MutationType
            - line: Line number (0-indexed)
            - original: Original code
            - mutated: Mutated code
            - description: Human-readable description
        """
        try:
            content = source_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Failed to read source file {source_file}: {type(e).__name__}: {e}")
            return []
            
        mutations = []
        lines = content.split('\n')
        
        # Parse AST for better mutation targeting
        try:
            tree = ast.parse(content)
            mutations.extend(self._generate_ast_mutations(tree, lines))
        except SyntaxError as e:
            logger.warning(f"Could not parse {source_file} AST: {e}")
        
        # Pattern-based mutations
        mutations.extend(self._generate_off_by_one_mutations(lines))
        mutations.extend(self._generate_boolean_mutations(lines))
        mutations.extend(self._generate_operator_mutations(lines))
        mutations.extend(self._generate_boundary_mutations(lines))
        
        # Enhanced mutations for AutoTaskTracker
        mutations.extend(self._generate_null_check_mutations(lines))
        mutations.extend(self._generate_string_empty_mutations(lines))
        mutations.extend(self._generate_list_empty_mutations(lines))
        mutations.extend(self._generate_database_mutations(lines))
        mutations.extend(self._generate_timeout_mutations(lines))
        mutations.extend(self._generate_retry_mutations(lines))
        mutations.extend(self._generate_log_level_mutations(lines))
        mutations.extend(self._generate_config_mutations(lines))
        mutations.extend(self._generate_async_mutations(lines))
        mutations.extend(self._generate_pensieve_mutations(lines))
        
        # Limit number of mutations
        if len(mutations) > self.max_mutations_per_file:
            mutations = mutations[:self.max_mutations_per_file]
            
        return mutations
    
    def _generate_ast_mutations(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Generate mutations based on AST analysis."""
        mutations = []
        
        for node in ast.walk(tree):
            # Return value mutations
            if isinstance(node, ast.Return) and hasattr(node, 'lineno'):
                line_idx = node.lineno - 1
                if line_idx < len(lines):
                    original = lines[line_idx].strip()
                    
                    # Mutate return values
                    if 'return None' not in original and 'return' in original:
                        mutated = re.sub(r'return\s+(.+)', 'return None', original)
                        if mutated != original:
                            mutations.append({
                                'type': MutationType.RETURN_VALUE.value,
                                'line': line_idx,
                                'original': original,
                                'mutated': mutated,
                                'description': 'Change return value to None'
                            })
        
        return mutations
    
    def _generate_off_by_one_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate off-by-one error mutations."""
        mutations = []
        
        for i, line in enumerate(lines):
            # Skip comments and empty lines
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            # Find comparison operators
            if CompiledPatterns.OFF_BY_ONE.search(line):
                original = line.strip()
                mutated = original
                
                # Replace > with >=, < with <=
                mutated = re.sub(r'(?<![<>=])<(?![<>=])', '<=', mutated)
                mutated = re.sub(r'(?<![<>=])>(?![<>=])', '>=', mutated)
                
                if mutated != original:
                    mutations.append({
                        'type': MutationType.OFF_BY_ONE.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Off-by-one comparison mutation'
                    })
        
        return mutations
    
    def _generate_boolean_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate boolean value mutations."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # True/False mutations
            if 'True' in original:
                mutated = original.replace('True', 'False')
                mutations.append({
                    'type': MutationType.BOOLEAN_FLIP.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Boolean True->False mutation'
                })
            elif 'False' in original:
                mutated = original.replace('False', 'True')
                mutations.append({
                    'type': MutationType.BOOLEAN_FLIP.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Boolean False->True mutation'
                })
            
            # and/or mutations
            if CompiledPatterns.BOOLEAN_LOGIC.search(original):
                mutated = re.sub(r'\s+and\s+', ' or ', original)
                if mutated == original:
                    mutated = re.sub(r'\s+or\s+', ' and ', original)
                    
                if mutated != original:
                    mutations.append({
                        'type': MutationType.CONDITION_FLIP.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Boolean operator mutation'
                    })
        
        return mutations
    
    def _generate_operator_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate arithmetic operator mutations."""
        mutations = []
        
        operator_map = {
            '+': '-',
            '-': '+',
            '*': '/',
            '/': '*'
        }
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Look for arithmetic operations
            for op, replacement in operator_map.items():
                if f' {op} ' in original:
                    mutated = original.replace(f' {op} ', f' {replacement} ')
                    mutations.append({
                        'type': MutationType.OPERATOR_CHANGE.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': f'Operator {op} -> {replacement} mutation'
                    })
                    break  # Only one mutation per line
        
        return mutations
    
    def _generate_boundary_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate boundary condition mutations."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # range() mutations
            range_match = re.search(r'range\((\d+)\)', original)
            if range_match:
                try:
                    value = int(range_match.group(1))
                    mutated = original.replace(f'range({value})', f'range({value + 1})')
                    mutations.append({
                        'type': MutationType.RANGE_BOUNDARY.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Range boundary mutation'
                    })
                except (ValueError, IndexError, AttributeError) as e:
                    logger.warning(f"Failed to parse range value: {type(e).__name__}: {e}")
            
            # Array index mutations (looking for [0], [1], [-1])
            if CompiledPatterns.BOUNDARY_NUMS.search(original):
                mutated = original
                mutated = re.sub(r'\[0\]', '[1]', mutated)
                mutated = re.sub(r'\[1\]', '[0]', mutated)
                mutated = re.sub(r'\[-1\]', '[-2]', mutated)
                
                if mutated != original:
                    mutations.append({
                        'type': MutationType.RANGE_BOUNDARY.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Array index boundary mutation'
                    })
        
        return mutations
    
    def _generate_null_check_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations that remove null/None checks."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Remove None checks: "if x is not None:" -> "if True:"
            if 'is not None' in original and 'if ' in original:
                mutated = re.sub(r'if\s+.*?\s+is\s+not\s+None\s*:', 'if True:', original)
                if mutated != original:
                    mutations.append({
                        'type': MutationType.NULL_CHECK.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Remove None check - test null handling'
                    })
            
            # Remove if x: style checks
            elif re.search(r'if\s+\w+\s*:', original) and 'not' not in original:
                mutated = re.sub(r'if\s+\w+\s*:', 'if True:', original)
                mutations.append({
                    'type': MutationType.NULL_CHECK.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove truthiness check'
                })
        
        return mutations
    
    def _generate_string_empty_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for string empty checks and operations."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Empty string mutations: "" -> "test"
            if '""' in original:
                mutated = original.replace('""', '"test"')
                mutations.append({
                    'type': MutationType.STRING_EMPTY.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Empty string -> non-empty string'
                })
            
            # Remove .strip() calls
            elif '.strip()' in original:
                mutated = original.replace('.strip()', '')
                mutations.append({
                    'type': MutationType.STRING_EMPTY.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove string strip() - test whitespace handling'
                })
            
            # len() == 0 checks
            elif re.search(r'len\(.*?\)\s*==\s*0', original):
                mutated = re.sub(r'len\(.*?\)\s*==\s*0', 'False', original)
                mutations.append({
                    'type': MutationType.STRING_EMPTY.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove empty length check'
                })
        
        return mutations
    
    def _generate_list_empty_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for list/collection empty checks."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Empty list mutations: [] -> ["item"]
            if '[]' in original and 'return []' not in original:
                mutated = original.replace('[]', '["test_item"]')
                mutations.append({
                    'type': MutationType.LIST_EMPTY.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Empty list -> non-empty list'
                })
            
            # Empty dict mutations: {} -> {"key": "value"}
            elif '{}' in original and 'return {}' not in original:
                mutated = original.replace('{}', '{"test_key": "test_value"}')
                mutations.append({
                    'type': MutationType.LIST_EMPTY.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Empty dict -> non-empty dict'
                })
            
            # if not list_var: checks
            elif re.search(r'if\s+not\s+\w+\s*:', original):
                mutated = re.sub(r'if\s+not\s+\w+\s*:', 'if False:', original)
                mutations.append({
                    'type': MutationType.LIST_EMPTY.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove empty collection check'
                })
        
        return mutations
    
    def _generate_database_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for database transaction handling."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Remove commit() calls
            if '.commit()' in original:
                mutated = original.replace('.commit()', '# .commit() removed')
                mutations.append({
                    'type': MutationType.DATABASE_TRANSACTION.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove database commit - test rollback handling'
                })
            
            # Change rollback() to commit()
            elif '.rollback()' in original:
                mutated = original.replace('.rollback()', '.commit()')
                mutations.append({
                    'type': MutationType.DATABASE_TRANSACTION.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Change rollback to commit - test error recovery'
                })
            
            # Remove close() calls
            elif '.close()' in original:
                mutated = original.replace('.close()', '# .close() removed')
                mutations.append({
                    'type': MutationType.DATABASE_TRANSACTION.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove connection close - test resource leaks'
                })
        
        return mutations
    
    def _generate_timeout_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for timeout values."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Timeout parameter mutations
            timeout_match = re.search(r'timeout\s*=\s*(\d+)', original)
            if timeout_match:
                value = int(timeout_match.group(1))
                # Drastically reduce timeout to trigger timeout errors
                new_value = max(1, value // 10)
                mutated = original.replace(f'timeout={value}', f'timeout={new_value}')
                mutations.append({
                    'type': MutationType.TIMEOUT_VALUE.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': f'Reduce timeout {value} -> {new_value} - test timeout handling'
                })
            
            # time.sleep() mutations
            sleep_match = re.search(r'time\.sleep\((\d+(?:\.\d+)?)\)', original)
            if sleep_match:
                value = float(sleep_match.group(1))
                new_value = value * 10  # Make sleeps longer to test patience
                mutated = original.replace(f'time.sleep({value})', f'time.sleep({new_value})')
                mutations.append({
                    'type': MutationType.TIMEOUT_VALUE.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': f'Increase sleep {value} -> {new_value} - test timeout handling'
                })
        
        return mutations
    
    def _generate_retry_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for retry logic."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Retry count mutations
            retry_patterns = [
                r'max_retries\s*=\s*(\d+)',
                r'retries\s*=\s*(\d+)',
                r'max_attempts\s*=\s*(\d+)'
            ]
            
            for pattern in retry_patterns:
                match = re.search(pattern, original)
                if match:
                    value = int(match.group(1))
                    # Set retries to 0 to test immediate failure
                    mutated = re.sub(pattern, lambda m: m.group(0).replace(str(value), '0'), original)
                    mutations.append({
                        'type': MutationType.RETRY_COUNT.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': f'Set retry count to 0 - test failure handling'
                    })
                    break
            
            # for _ in range(retries): mutations
            range_retry_match = re.search(r'for\s+\w+\s+in\s+range\((\d+)\)', original)
            if range_retry_match and any(word in original.lower() for word in ['retry', 'attempt']):
                value = int(range_retry_match.group(1))
                mutated = original.replace(f'range({value})', 'range(1)')
                mutations.append({
                    'type': MutationType.RETRY_COUNT.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Reduce retry loop to 1 iteration'
                })
        
        return mutations
    
    def _generate_log_level_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for logging levels."""
        mutations = []
        
        log_levels = {
            'logger.debug': 'logger.error',
            'logger.info': 'logger.error', 
            'logger.warning': 'logger.debug',
            'logger.error': 'logger.debug',
            'logging.DEBUG': 'logging.ERROR',
            'logging.INFO': 'logging.ERROR',
            'logging.WARNING': 'logging.DEBUG',
            'logging.ERROR': 'logging.DEBUG'
        }
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            for old_level, new_level in log_levels.items():
                if old_level in original:
                    mutated = original.replace(old_level, new_level)
                    mutations.append({
                        'type': MutationType.LOG_LEVEL.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': f'Change log level {old_level} -> {new_level}'
                    })
                    break
        
        return mutations
    
    def _generate_config_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for configuration values."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Default value mutations
            default_match = re.search(r'default\s*=\s*(\d+)', original)
            if default_match:
                value = int(default_match.group(1))
                new_value = value * 2 if value > 0 else 1
                mutated = original.replace(f'default={value}', f'default={new_value}')
                mutations.append({
                    'type': MutationType.CONFIG_VALUE.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': f'Change default value {value} -> {new_value}'
                })
            
            # Config.get() with defaults
            config_get_match = re.search(r'\.get\([^,]+,\s*([^)]+)\)', original)
            if config_get_match and 'config' in original.lower():
                default_val = config_get_match.group(1).strip()
                if default_val.isdigit():
                    new_val = str(int(default_val) * 2)
                    mutated = original.replace(default_val, new_val)
                    mutations.append({
                        'type': MutationType.CONFIG_VALUE.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': f'Change config default {default_val} -> {new_val}'
                    })
        
        return mutations
    
    def _generate_async_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations for async/await patterns."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Remove await keywords
            if 'await ' in original:
                mutated = original.replace('await ', '')
                mutations.append({
                    'type': MutationType.ASYNC_AWAIT.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove await - test sync/async mixing'
                })
            
            # Change async def to def
            elif 'async def ' in original:
                mutated = original.replace('async def ', 'def ')
                mutations.append({
                    'type': MutationType.ASYNC_AWAIT.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Remove async from function definition'
                })
        
        return mutations
    
    def _generate_pensieve_mutations(self, lines: List[str]) -> List[Dict]:
        """Generate mutations specific to Pensieve API integration."""
        mutations = []
        
        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            original = line.strip()
            
            # Remove API health checks
            if 'api_health' in original.lower() or 'health_check' in original.lower():
                if 'if ' in original:
                    mutated = re.sub(r'if\s+.*?health.*?:', 'if False:', original)
                    mutations.append({
                        'type': MutationType.PENSIEVE_API.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Force API health check to fail'
                    })
            
            # Change API fallback logic
            elif 'fallback' in original.lower() and ('api' in original.lower() or 'pensieve' in original.lower()):
                if 'if ' in original:
                    mutated = re.sub(r'if\s+.*?fallback.*?:', 'if True:', original)
                    mutations.append({
                        'type': MutationType.PENSIEVE_API.value,
                        'line': i,
                        'original': original,
                        'mutated': mutated,
                        'description': 'Force API fallback activation'
                    })
            
            # DatabaseManager pattern mutations
            elif 'DatabaseManager' in original and 'try:' in original:
                mutated = original.replace('try:', 'if False:  # try:')
                mutations.append({
                    'type': MutationType.PENSIEVE_API.value,
                    'line': i,
                    'original': original,
                    'mutated': mutated,
                    'description': 'Disable DatabaseManager try block - test error handling'
                })
        
        return mutations