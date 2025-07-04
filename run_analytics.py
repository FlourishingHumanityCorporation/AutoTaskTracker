#!/usr/bin/env python3
"""
Simple wrapper to run the analytics dashboard.
This avoids import path issues when running directly.
"""

import sys
import os

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the dashboard class directly
from autotasktracker.dashboards.analytics_refactored import AnalyticsDashboard

def main():
    """Run the analytics dashboard."""
    try:
        dashboard = AnalyticsDashboard()
        dashboard.run()
    except Exception as e:
        import streamlit as st
        st.error(f"Dashboard error: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()