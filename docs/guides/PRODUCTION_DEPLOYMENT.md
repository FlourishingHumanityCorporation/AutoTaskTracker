# Production Deployment Guide

## Overview

Guide for deploying the refactored dashboard architecture to production.

## Requirements

- Python 3.8+ with virtual environment
- Dependencies installed: `pip install -r requirements.txt`
- Memos service running: `memos ps` shows active
- Ports available: 8502-8506

## Validation

```bash
# Test database connection
python -c "from autotasktracker.core.database import DatabaseManager; print('OK' if DatabaseManager().test_connection() else 'FAIL')"

# Run tests
python -m pytest tests/test_dashboard_core.py -v

# Test refactored dashboards
python scripts/demo_core_refactoring.py
```

## Deployment

### Backup Current System
```bash
cp autotasktracker.py autotasktracker_backup.py
cp -r autotasktracker/dashboards dashboards_backup
```

### Deploy Refactored System
```bash
# Stop current system
python autotasktracker.py stop

# Start refactored system
python -m autotasktracker.dashboards.launcher_refactored start
```

### Verify Deployment
```bash
curl -s http://localhost:8502 | grep -q "Task Board" && echo "✅ Task Board OK"
curl -s http://localhost:8503 | grep -q "Analytics" && echo "✅ Analytics OK"
```

3. **Validate Production Traffic**
   ```bash
   # Health check on production ports
   curl -s http://localhost:8502 | grep -q "Task Board" && echo "✅ Production Task Board OK"
   curl -s http://localhost:8503 | grep -q "Analytics" && echo "✅ Production Analytics OK"
   ```

### Phase 3: Blue Environment Decommission

1. **Monitor for Issues (24-48 hours)**
   ```bash
   # Monitor logs
   tail -f ~/.streamlit/logs/*.log
   
   # Check performance metrics
   python scripts/monitor_dashboard_performance.py
   ```

2. **Decommission Blue Environment**
   ```bash
   # Only after confirming stability
   # Move old dashboards to archive
   mkdir -p autotasktracker/dashboards/archive_$(date +%Y%m%d)
   mv autotasktracker/dashboards/task_board.py autotasktracker/dashboards/archive_$(date +%Y%m%d)/
   mv autotasktracker/dashboards/analytics.py autotasktracker/dashboards/archive_$(date +%Y%m%d)/
   mv autotasktracker/dashboards/achievement_board.py autotasktracker/dashboards/archive_$(date +%Y%m%d)/
   ```

## 🔧 Production Configuration

### Environment Variables
```bash
# Add to ~/.bashrc or production environment
export ATT_CACHE_TTL=300          # 5 minutes cache TTL
export ATT_DB_POOL_SIZE=5         # Database connection pool
export ATT_MAX_QUERY_LIMIT=2000   # Maximum query results
export ATT_ENABLE_DEBUG=false     # Disable debug mode
export ATT_LOG_LEVEL=INFO         # Production logging
```

### Performance Tuning
```python
# autotasktracker/dashboards/production_config.py
PRODUCTION_CONFIG = {
    'cache_ttl_seconds': 300,           # 5 minute cache
    'db_pool_size': 5,                  # Connection pool
    'max_query_limit': 2000,            # Query limits
    'enable_performance_monitoring': True,
    'auto_refresh_interval': 300,       # 5 minute auto-refresh
    'screenshot_thumbnail_size': 150,   # Optimize image sizes
}
```

### Monitoring Setup
```bash
# Install monitoring dependencies
pip install psutil python-dotenv
# See scripts/production_monitor.py for monitoring implementation
```

## 📊 Performance Optimization

### Database Query Optimization
```python
# Add to repositories for production
class OptimizedTaskRepository(TaskRepository):
    def get_tasks_for_period_optimized(self, start_date, end_date, limit=1000):
        """Optimized query with indices and limits."""
        query = """
        SELECT e.id, e.created_at, e.file_path,
               m1.value as ocr_text, m2.value as active_window,
               m3.value as tasks, m4.value as category, m5.value as window_title
        FROM entities e INDEXED BY idx_created_at
        LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'text'
        LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
        LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
        LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'category'
        LEFT JOIN metadata_entries m5 ON e.id = m5.entity_id AND m5.key = 'window_title'
        WHERE e.created_at BETWEEN ? AND ?
        ORDER BY e.created_at DESC
        LIMIT ?
        """
        # Use optimized query in production
```

