"""Test documentation structure and organization."""
import logging
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)


class TestDocumentationStructure:
    """Test for proper documentation structure and organization."""
    
    @property
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent.parent
    
    @property
    def docs_dir(self):
        """Get docs directory"""
        return self.project_root / "docs"
        
    def get_all_docs(self):
        """Get all markdown files in docs directory"""
        return list(self.docs_dir.rglob("*.md"))
    
    def test_documentation_structure(self):
        """Test that docs follow the established structure"""
        allowed_structure = {
            'README.md': 'Root navigation file',
            'architecture/': 'Technical architecture docs',
            'features/': 'Feature-specific documentation', 
            'guides/': 'User guides and tutorials',
            'archive/': 'Historical documentation (minimize)'
        }
        
        # Check all files are in proper directories
        misplaced_files = []
        for doc_path in self.get_all_docs():
            relative_path = doc_path.relative_to(self.docs_dir)
            parts = relative_path.parts
            
            # Check if it's a root file
            if len(parts) == 1:
                if parts[0] not in allowed_structure:
                    misplaced_files.append(f"{parts[0]} in root (move to appropriate subfolder)")
            # Check if it's in an allowed directory
            elif parts[0] not in [d.rstrip('/') for d in allowed_structure if d.endswith('/')]:
                misplaced_files.append(f"{relative_path} in unknown directory '{parts[0]}'")
        
        assert not misplaced_files, f"Misplaced documentation:\n" + "\n".join(misplaced_files)
    
    def test_required_documentation_exists(self):
        """Test that essential documentation exists"""
        required_docs = {
            'README.md': 'Main documentation index',
            'architecture/CODEBASE_DOCUMENTATION.md': 'Primary technical reference',
            'guides/FEATURE_MAP.md': 'Feature-to-file mapping'
        }
        
        missing_docs = []
        for doc_path, description in required_docs.items():
            full_path = self.docs_dir / doc_path
            if not full_path.exists():
                missing_docs.append(f"{doc_path}: {description}")
        
        assert not missing_docs, f"Missing required documentation:\n" + "\n".join(missing_docs)
    
    def test_documentation_size_limits(self):
        """Test that individual docs aren't too large (sign of needing split)"""
        size_limits = {
            'planning/': 1000,  # Planning docs can be longer
            'architecture/': 800,  # Architecture docs can be detailed
            'default': 500  # Most docs should be concise
        }
        
        oversized_docs = []
        for doc_path in self.get_all_docs():
            content = doc_path.read_text()
            line_count = len(content.split('\n'))
            
            # Determine limit based on directory
            limit = size_limits['default']
            for dir_name, dir_limit in size_limits.items():
                if dir_name in str(doc_path):
                    limit = dir_limit
                    break
            
            if line_count > limit:
                oversized_docs.append(
                    f"{doc_path.relative_to(self.docs_dir)}: {line_count} lines (limit: {limit})"
                )
        
        # Warning only - don't fail the test
        if oversized_docs:
            logger.info("Large documentation files that might need splitting:")
            for doc in oversized_docs:
                logger.info(f"  {doc}")
    
    def test_consistent_naming_conventions(self):
        """Test that documentation follows consistent naming"""
        issues = []
        
        for doc_path in self.get_all_docs():
            filename = doc_path.stem
            
            # Check for inconsistent naming patterns
            if filename.lower() != filename and filename.upper() != filename:
                # Mixed case is OK for some files
                import re
                if not re.match(r'^[A-Z]+(_[A-Z]+)*$', filename):  # CONSTANT_CASE
                    if not re.match(r'^README', filename):  # README exception
                        issues.append(f"{doc_path.name}: inconsistent casing (use CONSTANT_CASE or lowercase)")
            
            # Check for problematic names
            if any(term in filename.lower() for term in ['temp', 'tmp', 'test', 'draft', 'wip']):
                issues.append(f"{doc_path.name}: contains temporary/draft terminology")
            
            import re
            if re.search(r'_v\d+|_\d+|_final|_new|_old', filename.lower()):
                issues.append(f"{doc_path.name}: contains version suffix (use git for versioning)")
        
        assert not issues, f"Naming convention issues:\n" + "\n".join(issues)
    
    def test_no_orphaned_documentation(self):
        """Test that documentation references existing code/features"""
        orphaned_docs = []
        
        # Check feature documentation
        features_dir = self.docs_dir / "features"
        if features_dir.exists():
            for feature_doc in features_dir.glob("*.md"):
                # Extract feature name from filename
                feature_name = feature_doc.stem.lower()
                
                # Check if corresponding code exists
                code_indicators = [
                    self.project_root / "autotasktracker" / feature_name,
                    self.project_root / "autotasktracker" / "features" / feature_name,
                    self.project_root / "scripts" / feature_name,
                ]
                
                if not any(path.exists() for path in code_indicators):
                    # Check if the feature is mentioned in any Python files
                    found_in_code = False
                    for py_file in self.project_root.rglob("*.py"):
                        try:
                            if feature_name in py_file.read_text(encoding='utf-8', errors='ignore').lower():
                                found_in_code = True
                                break
                        except (UnicodeDecodeError, OSError):
                            # Skip files that can't be read as text
                            continue
                    
                    if not found_in_code:
                        orphaned_docs.append(f"features/{feature_doc.name}: No corresponding code found")
        
        if orphaned_docs:
            logger.warning("Potentially orphaned documentation:")
            for doc in orphaned_docs:
                logger.warning(f"  {doc}")