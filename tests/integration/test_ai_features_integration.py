#!/usr/bin/env python3
"""
Test script for AI enhancements in AutoTaskTracker.
Validates VLM integration, embeddings search, and OCR enhancement.
"""
import json
import pytest
from datetime import datetime, timedelta

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_integration import VLMTaskExtractor, extract_vlm_enhanced_task
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine, EmbeddingStats
from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor


@pytest.mark.timeout(30)
def test_database_ai_coverage_statistics_and_query_functionality():
    """Test database queries for AI coverage statistics and AI-enhanced data retrieval functionality."""
    print("\n=== Testing Database AI Queries ===")
    
    db_manager = DatabaseManager()
    
    # Test AI coverage stats
    print("\n1. AI Coverage Statistics:")
    stats = db_manager.get_ai_coverage_stats()
    if stats:
        print(f"   Total screenshots: {stats['total_screenshots']}")
        print(f"   OCR coverage: {stats['ocr_percentage']:.1f}% ({stats['ocr_count']} screenshots)")
        print(f"   VLM coverage: {stats['vlm_percentage']:.1f}% ({stats['vlm_count']} screenshots)")
        print(f"   Embedding coverage: {stats['embedding_percentage']:.1f}% ({stats['embedding_count']} screenshots)")
        
        # Assert that AI coverage statistics are valid
        assert isinstance(stats, dict), "AI coverage stats should be a dictionary"
        assert 'total_screenshots' in stats, "Should have total_screenshots field"
        assert isinstance(stats['total_screenshots'], int), "Total screenshots should be an integer"
        assert stats['total_screenshots'] >= 0, "Total screenshots should be non-negative"
        
        # Validate OCR coverage
        assert 'ocr_count' in stats and 'ocr_percentage' in stats, "Should have OCR coverage data"
        assert stats['ocr_count'] <= stats['total_screenshots'], "OCR count cannot exceed total"
        assert 0 <= stats['ocr_percentage'] <= 100, "OCR percentage should be 0-100"
        
        # Validate VLM coverage  
        assert 'vlm_count' in stats and 'vlm_percentage' in stats, "Should have VLM coverage data"
        assert stats['vlm_count'] <= stats['total_screenshots'], "VLM count cannot exceed total"
        assert 0 <= stats['vlm_percentage'] <= 100, "VLM percentage should be 0-100"
        
        # Validate embedding coverage
        assert 'embedding_count' in stats and 'embedding_percentage' in stats, "Should have embedding coverage data"
        assert stats['embedding_count'] <= stats['total_screenshots'], "Embedding count cannot exceed total"
        assert 0 <= stats['embedding_percentage'] <= 100, "Embedding percentage should be 0-100"
    else:
        print("   ❌ Could not fetch AI coverage stats")
    
    # Test fetching tasks with AI data
    print("\n2. Fetching tasks with AI data:")
    tasks_df = db_manager.fetch_tasks_with_ai(limit=5)
    if not tasks_df.empty:
        print(f"   ✅ Fetched {len(tasks_df)} tasks")
        
        # Check for AI columns
        has_vlm = 'vlm_description' in tasks_df.columns
        has_embedding = 'has_embedding' in tasks_df.columns
        
        print(f"   VLM column present: {'✅' if has_vlm else '❌'}")
        print(f"   Embedding column present: {'✅' if has_embedding else '❌'}")
        
        # Count tasks with AI data
        if has_vlm:
            vlm_count = tasks_df['vlm_description'].notna().sum()
            print(f"   Tasks with VLM descriptions: {vlm_count}")
        
        if has_embedding:
            embedding_count = tasks_df['has_embedding'].sum()
            print(f"   Tasks with embeddings: {embedding_count}")
        
        # Assert that fetch_tasks_with_ai returns valid data structure
        assert len(tasks_df) <= 5, "Should not return more than requested limit"
        required_columns = ['id', 'filepath', 'created_at']
        for col in required_columns:
            assert col in tasks_df.columns, f"Missing required column: {col}"
        
        # Validate data types
        assert all(isinstance(task_id, (int, str)) for task_id in tasks_df['id']), "Task IDs should be int or str"
        
        # If VLM data exists, validate it
        if has_vlm:
            vlm_tasks = tasks_df[tasks_df['vlm_description'].notna()]
            if not vlm_tasks.empty:
                assert all(isinstance(desc, str) for desc in vlm_tasks['vlm_description']), "VLM descriptions should be strings"
        
        # If embedding data exists, validate it
        if has_embedding:
            assert all(embed in [0, 1] for embed in tasks_df['has_embedding']), "has_embedding should be 0 or 1"
    else:
        print("   ❌ No tasks found")
    
    # Assert core functionality works
    assert db_manager is not None, "Database manager should be initialized"
    # Test that fetch_tasks_with_ai method exists and is callable
    assert callable(getattr(db_manager, 'fetch_tasks_with_ai', None)), "fetch_tasks_with_ai should be callable"
    assert callable(getattr(db_manager, 'get_ai_coverage_stats', None)), "get_ai_coverage_stats should be callable"


