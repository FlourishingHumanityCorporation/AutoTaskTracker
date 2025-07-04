#!/bin/bash
# AutoTaskTracker - Simple Start Script

cd "$(dirname "$0")"

echo "🚀 Starting AutoTaskTracker..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Start everything
./autotask.py

echo ""
echo "✅ AutoTaskTracker stopped"