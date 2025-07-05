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
            # Ports (only flag non-standard high ports)
            (r':(\d{4,5})["\'\s]', 'hardcoded port', lambda m: int(m.group(1)) > 9000 and int(m.group(1)) not in [8000, 8080, 8502, 8503, 8505, 8839]),
            # Timeouts (only flag long timeouts > 30 seconds)
            (r'timeout\s*=\s*(\d+)', 'hardcoded timeout', lambda m: int(m.group(1)) > 30),
            # Sleep/wait times (only flag long sleeps > 5 seconds)
            (r'sleep\s*\(\s*(\d+)', 'hardcoded sleep', lambda m: float(m.group(1)) > 5),
            # Retry counts (only flag excessive retries > 5)
            (r'(?:retries|attempts|max_retries)\s*=\s*(\d+)', 'hardcoded retry count', lambda m: int(m.group(1)) > 5),
            # Buffer/batch sizes (only flag very large sizes > 1000)
            (r'(?:batch_size|buffer_size|chunk_size)\s*=\s*(\d+)', 'hardcoded size', lambda m: int(m.group(1)) > 1000),
            # URLs (only flag external production URLs)
            (r'["\']https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[^"\']+\.(?:com|org|net)[^"\']*["\']', 'hardcoded external URL', lambda m: True),
            # File paths (only flag absolute system paths, not project paths)
            (r'["\'](?:/(?:var|usr|etc|home)/[^"\']+|[A-Z]:\\(?:Program Files|Windows)[^"\']+)["\']', 'hardcoded system path', lambda m: True),
        ]
        
        # Files to skip (config files, tests, scripts with legitimate hardcoded values)
        skip_files = ['config.py', 'test_', 'conftest.py', '__init__.py', 'setup.py', 'launcher.py']
        
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
    
    def analyze_config_patterns(self, file_path: Path) -> List[Dict]:
        """Analyze configuration patterns and classify as good or poor."""
        patterns = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Good patterns
                if re.search(r'os\.getenv\([^,]+,\s*[^)]+\)', line):
                    patterns.append({
                        'type': 'good_pattern',
                        'file': file_path,
                        'line': line_num,
                        'pattern': 'Uses environment variables with defaults'
                    })
                
                if re.search(r'from.*config.*import', line):
                    patterns.append({
                        'type': 'good_pattern',
                        'file': file_path,
                        'line': line_num,
                        'pattern': 'Uses configuration module'
                    })
                
                # Poor patterns (only flag obvious hardcoding in non-config files)
                if not any(skip in file_path.name for skip in ['config.py', 'test_', 'conftest.py']):
                    if re.search(r':\d{4,5}["\'\s]', line) and 'localhost' not in line:
                        patterns.append({
                            'type': 'poor_pattern',
                            'file': file_path,
                            'line': line_num,
                            'pattern': 'Hardcoded port number'
                        })
                        
        except Exception as e:
            logger.warning(f"Error analyzing config patterns in {file_path}: {e}")
        
        return patterns