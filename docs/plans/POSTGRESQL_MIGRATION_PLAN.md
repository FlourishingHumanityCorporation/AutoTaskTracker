# PostgreSQL Migration Plan

**Status**: Ready for Implementation  
**Priority**: High  
**Estimated Timeline**: 2-3 days  
**Risk Level**: Low  

## Executive Summary

AutoTaskTracker is already configured for PostgreSQL via Pensieve. The migration involves:
1. **Verifying PostgreSQL setup** (already configured)
2. **Testing database connectivity** (Pensieve handles this)
3. **Migrating data from SQLite** (optional - can run fresh)
4. **Removing SQLite fallbacks** (simplify codebase)

**Key Insight**: This is actually a **simplification**, not a complex migration!

## Current State Analysis ✅

### Already Implemented:
- ✅ **PostgreSQL dependencies**: `psycopg2-binary==2.9.9` installed
- ✅ **Pensieve PostgreSQL config**: `postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker`
- ✅ **Database manager**: PostgreSQL URI detection and connection pooling
- ✅ **PostgreSQL adapter**: `postgresql_adapter.py` with capabilities detection
- ✅ **Fallback mechanisms**: SQLite fallback for development

### Benefits of PostgreSQL Migration:
- **Performance**: Better concurrent access and query optimization
- **Vector search**: pgvector extension for embeddings
- **Scalability**: Production-ready for large datasets
- **Consistency**: Single backend reduces complexity
- **Pensieve integration**: Native PostgreSQL support

## Migration Strategy (SIMPLIFIED)

### Phase 1: Verify PostgreSQL Setup (Day 1)

#### 1.1 Confirm PostgreSQL Service
- [ ] **1.1.1** Verify PostgreSQL is running on port 5433
- [ ] **1.1.2** Test connection: `psql postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker`
- [ ] **1.1.3** Verify pgvector extension if needed for embeddings

#### 1.1 Test Current Configuration
- [ ] **1.1.4** Run: `python -m memos.commands config` (verify PostgreSQL URI)
- [ ] **1.1.5** Test Pensieve connection: `python -m memos.commands ps`
- [ ] **1.1.6** Run health check: `python scripts/pensieve_health_check.py`

### Phase 2: Update AutoTaskTracker Configuration (Day 1-2)

#### 2.1 Simplify Database Manager
**Current Issue**: `database.py` is 1,183 lines supporting both SQLite and PostgreSQL

**Solution**: Make PostgreSQL the primary backend

- [ ] **2.1.1** Update `DatabaseManager.__init__()` to default to PostgreSQL
- [ ] **2.1.2** Remove SQLite-specific connection logic (keep as emergency fallback only)
- [ ] **2.1.3** Simplify connection pool to PostgreSQL-first
- [ ] **2.1.4** Update all dashboard imports to expect PostgreSQL

#### 2.2 Update Configuration
- [ ] **2.2.1** Update `autotasktracker/config.py` to prefer PostgreSQL
- [ ] **2.2.2** Update default database path to use Pensieve PostgreSQL URI
- [ ] **2.2.3** Remove SQLite path fallbacks in config files

### Phase 3: Test and Validate (Day 2-3)

#### 3.1 Testing Strategy
- [ ] **3.1.1** Run all health tests with PostgreSQL: `pytest tests/health/`
- [ ] **3.1.2** Test dashboard functionality: `python autotasktracker.py dashboard`
- [ ] **3.1.3** Verify AI features work: `python scripts/ai/ai_cli.py status`
- [ ] **3.1.4** Test data repositories: `pytest tests/unit/test_repositories.py`

#### 3.2 Data Migration (Optional)
If you have existing SQLite data:

- [ ] **3.2.1** Export SQLite data: `python scripts/export_sqlite_data.py`
- [ ] **3.2.2** Import to PostgreSQL via Pensieve API
- [ ] **3.2.3** Verify data integrity

**Recommended**: Start fresh with PostgreSQL for clean migration

### Phase 4: Cleanup and Optimization (Day 3)

#### 4.1 Remove Technical Debt
- [ ] **4.1.1** Remove SQLite-specific code from `database.py` (save ~400 lines)
- [ ] **4.1.2** Update tests to expect PostgreSQL
- [ ] **4.1.3** Remove SQLite fallback imports
- [ ] **4.1.4** Update documentation to reflect PostgreSQL-first approach

