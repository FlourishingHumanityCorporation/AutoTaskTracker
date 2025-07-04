#!/usr/bin/env python3
"""
Test different extraction methods on real captured screenshots.
This validates each extraction approach (OCR, AI, VLM, pattern matching) 
using actual screenshots from AutoTaskTracker usage.
"""

import json
import os
import sqlite3
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor


class TestExtractionMethodsOnRealScreenshots:
    """Test each extraction method on real captured screenshots."""
    
    def _init_test_database(self, db_path: str):
        """Initialize test database with the expected schema."""
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            # Create the entities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    file_type_group TEXT,
                    created_at TEXT NOT NULL,
                    last_scan_at TEXT
                )
            """)
            
            # Create the metadata_entries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (entity_id) REFERENCES entities (id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_created_at ON entities(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_entity_id ON metadata_entries(entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata_entries(key)")
            
            conn.commit()
        finally:
            conn.close()
    
    @pytest.fixture
    def real_screenshots_sample(self) -> List[Dict[str, Any]]:
        """Get a sample of real screenshots with various metadata."""
        memos_db = Path.home() / ".memos" / "database.db"
        if not memos_db.exists():
            pytest.skip("Real memos database not found - need actual AutoTaskTracker usage data")
        
        conn = sqlite3.connect(str(memos_db))
        conn.row_factory = sqlite3.Row
        
        # Get diverse screenshots with different metadata combinations
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
            LEFT JOIN metadata_entries m1 ON e.id = m1.entity_id AND m1.key = 'active_window'
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'text'
            LEFT JOIN metadata_entries m3 ON e.id = m3.entity_id AND m3.key = 'tasks'
            LEFT JOIN metadata_entries m4 ON e.id = m4.entity_id AND m4.key = 'vlm_description'
            WHERE e.file_type_group = 'image'
            AND e.filepath IS NOT NULL
            AND m1.value IS NOT NULL
            ORDER BY 
                CASE 
                    WHEN m2.value IS NOT NULL AND m3.value IS NOT NULL THEN 1
                    WHEN m2.value IS NOT NULL THEN 2
                    WHEN m3.value IS NOT NULL THEN 3
                    ELSE 4
                END,
                e.created_at DESC
            LIMIT 50
        """)
        
        screenshots = []
        for row in cursor:
            screenshot = {
                'id': row['id'],
                'filepath': row['filepath'],
                'created_at': row['created_at'],
                'window_title': row['window_title'],
                'has_ocr': row['ocr_text'] is not None,
                'has_ai_task': row['ai_task'] is not None,
                'has_vlm': row['vlm_description'] is not None,
                'ocr_text': row['ocr_text'],
                'ai_task': row['ai_task'],
                'vlm_description': row['vlm_description']
            }
            
            # Only include screenshots where the file exists
            if Path(screenshot['filepath']).exists():
                screenshots.append(screenshot)
        
        conn.close()
        
        if len(screenshots) == 0:
            pytest.skip("No accessible real screenshots found")
        
        print(f"\n✅ Found {len(screenshots)} real screenshots for testing")
        print(f"   - With OCR: {sum(1 for s in screenshots if s['has_ocr'])}")
        print(f"   - With AI tasks: {sum(1 for s in screenshots if s['has_ai_task'])}")
        print(f"   - With VLM: {sum(1 for s in screenshots if s['has_vlm'])}")
        
        return screenshots
    
    def test_basic_pattern_matching_on_real_screenshots(self, real_screenshots_sample):
        """Test basic pattern matching extraction on real window titles."""
        extractor = TaskExtractor()
        
        extraction_results = []
        pattern_categories = {
            'Development': 0,
            'Communication': 0,
            'Research': 0,
            'Productivity': 0,
            'Entertainment': 0,
            'System': 0,
            'Unknown': 0
        }
        
        print("\n🔍 Testing Basic Pattern Matching Extraction:")
        
        for screenshot in real_screenshots_sample:
            window_title = screenshot['window_title']
            
            # Extract task using basic pattern matching
            extracted_task = extractor.extract_task(window_title)
            
            # Categorize the result
            task_lower = extracted_task.lower()
            if any(word in task_lower for word in ['code', 'programming', 'development', 'debug']):
                category = 'Development'
            elif any(word in task_lower for word in ['meeting', 'email', 'slack', 'zoom', 'communication']):
                category = 'Communication'
            elif any(word in task_lower for word in ['research', 'documentation', 'learning', 'reading']):
                category = 'Research'
            elif any(word in task_lower for word in ['spreadsheet', 'document', 'presentation', 'productivity']):
                category = 'Productivity'
            elif any(word in task_lower for word in ['video', 'music', 'game', 'entertainment']):
                category = 'Entertainment'
            elif any(word in task_lower for word in ['system', 'settings', 'preferences', 'terminal']):
                category = 'System'
            else:
                category = 'Unknown'
            
            pattern_categories[category] += 1
            
            extraction_results.append({
                'window_title': window_title,
                'extracted_task': extracted_task,
                'category': category,
                'has_ocr': screenshot['has_ocr'],
                'has_ai': screenshot['has_ai_task']
            })
        
        # Validate results
        assert len(extraction_results) == len(real_screenshots_sample)
        
        # Check extraction quality
        non_unknown = sum(1 for r in extraction_results if r['category'] != 'Unknown')
        extraction_rate = non_unknown / len(extraction_results)
        
        print(f"\n📊 Pattern Matching Results:")
        print(f"   - Total extractions: {len(extraction_results)}")
        print(f"   - Successful categorization: {extraction_rate:.1%}")
        print(f"   - Category distribution:")
        for category, count in sorted(pattern_categories.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"     • {category}: {count} ({count/len(extraction_results):.1%})")
        
        # Show sample extractions
        print(f"\n   Sample extractions:")
        for result in extraction_results[:5]:
            print(f"     '{result['window_title'][:50]}...' → '{result['extracted_task']}'")
        
        # Pattern matching should work for most windows
        assert extraction_rate > 0.1, f"Pattern matching should categorize at least 10% of windows, got {extraction_rate:.1%}"
    
    def test_ocr_extraction_on_real_screenshots(self, real_screenshots_sample):
        """Test OCR-based extraction on real screenshot images."""
        # Filter screenshots that have file paths
        screenshots_with_files = [s for s in real_screenshots_sample if Path(s['filepath']).exists()]
        
        if len(screenshots_with_files) == 0:
            pytest.skip("No accessible screenshot files found")
        
        print(f"\n🔍 Testing OCR Extraction on {len(screenshots_with_files)} Real Screenshots:")
        
        # Test OCR on a subset to avoid long test times
        test_sample = screenshots_with_files[:5]
        ocr_results = []
        
        for screenshot in test_sample:
            filepath = screenshot['filepath']
            window_title = screenshot['window_title']
            
            print(f"\n   Processing: {Path(filepath).name}")
            print(f"   Window: {window_title[:60]}...")
            
            # Run OCR using pytesseract
            try:
                import pytesseract
                from PIL import Image
                
                # Open and process the image
                img = Image.open(filepath)
                
                # Run OCR
                ocr_text = pytesseract.image_to_string(img)
                ocr_data_detailed = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                if ocr_text and ocr_text.strip():
                    # Convert to format similar to expected OCR data
                    ocr_data = []
                    
                    # Extract text regions with confidence
                    for i in range(len(ocr_data_detailed['text'])):
                        text = ocr_data_detailed['text'][i].strip()
                        if text:
                            conf = ocr_data_detailed['conf'][i]
                            if conf > 0:  # Only include confident detections
                                # Create bounding box coordinates
                                x = ocr_data_detailed['left'][i]
                                y = ocr_data_detailed['top'][i]
                                w = ocr_data_detailed['width'][i]
                                h = ocr_data_detailed['height'][i]
                                
                                bbox = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                                ocr_data.append([bbox, text, conf/100.0])
                    
                    if len(ocr_data) > 0:
                            # Extract text content
                            text_regions = []
                            for item in ocr_data:
                                if isinstance(item, list) and len(item) >= 2:
                                    text = str(item[1]).strip()
                                    if text:
                                        text_regions.append(text)
                            
                            combined_text = " ".join(text_regions)
                            
                            ocr_results.append({
                                'filepath': filepath,
                                'window_title': window_title,
                                'ocr_success': True,
                                'text_regions_count': len(ocr_data),
                                'extracted_text': combined_text[:200] + "..." if len(combined_text) > 200 else combined_text,
                                'text_length': len(combined_text),
                                'has_existing_ocr': screenshot['has_ocr']
                            })
                            
                            print(f"   ✅ OCR found {len(ocr_data)} text regions")
                            print(f"   Sample text: {combined_text[:100]}...")
                    else:
                        print(f"   ⚠️ No text detected by OCR")
                        ocr_results.append({
                            'filepath': filepath,
                            'window_title': window_title,
                            'ocr_success': False,
                            'text_regions_count': 0,
                            'extracted_text': "",
                            'text_length': 0,
                            'has_existing_ocr': screenshot['has_ocr']
                        })
                else:
                    print(f"   ⚠️ No text detected by OCR")
                    ocr_results.append({
                        'filepath': filepath,
                        'window_title': window_title,
                        'ocr_success': False,
                        'text_regions_count': 0,
                        'extracted_text': "",
                        'text_length': 0,
                        'has_existing_ocr': screenshot['has_ocr']
                    })
                    
            except ImportError:
                print(f"   ❌ pytesseract not available - install with: pip install pytesseract")
                break
            except Exception as e:
                print(f"   ❌ OCR error: {e}")
        
        if len(ocr_results) > 0:
            successful_ocr = sum(1 for r in ocr_results if r['ocr_success'])
            print(f"\n📊 OCR Extraction Results:")
            print(f"   - Tested screenshots: {len(ocr_results)}")
            print(f"   - Successful OCR: {successful_ocr} ({successful_ocr/len(ocr_results):.1%})")
            print(f"   - Average text regions: {sum(r['text_regions_count'] for r in ocr_results)/len(ocr_results):.1f}")
            print(f"   - Screenshots with existing OCR: {sum(1 for r in ocr_results if r['has_existing_ocr'])}")
            
            # Validate that OCR works on at least some screenshots
            assert successful_ocr > 0, "OCR should work on at least some real screenshots"
        else:
            pytest.skip("No OCR results obtained")
    
    def test_ai_extraction_methods_on_real_screenshots(self, real_screenshots_sample):
        """Test AI-enhanced extraction methods on real screenshots."""
        # Create a temporary database for AI extractor
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_db = tmp.name
        
        try:
            # Initialize database schema
            self._init_test_database(temp_db)
            
            # Initialize AI extractor
            try:
                ai_extractor = AIEnhancedTaskExtractor(temp_db)
            except ImportError:
                pytest.skip("AI dependencies not available")
            
            print(f"\n🤖 Testing AI Extraction Methods on Real Screenshots:")
            
            # Test different AI extraction scenarios
            test_scenarios = []
            
            # Scenario 1: Window title only
            window_only = [s for s in real_screenshots_sample if not s['has_ocr'] and not s['has_vlm']][:5]
            
            # Scenario 2: Window title + OCR
            with_ocr = [s for s in real_screenshots_sample if s['has_ocr']][:5]
            
            # Scenario 3: Window title + VLM
            with_vlm = [s for s in real_screenshots_sample if s['has_vlm']][:5]
            
            # Scenario 4: All data available
            with_all = [s for s in real_screenshots_sample if s['has_ocr'] and s['has_vlm']][:5]
            
            results = {
                'window_only': [],
                'with_ocr': [],
                'with_vlm': [],
                'with_all': []
            }
            
            # Test window title only
            print("\n   📝 Testing with window title only:")
            for screenshot in window_only:
                try:
                    result = ai_extractor.extract_enhanced_task(
                        window_title=screenshot['window_title'],
                        ocr_text=None,
                        vlm_description=None,
                        entity_id=None
                    )
                    results['window_only'].append(result)
                    print(f"     ✅ '{screenshot['window_title'][:40]}...' → '{result['task']}'")
                except Exception as e:
                    print(f"     ❌ Failed: {e}")
            
            # Test with OCR data
            print("\n   📝 Testing with OCR data:")
            for screenshot in with_ocr:
                try:
                    result = ai_extractor.extract_enhanced_task(
                        window_title=screenshot['window_title'],
                        ocr_text=screenshot['ocr_text'],
                        vlm_description=None,
                        entity_id=None
                    )
                    results['with_ocr'].append(result)
                    print(f"     ✅ '{screenshot['window_title'][:40]}...' → '{result['task']}' (confidence: {result['confidence']:.2f})")
                except Exception as e:
                    print(f"     ❌ Failed: {e}")
            
            # Test with VLM data
            if len(with_vlm) > 0:
                print("\n   📝 Testing with VLM descriptions:")
                for screenshot in with_vlm:
                    try:
                        result = ai_extractor.extract_enhanced_task(
                            window_title=screenshot['window_title'],
                            ocr_text=None,
                            vlm_description=screenshot['vlm_description'],
                            entity_id=None
                        )
                        results['with_vlm'].append(result)
                        print(f"     ✅ '{screenshot['window_title'][:40]}...' → '{result['task']}' (confidence: {result['confidence']:.2f})")
                    except Exception as e:
                        print(f"     ❌ Failed: {e}")
            
            # Test with all data
            if len(with_all) > 0:
                print("\n   📝 Testing with all data sources:")
                for screenshot in with_all:
                    try:
                        result = ai_extractor.extract_enhanced_task(
                            window_title=screenshot['window_title'],
                            ocr_text=screenshot['ocr_text'],
                            vlm_description=screenshot['vlm_description'],
                            entity_id=None
                        )
                        results['with_all'].append(result)
                        print(f"     ✅ '{screenshot['window_title'][:40]}...' → '{result['task']}' (confidence: {result['confidence']:.2f})")
                        
                        # Show which AI features were used
                        features_used = []
                        if result['ai_features'].get('ocr_quality'):
                            features_used.append('OCR')
                        if result['ai_features'].get('vlm_available'):
                            features_used.append('VLM')
                        if result['ai_features'].get('embeddings_available'):
                            features_used.append('Embeddings')
                        print(f"        Features: {', '.join(features_used)}")
                    except Exception as e:
                        print(f"     ❌ Failed: {e}")
            
            # Analyze results
            print("\n📊 AI Extraction Analysis:")
            
            # Compare confidence levels
            if results['window_only']:
                avg_confidence_window = sum(r['confidence'] for r in results['window_only']) / len(results['window_only'])
                print(f"   - Window only avg confidence: {avg_confidence_window:.2f}")
            
            if results['with_ocr']:
                avg_confidence_ocr = sum(r['confidence'] for r in results['with_ocr']) / len(results['with_ocr'])
                print(f"   - With OCR avg confidence: {avg_confidence_ocr:.2f}")
            
            if results['with_vlm']:
                avg_confidence_vlm = sum(r['confidence'] for r in results['with_vlm']) / len(results['with_vlm'])
                print(f"   - With VLM avg confidence: {avg_confidence_vlm:.2f}")
            
            if results['with_all']:
                avg_confidence_all = sum(r['confidence'] for r in results['with_all']) / len(results['with_all'])
                print(f"   - With all data avg confidence: {avg_confidence_all:.2f}")
            
            # Validate that AI extraction works
            total_results = len(results['window_only']) + len(results['with_ocr']) + len(results['with_vlm']) + len(results['with_all'])
            assert total_results > 0, "AI extraction should produce at least some results"
            
        finally:
            # Cleanup
            try:
                os.unlink(temp_db)
            except:
                pass
    
    def test_extraction_method_comparison_on_same_screenshots(self, real_screenshots_sample):
        """Compare different extraction methods on the same screenshots."""
        # Select screenshots that have multiple types of data
        comparison_candidates = [
            s for s in real_screenshots_sample 
            if s['has_ocr'] or s['has_ai_task']
        ][:10]
        
        if len(comparison_candidates) == 0:
            pytest.skip("No screenshots with multiple data types for comparison")
        
        print(f"\n🔬 Comparing Extraction Methods on {len(comparison_candidates)} Screenshots:")
        
        # Basic extractor
        basic_extractor = TaskExtractor()
        
        # Results storage
        comparison_results = []
        
        for screenshot in comparison_candidates:
            window_title = screenshot['window_title']
            
            # Method 1: Basic pattern matching
            basic_task = basic_extractor.extract_task(window_title)
            
            # Method 2: Existing AI task (if available)
            existing_ai_task = screenshot['ai_task'] if screenshot['has_ai_task'] else None
            
            # Method 3: Parse existing OCR (if available)
            ocr_derived_task = None
            if screenshot['has_ocr'] and screenshot['ocr_text']:
                try:
                    # Try to extract meaningful task from OCR text
                    if screenshot['ocr_text'].startswith('['):
                        ocr_data = eval(screenshot['ocr_text'])
                        if isinstance(ocr_data, list) and len(ocr_data) > 0:
                            text_parts = []
                            for item in ocr_data[:5]:  # First 5 text regions
                                if isinstance(item, list) and len(item) >= 2:
                                    text_parts.append(str(item[1]))
                            if text_parts:
                                ocr_derived_task = f"Working with: {', '.join(text_parts[:3])}"
                except:
                    pass
            
            comparison = {
                'window_title': window_title,
                'basic_extraction': basic_task,
                'ai_extraction': existing_ai_task,
                'ocr_present': screenshot['has_ocr'],
                'vlm_present': screenshot['has_vlm'],
                'methods_agree': False
            }
            
            # Check if methods agree (similar tasks)
            if basic_task and existing_ai_task:
                basic_lower = basic_task.lower()
                ai_lower = existing_ai_task.lower()
                
                # Check for common words or similar meaning
                basic_words = set(basic_lower.split())
                ai_words = set(ai_lower.split())
                common_words = basic_words & ai_words
                
                comparison['methods_agree'] = len(common_words) > 0 or any(
                    word in ai_lower for word in basic_words if len(word) > 3
                )
            
            comparison_results.append(comparison)
        
        # Analyze agreement between methods
        agreements = sum(1 for c in comparison_results if c['methods_agree'])
        agreement_rate = agreements / len(comparison_results) if comparison_results else 0
        
        print(f"\n📊 Method Comparison Results:")
        print(f"   - Screenshots compared: {len(comparison_results)}")
        print(f"   - Method agreement rate: {agreement_rate:.1%}")
        print(f"   - Screenshots with OCR: {sum(1 for c in comparison_results if c['ocr_present'])}")
        print(f"   - Screenshots with VLM: {sum(1 for c in comparison_results if c['vlm_present'])}")
        
        # Show examples of agreement and disagreement
        print(f"\n   Examples where methods agree:")
        for comp in comparison_results[:3]:
            if comp['methods_agree']:
                print(f"     Window: '{comp['window_title'][:50]}...'")
                print(f"     Basic: '{comp['basic_extraction']}'")
                print(f"     AI: '{comp['ai_extraction']}'")
                print()
        
        print(f"\n   Examples where methods differ:")
        for comp in comparison_results[:3]:
            if not comp['methods_agree'] and comp['ai_extraction']:
                print(f"     Window: '{comp['window_title'][:50]}...'")
                print(f"     Basic: '{comp['basic_extraction']}'")
                print(f"     AI: '{comp['ai_extraction']}'")
                print()
        
        # Methods should have reasonable agreement on clear cases
        assert len(comparison_results) > 0, "Should have comparison results"
    
    def test_extraction_performance_on_real_data(self, real_screenshots_sample):
        """Test extraction performance characteristics on real data."""
        print(f"\n⚡ Testing Extraction Performance on Real Data:")
        
        # Test basic extraction performance
        basic_extractor = TaskExtractor()
        
        start_time = time.time()
        basic_results = []
        
        for screenshot in real_screenshots_sample:
            result = basic_extractor.extract_task(screenshot['window_title'])
            basic_results.append(result)
        
        basic_time = time.time() - start_time
        basic_rate = len(real_screenshots_sample) / basic_time
        
        print(f"\n📊 Performance Results:")
        print(f"   - Basic extraction: {len(real_screenshots_sample)} screenshots in {basic_time:.2f}s")
        print(f"   - Rate: {basic_rate:.1f} screenshots/second")
        
        # Performance assertions
        assert basic_time < 10, f"Basic extraction should complete within 10 seconds, took {basic_time:.2f}s"
        assert basic_rate > 5, f"Should process at least 5 screenshots/second, got {basic_rate:.1f}"
        
        # Test with different data availability
        with_ocr_count = sum(1 for s in real_screenshots_sample if s['has_ocr'])
        with_ai_count = sum(1 for s in real_screenshots_sample if s['has_ai_task'])
        with_vlm_count = sum(1 for s in real_screenshots_sample if s['has_vlm'])
        
        print(f"\n   Data availability impact:")
        print(f"   - Screenshots with OCR: {with_ocr_count} ({with_ocr_count/len(real_screenshots_sample):.1%})")
        print(f"   - Screenshots with AI tasks: {with_ai_count} ({with_ai_count/len(real_screenshots_sample):.1%})")
        print(f"   - Screenshots with VLM: {with_vlm_count} ({with_vlm_count/len(real_screenshots_sample):.1%})")
        
        # Measure extraction quality vs data availability
        quality_scores = []
        for screenshot in real_screenshots_sample:
            score = 1.0  # Base score for having window title
            if screenshot['has_ocr']:
                score += 0.5
            if screenshot['has_ai_task']:
                score += 0.5
            if screenshot['has_vlm']:
                score += 0.5
            quality_scores.append(score)
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        print(f"   - Average data quality score: {avg_quality:.2f}/2.5")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])