"""
Configuration pattern analyzer for health tests.

Analyzes code for proper configuration patterns including:
- Hardcoded values that should be configurable
- Configuration management best practices
- Environment variable usage
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Callable
import logging

logger = logging.getLogger(__name__)


class ConfigurationAnalyzer:
    """Analyzer for configuration patterns."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def analyze_hardcoded_values(self, file_path: Path) -> List[Dict]:
        """Analyze file for hardcoded values that should be configurable."""
        hardcoding_issues = []
        
        # Patterns for hardcoded values
        hardcoded_patterns = [
            # Ports (except well-known ports like 80, 443)
            (r':(\d{4,5})["\'\s]', 'hardcoded port', lambda m: int(m.group(1)) not in [80, 443, 22]),
            # Timeouts
            (r'timeout\s*=\s*(\d+)', 'hardcoded timeout', lambda m: True),
            # Sleep/wait times
            (r'sleep\s*\(\s*(\d+)', 'hardcoded sleep', lambda m: float(m.group(1)) > 1),
            # Retry counts
            (r'(?:retries|attempts|max_retries)\s*=\s*(\d+)', 'hardcoded retry count', lambda m: True),
            # Buffer/batch sizes
            (r'(?:batch_size|buffer_size|chunk_size)\s*=\s*(\d+)', 'hardcoded size', lambda m: int(m.group(1)) > 100),
            # URLs (except localhost)
            (r'["\']https?://(?!localhost|127\.0\.0\.1)[^"\']+["\']', 'hardcoded URL', lambda m: True),
            # File paths (except relative paths)
            (r'["\'](?:/[^"\']+|[A-Z]:\\[^"\']+)["\']', 'hardcoded absolute path', lambda m: '.memos' not in m.group(0)),
        ]
        
        # Files to skip (config files, tests)
        skip_files = ['config.py', 'test_', 'conftest.py', '__init__.py']
        
        if any(skip in file_path.name for skip in skip_files):
            return hardcoding_issues
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern, description, validator in hardcoded_patterns:
                matches = list(re.finditer(pattern, content))
                for match in matches:
                    if validator(match):
                        line_no = content[:match.start()].count('\n') + 1
                        # Get the full line for context
                        lines = content.split('\n')
                        if line_no <= len(lines):
                            full_line = lines[line_no - 1].strip()
                            
                            # Skip if it's in a comment
                            comment_idx = full_line.find('#')
                            if comment_idx >= 0:
                                # Check if the match is after the comment start
                                line_start = sum(len(l) + 1 for l in lines[:line_no - 1])
                                match_pos_in_line = match.start() - line_start
                                if match_pos_in_line > comment_idx:
                                    continue
                            
                            # Skip if it's in a docstring or test data
                            context_start = max(0, line_no - 3)
                            context_end = min(len(lines), line_no + 3)
                            context = '\n'.join(lines[context_start:context_end])
                            if any(marker in context for marker in ['"""', "'''", 'test_data', 'example', 'default=']):
                                continue
                                
                            # Skip if it's a well-known constant
                            if any(const in full_line for const in ['__version__', 'DEFAULT_', 'MAX_', 'MIN_']):
                                continue
                                
                            hardcoding_issues.append({
                                'file': file_path,
                                'line': line_no,
                                'type': description,
                                'value': match.group(0),
                                'context': full_line[:80]
                            })
                        
        except Exception as e:
            logger.warning(f"Error analyzing hardcoded values in {file_path}: {e}")
        
        return hardcoding_issues
    
    def analyze_config_usage(self, file_path: Path) -> Dict[str, bool]:
        """Analyze configuration usage patterns."""
        patterns = {
            'uses_env_vars': False,
            'uses_config_module': False,
            'has_defaults': False,
            'validates_config': False
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for environment variable usage
            if re.search(r'os\.getenv|os\.environ', content):
                patterns['uses_env_vars'] = True
            
            # Check for config module usage
            if re.search(r'from.*config.*import|import.*config', content):
                patterns['uses_config_module'] = True
            
            # Check for default values
            if re.search(r'getenv\([^,]+,\s*[^)]+\)', content):
                patterns['has_defaults'] = True
            
            # Check for config validation
            if any(keyword in content for keyword in ['validate_config', 'check_config', 'config_error']):
                patterns['validates_config'] = True
                
        except Exception as e:
            logger.warning(f"Error analyzing config usage in {file_path}: {e}")
        
        return patterns