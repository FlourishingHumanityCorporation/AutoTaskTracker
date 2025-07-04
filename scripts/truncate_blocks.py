#!/usr/bin/env python3
import re
from pathlib import Path

def truncate_large_blocks(file_path):
    content = file_path.read_text()
    original = content
    
    def replace_block(match):
        block = match.group(0)
        lines = block.count('\n')
        if lines > 20:
            lines_list = block.split('\n')
            opener = lines_list[0]
            first_lines = lines_list[1:4] if len(lines_list) > 1 else []
            
            if first_lines:
                preview = '\n'.join(first_lines)
                return f'{opener}\n{preview}\n    # ... (truncated - see source files)\n```'
            else:
                return f'{opener}\n    # ... (code block truncated)\n```'
        return block
    
    content = re.sub(r'```[\s\S]*?```', replace_block, content)
    
    if content != original:
        file_path.write_text(content)
        return True
    return False

docs_dir = Path('docs')
files = [
    'REFACTORING_COMPLETE.md',
    'archive/CLAUDE_LEGACY.md', 
    'features/VLM_ANALYSIS.md',
    'architecture/ARCHITECTURE.md',
    'guides/CORE_METHODS_DETAILED.md'
]

for file_name in files:
    file_path = docs_dir / file_name
    if file_path.exists() and truncate_large_blocks(file_path):
        print(f'✅ Fixed {file_name}')
    else:
        print(f'ℹ️  No changes for {file_name}')