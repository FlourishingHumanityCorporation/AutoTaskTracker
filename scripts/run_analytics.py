#!/usr/bin/env python3
"""Runner for Analytics dashboard"""
import streamlit as st
st.set_page_config(page_title="AutoTaskTracker - Analytics", page_icon="📊", layout="wide")

from autotasktracker.dashboards.analytics import main

if __name__ == "__main__":
    main()