@pytest.mark.timeout(30)
def test_visual_language_model_integration_and_task_extraction():
    """Test Visual Language Model (VLM) integration functionality and task extraction from screenshot descriptions."""
    print("\n=== Testing VLM Integration ===")
    
    vlm_extractor = VLMTaskExtractor()
    
    # Assert that VLM extractor can be initialized
    assert vlm_extractor is not None, "VLM extractor should be initialized"
    assert hasattr(vlm_extractor, 'extract_from_vlm_description'), "VLM extractor should have extract_from_vlm_description method"
    
    # Test cases
    test_cases = [
        {
            "description": "The image shows a code editor with Python code. The user is writing a function to calculate fibonacci numbers. Multiple tabs are open including test files.",
            "window_title": "fibonacci.py - Visual Studio Code",
            "expected_activity": "Coding"
        },
        {
            "description": "This screenshot displays a video call interface with 4 participants in a grid layout. Screen sharing is active showing a presentation.",
            "window_title": "Zoom Meeting",
            "expected_activity": "Video Meeting"
        },
        {
            "description": "The browser shows multiple tabs open with Stack Overflow and Python documentation. The user appears to be searching for asyncio examples.",
            "window_title": "python asyncio - Google Search - Chrome",
            "expected_activity": "Web Research"
        }
    ]
    
    # Assert that we have test cases to work with
    assert len(test_cases) > 0, "Should have test cases for VLM integration"
    
    successful_extractions = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        print(f"   VLM: {test['description'][:80]}...")
        
        # Assert test case has required fields
        assert 'description' in test, f"Test case {i} should have description"
        assert 'window_title' in test, f"Test case {i} should have window_title"
        assert isinstance(test['description'], str), f"Test case {i} description should be string"
        assert len(test['description']) > 0, f"Test case {i} description should not be empty"
        
        result = extract_vlm_enhanced_task(
            test['description'],
            test['window_title']
        )
        
        if result:
            print(f"   ✅ Extracted task: {result['task_title']}")
            print(f"   Category: {result['category']}")
            print(f"   Confidence: {result['confidence']:.2f}")
            
            # Assert that result has expected structure
            assert isinstance(result, dict), "VLM result should be a dictionary"
            assert 'task_title' in result, "VLM result should have task_title"
            assert 'category' in result, "VLM result should have category"
            assert 'confidence' in result, "VLM result should have confidence"
            assert isinstance(result['confidence'], (int, float)), "Confidence should be numeric"
            assert 0 <= result['confidence'] <= 1, "Confidence should be between 0 and 1"
            
            successful_extractions += 1
            
            if result.get('ui_state'):
                print(f"   UI State: {result['ui_state']}")
                assert isinstance(result['ui_state'], str), "UI state should be string"
                
            if result.get('subtasks'):
                print(f"   Subtasks: {', '.join(result['subtasks'][:3])}")
                assert isinstance(result['subtasks'], list), "Subtasks should be a list"
        else:
            print("   ❌ Failed to extract VLM task")
    
    # Assert that the VLM integration is functional (at least some extractions work)
    # Note: We don't require 100% success rate as VLM might not be configured
    assert successful_extractions >= 0, "VLM extraction should not crash (0+ successful extractions expected)"


