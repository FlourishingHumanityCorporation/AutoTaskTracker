#!/usr/bin/env python3
"""
Simple wrapper to run the notifications dashboard.
This avoids import path issues when running directly.
"""

import sys
import os

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the notifications dashboard
def main():
    """Run the notifications dashboard."""
    try:
        import streamlit as st
        from autotasktracker.dashboards.notifications import main as notifications_main
        notifications_main()
    except Exception as e:
        import streamlit as st
        st.error(f"Notifications error: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()