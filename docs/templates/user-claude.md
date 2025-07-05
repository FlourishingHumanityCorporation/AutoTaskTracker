# Personal Claude Code Configuration

**Template for `~/.claude/CLAUDE.md` - Personal preferences across all projects**

Copy this template to `~/.claude/CLAUDE.md` and customize for your personal workflow preferences.

---

## 🔧 PERSONAL PREFERENCES

### Commit Message Style
```bash
# My preferred commit format (if different from project standards)
# Example: Use emoji prefixes
# 🚀 feat(scope): description
# 🐛 fix(scope): description  
# 📚 docs(scope): description
```

### Code Style Preferences
```python
# Personal Python style preferences
# - Prefer f-strings over .format()
# - Always use type hints
# - Prefer explicit imports over star imports
# - Use descriptive variable names even if longer
```

### Development Workflow
- **Testing approach**: Prefer TDD when possible
- **Documentation**: Update docs with every feature
- **Refactoring**: Refactor before adding new features
- **Error handling**: Always use specific exception types

## 🛠️ CUSTOM TOOL SHORTCUTS

### Quick Commands
```bash
# Personal shortcuts for common tasks
# test: Run my preferred test suite
# lint: My linting setup
# deploy: My deployment process
```

### Analysis Preferences
- **Code review focus**: Security, performance, maintainability
- **Complexity tolerance**: Prefer simpler solutions even if slightly less efficient
- **Documentation style**: Include examples in all docstrings

## 📝 PROMPT TEMPLATES

### Code Review Template
```
Please review this code focusing on:
1. Security implications
2. Performance bottlenecks  
3. Maintainability concerns
4. Test coverage adequacy
5. Documentation completeness

Provide specific, actionable feedback.
```

### Debugging Template
```
Help me debug this issue:
1. Analyze the error message and stack trace
2. Identify the most likely root causes
3. Suggest debugging steps in order of likelihood
4. Provide prevention strategies for the future
```

### Architecture Review Template
```
Review this architectural decision:
1. Evaluate pros and cons
2. Consider alternatives
3. Assess long-term maintainability
4. Identify potential scaling issues
5. Suggest improvements
```

## 🎯 PROJECT-AGNOSTIC RULES

### Code Quality Standards
- **Function length**: Max 20 lines preferred
- **Class size**: Max 200 lines preferred  
- **Nesting depth**: Max 3 levels preferred
- **Parameter count**: Max 5 parameters preferred

### Documentation Standards
- **README updates**: Always update README with new features
- **API documentation**: Document all public methods
- **Change notes**: Include rationale for architectural decisions
- **Examples**: Provide usage examples for complex features

### Security Practices
- **Dependency management**: Regularly update dependencies
- **Secret handling**: Never commit secrets, use environment variables
- **Input validation**: Validate all external inputs
- **Error information**: Don't expose sensitive data in error messages

## 🚀 PRODUCTIVITY ENHANCEMENTS

### Development Preferences
- **IDE setup**: VS Code with Python, GitLens, and Pylance extensions
- **Terminal**: Prefer detailed error messages and stack traces
- **Git workflow**: Feature branches with descriptive names
- **Testing**: Run tests automatically before commits

### Personal Automation
```bash
# Custom aliases and functions I use
alias pytest-watch="pytest --watchman"
alias git-clean="git branch --merged | grep -v master | xargs git branch -d"
alias complexity-check="radon cc . -a -nc"
```

### Learning Preferences
- **New technologies**: Provide explanations with examples
- **Code patterns**: Show both the pattern and its alternatives
- **Best practices**: Explain the reasoning behind recommendations
- **Trade-offs**: Always explain trade-offs in technical decisions

## 🔍 DEBUGGING APPROACH

### Problem-Solving Process
1. **Reproduce** the issue consistently
2. **Isolate** the problem to smallest possible scope
3. **Hypothesize** about root causes
4. **Test** hypotheses systematically
5. **Document** the solution and prevention

### Error Handling Philosophy
- **Fail fast**: Catch errors as early as possible
- **Fail clearly**: Provide specific, actionable error messages
- **Fail safely**: Ensure system remains in consistent state
- **Log meaningfully**: Include context needed for debugging

## 📊 PERSONAL METRICS

### Code Quality Tracking
- **Bugs per feature**: Track defect rate in my code
- **Code review feedback**: Monitor common review comments
- **Test coverage**: Maintain >90% coverage on my contributions
- **Documentation completeness**: Ensure all public APIs documented

### Learning Goals
- **New patterns**: Learn one new design pattern per month
- **Technology exploration**: Try one new tool/library per quarter
- **Best practices**: Read one architecture/engineering book per quarter
- **Community contribution**: Contribute to open source monthly

---

## 💡 USAGE NOTES

**Activation**: This file is automatically loaded for all Claude Code sessions on this machine.

**Precedence**: Project-specific CLAUDE.md files override these settings when working on specific projects.

**Updates**: Review and update this file quarterly to reflect evolving preferences and learnings.

**Sharing**: This file is personal - don't commit to project repositories.

**Backup**: Keep a backup copy since this affects all Claude Code interactions.