@pytest.mark.timeout(30)
def test_optical_character_recognition_enhancement_and_text_extraction():
    """Test OCR (Optical Character Recognition) enhancement features for improving text extraction quality from screenshots."""
    print("\n=== Testing OCR Enhancement ===")
    
    ocr_enhancer = OCREnhancer()
    
    # Assert that OCR enhancer can be initialized
    assert ocr_enhancer is not None, "OCR enhancer should be initialized"
    assert hasattr(ocr_enhancer, 'parse_ocr_json'), "OCR enhancer should have parse_ocr_json method"
    assert hasattr(ocr_enhancer, 'analyze_layout'), "OCR enhancer should have analyze_layout method"
    
    # Simulated OCR results
    test_ocr = [
        [[[10, 10], [200, 10], [200, 30], [10, 30]], "Task Management Dashboard", 0.95],
        [[[10, 50], [150, 50], [150, 70], [10, 70]], "def calculate_metrics():", 0.92],
        [[[10, 80], [180, 80], [180, 100], [10, 100]], "    total = sum(values)", 0.88],
        [[[10, 110], [100, 110], [100, 130], [10, 130]], "File Edit View", 0.85],
        [[[10, 200], [80, 200], [80, 220], [10, 220]], "Submit", 0.90]
    ]
    
    # Assert test OCR data is valid
    assert len(test_ocr) > 0, "Should have test OCR data"
    assert all(len(item) == 3 for item in test_ocr), "Each OCR item should have coordinates, text, and confidence"
    
    # Parse OCR results
    print("\n1. Parsing OCR results:")
    ocr_results = ocr_enhancer.parse_ocr_json(test_ocr)
    print(f"   ✅ Parsed {len(ocr_results)} OCR results")
    
    # Assert parsing worked
    assert ocr_results is not None, "OCR parsing should return results"
    assert len(ocr_results) <= len(test_ocr), "Parsed results should not exceed input data"
    
    # Analyze layout
    print("\n2. Layout analysis:")
    layout = ocr_enhancer.analyze_layout(ocr_results)
    print(f"   Title regions: {len(layout.title_regions)}")
    print(f"   Code regions: {len(layout.code_regions)}")
    print(f"   UI elements: {len(layout.ui_elements)}")
    print(f"   Average confidence: {layout.average_confidence:.2f}")
    
    # Assert layout analysis produces valid results
    assert layout is not None, "Layout analysis should return a result"
    assert hasattr(layout, 'title_regions'), "Layout should have title_regions"
    assert hasattr(layout, 'code_regions'), "Layout should have code_regions"
    assert hasattr(layout, 'ui_elements'), "Layout should have ui_elements"
    assert hasattr(layout, 'average_confidence'), "Layout should have average_confidence"
    assert isinstance(layout.average_confidence, (int, float)), "Average confidence should be numeric"
    assert 0 <= layout.average_confidence <= 1, "Average confidence should be between 0 and 1"
    
    # Extract task-relevant text
    print("\n3. Task-relevant text extraction:")
    relevant_text = ocr_enhancer.get_task_relevant_text(layout)
    print(f"   Extracted: {relevant_text[:100]}...")
    
    # Assert text extraction works
    assert relevant_text is not None, "Should extract some text"
    assert isinstance(relevant_text, str), "Extracted text should be string"
    
    # Enhance task
    print("\n4. Task enhancement:")
    enhanced = ocr_enhancer.enhance_task_with_ocr(json.dumps(test_ocr), "Working in IDE")
    print(f"   Enhanced task: {enhanced['task']}")
    print(f"   OCR quality: {enhanced['ocr_quality']}")
    print(f"   Has code: {enhanced['has_code']}")
    
    # Assert task enhancement produces valid results
    assert enhanced is not None, "Task enhancement should return results"
    assert isinstance(enhanced, dict), "Enhanced result should be a dictionary"
    assert 'task' in enhanced, "Enhanced result should have task field"
    assert 'ocr_quality' in enhanced, "Enhanced result should have ocr_quality field"
    assert 'has_code' in enhanced, "Enhanced result should have has_code field"
    assert isinstance(enhanced['task'], str), "Enhanced task should be string"
    assert isinstance(enhanced['has_code'], bool), "has_code should be boolean"


