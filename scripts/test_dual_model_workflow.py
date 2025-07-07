#!/usr/bin/env python3
"""
Test Dual-Model Workflow
Tests the complete dual-model processing workflow with VLM + Llama3 session analysis.
"""
import sys
import os
import time
import json
import logging
from pathlib import Path
from PIL import Image, ImageDraw
import tempfile
from datetime import datetime, timedelta
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.config import get_config
from autotasktracker.ai.dual_model_processor import DualModelProcessor, create_dual_model_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_screenshots(count: int = 5) -> List[str]:
    """Create test screenshots simulating a workflow session."""
    screenshots = []
    
    for i in range(count):
        try:
            # Create different types of screenshots to simulate workflow
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            if i < 2:
                # IDE/coding screenshots
                draw.text((20, 20), f"Code Editor - Step {i+1}", fill='black')
                draw.text((20, 50), "main.py - Python Development", fill='blue')
                draw.text((20, 80), f"def process_data_{i}():", fill='green')
                draw.text((40, 100), f"    return result_{i}", fill='green')
                app_type = "IDE"
            elif i < 4:
                # Browser/research screenshots
                draw.text((20, 20), f"Web Browser - Research {i+1}", fill='black')
                draw.text((20, 50), "Python Documentation", fill='blue')
                draw.text((20, 80), f"Reading about feature_{i}", fill='purple')
                app_type = "Browser"
            else:
                # Meeting/communication screenshots
                draw.text((20, 20), f"Video Meeting - Minute {i+1}", fill='black')
                draw.text((20, 50), "Team standup discussion", fill='blue')
                draw.text((20, 80), f"Discussing sprint item {i}", fill='red')
                app_type = "Meeting"
            
            # Add some UI elements
            draw.rectangle([20, 120, 300, 150], outline='gray', width=2)
            draw.text((30, 130), f"{app_type} Window", fill='gray')
            
            # Save screenshot
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            img.save(temp_file.name)
            screenshots.append(temp_file.name)
            logger.info(f"Created test screenshot {i+1}: {app_type} -> {temp_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to create test screenshot {i+1}: {e}")
    
    return screenshots


