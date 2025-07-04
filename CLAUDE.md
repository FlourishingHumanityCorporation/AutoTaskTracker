# AutoTaskTracker - Mission Critical Context

IMPROVE THE CURRENT FILE RATHER THAN CREATING A NEW FILE THAT'S CALLED FILE_IMPROVED!!!


## Project Overview
AutoTaskTracker is an AI-powered application that passively discovers and organizes daily tasks from screenshots. It runs continuously in the background, capturing screen activity and using AI to infer completed tasks without manual logging.

## Core Requirements
- **Passive Operation**: Must run unobtrusively in the background without impacting system performance
- **AI-Powered Analysis**: Uses OCR, object detection, and LLMs to understand screen content
- **Engaging Interface**: Custom task board showing discovered tasks and productivity insights
- **Automated Discovery**: Automatically identifies and categorizes tasks from screen activity

## Technical Architecture

### Backend (Python/Pensieve)
- **Pensieve** (memos): Open-source Python package for screenshot capture and AI analysis
- Three core services:
  - `memos record`: Captures screenshots at regular intervals
  - `memos watch`: Queues screenshots for AI processing
  - `memos serve`: Provides REST API and web interface
- Data stored in `~/.memos/` directory (config, SQLite DB, screenshots)
- AI Pipeline: Screenshot → OCR → Embeddings → Task Classification

### Frontend (Streamlit)
- Custom dashboard at `task_board.py`
- Connects directly to Pensieve SQLite database
- Displays tasks with screenshots, timestamps, and AI-generated summaries
- Real-time updates as new tasks are discovered

### AI Components
- **OCR**: Tesseract or EasyOCR for text extraction
- **Embeddings**: jinaai/jina-embeddings-v2-base-en for semantic search
- **Optional LLM**: Ollama with minicpm-v model for advanced task summarization
- **UI Detection**: YOLOv8n for identifying buttons, forms, etc.

## Critical Commands
```bash
# Setup
python3 -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install memos streamlit pandas plotly

# Initialize and start Pensieve
memos init
memos enable
memos start

# Check status
memos ps

# View logs
ls ~/.memos/logs/

# Run custom dashboard
./venv/bin/streamlit run task_board.py

# Run analytics dashboard
./venv/bin/streamlit run task_analytics.py --server.port 8503

# Or run in background
./venv/bin/streamlit run task_board.py --server.headless true --server.port 8502 &
./venv/bin/streamlit run task_analytics.py --server.headless true --server.port 8503 &
```

## Key File Locations
- Config: `~/.memos/config.yaml`
- Database: `~/.memos/database.db`
- Screenshots: `~/.memos/screenshots/`
- Logs: `~/.memos/logs/`

## Database Schema (Key Tables)
- `entities`: Contains file info including screenshots (filepath, created_at, last_scan_at)
- `metadata_entries`: Contains OCR text and active window data linked to entities
- Query pattern: 
```sql
SELECT e.*, me.metadata_value as ocr_text 
FROM entities e 
LEFT JOIN metadata_entries me ON e.id = me.entity_id 
WHERE e.file_type_group = 'image'
```

## Performance Considerations
- Screenshots: ~400MB/day, ~8GB/month storage
- CPU-only OCR is acceptable, but LLM features require GPU (8GB+ VRAM)
- Use pagination and thumbnails in dashboard to handle large datasets
- Configure retention policy in config.yaml to manage disk usage

## Common Issues & Solutions
1. **High resource usage**: Disable LLM features, use CPU-only mode
2. **Disk space**: Set appropriate retention in config.yaml
3. **Port conflicts**: Memos uses 8839, Streamlit uses 8502 by default
4. **No screenshots appearing**: Check `memos ps`, verify screen capture permissions
5. **Database not found**: Memos uses `database.db` not `memos.db`

## Development Priorities
1. ✅ Core functionality with Pensieve backend (Complete)
2. ✅ Basic Streamlit dashboard for task visualization (Complete)
3. Performance optimization (quantization, caching)
4. Advanced LLM integration (optional, requires GPU)

## Testing & Validation
- Verify screenshot capture: Check `~/.memos/screenshots/` directory
- Test OCR accuracy: Use `memos` web UI at http://localhost:8839
- Monitor performance: Watch CPU/memory usage during operation
- Validate task detection: Review activities in Streamlit dashboard at http://localhost:8502

## Deployment Notes
- Screenshots may contain sensitive information
- Consider cloud sync for backup and multi-device access
- Monitor storage usage as screenshots accumulate
- Configure appropriate retention policies

## Current Project Status
- ✅ Memos/Pensieve backend installed and running
- ✅ Screenshot capture working (780+ screenshots captured)
- ✅ Database integration functional
- ✅ Streamlit dashboard created and operational
- ✅ Task Analytics Dashboard with productivity insights
- ✅ All tests passing (9/9) including Playwright e2e tests
- ✅ OCR processing fully functional (585+ results)
- ✅ Task categorization implemented
- ✅ Export functionality (CSV, JSON, TXT reports)

## Future Enhancements
- ✅ Task categorization and analytics (IMPLEMENTED)
- API integration with external task boards (Trello, Asana)
- Multimodal LLMs for better task understanding
- Automated task pattern recognition
- Enhanced UI element detection with YOLO models
- Advanced search and filtering capabilities
- Custom task rules and automation