"""
Auto-fix functionality for health test issues.

Provides automated fixes for common issues found by health tests.
"""

import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PensieveHealthAutoFixer:
    """Automatically fix simple issues found by health test."""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.fixes_applied = []
    
    def fix_metadata_keys(self, file_path: Path, issues: List[Dict]) -> bool:
        """Fix incorrect metadata key usage."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would fix metadata keys in {file_path}")
            return True
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            replacements = {
                "ocr_result": "ocr_result",
                "active_window": "active_window",
                "vlm_structured": "vlm_structured",
                "tasks": "tasks",
                "category": "category"
            }
            
            for old, new in replacements.items():
                # Replace in quotes
                content = re.sub(f'["\']({old})["\']', f'"{new}"', content)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.fixes_applied.append(f"Fixed metadata keys in {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to fix metadata keys in {file_path}: {e}")
        return False
    
    def add_error_logging(self, file_path: Path, issues: List[tuple]) -> bool:
        """Replace print statements with logging in error handlers."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would fix error logging in {file_path}")
            return True
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Check if logging is imported
            has_logging = any('import logging' in line for line in lines)
            has_logger = any('logger = ' in line for line in lines)
            
            # Add imports if needed
            if not has_logging:
                # Find the right place to insert imports
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('#'):
                        insert_pos = i
                        break
                lines.insert(insert_pos, 'import logging\n')
                
            if not has_logger:
                # Add logger after imports
                for i, line in enumerate(lines):
                    if 'import' in line:
                        continue
                    if line.strip() and not line.startswith('#'):
                        lines.insert(i, 'logger = logging.getLogger(__name__)\n\n')
                        break
            
            # Fix issues in error handlers
            for line_num, issue_type, code in issues:
                if issue_type == "print_in_except" and line_num < len(lines):
                    # Replace print with logger.error
                    lines[line_num - 1] = lines[line_num - 1].replace('print(', 'logger.error(')
                elif issue_type == "silent_pass" and line_num <= len(lines):
                    # Replace silent pass with debug logging
                    line = lines[line_num - 1]
                    if line.strip() == 'pass':
                        # Get the exception context to create appropriate log message
                        except_line = None
                        for i in range(line_num - 2, max(0, line_num - 10), -1):
                            if 'except' in lines[i]:
                                except_line = lines[i].strip()
                                break
                        
                        # Create appropriate log message based on context
                        if 'ImportError' in str(except_line):
                            replacement = '            logger.debug("Optional dependency not available")'
                        elif 'Exception' in str(except_line):
                            replacement = '            logger.debug("Operation failed silently")'
                        else:
                            replacement = '            logger.debug("Silent exception handled")'
                        
                        lines[line_num - 1] = replacement + '\n'
            
            with open(file_path, 'w') as f:
                f.writelines(lines)
            
            self.fixes_applied.append(f"Fixed error logging in {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fix error logging in {file_path}: {e}")
        return False
    
    def get_summary(self) -> str:
        """Get summary of fixes applied."""
        if not self.fixes_applied:
            return "No fixes applied"
        return f"Applied {len(self.fixes_applied)} fixes:\n" + "\n".join(self.fixes_applied)