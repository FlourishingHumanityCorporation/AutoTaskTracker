# Complexity Budget Check

Analyze the complexity impact of proposed changes and provide recommendations.

## Instructions for Claude:

1. **Calculate Current Complexity**:
   ```bash
   # Install complexity analysis tools if needed
   pip install radon xenon >/dev/null 2>&1
   
   # Analyze current complexity
   radon cc . -a -nc
   radon mi . -a
   ```

2. **Analyze Proposed Changes**:
   - Review the files and changes being proposed
   - Estimate complexity impact using these metrics:
     - **Cyclomatic Complexity**: Number of decision points
     - **Maintainability Index**: Overall maintainability score  
     - **Lines of Code**: Raw size impact
     - **Dependencies**: New imports and coupling

3. **Calculate Complexity Budget**:
   ```python
   # Use this complexity scoring system
   complexity_score = (
       cyclomatic_complexity * 2 +
       (lines_of_code / 10) +
       (new_dependencies * 5) +
       (nested_levels * 3)
   )
   ```

4. **Provide Recommendations**:
   - **Current Score**: Report baseline complexity
   - **Proposed Impact**: Estimate score change from changes
   - **Budget Assessment**: Is the change within reasonable limits?
   - **Refactoring Suggestions**: How to reduce complexity if needed

5. **Example Assessment**:
   ```
   Current complexity score: 25
   Proposed change adds: 5 points
   New total: 30 points
   
   Assessment: ACCEPTABLE (under threshold of 40)
   
   Recommendations:
   - Consider extracting helper method for repeated logic
   - Break down 15-line function into smaller functions
   - Current change is within budget, no blocking issues
   ```

6. **Complexity Thresholds**:
   - **Low**: 0-20 points (simple, maintainable)
   - **Medium**: 21-40 points (acceptable, monitor)  
   - **High**: 41-60 points (needs refactoring)
   - **Critical**: 60+ points (immediate attention required)

This command helps maintain codebase quality by preventing complexity creep and encouraging thoughtful design decisions.