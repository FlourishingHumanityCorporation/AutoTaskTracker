# Memos Configuration Guide for AutoTaskTracker

## Overview

This guide explains how to configure memos/pensieve to use AutoTaskTracker-specific settings permanently.

## Configuration Resolution Order

Memos uses this order of precedence for configuration:

1. **Environment Variables** (Highest Priority)
2. **YAML Configuration File** (`~/.memos/config.yaml`)
3. **Default Values** (Lowest Priority)

## Available Environment Variables

All memos settings can be overridden using environment variables with the `MEMOS_` prefix:

### Core Settings
- `MEMOS_BASE_DIR`: Base directory for all memos data
- `MEMOS_DATABASE_PATH`: Database connection string (SQLite path or PostgreSQL URL)
- `MEMOS_SCREENSHOTS_DIR`: Directory for screenshots
- `MEMOS_SERVER_HOST`: Server host address
- `MEMOS_SERVER_PORT`: Server port number
- `MEMOS_RECORD_INTERVAL`: Screenshot capture interval in seconds

### Plugin Settings
- `MEMOS_OCR_ENABLED`: Enable/disable OCR plugin
- `MEMOS_VLM_ENABLED`: Enable/disable VLM plugin
- `MEMOS_DEFAULT_PLUGINS`: Comma-separated list of default plugins

## Permanent Configuration Methods

### Method 1: Direct Config File Replacement (Recommended)

The most robust approach is to directly replace the main config file:

```bash
# Backup original config
cp ~/.memos/config.yaml ~/.memos/config.yaml.original

# Copy AutoTaskTracker config to main config
cp ~/.memos/config_autotasktracker.yaml ~/.memos/config.yaml

# Restart memos services
memos stop
memos start
```

**Pros:**
- Always works regardless of how memos is invoked
- No need to set environment variables
- Configuration persists across system restarts
- Works with all memos commands

**Cons:**
- Overwrites the default config file
- May need to be redone if memos is reinstalled

### Method 2: Environment Variables via Shell Profile

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# AutoTaskTracker memos configuration
export MEMOS_BASE_DIR="/Users/paulrohde/AutoTaskTracker.memos"
export MEMOS_DATABASE_PATH="postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"
export MEMOS_SCREENSHOTS_DIR="/Users/paulrohde/AutoTaskTracker.memos/screenshots"
export MEMOS_SERVER_PORT="8841"
export MEMOS_SERVER_HOST="localhost"
```

**Pros:**
- Keeps original config file intact
- Easy to version control
- Can be easily enabled/disabled

**Cons:**
- Only works for interactive shells
- May not work for system services or cron jobs

### Method 3: Wrapper Script

Use the provided wrapper script:

```bash
# Use wrapper script instead of direct memos command
/Users/paulrohde/CodeProjects/AutoTaskTracker/scripts/memos_autotask.sh config
/Users/paulrohde/CodeProjects/AutoTaskTracker/scripts/memos_autotask.sh start
```

**Pros:**
- Flexible and portable
- Can be version controlled
- Easy to customize

**Cons:**
- Requires remembering to use wrapper script
- May not work with all integrations

### Method 4: Environment File

Source the environment file when needed:

```bash
# Source environment variables
source /Users/paulrohde/CodeProjects/AutoTaskTracker/scripts/memos_autotask.env

# Then use memos normally
memos config
memos start
```

**Pros:**
- Temporary configuration
- Easy to enable/disable
- Good for testing

**Cons:**
- Must be sourced in each session
- Not persistent across shell sessions

## Verification

After applying any configuration method, verify it works:

```bash
# Check configuration
memos config

# Verify key settings
memos config | grep -E "(base_dir|database_path|screenshots_dir|server_port)"

# Check service status
memos ps
```

## Troubleshooting

### Config Not Taking Effect

1. **Check config file syntax:** YAML must be valid
2. **Restart services:** Some changes require restart
3. **Check environment variables:** Use `env | grep MEMOS` to verify
4. **Verify file permissions:** Config files must be readable

### Services Not Starting

1. **Check database connection:** Ensure PostgreSQL is running
2. **Check port conflicts:** Ensure port 8841 is available
3. **Check directory permissions:** Ensure base directory is writable
4. **Check logs:** Look in `~/.memos/logs/` for error messages

## Current AutoTaskTracker Configuration

```yaml
base_dir: /Users/paulrohde/AutoTaskTracker.memos
database_path: postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker
screenshots_dir: /Users/paulrohde/AutoTaskTracker.memos/screenshots
server_host: localhost
server_port: 8841
default_plugins:
  - builtin_ocr
  - builtin_vlm
record_interval: 4
watch:
  processing_interval: 1
  rate_window_size: 20
  sparsity_factor: 1
```

## Best Practices

1. **Always backup config files** before making changes
2. **Test configuration changes** in development first
3. **Document any manual changes** for future reference
4. **Use version control** for configuration files when possible
5. **Monitor service logs** after configuration changes