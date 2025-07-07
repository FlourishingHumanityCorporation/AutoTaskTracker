"""API endpoints for dashboard data."""

import streamlit as st
import json
from datetime import datetime
from autotasktracker.dashboards.data.repositories import MetricsRepository


def setup_api_endpoints():
    """Set up API endpoints in Streamlit app."""
    
    # Check for API mode in query params
    query_params = st.query_params
    
    if query_params.get('api') == 'metrics':
        # API mode - return JSON data
        date_range = query_params.get('range', 'today')
        
        # Calculate dates based on range
        now = datetime.now()
        if date_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            # Add more ranges as needed
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get metrics
        repo = MetricsRepository()
        summary = repo.get_metrics_summary(start_date, end_date)
        
        # Return as JSON
        response = {
            'timestamp': now.isoformat(),
            'date_range': date_range,
            'metrics': summary
        }
        
        # Use st.json to display JSON response
        st.json(response)
        
        # Stop further execution
        st.stop()


def get_dashboard_state():
    """Get current dashboard state programmatically."""
    return {
        'metrics': st.session_state.get('current_metrics', {}),
        'filters': st.session_state.get('current_filters', {}),
        'timestamp': datetime.now().isoformat()
    }