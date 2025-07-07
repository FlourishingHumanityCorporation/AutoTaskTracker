#!/usr/bin/env python3
"""
Test Deterministic VLM Processing
Tests VLM processing with temperature 0.0 for consistent, deterministic output.
"""
import sys
import os
import time
import json
import logging
from pathlib import Path
from PIL import Image, ImageDraw
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.config import get_config
from autotasktracker.ai.vlm_processor import SmartVLMProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_image():
    """Create a deterministic test image."""
    try:
        # Create test image with consistent content
        img = Image.new('RGB', (600, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add title
        draw.text((20, 20), "Deterministic VLM Test", fill='black')
        draw.text((20, 50), "Temperature: 0.0 for consistent output", fill='blue')
        
        # Add structured content that should produce consistent analysis
        draw.text((20, 100), "Application: Code Editor", fill='black')
        draw.text((20, 130), "File: main.py", fill='green')
        draw.text((20, 160), "Task: Writing Python function", fill='purple')
        
        # Add UI elements
        draw.rectangle([20, 200, 300, 230], outline='blue', width=2)
        draw.text((30, 210), "Save File", fill='blue')
        
        draw.rectangle([320, 200, 500, 230], outline='red', width=2)
        draw.text((330, 210), "Run Code", fill='red')
        
        # Add code-like content
        draw.text((20, 260), "def calculate_sum(a, b):", fill='black')
        draw.text((40, 280), "return a + b", fill='black')
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Failed to create test image: {e}")
        return None


def test_deterministic_processing(num_runs=3):
    """Test VLM processing multiple times to verify deterministic output."""
    logger.info(f"Testing deterministic VLM processing with {num_runs} runs...")
    
    # Get configuration
    config = get_config()
    logger.info(f"VLM temperature: {config.VLM_TEMPERATURE}")
    
    if config.VLM_TEMPERATURE != 0.0:
        logger.warning(f"Temperature is {config.VLM_TEMPERATURE}, expected 0.0 for deterministic processing")
    
    # Create test image
    test_image = create_test_image()
    if not test_image:
        logger.error("Failed to create test image")
        return False
    
    results = []
    processing_times = []
    
    try:
        # Initialize VLM processor
        processor = SmartVLMProcessor()
        
        for run in range(num_runs):
            logger.info(f"Run {run + 1}/{num_runs}...")
            
            start_time = time.time()
            result = processor.process_image(
                image_path=test_image,
                window_title="Deterministic Test - Code Editor",
                priority="normal"
            )
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
            
            if result:
                # Extract key fields for comparison
                comparison_result = {
                    'description': result.get('description', ''),
                    'tasks': result.get('tasks', ''),
                    'category': result.get('category', ''),
                    'app_type': result.get('app_type', ''),
                    'confidence': result.get('confidence', 0)
                }
                results.append(comparison_result)
                logger.info(f"Run {run + 1} completed in {processing_time:.2f}s")
                logger.info(f"Task extracted: {result.get('tasks', 'None')}")
            else:
                logger.error(f"Run {run + 1} failed - no result")
                return False
        
        # Analyze results for consistency
        logger.info("\nAnalyzing deterministic consistency...")
        
        # Compare descriptions
        descriptions = [r['description'] for r in results]
        unique_descriptions = set(descriptions)
        
        # Compare extracted tasks
        tasks = [r['tasks'] for r in results]
        unique_tasks = set(tasks)
        
        # Compare categories
        categories = [r['category'] for r in results]
        unique_categories = set(categories)
        
        # Results summary
        consistency_report = {
            'total_runs': num_runs,
            'avg_processing_time': sum(processing_times) / len(processing_times),
            'min_processing_time': min(processing_times),
            'max_processing_time': max(processing_times),
            'description_consistency': len(unique_descriptions) == 1,
            'task_consistency': len(unique_tasks) == 1,
            'category_consistency': len(unique_categories) == 1,
            'unique_descriptions': len(unique_descriptions),
            'unique_tasks': len(unique_tasks),
            'unique_categories': len(unique_categories),
            'sample_description': descriptions[0][:200] + "..." if descriptions[0] else "None",
            'sample_task': tasks[0] if tasks[0] else "None",
            'sample_category': categories[0] if categories[0] else "None"
        }
        
        # Print detailed results
        print("\n" + "="*60)
        print("DETERMINISTIC VLM PROCESSING RESULTS")
        print("="*60)
        print(f"Temperature: {config.VLM_TEMPERATURE}")
        print(f"Total Runs: {consistency_report['total_runs']}")
        print(f"Average Processing Time: {consistency_report['avg_processing_time']:.2f}s")
        print(f"Time Range: {consistency_report['min_processing_time']:.2f}s - {consistency_report['max_processing_time']:.2f}s")
        print()
        
        # Consistency analysis
        print("CONSISTENCY ANALYSIS:")
        desc_status = "✓" if consistency_report['description_consistency'] else "✗"
        task_status = "✓" if consistency_report['task_consistency'] else "✗"
        cat_status = "✓" if consistency_report['category_consistency'] else "✗"
        
        print(f"{desc_status} Description Consistency: {consistency_report['unique_descriptions']} unique outputs")
        print(f"{task_status} Task Consistency: {consistency_report['unique_tasks']} unique outputs")
        print(f"{cat_status} Category Consistency: {consistency_report['unique_categories']} unique outputs")
        print()
        
        # Sample outputs
        print("SAMPLE OUTPUTS:")
        print(f"Task: {consistency_report['sample_task']}")
        print(f"Category: {consistency_report['sample_category']}")
        print(f"Description: {consistency_report['sample_description']}")
        print()
        
        # Overall assessment
        all_consistent = (consistency_report['description_consistency'] and 
                         consistency_report['task_consistency'] and 
                         consistency_report['category_consistency'])
        
        if all_consistent:
            print("✓ DETERMINISTIC PROCESSING VERIFIED")
            print("Temperature 0.0 produces consistent outputs")
        else:
            print("⚠ PARTIAL DETERMINISM DETECTED")
            print("Some variation in outputs - may need further investigation")
        
        # Save detailed results
        results_file = Path("deterministic_test_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                'consistency_report': consistency_report,
                'all_results': results,
                'processing_times': processing_times
            }, f, indent=2)
        print(f"\nDetailed results saved to: {results_file}")
        
        return all_consistent
        
    except Exception as e:
        logger.error(f"Deterministic test failed: {e}")
        return False
    finally:
        # Cleanup
        if test_image and os.path.exists(test_image):
            try:
                os.unlink(test_image)
                logger.debug("Cleaned up test image")
            except Exception as e:
                logger.error(f"Failed to cleanup test image: {e}")


def main():
    """Main test function."""
    logger.info("Starting deterministic VLM processing test...")
    
    try:
        # Test deterministic processing
        success = test_deterministic_processing(num_runs=3)
        
        if success:
            print("\n✓ DETERMINISTIC VLM TEST PASSED")
            print("Ready for dual-model implementation")
            return 0
        else:
            print("\n⚠ DETERMINISTIC VLM TEST PARTIALLY SUCCESSFUL")
            print("Review results and consider adjustments")
            return 1
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n✗ Test failed with error: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)