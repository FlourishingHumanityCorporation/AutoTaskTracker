#!/usr/bin/env python3
"""Document repository interfaces before refactoring."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.dashboards.data.repositories import BaseRepository, TaskRepository, ActivityRepository, MetricsRepository
import inspect

def document_class_interface(cls, name):
    print(f'\n## {name}')
    print(f'**Purpose**: {cls.__doc__ or "No docstring available"}')
    
    # Get all public methods
    public_methods = []
    private_methods = []
    
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('__'):
            try:
                sig = str(inspect.signature(attr))
                method_info = f'- `{attr_name}{sig}`'
            except:
                method_info = f'- `{attr_name}(...)`'
            
            if attr_name.startswith('_'):
                private_methods.append(method_info)
            else:
                public_methods.append(method_info)
    
    if public_methods:
        print('**Public Methods**:')
        for method in sorted(public_methods):
            print(method)
    
    if private_methods:
        print('**Private Methods**:')
        for method in sorted(private_methods[:10]):  # Limit to first 10
            print(method)
        if len(private_methods) > 10:
            print(f'... and {len(private_methods) - 10} more private methods')

def main():
    print('# Repository Interface Documentation')
    print('Current interfaces that must be preserved during refactoring.')
    print(f'Generated on: {os.popen("date").read().strip()}')
    
    document_class_interface(BaseRepository, 'BaseRepository')
    document_class_interface(TaskRepository, 'TaskRepository') 
    document_class_interface(ActivityRepository, 'ActivityRepository')
    document_class_interface(MetricsRepository, 'MetricsRepository')
    
    print('\n## Import Statements')
    print('```python')
    print('from autotasktracker.dashboards.data.repositories import (')
    print('    BaseRepository, TaskRepository, ActivityRepository, MetricsRepository')
    print(')')
    print('```')
    
    print('\n## Usage Examples')
    print('```python')
    print('# Current usage patterns that must continue working:')
    print('task_repo = TaskRepository()')
    print('metrics_repo = MetricsRepository()')
    print('activity_repo = ActivityRepository()')
    print('')
    print('# Performance stats access')
    print('stats = task_repo.get_performance_stats()')
    print('')
    print('# Cache management')
    print('task_repo.invalidate_cache()')
    print('```')

if __name__ == "__main__":
    main()