# Repository Refactoring Plan

**Target**: `autotasktracker/dashboards/data/repositories.py` (1249 lines)  
**Goal**: Split into focused classes while maintaining 100% functionality  
**Current State**: Single file with 4 classes (BaseRepository, TaskRepository, ActivityRepository, MetricsRepository)

## Analysis Summary

**Current Structure:**
- **BaseRepository** (lines 20-443): 423 lines - API routing, caching, circuit breaker logic
- **TaskRepository** (lines 444-835): 391 lines - Task data access and processing
- **ActivityRepository** (lines 836-949): 113 lines - Activity and time tracking data
- **MetricsRepository** (lines 950-1249): 299 lines - Analytics and metrics computation

**Dependencies Found:**
- Used by: `task_board.py`, `analytics.py`, `__init__.py`, `performance_display.py`, `base.py`
- Imports: `DatabaseManager`, `PostgreSQLAdapter`, `PensieveAPIClient`, `models.py`

---

## Phase 1: Preparation & Safety Setup

### Pre-Refactoring Checklist

- [ ] **1.1** Run health tests to establish baseline
  ```bash
  pytest tests/health/ -v
  make complexity-check  # Current complexity score
  ```

- [ ] **1.2** Create comprehensive backup
  ```bash
  cp autotasktracker/dashboards/data/repositories.py autotasktracker/dashboards/data/repositories_backup.py
  git add . && git commit -m "backup: save repositories.py before refactoring"
  ```

- [ ] **1.3** Test all dashboard imports work
  ```bash
  python -c "from autotasktracker.dashboards.data.repositories import TaskRepository, MetricsRepository, ActivityRepository; print('✅ All imports work')"
  ```

- [ ] **1.4** Capture current functionality with integration test
  ```bash
  # Create test_repository_functionality.py to verify existing behavior
  pytest tests/integration/test_repository_functionality.py -v
  ```

- [ ] **1.5** Document current interface contracts
  ```bash
  # Generate method signatures and public interface documentation
  python scripts/analysis/document_repository_interface.py
  ```

### Pre-Mortem Risk Analysis

**❌ HIGH RISK: Import chain breakage**
- **Risk**: Dashboard imports fail after refactoring
- **Mitigation**: Create `__init__.py` with re-exports to maintain backward compatibility
- **Action**: Add step 2.1 to create compatibility layer

**❌ MEDIUM RISK: Circular dependencies**
- **Risk**: New modules import each other causing circular imports
- **Mitigation**: Use dependency injection and interface segregation
- **Action**: Add step 3.2 to define clear interfaces first

**❌ MEDIUM RISK: State/caching inconsistency**
- **Risk**: Split caching leads to inconsistent state across repositories
- **Mitigation**: Extract shared CacheManager as singleton
- **Action**: Add step 4.1 to create CacheCoordinator

**❌ LOW RISK: Performance degradation**
- **Risk**: Multiple repository instances vs. single instance
- **Mitigation**: Implement repository factory pattern
- **Action**: Add step 5.1 to create RepositoryFactory

---

## Phase 2: Interface Compatibility Layer

### Step 2.1: Create Backward Compatibility

- [ ] **2.1.1** Create `autotasktracker/dashboards/data/compatibility.py`
  ```python
  # Temporary compatibility layer to prevent import breakage
  from .core.base_repository import BaseRepository
  from .task.task_repository import TaskRepository  
  from .activity.activity_repository import ActivityRepository
  from .metrics.metrics_repository import MetricsRepository
  
  # Re-export everything for backward compatibility
  __all__ = ['BaseRepository', 'TaskRepository', 'ActivityRepository', 'MetricsRepository']
  ```

- [ ] **2.1.2** Update `repositories.py` to use compatibility layer
  ```python
  # Add at top of repositories.py
  import warnings
  warnings.warn("repositories.py is deprecated. Import from specific modules.", DeprecationWarning)
  from .compatibility import *
  ```

- [ ] **2.1.3** Test compatibility layer works
  ```bash
  python -c "from autotasktracker.dashboards.data.repositories import TaskRepository; print('✅ Compatibility layer works')"
  ```

---

## Phase 3: Extract Core Infrastructure

### Step 3.1: Extract Shared Components

- [ ] **3.1.1** Create `autotasktracker/dashboards/data/core/cache_coordinator.py`
  ```python
  # Extract lines 37-47, 378-394 from BaseRepository
  # Shared caching logic with performance stats
  ```

- [ ] **3.1.2** Create `autotasktracker/dashboards/data/core/circuit_breaker.py`
  ```python
  # Extract lines 49-57, 193-232 from BaseRepository  
  # API failure handling and circuit breaker logic
  ```

- [ ] **3.1.3** Create `autotasktracker/dashboards/data/core/query_router.py`
  ```python
  # Extract lines 169-192, 233-377 from BaseRepository
  # API routing and query execution logic
  ```

### Step 3.2: Define Clear Interfaces

