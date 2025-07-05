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
from .constants import CONSTANTS

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


class MutationGenerator:
    """Generates mutations for source files to test effectiveness."""
    
    def __init__(self, max_mutations_per_file: Optional[int] = None):
        self.max_mutations_per_file = max_mutations_per_file or CONSTANTS.MUTATION_TESTING.MAX_MUTATIONS_PER_FILE
        
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