# Scripts Module Context

**Focus**: Standalone scripts for processing, analysis, and maintenance

## Module-Specific Rules

- **Robust error handling**: Scripts should handle missing dependencies gracefully
- **Progress reporting**: Long-running scripts must show progress
- **Logging**: Use proper logging instead of print statements
- **CLI interfaces**: Provide clear command-line interfaces with help
- **Idempotent operations**: Scripts should be safe to run multiple times

## Script Categories

**Processing Scripts (`processing/`):**
- `auto_processor.py` - Automated screenshot processing with AI
- `process_tasks.py` - Task extraction pipeline
- `realtime_processor.py` - Continuous screenshot monitoring
- `screenshot_processor.py` - Batch screenshot processing

**AI Scripts (`ai/`):**
- `ai_cli.py` - AI model management and status
- `vlm_processor.py` - VLM processing utilities
- `generate_embeddings_simple.py` - Embeddings generation

**Analysis Scripts (`analysis/`):**
- `pipeline_monitor.py` - Processing pipeline monitoring
- `comparison_cli.py` - Pipeline comparison tools
- `cache_performance_test.py` - Performance testing

## Script Patterns

```python
# ✅ Correct: Script structure with proper imports
#!/usr/bin/env python3
"""
Script description and usage.
"""
import sys
import os
import argparse
import logging
from pathlib import Path

# Add parent directory to path for AutoTaskTracker imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.config_manager import get_config

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--limit', type=int, default=100, help='Limit processing')
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Script logic here
        db = DatabaseManager()
        # ... rest of script
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        if args.verbose:
            raise
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## CLI Best Practices

- **Help text**: Provide clear --help documentation
- **Default values**: Use sensible defaults for all options
- **Validation**: Validate arguments before processing
- **Exit codes**: Use proper exit codes (0 for success, 1+ for errors)
- **Progress bars**: Use tqdm for long operations

## Processing Scripts Guidelines

- **Batch size**: Process data in configurable batches
- **Resume capability**: Allow resuming interrupted operations
- **Dry run mode**: Provide --dry-run option for testing
- **Statistics**: Report processing statistics at completion
- **Resource monitoring**: Monitor memory and CPU usage

## Integration with Main System

- **Database access**: Always use DatabaseManager
- **Configuration**: Read from AutoTaskTracker config
- **Logging**: Use project logging standards
- **Error handling**: Integrate with project error handling patterns

## Script Testing

- Test scripts with various argument combinations
- Verify error handling with invalid inputs
- Test interrupt handling (Ctrl+C)
- Validate output formats and statistics
- Test with missing dependencies