# Process Screenshots

Run the AutoTaskTracker processing pipeline on captured screenshots.

## Arguments
- `$ARGUMENTS` - Optional: `--limit N` to process only N screenshots, `--recent` for recent only

## Instructions for Claude:

1. **Check System Status**:
   ```bash
   # Verify Pensieve is capturing
   memos ps
   
   # Check database connectivity
   python -c "from autotasktracker.core.database import DatabaseManager; print('DB: OK')"
   ```

2. **Run Processing Pipeline**:
   ```bash
   # Process screenshots with AI pipeline
   python scripts/processing/process_tasks.py $ARGUMENTS
   ```

3. **Alternative Processing Options**:
   ```bash
   # OCR-only processing
   python scripts/run_ocr_processing.py $ARGUMENTS
   
   # Realtime processor (continuous)
   python scripts/processing/realtime_processor.py
   
   # Auto processor (batch with AI)
   python scripts/processing/auto_processor.py $ARGUMENTS
   ```

4. **Generate Embeddings** (for semantic search):
   ```bash
   python scripts/generate_embeddings.py --limit 50
   ```

5. **Verify Processing Results**:
   ```bash
   # Check processed count
   python -c "
   from autotasktracker.core.database import DatabaseManager
   db = DatabaseManager()
   tasks = db.fetch_tasks(limit=10)
   print(f'Recent tasks processed: {len(tasks)}')
   "
   ```

6. **Report Status**: Provide summary of:
   - Screenshots processed
   - Tasks extracted  
   - Any processing errors
   - Recommendations for next steps

This command runs the complete AutoTaskTracker processing pipeline.