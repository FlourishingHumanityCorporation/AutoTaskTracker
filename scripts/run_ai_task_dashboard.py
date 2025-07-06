#!/usr/bin/env python3
"""
Run the AI Task Explorer dashboard.

This script launches the Streamlit-based dashboard for viewing AI-extracted tasks.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the AI Task Explorer dashboard."""
    try:
        from autotasktracker.dashboards.ai_task_dashboard import AITaskDashboard
        
        logger.info("Starting AI Task Explorer dashboard...")
        dashboard = AITaskDashboard()
        dashboard.run()
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Make sure you have installed all required dependencies.")
        logger.error("Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running dashboard: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