- [ ] **3.2.1** Create `autotasktracker/dashboards/data/interfaces.py`
  ```python
  from abc import ABC, abstractmethod
  from typing import Protocol, List, Dict, Any
  import pandas as pd
  
  class DataRepository(Protocol):
      def _execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame: ...
      def invalidate_cache(self, pattern: str = None) -> None: ...
      def get_performance_stats(self) -> Dict[str, Any]: ...
  
  class TaskDataAccess(Protocol):
      def get_tasks_for_period(self, start_date, end_date, **kwargs) -> List[Task]: ...
      def get_task_groups(self, **kwargs) -> List[TaskGroup]: ...
  ```

- [ ] **3.2.2** Create `autotasktracker/dashboards/data/core/base_repository.py`
  ```python
  # Extract lines 20-167 from repositories.py
  # Keep only essential base functionality
  # Use composition for cache_coordinator, circuit_breaker, query_router
  ```

---

## Phase 4: Split Repository Classes

### Step 4.1: Extract TaskRepository

- [ ] **4.1.1** Create `autotasktracker/dashboards/data/task/task_repository.py`
  ```python
  # Extract TaskRepository class (lines 444-835)
  # Inherit from BaseRepository
  # Focus only on task-related data access
  ```

- [ ] **4.1.2** Create `autotasktracker/dashboards/data/task/task_transformer.py`
  ```python
  # Extract lines 591-744 from TaskRepository
  # _convert_task_dicts_to_objects, _normalize_window_title, _extract_task_context
  # Pure transformation logic with no database dependencies
  ```

- [ ] **4.1.3** Test TaskRepository in isolation
  ```bash
  python -c "from autotasktracker.dashboards.data.task.task_repository import TaskRepository; repo = TaskRepository(); print('✅ TaskRepository isolated')"
  ```

### Step 4.2: Extract ActivityRepository

- [ ] **4.2.1** Create `autotasktracker/dashboards/data/activity/activity_repository.py`
  ```python
  # Extract ActivityRepository class (lines 836-949)
  # Inherit from BaseRepository
  # Focus only on activity and time tracking data
  ```

- [ ] **4.2.2** Test ActivityRepository in isolation
  ```bash
  python -c "from autotasktracker.dashboards.data.activity.activity_repository import ActivityRepository; repo = ActivityRepository(); print('✅ ActivityRepository isolated')"
  ```

### Step 4.3: Extract MetricsRepository

- [ ] **4.3.1** Create `autotasktracker/dashboards/data/metrics/metrics_repository.py`
  ```python
  # Extract MetricsRepository class (lines 950-1249)
  # Inherit from BaseRepository
  # Focus only on analytics and metrics computation
  ```

- [ ] **4.3.2** Create `autotasktracker/dashboards/data/metrics/metrics_calculator.py`
  ```python
  # Extract complex metrics calculation methods
  # Pure computation logic with no database dependencies
  ```

- [ ] **4.3.3** Test MetricsRepository in isolation
  ```bash
  python -c "from autotasktracker.dashboards.data.metrics.metrics_repository import MetricsRepository; repo = MetricsRepository(); print('✅ MetricsRepository isolated')"
  ```

---

## Phase 5: Integration & Optimization

### Step 5.1: Create Repository Factory

- [ ] **5.1.1** Create `autotasktracker/dashboards/data/factory.py`
  ```python
  class RepositoryFactory:
      """Centralized repository creation with shared dependencies."""
      
      def __init__(self, db_manager=None, use_pensieve=True):
          self.db_manager = db_manager or DatabaseManager()
          self.use_pensieve = use_pensieve
          self._cache_coordinator = CacheCoordinator()
          self._circuit_breaker = CircuitBreaker()
          
      def create_task_repository(self) -> TaskRepository:
          return TaskRepository(
              db_manager=self.db_manager,
              use_pensieve=self.use_pensieve,
              cache_coordinator=self._cache_coordinator
          )
      
      # Similar methods for ActivityRepository, MetricsRepository
  ```

- [ ] **5.1.2** Update dashboard imports to use factory
  ```python
  # Update task_board.py, analytics.py to use RepositoryFactory
  from autotasktracker.dashboards.data.factory import RepositoryFactory
  
  factory = RepositoryFactory()
  task_repo = factory.create_task_repository()
  metrics_repo = factory.create_metrics_repository()
  ```

### Step 5.2: Update Package Structure

- [ ] **5.2.1** Create module `__init__.py` files
  ```python
  # autotasktracker/dashboards/data/core/__init__.py
  from .base_repository import BaseRepository
  from .cache_coordinator import CacheCoordinator
  # etc.
  
  # autotasktracker/dashboards/data/task/__init__.py
  from .task_repository import TaskRepository
  from .task_transformer import TaskTransformer
  
  # Similar for activity/, metrics/
  ```

- [ ] **5.2.2** Update main `data/__init__.py`
  ```python
  # Maintain backward compatibility while encouraging new imports
  from .task.task_repository import TaskRepository
  from .activity.activity_repository import ActivityRepository  
  from .metrics.metrics_repository import MetricsRepository
  from .factory import RepositoryFactory
  
  # Legacy compatibility (with deprecation warning)
  from .compatibility import *
  ```

