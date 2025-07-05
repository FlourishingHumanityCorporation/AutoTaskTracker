# Config Usage Guide

This guide shows how to properly use the AutoTaskTracker configuration system to avoid hardcoding values.

## Quick Reference

```python
from autotasktracker.config import get_config

config = get_config()

# ✅ CORRECT - Use config
db_path = config.get_db_path()
port = config.TASK_BOARD_PORT
url = config.get_service_url('memos')
host = config.SERVER_HOST

# ❌ WRONG - Hardcoded values
db_path = "~/.memos/database.db"
port = 8502
url = "http://localhost:8839"
host = "localhost"
```

## Common Patterns

### Database Paths
```python
# ✅ CORRECT
from autotasktracker.config import get_config
config = get_config()
db_path = config.get_db_path()

# ❌ WRONG
db_path = "~/.memos/database.db"
```

### Service URLs
```python
# ✅ CORRECT
from autotasktracker.config import get_config
config = get_config()
memos_url = config.get_service_url('memos')
analytics_url = config.get_service_url('analytics')

# ❌ WRONG
memos_url = "http://localhost:8839"
analytics_url = "http://localhost:8503"
```

### Ports
```python
# ✅ CORRECT
from autotasktracker.config import get_config
config = get_config()
task_board_port = config.TASK_BOARD_PORT
analytics_port = config.ANALYTICS_PORT

# ❌ WRONG
task_board_port = 8502
analytics_port = 8503
```

### Directory Paths
```python
# ✅ CORRECT
from autotasktracker.config import get_config
config = get_config()
screenshots_dir = config.screenshots_dir
vlm_cache_dir = config.vlm_cache_dir

# ❌ WRONG
screenshots_dir = "~/.memos/screenshots"
vlm_cache_dir = "~/.memos/vlm_cache"
```

## Configuration Validation

The config system validates all values:

### Valid Environment Variables
```bash
# These work
export AUTOTASK_DB_PATH="/tmp/test.db"
export AUTOTASK_VLM_PORT="25000"
export AUTOTASK_BATCH_SIZE="50"
export AUTOTASK_VLM_MODEL="test-model"
```

### Invalid Values Fall Back to Defaults
```bash
# These are rejected and fall back to defaults
export AUTOTASK_VLM_PORT="not_a_number"  # Falls back to 11434
export AUTOTASK_BATCH_SIZE="invalid"     # Falls back to 50
```

## Testing Configuration

### Process-Level Singleton
The config is a process-level singleton, not thread-safe:

```python
# ✅ CORRECT - Sequential testing
def test_config_values():
    with patch.dict(os.environ, {'AUTOTASK_DB_PATH': '/tmp/test.db'}):
        reset_config()
        config = get_config()
        assert config.get_db_path() == '/tmp/test.db'

# ❌ WRONG - Concurrent testing
def test_concurrent_config():
    # Don't do this - config is a global singleton
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(test_config_setup, i) for i in range(3)]
```

### Test Mode Detection
The config automatically detects test mode:

```python
# Test paths are allowed when running under pytest
os.environ['AUTOTASK_DB_PATH'] = 'test_database.db'  # Allowed in tests
os.environ['AUTOTASK_DB_PATH'] = '/tmp/test_app.db'  # Allowed in tests
```

## Dashboard Configuration

Dashboard files MUST use config for ports:

```python
# ✅ CORRECT - Dashboard file
import streamlit as st
from autotasktracker.config import get_config

config = get_config()
st.set_page_config(page_title="Analytics", page_icon="📊")

if __name__ == "__main__":
    st.run(port=config.ANALYTICS_PORT)

# ❌ WRONG - Dashboard file
import streamlit as st

if __name__ == "__main__":
    st.run(port=8503)  # Hardcoded port not allowed
```

## Available Configuration

### Ports
- `config.MEMOS_PORT` (8839)
- `config.TASK_BOARD_PORT` (8502)
- `config.ANALYTICS_PORT` (8503)
- `config.TIME_TRACKER_PORT` (8505)
- `config.VLM_PORT` (11434)

### Paths
- `config.get_db_path()` - Database file path
- `config.screenshots_dir` - Screenshots directory
- `config.vlm_cache_dir` - VLM cache directory
- `config.memos_dir` - Memos data directory

### Network
- `config.SERVER_HOST` - Hostname for services (default: "localhost")
- `config.get_service_url(service_name)` - Full service URL

### AI Settings
- `config.vlm_model` - VLM model name
- `config.vlm_port` - VLM service port
- `config.embedding_model` - Embedding model name
- `config.batch_size` - Processing batch size

## Environment Variables

All config values can be overridden with environment variables:

```bash
# Database and paths
export AUTOTASK_DB_PATH="/custom/path/database.db"
export AUTOTASK_SCREENSHOTS_DIR="/custom/screenshots"
export AUTOTASK_VLM_CACHE_DIR="/custom/vlm_cache"

# Ports
export AUTOTASK_TASK_BOARD_PORT="9502"
export AUTOTASK_ANALYTICS_PORT="9503"
export AUTOTASK_VLM_PORT="12434"

# AI settings
export AUTOTASK_VLM_MODEL="custom-model"
export AUTOTASK_BATCH_SIZE="100"
export AUTOTASK_CONFIDENCE_THRESHOLD="0.8"

# Application settings
export AUTOTASK_AUTO_REFRESH_SECONDS="60"
```

## Compliance Checking

Use the config compliance scanner to find violations:

```bash
# Scan for violations
python scripts/analysis/config_compliance_scanner.py

# Get fix suggestions
python scripts/analysis/config_compliance_scanner.py --fix

# CI mode (exit 1 if violations found)
python scripts/analysis/config_compliance_scanner.py --ci
```

## Migration from Hardcoded Values

### Step 1: Add Config Import
```python
from autotasktracker.config import get_config
```

### Step 2: Get Config Instance
```python
config = get_config()
```

### Step 3: Replace Hardcoded Values
```python
# Before
db_path = "~/.memos/database.db"
port = 8502
url = "http://localhost:8839"

# After  
db_path = config.get_db_path()
port = config.TASK_BOARD_PORT
url = config.get_service_url('memos')
```

### Step 4: Verify with Scanner
```bash
python scripts/analysis/config_compliance_scanner.py --fix
```

## Best Practices

1. **Always import config** when using ports, paths, or URLs
2. **Use specific config methods** rather than direct attribute access
3. **Test with environment variables** to ensure configurability
4. **Run compliance scanner** before committing changes
5. **Don't hardcode localhost** - use `config.SERVER_HOST`
6. **Use sequential testing** for config-dependent tests
7. **Document environment variables** when adding new config options

## Common Mistakes

❌ **Hardcoding in dashboard files**
```python
streamlit run app.py --server.port 8502  # Wrong
```

❌ **Direct database connections**
```python
sqlite3.connect("~/.memos/database.db")  # Wrong
```

❌ **Hardcoded service URLs**
```python
requests.get("http://localhost:8839/api/health")  # Wrong
```

❌ **Thread-unsafe config testing**
```python
# Don't test config with threads - it's a global singleton
```

✅ **Use config for everything**
```python
from autotasktracker.config import get_config
config = get_config()
```