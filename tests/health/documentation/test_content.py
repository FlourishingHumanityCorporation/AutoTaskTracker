"""Test documentation content quality."""
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
import pytest

from . import safe_read_text

logger = logging.getLogger(__name__)


class TestDocumentationContent:
    """Test for documentation content quality and standards."""
    
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
                
            content = safe_read_text(doc_path).lower()
            for pattern in outdated_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    outdated_docs.append(f"{doc_path.relative_to(self.docs_dir)}: contains '{pattern}'")
                    break
        
        assert not outdated_docs, f"Found outdated terminology:\n" + "\n".join(outdated_docs)
    
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
                
            content = safe_read_text(doc_path)
            first_lines = '\n'.join(content.split('\n')[:10])  # Check first 10 lines
            
            for pattern in announcement_patterns:
                if re.search(pattern, first_lines, re.IGNORECASE | re.MULTILINE):
                    announcement_docs.append(
                        f"{doc_path.relative_to(self.docs_dir)}: looks like announcement (pattern: {pattern})"
                    )
                    break
        
        assert not announcement_docs, f"Found announcement-style docs:\n" + "\n".join(announcement_docs)
    
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
                
            content = safe_read_text(doc_path)
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
            logger.warning("Documentation with informal language:")
            for doc in informal_docs:
                logger.warning(f"  {doc}")
    
    def test_no_code_snippets_in_docs(self):
        """Test that docs don't contain large code snippets (maintenance nightmare)"""
        code_block_pattern = r'```[\s\S]*?```'
        
        docs_with_code = []
        for doc_path in self.get_all_docs():
            content = safe_read_text(doc_path)
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
    
    def test_measured_technical_language(self):
        """Test that documentation uses measured, technical language"""
        superlative_patterns = [
            r'\b(perfect|flawless|best|amazing|excellent)\b',
            r'\b(revolutionary|game-changing|cutting-edge)\b',
            r'\b(blazing fast|lightning fast|super fast)\b',
            r'\b(powerful|robust|enterprise-grade)\b',
            r'\b(seamless|effortless|magical)\b',
        ]
        
        # Allowed contexts where superlatives might be acceptable
        allowed_contexts = [
            'best practice',
            'excellent documentation',
            'powerful feature',
            'robust error handling'
        ]
        
        docs_with_superlatives = []
        for doc_path in self.get_all_docs():
            if 'archive' in str(doc_path):
                continue
                
            content = safe_read_text(doc_path)
            found_superlatives = []
            
            for pattern in superlative_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Check if it's in an allowed context
                    context = content[max(0, match.start()-20):match.end()+20].lower()
                    if not any(allowed in context for allowed in allowed_contexts):
                        found_superlatives.append(match.group(0))
            
            if found_superlatives:
                docs_with_superlatives.append(
                    f"{doc_path.relative_to(self.docs_dir)}: superlatives ({', '.join(set(found_superlatives))})"
                )
        
        if docs_with_superlatives:
            logger.warning("Documentation with superlative language:")
            for doc in docs_with_superlatives[:5]:
                logger.warning(f"  {doc}")
            logger.warning("Use measured, descriptive language instead")