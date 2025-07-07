# PostgreSQL Setup Guide for AutoTaskTracker

This guide provides step-by-step instructions for setting up PostgreSQL as the database backend for AutoTaskTracker.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Administrative access to install PostgreSQL

## Installation

### macOS

1. **Install PostgreSQL using Homebrew:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

2. **Verify installation:**
```bash
psql --version
# Should output: psql (PostgreSQL) 15.x
```

### Ubuntu/Debian

1. **Install PostgreSQL:**
```bash
sudo apt update
sudo apt install postgresql-15 postgresql-contrib
sudo systemctl start postgresql
```

2. **Verify installation:**
```bash
psql --version
```

### Windows

1. **Download PostgreSQL installer:**
   - Visit https://www.postgresql.org/download/windows/
   - Download the installer for PostgreSQL 15
   - Run the installer with default settings

2. **Add PostgreSQL to PATH:**
   - Add `C:\Program Files\PostgreSQL\15\bin` to your system PATH

## Database Setup

### 1. Create Database User

```bash
# macOS/Linux
sudo -u postgres createuser -s postgres

# Set password (if not already set)
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'mysecretpassword';"
```

### 2. Create AutoTaskTracker Database

```bash
# Create the database
sudo -u postgres createdb autotasktracker

# Verify connection
psql -U postgres -d autotasktracker -c "SELECT version();"
```

### 3. Configure PostgreSQL for AutoTaskTracker

Edit PostgreSQL configuration to use port 5433 (to avoid conflicts):

```bash
# Find config file location
sudo -u postgres psql -c "SHOW config_file;"

# Edit postgresql.conf
sudo nano /path/to/postgresql.conf
```

Change the port:
```
port = 5433
```

Restart PostgreSQL:
```bash
# macOS
brew services restart postgresql@15

# Linux
sudo systemctl restart postgresql

# Windows
net stop postgresql-x64-15
net start postgresql-x64-15
```

## AutoTaskTracker Configuration

1. **Verify configuration file:**
```bash
cat ~/.memos/config_autotasktracker.yaml
```

Should contain:
```yaml
database_path: postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker
server_port: 8841
```

2. **Validate configuration:**
```bash
python scripts/utils/validate_config.py
```

## Python Dependencies

Install required Python packages:
```bash
pip install psycopg2-binary
```

## Quick Setup with Docker (Alternative)

If you prefer using Docker:

1. **Create docker-compose.yml:**
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: mysecretpassword
      POSTGRES_DB: autotasktracker
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

2. **Start PostgreSQL:**
```bash
docker-compose up -d
```

## Testing the Connection

1. **Test with autotask.py:**
```bash
python autotask.py test
```

Expected output:
```
Testing PostgreSQL connection...
✅ PostgreSQL connection successful
   Entities: 6,606
   Metadata: 54,245
```

2. **Test with psql:**
```bash
psql -h localhost -p 5433 -U postgres -d autotasktracker -c "\dt"
```

## Troubleshooting

### Connection Refused
- Check PostgreSQL is running: `brew services list` or `sudo systemctl status postgresql`
- Verify port 5433 is not in use: `lsof -i :5433`

### Authentication Failed
- Check password in config_autotasktracker.yaml matches PostgreSQL user password
- Verify pg_hba.conf allows password authentication:
  ```
  local   all   all   md5
  host    all   all   127.0.0.1/32   md5
  ```

### Database Does Not Exist
- Create database: `sudo -u postgres createdb autotasktracker`
- Check database list: `sudo -u postgres psql -l`

### Performance Issues
- Increase shared_buffers in postgresql.conf (e.g., 256MB)
- Add indexes for frequently queried columns
- Use connection pooling (already implemented in DatabaseManager)

## Migration from SQLite

If you have existing data in SQLite:

1. **Export from SQLite:**
```bash
sqlite3 ~/.memos/database.db .dump > backup.sql
```

2. **Convert and import to PostgreSQL:**
```bash
# Use migration tools or manual conversion
# AutoTaskTracker includes migration utilities
```

## Maintenance

### Regular Backups
```bash
# Backup database
pg_dump -U postgres -h localhost -p 5433 autotasktracker > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U postgres -h localhost -p 5433 autotasktracker < backup_20250706.sql
```

### Monitoring
```bash
# Check database size
psql -U postgres -d autotasktracker -c "SELECT pg_database_size('autotasktracker');"

# Active connections
psql -U postgres -d autotasktracker -c "SELECT count(*) FROM pg_stat_activity;"
```

## Next Steps

1. Launch AutoTaskTracker dashboards:
```bash
python autotasktracker.py dashboard  # Task Board on port 8602
python autotasktracker.py analytics  # Analytics on port 8603
python autotasktracker.py timetracker # Time Tracker on port 8605
```

2. Configure Pensieve/memos for screenshot capture:
```bash
memos start
```

3. Review [Configuration Guide](../guides/CONFIGURATION_GUIDE.md) for advanced settings

---

For more help, see the [troubleshooting guide](../guides/troubleshooting.md) or open an issue on GitHub.