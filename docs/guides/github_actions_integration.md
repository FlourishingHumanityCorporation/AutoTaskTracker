# GitHub Actions Integration

Integrate Claude Code directly into AutoTaskTracker's CI/CD pipeline for automated development workflows.

## Overview

Anthropic provides official GitHub Actions that enable Claude to:
- Create pull requests from issue descriptions (`@claude implement`)
- Fix bugs automatically (`@claude fix`)
- Conduct automated code reviews
- Run health checks and generate reports

## Setup Requirements

### 1. Install GitHub App

1. Go to the [Claude Code GitHub App](https://github.com/apps/claude-code)
2. Install the app on your repository
3. Grant necessary permissions:
   - Read repository contents
   - Write pull requests and issues
   - Run Actions workflows

### 2. Configure Repository Secrets

Add the following secrets to your repository settings:

```bash
# Required secrets
ANTHROPIC_API_KEY=your-anthropic-api-key
CLAUDE_APP_ID=your-github-app-id
CLAUDE_APP_PRIVATE_KEY=your-github-app-private-key
```

### 3. Workflow Configuration

Create `.github/workflows/claude-integration.yml`:

```yaml
name: Claude Code Integration

on:
  issues:
    types: [opened, edited]
  issue_comment:
    types: [created]
  pull_request:
    types: [opened, synchronize]

jobs:
  claude-automation:
    runs-on: ubuntu-latest
    if: contains(github.event.comment.body, '@claude') || contains(github.event.issue.body, '@claude')
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        fetch-depth: 0

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .

    - name: Claude Code Action
      uses: anthropics/claude-code-action@v1
      with:
        anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
        github-token: ${{ secrets.GITHUB_TOKEN }}
        app-id: ${{ secrets.CLAUDE_APP_ID }}
        private-key: ${{ secrets.CLAUDE_APP_PRIVATE_KEY }}
        respect-claude-md: true
```

## AutoTaskTracker-Specific Workflows

### Automated Feature Implementation

**Issue Template** (`.github/ISSUE_TEMPLATE/feature_request.md`):

```markdown
---
name: Feature Request
about: Request a new feature for AutoTaskTracker
title: '[FEATURE] '
labels: enhancement
---

## Feature Description
Brief description of the requested feature.

## Implementation Requirements
- [ ] Pensieve integration considerations
- [ ] AI processing requirements
- [ ] Dashboard updates needed
- [ ] Testing requirements

## Acceptance Criteria
- [ ] Feature works with Pensieve API
- [ ] Graceful fallbacks implemented
- [ ] Health tests pass
- [ ] Documentation updated

## Claude Implementation
@claude implement this feature following AutoTaskTracker patterns
```

### Automated Bug Fixes

**Bug Report Template** (`.github/ISSUE_TEMPLATE/bug_report.md`):

```markdown
---
name: Bug Report
about: Report a bug in AutoTaskTracker
title: '[BUG] '
labels: bug
---

## Bug Description
Description of the bug and expected behavior.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Environment
- Python version:
- Pensieve version:
- AutoTaskTracker version:

## Logs
```
Relevant log output
```

## Claude Fix
@claude fix this bug ensuring all health tests pass
```

### Health Check Automation

Create `.github/workflows/health-checks.yml`:

```yaml
name: AutoTaskTracker Health Checks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  health-check:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -e .
    
    - name: Run Health Tests
      run: |
        pytest tests/health/ -v --tb=short
        
    - name: Claude Health Analysis
      uses: anthropics/claude-code-action@v1
      with:
        anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
        github-token: ${{ secrets.GITHUB_TOKEN }}
        command: "analyze-health-results"
        context: "AutoTaskTracker health check results"
      if: failure()
```

## Claude Commands for Issues

### Implementation Commands

```bash
# Implement new feature
@claude implement this feature following AutoTaskTracker patterns in the AI module

# Fix bug with context
@claude fix this database connection issue, ensure DatabaseManager usage

# Add tests
@claude add comprehensive tests for the VLM processing pipeline

# Update documentation
@claude update docs to reflect the new Pensieve integration changes
```

### Review Commands

```bash
# Code review
@claude review this PR for AutoTaskTracker best practices

# Security review
@claude security-review focusing on AI model safety and data privacy

# Performance review
@claude performance-review this dashboard implementation
```

## Advanced Automation Patterns

### Automated Plan Generation

Create workflow that generates implementation plans:

```yaml
- name: Generate Implementation Plan
  uses: anthropics/claude-code-action@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    command: |
      Use the /new-feature command to generate a detailed implementation plan
      for this issue. Create a plan.md file in the repository.
```

### Automated Testing

```yaml
- name: Claude Test Generation
  uses: anthropics/claude-code-action@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    command: |
      Generate comprehensive tests for the changes in this PR.
      Include unit tests, integration tests, and health tests.
      Follow AutoTaskTracker testing patterns.
```

### Pensieve Integration Validation

```yaml
- name: Validate Pensieve Integration
  uses: anthropics/claude-code-action@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    command: |
      Validate that this PR maintains proper Pensieve integration:
      - Uses DatabaseManager instead of direct sqlite3
      - Implements graceful API fallbacks
      - Follows Pensieve-first patterns
      Report any violations found.
```

## Integration with CLAUDE.md

Claude respects the project's CLAUDE.md file when running in GitHub Actions. This ensures:

- Consistent code style enforcement
- Proper architectural patterns
- AutoTaskTracker-specific rules and guidelines
- Testing requirements compliance

## Security Considerations

### Secret Management
- Use GitHub repository secrets for sensitive data
- Rotate API keys regularly
- Limit GitHub App permissions to minimum required

### Permission Scope
```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write
  actions: read
```

### Code Review Requirements
- Require manual review for security-sensitive changes
- Automatic approval only for documentation and test updates
- Human oversight for architecture changes

## Monitoring and Analytics

### Track Claude Usage
```yaml
- name: Log Claude Usage
  run: |
    echo "Claude action completed at $(date)" >> .github/claude-usage.log
    git add .github/claude-usage.log
    git commit -m "chore: log Claude usage" || true
```

### Performance Metrics
```yaml
- name: Report Performance Impact
  uses: anthropics/claude-code-action@v1
  with:
    command: |
      Analyze the performance impact of changes in this PR.
      Compare before/after metrics for:
      - Health test execution time
      - Dashboard loading performance
      - AI processing speed
```

This GitHub Actions integration enables fully automated development workflows while maintaining AutoTaskTracker's quality standards and architectural patterns.