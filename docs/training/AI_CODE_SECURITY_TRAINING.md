# AI Code Security Training Module

## 🎓 Module Overview

**Duration:** 2 hours  
**Level:** All developers using AI coding assistants  
**Objective:** Master secure AI-assisted development practices

## 📚 Learning Objectives

By the end of this module, you will:
1. Understand unique vulnerabilities in AI-generated code
2. Apply the "AI as Junior Developer" review paradigm
3. Use AutoTaskTracker's security tools effectively
4. Write secure prompts that generate safer code
5. Respond appropriately to security findings

## 🧠 Module 1: Understanding AI Code Vulnerabilities (30 min)

### The AI Hallucination Problem

AI models are pattern matchers, not logical reasoners. They:
- Generate plausible-looking code that may be fundamentally flawed
- Lack project-specific context (architecture, security policies)
- Often produce "happy path" code without error handling
- May suggest non-existent packages (slopsquatting risk)

### Exercise 1.1: Spot the AI Flaw

Review this AI-generated code and identify issues:

```python
# AI was asked: "Create a function to get user data from database"
def get_user_data(user_id):
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = cursor.execute(query).fetchone()
    return result
```

<details>
<summary>Answer</summary>

Issues found:
1. **SQL Injection**: String formatting in query
2. **Direct DB Connection**: Not using DatabaseManager
3. **No Error Handling**: What if connection fails?
4. **No Connection Cleanup**: Connection never closed
5. **No Input Validation**: user_id could be anything
6. **No Authentication Check**: Anyone can query any user

</details>

### Common AI Vulnerability Patterns

1. **Authentication Bypass**
   ```python
   # AI often forgets auth decorators
   @app.route('/admin/delete')
   def delete_user():  # Missing @require_auth!
   ```

2. **Hardcoded Secrets**
   ```python
   # AI learns from public code with bad practices
   API_KEY = "sk-1234567890"  # Never do this!
   ```

3. **Missing Validation**
   ```python
   # AI assumes inputs are always valid
   user_input = request.form['data']
   process_data(user_input)  # No sanitization!
   ```

## 🛡️ Module 2: AutoTaskTracker Security Tools (45 min)

### Tool Overview

| Tool | Purpose | When to Use |
|------|---------|-------------|
| Semgrep | AI-specific code patterns | Every commit |
| Bandit | General Python security | Every commit |
| Package Validator | Dependency safety | Adding packages |
| DAST Tester | Runtime security | Dashboard changes |

### Exercise 2.1: Run Your First Security Scan

```bash
# 1. Clone a branch with intentionally vulnerable code
git checkout training/security-exercise-1

# 2. Run Semgrep
semgrep --config=.semgrep.yml autotasktracker/training/

# 3. Interpret results
# How many findings? What severity? 

# 4. Fix one issue and re-run
# Did the finding disappear?
```

### Exercise 2.2: Validate a Suspicious Package

The AI suggests: "Install the `quick-json-parser` package"

```bash
# Check if it's legitimate
python scripts/security/package_validator.py --package quick-json-parser

# What's the risk score?
# What warnings appear?
# Would you install it?
```

### Tool Outputs Explained

**Semgrep Finding:**
```json
{
  "check_id": "missing-auth-on-streamlit-endpoints",
  "path": "dashboards/admin.py",
  "line": 42,
  "message": "Streamlit endpoint 'delete_all_data' lacks authentication"
}
```

**What it means:** Critical security flaw - anyone can delete data!

**Package Validator Output:**
```json
{
  "package_name": "json-quik-parser",
  "risk_score": 8.5,
  "warnings": [
    "Package age risk: 9/10",
    "Possible typosquatting: 8/10"
  ]
}
```

**What it means:** High risk - likely a malicious package!

## ✍️ Module 3: Secure Prompt Engineering (30 min)

### The Security-First Prompt Formula

```
[PERSONA] + [CONTEXT] + [SECURITY REQUIREMENTS] + [SPECIFIC CONSTRAINTS]
```

### Exercise 3.1: Improve This Prompt

**Poor Prompt:**
> "Create a user login function"

**Your Improved Version:**
```
[Write your secure prompt here]




```

<details>
<summary>Example Answer</summary>

**Secure Prompt:**
> "Act as a senior backend engineer with security expertise. Create a Flask 2.0 user login function that:
> 1. Validates email/password against SQL injection
> 2. Uses DatabaseManager for database access (not direct sqlite3)
> 3. Implements rate limiting (max 5 attempts per minute)
> 4. Hashes passwords with bcrypt
> 5. Returns appropriate HTTP status codes
> 6. Logs failed attempts with IP addresses
> 7. Never exposes internal error details
> Include comprehensive error handling and type hints."

</details>

### Prompt Security Checklist

Before sending a prompt, ensure it includes:
- [ ] Authentication/authorization requirements
- [ ] Input validation needs  
- [ ] Error handling expectations
- [ ] Logging requirements
- [ ] Project-specific patterns (DatabaseManager, etc.)

