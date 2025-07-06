#!/usr/bin/env python3
"""Create baseline performance metrics for dashboards before refactoring."""

import time
import json
import psutil
import subprocess
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardPerformanceProfiler:
    """Profile dashboard performance metrics."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "dashboards": {},
            "system_info": self.get_system_info()
        }
    
    def get_system_info(self):
        """Get system information."""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "python_version": subprocess.check_output(["python", "--version"]).decode().strip()
        }
    
    def measure_dashboard_startup(self, dashboard_name: str, port: int):
        """Measure dashboard startup time and initial render."""
        logger.info(f"Measuring {dashboard_name} startup performance...")
        
        # Start dashboard process
        start_time = time.time()
        process = subprocess.Popen(
            ["python", "autotasktracker.py", dashboard_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for dashboard to be ready (check for port availability)
        ready = False
        timeout = 30
        while not ready and time.time() - start_time < timeout:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                if result == 0:
                    ready = True
            except Exception:
                pass
            time.sleep(0.5)
        
        startup_time = time.time() - start_time
        
        # Measure memory usage
        memory_usage = psutil.Process(process.pid).memory_info().rss / 1024 / 1024  # MB
        
        # Clean up
        process.terminate()
        process.wait()
        
        return {
            "startup_time": startup_time,
            "memory_usage_mb": memory_usage,
            "ready": ready
        }
    
    def profile_all_dashboards(self):
        """Profile all dashboards."""
        dashboards = [
            ("dashboard", 8502),
            ("analytics", 8503),
            ("timetracker", 8505)
        ]
        
        for dashboard_name, port in dashboards:
            metrics = self.measure_dashboard_startup(dashboard_name, port)
            self.results["dashboards"][dashboard_name] = metrics
            logger.info(f"{dashboard_name}: {metrics}")
            time.sleep(2)  # Cool down between tests
    
    def save_results(self):
        """Save baseline results."""
        output_dir = Path("tests/performance/baselines")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"dashboard_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Baseline saved to: {output_file}")
        return output_file

def main():
    """Run performance baseline measurement."""
    profiler = DashboardPerformanceProfiler()
    
    logger.info("Starting dashboard performance baseline measurement...")
    logger.info("This will start and stop each dashboard to measure startup time.")
    
    profiler.profile_all_dashboards()
    output_file = profiler.save_results()
    
    # Print summary
    print("\n=== Dashboard Performance Baseline ===")
    for dashboard, metrics in profiler.results["dashboards"].items():
        print(f"\n{dashboard.upper()}:")
        print(f"  Startup Time: {metrics['startup_time']:.2f}s")
        print(f"  Memory Usage: {metrics['memory_usage_mb']:.1f} MB")
        print(f"  Ready: {metrics['ready']}")
    
    print(f"\nBaseline saved to: {output_file}")

if __name__ == "__main__":
    main()