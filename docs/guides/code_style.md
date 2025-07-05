# Code Style & Formatting Guidelines

## Python Code Standards

### Formatting
- **Indentation**: 4 spaces (no tabs)
- **Line Length**: 88 characters (Black formatter standard)
- **String Quotes**: Double quotes for strings, single quotes for string literals in code
- **Import Organization**: 
  1. Standard library imports
  2. Third-party imports  
  3. Local application imports
  4. Separate groups with blank lines

### Naming Conventions
- **Variables/Functions**: snake_case (`user_name`, `calculate_total`)
- **Classes**: PascalCase (`DatabaseManager`, `TaskExtractor`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private Methods**: Leading underscore (`_internal_method`)
- **Protected Methods**: Single underscore (`_protected_method`)

### Type Hints
- **Always use type hints** for function parameters and return values
- **Use Optional** for nullable parameters: `Optional[str]`
- **Use Union** for multiple types: `Union[str, int]`
- **Import types** from `typing` module

```python
from typing import Optional, List, Dict, Union

def process_tasks(tasks: List[Dict[str, str]], limit: Optional[int] = None) -> bool:
    """Process tasks with optional limit."""
    return True
```

## Database Patterns
- **NEVER use `sqlite3.connect()` directly** - Always use `DatabaseManager`
- **Use context managers** for database connections
- **Specify exception types** - No bare `except:` clauses

```python
# ✅ CORRECT
from autotasktracker.core.database import DatabaseManager
try:
    db = DatabaseManager()
    with db.get_connection() as conn:
        result = conn.execute(query)
except sqlite3.Error as e:
    logger.error(f"Database error: {e}")

# ❌ WRONG
try:
    conn = sqlite3.connect("database.db")
    result = conn.execute(query)
except:
    pass
```

## Error Handling
- **Specific exception types**: `except ValueError:` not `except:`
- **Logging over print**: Use `logging.getLogger(__name__)` not `print()`
- **Graceful degradation**: Handle missing dependencies gracefully

## Import Guidelines
- **Use specific imports**: `from module import SpecificClass`
- **Avoid star imports**: No `from module import *`
- **No sys.path manipulation**: Use proper package structure

## Documentation
- **Docstrings**: Use Google-style docstrings
- **Type information**: Include parameter and return types
- **Examples**: Provide usage examples for complex functions
- **Language**: Matter-of-fact, no progress percentages or superlatives
- **Updates**: Document what changed, not how much progress was made
- **Task summaries**: Report concrete changes, not subjective success claims

```python
def extract_tasks(content: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Extract tasks from content using AI classification.
    
    Args:
        content: The text content to analyze
        threshold: Confidence threshold for task classification
        
    Returns:
        List of task dictionaries with 'text', 'confidence', 'category' keys
        
    Example:
        >>> tasks = extract_tasks("Remember to buy milk")
        >>> print(tasks[0]['text'])
        'buy milk'
    """
    pass
```

## File Organization
- **No root directory files**: Use proper subdirectories
- **Logical grouping**: Related functionality in same module
- **Single responsibility**: One main purpose per file
- **Clear naming**: File names reflect their contents