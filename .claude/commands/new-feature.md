# Create New Feature Plan

Generate a detailed implementation plan for a new AutoTaskTracker feature.

## Arguments
- `$ARGUMENTS` - Feature description (e.g., "Add real-time task notifications")

## Instructions for Claude:

1. **Analyze Feature Request**:
   - Parse the feature description from `$ARGUMENTS`
   - Identify core requirements and scope
   - Check if similar functionality exists

2. **Pensieve Integration Assessment**:
   ```bash
   # Check existing Pensieve capabilities
   memos --help | grep -i "$ARGUMENTS" || echo "No direct Pensieve support found"
   ```

3. **Create Implementation Plan**:
   - Copy the plan template: `@docs/templates/plan.md`
   - Fill in the feature details:
     - Overview and requirements
     - Break into phases and tasks
     - Identify files that need modification
     - Estimate complexity (Low/Medium/High)
     - Define testing strategy

4. **Technology Stack Analysis**:
   - Determine if feature needs:
     - New AI models or processing
     - Database schema changes
     - Dashboard modifications
     - Pensieve integration changes
     - New API endpoints

5. **Save Plan File**:
   ```bash
   # Create plan file with sanitized name
   FEATURE_NAME=$(echo "$ARGUMENTS" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
   cp docs/templates/plan.md "plan-${FEATURE_NAME}.md"
   ```

6. **Next Steps Guidance**:
   - Recommend starting with TDD approach if applicable
   - Suggest breaking into smaller sub-features if complex
   - Identify which existing patterns to follow
   - Point to relevant documentation and examples

7. **Report Plan Location**: Provide path to the created plan file and summary of recommended approach.

This command creates a structured implementation plan following AutoTaskTracker best practices.