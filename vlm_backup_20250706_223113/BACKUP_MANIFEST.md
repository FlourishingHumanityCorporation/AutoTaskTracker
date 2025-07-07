# VLM Configuration Backup Manifest
                
**Backup Created**: 20250706_223113
**Backup Directory**: vlm_backup_20250706_223113

## Files Backed Up

- **Main configuration file**\n  - Source: `autotasktracker/config.py`\n  - Backup: `vlm_backup_20250706_223113/config/config.py`\n\n- **VLM processor implementation**\n  - Source: `autotasktracker/ai/vlm_processor.py`\n  - Backup: `vlm_backup_20250706_223113/config/vlm_processor.py`\n\n- **Project instructions**\n  - Source: `CLAUDE.md`\n  - Backup: `vlm_backup_20250706_223113/config/CLAUDE.md`\n\n- **Python dependencies**\n  - Source: `requirements.txt`\n  - Backup: `vlm_backup_20250706_223113/config/requirements.txt`\n\n- **Model validation results**\n  - Source: `validation_results.json`\n  - Backup: `vlm_backup_20250706_223113/logs/validation_results.json`\n\n- **Memory benchmark results**\n  - Source: `vlm_memory_benchmark.json`\n  - Backup: `vlm_backup_20250706_223113/logs/vlm_memory_benchmark.json`\n\n- **VLM script: validate_vlm_models.py**\n  - Source: `scripts/validate_vlm_models.py`\n  - Backup: `vlm_backup_20250706_223113/scripts/validate_vlm_models.py`\n\n- **VLM script: benchmark_vlm_memory.py**\n  - Source: `scripts/benchmark_vlm_memory.py`\n  - Backup: `vlm_backup_20250706_223113/scripts/benchmark_vlm_memory.py`\n\n- **VLM script: backup_vlm_config.py**\n  - Source: `scripts/backup_vlm_config.py`\n  - Backup: `vlm_backup_20250706_223113/scripts/backup_vlm_config.py`\n\n- **Restore script for rollback**\n  - Source: `generated`\n  - Backup: `vlm_backup_20250706_223113/restore_vlm_config.py`\n\n
## Directories Backed Up

- **VLM cache directory**\n  - Source: `/Users/paulrohde/AutoTaskTracker.memos/vlm_cache`\n  - Backup: `vlm_backup_20250706_223113/cache/vlm_cache`\n\n
## How to Restore

1. Run the restore script:
   ```bash
   python vlm_backup_20250706_223113/restore_vlm_config.py
   ```

2. Or manually copy files back to their original locations

3. Restart any running services to apply changes

## Configuration Snapshot

Current VLM configuration has been captured in `config/config_snapshot.json`
