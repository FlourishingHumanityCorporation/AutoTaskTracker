# Security Quick Start Guide

## Overview

AutoTaskTracker uses AI-specific security tools to catch issues common in AI-generated code:
- Missing authentication
- Fake package suggestions
- Poor error handling
- SQL injection risks

## Setup (5 minutes)

1. **Use the correct environment:**
   ```bash
   cd /Users/paulrohde/CodeProjects/AutoTaskTracker
   source venv/bin/activate  # CRITICAL: Use venv, not anaconda
   ```

2. **Install security tools:**
   ```bash
   pip install semgrep bandit pip-audit
   ```

3. **Run security check:**
   ```bash
   make security-check
   ```

## What Each Tool Does

- **Semgrep**: Finds AI-specific patterns (missing auth, unsafe operations)
- **Bandit**: Python security issues (subprocess, SQL, crypto)
- **pip-audit**: Checks dependencies for known vulnerabilities
- **Package Validator**: Prevents installation of fake packages

## Common Commands

```bash
# Full security scan
make security-check

# Check specific file
semgrep --config=.semgrep.yml path/to/file.py

# Validate a package before installing
python scripts/security/package_validator.py --package suspicious-package

# Set up git pre-commit hook
./scripts/setup_git_hooks.sh
```

## Fixing Common Issues

### MD5 Hash Warnings
```python
# Wrong
hashlib.md5(data).hexdigest()

# Right  
hashlib.md5(data, usedforsecurity=False).hexdigest()
```

### Subprocess Security
```python
# Wrong
subprocess.run(command, shell=True)

# Right
import shlex
subprocess.run(shlex.split(command))
```

### SQL Injection Prevention
```python
# Wrong
cursor.execute(f"SELECT * FROM table WHERE id = {user_input}")

# Right
cursor.execute("SELECT * FROM table WHERE id = ?", (user_input,))
```

## Next Steps

1. Review Semgrep findings: `semgrep --config=.semgrep.yml autotasktracker/`
2. Fix any high-severity Bandit issues
3. Keep dependencies updated with `pip-audit`

For detailed information, see [REFERENCE.md](REFERENCE.md).