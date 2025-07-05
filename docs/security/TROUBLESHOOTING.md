# Security Troubleshooting Guide

## Common Issues and Solutions

### Environment Issues

**Problem:** Semgrep won't install
```
ERROR: Could not find a version that satisfies the requirement semgrep
```

**Solution:** Use venv, not anaconda
```bash
cd /Users/paulrohde/CodeProjects/AutoTaskTracker
python3 -m venv venv
source venv/bin/activate
pip install semgrep
```

### Tool-Specific Issues

#### Semgrep

**Problem:** "No rules found" error
- **Cause:** Wrong config file path
- **Fix:** Use `--config=.semgrep.yml` (note the dot)

**Problem:** Too many false positives
- **Cause:** Rules too broad
- **Fix:** Add `pattern-not` exclusions to rules

#### Bandit

**Problem:** B608 SQL warnings on safe code
- **Cause:** Bandit can't detect parameterized queries in f-strings
- **Fix:** These are usually false positives if using `?` placeholders

**Problem:** MD5 warnings everywhere
- **Cause:** MD5 used for non-security purposes (caching)
- **Fix:** Add `usedforsecurity=False` parameter

#### pip-audit

**Problem:** Cache deserialization warnings
```
WARNING:cachecontrol.controller:Cache entry deserialization failed
```
- **Cause:** Corrupted cache from Python version mismatch
- **Fix:** Clear cache: `rm -rf ~/.cache/pip-audit/`

**Problem:** No vulnerabilities found (when you expect some)
- **Cause:** Outdated vulnerability database
- **Fix:** Force update: `pip-audit --refresh`

### Package Validator

**Problem:** HTTPError when checking packages
- **Cause:** PyPI API rate limiting
- **Fix:** Add delay between checks or use `--cache`

**Problem:** False positives on internal packages
- **Cause:** Private packages not on PyPI
- **Fix:** Add to exemption list in validator script

### CI/CD Issues

**Problem:** Security scan passes locally but fails in CI
- **Cause:** Different Python versions or missing tools
- **Fix:** Ensure CI installs all tools: `pip install semgrep bandit safety pip-audit`

**Problem:** Timeout in security scans
- **Cause:** Large codebase, slow runners
- **Fix:** Use parallel execution: `semgrep --jobs 4`

### Performance Issues

**Slow Scans:**
```bash
# Scan only changed files
git diff --name-only | grep "\.py$" | xargs semgrep --config=.semgrep.yml

# Use file size limits
semgrep --max-target-bytes 500000

# Exclude generated files
semgrep --exclude "*.generated.py"
```

### Integration Issues

**Git Hook Not Running:**
```bash
# Check hook is executable
chmod +x .githooks/pre-commit

# Verify git config
git config core.hooksPath .githooks
```

**VS Code Integration:**
1. Install Semgrep extension
2. Set workspace settings:
   ```json
   {
     "semgrep.rules": [".semgrep.yml"],
     "semgrep.exclude": ["tests/", "venv/"]
   }
   ```

## Debug Commands

```bash
# Test Semgrep rules
semgrep --test .semgrep.yml

# Verbose Bandit output
bandit -r autotasktracker/ -v

# Package validator debug mode
python scripts/security/package_validator.py --package test --debug

# Check tool versions
semgrep --version
bandit --version
pip-audit --version
```

## Getting Help

1. Check tool documentation:
   - [Semgrep docs](https://semgrep.dev/docs/)
   - [Bandit docs](https://bandit.readthedocs.io/)
   - [pip-audit docs](https://github.com/pypa/pip-audit)

2. AutoTaskTracker-specific issues:
   - Review [QUICKSTART.md](QUICKSTART.md) for setup
   - Check [REFERENCE.md](REFERENCE.md) for configuration

3. File issues:
   - Include tool versions
   - Provide minimal reproduction
   - Share relevant config files