---

## Phase 6: Validation & Cleanup

### Step 6.1: Functional Testing

- [ ] **6.1.1** Run comprehensive dashboard tests
  ```bash
  # Test all dashboards load without errors
  python -c "import autotasktracker.dashboards.task_board" 
  python -c "import autotasktracker.dashboards.analytics"
  python -c "import autotasktracker.dashboards.timetracker"
  ```

- [ ] **6.1.2** Run integration tests
  ```bash
  pytest tests/integration/test_repository_functionality.py -v
  pytest tests/functional/test_dashboard_data_loading.py -v
  ```

- [ ] **6.1.3** Verify data consistency
  ```bash
  # Test that old and new repositories return identical data
  python tests/integration/test_repository_equivalence.py
  ```

### Step 6.2: Performance Validation

- [ ] **6.2.1** Run complexity analysis
  ```bash
  make complexity-check
  # Verify: repositories.py removed, new files have complexity < 15
  ```

- [ ] **6.2.2** Check maintainability improvement
  ```bash
  radon mi autotasktracker/dashboards/data/ -s
  # Verify: all files have maintainability index > 15
  ```

- [ ] **6.2.3** Performance benchmark
  ```bash
  pytest tests/performance/test_repository_performance.py -v
  # Verify: no performance regression
  ```

### Step 6.3: Cleanup & Documentation

- [ ] **6.3.1** Remove deprecated files
  ```bash
  rm autotasktracker/dashboards/data/repositories_backup.py
  rm autotasktracker/dashboards/data/repositories.py
  rm autotasktracker/dashboards/data/compatibility.py
  ```

- [ ] **6.3.2** Update imports across codebase
  ```bash
  # Find and update all remaining imports
  grep -r "from.*repositories import" autotasktracker/dashboards/
  # Update to use specific module imports
  ```

- [ ] **6.3.3** Update documentation
  ```bash
  # Update CLAUDE.md, architecture docs to reflect new structure
  # Update code examples to use new import patterns
  ```

---

## Success Criteria & Verification

### Technical Metrics
- [ ] **All dashboards load without errors** (functional)
- [ ] **No complexity score > 15** in any new file (maintainability) 
- [ ] **All files have maintainability index > 15** (quality)
- [ ] **No performance regression > 10%** (speed)
- [ ] **100% test coverage** on refactored modules (reliability)

### Structural Improvements
- [ ] **4 files → 10+ focused files** (separation of concerns)
- [ ] **1249 lines → max 200 lines per file** (readability)
- [ ] **Clear module boundaries** (task/, activity/, metrics/, core/)
- [ ] **Eliminated circular dependencies** (architecture)
- [ ] **Backward compatibility maintained** (stability)

### Operational Benefits
- [ ] **Easier testing** of individual components
- [ ] **Faster CI builds** (reduced complexity scanning time)
- [ ] **Simplified debugging** (smaller, focused modules)
- [ ] **Enhanced team productivity** (multiple developers can work on different repositories)

---

## Rollback Plan

**If any step fails:**

1. **Immediate Rollback**
   ```bash
   git reset --hard HEAD~1  # If committed
   cp autotasktracker/dashboards/data/repositories_backup.py autotasktracker/dashboards/data/repositories.py
   ```

2. **Verify Rollback Success**
   ```bash
   pytest tests/health/ -v
   python -c "from autotasktracker.dashboards.data.repositories import TaskRepository; print('✅ Rollback successful')"
   ```

3. **Post-Rollback Analysis**
   - Document what failed and why
   - Adjust plan to address failure points
   - Consider smaller incremental steps

---

## Timeline Estimate

- **Phase 1-2**: 2 hours (prep and compatibility)
- **Phase 3**: 3 hours (extract core infrastructure)  
- **Phase 4**: 4 hours (split repository classes)
- **Phase 5**: 2 hours (integration and optimization)
- **Phase 6**: 2 hours (validation and cleanup)

**Total**: ~13 hours over 2-3 days

---

## Additional Safety Measures (From Pre-Mortem)

### Automated Validation Script

- [ ] **Create `scripts/validate_refactoring.py`**
  ```python
  # Script that runs after each phase to validate:
  # - All imports still work
  # - No functionality broken
  # - Performance within acceptable bounds
  # - Complexity improvements achieved
  ```

### Incremental Commit Strategy

- [ ] **Commit after each major step**
  ```bash
  # After Phase 3: "refactor: extract core infrastructure"
  # After Phase 4: "refactor: split repository classes"  
  # After Phase 5: "refactor: add factory and optimization"
  # After Phase 6: "refactor: cleanup and finalize"
  ```

### Stakeholder Communication

- [ ] **Notify team before starting**
  - Dashboard functionality may be temporarily affected
  - Development work should avoid `data/repositories.py` during refactoring
  - Estimated completion timeline

---

**Next Action**: Begin Phase 1 with preparation and safety setup.