#### 4.2 Enable PostgreSQL Features
- [ ] **4.2.1** Enable pgvector for embeddings if available
- [ ] **4.2.2** Optimize queries for PostgreSQL
- [ ] **4.2.3** Configure connection pooling for performance
- [ ] **4.2.4** Enable PostgreSQL-specific features in dashboards

## Implementation Steps

### Quick Start (If PostgreSQL is already running):

```bash
# 1. Verify PostgreSQL connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker')
print('PostgreSQL connection successful!')
conn.close()
"

# 2. Test Pensieve with PostgreSQL
python -m memos.commands config
python -m memos.commands ps

# 3. Run AutoTaskTracker (should work immediately)
python autotasktracker.py dashboard
```

### If PostgreSQL needs setup:

```bash
# 1. Start PostgreSQL with Docker
docker run -d \
  --name autotask-postgres \
  -e POSTGRES_DB=autotasktracker \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -p 5433:5432 \
  postgres:15

# 2. Optional: Add pgvector extension
docker exec autotask-postgres \
  psql -U postgres -d autotasktracker \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Code Changes Required

### 1. Update DatabaseManager to prefer PostgreSQL

```python
# autotasktracker/core/database.py (line ~85)
if db_path is None:
    if use_pensieve_api:
        try:
            pensieve_config = get_pensieve_config()
            self.db_path = pensieve_config.database_path
            # Ensure we're using PostgreSQL URI
            if not self.db_path.startswith('postgresql://'):
                logger.warning(f"Expected PostgreSQL URI, got: {self.db_path}")
                # Force PostgreSQL default
                self.db_path = "postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"
```

### 2. Simplify configuration priority

```python
# autotasktracker/config.py
def get_db_path(self) -> str:
    """Get database path - PostgreSQL first, SQLite fallback."""
    try:
        pensieve_config = get_pensieve_config()
        if pensieve_config.database_path.startswith('postgresql://'):
            return pensieve_config.database_path
    except ImportError:
        pass
    
    # Default to PostgreSQL
    return "postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"
```

## Risk Assessment

### LOW RISK FACTORS:
1. **Pensieve already configured** for PostgreSQL
2. **Dependencies already installed** (`psycopg2-binary`)
3. **Database manager supports both** backends
4. **Fallback mechanisms exist** if needed

### POTENTIAL ISSUES:
1. **PostgreSQL not running** → Easy fix: start PostgreSQL service
2. **Connection configuration** → Already configured in Pensieve
3. **Data migration** → Optional, can start fresh

### MITIGATION:
- Keep SQLite fallback during transition
- Test thoroughly with health checks
- Use Pensieve's built-in database management

## Success Criteria

- [ ] **SC-1** All dashboards load with PostgreSQL backend
- [ ] **SC-2** Pensieve health checks pass
- [ ] **SC-3** AI features work (embeddings, VLM)
- [ ] **SC-4** No performance degradation
- [ ] **SC-5** Vector search enabled (if pgvector available)

## Rollback Plan

**If anything goes wrong**:
1. **Revert database configuration** to SQLite
2. **Update Pensieve config** to use SQLite path
3. **Restart Pensieve service**
4. **Verify functionality restored**

**Rollback commands**:
```bash
# Update Pensieve to use SQLite
export MEMOS_DATABASE_PATH="~/.memos/database.db"
python -m memos.commands stop
python -m memos.commands start
```

## Timeline Summary

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| 1 | Verify PostgreSQL, test configuration | Working PostgreSQL connection |
| 2 | Update DatabaseManager, test dashboards | PostgreSQL-first architecture |
| 3 | Cleanup code, optimize features | Simplified, production-ready code |

## Expected Outcomes

### Technical Benefits:
- **Reduced codebase**: Remove ~400 lines of SQLite-specific code
- **Better performance**: PostgreSQL optimizations
- **Vector search**: pgvector for embeddings
- **Production ready**: Scalable database backend

### Operational Benefits:
- **Simplified architecture**: Single database backend
- **Pensieve alignment**: Use recommended PostgreSQL setup
- **Future proofing**: Ready for production deployment

---

**Next Steps**:
1. ✅ Verify PostgreSQL is running on port 5433
2. ✅ Test current Pensieve configuration
3. 🚀 Update DatabaseManager to prefer PostgreSQL
4. 🧪 Run comprehensive tests
5. 🎯 Deploy PostgreSQL-first architecture

**This migration is much simpler than the technical debt reduction!** 🎉