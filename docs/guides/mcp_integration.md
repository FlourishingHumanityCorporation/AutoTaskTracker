# MCP (Multi-Claude Protocol) Integration

MCP extends Claude's capabilities by connecting to external tools and services. This enables AutoTaskTracker to integrate with databases, monitoring services, web browsers, and other AI agents.

## MCP Configuration

### Project-Level MCP Setup

Create `.mcp.json` in the repository root:

```json
{
  "mcpServers": {
    "database": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sqlite", "--db-path", "~/.memos/database.db"],
      "env": {
        "NODE_ENV": "production"
      }
    },
    "browser": {
      "command": "npx", 
      "args": ["@modelcontextprotocol/server-puppeteer"],
      "env": {}
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "--allowed-dirs", ".", "docs", "scripts"],
      "env": {}
    }
  }
}
```

### Global MCP Configuration

For user-wide MCP servers, configure in `~/.claude/mcp_servers.json`:

```json
{
  "mcpServers": {
    "sentry": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sentry"],
      "env": {
        "SENTRY_DSN": "your-sentry-dsn"
      }
    }
  }
}
```

## AutoTaskTracker-Specific MCP Integrations

### Database MCP Server

**Purpose**: Allow Claude to query the AutoTaskTracker database directly

**Setup**:
```bash
# Install SQLite MCP server
npm install -g @modelcontextprotocol/server-sqlite

# Test connection
claude mcp serve database
```

**Usage Examples**:
- "Show me the last 10 screenshots processed"
- "Count tasks extracted in the last week"
- "Find screenshots containing 'meeting' in the OCR text"

### Pensieve Health MCP Server

Create custom MCP server for Pensieve monitoring:

```python
# scripts/mcp/pensieve_health_server.py
#!/usr/bin/env python3
"""
Custom MCP server for Pensieve health monitoring.
"""
import asyncio
import json
from mcp import Server, types
from autotasktracker.pensieve.health_monitor import get_health_status

app = Server("pensieve-health")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="check_pensieve_health",
            description="Check Pensieve service health status",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_processing_stats", 
            description="Get AutoTaskTracker processing statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 7}
                },
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "check_pensieve_health":
        health = get_health_status()
        return [types.TextContent(type="text", text=json.dumps(health, indent=2))]
    
    elif name == "get_processing_stats":
        days = arguments.get("days", 7)
        # Implementation here
        stats = {"processed": 150, "errors": 2, "days": days}
        return [types.TextContent(type="text", text=json.dumps(stats, indent=2))]
    
    raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    asyncio.run(app.run())
```

### Browser Automation MCP

**Purpose**: Automate dashboard testing and screenshot analysis

**Setup**:
```bash
npm install -g @modelcontextprotocol/server-puppeteer
```

**Usage Examples**:
- "Open the task board dashboard and take a screenshot"
- "Test all dashboard links are working"
- "Analyze dashboard performance metrics"

## MCP Troubleshooting

### Common Issues

**MCP Server Not Connecting**:
```bash
# Start MCP server manually for debugging
claude mcp serve database

# Check if server is responding
curl -X POST http://localhost:8080/health
```

**Finicky Connections**:
- Restart Claude Code: `claude auth logout && claude auth login`
- Clear MCP cache: Remove `~/.claude/mcp_cache/`
- Re-issue commands until connection establishes
- Check firewall/network restrictions

**Performance Issues**:
- Limit MCP server resources in configuration
- Use connection pooling for database servers
- Monitor MCP server memory usage

### Debugging MCP Integration

```bash
# Enable MCP debugging
export CLAUDE_MCP_DEBUG=1

# Check MCP server logs
tail -f ~/.claude/mcp_logs/database.log

# Test MCP server directly
claude mcp test database "SELECT COUNT(*) FROM entities"
```

## Advanced MCP Patterns

### Multi-Agent Collaboration

Configure MCP to enable collaboration between Claude instances:

```json
{
  "mcpServers": {
    "collaboration": {
      "command": "python",
      "args": ["scripts/mcp/multi_agent_server.py"],
      "env": {
        "AGENT_ROLE": "autotasktracker-primary"
      }
    }
  }
}
```

### Custom AutoTaskTracker Tools

Create project-specific MCP tools:

```python
# Custom tool for pipeline comparison
@app.call_tool()
async def compare_pipelines(arguments: dict):
    pipeline1 = arguments.get("pipeline1", "basic")
    pipeline2 = arguments.get("pipeline2", "ai_full")
    
    # Run comparison analysis
    from autotasktracker.comparison.analysis.performance_analyzer import compare
    results = compare(pipeline1, pipeline2)
    
    return [types.TextContent(
        type="text", 
        text=f"Pipeline Comparison:\n{json.dumps(results, indent=2)}"
    )]
```

## Security Considerations

### MCP Permissions

- **Restricted file access**: Limit filesystem MCP to necessary directories
- **Database permissions**: Use read-only database connections where possible
- **Environment isolation**: Don't expose sensitive environment variables
- **Network restrictions**: Limit MCP server network access

### Configuration Security

```json
{
  "mcpServers": {
    "secure-database": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sqlite", "--read-only", "--db-path", "~/.memos/database.db"],
      "allowedOperations": ["SELECT", "EXPLAIN"],
      "env": {}
    }
  }
}
```

## Integration with AutoTaskTracker Workflows

### Automated Processing with MCP

```bash
# Use MCP to trigger processing pipeline
claude mcp call pensieve-health "check_health" && \
claude mcp call database "SELECT COUNT(*) FROM entities WHERE processed = 0" && \
python scripts/processing/auto_processor.py
```

### Dashboard Monitoring

```bash
# Use browser MCP for dashboard health checks
claude mcp call browser "goto('http://localhost:8502')" && \
claude mcp call browser "screenshot('dashboard-health.png')"
```

### Performance Analytics

```bash
# Use custom MCP tools for performance analysis
claude mcp call pensieve-health "get_processing_stats" --days 30
```

This MCP integration enables Claude to directly interact with AutoTaskTracker's infrastructure, providing powerful automation and monitoring capabilities.