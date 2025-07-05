# Config System Architecture

This document explains the AutoTaskTracker configuration system architecture and its design decisions.

## Architecture Overview

The config system uses a **process-level singleton pattern** with **thread-safe initialization** and **security validation**.

```python
# Global singleton instance
_config_instance: Optional[Config] = None
_config_lock = None

def get_config() -> Config:
    """Thread-safe singleton pattern with lazy initialization."""
    global _config_instance, _config_lock
    
    if _config_instance is not None:
        return _config_instance
    
    if _config_lock is None:
        _config_lock = threading.Lock()
    
    with _config_lock:
        if _config_instance is None:
            _config_instance = Config()
        return _config_instance
```

## Design Decisions

### 1. Process-Level Singleton (Not Thread-Level)

**Why**: Configuration should be consistent across the entire application process.

**Implications**:
- One config instance per process
- All threads share the same configuration
- Environment changes affect the entire process
- Tests must run sequentially for config changes

### 2. Immutable After Initialization

**Why**: Prevents configuration drift and race conditions.

**Implementation**:
- Config is created once from environment variables
- No runtime modification of config values
- Changes require process restart or `reset_config()`

### 3. Security Validation

**Why**: Prevent path traversal and malicious configuration.

**Features**:
- Path validation with allowed prefixes
- Port range validation (1024-65535)
- Dangerous pattern detection
- Test mode detection for relaxed validation

## Configuration Flow

```
1. Application Start
   ↓
2. First get_config() Call
   ↓
3. Thread-Safe Initialization
   ↓
4. Read Environment Variables
   ↓
5. Validate All Values
   ↓
6. Create Config Instance
   ↓
7. Return Singleton
```

## Testing Architecture

### Process-Level Testing

```python
# ✅ CORRECT - Sequential testing
def test_config_scenario_1():
    with patch.dict(os.environ, {'AUTOTASK_DB_PATH': '/tmp/test1.db'}):
        reset_config()
        config = get_config()
        assert config.get_db_path() == '/tmp/test1.db'

def test_config_scenario_2():
    with patch.dict(os.environ, {'AUTOTASK_DB_PATH': '/tmp/test2.db'}):
        reset_config()
        config = get_config()
        assert config.get_db_path() == '/tmp/test2.db'
```

### Why Thread-Level Testing Fails

```python
# ❌ WRONG - This doesn't work
def test_concurrent_config():
    def test_thread(thread_id):
        with patch.dict(os.environ, {'AUTOTASK_DB_PATH': f'/tmp/test{thread_id}.db'}):
            reset_config()  # ⚠️ Global singleton reset
            config = get_config()  # ⚠️ Shared instance
            return config.get_db_path()
    
    # All threads get the same config instance
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(test_thread, i) for i in range(3)]
        results = [f.result() for f in futures]
        # Results are unpredictable due to race conditions
```

### Test Mode Detection

The config system automatically detects test environments:

```python
def _validate_path_security(path: str) -> str:
    # Check if we're in test mode
    is_test_mode = (
        os.getenv("PYTEST_CURRENT_TEST") is not None or
        os.getenv("AUTOTASK_TEST_MODE") == "1" or
        "test" in sys.argv[0].lower() or
        any("pytest" in arg for arg in sys.argv)
    )
    
    # In test mode, allow test-specific paths
    if is_test_mode and ("test" in path.lower() or path.startswith("test_")):
        return path
```

## Environment Variable Processing

### Validation Pipeline

```
Environment Variable
        ↓
Type Conversion (int, float, str)
        ↓
Range/Format Validation
        ↓
Security Validation
        ↓
Fallback to Default (if invalid)
        ↓
Store in Config
```

### Example: Port Validation

```python
def _validate_port_security(port: Union[str, int]) -> int:
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        raise ValueError(f"Port must be a valid integer: {port}")
    
    if port_int < 1024:
        raise ValueError(f"Privileged port not allowed: {port_int}")
    
    if not (1024 <= port_int <= 65535):
        raise ValueError(f"Port out of valid range: {port_int}")
    
    return port_int
```

## Error Handling Strategy

### Graceful Degradation

When configuration fails, the system falls back to safe defaults:

```python
def __post_init__(self):
    try:
        # Attempt to load and validate configuration
        self._load_environment_variables()
    except Exception as e:
        logger.error(f"Error during config initialization: {e}")
        # Fall back to safe defaults
        self._initialize_safe_defaults()
```

### Safe Defaults

```python
def _initialize_safe_defaults(self):
    """Initialize with safe default values in case of configuration errors."""
    self.db_path = Path(os.path.expanduser("~/.memos/database.db"))
    self.vlm_port = 11434
    self.batch_size = 50
    # ... other safe defaults
```

