#!/bin/bash
# Start the AutoTaskTracker screenshot processor

cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the processor
echo "Starting AutoTaskTracker Screenshot Processor..."
echo "Press Ctrl+C to stop"

python scripts/screenshot_processor.py --interval 30