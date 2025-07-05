# Start AutoTaskTracker Dashboards

Launch the AutoTaskTracker dashboard ecosystem.

## Instructions for Claude:

1. **Check Prerequisites**:
   ```bash
   # Verify Pensieve is running
   memos ps
   
   # Check for port conflicts
   lsof -i :8502 -i :8503 -i :8505 2>/dev/null || echo "Ports available"
   ```

2. **Start Dashboard Launcher**:
   ```bash
   python autotasktracker.py launcher
   ```
   
   **Alternative - Start Individual Dashboards**:
   ```bash
   # Main task board (port 8502)
   python autotasktracker.py dashboard &
   
   # Analytics dashboard (port 8503)  
   python autotasktracker.py analytics &
   
   # Time tracker (port 8505)
   python autotasktracker.py timetracker &
   ```

3. **Verify Dashboard Status**:
   ```bash
   # Check if dashboards are running
   curl -s http://localhost:8502 > /dev/null && echo "Task Board: ✅" || echo "Task Board: ❌"
   curl -s http://localhost:8503 > /dev/null && echo "Analytics: ✅" || echo "Analytics: ❌"  
   curl -s http://localhost:8505 > /dev/null && echo "Time Tracker: ✅" || echo "Time Tracker: ❌"
   ```

4. **Report URLs**:
   - Task Board: http://localhost:8502
   - Analytics: http://localhost:8503
   - Time Tracker: http://localhost:8505

This command starts the complete AutoTaskTracker dashboard ecosystem.