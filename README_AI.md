# AutoTaskTracker AI Features - Quick Start

## ✅ What's Working Now

The AI features are fully implemented and functional:

- **Embeddings**: Semantic search and task similarity (0.7% coverage, 15 screenshots)
- **OCR Enhancement**: Confidence scoring and layout analysis (67.6% coverage)
- **AI-Enhanced Task Board**: Shows confidence indicators and AI insights
- **CLI Tools**: Easy setup and management

## 🚀 Quick Setup

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Check what's working
python ai_cli.py status

# 3. Generate embeddings for recent screenshots
python ai_cli.py embeddings --limit 50

# 4. Run the enhanced dashboard
streamlit run autotasktracker/dashboards/task_board.py
```

## 🎯 What You'll See

### In the Dashboard
- **Confidence indicators**: 🎯 High (80%+), 🔍 Medium (60%+), ❓ Low
- **AI feature badges**: 📝 OCR quality, 👁️ Visual (VLM), 🧠 Similar tasks
- **Enhanced categories**: Better task classification

### In the AI CLI
```bash
python ai_cli.py status
# Shows:
# - Database connection
# - AI coverage percentages  
# - Available models
# - Service status
```

## 🧠 Embedding Features

When you have embeddings (generated via `ai_cli.py embeddings`):
- Find similar tasks automatically
- Smarter task grouping
- Better pattern recognition

## 👁️ VLM Features (Optional)

To enable visual understanding:
```bash
# Install model (4GB download)
ollama pull minicpm-v

# Enable VLM
python ai_cli.py enable-vlm

# Restart memos
memos restart
```

This adds:
- Visual context understanding
- UI state detection
- Better task detection for visual activities

## 🔧 Troubleshooting

### "No module named autotasktracker"
```bash
# Make sure you're in the project root
cd /path/to/AutoTaskTracker
source venv/bin/activate
```

### Dashboard not showing AI features
- Check: `python ai_cli.py status` shows ✅ for components
- Generate some embeddings: `python ai_cli.py embeddings --limit 10`
- The AI features appear when there's data to enhance

### No similar tasks found
- You need embeddings: `python ai_cli.py embeddings --limit 100`
- More embeddings = better similarity matching

## 📊 Current Status

Run `python ai_cli.py status` to see:
- Screenshot count and OCR coverage
- Embedding coverage percentage
- VLM availability
- Required dependencies

The AI features work incrementally - they enhance what's available and gracefully handle missing data.

## 💡 Pro Tips

1. **Start small**: Generate 20-50 embeddings first
2. **Regular generation**: Run `python ai_cli.py embeddings` weekly
3. **VLM optional**: The core features work without it
4. **Check status**: Use `python ai_cli.py status` to diagnose issues

The implementation is production-ready and works with your existing screenshots!