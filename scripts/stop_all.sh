#!/bin/bash
# Stop all AutoTaskTracker services

echo "🛑 Stopping AutoTaskTracker Services..."

cd "$(dirname "$0")/.."

# Function to stop service
stop_service() {
    name=$1
    pid_file="logs/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping $name (PID: $pid)..."
            kill $pid
            rm "$pid_file"
            echo "  ✓ $name stopped"
        else
            echo "  ! $name not running (stale PID file)"
            rm "$pid_file"
        fi
    else
        echo "  - $name not running"
    fi
}

# Stop services
stop_service "realtime-processor"
stop_service "session-processor"

echo ""
echo "✅ All services stopped"