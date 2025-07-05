# Example Effectiveness Validation Configurations

This directory contains example configuration files for different use cases of the effectiveness-based test validation system.

## 🚀 Quick Start

Copy any example configuration to your project:

```bash
# Copy to project config location
cp tests/health/testing/examples/fast_development.json tests/health/testing/effectiveness_config.json

# Or use environment variables (see each config for details)
export EFFECTIVENESS_MAX_MUTATIONS=5
export EFFECTIVENESS_TIMEOUT=15
```

## 📁 Available Configurations

### 🏃 `fast_development.json`
**Use case:** Daily development workflow, quick feedback  
**Focus:** Fast execution, basic mutation testing  
**Timeouts:** 10s per test, 60s total  
**Mutations:** 3 per file, basic patterns only  
**Thresholds:** Lenient (40% critical, 60% warning)

```bash
# Usage
cp examples/fast_development.json effectiveness_config.json
```

### 🔍 `quality_focused.json`  
**Use case:** Code review, critical path validation  
**Focus:** High quality standards, comprehensive analysis  
**Timeouts:** 45s per test, 600s total  
**Mutations:** 15 per file, comprehensive patterns  
**Thresholds:** Strict (80% critical, 90% warning)

```bash
# Usage  
cp examples/quality_focused.json effectiveness_config.json
```

### 🏗️ `comprehensive_ci.json`
**Use case:** CI/CD pipeline, production deployment  
**Focus:** Thorough analysis, all mutation types  
**Timeouts:** 60s per test, 900s total  
**Mutations:** 20 per file, all patterns  
**Thresholds:** Production-ready (70% critical, 85% warning)

```bash
# Usage
cp examples/comprehensive_ci.json effectiveness_config.json
```

## ⚙️ Configuration Parameters

### Mutation Testing
- **`max_mutations_per_file`**: Number of code changes to test per file
- **`timeout_seconds`**: Maximum time per test execution
- **`mutation_types`**: Types of bugs to simulate (off_by_one, boolean_flip, etc.)

### Analysis Limits  
- **`max_files_per_test`**: Maximum files to analyze in one run
- **`max_analysis_time_seconds`**: Total time budget for analysis
- **`min_effectiveness_threshold`**: Minimum acceptable effectiveness score

### Validation Weights
- **`mutation_weight`**: Importance of mutation testing (0.0-1.0)
- **`bug_pattern_weight`**: Importance of real bug patterns (0.0-1.0)  
- **`integration_weight`**: Importance of integration testing (0.0-1.0)

## 🎯 Choosing the Right Configuration

### For Daily Development
- Use **`fast_development.json`** 
- Quick feedback, focus on major issues
- Low resource usage

### For Code Reviews
- Use **`quality_focused.json`**
- Higher standards, comprehensive analysis
- Balanced performance vs thoroughness

### For CI/CD Pipelines  
- Use **`comprehensive_ci.json`**
- Production-ready validation
- Full mutation testing coverage

### For Custom Scenarios
Start with the closest example and modify:

```json
{
  "mutation": {
    "max_mutations_per_file": 8,
    "timeout_seconds": 30
  },
  "analysis": {
    "max_files_per_test": 15,
    "min_effectiveness_threshold": 60.0
  }
}
```

## 🔧 Environment Variable Overrides

Any configuration can be overridden with environment variables:

```bash
# Override mutation settings
export EFFECTIVENESS_MAX_MUTATIONS=5
export EFFECTIVENESS_TIMEOUT=20

# Override analysis settings  
export EFFECTIVENESS_MAX_FILES=10
export EFFECTIVENESS_MIN_THRESHOLD=50.0

# Override performance settings
export EFFECTIVENESS_PARALLEL=true
export EFFECTIVENESS_MAX_WORKERS=4

# Override logging
export EFFECTIVENESS_LOG_LEVEL=DEBUG
export EFFECTIVENESS_DETAILED_ERRORS=true
```

## 📊 Performance Guidelines

### Development Machine
- **Files**: 5-15 per run
- **Mutations**: 3-8 per file  
- **Timeout**: 10-30 seconds
- **Workers**: 2-4 threads

### CI Server
- **Files**: 25-50 per run
- **Mutations**: 10-20 per file
- **Timeout**: 30-60 seconds  
- **Workers**: 4-8 threads

### High-Performance Server
- **Files**: 50+ per run
- **Mutations**: 15-25 per file
- **Timeout**: 45-90 seconds
- **Workers**: 8+ threads

## 🚨 Troubleshooting

### Tests Timing Out
- Reduce `max_mutations_per_file`
- Decrease `timeout_seconds`  
- Set `enable_parallel_execution: false`

### Analysis Too Slow
- Reduce `max_files_per_test`
- Decrease `max_analysis_time_seconds`
- Enable parallel execution

### Too Many False Positives
- Lower thresholds (`min_effectiveness_threshold`)
- Reduce mutation types to basic patterns
- Increase `max_hardcoded_items` tolerance

### Missing Real Issues
- Increase `max_mutations_per_file`
- Add more `mutation_types`
- Raise thresholds for stricter validation

## 🔄 Upgrading Configurations

When updating the effectiveness validation system:

1. **Backup current config**: Save your working configuration
2. **Review new examples**: Check if new parameters are available
3. **Merge changes**: Add new parameters while keeping your customizations
4. **Test thoroughly**: Validate that the updated config works as expected

## 📚 Related Documentation

- [Configuration System](../config.py) - Technical implementation
- [Mutation Testing](../mutation_effectiveness.py) - Core mutation testing logic
- [Performance Optimization](../performance_optimizer.py) - Parallel execution and caching
- [README](../README.md) - System overview and usage examples