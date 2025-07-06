# CLI Migration Guide

This guide helps migrate from individual scripts to the unified `autotask` CLI.

## Installation

After updating the code, install the CLI:

```bash
pip install -e .
```

This makes the `autotask` command available globally.

## Command Mappings

### AI Operations

| Old Command | New Command |
|-------------|-------------|
| `python scripts/ai/ai_cli.py status` | `autotask ai status` |
| `python scripts/ai/ai_cli.py setup` | `autotask ai setup` |
| `python scripts/generate_embeddings.py --limit 100` | `autotask ai embeddings --limit 100` |
| `python scripts/ai/vlm_manager.py enable` | `autotask ai vlm enable` |
| `python scripts/ai/vlm_manager.py disable` | `autotask ai vlm disable` |

### Processing Operations

| Old Command | New Command |
|-------------|-------------|
| `python scripts/processing/process_screenshots.py --batch` | `autotask process screenshots --batch` |
| `python scripts/processing/process_tasks.py --limit 50` | `autotask process tasks --limit 50` |
| `python scripts/processing/process_sessions.py` | `autotask process sessions` |
| `python scripts/start_auto_processor.py start` | `autotask process auto` |
| `python scripts/start_auto_processor.py stop` | `autotask process stop` |

### Dashboard Management

| Old Command | New Command |
|-------------|-------------|
| `python autotasktracker.py dashboard` | `autotask dashboard start --type task` |
| `python autotasktracker.py analytics` | `autotask dashboard start --type analytics` |
| `python autotasktracker.py timetracker` | `autotask dashboard start --type time` |
| `python autotasktracker.py start` | `autotask dashboard start --type all` |
| `python autotasktracker.py launcher` | `autotask dashboard launcher` |

### System Checks

| Old Command | New Command |
|-------------|-------------|
| `python scripts/pensieve_health_check.py` | `autotask check health` |
| `python scripts/analysis/compliance_scanner.py` | `autotask check compliance` |
| `python scripts/analysis/production_readiness.py` | `autotask check production` |
| `python scripts/final_integrity_check.py` | `autotask check integrity` |

### Analysis Tools

| Old Command | New Command |
|-------------|-------------|
| `python scripts/analysis/ai_pipeline_comparison.py` | `autotask analyze pipeline` |
| `python scripts/analysis/performance_baseline.py` | `autotask analyze performance` |
| `python scripts/utils/analyze_codebase.py` | `autotask analyze code` |

## Common Options

The unified CLI supports global options:

```bash
# Verbose output
autotask --verbose ai status

# Quiet mode
autotask --quiet process screenshots

# Show version
autotask version

# Show configuration
autotask config
```

## Benefits

1. **Discoverability**: Use `autotask --help` to see all available commands
2. **Consistency**: All commands follow the same pattern
3. **Tab Completion**: Install shell completion for easier use
4. **Unified Configuration**: Global options apply to all subcommands
5. **Better Error Handling**: Consistent error messages and exit codes

## Shell Completion

Enable tab completion for your shell:

```bash
# Bash
eval "$(_AUTOTASK_COMPLETE=bash_source autotask)"

# Zsh
eval "$(_AUTOTASK_COMPLETE=zsh_source autotask)"

# Fish
eval (env _AUTOTASK_COMPLETE=fish_source autotask)
```

Add the appropriate line to your shell's configuration file (`.bashrc`, `.zshrc`, etc.).