# Meta-Testing Security Maintenance Playbook

## 🔧 Routine Maintenance Schedule

### Daily Tasks
- [ ] Monitor CI security scan results
- [ ] Review any blocked commits
- [ ] Check Slack for security questions

### Weekly Tasks
- [ ] Review security findings backlog
- [ ] Update package validator patterns if needed
- [ ] Run manual DAST scan on dashboards
- [ ] Generate security metrics report

### Monthly Tasks
- [ ] Full security tool version updates
- [ ] Review and tune Semgrep rules
- [ ] Analyze false positive rates
- [ ] Update security documentation
- [ ] Team security training session

### Quarterly Tasks
- [ ] Major security tool upgrades
- [ ] Comprehensive security audit
- [ ] Update threat model
- [ ] Review and update security policies

## 🚨 Common Issues and Solutions

### Issue: High False Positive Rate

**Symptoms:**
- Developers complaining about too many alerts
- Security findings being ignored
- Builds frequently blocked

**Solution:**
1. Review recent Semgrep findings:
   ```bash
   semgrep --config=.semgrep.yml autotasktracker/ --json > findings.json
   ```
2. Identify patterns causing false positives
3. Tune rules in `.semgrep.yml`:
   ```yaml
   pattern-not-inside:
     - pattern: |
         # Add exclusion patterns here
   ```
4. Test refined rules
5. Document changes

### Issue: Slow Security Scans

**Symptoms:**
- CI builds taking > 10 minutes
- Developer complaints about wait times

**Solution:**
1. Profile scan times:
   ```bash
   time semgrep --config=.semgrep.yml autotasktracker/
   time bandit -r autotasktracker/
   ```
2. Optimize configurations:
   - Reduce scan scope if appropriate
   - Use incremental scanning
   - Parallelize where possible
3. Consider caching strategies

### Issue: Package Validator False Alarms

**Symptoms:**
- Legitimate packages flagged as suspicious
- Developers bypassing checks

**Solution:**
1. Review flagged packages:
   ```bash
   python scripts/security/package_validator.py --package [name]
   ```
2. Update validator patterns if needed
3. Add to allowlist if appropriate
4. Document decision

### Issue: Security Tool Version Conflicts

**Symptoms:**
- Tool installation failures
- Incompatible Python versions
- CI failures after updates

**Solution:**
1. Check current versions:
   ```bash
   pip list | grep -E "semgrep|bandit|safety|pip-audit"
   ```
2. Test updates in isolated environment:
   ```bash
   python -m venv test-env
   source test-env/bin/activate
   pip install -r requirements.txt
   ```
3. Update requirements.txt with compatible versions
4. Test thoroughly before merging

## 📋 Maintenance Procedures

### Updating Semgrep Rules

1. **Identify Need:**
   - New AI vulnerability pattern discovered
   - False positive reduction needed
   - New AutoTaskTracker pattern to enforce

2. **Development Process:**
   ```bash
   # Create test file with vulnerability
   echo "vulnerable code" > test_vuln.py
   
   # Write rule in .semgrep.yml
   # Test rule
   semgrep --config=.semgrep.yml test_vuln.py
   
   # Verify no false positives
   semgrep --config=.semgrep.yml autotasktracker/
   ```

3. **Deployment:**
   - Commit rule changes
   - Update documentation
   - Notify team

### Adding New Security Tools

1. **Evaluation Criteria:**
   - Addresses gap in current coverage
   - Low false positive rate
   - Good CI/CD integration
   - Active maintenance

2. **Integration Steps:**
   ```bash
   # Add to requirements.txt
   echo "new-tool>=1.0.0" >> requirements.txt
   
   # Create configuration
   touch .new-tool-config
   
   # Update CI workflow
   # Update Makefile
   # Update health tests
   ```

3. **Rollout:**
   - Pilot with small team
   - Gather feedback
   - Tune configuration
   - Full deployment

### Security Metrics Analysis

1. **Generate Report:**
   ```bash
   python scripts/security/generate_metrics.py --format markdown
   ```

2. **Key Metrics to Track:**
   - Findings per KLOC trend
   - Time to remediation
   - False positive rate
   - Tool effectiveness

3. **Action Items:**
   - Identify concerning trends
   - Plan remediation sprints
   - Update training materials

