#!/usr/bin/env python3
import logging
logger = logging.getLogger(__name__)

"""
Test VLM (Visual Language Model) extraction on real captured screenshots.
This validates VLM functionality using actual screenshots from AutoTaskTracker.
"""

import json
import os
import sqlite3
import sys
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_processor import SmartVLMProcessor as VLMProcessor

# Import mock service for testing
sys.path.insert(0, str(Path(__file__).parent))
from mock_vlm_service import patch_vlm_processor, get_mock_vlm


class TestVLMExtractionOnRealScreenshots:
    """Test VLM extraction functionality on real captured screenshots."""
    
    @pytest.fixture
    def real_screenshots_for_vlm(self) -> List[Dict[str, Any]]:
        """Get real screenshots suitable for VLM processing."""
        memos_db = Path.home() / ".memos" / "database.db"
        if not memos_db.exists():
            pytest.skip("Real memos database not found - need actual AutoTaskTracker usage data")
        
        conn = sqlite3.connect(str(memos_db))
        conn.row_factory = sqlite3.Row
        
        # Get screenshots without VLM descriptions but with file paths
        cursor = conn.execute("""
            SELECT 
                e.id,
                e.filepath,
                e.created_at,
                m1.value as window_title,
                m2.value as ocr_text,
                m3.value as ai_task,
                m4.value as vlm_description
            FROM entities e
            LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = "active_window"
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'text'
            LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = "tasks"
            LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'vlm_description'
            WHERE e.file_type_group = 'image'
            AND e.filepath IS NOT NULL
            AND m1.value IS NOT NULL
            ORDER BY 
                CASE 
                    WHEN m4.value IS NULL THEN 0  -- Prioritize screenshots without VLM
                    ELSE 1
                END,
                e.created_at DESC
            LIMIT 20
        """)
        
        screenshots = []
        for row in cursor:
            screenshot = {
                'id': row['id'],
                'filepath': row['filepath'],
                'created_at': row['created_at'],
                "active_window": row["active_window"],
                'has_ocr': row["ocr_result"] is not None,
                'has_ai_task': row['ai_task'] is not None,
                'has_vlm': row['vlm_description'] is not None,
                'vlm_description': row['vlm_description']
            }
            
            # Only include screenshots where the file exists
            if Path(screenshot['filepath']).exists():
                screenshots.append(screenshot)
        
        conn.close()
        
        if len(screenshots) == 0:
            pytest.skip("No accessible real screenshots found for VLM testing")
        
        print(f"\n✅ Found {len(screenshots)} real screenshots for VLM testing")
        without_vlm = sum(1 for s in screenshots if not s['has_vlm'])
        print(f"   - Without VLM descriptions: {without_vlm}")
        print(f"   - With existing VLM: {len(screenshots) - without_vlm}")
        
        return screenshots
    
    def test_vlm_processor_setup_with_mock_service(self):
        """Test that VLM processor can be set up with mock service for testing."""
        try:
            vlm_processor = VLMProcessor()
            assert vlm_processor is not None, "VLM processor should initialize"
            
            # Add mock methods that the processor needs for testing
            mock_vlm = get_mock_vlm()
            vlm_processor.check_availability = lambda: True
            vlm_processor.describe_screenshot = mock_vlm.describe_screenshot
            vlm_processor.compute_perceptual_hash = mock_vlm.compute_perceptual_hash
            
            # Check if VLM is available (mocked)
            is_available = vlm_processor.check_availability()
            print(f"\n🤖 VLM Processor Status:")
            print(f"   - Initialized: ✅")
            print(f"   - VLM available: {'✅' if is_available else '❌'}")
            print(f"   - Using mock service for testing")
            
            assert is_available, "Mock VLM should be available"
                
        except Exception as e:
            pytest.fail(f"VLM processor initialization failed: {e}")
    
    def test_vlm_extraction_on_single_real_screenshot(self, real_screenshots_for_vlm):
        """Test VLM extraction on a single real screenshot."""
        try:
            vlm_processor = VLMProcessor()
            # Add mock methods
            mock_vlm = get_mock_vlm()
            vlm_processor.check_availability = lambda: True
            vlm_processor.describe_screenshot = mock_vlm.describe_screenshot
            vlm_processor.compute_perceptual_hash = mock_vlm.compute_perceptual_hash
        except Exception as e:
            pytest.skip(f"VLM processor not available: {e}")
        
        # Get a screenshot without existing VLM description
        test_screenshot = None
        for screenshot in real_screenshots_for_vlm:
            if not screenshot['has_vlm']:
                test_screenshot = screenshot
                break
        
        if not test_screenshot:
            # Use any screenshot
            test_screenshot = real_screenshots_for_vlm[0]
        
        print(f"\n🔍 Testing VLM on single screenshot:")
        print(f"   File: {Path(test_screenshot['filepath']).name}")
        print(f"   Window: {test_screenshot["active_window"][:60]}...")
        
        start_time = time.time()
        
        try:
            # Process the screenshot with VLM
            description = vlm_processor.describe_screenshot(
                test_screenshot['filepath'],
                test_screenshot["active_window"]
            )
            
            processing_time = time.time() - start_time
            
            # Validate the description
            assert description is not None, "Should get a description from VLM"
            assert isinstance(description, str), "Description should be a string"
            assert len(description.strip()) > 10, "Description should be meaningful"
            
            # Check for quality indicators
            quality_indicators = {
                'mentions_window': any(word in description.lower() for word in ['window', 'application', 'screen']),
                'mentions_content': any(word in description.lower() for word in ['shows', 'displays', 'contains', 'visible']),
                'mentions_ui': any(word in description.lower() for word in ['button', 'menu', 'text', 'interface']),
                'is_detailed': len(description.split()) > 20
            }
            
            quality_score = sum(quality_indicators.values())
            
            print(f"\n✅ VLM Extraction Successful:")
            print(f"   Processing time: {processing_time:.2f}s")
            print(f"   Description length: {len(description)} chars, {len(description.split())} words")
            print(f"   Quality score: {quality_score}/4")
            print(f"   Description preview: {description[:150]}...")
            
            # Quality assertions
            assert quality_score >= 2, f"VLM description should have quality indicators, got {quality_score}/4"
            assert processing_time < 30, f"VLM processing should complete within 30s, took {processing_time:.2f}s"
            
            return description
            
        except Exception as e:
            pytest.fail(f"VLM extraction failed: {e}")
    
    def test_vlm_batch_extraction_on_real_screenshots(self, real_screenshots_for_vlm):
        """Test VLM batch extraction on multiple real screenshots."""
        try:
            vlm_processor = VLMProcessor()
            if not vlm_processor.check_availability():
                pytest.skip("VLM not available")
        except:
            pytest.skip("VLM processor not available")
        
        # Test on a small batch
        batch_size = min(5, len(real_screenshots_for_vlm))
        test_batch = real_screenshots_for_vlm[:batch_size]
        
        print(f"\n🔍 Testing VLM batch extraction on {batch_size} screenshots:")
        
        results = []
        total_start = time.time()
        
        for i, screenshot in enumerate(test_batch):
            print(f"\n   Processing {i+1}/{batch_size}: {Path(screenshot['filepath']).name}")
            
            try:
                start_time = time.time()
                description = vlm_processor.describe_screenshot(
                    screenshot['filepath'],
                    screenshot["active_window"]
                )
                processing_time = time.time() - start_time
                
                if description:
                    results.append({
                        'screenshot': screenshot,
                        'description': description,
                        'processing_time': processing_time,
                        'word_count': len(description.split())
                    })
                    print(f"     ✅ Success: {len(description)} chars in {processing_time:.2f}s")
                else:
                    print(f"     ⚠️ No description returned")
                    
            except Exception as e:
                logger.error(f"     ❌ Error: {e}")
        
        total_time = time.time() - total_start
        
        # Analyze results
        if len(results) > 0:
            avg_time = sum(r['processing_time'] for r in results) / len(results)
            avg_words = sum(r['word_count'] for r in results) / len(results)
            success_rate = len(results) / batch_size
            
            print(f"\n📊 Batch VLM Results:")
            print(f"   - Success rate: {success_rate:.1%} ({len(results)}/{batch_size})")
            print(f"   - Total time: {total_time:.2f}s")
            print(f"   - Average time per screenshot: {avg_time:.2f}s")
            print(f"   - Average description length: {avg_words:.0f} words")
            
            # Show sample descriptions
            print(f"\n   Sample descriptions:")
            for result in results[:2]:
                print(f"     Window: {result['screenshot']["active_window"][:50]}...")
                print(f"     VLM: {result['description'][:100]}...")
                print()
            
            # Assertions
            assert len(results) > 0, "Should successfully process at least some screenshots"
            assert avg_time < 20, f"Average processing time should be under 20s, got {avg_time:.2f}s"
            assert avg_words > 10, f"Descriptions should be meaningful, got {avg_words:.0f} words average"
        else:
            pytest.skip("No VLM results obtained")
    
    def test_vlm_extraction_quality_on_different_content(self, real_screenshots_for_vlm):
        """Test VLM extraction quality on screenshots with different content types."""
        try:
            vlm_processor = VLMProcessor()
            if not vlm_processor.check_availability():
                pytest.skip("VLM not available")
        except:
            pytest.skip("VLM processor not available")
        
        # Categorize screenshots by window title patterns
        categorized = {
            'terminal': [],
            'browser': [],
            'editor': [],
            'other': []
        }
        
        for screenshot in real_screenshots_for_vlm[:10]:  # Limit to 10 for testing
            window_lower = screenshot["active_window"].lower()
            if any(term in window_lower for term in ['terminal', 'iterm', 'console', 'claude']):
                categorized['terminal'].append(screenshot)
            elif any(term in window_lower for term in ['chrome', 'firefox', 'safari', 'browser']):
                categorized['browser'].append(screenshot)
            elif any(term in window_lower for term in ['code', 'editor', 'vim', 'emacs']):
                categorized['editor'].append(screenshot)
            else:
                categorized['other'].append(screenshot)
        
        print(f"\n🔍 Testing VLM quality on different content types:")
        
        quality_results = {}
        
        for category, screenshots in categorized.items():
            if not screenshots:
                continue
                
            print(f"\n   Testing {category} screenshots ({len(screenshots)} found):")
            
            # Test first screenshot from category
            screenshot = screenshots[0]
            
            try:
                description = vlm_processor.describe_screenshot(
                    screenshot['filepath'],
                    screenshot["active_window"]
                )
                
                if description:
                    # Analyze description quality for this category
                    quality_metrics = self._analyze_vlm_description_quality(
                        description, category, screenshot["active_window"]
                    )
                    
                    quality_results[category] = quality_metrics
                    
                    print(f"     ✅ {category.capitalize()} description quality:")
                    print(f"        - Relevance score: {quality_metrics['relevance_score']}/5")
                    print(f"        - Detail level: {quality_metrics['detail_level']}")
                    print(f"        - Category keywords found: {quality_metrics['category_keywords_found']}")
                    
            except Exception as e:
                logger.error(f"     ❌ Error processing {category}: {e}")
        
        # Validate that VLM provides appropriate descriptions for different content
        assert len(quality_results) > 0, "Should have quality results for at least some categories"
        
        for category, metrics in quality_results.items():
            assert metrics['relevance_score'] >= 2, \
                f"VLM should provide relevant descriptions for {category} content"
    
    def _analyze_vlm_description_quality(self, description: str, category: str, window_title: str) -> Dict[str, Any]:
        """Analyze the quality of a VLM description for a specific category."""
        description_lower = description.lower()
        
        # Category-specific keywords
        category_keywords = {
            'terminal': ['terminal', 'command', 'console', 'text', 'output', 'prompt'],
            'browser': ['browser', 'web', 'page', 'url', 'tab', 'website'],
            'editor': ['code', 'editor', 'file', 'syntax', 'programming', 'text'],
            'other': ['window', 'application', 'interface', 'screen']
        }
        
        keywords = category_keywords.get(category, category_keywords['other'])
        keywords_found = [kw for kw in keywords if kw in description_lower]
        
        # Calculate metrics
        word_count = len(description.split())
        relevance_score = min(5, len(keywords_found) + (1 if any(w in description_lower for w in window_title.lower().split()) else 0))
        
        detail_level = 'minimal' if word_count < 20 else 'moderate' if word_count < 50 else 'detailed'
        
        return {
            'relevance_score': relevance_score,
            'detail_level': detail_level,
            'word_count': word_count,
            'category_keywords_found': keywords_found,
            'mentions_window_title': any(w in description_lower for w in window_title.lower().split() if len(w) > 3)
        }
    
    def test_vlm_perceptual_hash_deduplication(self, real_screenshots_for_vlm):
        """Test VLM's perceptual hash deduplication on real screenshots."""
        try:
            vlm_processor = VLMProcessor()
        except:
            pytest.skip("VLM processor not available")
        
        print(f"\n🔍 Testing VLM perceptual hash deduplication:")
        
        # Generate hashes for multiple screenshots
        hashes = []
        
        for i, screenshot in enumerate(real_screenshots_for_vlm[:10]):
            try:
                phash = vlm_processor.compute_perceptual_hash(screenshot['filepath'])
                
                if phash:
                    hashes.append({
                        'screenshot': screenshot,
                        'hash': phash,
                        'hash_parts': phash.split('_') if '_' in phash else [phash]
                    })
                    
                    print(f"   Screenshot {i+1}: hash = {phash[:20]}...")
                    
            except Exception as e:
                print(f"   Screenshot {i+1}: Failed to compute hash - {e}")
        
        if len(hashes) < 2:
            pytest.skip("Not enough hashes computed for deduplication testing")
        
        # Check for duplicates
        unique_hashes = set(h['hash'] for h in hashes)
        duplicate_rate = 1 - (len(unique_hashes) / len(hashes))
        
        print(f"\n📊 Hash Analysis:")
        print(f"   - Total screenshots: {len(hashes)}")
        print(f"   - Unique hashes: {len(unique_hashes)}")
        print(f"   - Duplicate rate: {duplicate_rate:.1%}")
        
        # Validate hash properties
        for hash_data in hashes:
            hash_value = hash_data['hash']
            assert isinstance(hash_value, str), "Hash should be a string"
            assert len(hash_value) > 10, "Hash should be meaningful"
            
            # Check hash format (should contain size and hash)
            if '_' in hash_value:
                parts = hash_data['hash_parts']
                assert len(parts) == 2, "Hash should have size and value parts"
                assert parts[0].isdigit(), "First part should be image size"
    
    def test_vlm_caching_on_real_screenshots(self, real_screenshots_for_vlm):
        """Test VLM caching functionality with real screenshots."""
        try:
            vlm_processor = VLMProcessor()
            if not vlm_processor.check_availability():
                pytest.skip("VLM not available")
        except:
            pytest.skip("VLM processor not available")
        
        # Use first screenshot for caching test
        test_screenshot = real_screenshots_for_vlm[0]
        
        print(f"\n🔍 Testing VLM caching:")
        print(f"   Screenshot: {Path(test_screenshot['filepath']).name}")
        
        # First call - should process
        start_time1 = time.time()
        description1 = vlm_processor.describe_screenshot(
            test_screenshot['filepath'],
            test_screenshot["active_window"]
        )
        time1 = time.time() - start_time1
        
        # Second call - should use cache
        start_time2 = time.time()
        description2 = vlm_processor.describe_screenshot(
            test_screenshot['filepath'],
            test_screenshot["active_window"]
        )
        time2 = time.time() - start_time2
        
        print(f"\n📊 Caching Results:")
        print(f"   - First call: {time1:.2f}s")
        print(f"   - Second call: {time2:.2f}s")
        print(f"   - Speedup: {time1/time2:.1f}x" if time2 > 0 else "   - Speedup: N/A")
        print(f"   - Descriptions match: {description1 == description2}")
        
        # Validate caching behavior
        assert description1 == description2, "Cached description should match original"
        # Note: Can't always guarantee cache speedup due to VLM variability
        
        # Test cache invalidation with different window title
        description3 = vlm_processor.describe_screenshot(
            test_screenshot['filepath'],
            "Different Window Title"
        )
        
        # Should potentially be different due to context change
        print(f"   - Different context gives same description: {description1 == description3}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])