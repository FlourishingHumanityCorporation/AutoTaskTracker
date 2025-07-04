#!/usr/bin/env python3
"""Runner for Time Tracker dashboard"""
import streamlit as st
st.set_page_config(page_title="AutoTaskTracker - Time Tracker", page_icon="⏱️", layout="wide")

from autotasktracker.dashboards.timetracker import main

if __name__ == "__main__":
    main()