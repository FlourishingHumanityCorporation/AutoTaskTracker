# 🤖 AutoTaskTracker

**Automatically discover what you're working on using AI** - No manual logging required!

AutoTaskTracker runs quietly in the background, capturing screenshots and using OCR/AI to understand your activities. Get beautiful dashboards showing your productivity patterns and task history.

## ✨ Features

- 📸 **Automatic Screenshot Capture** - Every few seconds, completely passive
- 🔍 **AI-Powered Text Extraction** - OCR processes all captured screens  
- 📊 **Live Analytics Dashboard** - Real-time productivity insights
- 📈 **Task Categorization** - Automatically groups activities (Coding, Communication, etc.)
- 💾 **Data Export** - Download your data as CSV, JSON, or reports
- 🖥️ **System Tray Integration** - Runs quietly in the background

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/FlourishingHumanityCorporation/AutoTaskTracker.git
cd AutoTaskTracker

# Install (one-time setup)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install memos  # Install separately if needed

# Initialize memos
memos init

# Start everything!
python autotasktracker.py start
```

**That's it!** Your browser will open with:
- Task Board: http://localhost:8502
- Analytics: http://localhost:8503

## 📸 Screenshots

### Task Board - See What You're Working On
- Live view of captured activities
- Auto-refreshes every 30 seconds
- Groups similar tasks together
- Shows OCR-extracted text

### Analytics Dashboard - Understand Your Patterns  
- Daily/weekly productivity metrics
- Activity distribution charts
- Focus session tracking
- Export data anytime

## 🎯 Live Use Tips

### Make it Start Automatically

**macOS**: Add to Login Items
1. Open System Preferences → Users & Groups
2. Click Login Items
3. Add `/path/to/AutoTaskTracker/start.sh`

**Linux**: Use the systemd service (see QUICKSTART.md)

### Optimize Performance

- **Disable screenshots**: Use the toggle in Task Board sidebar
- **Adjust grouping**: Change time intervals for task grouping
- **Clean old data**: `./autotask.py cleanup --days 7`

### Typical Daily Workflow

1. **Morning**: AutoTaskTracker starts with your computer
2. **Throughout the day**: Works silently in background
3. **Anytime**: Check dashboards to see your progress
4. **End of day**: Review analytics for insights
5. **Weekly**: Export data for time tracking/reports

## 📊 Resource Usage

- **CPU**: Minimal (< 5% average)
- **RAM**: ~200MB for all services
- **Storage**: ~400MB/day of screenshots
- **Network**: None - everything is local!

## 🛠️ Commands

```bash
# Start everything
./start.sh

# Or use the control script
./autotask.py           # Start with system tray
./autotask.py console   # Start in console mode  
./autotask.py status    # Check status
./autotask.py stop      # Stop everything
./autotask.py cleanup   # Clean old data
```

## 🔧 Configuration

Edit `~/.memos/config.yaml`:
- `record_interval`: Screenshot frequency (default: 4 seconds)
- `ocr.enabled`: Toggle OCR processing
- `vlm`: Enable advanced AI features (requires Ollama)

## 📈 What Gets Tracked

- Window titles and application names
- Text visible on screen (via OCR)
- Screenshots with timestamps
- Time spent in different applications
- Focus sessions and productivity patterns

## 🤝 Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

Built with:
- [Memos/Pensieve](https://github.com/arkohut/memos) - Screenshot capture engine
- [Streamlit](https://streamlit.io) - Dashboard framework
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - OCR engine

---

**Remember**: The best task tracker is the one you don't have to think about! 🚀