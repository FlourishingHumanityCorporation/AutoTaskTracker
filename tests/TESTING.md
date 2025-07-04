# Testing Guidelines for AutoTaskTracker

This document outlines the testing strategy and guidelines for the AutoTaskTracker project.

## Testing Philosophy

We follow Test-Driven Development (TDD) principles where practical, focusing on behavior rather than implementation details. Each test should be clear, focused, and independent.

## Test Structure

1. **Test Naming**: `test_<method_name>_<scenario>_<expected_behavior>`
2. **Test Organization**: Group related tests in classes when they test the same unit
3. **Test Isolation**: Each test should be independent and not rely on state from other tests

## Writing Effective Tests

### 1. Define the Behavior
Start by clearly stating what behavior you're testing in one sentence.

### 2. Write the Assertion First (TDD Style)
Begin with the expected outcome before writing the test setup.

### 3. Keep Setup Clean
- Use helper functions or builders for complex test data
- Keep test data minimal and focused
- Prefer factory_boy or similar for object creation

### 4. Make Tests Meaningful
- Ensure tests fail with helpful error messages
- Test edge cases and error conditions
- Avoid testing implementation details

## Example Test Case

```python
def test_format_duration_less_than_minute_returns_seconds():
    # Arrange
    duration = 45.5  # seconds
    
    # Act
    result = format_duration(duration)
    
    # Assert
    assert result == "45.5s"


def test_format_duration_more_than_minute_shows_minutes():
    # Arrange
    duration = 125.5  # 2 minutes 5.5 seconds
    
    # Act
    result = format_duration(duration)
    
    # Assert
    assert result == "2m 5.5s"
```

## Test Categories

1. **Unit Tests**: Test individual functions/methods in isolation
2. **Integration Tests**: Test interactions between components
3. **End-to-End Tests**: Test complete workflows

## Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src tests/

# Run a specific test file
pytest tests/test_models.py
```

## Test Coverage

We aim to maintain high test coverage, with particular focus on:
- Core business logic
- Data transformations
- Error handling
- Public APIs

## Mocking

Use the `pytest-mock` package for mocking. Follow these guidelines:
- Only mock external dependencies, not your own code
- Prefer dependency injection over monkey patching
- Keep mock setups simple and clear

## Continuous Integration

All tests must pass before code can be merged into the main branch. The CI pipeline will run:
1. Unit tests
2. Integration tests
3. Code style checks
4. Type checking (if applicable)
5. Security scanning

## Writing Maintainable Tests

- **Readability**: Tests should be self-documenting
- **Deterministic**: Tests should produce the same results every time
- **Fast**: Keep tests running quickly by avoiding I/O when possible
- **Independent**: Tests should not depend on each other
- **Revealing**: Test failures should clearly indicate what went wrong
