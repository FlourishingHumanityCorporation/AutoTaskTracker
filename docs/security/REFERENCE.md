# Security Technical Reference

## Tool Configuration

### Semgrep (.semgrep.yml)

AI-specific security rules targeting common patterns in AI-generated code:

```yaml
rules:
  - id: missing-auth-on-streamlit-endpoints
  - id: database-queries-without-validation  
  - id: missing-pensieve-integration
  - id: unsafe-file-operations
  - id: suspicious-imports
```

**Custom Rules Target:**
- Streamlit dashboards without authentication
- Database queries missing parameterization
- Direct file operations bypassing Pensieve
- Suspicious or non-existent package imports

### Bandit (.bandit)

```yaml
exclude_dirs:
  - /tests
  - /venv
  - /__pycache__

skips:
  - B101  # assert_used (common in tests)

tests:
  - B201  # flask_debug_true
  - B324  # hashlib_insecure_functions
  - B602  # subprocess_popen_with_shell_equals_true
  - B608  # hardcoded_sql_expressions
```

### Package Validator

**Script:** `scripts/security/package_validator.py`

**Features:**
- PyPI API integration
- Typosquatting detection  
- Package age verification
- Download count analysis
- Maintainer reputation check

**Risk Scoring (0-10):**
- 0-3: Low risk (established packages)
- 4-6: Medium risk (newer packages)
- 7-10: High risk (suspicious/non-existent)

## CI/CD Integration

### GitHub Actions (.github/workflows/ci.yml)

```yaml
security-scan:
  steps:
    - Install tools: semgrep bandit safety pip-audit
    - Run Semgrep with AI rules
    - Run Bandit security scan
    - Run pip-audit for vulnerabilities
    - Validate package legitimacy
    - Upload reports as artifacts
```

### Pre-commit Hook

```bash
#!/bin/bash
# .githooks/pre-commit
python scripts/security/package_validator.py --git-staged
bandit -r autotasktracker/ --severity-level medium
```

## Configuration Files

### .semgrep.yml
- 10+ AI-specific rules
- Pattern matching for common AI code issues
- Severity levels: ERROR, WARNING, INFO

### .bandit
- Excludes test directories
- Focuses on high/medium severity issues
- Customized for Python security

### .safety-policy.json
- Vulnerability threshold settings
- Package exemptions
- Update frequency configuration

## Advanced Usage

### Running Targeted Scans

```bash
# Scan only AI modules
semgrep --config=.semgrep.yml autotasktracker/ai/

# High-severity issues only
bandit -r autotasktracker/ -ll

# Check specific package
python scripts/security/package_validator.py --package numpy --verbose
```

### Custom Semgrep Rules

Add to `.semgrep.yml`:

```yaml
- id: custom-autotasktracker-pattern
  pattern: $X.connect("~/.memos/database.db")
  message: Use DatabaseManager instead of direct connection
  severity: ERROR
```

### Integration with Development

1. **IDE Integration**: Install Semgrep VS Code extension
2. **Git Hooks**: Auto-run on commit
3. **CI/CD**: Block PRs with security issues
4. **Monitoring**: Track security metrics over time

## Performance Optimization

- Use `--jobs 4` for parallel Semgrep scanning
- Cache pip-audit results with `--cache-dir`
- Run incremental scans on changed files only

For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).