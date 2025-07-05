# Workflow Patterns & Best Practices

## TDD Counter-Hallucination Pattern

**Problem:** AI generates over-engineered code, hallucinates functions, or reinvents existing logic  
**Solution:** Test-Driven Development provides concrete, verifiable targets

**Workflow:**
1. **Write Tests First**: "We are doing TDD. Write tests for this feature. These tests should fail initially."
2. **Confirm Failure**: Run tests and verify they fail as expected
3. **Commit Tests**: Lock in requirements before implementation
4. **Write Code**: Implement only what makes tests pass. Do not modify test files.
5. **Commit Code**: Final implementation when all tests pass

**Why it works:** Forces AI to use existing structures and prevents scope drift

## Foundational Workflow (Explore → Plan → Code → Commit)

**For new features or bug fixes:**
1. **Explore**: Read relevant files, gather context. Do NOT write code yet.
2. **Plan**: Create detailed, step-by-step implementation plan  
3. **Code**: Execute the approved plan
4. **Commit**: Commit with descriptive message, create PR if needed

## Complexity Management

**Complexity Threshold:** Large, complex tasks cause AI to produce low-quality code

**Solutions:**
- **Decompose Problems**: Break complex tasks into smaller sub-problems
- **Fresh Sessions**: Run sub-tasks in clean sessions with minimal context
- **Complexity Budgeting**: Consider the "cost" of changes to codebase complexity

**Example Prompt:**
```
Current complexity score: 25. This change adds 5 complexity points. 
Is this worth it? How could we refactor to stay under budget?
```

## Context Management

**Problem:** Long sessions cause performance degradation and hallucinations

**Solutions:**
- **Clear Context Often**: Use `/clear` or `/compact` between major tasks
- **Use `/reload`**: Reload fresh context from CLAUDE.md
- **Persistent Memory**: Store important context in files, not chat history

## Plan-Driven Execution

**For medium-to-large features:**
1. **Generate Plan**: Create detailed implementation plan in `plan.md`
2. **Execute Task**: "Open @plan.md, identify next incomplete task, implement it"
3. **Update and Commit**: Commit changes, mark task complete in plan
4. **Pause and Review**: Wait for user feedback after each task

## Anti-Patterns to Avoid

**"Code Vomit":**
- Symptom: 1,000 lines for a 5-line task
- Cause: Incomplete context, AI avoiding existing code
- Solution: Use TDD, explicit prompts, strengthen CLAUDE.md with core utility pointers

**"Ego Spirals":**
- Symptom: AI gets stuck in loops on large tasks
- Cause: Task exceeds complexity threshold
- Solution: Decompose problems, use fresh sessions

**Context Degradation:**
- Symptom: AI forgets instructions, contradicts itself
- Cause: Bloated context window
- Solution: Clear context frequently, use persistent memory

## Git History Management

**Use git commands for project history instead of manual changelogs:**
- `git log` - Review commit history
- `git show` - Examine specific commits  
- `git diff` - Compare changes
- **Instruction**: "Use git to learn about project history"

This approach is more efficient than loading massive static changelogs into memory.

## Living Document Process

**CLAUDE.md as Continuous Learning System:**

### **Feedback Loop Pattern**
1. **Assign Task**: Give Claude a development task
2. **Observe Output**: Review the generated code/results  
3. **Identify Issues**: Note any problems or suboptimal patterns
4. **Update CLAUDE.md**: Add rules to prevent entire class of errors
5. **Commit Changes**: Include CLAUDE.md updates with code changes

### **When to Update CLAUDE.md**
- AI generates code that violates project patterns
- AI misunderstands architectural decisions  
- AI recreates existing functionality instead of reusing
- AI uses deprecated patterns or methods
- AI generates overly complex solutions for simple problems

### **Update Process**
```bash
# Use the /changes command to document learnings
/changes

# Or manually update based on patterns observed
# Add specific rules to prevent recurring issues
```

### **Examples of Learning Updates**

**Before:** AI keeps creating duplicate database connections
**CLAUDE.md Update:** Add explicit rule "NEVER use sqlite3.connect() directly - Use DatabaseManager"

**Before:** AI ignores existing utility functions  
**CLAUDE.md Update:** Add pointer to core utilities in architecture section

**Before:** AI generates announcement-style documentation
**CLAUDE.md Update:** Add rule "NEVER use progress percentages or superlatives"

### **Institutional Knowledge Capture**
- Every correction teaches the entire team (and future AI sessions)
- CLAUDE.md becomes repository of hard-won project wisdom
- Reduces repetitive code review comments
- Enables consistent code generation across team members

**Key Principle:** Turn every AI mistake into a preventable pattern through CLAUDE.md refinement.