def test_single_screenshot_processing():
    """Test processing a single screenshot with dual-model."""
    logger.info("Testing single screenshot dual-model processing...")
    
    try:
        # Create dual-model processor
        processor = create_dual_model_processor()
        
        # Create test screenshot
        test_screenshots = create_test_screenshots(1)
        if not test_screenshots:
            logger.error("Failed to create test screenshot")
            return False
        
        # Process screenshot
        result = processor.process_screenshot(
            image_path=test_screenshots[0],
            window_title="Test IDE - main.py",
            entity_id=None  # No database entity for test
        )
        
        # Check result
        if result.success:
            logger.info("✓ Single screenshot processing successful")
            logger.info(f"Processing time: {result.processing_time:.2f}s")
            logger.info(f"Session ID: {result.session_id}")
            logger.info(f"VLM result: {result.vlm_result.get('tasks', 'None')}")
            
            if result.session_analysis:
                logger.info(f"Session analysis: {result.session_analysis.get('workflow_type', 'None')}")
            else:
                logger.info("Session analysis: Not available (need more screenshots)")
            
            return True
        else:
            logger.error(f"✗ Single screenshot processing failed: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"Single screenshot test failed: {e}")
        return False
    finally:
        # Cleanup
        for screenshot in test_screenshots:
            try:
                if os.path.exists(screenshot):
                    os.unlink(screenshot)
            except Exception as e:
                logger.error(f"Failed to cleanup {screenshot}: {e}")


def test_session_workflow():
    """Test complete session workflow with multiple screenshots."""
    logger.info("Testing dual-model session workflow...")
    
    test_screenshots = []
    try:
        # Create dual-model processor
        processor = create_dual_model_processor()
        
        # Create test screenshots for a workflow session
        test_screenshots = create_test_screenshots(5)
        if len(test_screenshots) < 5:
            logger.error("Failed to create enough test screenshots")
            return False
        
        # Process screenshots sequentially to build session
        results = []
        base_time = datetime.now()
        
        for i, screenshot_path in enumerate(test_screenshots):
            # Simulate time progression
            timestamp = base_time + timedelta(minutes=i*2)
            
            # Different window titles for different screenshot types
            if i < 2:
                window_title = f"PyCharm - main.py"
            elif i < 4:
                window_title = f"Chrome - Python Docs"
            else:
                window_title = f"Zoom - Team Meeting"
            
            result = processor.process_screenshot(
                image_path=screenshot_path,
                window_title=window_title,
                entity_id=None,
                timestamp=timestamp
            )
            
            results.append(result)
            logger.info(f"Processed screenshot {i+1}/5: {result.success}")
            
            # Check if session analysis becomes available
            if result.session_analysis:
                logger.info(f"Session analysis available: {result.session_analysis.get('workflow_type')}")
        
        # Finalize session
        processor.finalize_session()
        
        # Analyze results
        successful_results = [r for r in results if r.success]
        session_analyses = [r.session_analysis for r in results if r.session_analysis]
        
        logger.info(f"Session workflow results:")
        logger.info(f"  Total screenshots: {len(results)}")
        logger.info(f"  Successful processing: {len(successful_results)}")
        logger.info(f"  Session analyses generated: {len(session_analyses)}")
        
        # Debug: Show detailed results
        for i, result in enumerate(results):
            logger.info(f"  Result {i+1}: success={result.success}, session_id={result.session_id}")
        
        # Check session consistency
        session_ids = [r.session_id for r in results if r.session_id]
        unique_sessions = set(session_ids)
        
        logger.info(f"  Session IDs: {len(unique_sessions)} unique sessions")
        logger.info(f"  Session IDs: {list(unique_sessions)}")
        
        # Get processor status
        status = processor.get_session_status()
        logger.info(f"Final processor status:")
        logger.info(f"  Current session: {status['current_session_id']}")
        logger.info(f"  Screenshot count: {status['session_screenshot_count']}")
        
        # Debug the return condition
        test_result = len(successful_results) >= 4
        logger.info(f"Test condition: {len(successful_results)} >= 4 = {test_result}")
        
        return test_result
        
    except Exception as e:
        logger.error(f"Session workflow test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False
    finally:
        # Cleanup
        for screenshot in test_screenshots:
            try:
                if os.path.exists(screenshot):
                    os.unlink(screenshot)
            except Exception as e:
                logger.error(f"Failed to cleanup {screenshot}: {e}")


def test_batch_processing():
    """Test batch processing with dual-model."""
    logger.info("Testing dual-model batch processing...")
    
    test_screenshots = []
    try:
        # Create dual-model processor
        processor = create_dual_model_processor()
        
        # Create test screenshots
        test_screenshots = create_test_screenshots(3)
        if len(test_screenshots) < 3:
            logger.error("Failed to create test screenshots for batch processing")
            return False
        
        # Prepare window titles
        window_titles = [
            "PyCharm - main.py",
            "Chrome - Documentation", 
            "Slack - Team Chat"
        ]
        
        # Process batch
        start_time = time.time()
        results = processor.batch_process_screenshots(
            screenshot_paths=test_screenshots,
            window_titles=window_titles,
            entity_ids=[None] * len(test_screenshots)
        )
        processing_time = time.time() - start_time
        
        # Analyze batch results
        successful_results = [r for r in results if r.success]
        
        logger.info(f"Batch processing results:")
        logger.info(f"  Total screenshots: {len(results)}")
        logger.info(f"  Successful processing: {len(successful_results)}")
        logger.info(f"  Total processing time: {processing_time:.2f}s")
        logger.info(f"  Average time per screenshot: {processing_time/len(results):.2f}s")
        
        return len(successful_results) >= len(test_screenshots) * 0.8  # 80% success rate
        
    except Exception as e:
        logger.error(f"Batch processing test failed: {e}")
        return False
    finally:
        # Cleanup
        for screenshot in test_screenshots:
            try:
                if os.path.exists(screenshot):
                    os.unlink(screenshot)
            except Exception as e:
                logger.error(f"Failed to cleanup {screenshot}: {e}")


def test_memory_usage():
    """Test memory usage during dual-model processing."""
    logger.info("Testing dual-model memory usage...")
    
    try:
        # Try to import psutil for memory monitoring
        try:
            import psutil
            process = psutil.Process()
            memory_monitoring = True
        except ImportError:
            logger.warning("psutil not available - memory monitoring disabled")
            memory_monitoring = False
        
        # Get initial memory usage
        if memory_monitoring:
            initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
            logger.info(f"Initial memory usage: {initial_memory:.1f}MB")
        
        # Create processor and test screenshots
        processor = create_dual_model_processor()
        test_screenshots = create_test_screenshots(3)
        
        # Process screenshots and monitor memory
        for i, screenshot in enumerate(test_screenshots):
            result = processor.process_screenshot(
                image_path=screenshot,
                window_title=f"Test Window {i}",
                entity_id=None
            )
            
            if memory_monitoring:
                current_memory = process.memory_info().rss / (1024 * 1024)
                logger.info(f"Memory after screenshot {i+1}: {current_memory:.1f}MB")
        
        # Get final memory usage
        if memory_monitoring:
            final_memory = process.memory_info().rss / (1024 * 1024)
            memory_increase = final_memory - initial_memory
            logger.info(f"Final memory usage: {final_memory:.1f}MB")
            logger.info(f"Memory increase: {memory_increase:.1f}MB")
            
            # Check if memory usage is reasonable (< 500MB increase)
            return memory_increase < 500
        else:
            logger.info("Memory monitoring skipped - test passed")
            return True
        
    except Exception as e:
        logger.error(f"Memory usage test failed: {e}")
        return False
    finally:
        # Cleanup
        for screenshot in test_screenshots:
            try:
                if os.path.exists(screenshot):
                    os.unlink(screenshot)
            except Exception as e:
                logger.error(f"Failed to cleanup {screenshot}: {e}")


def main():
    """Main test function."""
    logger.info("Starting dual-model workflow tests...")
    
    # Check configuration
    config = get_config()
    logger.info(f"VLM Model: {config.VLM_MODEL_NAME}")
    logger.info(f"VLM Temperature: {config.VLM_TEMPERATURE}")
    logger.info(f"Llama3 Model: {config.LLAMA3_MODEL_NAME}")
    logger.info(f"Dual-model enabled: {config.ENABLE_DUAL_MODEL}")
    
    tests = [
        ("Single Screenshot Processing", test_single_screenshot_processing),
        ("Session Workflow", test_session_workflow),
        ("Batch Processing", test_batch_processing),
        ("Memory Usage", test_memory_usage)
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
    print("\n" + "="*70)
    print("DUAL-MODEL WORKFLOW TEST RESULTS")
    print("="*70)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dual-model workflow is ready for production.")
        return 0
    elif passed > 0:
        print("⚠ Some tests passed. Review failures and optimize.")
        return 1
    else:
        print("❌ All tests failed. Check model setup and configuration.")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)