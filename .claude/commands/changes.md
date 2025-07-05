# Save Task Block Changes to CLAUDE.md

Summarize the current task block's work, distill key changes into concise bullet points, and append them under a dated heading in CLAUDE.md.

## Instructions for Claude:

1. **Analyze Current Task Block**: Review the conversation history and identify:
   - Major code changes made
   - New features implemented  
   - Bug fixes applied
   - Documentation updates
   - Configuration changes

2. **Create Summary**: Generate 3-5 concise bullet points describing the most important changes:
   - Focus on "what" was changed, not "how"
   - Use past tense and technical language
   - Avoid superlatives, progress percentages, or announcement-style language
   - NO "successfully implemented", "85% complete", "amazing results"
   - Include file paths where relevant
   - Document concrete changes, not subjective assessments

3. **Update CLAUDE.md**: Append to the "Recent Changes" section:
   ```markdown
   **YYYY-MM-DD: [Brief Session Description]**
   - [Change 1 with file reference]
   - [Change 2 with file reference]
   - [Change 3 with file reference]
   ```

4. **Tag Conflicts**: If new information conflicts with existing CLAUDE.md content:
   - Mark older information as `#Deprecated` 
   - Do not delete deprecated information
   - Preserve historical record

5. **Commit Changes**: After updating CLAUDE.md, commit the changes with message:
   `docs(claude): update session changes and deprecated conflicting info`

This command implements the community best practice of consolidating task block memory into persistent documentation.