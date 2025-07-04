"""
Test suite for documentation quality and organization.
Prevents documentation rot and maintains high standards.
"""

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
import pytest


class TestDocumentationHealth:
    """Tests for documentation quality, organization, and relevance"""
    
    @property
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent
    
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
                    similarity = len(common_lines) / max(len(lines), len(other_lines))
                    if similarity > 0.5:
                        duplicates.append(f"{doc_path.name} duplicates {other_path.name} ({similarity:.0%})")
            
            content_hashes[doc_path] = lines
        
        assert not duplicates, f"Found duplicate content:\n" + "\n".join(duplicates)
    
    def test_no_outdated_terminology(self):
        """Test for outdated terms and references"""
        outdated_patterns = [
            # Outdated status indicators
            r'as of (January|February|March|April|May|June|July|August|September|October|November|December) 202[0-4]',
            r'(IMPLEMENTED|COMPLETE|DONE|FINISHED).*\b202[0-4]\b',
            r'current status.*\b202[0-4]\b',
            
            # Victory lap language
            r'we (did it|succeeded|accomplished|finished)',
            r'(successfully implemented|now complete|fully functional)',
            r'✅.*complete[d]?\s*!+',
            
            # Snapshot-in-time statistics
            r'\d+\+?\s*(screenshots?|images?)\s*(captured|processed|analyzed)',
            r'coverage:\s*\d+\.?\d*%',
            r'total:\s*\d+\s*(files?|screenshots?|tasks?)',
            
            # Old version references
            r'v\d+\.\d+\.\d+',
            r'\b(alpha|beta|release candidate)\b\s*\d*',
            r'\brc\d+\b',  # rc1, rc2, etc.
            
            # TODO/FIXME that are likely stale
            r'TODO:.*\b202[0-4]\b',
            r'FIXME:.*\b202[0-4]\b',
        ]
        
        outdated_docs = []
        for doc_path in self.get_all_docs():
            # Skip archive folder - it's allowed to have outdated content
            if 'archive' in str(doc_path):
                continue
                
            content = doc_path.read_text().lower()
            for pattern in outdated_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    outdated_docs.append(f"{doc_path.relative_to(self.docs_dir)}: contains '{pattern}'")
                    break
        
        assert not outdated_docs, f"Found outdated terminology:\n" + "\n".join(outdated_docs)
    
    def test_documentation_structure(self):
        """Test that docs follow the established structure"""
        allowed_structure = {
            'README.md': 'Root navigation file',
            'CONSOLIDATION_NOTES.md': 'Organization notes',
            'CLEANUP_SUMMARY.md': 'Cleanup tracking',
            'architecture/': 'Technical architecture docs',
            'features/': 'Feature-specific documentation',
            'guides/': 'User guides and tutorials',
            'design/': 'UI/UX specifications',
            'planning/': 'Future plans and ideas',
            'archive/': 'Historical documentation'
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
    
    def test_no_announcement_style_docs(self):
        """Test for announcement/blog-style documentation that should be removed"""
        announcement_patterns = [
            r'^#\s*🚀.*complete[d]?!*$',
            r'^#\s*✅.*ready.*production',
            r'^#\s*🎉',
            r'we\'re (proud|excited|happy) to',
            r'introducing|announcement|we are pleased',
            r'what\'s new|release notes|changelog',
            r'(shipped|launched|deployed|went live)',
        ]
        
        announcement_docs = []
        for doc_path in self.get_all_docs():
            if 'archive' in str(doc_path):
                continue
                
            content = doc_path.read_text()
            first_lines = '\n'.join(content.split('\n')[:10])  # Check first 10 lines
            
            for pattern in announcement_patterns:
                if re.search(pattern, first_lines, re.IGNORECASE | re.MULTILINE):
                    announcement_docs.append(
                        f"{doc_path.relative_to(self.docs_dir)}: looks like announcement (pattern: {pattern})"
                    )
                    break
        
        assert not announcement_docs, f"Found announcement-style docs:\n" + "\n".join(announcement_docs)
    
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
            print(f"\n⚠️  Large documentation files that might need splitting:")
            for doc in oversized_docs:
                print(f"  {doc}")
    
    def test_no_code_snippets_in_docs(self):
        """Test that docs don't contain large code snippets (maintenance nightmare)"""
        code_block_pattern = r'```[\s\S]*?```'
        
        docs_with_code = []
        for doc_path in self.get_all_docs():
            content = doc_path.read_text()
            code_blocks = re.findall(code_block_pattern, content)
            
            # Check for large code blocks (>20 lines)
            for block in code_blocks:
                lines = block.count('\n')
                if lines > 20:
                    docs_with_code.append(
                        f"{doc_path.relative_to(self.docs_dir)}: contains {lines}-line code block"
                    )
        
        assert not docs_with_code, (
            f"Found large code blocks in documentation (maintenance risk):\n" + 
            "\n".join(docs_with_code) +
            "\nConsider linking to actual code files instead"
        )
    
    def test_consistent_naming_conventions(self):
        """Test that documentation follows consistent naming"""
        issues = []
        
        for doc_path in self.get_all_docs():
            filename = doc_path.stem
            
            # Check for inconsistent naming patterns
            if filename.lower() != filename and filename.upper() != filename:
                # Mixed case is OK for some files
                if not re.match(r'^[A-Z]+(_[A-Z]+)*$', filename):  # CONSTANT_CASE
                    if not re.match(r'^README', filename):  # README exception
                        issues.append(f"{doc_path.name}: inconsistent casing (use CONSTANT_CASE or lowercase)")
            
            # Check for problematic names
            if any(term in filename.lower() for term in ['temp', 'tmp', 'test', 'draft', 'wip']):
                issues.append(f"{doc_path.name}: contains temporary/draft terminology")
            
            if re.search(r'_v\d+|_\d+|_final|_new|_old', filename.lower()):
                issues.append(f"{doc_path.name}: contains version suffix (use git for versioning)")
        
        assert not issues, f"Naming convention issues:\n" + "\n".join(issues)
    
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
    
    def test_no_personal_or_informal_language(self):
        """Test for overly informal or personal language in docs"""
        informal_patterns = [
            r'\b(I|I\'m|I\'ve|me|my)\b',  # First person
            r'\b(we\'re|we\'ve|we\'ll)\b',  # First person plural (except "we recommend")
            r'\b(gonna|wanna|gotta|kinda|sorta)\b',  # Informal contractions
            r'!{2,}',  # Multiple exclamation marks
            r'\.{4,}',  # Excessive ellipsis
            r'\b(awesome|amazing|fantastic|incredible)\b',  # Hyperbole
            r'\b(obviously|clearly|simply|just)\b',  # Condescending terms
            r':\)|;\)|:D|:P',  # Emoticons
            r'\b(lol|omg|wtf|btw)\b',  # Internet slang
        ]
        
        informal_docs = []
        for doc_path in self.get_all_docs():
            # Skip planning docs which might be more informal
            if 'planning' in str(doc_path) or 'archive' in str(doc_path):
                continue
                
            content = doc_path.read_text()
            found_patterns = []
            
            for pattern in informal_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Allow "we recommend" pattern
                    if pattern == r'\b(we\'re|we\'ve|we\'ll)\b' and 'we recommend' in content.lower():
                        continue
                    found_patterns.append(pattern)
            
            if found_patterns:
                informal_docs.append(
                    f"{doc_path.relative_to(self.docs_dir)}: informal language ({', '.join(found_patterns)})"
                )
        
        # Warning only for minor infractions
        if informal_docs:
            print(f"\n⚠️  Documentation with informal language:")
            for doc in informal_docs:
                print(f"  {doc}")
    
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
            print(f"\n⚠️  Potentially stale documentation:")
            for doc in potentially_stale:
                print(f"  {doc}")


def main():
    """Run documentation health checks independently"""
    test = TestDocumentationHealth()
    
    print("🔍 Documentation Health Check")
    print("=" * 50)
    
    tests = [
        ("No duplicate content", test.test_no_duplicate_content),
        ("No outdated terminology", test.test_no_outdated_terminology),
        ("Proper structure", test.test_documentation_structure),
        ("No announcements", test.test_no_announcement_style_docs),
        ("Size limits", test.test_documentation_size_limits),
        ("No large code blocks", test.test_no_code_snippets_in_docs),
        ("Naming conventions", test.test_consistent_naming_conventions),
        ("Required docs exist", test.test_required_documentation_exists),
        ("Professional language", test.test_no_personal_or_informal_language),
        ("Freshness check", test.test_documentation_freshness),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {test_name}: Error - {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed}")
    
    if failed > 0:
        print("\n💡 Run with pytest for detailed output:")
        print("   pytest tests/test_documentation_health.py -v")
        exit(1)


if __name__ == "__main__":
    main()