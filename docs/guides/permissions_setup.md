# Claude Code Permissions Setup

Team-shared permissions configuration for consistent Claude Code behavior across the project.

## Permissions Configuration

The project includes a shared `.claude/settings.json` file that defines team-wide permissions for Claude Code operations.

### Enabled Permissions

**File Operations:**
- `Edit: true` - Allow file editing without prompts
- `Write: true` - Allow file creation without prompts

**Safe Commands:**
- `Bash(git *)` - All git operations (commit, push, pull, etc.)
- `Bash(pytest *)` - All pytest test execution
- `Bash(python scripts/*)` - AutoTaskTracker scripts execution
- `Bash(memos *)` - Pensieve/memos service operations

**Restricted Commands:**
- `Bash(npm *)` - Package installations require confirmation
- `Bash(pip install *)` - Python package installations require confirmation  
- `Bash(rm -rf *)` - Destructive operations require confirmation

### Project-Specific Settings

**Quality Gates:**
- `healthCheckBeforeCommit: true` - Run health checks before commits
- `requireTestsForFeatures: true` - Require tests for new features
- `conventionalCommits: true` - Enforce conventional commit format

**Context Management:**
- `autoCompact: true` - Automatically compact context when needed
- `maxContextLines: 10000` - Limit context window size

## Setup Instructions

### Individual Developer Setup

1. **Copy team settings** (if not automatically loaded):
   ```bash
   cp .claude/settings.json ~/.claude/autotasktracker-settings.json
   ```

2. **Apply permissions**:
   ```bash
   claude permissions import .claude/settings.json
   ```

3. **Verify permissions**:
   ```bash
   claude permissions list
   ```

### Team Consistency

The `.claude/settings.json` file is committed to the repository to ensure all team members use consistent permissions. This prevents:

- Inconsistent prompting behavior between developers
- Accidental dangerous operations
- Different safety levels across the team

### Custom Permissions

Developers can override team settings locally if needed:

```bash
# Add personal permission (not committed)
claude permissions add "Bash(custom-command)"

# Remove team permission locally
claude permissions remove "Bash(git push)"
```

## Permission Categories

### Development Workflow
- **Safe operations**: File edits, git operations, testing
- **Project scripts**: AutoTaskTracker-specific scripts
- **Service management**: Pensieve/memos operations

### Restricted Operations
- **Package management**: Requires explicit confirmation
- **System modifications**: Require manual approval
- **Destructive operations**: Always prompt for confirmation

### Emergency Override

In case of issues with permissions:

```bash
# Reset all permissions
claude permissions reset

# Disable all permissions temporarily
claude permissions set-mode prompt-all

# Re-import team settings
claude permissions import .claude/settings.json
```

## Integration with Workflows

### Automated Testing
The permissions enable Claude to run health checks and tests without prompting:

```bash
# These run without prompts due to permissions
pytest tests/health/ -v
python scripts/pensieve_health_check.py
git commit -m "fix: resolve database connection issue"
```

### Safety Boundaries
Dangerous operations still require confirmation:

```bash
# These will prompt for confirmation
pip install new-package
rm -rf important-directory/
npm install --global risky-package
```

This permissions setup balances productivity with safety, enabling smooth Claude Code workflows while protecting against dangerous operations.