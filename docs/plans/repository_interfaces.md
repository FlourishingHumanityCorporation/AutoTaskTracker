# Repository Interface Documentation
Current interfaces that must be preserved during refactoring.
Generated on: Sat Jul  5 15:17:56 PDT 2025

## BaseRepository
**Purpose**: Base repository with common functionality.
**Public Methods**:
- `get_cache_stats(self) -> Dict[str, Any]`
- `get_performance_stats(self) -> Dict[str, Any]`
- `invalidate_cache(self, pattern: str = None)`
**Private Methods**:
- `_execute_api_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_listing_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_specific_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pandas.core.frame.DataFrame`
- `_execute_search_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_is_circuit_breaker_open(self) -> bool`
- `_is_data_query(self, query: str) -> bool`
- `_record_api_failure(self, error_message: str)`
- `_reset_circuit_breaker(self)`
- `_route_query_to_available_endpoints(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`

## TaskRepository
**Purpose**: Repository for task-related data access.
**Public Methods**:
- `get_cache_stats(self) -> Dict[str, Any]`
- `get_performance_stats(self) -> Dict[str, Any]`
- `get_task_groups(self, start_date: datetime.datetime, end_date: datetime.datetime, min_duration_minutes: float = 0.5, gap_threshold_minutes: float = 15) -> List[autotasktracker.dashboards.data.models.TaskGroup]`
- `get_tasks_for_period(self, start_date: datetime.datetime, end_date: datetime.datetime, categories: Optional[List[str]] = None, limit: int = 1000) -> List[autotasktracker.dashboards.data.models.Task]`
- `invalidate_cache(self, pattern: str = None)`
**Private Methods**:
- `_convert_task_dicts_to_objects(self, task_dicts: List[Dict[str, Any]]) -> List[autotasktracker.dashboards.data.models.Task]`
- `_execute_api_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_listing_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_specific_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pandas.core.frame.DataFrame`
- `_execute_search_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_extract_task_context(self, title: str) -> str`
- `_get_tasks_sqlite_fallback(self, start_date: datetime.datetime, end_date: datetime.datetime, categories: Optional[List[str]] = None, limit: int = 1000) -> List[autotasktracker.dashboards.data.models.Task]`
- `_is_circuit_breaker_open(self) -> bool`
- `_is_data_query(self, query: str) -> bool`
... and 4 more private methods

## ActivityRepository
**Purpose**: Repository for activity/screenshot data.
**Public Methods**:
- `get_cache_stats(self) -> Dict[str, Any]`
- `get_performance_stats(self) -> Dict[str, Any]`
- `get_recent_activities(self, limit: int = 50, categories: Optional[List[str]] = None) -> List[autotasktracker.dashboards.data.models.Activity]`
- `invalidate_cache(self, pattern: str = None)`
**Private Methods**:
- `_convert_task_dicts_to_activities(self, task_dicts: List[Dict[str, Any]]) -> List[autotasktracker.dashboards.data.models.Activity]`
- `_execute_api_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_listing_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_specific_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pandas.core.frame.DataFrame`
- `_execute_search_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_get_activities_sqlite_fallback(self, limit: int = 50, categories: Optional[List[str]] = None) -> List[autotasktracker.dashboards.data.models.Activity]`
- `_is_circuit_breaker_open(self) -> bool`
- `_is_data_query(self, query: str) -> bool`
- `_record_api_failure(self, error_message: str)`
... and 2 more private methods

## MetricsRepository
**Purpose**: Repository for metrics and analytics data.
**Public Methods**:
- `get_cache_stats(self) -> Dict[str, Any]`
- `get_daily_metrics(self, date: datetime.datetime) -> Optional[autotasktracker.dashboards.data.models.DailyMetrics]`
- `get_metrics_summary(self, start_date: datetime.datetime, end_date: datetime.datetime) -> Dict[str, Any]`
- `get_performance_stats(self) -> Dict[str, Any]`
- `invalidate_cache(self, pattern: str = None)`
**Private Methods**:
- `_calculate_daily_metrics_from_tasks(self, task_dicts: List[Dict[str, Any]], date) -> autotasktracker.dashboards.data.models.DailyMetrics`
- `_calculate_metrics_summary_from_tasks(self, task_dicts: List[Dict[str, Any]], start_date: datetime.datetime, end_date: datetime.datetime) -> Dict[str, Any]`
- `_execute_api_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_listing_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_entity_specific_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_execute_query(self, query: str, params: tuple = (), cache_ttl: int = 300) -> pandas.core.frame.DataFrame`
- `_execute_search_query(self, query: str, params: tuple) -> Optional[pandas.core.frame.DataFrame]`
- `_get_daily_metrics_sqlite_fallback(self, date, start: datetime.datetime, end: datetime.datetime) -> Optional[autotasktracker.dashboards.data.models.DailyMetrics]`
- `_get_metrics_summary_sqlite_fallback(self, start_date: datetime.datetime, end_date: datetime.datetime) -> Dict[str, Any]`
- `_is_circuit_breaker_open(self) -> bool`
... and 4 more private methods

## Import Statements
```python
from autotasktracker.dashboards.data.repositories import (
    BaseRepository, TaskRepository, ActivityRepository, MetricsRepository
)
```

## Usage Examples
```python
# Current usage patterns that must continue working:
task_repo = TaskRepository()
metrics_repo = MetricsRepository()
activity_repo = ActivityRepository()

# Performance stats access
stats = task_repo.get_performance_stats()

# Cache management
task_repo.invalidate_cache()
```
