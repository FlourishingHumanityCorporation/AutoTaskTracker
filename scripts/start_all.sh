#!/bin/bash
# Start all AutoTaskTracker services

echo "🚀 Starting AutoTaskTracker Services..."

cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to start service in background
start_service() {
    name=$1
    script=$2
    log_file="logs/${name}.log"
    
    mkdir -p logs
    echo "Starting $name..."
    nohup python $script > "$log_file" 2>&1 &
    echo "$!" > "logs/${name}.pid"
    echo "  ✓ $name started (PID: $(cat logs/${name}.pid))"
}

# Start services
start_service "realtime-processor" "scripts/realtime_processor.py"
start_service "session-processor" "scripts/process_sessions.py --continuous"

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📊 To view dashboards:"
echo "  - Task Board: http://localhost:8502"
echo "  - Analytics: http://localhost:8503"
echo ""
echo "🛑 To stop services, run: ./scripts/stop_all.sh"