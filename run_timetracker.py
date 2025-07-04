#!/usr/bin/env python3
"""
Simple wrapper to run the timetracker dashboard.
This avoids import path issues when running directly.
"""

import sys
import os

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the timetracker dashboard
def main():
    """Run the timetracker dashboard."""
    try:
        import streamlit as st
        from autotasktracker.dashboards.timetracker import main as timetracker_main
        timetracker_main()
    except Exception as e:
        import streamlit as st
        st.error(f"Timetracker error: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()