#!/usr/bin/env python3
"""
Fix unsafe file operations identified in technical debt analysis.

This script demonstrates fixing one of the 12 unsafe file operations
by adding proper path validation.
"""
import logging
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def add_path_validation(file_path: Path, line_number: int, current_line: str) -> str:
    """Add path validation to unsafe file operations."""
    
    # Pattern: with open(some_path, 'r') as f:
    open_pattern = r'with open\(([^,]+),\s*[\'"][rwa]+[\'"]\)\s*as\s+\w+:'
    
    if re.search(open_pattern, current_line.strip()):
        # Extract the file path variable
        match = re.search(r'with open\(([^,]+),', current_line)
        if match:
            path_var = match.group(1).strip()
            
            # Generate validation code
            validation_code = f"""        # Validate file path to prevent directory traversal
        {path_var}_resolved = Path({path_var}).resolve()
        if not str({path_var}_resolved).startswith(str(Path.cwd().resolve())):
            raise ValueError(f"Invalid file path: {{{{path_var}}}}")
        
        {current_line.strip()}"""
            
            return validation_code
    
    return current_line


def fix_file_operations(file_path: str) -> bool:
    """Fix unsafe file operations in a specific file."""
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read original content
        with open(path, 'r') as f:
            lines = f.readlines()
        
        # Track changes
        changes_made = False
        new_lines = []
        
        for i, line in enumerate(lines):
            # Look for unsafe file operations
            if 'with open(' in line and ('cache' in line or 'config' in line):
                logger.info(f"Found potential unsafe file operation at line {i+1}: {line.strip()}")
                
                # Add validation (this is a demonstration - real implementation would be more sophisticated)
                if '# Validate file path' not in lines[max(0, i-3):i+1]:  # Don't add if already present
                    validated_line = add_path_validation(path, i+1, line)
                    if validated_line != line:
                        new_lines.append(validated_line)
                        changes_made = True
                        logger.info(f"Added path validation at line {i+1}")
                        continue
            
            new_lines.append(line)
        
        if changes_made:
            # Write back with backup
            backup_path = path.with_suffix(path.suffix + '.backup')
            path.rename(backup_path)
            
            with open(path, 'w') as f:
                f.writelines(new_lines)
            
            logger.info(f"Fixed {file_path} (backup: {backup_path})")
            return True
        else:
            logger.info(f"No changes needed for {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix unsafe file operations in identified files."""
    
    # Files identified in technical debt analysis
    unsafe_files = [
        "autotasktracker/ai/vlm_processor.py",
        "autotasktracker/core/config_manager.py", 
        "autotasktracker/core/time_tracker.py"
    ]
    
    print("🔧 Fixing unsafe file operations...")
    
    fixed_count = 0
    for file_path in unsafe_files:
        print(f"Checking {file_path}...")
        if fix_file_operations(file_path):
            fixed_count += 1
    
    print(f"✅ Fixed {fixed_count}/{len(unsafe_files)} files")
    print("\nThis demonstrates the value of technical debt analysis:")
    print("- Identified specific security issues")
    print("- Provided targeted fixes")
    print("- Reduced manual security review effort")
    
    if fixed_count > 0:
        print("\n⚠️ Note: Review changes before committing!")
        print("Run: git diff to see what was changed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()