#!/usr/bin/env python3
"""
Fix all large code blocks in documentation by replacing with source references.
"""
import re
from pathlib import Path

def fix_code_blocks_in_file(file_path: Path, method_mappings: dict = None):
    """Fix large code blocks in a single file."""
    if not file_path.exists():
        return False
    
    content = file_path.read_text()
    original_content = content
    
    # Pattern to match code blocks
    code_block_pattern = r'```(?:python)?\n(.*?)\n```'
    
    def replace_code_block(match):
        code = match.group(1)
        lines = code.split('\n')
        
        # Skip small code blocks (<=20 lines)
        if len(lines) <= 20:
            return match.group(0)
        
        # For large blocks, try to identify and replace
        if method_mappings:
            for method_name, info in method_mappings.items():
                if method_name in code:
                    preview = '\n'.join(lines[:3])
                    if preview.strip():
                        return f"```python\n{preview}\n    # ... (see source for full implementation)\n```\n\n[View source: {info['description']}](../../{info['file']})"
        
        # Default replacement for unidentified large blocks
        preview = '\n'.join(lines[:3])
        return f"```python\n{preview}\n    # ... (truncated - see source files for full implementation)\n```"
    
    # Apply replacements
    content = re.sub(code_block_pattern, replace_code_block, content, flags=re.DOTALL)
    
    if content != original_content:
        file_path.write_text(content)
        return True
    return False

def main():
    """Fix code blocks in all problematic documentation files."""
    docs_dir = Path(__file__).parent.parent / "docs"
    
    # Method mappings for specific files
    core_methods_mappings = {
        "def semantic_search": {
            "file": "autotasktracker/ai/embeddings_search.py",
            "description": "Semantic search implementation"
        },
        "def cosine_similarity": {
            "file": "autotasktracker/ai/embeddings_search.py", 
            "description": "Cosine similarity calculation"
        },
        "def extract_task": {
            "file": "autotasktracker/core/task_extractor.py",
            "description": "Task extraction logic"
        },
        "def categorize": {
            "file": "autotasktracker/core/categorizer.py",
            "description": "Activity categorization"
        },
        "def get_task_from_vlm": {
            "file": "autotasktracker/core/categorizer.py",
            "description": "VLM-based task extraction"
        },
        "def process_image": {
            "file": "autotasktracker/ai/vlm_processor.py",
            "description": "VLM image processing"
        }
    }
    
    vlm_analysis_mappings = {
        "class VLMProcessor": {
            "file": "autotasktracker/ai/vlm_processor.py",
            "description": "VLM processor class"
        }
    }
    
    # Files to fix with their specific mappings
    files_to_fix = [
        (docs_dir / "guides" / "CORE_METHODS_DETAILED.md", core_methods_mappings),
        (docs_dir / "features" / "VLM_ANALYSIS.md", vlm_analysis_mappings),
        (docs_dir / "architecture" / "ARCHITECTURE.md", None),
        (docs_dir / "archive" / "CLAUDE_LEGACY.md", None),
    ]
    
    fixed_count = 0
    for file_path, mappings in files_to_fix:
        if file_path.exists():
            if fix_code_blocks_in_file(file_path, mappings):
                print(f"✅ Fixed code blocks in {file_path.name}")
                fixed_count += 1
            else:
                print(f"ℹ️  No large code blocks found in {file_path.name}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n🎉 Fixed {fixed_count} documentation files")

if __name__ == "__main__":
    main()