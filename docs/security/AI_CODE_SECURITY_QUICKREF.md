# 🛡️ AI Code Security Quick Reference

## 🚨 Before You Commit AI-Generated Code

### 1️⃣ Run Security Scans
```bash
# Quick security check (30 seconds)
semgrep --config=.semgrep.yml path/to/your/file.py --quiet

# Full security validation (2 minutes)
make security-check  # If available, or:
semgrep --config=.semgrep.yml autotasktracker/
bandit -r autotasktracker/
```

### 2️⃣ Validate New Dependencies
```bash
# NEVER blindly trust AI package suggestions!
python scripts/security/package_validator.py --package suspicious-package

# Check all dependencies
python scripts/security/package_validator.py --requirements requirements.txt
```

### 3️⃣ Review Checklist for AI Code

**Security Fundamentals**
- [ ] Authentication required on all endpoints?
- [ ] Input validation and sanitization present?
- [ ] No hardcoded credentials or API keys?
- [ ] Error handling doesn't expose sensitive info?

**AutoTaskTracker Patterns**
- [ ] Uses DatabaseManager, not sqlite3.connect()?
- [ ] Follows Pensieve integration patterns?
- [ ] No print() statements (use logging)?
- [ ] No bare except: clauses?

**Dependencies**
- [ ] All new packages validated?
- [ ] No packages with suspicious names?
- [ ] Version pinning in requirements.txt?

## 🔴 Red Flags in AI-Generated Code

### Immediate Blockers
```python
# ❌ NEVER: Direct database connections
conn = sqlite3.connect("database.db")

# ❌ NEVER: Hardcoded secrets
API_KEY = "sk-1234567890abcdef"

# ❌ NEVER: Unsafe operations
eval(user_input)
exec(dynamic_code)

# ❌ NEVER: Missing authentication
@app.route("/delete-user")  # No auth!
def delete_user(user_id):
    pass
```

### Common AI Mistakes
```python
# ❌ Missing input validation
user_input = request.form['data']
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# ❌ Broad exception handling
try:
    risky_operation()
except:  # Catches everything!
    pass

# ❌ Information disclosure
except Exception as e:
    return f"Error: {e}"  # Exposes internals
```

## ✅ Correct Patterns

### Secure Database Access
```python
# ✅ Use DatabaseManager
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    # Parameterized queries
    conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

### Proper Error Handling
```python
# ✅ Specific exceptions with safe messages
try:
    result = process_user_data(input_data)
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    return {"error": "Invalid input provided"}, 400
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    return {"error": "Service temporarily unavailable"}, 503
```

### Secure Configuration
```python
# ✅ Environment variables for secrets
import os
from autotasktracker.config import get_config

config = get_config()
api_key = os.environ.get('API_KEY')
if not api_key:
    raise ValueError("API_KEY environment variable not set")
```

## 🎯 Quick Commands

### Security Testing
```bash
# Test specific dashboard
python scripts/security/dashboard_security_tester.py --port 8502

# Test all dashboards
python scripts/security/dashboard_security_tester.py --all

# Run health checks
pytest tests/health/test_metatesting_security.py -v
```

### Package Management
```bash
# Before pip install
python scripts/security/pre_install_hook.py --package package-name

# Validate requirements file
python scripts/security/package_validator.py --requirements requirements.txt --fail-on-suspicious
```

## 📋 Security Tool Status

| Tool | Purpose | Config File | CI Status |
|------|---------|-------------|-----------|
| Semgrep | AI-specific patterns | `.semgrep.yml` | ✅ Active |
| Bandit | Python security | `.bandit` | ✅ Active |
| Safety | CVE scanning | `.safety-policy.json` | ✅ Active |
| pip-audit | Dependency audit | Built-in | ✅ Active |
| Package Validator | Slopsquatting | `scripts/security/` | ✅ Active |
| DAST | Runtime testing | `scripts/security/` | ✅ Active |

## 🆘 Getting Help

1. **Security Questions**: Check `scripts/security/README.md`
2. **AI Patterns**: Review `docs/guides/workflow_patterns.md`
3. **Meta-Testing Details**: See `docs/security/META_TESTING_IMPLEMENTATION.md`
4. **Report Issues**: Create ticket with `security` label

## 🔑 Key Principles

1. **AI = Junior Developer**: Review with same scrutiny
2. **Context is King**: AI lacks project-specific knowledge
3. **Verify Everything**: Dependencies, patterns, security
4. **Automate Checks**: Let tools catch common issues
5. **Document Decisions**: Why you accepted/rejected AI code

---

**Remember**: The AI is a tool. You are responsible for the code you commit.

*Quick Reference Version 1.0 | Updated: 2025-07-05*