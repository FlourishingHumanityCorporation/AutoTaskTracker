#!/usr/bin/env python
"""Check what the dashboard is currently showing."""

import requests
import re

try:
    # Get dashboard HTML
    response = requests.get("http://localhost:8602")
    html = response.text
    
    # Extract metrics using regex
    # Look for metric values
    metrics_pattern = r'<div[^>]*data-testid="metric-value"[^>]*>([^<]+)</div>'
    total_pattern = r'Total Activities[^<]*<[^>]*>([0-9,]+)'
    
    print("Dashboard Status:")
    print(f"   Response status: {response.status_code}")
    
    # Try to find total activities
    total_match = re.search(total_pattern, html, re.IGNORECASE)
    if total_match:
        print(f"   Total Activities shown: {total_match.group(1)}")
    else:
        # Look for any number near "Total Activities"
        pattern2 = r'Total Activities[^0-9]*([0-9,]+)'
        match2 = re.search(pattern2, html)
        if match2:
            print(f"   Total Activities shown: {match2.group(1)}")
        else:
            print("   Could not find Total Activities metric")
    
    # Save a snippet for inspection
    with open("/tmp/dashboard_snippet.html", "w") as f:
        f.write(html[:5000])
    print("\n   Saved HTML snippet to /tmp/dashboard_snippet.html")
    
except Exception as e:
    print(f"Error: {e}")
    print("Make sure the dashboard is running on http://localhost:8602")