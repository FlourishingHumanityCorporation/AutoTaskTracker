# SQLite to PostgreSQL Migration Guide

This guide helps existing AutoTaskTracker users migrate from SQLite to PostgreSQL.

## Before You Start

**⚠️ IMPORTANT**: Create backups before proceeding with the migration.

### Prerequisites
- Existing AutoTaskTracker installation with SQLite data
- PostgreSQL 15 installed (see [PostgreSQL Setup Guide](../setup/postgresql_setup.md))
- Python dependencies updated: `pip install psycopg2-binary`

## Migration Steps

### Step 1: Backup Your Data

```bash
# Backup your SQLite database
cp ~/.memos/database.db ~/.memos/database_backup_$(date +%Y%m%d).db

# Backup your configuration
cp ~/.memos/config_autotasktracker.yaml ~/.memos/config_backup_$(date +%Y%m%d).yaml

# Export screenshots directory (if needed)
tar -czf ~/.memos/screenshots_backup_$(date +%Y%m%d).tar.gz ~/.memos/screenshots/
```

### Step 2: Set Up PostgreSQL

Follow the [PostgreSQL Setup Guide](../setup/postgresql_setup.md) or use the automated script:

```bash
# Run the setup script
./scripts/setup_postgresql.sh

# Or use Docker
docker-compose up -d
```

### Step 3: Export Data from SQLite

```bash
# Export your SQLite data
sqlite3 ~/.memos/database.db .dump > /tmp/autotask_sqlite_export.sql
```

### Step 4: Convert SQLite Export to PostgreSQL

SQLite and PostgreSQL have different syntax. Here's a conversion script:

```bash
# Create PostgreSQL-compatible SQL
sed -e 's/AUTOINCREMENT/SERIAL/g' \
    -e 's/INTEGER PRIMARY KEY/SERIAL PRIMARY KEY/g' \
    -e 's/TEXT/VARCHAR(255)/g' \
    -e '/^PRAGMA/d' \
    -e '/^BEGIN TRANSACTION/d' \
    -e '/^COMMIT/d' \
    /tmp/autotask_sqlite_export.sql > /tmp/autotask_postgresql_import.sql
```

**Note**: For complex migrations, consider using dedicated tools like `pgloader`:

```bash
# Install pgloader (macOS)
brew install pgloader

# Convert SQLite to PostgreSQL
pgloader sqlite:///Users/$(whoami)/.memos/database.db \
         postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker
```

### Step 5: Import Data to PostgreSQL

```bash
# Import to PostgreSQL
psql -U postgres -h localhost -p 5433 -d autotasktracker -f /tmp/autotask_postgresql_import.sql
```

### Step 6: Update Configuration

Update your configuration file to use PostgreSQL:

```bash
# Backup current config
cp ~/.memos/config_autotasktracker.yaml ~/.memos/config_autotasktracker_sqlite_backup.yaml

# Update database path in config
sed -i '' 's|database_path:.*|database_path: postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker|' ~/.memos/config_autotasktracker.yaml
```

Or manually edit `~/.memos/config_autotasktracker.yaml`:

```yaml
database_path: postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker
server_port: 8841
# ... rest of config unchanged
```

### Step 7: Verify Migration

```bash
# Test database connection
python autotask.py test

# Validate configuration
python scripts/utils/validate_config.py

# Check data integrity
python -c "
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
print(f'Entities: {db.get_entity_count()}')
print(f'Metadata: {db.get_metadata_count()}')
"
```

### Step 8: Test Dashboards

```bash
# Launch main dashboard
python autotasktracker.py dashboard

# Test other dashboards
python autotasktracker.py analytics
python autotasktracker.py timetracker
```

## Troubleshooting

### Data Import Issues

**Error: `syntax error at or near "AUTOINCREMENT"`**
```bash
# Fix SQLite-specific syntax
sed -i 's/AUTOINCREMENT/SERIAL/g' /tmp/autotask_postgresql_import.sql
```

**Error: `column "id" is of type integer but expression is of type text`**
```bash
# Fix data type mismatches
sed -i "s/'([0-9]+)'/(\\1)/g" /tmp/autotask_postgresql_import.sql
```

### Connection Issues

**Error: `FATAL: password authentication failed`**
```bash
# Reset PostgreSQL password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'mysecretpassword';"
```

