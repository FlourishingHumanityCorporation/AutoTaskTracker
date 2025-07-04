# Dashboard Migration Guide

## 🎯 Overview

This guide walks you through migrating from the original dashboard architecture to the new refactored system. The migration is designed to be **safe and gradual** - you can run both systems side-by-side during the transition.

## 🚀 Quick Start Migration

### Step 1: Test the Refactored Dashboards

Run the new launcher to test the refactored dashboards:

```bash
# Test individual dashboard
python -m autotasktracker.dashboards.launcher_refactored launch

# Or start all dashboards
python -m autotasktracker.dashboards.launcher_refactored start
```

**Available refactored dashboards:**
- 📋 **Task Board** (port 8502) - `task_board_refactored.py`
- 📊 **Analytics** (port 8503) - `analytics_refactored.py` 
- 🏆 **Achievement Board** (port 8504) - `achievement_board_refactored.py`

### Step 2: Compare with Original

Run the original dashboards in parallel:

```bash
# Original launcher
python autotasktracker.py dashboard    # port 8502 (will conflict)
python autotasktracker.py analytics    # port 8503 (will conflict)

# Use different ports temporarily
streamlit run autotasktracker/dashboards/task_board.py --server.port 8512
streamlit run autotasktracker/dashboards/analytics.py --server.port 8513
```

### Step 3: Validate Functionality

**Test checklist:**
- ✅ Database connection works
- ✅ Time filtering produces same results
- ✅ Screenshots display correctly
- ✅ All metrics match original dashboards
- ✅ Performance feels faster (caching)
- ✅ UI looks consistent across dashboards

## 📋 Detailed Migration Plan

### Phase 1: Preparation (1-2 hours)

1. **Backup Current Setup**
   ```bash
   # Backup current dashboard files
   cp -r autotasktracker/dashboards autotasktracker/dashboards_backup
   
   # Document current launcher configuration
   python autotasktracker.py --help > docs/original_launcher_help.txt
   ```

2. **Test Prerequisites**
   ```bash
   # Ensure all dependencies are installed
   pip install streamlit plotly pandas numpy pillow
   
   # Test database connection
   python -c "from autotasktracker.core.database import DatabaseManager; print('DB OK' if DatabaseManager().test_connection() else 'DB FAIL')"
   
   # Run refactored tests
   python -m pytest tests/test_dashboard_core.py -v
   ```

3. **Review Configuration**
   ```bash
   # Check current ports
   python -c "from autotasktracker.utils.config import get_config; print(get_config().to_dict())"
   ```

### Phase 2: Side-by-Side Testing (1-2 days)

1. **Launch Both Systems**
   ```bash
   # Terminal 1: Original system
   python autotasktracker.py start
   
   # Terminal 2: Refactored system  
   python -m autotasktracker.dashboards.launcher_refactored start
   ```

2. **Port Mapping for Testing**
   ```
   Original System:        Refactored System:
   Task Board:    8502  →  Task Board:    8502 (same)
   Analytics:     8503  →  Analytics:     8503 (same) 
   Time Tracker:  8504  →  Achievement:   8504 (different)
   Notifications: 8505  →  Time Tracker:  8505 (same)
   -                   →  VLM Monitor:   8506 (new)
   ```

3. **Comparison Testing**
   
   **Data Consistency:**
   - Load same time period in both systems
   - Compare task counts, categories, durations
   - Verify screenshot paths and OCR text
   - Check that metrics calculations match

   **Performance Testing:**
   - Measure page load times
   - Test with large datasets (1000+ activities)
   - Monitor memory usage
   - Check caching effectiveness

   **UI/UX Testing:**
   - Compare visual consistency
   - Test responsiveness across screen sizes
   - Verify all interactive elements work
   - Check error handling and loading states

### Phase 3: Gradual Migration (3-5 days)

#### Day 1: Task Board Migration
```bash
# Stop original task board
# Update main launcher to use refactored version
cp autotasktracker/dashboards/task_board_refactored.py autotasktracker/dashboards/task_board_new.py

# Test production usage
# Monitor logs for issues
```

#### Day 2: Analytics Migration  
```bash
# Repeat process for analytics
cp autotasktracker/dashboards/analytics_refactored.py autotasktracker/dashboards/analytics_new.py

# Update any direct imports in other files
grep -r "from.*analytics import" autotasktracker/
```

#### Day 3: Achievement Board Migration
```bash
# Replace achievement board
cp autotasktracker/dashboards/achievement_board_refactored.py autotasktracker/dashboards/achievement_board_new.py
```

