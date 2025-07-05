# AutoTaskTracker Auto Processor

## Overview

The AutoTaskTracker Auto Processor automatically handles OCR text extraction and task categorization for screenshots captured by Pensieve. It runs in the background to ensure all screenshots are processed with minimal manual intervention.

## Root Cause Analysis

The original issue was that Pensieve was capturing screenshots but the built-in OCR plugin wasn't processing them automatically. This led to:

- 2,512 screenshots captured
- 0% OCR coverage initially  
- Dashboard showing empty data
- Broken data pipeline: Screenshots → (missing OCR) → No task extraction

## Solution

Created an automatic processor that:

1. **OCR Processing**: Uses `ocrmac` (macOS) or `pytesseract` (fallback) to extract text from screenshots
2. **Task Extraction**: Analyzes window titles and OCR text to identify tasks and activities
3. **Categorization**: Automatically categorizes activities (Coding, AI Tools, Communication, etc.)
4. **Background Processing**: Runs continuously to process new screenshots

## Current Status

After implementing the auto processor:

- **OCR Coverage**: 12.2% (307/2,512 screenshots)
- **Task Coverage**: 18.0% (453/2,512 screenshots)  
- **OCR Capability**: ✅ Working (ocrmac available)
- **Dashboard**: ✅ Displaying processed data with tasks and categories
- **Database**: ✅ Fully functional

## Usage

### Start Auto Processor (Background)

```bash
# Start with default 30-second interval
python scripts/start_auto_processor.py start

# Start with custom interval
python scripts/start_auto_processor.py start --interval 60

# Start in foreground (for debugging)
python scripts/start_auto_processor.py start --foreground
```

### Check Status

```bash
python scripts/start_auto_processor.py status
```

### Stop Auto Processor

```bash
python scripts/start_auto_processor.py stop
```

### Restart Auto Processor

```bash
python scripts/start_auto_processor.py restart
```

### Run Single Batch (Manual)

```bash
# Process one batch and exit
python scripts/start_auto_processor.py run

# Or run directly
python scripts/processing/auto_processor.py --batch
```

## Processing Pipeline

1. **Screenshot Capture**: Pensieve captures screenshots automatically
2. **OCR Processing**: Auto processor extracts text using ocrmac
3. **Task Extraction**: Analyzes window titles and OCR text to identify tasks
4. **Categorization**: Automatically assigns categories based on application/content
5. **Dashboard Display**: Processed data appears in AutoTaskTracker dashboards

## Files

- `scripts/processing/auto_processor.py` - Main auto processor script
- `scripts/start_auto_processor.py` - Startup/management script  
- `scripts/auto_processor.log` - Processing log file
- `scripts/auto_processor.pid` - Process ID file (when running)

## Troubleshooting

### OCR Not Working

If OCR fails, check:

```bash
# Test OCR capability
python -c "import ocrmac; print('ocrmac available')"

# Check dependencies
pip install ocrmac  # macOS
pip install pytesseract  # Cross-platform fallback
```

### Processing Stopped

Check if auto processor is running:

```bash
python scripts/start_auto_processor.py status
```

Restart if needed:

```bash
python scripts/start_auto_processor.py restart
```

### Database Issues

Verify database connection:

```bash
python scripts/final_integrity_check.py
```

## Performance

- **Processing Speed**: ~1 screenshot per second
- **Memory Usage**: Minimal (batch processing)
- **CPU Usage**: Low (uses efficient OCR libraries)
- **Coverage Rate**: Processes 50-100 screenshots per batch

## Next Steps

To improve coverage to 100%:

1. **Run catch-up processing**:
   ```bash
   # Process larger batches to catch up
   python scripts/processing/auto_processor.py --limit 500
   ```

2. **Enable continuous processing**:
   ```bash
   # Start auto processor to handle new screenshots
   python scripts/start_auto_processor.py start
   ```

3. **Monitor progress**:
   ```bash
   # Check coverage regularly
   python scripts/final_integrity_check.py
   ```

The auto processor will continuously maintain OCR and task extraction coverage as new screenshots are captured.