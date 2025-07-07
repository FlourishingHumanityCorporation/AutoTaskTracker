#!/usr/bin/env python3
"""
VLM Configuration Backup Script
Creates backup of current VLM configuration before dual-model implementation changes.
"""
import sys
import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VLMConfigBackup:
    """Creates comprehensive backup of VLM configuration and state."""
    
    def __init__(self):
        """Initialize backup manager."""
        self.config = get_config()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"vlm_backup_{self.timestamp}")
        self.backup_summary = {
            'timestamp': self.timestamp,
            'backup_dir': str(self.backup_dir),
            'files_backed_up': [],
            'directories_backed_up': [],
            'config_snapshot': {},
            'errors': [],
            'success': False
        }
        
    def create_backup_directory(self):
        """Create backup directory structure."""
        try:
            self.backup_dir.mkdir(exist_ok=True)
            
            # Create subdirectories
            subdirs = ['config', 'cache', 'scripts', 'logs']
            for subdir in subdirs:
                (self.backup_dir / subdir).mkdir(exist_ok=True)
            
            logger.info(f"Created backup directory: {self.backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            self.backup_summary['errors'].append(f"Directory creation failed: {e}")
            return False
    
    def backup_config_files(self):
        """Backup configuration files."""
        config_files = [
            ('autotasktracker/config.py', 'Main configuration file'),
            ('autotasktracker/ai/vlm_processor.py', 'VLM processor implementation'),
            ('CLAUDE.md', 'Project instructions'),
            ('requirements.txt', 'Python dependencies'),
        ]
        
        for file_path, description in config_files:
            try:
                source = Path(file_path)
                if source.exists():
                    dest = self.backup_dir / 'config' / source.name
                    shutil.copy2(source, dest)
                    self.backup_summary['files_backed_up'].append({
                        'source': str(source),
                        'destination': str(dest),
                        'description': description
                    })
                    logger.info(f"Backed up {description}: {source} -> {dest}")
                else:
                    logger.warning(f"Config file not found: {source}")
            except Exception as e:
                error_msg = f"Failed to backup {file_path}: {e}"
                logger.error(error_msg)
                self.backup_summary['errors'].append(error_msg)
    
    def backup_vlm_cache(self):
        """Backup VLM cache and related data."""
        try:
            vlm_cache_dir = Path(self.config.get_vlm_cache_path())
            if vlm_cache_dir.exists():
                dest_cache_dir = self.backup_dir / 'cache' / 'vlm_cache'
                shutil.copytree(vlm_cache_dir, dest_cache_dir, dirs_exist_ok=True)
                self.backup_summary['directories_backed_up'].append({
                    'source': str(vlm_cache_dir),
                    'destination': str(dest_cache_dir),
                    'description': 'VLM cache directory'
                })
                logger.info(f"Backed up VLM cache: {vlm_cache_dir} -> {dest_cache_dir}")
            else:
                logger.info("VLM cache directory not found - nothing to backup")
        except Exception as e:
            error_msg = f"Failed to backup VLM cache: {e}"
            logger.error(error_msg)
            self.backup_summary['errors'].append(error_msg)
    
    def backup_validation_results(self):
        """Backup validation and benchmark results."""
        result_files = [
            ('validation_results.json', 'Model validation results'),
            ('vlm_memory_benchmark.json', 'Memory benchmark results'),
        ]
        
        for file_name, description in result_files:
            try:
                source = Path(file_name)
                if source.exists():
                    dest = self.backup_dir / 'logs' / file_name
                    shutil.copy2(source, dest)
                    self.backup_summary['files_backed_up'].append({
                        'source': str(source),
                        'destination': str(dest),
                        'description': description
                    })
                    logger.info(f"Backed up {description}: {source} -> {dest}")
            except Exception as e:
                error_msg = f"Failed to backup {file_name}: {e}"
                logger.error(error_msg)
                self.backup_summary['errors'].append(error_msg)
    
    def backup_scripts(self):
        """Backup scripts directory."""
        try:
            scripts_dir = Path('scripts')
            if scripts_dir.exists():
                dest_scripts_dir = self.backup_dir / 'scripts'
                
                # Copy specific scripts related to VLM
                vlm_scripts = [
                    'validate_vlm_models.py',
                    'benchmark_vlm_memory.py',
                    'backup_vlm_config.py'
                ]
                
                for script_name in vlm_scripts:
                    script_path = scripts_dir / script_name
                    if script_path.exists():
                        dest_path = dest_scripts_dir / script_name
                        shutil.copy2(script_path, dest_path)
                        self.backup_summary['files_backed_up'].append({
                            'source': str(script_path),
                            'destination': str(dest_path),
                            'description': f'VLM script: {script_name}'
                        })
                        logger.info(f"Backed up script: {script_path} -> {dest_path}")
                
                logger.info("Backed up VLM-related scripts")
        except Exception as e:
            error_msg = f"Failed to backup scripts: {e}"
            logger.error(error_msg)
            self.backup_summary['errors'].append(error_msg)
    
    def capture_config_snapshot(self):
        """Capture current configuration state."""
        try:
            config_dict = self.config.to_dict()
            
            # Add VLM-specific configuration
            vlm_config = {
                'VLM_MODEL_NAME': self.config.VLM_MODEL_NAME,
                'VLM_TEMPERATURE': self.config.VLM_TEMPERATURE,
                'LLAMA3_MODEL_NAME': self.config.LLAMA3_MODEL_NAME,
                'ENABLE_DUAL_MODEL': self.config.ENABLE_DUAL_MODEL,
                'OLLAMA_PORT': self.config.OLLAMA_PORT,
                'VLM_CONCURRENCY': self.config.VLM_CONCURRENCY,
                'ENABLE_VLM': self.config.ENABLE_VLM,
                'VLM_CACHE_DIR': self.config.VLM_CACHE_DIR,
            }
            
            self.backup_summary['config_snapshot'] = {
                'full_config': config_dict,
                'vlm_specific': vlm_config,
                'environment_vars': {
                    'MEMOS_CONFIG_PATH': os.getenv('MEMOS_CONFIG_PATH'),
                    'OLLAMA_URL': os.getenv('OLLAMA_URL'),
                    'AUTOTASK_VLM_MODEL': os.getenv('AUTOTASK_VLM_MODEL'),
                }
            }
            
            # Save config snapshot
            config_file = self.backup_dir / 'config' / 'config_snapshot.json'
            with open(config_file, 'w') as f:
                json.dump(self.backup_summary['config_snapshot'], f, indent=2, default=str)
            
            logger.info("Captured configuration snapshot")
            
        except Exception as e:
            error_msg = f"Failed to capture config snapshot: {e}"
            logger.error(error_msg)
            self.backup_summary['errors'].append(error_msg)
    
    def create_restore_script(self):
        """Create restore script for rollback."""
        restore_script_content = f'''#!/usr/bin/env python3
"""
VLM Configuration Restore Script
Restores VLM configuration from backup {self.timestamp}
"""
import os
import sys
import shutil
from pathlib import Path

def restore_config():
    """Restore configuration from backup."""
    backup_dir = Path("{self.backup_dir}")
    
    if not backup_dir.exists():
        print(f"ERROR: Backup directory not found: {{backup_dir}}")
        return False
    
    print(f"Restoring VLM configuration from backup: {{backup_dir}}")
    
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
        vlm_cache_path = Path("{self.config.get_vlm_cache_path()}")
        if vlm_cache_path.exists():
            shutil.rmtree(vlm_cache_path)
        shutil.copytree(cache_backup, vlm_cache_path)
        print(f"Restored VLM cache to {{vlm_cache_path}}")
    
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
'''
        
        try:
            restore_script = self.backup_dir / 'restore_vlm_config.py'
            with open(restore_script, 'w') as f:
                f.write(restore_script_content)
            restore_script.chmod(0o755)  # Make executable
            
            self.backup_summary['files_backed_up'].append({
                'source': 'generated',
                'destination': str(restore_script),
                'description': 'Restore script for rollback'
            })
            
            logger.info(f"Created restore script: {restore_script}")
            
        except Exception as e:
            error_msg = f"Failed to create restore script: {e}"
            logger.error(error_msg)
            self.backup_summary['errors'].append(error_msg)
    
    def save_backup_summary(self):
        """Save backup summary and manifest."""
        try:
            summary_file = self.backup_dir / 'backup_summary.json'
            with open(summary_file, 'w') as f:
                json.dump(self.backup_summary, f, indent=2, default=str)
            
            logger.info(f"Saved backup summary: {summary_file}")
            
            # Also create a human-readable manifest
            manifest_file = self.backup_dir / 'BACKUP_MANIFEST.md'
            with open(manifest_file, 'w') as f:
                f.write(f"""# VLM Configuration Backup Manifest
                
**Backup Created**: {self.backup_summary['timestamp']}
**Backup Directory**: {self.backup_summary['backup_dir']}

## Files Backed Up

""")
                for file_info in self.backup_summary['files_backed_up']:
                    f.write(f"- **{file_info['description']}**\\n")
                    f.write(f"  - Source: `{file_info['source']}`\\n")
                    f.write(f"  - Backup: `{file_info['destination']}`\\n\\n")
                
                f.write(f"""
## Directories Backed Up

""")
                for dir_info in self.backup_summary['directories_backed_up']:
                    f.write(f"- **{dir_info['description']}**\\n")
                    f.write(f"  - Source: `{dir_info['source']}`\\n")
                    f.write(f"  - Backup: `{dir_info['destination']}`\\n\\n")
                
                if self.backup_summary['errors']:
                    f.write(f"""
## Errors Encountered

""")
                    for error in self.backup_summary['errors']:
                        f.write(f"- {error}\\n")
                
                f.write(f"""
## How to Restore

1. Run the restore script:
   ```bash
   python {self.backup_dir}/restore_vlm_config.py
   ```

2. Or manually copy files back to their original locations

3. Restart any running services to apply changes

## Configuration Snapshot

Current VLM configuration has been captured in `config/config_snapshot.json`
""")
            
            logger.info(f"Created backup manifest: {manifest_file}")
            
        except Exception as e:
            error_msg = f"Failed to save backup summary: {e}"
            logger.error(error_msg)
            self.backup_summary['errors'].append(error_msg)
    
    def run_backup(self) -> Dict:
        """Run complete backup process."""
        logger.info("Starting VLM configuration backup...")
        
        try:
            # Create backup directory
            if not self.create_backup_directory():
                return self.backup_summary
            
            # Backup configuration files
            self.backup_config_files()
            
            # Backup VLM cache
            self.backup_vlm_cache()
            
            # Backup validation results
            self.backup_validation_results()
            
            # Backup scripts
            self.backup_scripts()
            
            # Capture configuration snapshot
            self.capture_config_snapshot()
            
            # Create restore script
            self.create_restore_script()
            
            # Save summary
            self.save_backup_summary()
            
            # Mark as successful if no critical errors
            if not any('Failed to create backup directory' in error for error in self.backup_summary['errors']):
                self.backup_summary['success'] = True
            
            logger.info("VLM configuration backup completed")
            
        except Exception as e:
            error_msg = f"Backup process failed: {e}"
            logger.error(error_msg)
            self.backup_summary['errors'].append(error_msg)
        
        return self.backup_summary


def main():
    """Main backup function."""
    backup_manager = VLMConfigBackup()
    
    try:
        # Run backup
        results = backup_manager.run_backup()
        
        # Print summary
        print("\\n" + "="*60)
        print("VLM CONFIGURATION BACKUP RESULTS")
        print("="*60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Backup Directory: {results['backup_dir']}")
        print(f"Files Backed Up: {len(results['files_backed_up'])}")
        print(f"Directories Backed Up: {len(results['directories_backed_up'])}")
        print(f"Success: {'✓' if results['success'] else '✗'}")
        
        if results['errors']:
            print(f"\\nErrors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        print(f"\\nBackup location: {results['backup_dir']}")
        print(f"To restore: python {results['backup_dir']}/restore_vlm_config.py")
        
        # Return appropriate exit code
        return 0 if results['success'] else 1
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)