### Caching Strategy
```python
# Production caching configuration
PRODUCTION_CACHE_CONFIG = {
    'time_filtered_data': {'ttl': 300, 'max_size': 100},
    'metrics_summary': {'ttl': 600, 'max_size': 50},
    'category_breakdown': {'ttl': 900, 'max_size': 20},
    'hourly_activity': {'ttl': 1800, 'max_size': 20},
}
```

## 🔒 Security Considerations

### Dashboard Security
```python
# Add security headers to dashboards
def add_security_headers():
    """Add security headers for production."""
    st.markdown("""
    <script>
    // Disable right-click context menu
    document.addEventListener('contextmenu', e => e.preventDefault());
    
    // Add security headers via meta tags
    const meta = document.createElement('meta');
    meta.httpEquiv = 'X-Frame-Options';
    meta.content = 'DENY';
    document.head.appendChild(meta);
    </script>
    """, unsafe_allow_html=True)
```

### Access Control
```bash
# Configure firewall rules (example for Ubuntu)
sudo ufw allow from 192.168.1.0/24 to any port 8502
sudo ufw allow from 192.168.1.0/24 to any port 8503
sudo ufw allow from 192.168.1.0/24 to any port 8504
sudo ufw deny 8502
sudo ufw deny 8503 
sudo ufw deny 8504
```

## 🚨 Rollback Procedures

### Immediate Rollback (< 5 minutes)
```bash
# Stop new system
python -m autotasktracker.dashboards.launcher_refactored stop

# Start original system
python autotasktracker_original.py start

# Verify rollback
curl -s http://localhost:8502 | grep -q "Task Board" && echo "✅ Rollback successful"
```

### Data Rollback (if needed)
```bash
# Restore database from backup
cp ~/.memos/database.db ~/.memos/database.db.refactored_backup
cp ~/.memos/database_backup_$(date +%Y%m%d).db ~/.memos/database.db

# Restart memos
memos restart
```

## 📈 Success Metrics

### Performance Metrics
- [ ] Page load time < 3 seconds
- [ ] Database query time < 1 second
- [ ] Cache hit rate > 80%
- [ ] Memory usage stable under 500MB
- [ ] CPU usage < 50% average

### Functionality Metrics
- [ ] All dashboards accessible
- [ ] Data consistency maintained
- [ ] Screenshots displaying correctly
- [ ] Time filtering working accurately
- [ ] Export functionality operational

### User Experience Metrics
- [ ] Zero error reports in first 24 hours
- [ ] Consistent UI across all dashboards
- [ ] Fast loading and responsive interface
- [ ] Smooth transitions and interactions

## 🎯 Post-Deployment Tasks

### Week 1: Monitoring
- [ ] Monitor performance metrics daily
- [ ] Check error logs twice daily
- [ ] Validate data accuracy
- [ ] Collect user feedback

### Week 2: Optimization
- [ ] Analyze cache hit rates
- [ ] Optimize slow queries
- [ ] Fine-tune cache TTL values
- [ ] Review memory usage patterns

### Month 1: Enhancement
- [ ] Plan new features using component library
- [ ] Implement WebSocket for real-time updates
- [ ] Add advanced analytics features
- [ ] Create dashboard templates

## 🔧 Troubleshooting Guide

### Common Issues

**Dashboard won't start:**
```bash
# Check port availability
netstat -tulpn | grep :8502

# Check Python path
python -c "import autotasktracker.dashboards.base; print('Import OK')"

# Check database connection
python -c "from autotasktracker.core.database import DatabaseManager; print(DatabaseManager().test_connection())"
```

**Performance issues:**
```bash
# Clear cache
python -c "from autotasktracker.dashboards.cache import DashboardCache; DashboardCache.clear_cache()"

# Check memory usage
ps aux | grep streamlit

# Monitor database queries
sqlite3 ~/.memos/database.db ".explain"
```

**Data inconsistencies:**
```bash
# Compare data between old and new systems
python scripts/validate_data_consistency.py

# Rebuild cache
python scripts/rebuild_dashboard_cache.py
```

## 📞 Support Contacts

- **Technical Issues**: Check troubleshooting section first
- **Performance Problems**: Monitor logs and system metrics
- **Data Issues**: Validate database integrity
- **Rollback Required**: Follow immediate rollback procedure

---

**This deployment guide ensures a smooth transition to the refactored architecture while maintaining system stability and user experience.**