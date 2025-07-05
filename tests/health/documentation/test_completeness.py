"""Test documentation completeness and anti-patterns."""
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
import pytest

logger = logging.getLogger(__name__)


class TestDocumentationCompleteness:
    """Test for documentation completeness and avoiding anti-patterns."""
    
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
    
    def test_no_duplicate_content(self):
        """Test that documentation doesn't have significant duplication"""
        docs = self.get_all_docs()
        content_hashes = {}
        duplicates = []
        
        for doc_path in docs:
            content = doc_path.read_text()
            # Extract meaningful content (ignore headers and whitespace)
            lines = [line.strip() for line in content.split('\n') 
                    if line.strip() and not line.startswith('#')]
            
            # Check for files with >50% similar content
            for other_path, other_lines in content_hashes.items():
                if doc_path != other_path:
                    common_lines = set(lines) & set(other_lines)
                    similarity = len(common_lines) / max(len(lines), len(other_lines)) if max(len(lines), len(other_lines)) > 0 else 0
                    if similarity > 0.5:
                        duplicates.append(f"{doc_path.name} duplicates {other_path.name} ({similarity:.0%})")
            
            content_hashes[doc_path] = lines
        
        assert not duplicates, f"Found duplicate content:\n" + "\n".join(duplicates)
    
    def test_no_completion_status_docs(self):
        """Test for completion/status documents that should be deleted"""
        # Check filenames first - be more specific to avoid false positives
        completion_filename_patterns = [
            r'.*_complete[d]?\.md$',  # task_completed.md but not IMPLEMENTATION_COMPLETE.md
            r'.*_fix(ed|es)\.md$',   # bugs_fixed.md 
            r'.*_summary\.md$',      # work_summary.md but not UNIT_TEST_SUMMARY.md
            r'.*_status\.md$',       # project_status.md
            r'.*cleanup_.*\.md$',    # cleanup_notes.md
            r'.*consolidation_.*\.md$', # consolidation_notes.md
            r'.*_final\.md$',        # notes_final.md
            r'.*everything_.*\.md$', # everything_done.md
        ]
        
        # Exclude legitimate documentation types
        legitimate_patterns = [
            r'security.*\.md$',      # Security documentation
            r'.*migration.*\.md$',   # Migration guides
            r'.*refactor.*\.md$',    # Refactoring documentation  
            r'.*_guide\.md$',        # User guides
            r'.*_reference\.md$',    # Reference documentation
            r'unit_test_.*\.md$',    # Test documentation
            r'implementation_.*\.md$' # Implementation documentation
        ]
        
        completion_content_patterns = [
            r'everything is now fix(ed|es)',
            r'all bugs.*complete[d]?',
            r'temporary.*fix(ed|es).*complete[d]?',
            r'what we just (did|accomplished|fixed)',
            r'summary of emergency fix(ed|es)',
            r'(immediate|quick).*cleanup',
        ]
        
        problematic_docs = []
        for doc_path in self.get_all_docs():
            if 'archive' in str(doc_path):
                continue
                
            filename = doc_path.name.lower()
            relative_path = str(doc_path.relative_to(self.docs_dir)).lower()
            
            # Skip legitimate documentation types
            is_legitimate = False
            for pattern in legitimate_patterns:
                if re.search(pattern, relative_path, re.IGNORECASE):
                    is_legitimate = True
                    break
            
            if is_legitimate:
                continue
            
            # Check filename patterns for problematic docs
            for pattern in completion_filename_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    problematic_docs.append(
                        f"{doc_path.relative_to(self.docs_dir)}: completion/status filename ({pattern})"
                    )
                    break
            
            # Check content patterns for temporary/completion language
            content = doc_path.read_text().lower()
            for pattern in completion_content_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    problematic_docs.append(
                        f"{doc_path.relative_to(self.docs_dir)}: completion/status content ({pattern})"
                    )
                    break
        
        assert not problematic_docs, f"Found completion/status docs (DELETE don't archive):\n" + "\n".join(problematic_docs)
    
    def test_no_process_documentation(self):
        """Test for process documentation that should be deleted"""
        process_patterns = [
            r'deployment.*guide.*refactor',
            r'migration.*guide',
            r'refactor(ing|ed).*process',
            r'how.*cleanup',
            r'consolidation.*process',
            r'what.*removed',
            r'before.*after.*comparison',
            r'step.*by.*step.*migration',
        ]
        
        process_docs = []
        for doc_path in self.get_all_docs():
            if 'archive' in str(doc_path):
                continue
                
            content = doc_path.read_text().lower()
            
            # Check if it's primarily about process rather than actual use
            process_indicators = 0
            total_indicators = len(process_patterns)
            
            for pattern in process_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    process_indicators += 1
            
            # If more than 30% of process patterns match, it's likely process documentation
            if process_indicators > 0 and total_indicators > 0 and process_indicators / total_indicators > 0.3:
                process_docs.append(
                    f"{doc_path.relative_to(self.docs_dir)}: appears to be process documentation"
                )
        
        # This is a warning only - manual review needed for process docs
        if process_docs:
            logger.info("Potential process documentation (review for deletion):")
            for doc in process_docs:
                logger.info(f"  {doc}")
    
    def test_documentation_freshness(self):
        """Test that docs have been updated recently (catch stale docs)"""
        # This is a heuristic - docs not modified in 6 months might be stale
        stale_threshold = timedelta(days=180)
        now = datetime.now()
        
        potentially_stale = []
        for doc_path in self.get_all_docs():
            # Skip archive - it's meant to be old
            if 'archive' in str(doc_path):
                continue
                
            # Check file modification time
            mtime = datetime.fromtimestamp(doc_path.stat().st_mtime)
            age = now - mtime
            
            if age > stale_threshold:
                potentially_stale.append(
                    f"{doc_path.relative_to(self.docs_dir)}: "
                    f"not modified in {age.days} days"
                )
        
        # Just warn, don't fail
        if potentially_stale:
            logger.info("Potentially stale documentation:")
            for doc in potentially_stale[:5]:
                logger.info(f"  {doc}")
            if len(potentially_stale) > 5:
                logger.info(f"  ... and {len(potentially_stale) - 5} more")
    
    def test_documentation_coverage(self):
        """Test that major features have documentation"""
        # Major features that should be documented
        expected_features = [
            'task_extraction',
            'ocr',
            'embeddings',
            'dashboards',
            'pensieve_integration',
            'vlm',
            'configuration',
        ]
        
        missing_docs = []
        for feature in expected_features:
            # Check if feature is documented anywhere
            documented = False
            for doc_path in self.get_all_docs():
                content = doc_path.read_text().lower()
                if feature.replace('_', ' ') in content or feature in content:
                    documented = True
                    break
            
            if not documented:
                missing_docs.append(f"{feature}: No documentation found")
        
        if missing_docs:
            logger.warning("Features without documentation:")
            for feature in missing_docs:
                logger.warning(f"  {feature}")
    
    def test_no_root_clutter(self):
        """Test that docs root directory isn't cluttered"""
        allowed_root_files = ['README.md', 'CONTRIBUTING.md', 'CHANGELOG.md']
        
        root_files = [f for f in self.docs_dir.iterdir() if f.is_file()]
        clutter_files = []
        
        for file_path in root_files:
            if file_path.name not in allowed_root_files:
                # Suggest where it should go
                suggestion = "archive/"
                if 'feature' in file_path.name.lower():
                    suggestion = "features/"
                elif 'guide' in file_path.name.lower() or 'how' in file_path.name.lower():
                    suggestion = "guides/"
                elif 'architecture' in file_path.name.lower() or 'design' in file_path.name.lower():
                    suggestion = "architecture/"
                
                clutter_files.append(f"{file_path.name} → {suggestion}")
        
        assert not clutter_files, f"Root directory clutter (move to subdirs):\n" + "\n".join(clutter_files)