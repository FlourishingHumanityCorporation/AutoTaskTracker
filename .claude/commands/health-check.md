# AutoTaskTracker Health Check

Run comprehensive health checks for the AutoTaskTracker system.

## Instructions for Claude:

1. **Check Pensieve Service**:
   ```bash
   memos ps
   ```

2. **Run Core Health Tests**:
   ```bash
   pytest tests/health/ -v --tb=short
   ```

3. **Check Integration Health**:
   ```bash
   python scripts/pensieve_health_check.py
   ```

4. **Verify Database Connection**:
   ```bash
   python -c "
   from autotasktracker.core.database import DatabaseManager
   db = DatabaseManager()
   print('Database connection: OK')
   print(f'Pool stats: {db.get_pool_stats()}')
   "
   ```

5. **Check AI Dependencies**:
   ```bash
   python scripts/ai/ai_cli.py status
   ```

6. **Report Results**: Summarize the health status in a clear format:
   - ✅ Component healthy
   - ⚠️ Component degraded but functional  
   - ❌ Component failing

This command provides a complete system health overview for AutoTaskTracker.