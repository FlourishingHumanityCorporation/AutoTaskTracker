# AutoTaskTracker Configuration Guide

## Single Configuration System

### THE ONLY CONFIGURATION FILE: `autotasktracker/config.py`

```python
# ✅ CORRECT - This is the only way:
from autotasktracker.config import get_config
config = get_config()
```

## Current State (as of 2025-01-06)

### What We Have
- **Single config file**: `autotasktracker/config.py` (~830 lines)
- **All ports defined inline**: No separate ports file
- **No duplicate properties**: Cleaned up DB_PATH, POSTGRESQL_URL duplicates
- **Fast-fail initialization**: No more silent errors
- **Thread-safe singleton**: Proper locking for concurrent access

### What It Contains
- **44+ Port definitions** (8600-8699 range for AutoTaskTracker)
- **Database configuration** (PostgreSQL on port 5433)
- **Directory paths** (screenshots, logs, cache, etc.)
- **API endpoints** dictionary
- **AI model settings** (VLM, OCR, embeddings)
- **Feature flags**
- **Security validation functions**
- **Pensieve integration** (currently disabled to prevent recursion)

### Known Technical Debt
- File is still a 830-line god object
- Ports are hardcoded inline
- Tight coupling with external services
- See TECHNICAL_DEBT_CONFIG.md for details

## Port Configuration - Single Source of Truth

All ports are defined in `config.py`:

```python
# Dashboard Ports (8600-8699 range)
TASK_BOARD_PORT = 8602
ANALYTICS_PORT = 8603
TIMETRACKER_PORT = 8605
NOTIFICATIONS_PORT = 8606
ADVANCED_ANALYTICS_PORT = 8607
OVERVIEW_PORT = 8608
FOCUS_TRACKER_PORT = 8609
DAILY_SUMMARY_PORT = 8610

# Administrative Ports
LAUNCHER_PORT = 8611
VLM_MONITOR_PORT = 8612

# API Ports
AUTOTASK_API_PORT = 8620
HEALTH_CHECK_PORT = 8621
METRICS_PORT = 8622
WEBHOOK_PORT = 8623

# External Services
MEMOS_PORT = 8841
OLLAMA_PORT = 11434
POSTGRES_PORT = 5433  # Note: Using 5433, not default 5432
```

## Database Configuration - Single Source of Truth

```python
# PostgreSQL (Primary Database)
DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"

# SQLite (Fallback Only)
SQLITE_PATH = "~/.memos/database.db"
```

## How to Use Configuration

### Getting a Port
```python
from autotasktracker.config import get_config

config = get_config()
port = config.TASK_BOARD_PORT  # Returns: 8602
```

### Getting a Service URL
```python
config = get_config()
url = config.get_url_by_service('task_board')  # Returns: "http://localhost:8602"
```

### Getting API Endpoints
```python
config = get_config()
endpoints = config.API_ENDPOINTS
ollama_api = endpoints['ollama_api']  # Returns: "http://localhost:11434"
```

### Environment Variable Overrides
All settings can be overridden with environment variables:

```bash
# Port overrides
export AUTOTASK_TASK_BOARD_PORT=8700
export AUTOTASK_ANALYTICS_PORT=8701

# Database overrides
export AUTOTASK_POSTGRES_HOST=remotehost
export AUTOTASK_POSTGRES_PORT=5432

# Path overrides
export AUTOTASK_SCREENSHOTS_DIR=/custom/screenshots
export AUTOTASK_VLM_CACHE_DIR=/custom/cache
```

## No Migration Needed!

There is only ONE configuration file: `autotasktracker/config.py`

All code should use:
```python
from autotasktracker.config import get_config
config = get_config()
```

## Common Patterns

### Dashboard Launch
```python
from autotasktracker.config import get_config
import subprocess

config = get_config()
cmd = [
    'streamlit', 'run', 'dashboard.py',
    '--server.port', str(config.TASK_BOARD_PORT)
]
subprocess.run(cmd)
```

### Database Connection
```python
from autotasktracker.config import get_config
import psycopg2

config = get_config()
conn = psycopg2.connect(config.DATABASE_URL)
```

### API Client
```python
from autotasktracker.config import get_config
import requests

config = get_config()
response = requests.get(config.API_ENDPOINTS['ollama_api'])
```

## Validation and Testing

### Validate Configuration
```python
config = get_central_config()
issues = config.validate_configuration()
if issues:
    print(f"Configuration issues: {issues}")
```

### Check All Ports
```python
config = get_central_config()
all_ports = config.get_all_ports()
print(f"Total ports configured: {len(all_ports)}")
```

## DO NOT USE These Patterns

### ❌ Creating Multiple Config Instances
```python
# NEVER DO THIS
config1 = Config()  # Don't create instances directly
config2 = Config()  # Use get_config() instead
```

### ❌ Direct SQLite Access
```python
# NEVER DO THIS
import sqlite3
conn = sqlite3.connect("~/.memos/database.db")
```

### ❌ Hardcoded Ports
```python
# NEVER DO THIS
port = 8602  # Always use config.TASK_BOARD_PORT
```

### ❌ Hardcoded URLs
```python
# NEVER DO THIS  
url = "http://localhost:8602"  # Use config.get_url_by_service('task_board')
```

## Quick Reference

| Need | Use |
|------|-----|
| Any port number | `config.TASK_BOARD_PORT`, etc. |
| Service URL | `config.get_url_by_service('service_name')` |
| API endpoint | `config.API_ENDPOINTS['endpoint_name']` |
| Database URL | `config.DATABASE_URL` |
| Directory path | `config.SCREENSHOTS_DIR`, etc. |
| Feature flag | `config.ENABLE_VLM`, etc. |

## Summary

1. **There is ONLY ONE config file**: `autotasktracker/config.py`
2. **NEVER hardcode ports or URLs** - Always get from config
3. **Use environment variables** for deployment overrides
4. **PostgreSQL port is 5433** not 5432 in this project
5. **Thread-safe singleton pattern** ensures proper access

This unified configuration system provides:
- ✅ Single source of truth - NO confusion
- ✅ Type safety with dataclasses
- ✅ Security validations for paths and ports
- ✅ Pensieve integration with dynamic paths
- ✅ Thread-safe access with proper locking
- ✅ Environment variable overrides
- ✅ Backward compatibility aliases
- ✅ ZERO configuration confusion