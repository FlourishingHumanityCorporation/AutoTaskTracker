# Configuration Migration Guide

This guide explains how to migrate from the old `Config` class to the new Pydantic-based configuration system.

## Overview

The AutoTaskTracker configuration system has been modernized from a custom `Config` class to a Pydantic-based system that provides:
- Type safety and automatic validation
- Environment variable support with `.env` files
- Nested configuration structure
- Better error messages

## Migration Examples

### Basic Usage

**Old Pattern:**
```python
from autotasktracker.utils.config import Config

# Creating config with custom values
config = Config(
    TASK_BOARD_PORT=9000,
    DB_PATH='/custom/path/db.db'
)

# Accessing values
port = config.TASK_BOARD_PORT
db_path = config.DB_PATH
```

**New Pattern:**
```python
from autotasktracker.config import get_config

# Get singleton config instance
config = get_config()

# Accessing values (backward compatible)
port = config.TASK_BOARD_PORT
db_path = config.DB_PATH

# Or use new nested structure
port = config.server.task_board_port
db_path = config.database.path
```

### Testing with Custom Values

**Old Pattern:**
```python
def test_something():
    config = Config(MEMOS_PORT=9999)
    assert config.MEMOS_PORT == 9999
```

**New Pattern:**
```python
import os
from unittest.mock import patch
from autotasktracker.config import get_config, reset_config

def test_something():
    with patch.dict(os.environ, {'AUTOTASK_SERVER__MEMOS_PORT': '9999'}):
        reset_config()  # Clear cached config
        config = get_config()
        assert config.MEMOS_PORT == 9999
```

### Environment Variables

The new system uses environment variables with a specific naming pattern:

- Top-level settings: `AUTOTASK_<FIELD_NAME>`
- Nested settings: `AUTOTASK_<SECTION>__<FIELD_NAME>` (note the double underscore)

**Examples:**
```bash
# Top-level setting
AUTOTASK_DEBUG=true

# Nested settings
AUTOTASK_DATABASE__PATH=/custom/db.db
AUTOTASK_SERVER__TASK_BOARD_PORT=9000
AUTOTASK_VLM__MODEL=llava
```

### Configuration Structure

**Old Structure (flat):**
```python
config.DB_PATH
config.TASK_BOARD_PORT
config.VLM_MODEL
config.EMBEDDING_MODEL
```

**New Structure (nested):**
```python
config.database.path
config.server.task_board_port
config.vlm.model
config.embedding.model
```

### Service URL Generation

**Old Pattern:**
```python
url = config.get_service_url('task_board')
```

**New Pattern:**
```python
# Same method still works
url = config.get_service_url('task_board')
```

### Validation

**Old Pattern:**
```python
config = Config(MEMOS_PORT=500)
if not config.validate():
    print("Invalid config")
```

**New Pattern:**
```python
# Validation happens automatically
try:
    config = get_config()
except ValidationError as e:
    print(f"Invalid config: {e}")

# Or check after loading
if not config.validate():
    print("Invalid config")
```

## Common Migration Tasks

### 1. Update Imports

```python
# Old
from autotasktracker.utils.config import Config

# New
from autotasktracker.config import get_config, reset_config
```

### 2. Replace Config() Constructor

```python
# Old
config = Config(TASK_BOARD_PORT=9000)

# New (for testing)
with patch.dict(os.environ, {'AUTOTASK_SERVER__TASK_BOARD_PORT': '9000'}):
    reset_config()
    config = get_config()
```

### 3. Update Docker/Deployment Scripts

Update your `.env` files or docker-compose environment sections:

```yaml
# docker-compose.yml
environment:
  - AUTOTASK_DATABASE__PATH=/data/db.db
  - AUTOTASK_SERVER__TASK_BOARD_PORT=8502
  - AUTOTASK_VLM__MODEL=minicpm-v
```

## Legacy Compatibility

All old attribute names (e.g., `DB_PATH`, `TASK_BOARD_PORT`) are maintained as properties for backward compatibility. This means existing code will continue to work without modification.

## Deprecation Timeline

1. **Current**: Both old and new patterns work
2. **Next Release**: Deprecation warnings added to old `Config` class
3. **Future Release**: Old `Config` class removed

## Benefits of Migration

1. **Type Safety**: Automatic type conversion and validation
2. **Better Errors**: Clear validation error messages
3. **Environment Support**: Native `.env` file support
4. **IDE Support**: Better autocomplete with typed fields
5. **Maintainability**: Cleaner, more organized configuration

## Need Help?

If you encounter issues during migration:
1. Check that environment variables use double underscores for nested values
2. Ensure `reset_config()` is called in tests when changing environment
3. Verify your `.env` file follows the naming pattern in `.env.example`