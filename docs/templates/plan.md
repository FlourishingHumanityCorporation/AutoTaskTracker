# Implementation Plan: [Feature Name]

**Created:** [YYYY-MM-DD]  
**Status:** Planning | In Progress | Review | Complete  
**Estimated Complexity:** Low | Medium | High  

## Overview

Brief description of the feature/task and its purpose.

## Requirements

- [ ] Requirement 1
- [ ] Requirement 2  
- [ ] Requirement 3

## Implementation Tasks

### Phase 1: [Phase Name]
**Status:** ⏸️ Pending | 🔄 In Progress | ✅ Complete

- [ ] Task 1.1 - Brief description
  - **Files:** `path/to/file1.py`, `path/to/file2.py`
  - **Dependencies:** None | Task X.Y
  - **Estimated effort:** 1-2 hours | Half day | Full day
  
- [ ] Task 1.2 - Brief description
  - **Files:** `path/to/file.py`
  - **Dependencies:** Task 1.1
  - **Estimated effort:** 1-2 hours

### Phase 2: [Phase Name]
**Status:** ⏸️ Pending

- [ ] Task 2.1 - Brief description
  - **Files:** `path/to/file.py`
  - **Dependencies:** Phase 1 complete
  - **Estimated effort:** Half day

## Testing Strategy

- [ ] Unit tests for core functionality
- [ ] Integration tests for [specific integration]
- [ ] Functional tests with real data
- [ ] Health tests validation

**Test files to create/update:**
- `tests/unit/test_[feature].py`
- `tests/integration/test_[feature]_integration.py`

## Validation Criteria

- [ ] All tests pass
- [ ] Health checks pass: `pytest tests/health/ -v`
- [ ] No performance degradation
- [ ] Documentation updated
- [ ] Pensieve integration maintained

## Rollback Plan

**If implementation fails:**
1. Revert commits: `git revert [commit-hash]`
2. Restore backup of modified files
3. Run health checks to confirm system stability

## Notes & Decisions

**Design decisions:**
- Decision 1: Rationale
- Decision 2: Rationale

**Blocked items:**
- [ ] Blocked item 1: Reason and resolution plan

## Completion Checklist

- [ ] All tasks completed
- [ ] Tests passing
- [ ] Documentation updated  
- [ ] Code reviewed
- [ ] Performance validated
- [ ] Commit messages follow conventional format
- [ ] Plan marked as Complete

---

**Usage Instructions:**
1. Copy this template when starting new features
2. Update status after each task completion
3. Use `/changes` command to document progress
4. Commit plan updates with implementation changes