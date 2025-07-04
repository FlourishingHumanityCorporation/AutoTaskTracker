#!/usr/bin/env python3
"""Runner for Task Board dashboard"""
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
st.set_page_config(page_title="AutoTaskTracker - Task Board", page_icon="📋", layout="wide")

from autotasktracker.dashboards.task_board import main

if __name__ == "__main__":
    main()