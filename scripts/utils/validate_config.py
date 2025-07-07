#!/usr/bin/env python3
"""
Configuration validation script for AutoTaskTracker.
Ensures configuration files contain correct database URLs and ports.
"""

import yaml
import os
import sys
from pathlib import Path
from datetime import datetime

# Expected configuration values
EXPECTED_CONFIG = {
    'database_path': 'postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker',
    'server_port': 8841,
    'server_host': 'localhost'
}


def validate_config_file(config_path: Path) -> tuple[bool, list[str]]:
    """Validate a configuration file.
    
    Returns:
        (success, issues) tuple
    """
    issues = []
    
    if not config_path.exists():
        return False, [f"Config file not found: {config_path}"]
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return False, [f"Failed to parse YAML: {e}"]
    
    # Check database path
    if config.get('database_path') != EXPECTED_CONFIG['database_path']:
        issues.append(
            f"Incorrect database_path: {config.get('database_path')}\n"
            f"  Expected: {EXPECTED_CONFIG['database_path']}"
        )
    
    # Check server port
    if config.get('server_port') != EXPECTED_CONFIG['server_port']:
        issues.append(
            f"Incorrect server_port: {config.get('server_port')}\n"
            f"  Expected: {EXPECTED_CONFIG['server_port']}"
        )
    
    # Check for SQLite references
    db_path = config.get('database_path', '')
    if 'sqlite' in db_path.lower() or '.db' in db_path:
        issues.append(f"SQLite reference found in database_path: {db_path}")
    
    return len(issues) == 0, issues


def backup_config(config_path: Path) -> Path:
    """Create a backup of the config file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = config_path.parent / f"{config_path.stem}_backup_{timestamp}{config_path.suffix}"
    
    if config_path.exists():
        with open(config_path, 'r') as src:
            with open(backup_path, 'w') as dst:
                dst.write(src.read())
    
    return backup_path


def fix_config_file(config_path: Path) -> bool:
    """Fix configuration issues in the file."""
    try:
        # Load current config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Apply fixes
        config['database_path'] = EXPECTED_CONFIG['database_path']
        config['server_port'] = EXPECTED_CONFIG['server_port']
        config['server_host'] = EXPECTED_CONFIG['server_host']
        
        # Write fixed config
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        return True
    except Exception as e:
        print(f"Error fixing config: {e}")
        return False


def main():
    """Main validation routine."""
    config_path = Path('/Users/paulrohde/AutoTaskTracker.memos') / 'config_autotasktracker.yaml'
    
    print("AutoTaskTracker Configuration Validator")
    print("=" * 40)
    print(f"Checking: {config_path}")
    print()
    
    # Validate current config
    valid, issues = validate_config_file(config_path)
    
    if valid:
        print("✅ Configuration is valid!")
        print(f"   Database: PostgreSQL on port 5433")
        print(f"   Server: Port {EXPECTED_CONFIG['server_port']}")
        return 0
    
    # Show issues
    print("❌ Configuration issues found:")
    for issue in issues:
        print(f"   - {issue}")
    print()
    
    # Offer to fix
    response = input("Would you like to fix these issues? [y/N]: ")
    if response.lower() == 'y':
        # Create backup
        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path}")
        
        # Fix issues
        if fix_config_file(config_path):
            print("✅ Configuration fixed!")
            
            # Verify fix
            valid, issues = validate_config_file(config_path)
            if valid:
                print("✅ Validation passed!")
            else:
                print("❌ Validation still failing:")
                for issue in issues:
                    print(f"   - {issue}")
                return 1
        else:
            print("❌ Failed to fix configuration")
            return 1
    
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())