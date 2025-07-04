#!/usr/bin/env python3
"""
Simple wrapper to run the VLM monitor dashboard.
This avoids import path issues when running directly.
"""

import sys
import os

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the VLM monitor dashboard
def main():
    """Run the VLM monitor dashboard."""
    try:
        import streamlit as st
        from autotasktracker.dashboards.vlm_monitor import main as vlm_monitor_main
        vlm_monitor_main()
    except Exception as e:
        import streamlit as st
        st.error(f"VLM Monitor error: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()