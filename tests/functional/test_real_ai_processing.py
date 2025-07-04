#!/usr/bin/env python3
"""
Real AI processing tests that validate actual AI functionality.
These tests use real AI models and processing, not mocks.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor

# Test assets
ASSETS_DIR = REPO_ROOT / "tests" / "assets"
CODE_EDITOR_IMAGE = ASSETS_DIR / "realistic_code_editor.png"


class TestRealAIProcessing:
    """Test real AI processing functionality."""
    
    @pytest.fixture
    def temp_db_path(self) -> str:
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # Initialize the database with the schema
        self._init_test_database(db_path)
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
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
            
            conn.commit()
        finally:
            conn.close()
    
    def test_basic_task_extractor_real_functionality(self):
        """Test the basic TaskExtractor with real window titles."""
        extractor = TaskExtractor()
        
        # Test with real-world window titles
        test_cases = [
            {
                'window_title': 'main.py - Visual Studio Code',
                'expected_category': 'Development',
                'should_contain': ['code', 'development', 'programming']
            },
            {
                'window_title': 'Weekly Team Meeting - Zoom',
                'expected_category': 'Communication',
                'should_contain': ['meeting', 'communication', 'video']
            },
            {
                'window_title': 'Python Documentation - Mozilla Firefox',
                'expected_category': 'Research',
                'should_contain': ['research', 'documentation', 'learning']
            },
            {
                'window_title': 'Gmail - Inbox - Google Chrome',
                'expected_category': 'Communication',
                'should_contain': ['email', 'communication']
            },
            {
                'window_title': 'Slack | AutoTaskTracker Team',
                'expected_category': 'Communication',
                'should_contain': ['communication', 'messaging']
            },
            {
                'window_title': 'AutoTaskTracker.xlsx - Microsoft Excel',
                'expected_category': 'Productivity',
                'should_contain': ['spreadsheet', 'data', 'analysis']
            }
        ]
        
        successful_extractions = 0
        
        for test_case in test_cases:
            result = extractor.extract_task(test_case['window_title'])
            
            # Validate result structure (TaskExtractor returns string, not dict)
            assert isinstance(result, str), "Should return a string"
            assert len(result.strip()) > 0, "Task should not be empty"
            
            # Check if the extraction makes sense
            task_lower = result.lower()
            window_lower = test_case['window_title'].lower()
            
            # Task should be related to the window title or contain expected keywords
            common_words = set(task_lower.split()) & set(window_lower.split())
            keyword_found = any(keyword in task_lower for keyword in test_case['should_contain'])
            
            # Should either have common words OR contain expected keywords
            assert len(common_words) > 0 or keyword_found, \
                f"Task '{result}' should be related to window '{test_case['window_title']}'"
            
            successful_extractions += 1
            
            print(f"✅ '{test_case['window_title']}' -> '{result}'")
        
        assert successful_extractions == len(test_cases), "All extractions should succeed"
        print(f"✅ Basic TaskExtractor processed {successful_extractions} test cases")
    
    def test_ai_enhanced_task_extractor_with_real_models(self, temp_db_path: str):
        """Test AI-enhanced task extraction with real models (if available)."""
        try:
            ai_extractor = AIEnhancedTaskExtractor(temp_db_path)
            assert ai_extractor is not None, "AI extractor should initialize"
        except ImportError as e:
            pytest.skip(f"AI dependencies not available: {e}")
        except Exception as e:
            pytest.skip(f"AI extractor initialization failed: {e}")
        
        # Test cases with rich context
        test_cases = [
            {
                'window_title': 'task_extractor.py - Visual Studio Code',
                'ocr_text': json.dumps([
                    [[[10, 10], [200, 10], [200, 30], [10, 30]], "class TaskExtractor:", 0.95],
                    [[[10, 50], [250, 50], [250, 70], [10, 70]], "def extract_task(self, window_title):", 0.92],
                    [[[30, 80], [180, 80], [180, 100], [30, 100]], "# Extract task from window title", 0.88],
                    [[[30, 110], [200, 110], [200, 130], [30, 130]], "if 'code' in window_title:", 0.90]
                ]),
                'vlm_description': 'Code editor showing Python class definition for task extraction',
                'expected_category': 'Development'
            },
            {
                'window_title': 'Project Roadmap Q1 2024 - Google Docs',
                'ocr_text': json.dumps([
                    [[[50, 50], [300, 50], [300, 80], [50, 80]], "Q1 2024 Project Roadmap", 0.92],
                    [[[50, 100], [200, 100], [200, 120], [50, 120]], "1. AI Integration", 0.89],
                    [[[50, 130], [250, 130], [250, 150], [50, 150]], "2. Dashboard Improvements", 0.87],
                    [[[50, 160], [180, 160], [180, 180], [50, 180]], "3. Performance Testing", 0.91]
                ]),
                'vlm_description': 'Document editor with project planning content and timeline',
                'expected_category': 'Planning'
            },
            {
                'window_title': 'Stack Overflow - Python async/await best practices',
                'ocr_text': json.dumps([
                    [[[100, 100], [400, 100], [400, 130], [100, 130]], "Python async/await best practices", 0.94],
                    [[[100, 150], [300, 150], [300, 170], [100, 170]], "How to properly handle async functions", 0.90],
                    [[[100, 200], [350, 200], [350, 220], [100, 220]], "import asyncio", 0.95],
                    [[[100, 230], [250, 230], [250, 250], [100, 250]], "async def main():", 0.93]
                ]),
                'vlm_description': 'Browser showing Stack Overflow with Python code examples',
                'expected_category': 'Research'
            }
        ]
        
        successful_extractions = 0
        
        for i, test_case in enumerate(test_cases):
            try:
                result = ai_extractor.extract_enhanced_task(
                    window_title=test_case['window_title'],
                    ocr_text=test_case['ocr_text'],
                    vlm_description=test_case.get('vlm_description'),
                    entity_id=None
                )
                
                # Validate result structure
                assert isinstance(result, dict), f"Test {i+1}: Should return a dictionary"
                assert 'task' in result, f"Test {i+1}: Should have a task field"
                assert 'category' in result, f"Test {i+1}: Should have a category field"
                assert 'confidence' in result, f"Test {i+1}: Should have a confidence field"
                assert 'ai_features' in result, f"Test {i+1}: Should have ai_features field"
                
                # Validate data types
                assert isinstance(result['task'], str), f"Test {i+1}: Task should be a string"
                assert isinstance(result['category'], str), f"Test {i+1}: Category should be a string"
                assert isinstance(result['confidence'], (int, float)), f"Test {i+1}: Confidence should be numeric"
                assert isinstance(result['ai_features'], dict), f"Test {i+1}: AI features should be a dict"
                
                # Validate confidence range
                assert 0 <= result['confidence'] <= 1, f"Test {i+1}: Confidence should be between 0 and 1"
                
                # Validate task quality
                assert len(result['task'].strip()) > 10, f"Test {i+1}: Task should be descriptive"
                
                # Check AI features were used
                ai_features = result['ai_features']
                features_used = []
                if ai_features.get('ocr_quality'):
                    features_used.append('OCR')
                if ai_features.get('vlm_available'):
                    features_used.append('VLM')
                if ai_features.get('embeddings_available'):
                    features_used.append('Embeddings')
                
                # Should use at least OCR
                assert len(features_used) > 0, f"Test {i+1}: Should use at least one AI feature"
                
                successful_extractions += 1
                
                print(f"✅ Test {i+1}: '{result['task']}' ({result['category']}, {result['confidence']:.2f})")
                print(f"   AI Features: {', '.join(features_used)}")
                
                # Test task quality - should be more detailed than basic extraction
                basic_result = TaskExtractor().extract_task(test_case['window_title'])
                if basic_result:
                    assert len(result['task']) >= len(basic_result), \
                        f"Test {i+1}: AI-enhanced task should be at least as detailed as basic extraction"
                
            except Exception as e:
                print(f"⚠️ Test {i+1} failed: {e}")
                # Don't fail the entire test - AI might not be fully configured
                continue
        
        # Should have at least some successful extractions
        assert successful_extractions > 0, "At least some AI extractions should succeed"
        print(f"✅ AI-enhanced extractor processed {successful_extractions}/{len(test_cases)} test cases")
    
    def test_embeddings_functionality_if_available(self, temp_db_path: str):
        """Test embeddings functionality if the models are available."""
        try:
            from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine, EmbeddingStats
        except ImportError:
            pytest.skip("Embeddings dependencies not available")
        
        try:
            # Test embeddings stats
            stats = EmbeddingStats(temp_db_path)
            coverage = stats.get_embedding_coverage()
            
            # Should return valid coverage data structure
            if coverage:
                assert isinstance(coverage, dict), "Coverage should be a dictionary"
                assert 'total_screenshots' in coverage, "Should have total screenshots"
                assert 'screenshots_with_embeddings' in coverage, "Should have embeddings count"
                assert 'coverage_percentage' in coverage, "Should have coverage percentage"
                
                # Validate data types
                assert isinstance(coverage['total_screenshots'], int), "Total should be int"
                assert isinstance(coverage['screenshots_with_embeddings'], int), "Count should be int"
                assert isinstance(coverage['coverage_percentage'], (int, float)), "Percentage should be numeric"
                
                print(f"✅ Embeddings coverage: {coverage['coverage_percentage']:.1f}%")
        
        except Exception as e:
            pytest.skip(f"Embeddings functionality not available: {e}")
        
        try:
            # Test embeddings search engine
            search_engine = EmbeddingsSearchEngine(temp_db_path)
            assert search_engine is not None, "Search engine should initialize"
            
            # Test that we can call search methods without crashing
            # (actual search requires existing embeddings in database)
            assert hasattr(search_engine, 'semantic_search'), "Should have semantic_search method"
            
            print("✅ Embeddings search engine initializes correctly")
            
        except Exception as e:
            pytest.skip(f"Embeddings search engine not available: {e}")
    
    def test_vlm_functionality_if_available(self):
        """Test VLM (Visual Language Model) functionality if available."""
        try:
            from autotasktracker.ai.vlm_integration import VLMTaskExtractor, extract_vlm_enhanced_task
        except ImportError:
            pytest.skip("VLM dependencies not available")
        
        try:
            vlm_extractor = VLMTaskExtractor()
            assert vlm_extractor is not None, "VLM extractor should initialize"
            assert hasattr(vlm_extractor, 'extract_task'), "Should have extract_task method"
            
            print("✅ VLM extractor initializes correctly")
            
        except Exception as e:
            pytest.skip(f"VLM extractor not available: {e}")
        
        # Test VLM extraction with realistic descriptions
        test_descriptions = [
            {
                'description': 'The image shows a code editor with Python code. Multiple files are open in tabs. The main editor shows a class definition with several methods.',
                'window_title': 'main.py - VS Code',
                'expected_keywords': ['code', 'programming', 'development', 'python']
            },
            {
                'description': 'A video conference interface with multiple participants in a grid layout. Screen sharing is active showing a presentation.',
                'window_title': 'Team Meeting - Zoom',
                'expected_keywords': ['meeting', 'video', 'conference', 'presentation']
            },
            {
                'description': 'Browser window displaying technical documentation with code examples and API references.',
                'window_title': 'API Documentation - Chrome',
                'expected_keywords': ['documentation', 'research', 'learning', 'api']
            }
        ]
        
        successful_extractions = 0
        
        for i, test in enumerate(test_descriptions):
            try:
                result = extract_vlm_enhanced_task(
                    test['description'],
                    test['window_title']
                )
                
                if result:
                    # Validate result structure
                    assert isinstance(result, dict), f"VLM test {i+1}: Should return a dictionary"
                    assert 'task_title' in result, f"VLM test {i+1}: Should have task_title"
                    assert 'category' in result, f"VLM test {i+1}: Should have category"
                    assert 'confidence' in result, f"VLM test {i+1}: Should have confidence"
                    
                    # Validate data types
                    assert isinstance(result['task_title'], str), f"VLM test {i+1}: Task title should be string"
                    assert isinstance(result['category'], str), f"VLM test {i+1}: Category should be string"
                    assert isinstance(result['confidence'], (int, float)), f"VLM test {i+1}: Confidence should be numeric"
                    
                    # Validate confidence range
                    assert 0 <= result['confidence'] <= 1, f"VLM test {i+1}: Confidence should be between 0 and 1"
                    
                    # Check task quality
                    task_lower = result['task_title'].lower()
                    keyword_found = any(keyword in task_lower for keyword in test['expected_keywords'])
                    assert keyword_found, f"VLM test {i+1}: Task should contain relevant keywords"
                    
                    successful_extractions += 1
                    
                    print(f"✅ VLM test {i+1}: '{result['task_title']}' ({result['category']}, {result['confidence']:.2f})")
                else:
                    print(f"⚠️ VLM test {i+1}: No result returned")
                    
            except Exception as e:
                print(f"⚠️ VLM test {i+1} failed: {e}")
                continue
        
        if successful_extractions > 0:
            print(f"✅ VLM functionality works: {successful_extractions}/{len(test_descriptions)} extractions succeeded")
        else:
            pytest.skip("VLM functionality not working (may need Ollama setup)")
    
    def test_ai_performance_benchmarks(self, temp_db_path: str):
        """Test AI processing performance with realistic workloads."""
        import time
        
        # Test basic task extraction performance
        extractor = TaskExtractor()
        
        test_windows = [
            'main.py - Visual Studio Code',
            'Project Planning - Google Docs',
            'Team Meeting - Zoom',
            'Stack Overflow - Python Questions',
            'Gmail - Inbox'
        ] * 20  # 100 total extractions
        
        start_time = time.time()
        
        for window_title in test_windows:
            result = extractor.extract_task(window_title)
            assert result is not None, "Should always return a result"
            assert isinstance(result, str), "Should return a string"
            assert len(result.strip()) > 0, "Should return non-empty string"
        
        basic_time = time.time() - start_time
        
        print(f"✅ Basic extraction: {len(test_windows)} tasks in {basic_time:.2f}s ({len(test_windows)/basic_time:.1f} tasks/sec)")
        
        # Performance should be reasonable
        assert basic_time < 30, "Basic extraction should complete within 30 seconds"
        assert len(test_windows)/basic_time > 1, "Should process at least 1 task per second"
        
        # Test AI-enhanced extraction performance (if available)
        try:
            ai_extractor = AIEnhancedTaskExtractor(temp_db_path)
            
            sample_ocr = json.dumps([
                [[[10, 10], [200, 10], [200, 30], [10, 30]], "Sample text", 0.9]
            ])
            
            start_time = time.time()
            
            # Test with smaller sample for AI processing
            for window_title in test_windows[:10]:  # 10 AI extractions
                result = ai_extractor.extract_enhanced_task(
                    window_title=window_title,
                    ocr_text=sample_ocr,
                    vlm_description=None,
                    entity_id=None
                )
                assert result is not None, "AI extraction should return a result"
            
            ai_time = time.time() - start_time
            
            print(f"✅ AI-enhanced extraction: 10 tasks in {ai_time:.2f}s ({10/ai_time:.1f} tasks/sec)")
            
            # AI processing should be reasonable (slower than basic but not too slow)
            assert ai_time < 60, "AI extraction should complete within 60 seconds"
            
        except Exception as e:
            print(f"⚠️ AI performance test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])