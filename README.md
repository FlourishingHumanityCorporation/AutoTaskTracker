# AutoTaskTracker

AI-powered passive task discovery from screenshots. No manual logging required.

AutoTaskTracker captures screenshots every few seconds and uses OCR/AI to automatically understand your activities, providing beautiful dashboards showing productivity patterns and task history.

## Features

- **Automatic Screenshot Capture** - Passive background operation
- **AI-Powered Analysis** - OCR, embeddings, and optional VLM processing
- **Live Dashboards** - Task board, analytics, and time tracking
- **Smart Categorization** - Automatic activity classification


## Quick Start

```bash
# Clone and install
git clone https://github.com/FlourishingHumanityCorporation/AutoTaskTracker.git
cd AutoTaskTracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize and start
memos init
python autotasktracker.py start
```

Dashboards automatically open at:
- Task Board: http://localhost:8502
- Analytics: http://localhost:8503

## Usage

### Task Board Dashboard
Real-time view of activities with automatic task grouping and OCR text extraction.

### Analytics Dashboard  
Productivity metrics, activity distribution charts, and focus session tracking.

### Daily Workflow
1. AutoTaskTracker runs automatically in background
2. Check dashboards anytime for progress insights
3. Review analytics for productivity patterns
4. Export data for reports as needed

## Resource Usage

- **CPU**: <5% average
- **RAM**: ~200MB
- **Storage**: ~400MB/day screenshots
- **Network**: None (local only)

## Commands

```bash
python autotasktracker.py start      # Start all services
python autotasktracker.py dashboard  # Task board only  
python autotasktracker.py analytics  # Analytics only
python autotasktracker.py status     # Check status
python autotasktracker.py stop       # Stop everything
```

## Configuration

Edit `~/.memos/config.yaml`:
- `record_interval`: Screenshot frequency (default: 4 seconds)
- `ocr.enabled`: Toggle OCR processing
- `vlm`: Enable VLM features (requires Ollama)

## Data Captured

- Window titles and application names
- OCR text from screenshots
- Timestamps and activity duration
- Focus sessions and productivity patterns

## Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file.

## Built With

- [Memos/Pensieve](https://github.com/arkohut/memos) - Screenshot capture
- [Streamlit](https://streamlit.io) - Dashboard framework  
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - OCR engine