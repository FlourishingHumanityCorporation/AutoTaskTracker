# Testing Guide

## MANDATORY Before ANY Commit:

```bash
# 1. Core health checks (type-based modular structure)
pytest tests/health/code_quality/ -v                    # Imports, exceptions, naming, style
pytest tests/health/database/ -v                        # Database patterns and connections
pytest tests/health/configuration/ -v                   # Configuration loading and usage

# 2. Integration and documentation health checks
pytest tests/health/integration/ -v                     # Pensieve API, service commands, backends
pytest tests/health/documentation/ -v                   # Documentation structure and content
pytest tests/health/testing/ -v                         # Testing system organization

# 3. Effectiveness-based validation (validates actual bug-catching ability)
pytest tests/health/testing/test_effectiveness_validation.py -v  # Mutation testing effectiveness
python tests/health/testing/real_world_demo.py                   # Quick effectiveness demo

# 3. Core error and documentation health checks
pytest tests/health/test_error_health.py -v             # Error handling patterns and file validation
pytest tests/health/test_documentation_health.py -v     # Documentation quality and structure

# 4. Legacy core tests (comprehensive but monolithic - prefer modular tests above)
pytest tests/health/test_codebase_health.py -v          # General code quality (1,051 lines)
pytest tests/health/test_testing_system_health.py -v    # Testing system health (1,966 lines)

# 5. Critical functionality
pytest tests/integration/test_pensieve_critical_path.py -v

# 6. Real functional tests (validates actual functionality)
python tests/run_functional_tests.py --verbose

# Alternative: Run all health tests together
pytest tests/health/ -v

# Performance optimization options
export PENSIEVE_MAX_FILES_PER_TEST=30    # Reduce file scan scope for faster tests
pytest tests/health/ -x --tb=short       # Stop on first failure, short traceback
pytest tests/health/ -n auto             # Parallel execution (requires pytest-xdist)

# Optimized parallel execution (recommended for CI/CD)
python scripts/run_health_tests_parallel.py                    # Auto-detect workers, optimized settings
python scripts/run_health_tests_parallel.py --fast             # Fast mode: reduced file scanning
python scripts/run_health_tests_parallel.py -w 2               # Use specific number of workers
python scripts/run_health_tests_parallel.py tests/health/database/ --fast  # Test specific module
```

## Real Functional Tests

```bash
# Run all functional tests
python tests/run_functional_tests.py

# Run specific categories
python tests/run_functional_tests.py --category ocr       # Real OCR
python tests/run_functional_tests.py --category database # Real SQLite
python tests/run_functional_tests.py --category ai       # Real AI
python tests/run_functional_tests.py --category pipeline # End-to-end
```

## What Tests Check:
- ✅ No bare except clauses
- ✅ No sys.path hacks
- ✅ No root directory clutter
- ✅ Proper database usage
- ✅ Documentation quality
- ✅ No duplicate/improved files
- ✅ Testing system health and organization
- ✅ Test categorization and discoverability
- ✅ No infinite loops in tests
- ✅ Proper fixture usage
- ✅ **Effectiveness validation**: Tests actually catch real bugs through mutation testing

## Effectiveness-Based Validation

**Core Question**: "Would these tests catch the bug that will happen next week?"

### How It Works:
1. **Mutation Testing**: Introduces controlled bugs into code
2. **Test Execution**: Runs tests against mutated code
3. **Effectiveness Measurement**: Calculates percentage of bugs caught
4. **AutoTaskTracker-Specific Patterns**: Tests for database errors, API failures, exception handling

### Configuration:
```bash
# Fast demo (3 mutations, 45s timeout)
python tests/health/testing/real_world_demo.py

# Full analysis (10 mutations, 60s timeout)
EFFECTIVENESS_MAX_MUTATIONS=10 EFFECTIVENESS_TIMEOUT=60 pytest tests/health/testing/test_effectiveness_validation.py -v
```

### Effectiveness Thresholds:
- **70%+**: Effective test - good bug-catching ability
- **50-69%**: Moderate - some bugs may slip through  
- **<50%**: Needs work - significant gaps in test coverage