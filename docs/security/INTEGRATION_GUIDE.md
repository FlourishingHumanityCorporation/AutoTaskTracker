# Meta-Testing Security Integration Guide

## 🚀 Quick Start for Developers

### 1. Initial Setup (One-Time)

```bash
# Install security tools
pip install -r requirements.txt

# Setup git hooks
./scripts/setup_git_hooks.sh

# Verify installation
make security-check
```

### 2. Daily Workflow

#### Before Starting AI-Assisted Development
```bash
# Pull latest security rules
git pull origin main

# Check your environment
make health-check
```

#### During Development
```bash
# After AI generates code
make scan-code

# Before adding dependencies
python scripts/security/package_validator.py --package new-package

# Quick security check
make pre-commit-check
```

#### Before Committing
The pre-commit hook automatically runs security checks. If it fails:

```bash
# See detailed errors
semgrep --config=.semgrep.yml autotasktracker/

# Fix and recheck
make security-check
```

## 📋 Common Scenarios

### Scenario 1: AI Suggests a New Package

```bash
# AI says: "Install awesome-helper package"
# You do:
python scripts/security/package_validator.py --package awesome-helper

# If suspicious (high risk score):
# - Research the package on PyPI
# - Check GitHub repository
# - Look for alternatives
# - Document why you're using it despite risks
```

### Scenario 2: AI Generates Database Code

```python
# ❌ AI might generate:
import sqlite3
conn = sqlite3.connect("~/.memos/database.db")

# ✅ You must change to:
from autotasktracker.core.database import DatabaseManager
db = DatabaseManager()
with db.get_connection() as conn:
    # your code here
```

### Scenario 3: AI Creates New Endpoint

```python
# ❌ AI might generate:
@app.route("/admin/delete-all")
def delete_everything():
    # dangerous operation without auth

# ✅ You must add:
@app.route("/admin/delete-all")
@require_auth(roles=['admin'])
@validate_csrf_token
def delete_everything():
    # safe operation with auth
```

## 🛠️ Tool Integration

### VS Code Setup

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.banditEnabled": true,
  "python.linting.banditArgs": ["--configfile", ".bandit"],
  "files.associations": {
    "*.semgrep.yml": "yaml"
  }
}
```

### PyCharm Setup

1. Install Security plugins:
   - Semgrep Plugin
   - Python Security Plugin

2. Configure External Tools:
   - Name: "AI Security Check"
   - Program: `make`
   - Arguments: `security-check`
   - Working directory: `$ProjectFileDir$`

### GitHub Copilot Integration

When using GitHub Copilot:

1. **Review Mode**: Always review suggestions before accepting
2. **Security Lens**: Check each suggestion against our patterns
3. **Test First**: Write tests before accepting complex suggestions

## 📊 Security Metrics

### Track Your Security Posture

```bash
# Generate security report
python scripts/security/generate_metrics.py  # TODO: Create this

# Key metrics to track:
# - Security issues per 1000 lines of code
# - Time to fix security issues
# - False positive rate
# - Package risk scores
```

### Team Dashboard

Access the security dashboard (when available):
- http://localhost:8509/security-metrics
- Shows trends, common issues, team performance

## 🔥 Incident Response

### If Security Tools Find Issues

1. **High Severity** (Blocks commit):
   - Fix immediately
   - Cannot be bypassed
   - Examples: Hardcoded secrets, SQL injection

2. **Medium Severity** (Warning):
   - Fix before merging to main
   - Can commit locally for WIP
   - Examples: Missing error handling

3. **Low Severity** (Info):
   - Fix in next refactor
   - Track in backlog
   - Examples: Code style issues

### Emergency Bypass

**Use only when absolutely necessary:**

```bash
# Bypass pre-commit (document why!)
git commit --no-verify -m "EMERGENCY: [reason]"

# Create immediate follow-up task
echo "Fix security issues in commit abc123" >> TODO.md
```

## 📚 Learning Resources

### Internal Resources
- [AI Code Security Quick Reference](AI_CODE_SECURITY_QUICKREF.md)
- [Meta-Testing Implementation](META_TESTING_IMPLEMENTATION.md)
- [Security Tools README](../../scripts/security/README.md)

### External Resources
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Semgrep Rule Writing](https://semgrep.dev/docs/writing-rules/overview/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)

## 🎯 Security Champions Program

### Becoming a Security Champion
1. Complete security training
2. Contribute 3+ Semgrep rules
3. Mentor team on secure AI coding
4. Lead security reviews

### Champion Responsibilities
- Review high-risk AI code
- Update security patterns
- Train team members
- Track security metrics

## 📈 Continuous Improvement

### Monthly Security Review
- Review new AI vulnerability patterns
- Update Semgrep rules
- Analyze security metrics
- Plan improvements

### Quarterly Security Training
- New attack vectors
- Tool updates
- Process improvements
- Case studies

## 🆘 Getting Help

### Slack Channels
- #security - General security questions
- #ai-code-review - AI code review help
- #security-tools - Tool issues/questions

### Escalation Path
1. Try automated tools first
2. Check documentation
3. Ask in Slack
4. Contact Security Champion
5. File security ticket

## ✅ Checklist for New Developers

- [ ] Installed all security tools
- [ ] Configured git hooks
- [ ] Read AI Code Security Quick Reference
- [ ] Completed security training
- [ ] Ran first security check
- [ ] Joined security Slack channels

---

**Remember**: Security is everyone's responsibility. When in doubt, ask!

*Last Updated: 2025-07-05*