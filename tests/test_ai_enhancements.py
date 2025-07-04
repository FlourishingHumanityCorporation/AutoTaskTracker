#!/usr/bin/env python3
"""
Test script for AI enhancements in AutoTaskTracker.
Validates VLM integration, embeddings search, and OCR enhancement.
"""
import os
import sys
import json
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.vlm_integration import VLMTaskExtractor, extract_vlm_enhanced_task
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from autotasktracker.ai.embeddings_search import EmbeddingsSearchEngine, EmbeddingStats
from autotasktracker.ai.ai_task_extractor import AIEnhancedTaskExtractor


def test_database_ai_queries():
    """Test database queries for AI data."""
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
    else:
        print("   ❌ No tasks found")


def test_vlm_integration():
    """Test VLM task extraction."""
    print("\n=== Testing VLM Integration ===")
    
    vlm_extractor = VLMTaskExtractor()
    
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
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        print(f"   VLM: {test['description'][:80]}...")
        
        result = extract_vlm_enhanced_task(
            test['description'],
            test['window_title']
        )
        
        if result:
            print(f"   ✅ Extracted task: {result['task_title']}")
            print(f"   Category: {result['category']}")
            print(f"   Confidence: {result['confidence']:.2f}")
            
            if result.get('ui_state'):
                print(f"   UI State: {result['ui_state']}")
                
            if result.get('subtasks'):
                print(f"   Subtasks: {', '.join(result['subtasks'][:3])}")
        else:
            print("   ❌ Failed to extract VLM task")


def test_ocr_enhancement():
    """Test OCR enhancement features."""
    print("\n=== Testing OCR Enhancement ===")
    
    ocr_enhancer = OCREnhancer()
    
    # Simulated OCR results
    test_ocr = [
        [[[10, 10], [200, 10], [200, 30], [10, 30]], "Task Management Dashboard", 0.95],
        [[[10, 50], [150, 50], [150, 70], [10, 70]], "def calculate_metrics():", 0.92],
        [[[10, 80], [180, 80], [180, 100], [10, 100]], "    total = sum(values)", 0.88],
        [[[10, 110], [100, 110], [100, 130], [10, 130]], "File Edit View", 0.85],
        [[[10, 200], [80, 200], [80, 220], [10, 220]], "Submit", 0.90]
    ]
    
    # Parse OCR results
    print("\n1. Parsing OCR results:")
    ocr_results = ocr_enhancer.parse_ocr_json(test_ocr)
    print(f"   ✅ Parsed {len(ocr_results)} OCR results")
    
    # Analyze layout
    print("\n2. Layout analysis:")
    layout = ocr_enhancer.analyze_layout(ocr_results)
    print(f"   Title regions: {len(layout.title_regions)}")
    print(f"   Code regions: {len(layout.code_regions)}")
    print(f"   UI elements: {len(layout.ui_elements)}")
    print(f"   Average confidence: {layout.average_confidence:.2f}")
    
    # Extract task-relevant text
    print("\n3. Task-relevant text extraction:")
    relevant_text = ocr_enhancer.get_task_relevant_text(layout)
    print(f"   Extracted: {relevant_text[:100]}...")
    
    # Enhance task
    print("\n4. Task enhancement:")
    enhanced = ocr_enhancer.enhance_task_with_ocr(json.dumps(test_ocr), "Working in IDE")
    print(f"   Enhanced task: {enhanced['task']}")
    print(f"   OCR quality: {enhanced['ocr_quality']}")
    print(f"   Has code: {enhanced['has_code']}")


def test_embeddings_search():
    """Test embeddings search functionality."""
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
            else:
                print("   ❌ No similar tasks found")
        else:
            print("   ⚠️  No tasks with embeddings found for testing")
    else:
        print("   ⚠️  No tasks available for semantic search test")


def test_enhanced_task_extractor():
    """Test the integrated enhanced task extractor."""
    print("\n=== Testing Enhanced Task Extractor ===")
    
    db_manager = DatabaseManager()
    ai_extractor = AIEnhancedTaskExtractor(db_manager.db_path)
    
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
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {test['window_title']}")
        
        result = ai_extractor.extract_enhanced_task(
            window_title=test['window_title'],
            ocr_text=test['ocr_text'],
            vlm_description=test.get('vlm_description'),
            entity_id=test.get('entity_id')
        )
        
        print(f"   Task: {result['task']}")
        print(f"   Category: {result['category']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        
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