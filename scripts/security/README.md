# AutoTaskTracker Security Tools

This directory contains security tools implementing meta-testing best practices for AI-generated code protection.

## 🎯 Overview

AutoTaskTracker implements a multi-layered security approach following the meta-testing framework from `docs/meta/bestpractices_metatest.md`. This addresses the unique vulnerabilities introduced by AI-generated code through:

- **Static Analysis (SAST)**: AI-specific Semgrep rules + Bandit security scanning
- **Supply Chain Analysis (SCA)**: Package legitimacy validation + dependency vulnerability scanning  
- **Dynamic Analysis (DAST)**: Basic runtime security testing for Streamlit dashboards
- **Human Review**: Enhanced code review processes for AI-generated code

## 🛠️ Tools

### 1. Package Validator (`package_validator.py`)
Protects against slopsquatting attacks by validating package legitimacy.

```bash
# Validate a single package
python scripts/security/package_validator.py --package some-package-name

# Validate all packages in requirements.txt
python scripts/security/package_validator.py --requirements requirements.txt

# Fail CI on suspicious packages
python scripts/security/package_validator.py --requirements requirements.txt --fail-on-suspicious
```

**Features:**
- Age and download count analysis
- Maintainer reputation checks
- Suspicious naming pattern detection
- Typosquatting similarity analysis
- Caching for performance

### 2. Dashboard Security Tester (`dashboard_security_tester.py`)
Basic DAST testing for AutoTaskTracker's Streamlit dashboards.

```bash
# Test all dashboards
python scripts/security/dashboard_security_tester.py --all

# Test specific dashboard
python scripts/security/dashboard_security_tester.py --port 8502

# Generate JSON report
python scripts/security/dashboard_security_tester.py --all --output security-report.json
```

**Tests:**
- XSS vulnerability detection
- Directory traversal attempts
- Information disclosure checks
- Security header validation
- HTTP method testing

### 3. Pre-Install Hook (`pre_install_hook.py`)
Git hook to validate packages before installation.

```bash
# Add to .git/hooks/pre-commit
python scripts/security/pre_install_hook.py --requirements requirements.txt --strict
```

## 📋 Configuration Files

### `.semgrep.yml`
AI-specific security rules targeting common patterns in AI-generated code:

- Missing authentication on Streamlit endpoints
- Database queries without validation
- Hardcoded credentials and API keys
- Unsafe file operations and eval/exec usage
- AutoTaskTracker architectural pattern violations

### `.bandit`
Bandit configuration focused on AI code vulnerability patterns:

- Comprehensive test coverage for security issues
- JSON output for CI integration
- Exclusions for test files and known safe patterns

### `.safety-policy.json`
Safety dependency scanner configuration:

- CVSS severity thresholds
- Vulnerability ignore lists
- JSON output formatting

## 🚀 CI Integration

Security tools are integrated into GitHub Actions workflow (`.github/workflows/ci.yml`):

```yaml
- name: Run Semgrep AI-specific security scan
- name: Run Bandit security scan  
- name: Run Safety dependency scan
- name: Run pip-audit dependency scan
- name: Validate package legitimacy
```

Reports are uploaded as CI artifacts for review.

## 🎯 Risk-Based Testing Approach

AutoTaskTracker follows the **"Workshop" configuration** from meta-testing best practices:

- **Risk Profile**: Internal tool with non-sensitive data (Low-Medium risk)
- **SAST**: Monitor/comment mode with AI-specific rules
- **SCA**: Standard scanning with slopsquatting protection
- **DAST**: Optional but recommended for dashboard APIs
- **Review**: Standard peer review with AI code awareness

## 📊 Compliance Monitoring

Run the meta-testing compliance health check:

```bash
pytest tests/health/test_metatesting_security.py -v
```

This validates:
- ✅ Security tools properly installed and configured
- ✅ AI-specific rules implemented
- ✅ Package validation operational
- ✅ DAST capabilities available
- ✅ CI integration complete

**Target**: ≥80% compliance score for AutoTaskTracker's risk profile

## 🔧 Usage Examples

### Daily Development Workflow

```bash
# Before adding new dependencies
python scripts/security/pre_install_hook.py --package new-package-name

# Before committing code with AI assistance
semgrep --config=.semgrep.yml autotasktracker/ --quiet

# Periodic dashboard security check
python scripts/security/dashboard_security_tester.py --all
```

### CI/CD Integration

```bash
# Full security validation (as run in CI)
semgrep --config=.semgrep.yml autotasktracker/ --json --output=semgrep-report.json
bandit --configfile .bandit -r autotasktracker/
safety check --policy-file .safety-policy.json
pip-audit --format=json --output=pip-audit-report.json
python scripts/security/package_validator.py --requirements requirements.txt --fail-on-suspicious
```

## 📚 Best Practices

### For AI-Generated Code Review

1. **Treat AI as Junior Developer**: Apply same scrutiny as reviewing junior developer code
2. **Focus on Context**: AI lacks project-specific context - verify architectural alignment  
3. **Security First**: Always check for missing authentication, input validation, error handling
4. **Dependency Validation**: Never trust AI package suggestions without validation

### For Security Tool Configuration

1. **Customize Rules**: Default tool configurations miss AI-specific patterns
2. **Monitor False Positives**: Tune rules to reduce noise while maintaining coverage
3. **Regular Updates**: Keep security tool rulesets current with emerging AI vulnerabilities
4. **Document Exceptions**: When disabling rules, document why with ticket references

## 🔗 References

- [Meta-Testing Best Practices](../../docs/meta/bestpractices_metatest.md)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [AutoTaskTracker Workflow Patterns](../../docs/guides/workflow_patterns.md)
- [AutoTaskTracker Code Style Guide](../../docs/guides/code_style.md)