#!/usr/bin/env python3
"""
Test Llama Session Processor
Tests the new session reasoning functionality for dual-model implementation.
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.ai.session_processor import LlamaSessionProcessor, create_session_processor
from autotasktracker.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_mock_session_data():
    """Create mock session data for testing."""
    base_time = datetime.now() - timedelta(hours=1)
    
    # Simulate a coding session
    mock_data = []
    
    # Session 1: Coding session (30 minutes)
    for i in range(8):
        timestamp = base_time + timedelta(minutes=i*3)
        mock_data.append({
            'timestamp': timestamp.isoformat(),
            'entity_id': f'entity_{i}',
            'vlm_result': {
                'app_type': 'IDE',
                'tasks': 'Software Development',
                'category': 'Development',
                'description': f'User is editing Python code in an IDE. File visible: main.py. The code shows function definitions and debugging activities. Step {i+1} of coding session.',
                'confidence': 0.9
            }
        })
    
    # 10-minute break (session boundary)
    break_time = base_time + timedelta(minutes=25)
    
    # Session 2: Research session (20 minutes)
    for i in range(6):
        timestamp = break_time + timedelta(minutes=i*3)
        mock_data.append({
            'timestamp': timestamp.isoformat(),
            'entity_id': f'entity_{i+8}',
            'vlm_result': {
                'app_type': 'Browser',
                'tasks': 'Web Browsing',
                'category': 'Research',
                'description': f'User is browsing documentation and tutorials. Reading about Python libraries and best practices. Research step {i+1}.',
                'confidence': 0.8
            }
        })
    
    # Session 3: Meeting (15 minutes)
    meeting_time = break_time + timedelta(minutes=25)
    for i in range(5):
        timestamp = meeting_time + timedelta(minutes=i*3)
        mock_data.append({
            'timestamp': timestamp.isoformat(),
            'entity_id': f'entity_{i+14}',
            'vlm_result': {
                'app_type': 'Meeting',
                'tasks': 'Video Conference',
                'category': 'Communication',
                'description': f'User is in a video meeting. Screen shows participants and shared presentation. Meeting minute {i*3+1}.',
                'confidence': 0.9
            }
        })
    
    return mock_data


def test_session_boundary_detection():
    """Test session boundary detection."""
    logger.info("Testing session boundary detection...")
    
    processor = create_session_processor()
    mock_data = create_mock_session_data()
    
    # Test boundary detection
    boundaries = processor.detect_session_boundaries(mock_data)
    
    logger.info(f"Detected {len(boundaries)} session boundaries")
    for i, boundary in enumerate(boundaries):
        duration = (boundary.end_time - boundary.start_time).total_seconds() / 60
        logger.info(f"Session {i+1}: {boundary.boundary_type}, Duration: {duration:.1f} minutes")
    
    return len(boundaries) > 0


def test_session_workflow_analysis():
    """Test workflow analysis for a single session."""
    logger.info("Testing session workflow analysis...")
    
    processor = create_session_processor()
    mock_data = create_mock_session_data()
    
    # Test analysis on first session (coding)
    coding_session = mock_data[:8]  # First 8 items (coding session)
    
    analysis = processor.analyze_session_workflow(coding_session)
    
    if 'error' in analysis:
        logger.error(f"Session analysis failed: {analysis['error']}")
        return False
    
    logger.info("Session analysis successful:")
    logger.info(f"Workflow type: {analysis.get('workflow_type', 'Unknown')}")
    logger.info(f"Main activities: {analysis.get('main_activities', [])}")
    logger.info(f"Efficiency: {analysis.get('efficiency', 'Unknown')}")
    logger.info(f"Focus level: {analysis.get('focus_level', 'Unknown')}")
    
    return 'workflow_type' in analysis


def test_chunk_and_summarize():
    """Test complete chunk-and-summarize workflow."""
    logger.info("Testing chunk-and-summarize workflow...")
    
    processor = create_session_processor()
    mock_data = create_mock_session_data()
    
    # Test complete workflow analysis
    workflow_analysis = processor.chunk_and_summarize_workflow(mock_data)
    
    if 'error' in workflow_analysis:
        logger.error(f"Workflow analysis failed: {workflow_analysis['error']}")
        return False
    
    logger.info("Complete workflow analysis successful:")
    
    # Print overall summary
    overall = workflow_analysis.get('overall_summary', {})
    logger.info(f"Primary workflow: {overall.get('primary_workflow_type', 'Unknown')}")
    logger.info(f"Total duration: {overall.get('total_duration_minutes', 0):.1f} minutes")
    logger.info(f"Total sessions: {overall.get('total_sessions', 0)}")
    logger.info(f"Unique activities: {overall.get('activity_count', 0)}")
    
    # Print session boundaries
    boundaries = workflow_analysis.get('session_boundaries', [])
    logger.info(f"Session boundaries detected: {len(boundaries)}")
    
    # Print individual session analyses
    sessions = workflow_analysis.get('session_analyses', [])
    logger.info(f"Individual session analyses: {len(sessions)}")
    for i, session in enumerate(sessions):
        logger.info(f"  Session {i+1}: {session.get('workflow_type', 'Unknown')} "
                   f"({session.get('session_boundary', {}).get('duration_minutes', 0):.1f} min)")
    
    return 'overall_summary' in workflow_analysis


def test_llama3_connectivity():
    """Test basic Llama3 connectivity."""
    logger.info("Testing Llama3 connectivity...")
    
    processor = create_session_processor()
    
    # Simple test prompt
    response = processor._call_llama3("Hello, can you respond with 'Llama3 is working'?", temperature=0.0)
    
    if response:
        logger.info(f"Llama3 response: {response[:100]}...")
        return "working" in response.lower() or "hello" in response.lower()
    else:
        logger.error("Llama3 connectivity test failed")
        return False


def main():
    """Main test function."""
    logger.info("Starting Llama Session Processor tests...")
    
    tests = [
        ("Llama3 Connectivity", test_llama3_connectivity),
        ("Session Boundary Detection", test_session_boundary_detection),
        ("Session Workflow Analysis", test_session_workflow_analysis),
        ("Chunk and Summarize", test_chunk_and_summarize)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            success = test_func()
            results[test_name] = success
            status = "✓ PASSED" if success else "✗ FAILED"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*60)
    print("LLAMA SESSION PROCESSOR TEST RESULTS")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Session processor is ready for dual-model implementation.")
        return 0
    elif passed > 0:
        print("⚠ Some tests passed. Review failures and retry.")
        return 1
    else:
        print("❌ All tests failed. Check Llama3 setup and configuration.")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)