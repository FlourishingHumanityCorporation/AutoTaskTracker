#!/usr/bin/env python3
"""
VLM Optimization Script - Improves VLM processing robustness
"""
import os
import sys
import subprocess
import time
import yaml
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from autotasktracker.core.database import DatabaseManager


class VLMOptimizer:
    """Optimizes VLM processing for better coverage and performance."""
    
    def __init__(self):
        self.config_path = Path.home() / '.memos' / 'config.yaml'
        self.db = DatabaseManager()
        
    def get_current_stats(self):
        """Get current VLM processing statistics."""
        stats = self.db.get_ai_coverage_stats()
        
        # Get recent processing rate
        query = """
        SELECT 
            COUNT(*) as vlm_last_hour
        FROM entities e
        JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
        WHERE e.created_at >= datetime('now', '-1 hour')
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            recent = cursor.fetchone()
            stats['vlm_last_hour'] = recent['vlm_last_hour'] if recent else 0
            
        return stats
    
    def check_ollama_status(self):
        """Check if Ollama is running and responsive."""
        try:
            # Check if ollama is running
            result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return False, "Ollama not running"
                
            # Test VLM model response time
            start = time.time()
            test_cmd = [
                'curl', '-s', '-X', 'POST',
                'http://localhost:11434/api/generate',
                '-d', '{"model": "minicpm-v", "prompt": "test", "options": {"num_predict": 1}}'
            ]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
            response_time = time.time() - start
            
            if result.returncode == 0:
                return True, f"Ollama responsive (test took {response_time:.1f}s)"
            else:
                return False, "Ollama not responding to test"
                
        except subprocess.TimeoutExpired:
            return False, "Ollama timeout"
        except Exception as e:
            return False, f"Ollama check failed: {e}"
    
    def optimize_config(self, aggressive=False):
        """Optimize memos configuration for better VLM processing."""
        # Load current config
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create backup
        backup_path = self.config_path.with_suffix('.yaml.backup')
        with open(backup_path, 'w') as f:
            yaml.dump(config, f)
        
        # Optimize watch settings
        if 'watch' not in config:
            config['watch'] = {}
            
        if aggressive:
            # Aggressive settings for maximum VLM coverage
            config['watch']['processing_interval'] = 1  # Process every file
            config['watch']['sparsity_factor'] = 1.0   # Don't skip any
            config['watch']['rate_window_size'] = 20   # Larger window for stability
            print("✅ Applied aggressive VLM settings (process every screenshot)")
        else:
            # Balanced settings for better VLM coverage
            config['watch']['processing_interval'] = 2  # Process every 2nd file
            config['watch']['sparsity_factor'] = 1.2   # Small adjustment factor
            config['watch']['rate_window_size'] = 15   # Medium window
            print("✅ Applied balanced VLM settings (process every 2nd screenshot)")
        
        # Ensure VLM is enabled
        if 'minicpm_v' in config:
            config['minicpm_v']['enabled'] = True
            # Add performance options
            config['minicpm_v']['timeout'] = 30  # 30 second timeout
            config['minicpm_v']['max_retries'] = 2
            
        # Save optimized config
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        return config
    
    def restart_watch_service(self):
        """Restart memos watch service with optimized settings."""
        print("\n🔄 Restarting watch service...")
        
        # Stop existing watch processes
        subprocess.run(['pkill', '-f', 'memos watch'], capture_output=True)
        time.sleep(2)
        
        # Start new watch service
        env = os.environ.copy()
        env['MEMOS_PROCESSING_WORKERS'] = '2'  # Use 2 workers for better throughput
        
        # Use the memos binary directly
        memos_path = Path(sys.executable).parent / 'memos'
        cmd = [str(memos_path), 'watch']
        process = subprocess.Popen(cmd, env=env, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # Wait a bit and check if it started
        time.sleep(3)
        if process.poll() is None:
            print("✅ Watch service restarted successfully")
            return True
        else:
            print("❌ Watch service failed to start")
            stdout, stderr = process.communicate()
            print(f"Error: {stderr.decode()}")
            return False
    
    def monitor_performance(self, duration_minutes=5):
        """Monitor VLM processing performance."""
        print(f"\n📊 Monitoring VLM performance for {duration_minutes} minutes...")
        
        start_stats = self.get_current_stats()
        start_time = datetime.now()
        
        # Display initial stats
        print(f"\nInitial stats:")
        print(f"  Total screenshots: {start_stats['total_screenshots']}")
        print(f"  VLM processed: {start_stats['vlm_count']} ({start_stats['vlm_percentage']:.1f}%)")
        print(f"  VLM in last hour: {start_stats['vlm_last_hour']}")
        
        # Monitor for specified duration
        check_interval = 30  # Check every 30 seconds
        checks = duration_minutes * 60 // check_interval
        
        for i in range(checks):
            time.sleep(check_interval)
            current_stats = self.get_current_stats()
            
            # Calculate rates
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
            new_vlm = current_stats['vlm_count'] - start_stats['vlm_count']
            new_total = current_stats['total_screenshots'] - start_stats['total_screenshots']
            
            vlm_rate = new_vlm / elapsed_minutes if elapsed_minutes > 0 else 0
            total_rate = new_total / elapsed_minutes if elapsed_minutes > 0 else 0
            coverage_rate = (new_vlm / new_total * 100) if new_total > 0 else 0
            
            print(f"\n[{elapsed_minutes:.1f} min] Progress:")
            print(f"  New screenshots: {new_total} ({total_rate:.1f}/min)")
            print(f"  New VLM processed: {new_vlm} ({vlm_rate:.1f}/min)")
            print(f"  Coverage rate: {coverage_rate:.1f}%")
            print(f"  Total VLM: {current_stats['vlm_count']} ({current_stats['vlm_percentage']:.1f}%)")
        
        # Final report
        final_stats = self.get_current_stats()
        total_new_vlm = final_stats['vlm_count'] - start_stats['vlm_count']
        total_new_screenshots = final_stats['total_screenshots'] - start_stats['total_screenshots']
        
        print(f"\n📈 Final Report:")
        print(f"  Duration: {duration_minutes} minutes")
        print(f"  New VLM processed: {total_new_vlm}")
        print(f"  New screenshots: {total_new_screenshots}")
        print(f"  Effective coverage: {total_new_vlm / total_new_screenshots * 100:.1f}%" if total_new_screenshots > 0 else "N/A")
        
        return total_new_vlm, total_new_screenshots
    
    def create_health_check_script(self):
        """Create a health check script for continuous monitoring."""
        script_content = '''#!/bin/bash
# VLM Health Check Script - Run via cron for continuous monitoring

source $PROJECT_DIR/venv/bin/activate

# Check if watch service is running
if ! pgrep -f "memos watch" > /dev/null; then
    echo "$(date): Watch service not running, restarting..."
    cd "$PROJECT_DIR"
    python scripts/vlm_optimizer.py --restart
fi

# Check VLM processing rate
python -c "
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
stats = db.get_ai_coverage_stats()
if stats['vlm_percentage'] < 10:
    print(f'$(date): VLM coverage low: {stats[\"vlm_percentage\"]:.1f}%')
"
'''
        
        health_check_path = Path(__file__).parent / 'vlm_health_check.sh'
        with open(health_check_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(health_check_path, 0o755)
        print(f"\n✅ Created health check script: {health_check_path}")
        print("   Add to crontab: */5 * * * * /path/to/vlm_health_check.sh")
        
        return health_check_path


def main():
    """Main function to run VLM optimization."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VLM Processing Optimizer')
    parser.add_argument('--aggressive', action='store_true', 
                       help='Use aggressive settings for maximum coverage')
    parser.add_argument('--monitor', type=int, metavar='MINUTES',
                       help='Monitor performance for N minutes')
    parser.add_argument('--restart', action='store_true',
                       help='Just restart the watch service')
    parser.add_argument('--health-check', action='store_true',
                       help='Create health check script')
    
    args = parser.parse_args()
    
    optimizer = VLMOptimizer()
    
    print("🔧 VLM Processing Optimizer")
    print("=" * 40)
    
    # Show current status
    stats = optimizer.get_current_stats()
    print(f"\n📊 Current Status:")
    print(f"  Total screenshots: {stats['total_screenshots']}")
    print(f"  VLM coverage: {stats['vlm_percentage']:.1f}% ({stats['vlm_count']} processed)")
    print(f"  OCR coverage: {stats['ocr_percentage']:.1f}%")
    print(f"  VLM in last hour: {stats['vlm_last_hour']}")
    
    # Check Ollama
    ollama_ok, ollama_msg = optimizer.check_ollama_status()
    print(f"\n🤖 Ollama Status: {'✅' if ollama_ok else '❌'} {ollama_msg}")
    
    if not ollama_ok:
        print("\n⚠️  Ollama issues detected. Please ensure Ollama is running:")
        print("   ollama serve")
        return
    
    if args.restart:
        optimizer.restart_watch_service()
        return
        
    if args.health_check:
        optimizer.create_health_check_script()
        return
    
    # Optimize configuration
    print(f"\n⚙️  Optimizing configuration...")
    config = optimizer.optimize_config(aggressive=args.aggressive)
    
    # Restart watch service
    if optimizer.restart_watch_service():
        print("\n✅ Optimization complete!")
        
        # Monitor if requested
        if args.monitor:
            optimizer.monitor_performance(args.monitor)
    else:
        print("\n❌ Failed to restart watch service")
        print("   Please check logs: tail -f ~/.memos/logs/watch.log")


if __name__ == '__main__':
    main()