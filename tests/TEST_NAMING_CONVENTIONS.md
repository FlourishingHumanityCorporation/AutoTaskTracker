# Test Naming Conventions

This document establishes the naming conventions for all tests in AutoTaskTracker to ensure clarity, prevent duplicates, and make it easy to understand what each test does.

## Test File Naming Convention

**Pattern**: `test_<component>_<specific_area>.py`

### Examples:
- `test_pensieve_critical_path.py` - Critical path tests for Pensieve backend
- `test_pensieve_end_to_end.py` - Full end-to-end Pensieve integration
- `test_basic_functionality.py` - Basic functionality smoke tests
- `test_ai_features_integration.py` - AI features integration tests
- `test_dashboard_core.py` - Core dashboard data models and repositories
- `test_dashboard_refactored_components.py` - Refactored UI components
- `test_codebase_health.py` - Code quality and organization checks
- `test_testing_system_health.py` - Testing system validation

## Test Function Naming Convention

**Pattern**: `test_<component>_<action>_<expected_outcome>_<context>`

### Structure:
1. **Component**: What system/component is being tested
2. **Action**: What action or behavior is being tested
3. **Expected Outcome**: What should happen
4. **Context**: Additional context if needed

### Examples:

#### Pensieve Tests
- `test_pensieve_screenshot_capture_creates_database_entry()` 
- `test_pensieve_watch_service_sets_processed_timestamp()`
- `test_pensieve_memos_services_status_command_shows_running_processes()`
- `test_pensieve_rest_api_health_endpoint_responds_successfully()`
- `test_pensieve_complete_pipeline_capture_to_api_retrieval()`

#### AI Feature Tests
- `test_visual_language_model_integration_and_task_extraction()`
- `test_optical_character_recognition_enhancement_and_text_extraction()`
- `test_semantic_embeddings_search_engine_functionality()`
- `test_ai_enhanced_integrated_task_extractor_with_multiple_ai_features()`
- `test_database_ai_coverage_statistics_and_query_functionality()`

#### Dashboard Tests
- `test_task_data_model_creates_valid_object_with_duration_calculation()`
- `test_task_group_data_model_aggregates_multiple_tasks_with_time_range()`
- `test_daily_metrics_data_model_calculates_productivity_statistics()`
- `test_task_repository_initialization_with_database_connection()`
- `test_get_tasks_for_date_range_returns_formatted_task_objects()`
- `test_metrics_repository_handles_empty_database_gracefully()`

#### Dashboard Components Tests
- `test_time_filter_component_calculates_today_date_range_correctly()`
- `test_category_filter_component_provides_expected_default_categories()`
- `test_dashboard_cache_creates_consistent_keys_for_same_parameters()`
- `test_dashboard_cache_stores_and_retrieves_data_with_ttl_expiration()`

#### E2E Tests
- `test_complete_end_to_end_user_journey_from_screenshot_to_dashboard_display()`
- `test_pensieve_pipeline_processes_screenshots_in_headless_ci_environment()`

#### Integration Tests
- `test_task_and_metrics_repositories_work_together_in_integration()`
- `test_refactored_dashboard_components_work_together_in_integration()`

## Anti-Patterns to Avoid

### ❌ Bad Naming Examples:
- `test_basic()` - Too vague
- `test_functionality()` - No specifics
- `test_repo()` - Which repo? What about it?
- `test_init()` - What's being initialized?
- `test_model()` - Which model? What aspect?
- `test_vlm()` - What about VLM?

### ✅ Good Naming Examples:
- `test_task_repository_initialization_with_database_connection()` - Clear, specific
- `test_visual_language_model_integration_and_task_extraction()` - Descriptive
- `test_pensieve_screenshot_capture_creates_database_entry()` - Action and outcome clear

## Benefits of This Convention

1. **No Duplicates**: Long descriptive names make it obvious if tests are doing the same thing
2. **Self-Documenting**: Test name explains exactly what it tests
3. **Easy to Find**: Consistent naming makes it easy to locate specific tests
4. **Clear Intent**: Each test's purpose is immediately obvious
5. **Grep-Friendly**: Easy to search for tests related to specific components

## Validation

The `test_testing_system_health.py` includes checks to ensure:
- All test functions follow naming conventions
- No duplicate test names exist
- Test functions are descriptive and discoverable
- Tests are properly categorized

## Migration Complete

All existing tests have been migrated to follow these conventions as of the test system overhaul.