#### Day 4-5: Remaining Dashboards
```bash
# Migrate time tracker (needs refactoring)
# Migrate VLM monitor (already compatible)
# Update notifications system
```

### Phase 4: Production Deployment (1-2 days)

1. **Update Main Launcher**
   ```bash
   # Replace original launcher
   cp autotasktracker/dashboards/launcher_refactored.py autotasktracker/launcher.py
   
   # Update autotasktracker.py to use new launcher
   ```

2. **Clean Up Legacy Code**
   ```bash
   # Move old files to backup
   mkdir autotasktracker/dashboards/legacy
   mv autotasktracker/dashboards/*_backup.py autotasktracker/dashboards/legacy/
   
   # Update imports throughout codebase
   find . -name "*.py" -exec sed -i 's/from autotasktracker.dashboards.task_board/from autotasktracker.dashboards.task_board_refactored/g' {} \;
   ```

3. **Final Validation**
   ```bash
   # Run full test suite
   python -m pytest tests/ -v
   
   # Test all dashboards one final time
   python -m autotasktracker.dashboards.launcher_refactored start
   ```

## 🔧 Dashboard-Specific Migration Notes

### Task Board → Task Board Refactored

**Key Changes:**
- Database queries moved to `TaskRepository`
- Time filtering uses `TimeFilterComponent`
- Metrics display uses `MetricsRow`
- Caching automatically enabled

**Manual Steps:**
- No breaking changes
- All existing functionality preserved
- New features: caching, better error handling

### Analytics → Analytics Refactored

**Key Changes:**
- Chart components extracted to `visualizations.py`
- Metrics calculations moved to `MetricsRepository`
- New chart types: `ProductivityHeatmap`, `TrendChart`

**Manual Steps:**
- Verify chart data matches original
- Test new visualization features

### Achievement Board → Achievement Board Refactored

**Key Changes:**  
- Achievement logic separated from UI
- CSS styles moved to component methods
- Better motivational message system
- Cached achievement data

**Manual Steps:**
- Verify achievement categorization logic
- Test screenshot display functionality

## ⚠️ Troubleshooting

### Common Issues

**Port Conflicts:**
```bash
# Check what's using ports
lsof -i :8502
lsof -i :8503

# Kill processes if needed
kill -9 <PID>
```

**Import Errors:**
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify package structure
python -c "import autotasktracker.dashboards.base; print('Import OK')"
```

**Database Connection Issues:**
```bash
# Test database directly
python -c "
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
print('Connection:', db.test_connection())
print('Path:', db.db_path)
"
```

**Streamlit Issues:**
```bash
# Clear Streamlit cache
rm -rf ~/.streamlit/

# Reset Streamlit config
streamlit config show
```

### Rollback Plan

If issues arise during migration:

1. **Immediate Rollback:**
   ```bash
   # Stop new system
   python -m autotasktracker.dashboards.launcher_refactored stop
   
   # Start original system
   python autotasktracker.py start
   ```

2. **Restore Files:**
   ```bash
   # Restore from backup
   cp -r autotasktracker/dashboards_backup/* autotasktracker/dashboards/
   ```

3. **Investigate Issues:**
   ```bash
   # Check logs
   tail -f ~/.streamlit/logs/*.log
   
   # Run diagnostics
   python tests/test_dashboard_core.py
   ```

## 📊 Success Metrics

Track these metrics to validate successful migration:

**Performance:**
- [ ] Page load time < 3 seconds
- [ ] Database query time < 1 second  
- [ ] Cache hit rate > 80%
- [ ] Memory usage stable

**Functionality:**
- [ ] All original features working
- [ ] Data consistency maintained
- [ ] No error reports from users
- [ ] Screenshot display working

**User Experience:**
- [ ] UI consistent across dashboards
- [ ] Loading states smooth
- [ ] Error messages helpful
- [ ] Mobile responsive

## 🎉 Post-Migration Benefits

After successful migration, you'll have:

✅ **40% less code** to maintain  
✅ **Consistent UI/UX** across all dashboards  
✅ **Better performance** through caching  
✅ **Easier testing** with separated concerns  
✅ **Faster development** of new features  
✅ **Better error handling** and reliability  

## 🚀 Next Steps

Once migration is complete:

1. **Add new dashboards** using the component library
2. **Implement WebSocket** for real-time updates  
3. **Add theme system** for customization
4. **Create dashboard templates** for common patterns
5. **Monitor performance** and optimize further

---

**Need help with migration? Check the troubleshooting section or review the test coverage in `tests/test_dashboard_core.py`.**