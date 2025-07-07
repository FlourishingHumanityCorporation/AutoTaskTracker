#!/usr/bin/env python3
"""
VLM Configuration Restore Script
Restores VLM configuration from backup 20250706_223113
"""
import os
import sys
import shutil
from pathlib import Path

def restore_config():
    """Restore configuration from backup."""
    backup_dir = Path("vlm_backup_20250706_223113")
    
    if not backup_dir.exists():
        print(f"ERROR: Backup directory not found: {backup_dir}")
        return False
    
    print(f"Restoring VLM configuration from backup: {backup_dir}")
    
    # Restore configuration files
    config_backup = backup_dir / 'config'
    if config_backup.exists():
        # Restore main config
        config_py = config_backup / 'config.py'
        if config_py.exists():
            shutil.copy2(config_py, 'autotasktracker/config.py')
            print("Restored autotasktracker/config.py")
        
        # Restore VLM processor
        vlm_processor = config_backup / 'vlm_processor.py'
        if vlm_processor.exists():
            shutil.copy2(vlm_processor, 'autotasktracker/ai/vlm_processor.py')
            print("Restored autotasktracker/ai/vlm_processor.py")
    
    # Restore VLM cache
    cache_backup = backup_dir / 'cache' / 'vlm_cache'
    if cache_backup.exists():
        vlm_cache_path = Path("/Users/paulrohde/AutoTaskTracker.memos/vlm_cache")
        if vlm_cache_path.exists():
            shutil.rmtree(vlm_cache_path)
        shutil.copytree(cache_backup, vlm_cache_path)
        print(f"Restored VLM cache to {vlm_cache_path}")
    
    print("VLM configuration restore completed")
    print("IMPORTANT: Restart any running services to apply restored configuration")
    return True

if __name__ == "__main__":
    if restore_config():
        print("✓ Restore successful")
        sys.exit(0)
    else:
        print("✗ Restore failed")
        sys.exit(1)
