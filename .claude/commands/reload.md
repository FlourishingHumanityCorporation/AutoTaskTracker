# Reload Clean Context from CLAUDE.md

Clear the interactive context and reload essential instructions from persistent memory.

## Instructions for Claude:

1. **Clear Context**: Use `/clear` or `/compact` to remove cluttered conversation history

2. **Reload CLAUDE.md**: Read the entire contents of `./CLAUDE.md` and treat it as fresh system-level context

3. **Load Documentation**: Process all files referenced via @ imports:
   - @docs/architecture/pensieve_integration.md
   - @docs/guides/testing_guide.md  
   - @docs/guides/code_style.md
   - @docs/guides/common_issues.md

4. **Confirm Ready**: Respond with a brief confirmation that context has been reloaded and you're ready for the next task

5. **Apply Fresh Context**: Use the reloaded context for all subsequent interactions in this session

This command implements the community best practice of managing context degradation by consolidating volatile chat history into persistent long-term memory stored in CLAUDE.md and supporting documentation files.

The workflow enables:
- Clean separation of short-term (chat) vs long-term (file) memory
- Prevention of context window bloat and performance degradation  
- Consistent behavior across sessions through persistent instructions
- Efficient token usage by loading only essential context