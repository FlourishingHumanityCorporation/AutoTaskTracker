#!/bin/bash
# Quick dashboard status check

echo "🔍 AutoTaskTracker Dashboard Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if dashboard is running
if pgrep -f "streamlit run.*task_board.py" > /dev/null; then
    echo "✅ Dashboard: RUNNING (http://localhost:8602)"
else
    echo "❌ Dashboard: NOT RUNNING"
fi

# Check Pensieve/Memos status
if pgrep -f "memos.*server" > /dev/null; then
    echo "✅ Pensieve: RUNNING"
else
    echo "❌ Pensieve: NOT RUNNING"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get current metrics
python "$(dirname "$0")/get_metrics.py" 2>/dev/null