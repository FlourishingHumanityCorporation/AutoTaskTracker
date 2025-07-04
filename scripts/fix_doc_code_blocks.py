#!/usr/bin/env python3
"""
Fix large code blocks in documentation by replacing them with links to source files.
"""
import re
from pathlib import Path

# Mapping of code snippets to their source locations
CODE_REPLACEMENTS = {
    # CORE_METHODS_DETAILED.md
    "def semantic_search": {
        "file": "autotasktracker/ai/embeddings_search.py",
        "line": 89,
        "description": "Semantic search implementation"
    },
    "def cosine_similarity": {
        "file": "autotasktracker/ai/embeddings_search.py", 
        "line": 56,
        "description": "Cosine similarity calculation"
    },
    "def extract_task": {
        "file": "autotasktracker/core/task_extractor.py",
        "line": 109,
        "description": "Task extraction logic"
    },
    "def categorize": {
        "file": "autotasktracker/core/categorizer.py",
        "line": 45,
        "description": "Activity categorization"
    },
    "def get_task_from_vlm": {
        "file": "autotasktracker/core/categorizer.py",
        "line": 186,
        "description": "VLM-based task extraction"
    },
    "def process_image": {
        "file": "autotasktracker/ai/vlm_processor.py",
        "line": 169,
        "description": "VLM image processing"
    },
    "def search_similar_activities": {
        "file": "autotasktracker/dashboards/task_board.py",
        "line": None,
        "description": "Similar activity search"
    }
}

def fix_large_code_blocks(file_path: Path):
    """Replace large code blocks with source links."""
    content = file_path.read_text()
    original_content = content
    
    # Find all code blocks
    code_block_pattern = r'```python\n(.*?)\n```'
    
    def replace_code_block(match):
        code = match.group(1)
        lines = code.split('\n')
        
        # Skip if small code block
        if len(lines) <= 20:
            return match.group(0)
        
        # Try to identify the code
        for key, info in CODE_REPLACEMENTS.items():
            if key in code:
                if info["line"]:
                    link = f"[View source: {info['description']}](../../{info['file']}#L{info['line']})"
                else:
                    link = f"[View source: {info['description']}](../../{info['file']})"
                
                # Keep first few lines as preview
                preview = '\n'.join(lines[:5])
                if len(lines) > 5:
                    preview += '\n    # ... (see source file for full implementation)'
                
                return f"```python\n{preview}\n```\n\n{link}"
        
        # If we can't identify it, just add a note
        preview = '\n'.join(lines[:5])
        return f"```python\n{preview}\n    # ... (truncated for readability)\n```"
    
    # Replace all large code blocks
    content = re.sub(code_block_pattern, replace_code_block, content, flags=re.DOTALL)
    
    if content != original_content:
        file_path.write_text(content)
        return True
    return False

def main():
    """Fix code blocks in all documentation files."""
    docs_dir = Path(__file__).parent.parent / "docs"
    
    files_to_fix = [
        docs_dir / "guides" / "CORE_METHODS_DETAILED.md",
        docs_dir / "features" / "VLM_ANALYSIS.md",
        docs_dir / "architecture" / "ARCHITECTURE.md"
    ]
    
    for file_path in files_to_fix:
        if file_path.exists():
            if fix_large_code_blocks(file_path):
                print(f"✅ Fixed code blocks in {file_path.name}")
            else:
                print(f"ℹ️  No changes needed in {file_path.name}")

if __name__ == "__main__":
    main()