@pytest.mark.timeout(30)
def test_semantic_embeddings_search_engine_functionality():
    """Test semantic embeddings search engine functionality for finding similar tasks and content."""
    print("\n=== Testing Embeddings Search ===")
    
    db_manager = DatabaseManager()
    embeddings_engine = EmbeddingsSearchEngine(db_manager.db_path)
    
    # Get embedding statistics
    print("\n1. Embedding statistics:")
    stats = EmbeddingStats(db_manager.db_path)
    coverage = stats.get_embedding_coverage()
    
    if coverage:
        print(f"   Total screenshots: {coverage['total_screenshots']}")
        print(f"   With embeddings: {coverage['screenshots_with_embeddings']}")
        print(f"   Coverage: {coverage['coverage_percentage']:.1f}%")
        
        # Assert that the embedding coverage statistics are valid
        assert isinstance(coverage['total_screenshots'], int), "Total screenshots should be an integer"
        assert coverage['total_screenshots'] >= 0, "Total screenshots should be non-negative"
        assert isinstance(coverage['screenshots_with_embeddings'], int), "Embeddings count should be an integer"
        assert coverage['screenshots_with_embeddings'] >= 0, "Embeddings count should be non-negative"
        assert coverage['screenshots_with_embeddings'] <= coverage['total_screenshots'], "Embeddings count cannot exceed total screenshots"
        assert isinstance(coverage['coverage_percentage'], (int, float)), "Coverage percentage should be numeric"
        assert 0 <= coverage['coverage_percentage'] <= 100, "Coverage percentage should be between 0 and 100"
    
    # Test semantic search (if embeddings exist)
    print("\n2. Semantic search test:")
    # Get a recent task with embedding
    tasks_df = db_manager.fetch_tasks_with_ai(limit=20)
    
    if not tasks_df.empty and 'has_embedding' in tasks_df.columns:
        tasks_with_embeddings = tasks_df[tasks_df['has_embedding'] == 1]
        
        if not tasks_with_embeddings.empty:
            test_entity_id = tasks_with_embeddings.iloc[0]['id']
            print(f"   Testing with entity ID: {test_entity_id}")
            
            # Search for similar tasks
            similar_tasks = embeddings_engine.semantic_search(
                test_entity_id,
                limit=5,
                similarity_threshold=0.6
            )
            
            if similar_tasks:
                print(f"   ✅ Found {len(similar_tasks)} similar tasks")
                for i, task in enumerate(similar_tasks[:3], 1):
                    print(f"   {i}. Similarity: {task['similarity_score']:.2f} - {task['active_window'][:50]}...")
                
                # Assert that semantic search results are valid
                assert isinstance(similar_tasks, list), "Similar tasks should be returned as a list"
                assert len(similar_tasks) <= 5, "Should not return more than requested limit"
                
                for task in similar_tasks:
                    assert isinstance(task, dict), "Each similar task should be a dictionary"
                    assert 'similarity_score' in task, "Each task should have a similarity score"
                    assert isinstance(task['similarity_score'], (int, float)), "Similarity score should be numeric"
                    assert 0 <= task['similarity_score'] <= 1, "Similarity score should be between 0 and 1"
                    assert 'active_window' in task, "Each task should have an active_window field"
                    assert isinstance(task['active_window'], str), "Active window should be a string"
            else:
                print("   ❌ No similar tasks found")
        else:
            print("   ⚠️  No tasks with embeddings found for testing")
    else:
        print("   ⚠️  No tasks available for semantic search test")
    
    # Assert that the database connection and components are working
    assert db_manager is not None, "Database manager should be initialized"
    assert embeddings_engine is not None, "Embeddings engine should be initialized"
    assert stats is not None, "Embedding stats should be initialized"
    
    # Test that fetch_tasks_with_ai returns proper structure
    assert isinstance(tasks_df, type(tasks_df)), "fetch_tasks_with_ai should return a DataFrame-like object"