**Error: `could not connect to server: Connection refused`**
```bash
# Start PostgreSQL service
brew services start postgresql@15  # macOS
sudo systemctl start postgresql    # Linux
```

### Data Validation Issues

**Missing data after migration:**
1. Check if all tables were created:
   ```sql
   \dt  -- List tables in PostgreSQL
   ```

2. Compare record counts:
   ```bash
   # SQLite count
   sqlite3 ~/.memos/database.db "SELECT COUNT(*) FROM entities;"
   
   # PostgreSQL count
   psql -U postgres -d autotasktracker -c "SELECT COUNT(*) FROM entities;"
   ```

3. Re-run import if needed:
   ```bash
   # Drop and recreate tables
   psql -U postgres -d autotasktracker -c "DROP TABLE IF EXISTS metadata_entries, entities CASCADE;"
   psql -U postgres -d autotasktracker -f scripts/sql/init.sql
   psql -U postgres -d autotasktracker -f /tmp/autotask_postgresql_import.sql
   ```

## Performance Optimization

After migration, optimize PostgreSQL for your data:

```sql
-- Analyze tables for query planner
ANALYZE entities;
ANALYZE metadata_entries;

-- Add additional indexes if needed
CREATE INDEX idx_metadata_value_text ON metadata_entries USING gin(to_tsvector('english', value));

-- Update statistics
VACUUM ANALYZE;
```

## Rollback Plan

If you need to rollback to SQLite:

```bash
# Restore SQLite database
cp ~/.memos/database_backup_YYYYMMDD.db ~/.memos/database.db

# Restore configuration
cp ~/.memos/config_backup_YYYYMMDD.yaml ~/.memos/config_autotasktracker.yaml

# Stop PostgreSQL if not needed
brew services stop postgresql@15  # macOS
docker-compose down               # Docker
```

## Post-Migration Cleanup

After successful migration and testing:

```bash
# Remove backup files (optional)
rm ~/.memos/database_backup_*.db
rm ~/.memos/config_backup_*.yaml
rm /tmp/autotask_*_export.sql

# Remove SQLite support (if desired)
# Note: This is optional and irreversible
```

## Data Migration Tools

### Using pgloader (Recommended)

pgloader handles data type conversion automatically:

```bash
# Install pgloader
brew install pgloader  # macOS
sudo apt install pgloader  # Ubuntu

# Migrate with pgloader
pgloader --verbose \
  sqlite:///Users/$(whoami)/.memos/database.db \
  postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker
```

### Using Custom Python Script

For advanced migration needs, you can create a custom script:

```python
import sqlite3
import psycopg2
from autotasktracker.config import get_config

def migrate_data():
    # Connect to both databases
    sqlite_conn = sqlite3.connect('~/.memos/database.db')
    
    config = get_config()
    pg_conn = psycopg2.connect(config.DATABASE_URL)
    
    # Migrate entities
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    sqlite_cursor.execute("SELECT id, filepath, created_at FROM entities")
    entities = sqlite_cursor.fetchall()
    
    for entity in entities:
        pg_cursor.execute(
            "INSERT INTO entities (id, filepath, created_at) VALUES (%s, %s, %s)",
            entity
        )
    
    # Migrate metadata_entries
    # ... similar process
    
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate_data()
```

## FAQ

**Q: How long does migration take?**
A: Depends on data size. Typical installations (10k-100k records) take 5-15 minutes.

**Q: Can I run both SQLite and PostgreSQL simultaneously?**
A: No, AutoTaskTracker now only supports PostgreSQL.

**Q: What if I lose data during migration?**
A: Always keep your SQLite backup. You can restore and retry migration.

**Q: Do I need to migrate screenshots?**
A: Screenshots are stored as files, not in the database. No migration needed.

**Q: Will my dashboard configurations be preserved?**
A: Yes, dashboard configurations are separate from database choice.

## Need Help?

- Check the [troubleshooting guide](../setup/postgresql_setup.md#troubleshooting)
- Review [configuration documentation](../guides/CONFIGURATION_GUIDE.md)
- Open an issue on GitHub with migration logs

---

**Migration Complete!** Your AutoTaskTracker installation should now be running on PostgreSQL with all your historical data preserved.