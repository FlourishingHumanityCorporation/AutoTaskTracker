#!/usr/bin/env python3
"""
Simple wrapper to run the task board dashboard.
This avoids import path issues when running directly.
"""

import sys
import os

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the dashboard class directly
from autotasktracker.dashboards.task_board_refactored import TaskBoardDashboard

def main():
    """Run the task board dashboard."""
    try:
        dashboard = TaskBoardDashboard()
        dashboard.run()
    except Exception as e:
        import streamlit as st
        st.error(f"Dashboard error: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()