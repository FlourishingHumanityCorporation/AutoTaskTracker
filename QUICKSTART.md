# 🚀 AutoTaskTracker Quick Start Guide

## One-Command Start

```bash
./autotask.py
```

That's it! AutoTaskTracker will:
- ✅ Start capturing screenshots automatically
- ✅ Process them with OCR
- ✅ Open dashboards in your browser
- ✅ Run in system tray (or console if not available)

## What You'll See

### 1. Task Board (http://localhost:8502)
- Live view of your current activities
- Auto-refreshes every 30 seconds
- Shows screenshots and extracted text
- Groups similar activities together

### 2. Analytics Dashboard (http://localhost:8503)
- Productivity metrics and insights
- Activity distribution charts
- Focus session analysis
- Export your data anytime

### 3. Time Tracker (http://localhost:8504)
- Detailed time tracking for every task
- See exactly how long you spent on each activity
- Timeline view of your day
- Export time sheets for billing/reporting

## Keyboard Shortcuts (Console Mode)

When running in console mode:
- `status` - Check system status
- `open task` - Open task board
- `open analytics` - Open analytics  
- `cleanup` - Remove old data
- `quit` - Stop everything

## Make It Start Automatically

### macOS
```bash
# Create launch agent
cat > ~/Library/LaunchAgents/com.autotasktracker.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.autotasktracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PWD/autotask.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$PWD</string>
</dict>
</plist>
EOF

# Load it
launchctl load ~/Library/LaunchAgents/com.autotasktracker.plist
```

### Linux (systemd)
```bash
# Create service file
sudo tee /etc/systemd/system/autotasktracker.service << EOF
[Unit]
Description=AutoTaskTracker
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=$PWD/autotask.py --no-tray
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable autotasktracker
sudo systemctl start autotasktracker
```

## Tips for Best Results

1. **Let it run continuously** - The more data, the better insights
2. **Check analytics weekly** - See your productivity patterns
3. **Export data regularly** - Keep backups of your task history
4. **Adjust grouping interval** - Find what works for your workflow

## Storage Management

AutoTaskTracker uses about:
- 400MB per day of screenshots
- 8GB per month

To clean old data:
```bash
./autotask.py cleanup --days 7  # Keep only last 7 days
```

## Troubleshooting

If nothing appears:
1. Check if memos is running: `memos ps`
2. Wait a few minutes for data to accumulate
3. Refresh the dashboards

## Stop Everything

```bash
./autotask.py stop
```

Or just press Ctrl+C if running in console mode.