# Common Issues & Troubleshooting

## Port Conflicts
- Memos: 8839
- Task Board: 8502
- Analytics: 8503
- Time Tracker: 8505

## Database Issues
- Path: `~/.memos/database.db` (NOT `memos.db`)
- Always use DatabaseManager for connections
- Check permissions if connection fails

## Pensieve/Memos Screenshot Capture Issues
**CRITICAL**: Pensieve is installed in `venv/` environment, NOT `anaconda3/`
```bash
# ✅ CORRECT commands (use venv Python):
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands ps
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands start
/Users/paulrohde/CodeProjects/AutoTaskTracker/venv/bin/python -m memos.commands stop

# ❌ WRONG: Don't try to install pensieve in anaconda3 (dependency conflicts)
```

## AI Features Not Working
1. Run `python scripts/ai/ai_cli.py status`
2. Install sentence-transformers: `pip install sentence-transformers`
3. Check Pensieve health: `python scripts/pensieve_health_check.py`

## Import Errors
- Scripts need parent directory in sys.path
- Dashboards gracefully degrade if AI modules missing
- Check virtual environment is activated

## Module Organization Best Practices
- Check existing structure before creating files
- Use proper imports: `from autotasktracker.module import Class`
- Consolidate related functionality (e.g., all VLM code in ai/)
- Update all references when moving files

## Import Patterns
```python
# ✅ CORRECT - From within package
from autotasktracker.core.database import DatabaseManager

# ✅ CORRECT - From scripts/
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autotasktracker.core.database import DatabaseManager

# ❌ WRONG - Relative imports
from ..core.database import DatabaseManager
```

## Claude Code Permissions Configuration

**Streamline workflows by configuring permissions:**
```bash
# Grant standing approval for file edits
/permissions add Edit

# Allow git commit commands without prompts
/permissions add "Bash(git commit:*)"

# Allow specific test commands
/permissions add "Bash(pytest:*)"
```

**Settings file:** `.claude/settings.json` (can be committed for team consistency)

**MCP Integration Issues:**
- MCP servers can be unstable
- Try running `claude mcp serve` in separate terminal
- Re-issue prompts until connection establishes