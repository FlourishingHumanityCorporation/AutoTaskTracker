#!/usr/bin/env python3
"""
Time Tracker Dashboard Runner
Runs the time tracker dashboard with proper environment setup
"""

import os
import sys
import subprocess

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def main():
    """Run the time tracker dashboard"""
    # Use the virtual environment Python and streamlit
    venv_python = os.path.join(project_root, 'venv', 'bin', 'python')
    
    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        sys.exit(1)
    
    # Run streamlit with the time tracker dashboard
    dashboard_path = os.path.join(project_root, 'autotasktracker', 'dashboards', 'timetracker.py')
    
    cmd = [
        venv_python, '-m', 'streamlit', 'run', 
        dashboard_path,
        '--server.port=8505',
        '--server.headless=true'
    ]
    
    print(f"Starting Time Tracker Dashboard on port 8505...")
    print(f"Access at: http://localhost:8505")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nTime Tracker Dashboard stopped by user")
    except Exception as e:
        print(f"Error running Time Tracker Dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()