## 🔄 Tool Update Procedures

### Semgrep Updates

```bash
# Check current version
semgrep --version

# Review changelog
# https://github.com/returntocorp/semgrep/releases

# Update
pip install --upgrade semgrep

# Test
make security-check

# Update requirements.txt
pip freeze | grep semgrep > requirements.txt
```

### Bandit Updates

```bash
# Similar process
pip install --upgrade bandit
bandit --version
# Test and update requirements.txt
```

### Package Validator Maintenance

1. **Update Suspicious Patterns:**
   ```python
   # In package_validator.py
   self.suspicious_patterns = [
       r'.*-?db$',  # Add new patterns
   ]
   ```

2. **Update Popular Packages List:**
   ```python
   popular_packages = [
       "requests", "numpy",  # Keep current
   ]
   ```

3. **Test Changes:**
   ```bash
   python scripts/security/package_validator.py --package test-pkg
   ```

## 🎯 Performance Optimization

### Scan Time Optimization

1. **Measure Baseline:**
   ```bash
   time make security-check
   ```

2. **Optimization Strategies:**
   - Use `.semgrepignore` for vendor code
   - Implement incremental scanning
   - Cache results where appropriate
   - Parallelize independent scans

3. **Incremental Scanning Setup:**
   ```bash
   # Only scan changed files
   git diff --name-only | grep '\.py$' | xargs semgrep --config=.semgrep.yml
   ```

### CI/CD Optimization

1. **Parallel Execution:**
   ```yaml
   # In .github/workflows/ci.yml
   strategy:
     matrix:
       tool: [semgrep, bandit, pip-audit]
   ```

2. **Caching:**
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.cache/semgrep
       key: ${{ runner.os }}-semgrep-${{ hashFiles('.semgrep.yml') }}
   ```

## 📊 Health Monitoring

### Weekly Health Check

```bash
# Run comprehensive health check
pytest tests/health/test_metatesting_security.py -v

# Check specific components
python -m pytest tests/health/test_metatesting_security.py::test_security_tools_installed
```

### Monthly Audit

1. **Tool Functionality:**
   ```bash
   for tool in semgrep bandit safety pip-audit; do
     echo "Testing $tool..."
     $tool --version
   done
   ```

2. **Configuration Validity:**
   ```bash
   # Validate configurations
   semgrep --validate .semgrep.yml
   python -c "import json; json.load(open('.safety-policy.json'))"
   ```

3. **Integration Testing:**
   ```bash
   # Test full pipeline
   make ci-local
   ```

## 🆘 Escalation Procedures

### Security Finding Escalation

1. **Critical Finding** (hardcoded secrets, SQL injection):
   - Immediate notification to team lead
   - Block deployment
   - Fix within 4 hours

2. **High Finding** (missing auth, XSS):
   - Create high-priority ticket
   - Fix before next release
   - Review similar code

3. **Medium/Low Finding**:
   - Add to backlog
   - Address in next sprint
   - Track trends

### Tool Failure Escalation

1. **CI Pipeline Blocked:**
   - Check tool logs
   - Attempt quick fix
   - If > 30 min, notify team
   - Consider temporary bypass

2. **Persistent False Positives:**
   - Document pattern
   - Create rule exception
   - Schedule rule review

## 📝 Documentation Updates

### When to Update Docs

- New security pattern discovered
- Tool configuration changed
- Process improved
- Common issue identified

### Documentation Checklist

- [ ] Update relevant `.md` files
- [ ] Update tool configurations
- [ ] Update CLAUDE.md if needed
- [ ] Notify team of changes

## 🔐 Security Incident Response

### Suspected Vulnerability in Production

1. **Immediate Actions:**
   ```bash
   # Verify vulnerability
   semgrep --config=security-critical-rules.yml production-code/
   
   # Check logs for exploitation
   grep -r "suspicious-pattern" logs/
   ```

2. **Containment:**
   - Disable affected feature if possible
   - Apply emergency patch
   - Monitor for exploitation

3. **Post-Incident:**
   - Root cause analysis
   - Update security rules
   - Team training on issue

---

**Emergency Contacts:**
- Security Team Lead: security-lead@company.com
- On-Call Security: +1-555-SECURE
- Incident Response: incident-response@company.com

*Playbook Version 1.0 | Last Updated: 2025-07-05*