## 🔍 Module 4: Code Review for AI Code (30 min)

### The "AI as Junior Developer" Paradigm

Review AI code as you would a talented but inexperienced junior's code:
- Assume good intentions but lack of context
- Check for fundamental security mistakes
- Verify business logic understanding
- Ensure architectural compliance

### Exercise 4.1: Security Code Review

Review this AI-generated PR:

```python
# Feature: Add user search functionality
@app.route('/search')
def search_users():
    search_term = request.args.get('q')
    
    conn = get_db_connection()
    users = conn.execute(
        f"SELECT id, name, email FROM users WHERE name LIKE '%{search_term}%'"
    ).fetchall()
    
    return jsonify([dict(u) for u in users])
```

**Your Review Comments:**
1. _________________________________
2. _________________________________
3. _________________________________

<details>
<summary>Example Review</summary>

**Security Issues:**
1. 🔴 **SQL Injection**: Direct string interpolation in query
2. 🟡 **No Authentication**: Public endpoint exposes user data
3. 🟡 **Information Disclosure**: Returns email addresses to anyone
4. 🔴 **Direct DB Access**: Should use DatabaseManager
5. 🟡 **No Rate Limiting**: Vulnerable to enumeration attacks
6. 🟡 **No Input Validation**: What if search_term is None?

**Suggested Fix:**
```python
@app.route('/search')
@require_auth  # Add authentication
@rate_limit(calls=10, period=60)  # Add rate limiting
def search_users():
    search_term = request.args.get('q', '').strip()
    
    if not search_term or len(search_term) < 3:
        return jsonify({'error': 'Search term too short'}), 400
    
    db = DatabaseManager()
    with db.get_connection() as conn:
        users = conn.execute(
            "SELECT id, name FROM users WHERE name LIKE ?",
            (f'%{search_term}%',)
        ).fetchall()
    
    # Don't expose emails
    return jsonify([{'id': u['id'], 'name': u['name']} for u in users])
```

</details>

## 🚨 Module 5: Incident Response (15 min)

### When Security Tools Find Issues

**Severity Levels:**
- **🔴 Critical**: Block deployment (hardcoded secrets, SQL injection)
- **🟡 High**: Fix before merge (missing auth, XSS)
- **🔵 Medium**: Fix within sprint (missing validation)
- **⚪ Low**: Track in backlog (code style, complexity)

### Exercise 5.1: Triage Security Findings

Your CI pipeline reports:
```
CRITICAL: hardcoded-api-key at config.py:42
HIGH: missing-auth-on-streamlit-endpoints at dashboards/admin.py:15
MEDIUM: bare-except-clause at utils/helpers.py:78
LOW: function-complexity-too-high at ai/processor.py:234
```

**Your Action Plan:**
1. First: _________________________________
2. Then: _________________________________
3. Next Sprint: ___________________________
4. Backlog: ______________________________

## 📊 Module 6: Metrics and Continuous Improvement (15 min)

### Key Security Metrics

Track your team's progress:
- **False Positive Rate**: Are tools too noisy?
- **Time to Fix**: How quickly do we address findings?
- **AI Code Rejection Rate**: How often do we reject AI suggestions?
- **Security Debt**: Backlog of security issues

### Exercise 6.1: Generate Your Metrics

```bash
# Generate security report
python scripts/security/generate_metrics.py --format markdown

# Review the report
# What's your compliance score?
# What are the top recommendations?
```

## 🎯 Final Assessment

### Practical Exercise

You're tasked with adding a new feature using AI assistance:

**Requirement:** "Add an endpoint to export user activity logs as CSV"

1. Write a secure prompt for the AI
2. Review the generated code
3. Run security scans
4. Fix any issues found
5. Document your security decisions

### Assessment Criteria
- [ ] Prompt includes security requirements
- [ ] Code review identifies major issues
- [ ] Security scans pass
- [ ] Fixes maintain functionality
- [ ] Documentation explains decisions

## 🏆 Certification

Complete all exercises and the final assessment to earn your:
**AutoTaskTracker AI Security Practitioner** certification

## 📚 Additional Resources

### Internal
- [AI Code Security Quick Reference](../security/AI_CODE_SECURITY_QUICKREF.md)
- [Meta-Testing Implementation](../security/META_TESTING_IMPLEMENTATION.md)
- [Integration Guide](../security/INTEGRATION_GUIDE.md)

### External
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [GitHub Copilot Security Best Practices](https://docs.github.com/en/copilot/security)
- [AI Security Alliance Resources](https://aisecurityalliance.org)

## 🤝 Support

- **Slack:** #ai-security-help
- **Office Hours:** Wednesdays 2-3 PM
- **Security Champions:** See team directory

---

**Remember:** You are the security gate between AI suggestions and production code. With great power comes great responsibility!

*Training Version 1.0 | Last Updated: 2025-07-05*