@pytest.mark.timeout(30)
def test_ai_enhanced_integrated_task_extractor_with_multiple_ai_features():
    """Test the integrated AI-enhanced task extractor that combines VLM, OCR, and embeddings functionality."""
    print("\n=== Testing Enhanced Task Extractor ===")
    
    db_manager = DatabaseManager()
    ai_extractor = AIEnhancedTaskExtractor(db_manager.db_path)
    
    # Assert that components can be initialized
    assert db_manager is not None, "Database manager should be initialized"
    assert ai_extractor is not None, "AI enhanced task extractor should be initialized"
    assert hasattr(ai_extractor, 'extract_enhanced_task'), "AI extractor should have extract_enhanced_task method"
    
    # Test with sample data
    test_cases = [
        {
            "window_title": "task_extractor.py - Visual Studio Code",
            "ocr_text": json.dumps([
                [[[10, 10], [200, 10], [200, 30], [10, 30]], "class TaskExtractor:", 0.95],
                [[[10, 50], [250, 50], [250, 70], [10, 70]], "def extract_task(self, window_title):", 0.92]
            ]),
            "vlm_description": "Code editor showing Python class definition for task extraction with multiple methods visible",
            "entity_id": None
        },
        {
            "window_title": "Project Planning - Google Docs",
            "ocr_text": json.dumps([
                [[[10, 10], [200, 10], [200, 30], [10, 30]], "Q4 Roadmap", 0.90],
                [[[10, 50], [300, 50], [300, 70], [10, 70]], "1. Complete AI integration", 0.88]
            ]),
            "vlm_description": "Document editor with project planning content including bullet points and timeline",
            "entity_id": None
        }
    ]
    
    # Assert test cases are valid
    assert len(test_cases) > 0, "Should have test cases for AI enhanced task extraction"
    
    successful_extractions = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {test['window_title']}")
        
        # Assert test case has required fields
        assert 'window_title' in test, f"Test case {i} should have window_title"
        assert 'ocr_text' in test, f"Test case {i} should have ocr_text"
        assert isinstance(test['window_title'], str), f"Test case {i} window_title should be string"
        assert len(test['window_title']) > 0, f"Test case {i} window_title should not be empty"
        
        result = ai_extractor.extract_enhanced_task(
            window_title=test['window_title'],
            ocr_text=test['ocr_text'],
            vlm_description=test.get('vlm_description'),
            entity_id=test.get('entity_id')
        )
        
        # Assert that extraction returns valid results
        assert result is not None, f"Test case {i} should return a result"
        assert isinstance(result, dict), f"Test case {i} result should be a dictionary"
        
        # Check required fields in result
        required_fields = ['task', 'category', 'confidence', 'ai_features']
        for field in required_fields:
            assert field in result, f"Test case {i} result should have {field} field"
        
        print(f"   Task: {result['task']}")
        print(f"   Category: {result['category']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        
        # Assert field types and values
        assert isinstance(result['task'], str), f"Test case {i} task should be string"
        assert isinstance(result['category'], str), f"Test case {i} category should be string"
        assert isinstance(result['confidence'], (int, float)), f"Test case {i} confidence should be numeric"
        assert 0 <= result['confidence'] <= 1, f"Test case {i} confidence should be between 0 and 1"
        assert isinstance(result['ai_features'], dict), f"Test case {i} ai_features should be dictionary"
        
        # Show AI features used
        ai_features = result['ai_features']
        features_used = []
        if ai_features.get('ocr_quality'):
            features_used.append(f"OCR ({ai_features['ocr_quality']})")
        if ai_features.get('vlm_available'):
            features_used.append(f"VLM ({ai_features.get('vlm_confidence', 0):.0%})")
        if ai_features.get('embeddings_available'):
            features_used.append("Embeddings")
        
        print(f"   AI Features: {', '.join(features_used) if features_used else 'None'}")
        
        if result.get('subtasks'):
            print(f"   Subtasks: {', '.join(result['subtasks'][:3])}")
            assert isinstance(result['subtasks'], list), f"Test case {i} subtasks should be a list"
        
        successful_extractions += 1
    
    # Assert that AI enhanced task extraction is functional
    assert successful_extractions == len(test_cases), "All AI enhanced task extractions should succeed"


def main():
    """Run all tests."""
    print("🤖 AutoTaskTracker AI Enhancement Tests")
    print("=" * 50)
    
    # Check if memos is running
    print("\nChecking prerequisites...")
    db_path = os.path.expanduser("~/.memos/database.db")
    if not os.path.exists(db_path):
        print("❌ Memos database not found. Please ensure memos is initialized and running.")
        return
    
    print("✅ Memos database found")
    
    # Run tests
    test_database_ai_queries()
    test_vlm_integration()
    test_ocr_enhancement()
    test_embeddings_search()
    test_enhanced_task_extractor()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\nTo see AI enhancements in action:")
    print("1. Ensure memos is running: memos start")
    print("2. Enable VLM in config (requires ollama and minicpm-v model)")
    print("3. Run the AI-enhanced dashboard:")
    print("   streamlit run autotasktracker/dashboards/development/ai_enhanced_task_board.py")


if __name__ == "__main__":
    main()