## Configuration Categories

### 1. Paths
- Database path (`DB_PATH`)
- Screenshots directory (`SCREENSHOTS_DIR`) 
- VLM cache directory (`VLM_CACHE_DIR`)

### 2. Network
- Service ports (`TASK_BOARD_PORT`, `ANALYTICS_PORT`, etc.)
- Server hostname (`SERVER_HOST`)

### 3. AI Settings
- Model names (`VLM_MODEL`, `EMBEDDING_MODEL`)
- Processing parameters (`BATCH_SIZE`, `CONFIDENCE_THRESHOLD`)

### 4. Application Settings
- Refresh intervals (`AUTO_REFRESH_SECONDS`)
- Cache settings (`CACHE_TTL_SECONDS`)

## Security Considerations

### Path Security

```python
# Rejected patterns
dangerous_patterns = [
    '/etc/', '/bin/', '/usr/bin/', '/sbin/', '/var/log/',
    'system32', 'windows', 'passwd', 'shadow', 'hosts',
    '..', '%', '$', '`', ';', '|', '&', '>', '<'
]

# Allowed prefixes
allowed_prefixes = [home_dir, "/tmp", "/var/folders", "./", os.getcwd()]
```

### Port Security

- No privileged ports (< 1024)
- Valid range: 1024-65535
- No system service ports (22, 80, 443, etc.)

## Testing Strategy

### Unit Tests

Test individual config validation functions:

```python
def test_port_validation():
    assert _validate_port_security("8502") == 8502
    
    with pytest.raises(ValueError):
        _validate_port_security("80")  # Privileged port
        
    with pytest.raises(ValueError):
        _validate_port_security("not_a_number")
```

### Integration Tests

Test complete config loading with environment variables:

```python
def test_valid_environment_variables():
    env_vars = {
        'AUTOTASK_DB_PATH': '/tmp/test.db',
        'AUTOTASK_VLM_PORT': '25000',
        'AUTOTASK_BATCH_SIZE': '100'
    }
    
    with patch.dict(os.environ, env_vars):
        reset_config()
        config = get_config()
        
        assert config.get_db_path() == '/tmp/test.db'
        assert config.vlm_port == 25000
        assert config.batch_size == 100
```

### System Tests

Test actual config behavior in realistic scenarios:

```python
def test_invalid_values_fallback_to_defaults():
    invalid_env = {
        'AUTOTASK_VLM_PORT': 'invalid_port',
        'AUTOTASK_BATCH_SIZE': 'not_a_number'
    }
    
    with patch.dict(os.environ, invalid_env):
        reset_config()
        config = get_config()
        
        # Should fall back to defaults
        assert isinstance(config.vlm_port, int)
        assert isinstance(config.batch_size, int)
```

## Performance Considerations

### Lazy Initialization

- Config is only created when first accessed
- Thread-safe initialization prevents multiple instances
- Subsequent calls return cached instance

### Memory Efficiency

- Single instance per process
- No unnecessary object creation
- Path objects created once

## Migration Guide

### From Hardcoded Values

```python
# Before
DATABASE_PATH = "~/.memos/database.db"
TASK_BOARD_PORT = 8502

# After
from autotasktracker.config import get_config
config = get_config()
database_path = config.get_db_path()
task_board_port = config.TASK_BOARD_PORT
```

### Adding New Configuration

1. Add field to `Config` dataclass
2. Add environment variable processing in `__post_init__`
3. Add validation if needed
4. Update documentation
5. Add tests

## Best Practices

### For Developers

1. **Always use config** - Never hardcode paths, ports, or URLs
2. **Import once** - Import config at module level when possible
3. **Test with environment variables** - Verify configurability
4. **Use specific methods** - Prefer `config.get_db_path()` over `str(config.db_path)`

### For Tests

1. **Test sequentially** - Don't use threads for config testing
2. **Use valid values** - Test with realistic configuration
3. **Reset between tests** - Use `reset_config()` to clear state
4. **Mock environment** - Use `patch.dict(os.environ)` for isolation

### For Deployment

1. **Set environment variables** - Override defaults in production
2. **Validate configuration** - Check config after deployment
3. **Monitor logs** - Watch for config validation warnings
4. **Document variables** - Keep environment variable docs updated

## Troubleshooting

### Common Issues

1. **Config not updating**: Check if `reset_config()` was called
2. **Invalid values ignored**: Check logs for validation warnings  
3. **Thread safety issues**: Don't modify config from multiple threads
4. **Test isolation**: Use environment variable mocking properly

### Debugging

```python
# Check current config
config = get_config()
print(f"DB Path: {config.get_db_path()}")
print(f"VLM Port: {config.vlm_port}")

# Reset and reload
reset_config()
config = get_config()
```