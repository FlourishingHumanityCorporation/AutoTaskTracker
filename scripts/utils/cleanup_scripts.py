#!/usr/bin/env python3
"""
Clean up and reorganize the scripts folder.
Archives old scripts and organizes remaining ones.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

# Define script categories
KEEP_SCRIPTS = {
    # Core processing
    'process_tasks.py',
    'process_sessions.py', 
    'realtime_processor.py',
    'screenshot_processor.py',
    
    # AI features
    'ai_cli.py',
    'generate_embeddings_simple.py',
    'vlm_processor.py',
    
    # Analysis tools
    'comparison_cli.py',
    'pipeline_monitor.py',
    
    # Utilities
    'test_dashboard.py',
    'cleanup_scripts.py',  # This script
    
    # Shell scripts
    'start_all.sh',
    'stop_all.sh',
    'start_processor.sh'
}

ARCHIVE_CATEGORIES = {
    'vlm_old': [
        'vlm_manager.py', 'vlm_batch_optimizer.py', 'vlm_coordinator.py',
        'vlm_health_check.py', 'vlm_optimizer.py', 'vlm_performance_test.py',
        'vlm_processing_service.py', 'vlm_system_status.py'
    ],
    'runners': [
        'run_analytics.py', 'run_task_board.py', 'run_timetracker.py',
        'run_time_tracker.py', 'run_notifications.py', 'run_vlm_monitor.py'
    ],
    'demos': [
        'demo_core_refactoring.py', 'demo_refactored_dashboards.py',
        'showcase_refactoring_power.py'
    ],
    'tests': [
        'test_runner.py', 'run_dashboard_test.py', 'final_comprehensive_test.py',
        'final_system_test.py'
    ],
    'fixes': [
        'fix_all_code_blocks.py', 'fix_doc_code_blocks.py', 'fix_window_titles.py',
        'truncate_blocks.py', 'migrate_to_package.py'
    ],
    'verification': [
        'verify_all_fixes.py', 'verify_refactoring.py', 'validate_refactoring.py',
        'examine_live_dashboard.py', 'live_dashboard_summary.py',
        'capture_dashboard_state.py', 'dashboard_visualization.py',
        'show_live_dashboard.py'
    ],
    'old_versions': [
        'task_processor.py', 'generate_embeddings.py', 'simple_capture.py',
        'simple_dashboard.py'
    ]
}


def cleanup_scripts(dry_run=True):
    """Clean up the scripts directory."""
    scripts_dir = Path(__file__).parent
    archive_dir = scripts_dir / 'archive' / datetime.now().strftime('%Y%m%d')
    
    # Get all Python and shell scripts
    all_scripts = set()
    for pattern in ['*.py', '*.sh']:
        all_scripts.update(f.name for f in scripts_dir.glob(pattern))
    
    # Calculate what to archive
    scripts_to_archive = all_scripts - KEEP_SCRIPTS
    
    print(f"📊 Script Analysis:")
    print(f"   Total scripts: {len(all_scripts)}")
    print(f"   Scripts to keep: {len(KEEP_SCRIPTS)}")
    print(f"   Scripts to archive: {len(scripts_to_archive)}")
    print(f"   Reduction: {len(scripts_to_archive)/len(all_scripts)*100:.1f}%")
    
    if dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
    else:
        print("\n🚀 EXECUTING cleanup...")
        archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Archive scripts by category
    archived_count = 0
    for category, scripts in ARCHIVE_CATEGORIES.items():
        category_dir = archive_dir / category
        
        if not dry_run:
            category_dir.mkdir(exist_ok=True)
        
        for script in scripts:
            if script in scripts_to_archive:
                src = scripts_dir / script
                if src.exists():
                    if dry_run:
                        print(f"   Would archive: {script} → archive/{category}/")
                    else:
                        dst = category_dir / script
                        shutil.move(str(src), str(dst))
                        print(f"   ✓ Archived: {script} → {category}/")
                    archived_count += 1
    
    # Archive any remaining scripts
    remaining = scripts_to_archive - set(sum(ARCHIVE_CATEGORIES.values(), []))
    if remaining:
        misc_dir = archive_dir / 'misc'
        if not dry_run:
            misc_dir.mkdir(exist_ok=True)
        
        for script in remaining:
            src = scripts_dir / script
            if src.exists():
                if dry_run:
                    print(f"   Would archive: {script} → archive/misc/")
                else:
                    dst = misc_dir / script
                    shutil.move(str(src), str(dst))
                    print(f"   ✓ Archived: {script} → misc/")
                archived_count += 1
    
    # Create organized structure for remaining scripts
    if not dry_run:
        print("\n📁 Creating organized structure...")
        
        # Create subdirectories
        subdirs = {
            'processing': ['process_tasks.py', 'process_sessions.py', 
                          'realtime_processor.py', 'screenshot_processor.py'],
            'ai': ['ai_cli.py', 'generate_embeddings_simple.py', 'vlm_processor.py'],
            'analysis': ['comparison_cli.py', 'pipeline_monitor.py'],
            'utils': ['test_dashboard.py', 'cleanup_scripts.py'],
            'bin': ['start_all.sh', 'stop_all.sh', 'start_processor.sh']
        }
        
        for subdir, scripts in subdirs.items():
            subdir_path = scripts_dir / subdir
            subdir_path.mkdir(exist_ok=True)
            
            for script in scripts:
                src = scripts_dir / script
                if src.exists():
                    dst = subdir_path / script
                    shutil.copy2(str(src), str(dst))
                    print(f"   ✓ Organized: {script} → {subdir}/")
    
    print(f"\n✅ Cleanup complete!")
    print(f"   Scripts archived: {archived_count}")
    print(f"   Scripts remaining: {len(KEEP_SCRIPTS)}")
    
    if dry_run:
        print("\n💡 Run with --execute to perform the cleanup")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up scripts folder')
    parser.add_argument('--execute', action='store_true',
                        help='Actually perform the cleanup (default is dry run)')
    
    args = parser.parse_args()
    cleanup_scripts(dry_run=not args.execute)


if __name__ == "__main__":
    main()