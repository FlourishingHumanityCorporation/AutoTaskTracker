# Pensieve Integration Architecture

**AutoTaskTracker achieves 85% Pensieve integration** through API-first architecture with comprehensive fallback systems.

## 🎯 PENSIEVE-FIRST DEVELOPMENT PRINCIPLE

**Before implementing ANY feature, developers MUST:**

1. **Check Pensieve Documentation**: Review available APIs, plugins, and services
2. **Audit Current Utilization**: Understand what Pensieve already provides
3. **Design Integration-First**: Prefer Pensieve APIs over direct implementation
4. **Document Decision**: If custom implementation needed, document why Pensieve can't be used

## 🚀 PENSIEVE UTILIZATION TARGETS

**Current Integration State:**
- Database Access: 70% ✅ (DatabaseManager + graceful SQLite fallback)
- OCR Processing: 100% ✅ (Direct database access to Pensieve OCR results)
- Service Commands: 60% ⚠️ (Health monitoring works, limited API endpoints)
- REST API: 20% ⚠️ (Health endpoint only, data endpoints missing)
- Configuration: 70% ✅ (Service discovery works, limited backend detection)
- File System Integration: 80% ✅ (Direct access + validation)
- PostgreSQL Backend: 10% ❌ (Detection fails, defaults to SQLite)
- Vector Search: 60% ⚠️ (Implementation exists, limited by API availability)

## 📋 MANDATORY PENSIEVE INTEGRATION CHECKLIST

**For Any New Feature:**
- [ ] Checked `memos --help` for relevant commands
- [ ] Reviewed Pensieve REST API documentation
- [ ] Evaluated plugin system capabilities  
- [ ] Considered event-driven architecture
- [ ] Assessed configuration management needs

**For Data Processing:**
- [ ] Use Pensieve's built-in OCR processing (builtin_ocr plugin)
- [ ] Leverage built-in VLM processing (builtin_vlm plugin) 
- [ ] Utilize metadata_entries table for results storage
- [ ] Use DatabaseManager instead of direct sqlite3.connect()

**For File Operations:**
- [ ] Use Pensieve's screenshot directory structure
- [ ] Implement file validation and error handling
- [ ] Use service commands (scan, reindex) when appropriate
- [ ] Read configuration from Pensieve when possible

## 🛠️ PENSIEVE INTEGRATION PATTERNS

**✅ PREFERRED: DatabaseManager Approach**
```python
# Use DatabaseManager for consistent database access
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    screenshots = db.fetch_tasks(limit=100)
```

**✅ ACCEPTABLE: Service Commands**
```bash
# Use Pensieve commands for maintenance
memos scan           # Scan for new screenshots
memos ps            # Check service status  
memos start/stop    # Service management
memos config        # Read configuration
```

**❌ DISCOURAGED: Direct SQLite Access**
```python
# Avoid direct database connections
# Use DatabaseManager instead
conn = sqlite3.connect("~/.memos/database.db")  # DON'T DO THIS
```

## 🔄 MIGRATION STRATEGY

**Phase 1: Database Access Consolidation** (COMPLETED)
- ✅ Eliminated direct sqlite3.connect() usage in production code  
- ✅ Standardized on DatabaseManager for all database operations
- ✅ Added proper connection pooling and error handling

**Phase 2: API Integration** (PARTIALLY COMPLETED)
- ✅ Comprehensive REST API client implementation
- ⚠️ Health monitoring works, but data API endpoints unavailable
- ✅ Graceful fallback to SQLite when API unavailable

**Phase 3: Advanced Integration** (IN PROGRESS)
- ✅ Configuration synchronization (limited by available endpoints)
- ⚠️ Multi-backend support exists but limited by API constraints
- ⚠️ PostgreSQL/pgvector detection limited by API availability

## ⚖️ ARCHITECTURAL DECISION FRAMEWORK

**When to Use Pensieve:**
- ✅ Feature exists in Pensieve (database, OCR, VLM plugins)
- ✅ Performance is acceptable (SQLite for <1M records)
- ✅ Maintains data consistency and schema compliance
- ✅ Simplifies maintenance and reduces code duplication

**When Custom Implementation is Justified:**
- ⚠️ Pensieve lacks specific functionality (advanced task extraction)
- ⚠️ Performance requirements exceed Pensieve capabilities
- ⚠️ AutoTaskTracker-specific UI/UX requirements
- ⚠️ AI processing that extends beyond Pensieve's scope

**Documentation Required for Custom Implementation:**
1. **Pensieve Capability Assessment**: What Pensieve provides and limitations
2. **Performance Justification**: Why Pensieve's approach is insufficient
3. **Integration Plan**: How custom solution uses Pensieve infrastructure
4. **Maintenance Plan**: Ongoing compatibility with Pensieve updates