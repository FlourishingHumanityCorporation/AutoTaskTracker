# Complexity Management & Budgeting

Systematic approach to managing code complexity and preventing technical debt in AutoTaskTracker.

## Complexity Budget System

### Complexity Scoring Formula

```python
complexity_score = (
    cyclomatic_complexity * 2 +     # Decision points (if/for/while)
    (lines_of_code / 10) +          # Size impact  
    (new_dependencies * 5) +        # Coupling impact
    (nested_levels * 3) +           # Nesting depth
    (pensieve_integration * 2)      # Integration complexity
)
```

### Complexity Thresholds

| Level | Score Range | Status | Action Required |
|-------|-------------|--------|----------------|
| **Low** | 0-20 | ✅ Simple, maintainable | Continue development |
| **Medium** | 21-40 | ⚠️ Acceptable, monitor | Consider optimizations |
| **High** | 41-60 | 🔶 Needs refactoring | Plan refactoring sprint |
| **Critical** | 60+ | ❌ Immediate attention | Block until resolved |

## Complexity Analysis Tools

### Automated Analysis

```bash
# Install complexity analysis tools
pip install radon xenon

# Analyze cyclomatic complexity
radon cc autotasktracker/ -a -nc

# Maintainability index
radon mi autotasktracker/ -a

# Halstead complexity
radon hal autotasktracker/ -a

# Generate complexity report
xenon --max-absolute B --max-modules A --max-average A autotasktracker/
```

### Claude Command Integration

```bash
# Use the complexity check command
/complexity-check

# Check specific file or module
/complexity-check autotasktracker/ai/vlm_processor.py
```

## AutoTaskTracker-Specific Complexity Factors

### Pensieve Integration Complexity

**Additional scoring for Pensieve integration:**
- **API-first pattern**: +2 points (necessary complexity)
- **Graceful fallback**: +3 points (safety complexity)
- **Health monitoring**: +1 point (operational complexity)
- **Multi-backend support**: +4 points (flexibility complexity)

### AI Pipeline Complexity

**AI processing complexity factors:**
- **Model loading**: +2 points per model
- **Graceful degradation**: +3 points (necessary for reliability)
- **Async processing**: +2 points (performance requirement)
- **Error handling**: +1 point per AI service

### Dashboard Complexity

**Streamlit dashboard complexity:**
- **State management**: +2 points per stateful component
- **Real-time updates**: +3 points (WebSocket complexity)
- **Data filtering**: +1 point per filter type
- **Component coupling**: +2 points per tight coupling

## Complexity Management Strategies

### 1. Function-Level Management

```python
# ✅ Low complexity - single responsibility
def extract_text_from_image(image_path: str) -> str:
    """Extract text using OCR with error handling."""
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        return ""

# ❌ High complexity - multiple responsibilities
def process_screenshot_with_ai_and_store_results(screenshot_path):
    # 50+ lines of mixed logic
    # OCR + VLM + task extraction + database storage
    # Multiple nested loops and conditions
    pass
```

### 2. Module-Level Management

**Recommended module complexity limits:**
- **Core modules** (`core/`): Max 30 points per file
- **AI modules** (`ai/`): Max 40 points per file (AI complexity expected)
- **Dashboard modules** (`dashboards/`): Max 25 points per file
- **Script modules** (`scripts/`): Max 35 points per file

### 3. Architectural Patterns for Complexity Reduction

**Repository Pattern:**
```python
# Reduces complexity by separating data access
class TaskRepository:
    def get_tasks(self, filters=None):
        # Complexity isolated here
        pass

# Dashboard uses simple interface
repo = TaskRepository()
tasks = repo.get_tasks(filters)
```

**Strategy Pattern for AI Processing:**
```python
# Reduces complexity through polymorphism
class ProcessingStrategy:
    def process(self, data): pass

class OCRStrategy(ProcessingStrategy): pass
class VLMStrategy(ProcessingStrategy): pass

# Simple context with complex strategies
processor = ProcessingContext(strategy)
result = processor.process(data)
```

## Complexity Monitoring Workflow

### Pre-Commit Analysis

```bash
# Add to git pre-commit hook
#!/bin/bash
echo "Checking complexity budget..."
current_score=$(radon cc autotasktracker/ -a -nc | grep "Average complexity" | awk '{print $3}')
if (( $(echo "$current_score > 4.0" | bc -l) )); then
    echo "❌ Complexity budget exceeded: $current_score"
    echo "Run /complexity-check for analysis"
    exit 1
fi
echo "✅ Complexity budget OK: $current_score"
```

### Continuous Monitoring

```python
# scripts/analysis/complexity_monitor.py
"""Monitor complexity trends over time."""

def track_complexity_metrics():
    metrics = {
        'timestamp': datetime.now(),
        'avg_cyclomatic': get_avg_complexity(),
        'high_complexity_files': find_complex_files(),
        'technical_debt_score': calculate_debt_score()
    }
    store_metrics(metrics)
    
def generate_complexity_report():
    """Generate weekly complexity report."""
    trends = analyze_complexity_trends()
    recommendations = generate_recommendations(trends)
    return {
        'status': get_complexity_status(),
        'trends': trends,
        'recommendations': recommendations
    }
```

## Refactoring Strategies

### When Complexity Budget Exceeded

1. **Extract Methods**: Break large functions into smaller ones
2. **Extract Classes**: Separate concerns into focused classes  
3. **Use Composition**: Replace inheritance with composition
4. **Simplify Conditionals**: Use early returns, guard clauses
5. **Remove Duplication**: Extract common patterns

### AutoTaskTracker-Specific Refactoring

**High-complexity AI processing:**
```python
# Before: Complex monolithic processor
def process_screenshot_complete(path):
    # 100+ lines of mixed AI processing
    pass

# After: Composed pipeline
class ProcessingPipeline:
    def __init__(self):
        self.steps = [OCRStep(), VLMStep(), ExtractionStep()]
    
    def process(self, path):
        data = {'path': path}
        for step in self.steps:
            data = step.process(data)
        return data
```

**Complex database operations:**
```python
# Before: Complex query building
def fetch_tasks_with_complex_filters(start, end, categories, processed):
    # Complex SQL building and parameter handling
    pass

# After: Query builder pattern
query = (TaskQueryBuilder()
         .with_date_range(start, end)
         .with_categories(categories)
         .with_processed_status(processed)
         .build())
```

## Integration with Development Workflow

### Feature Development

1. **Planning**: Estimate complexity impact during planning
2. **Implementation**: Monitor complexity during development
3. **Review**: Include complexity analysis in code reviews
4. **Refactoring**: Schedule regular complexity reduction sprints

### Team Process

```bash
# Include in definition of done
- [ ] Feature implemented and tested
- [ ] Complexity budget maintained
- [ ] No new high-complexity files introduced
- [ ] Refactoring opportunities identified
```

This complexity management system ensures AutoTaskTracker remains maintainable as it grows in functionality and sophistication.