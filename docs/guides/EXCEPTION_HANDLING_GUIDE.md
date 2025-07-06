# Exception Handling Guide for AutoTaskTracker

## Overview

This guide provides patterns for replacing generic exception handlers with specific ones throughout the codebase.

## Custom Exception Hierarchy

Use the custom exceptions defined in `autotasktracker.core.exceptions`:

```python
from autotasktracker.core.exceptions import (
    DatabaseError,
    ConfigurationError,
    AIProcessingError,
    PensieveIntegrationError,
    ValidationError
)
```

## Common Patterns

### 1. Database Operations

**Instead of:**
```python
except Exception as e:
    logger.error(f"Database error: {e}")
```

**Use:**
```python
except sqlite3.OperationalError as e:
    logger.error(f"Database locked or corrupted: {e}")
except sqlite3.DatabaseError as e:
    logger.error(f"Database query failed: {e}")
except pd.errors.DatabaseError as e:
    logger.error(f"Pandas SQL error: {e}")
except ConnectionError as e:
    logger.error(f"Database connection lost: {e}")
```

### 2. File Operations

**Instead of:**
```python
except Exception as e:
    logger.error(f"File error: {e}")
```

**Use:**
```python
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
except OSError as e:
    logger.error(f"OS error (disk full/path invalid): {e}")
```

### 3. JSON Operations

**Instead of:**
```python
except Exception as e:
    logger.error(f"JSON error: {e}")
```

**Use:**
```python
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON format: {e}")
except TypeError as e:
    logger.error(f"Non-serializable object: {e}")
except ValueError as e:
    logger.error(f"Invalid value for JSON: {e}")
```

### 4. Network/API Operations

**Instead of:**
```python
except Exception as e:
    logger.error(f"API error: {e}")
```

**Use:**
```python
except PensieveAPIError as e:
    logger.error(f"Pensieve API error: {e.message}")
except ConnectionError as e:
    logger.error(f"Network connection failed: {e}")
except TimeoutError as e:
    logger.error(f"Request timed out: {e}")
except requests.RequestException as e:
    logger.error(f"HTTP request failed: {e}")
```

### 5. AI/Model Operations

**Instead of:**
```python
except Exception as e:
    logger.error(f"AI processing error: {e}")
```

**Use:**
```python
except ImportError as e:
    logger.error(f"Required AI library not installed: {e}")
except ValueError as e:
    logger.error(f"Invalid input for model: {e}")
except RuntimeError as e:
    logger.error(f"Model execution failed: {e}")
except AIProcessingError as e:
    logger.error(f"AI processing failed: {e}")
```

## Migration Strategy

1. **Start with critical paths**: Database operations, API calls, file I/O
2. **Keep generic handler as last resort**: Always include a final generic handler for truly unexpected errors
3. **Log appropriate level**: Use `logger.debug()` for expected errors, `logger.error()` for unexpected ones
4. **Add context**: Include relevant variables in error messages
5. **Consider recovery**: Different exceptions may require different recovery strategies

## Example Migration

**Before:**
```python
def process_data(data):
    try:
        result = json.loads(data)
        db.save(result)
        return True
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return False
```

**After:**
```python
def process_data(data):
    try:
        result = json.loads(data)
        db.save(result)
        return True
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in data: {e}")
        return False
    except DatabaseError as e:
        logger.error(f"Failed to save to database: {e}")
        # Could retry or queue for later
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing data: {e}")
        return False
```

## Testing Exception Handling

Always test your exception handlers:

```python
def test_handle_json_error():
    """Test that JSON errors are handled properly."""
    with pytest.raises(json.JSONDecodeError):
        process_data("invalid json")
```