#!/usr/bin/env python3
"""
Test VLM Temperature Configuration
Tests the new configurable temperature setting in VLM processor.
"""
import sys
import os
import time
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
    """Create a simple test image."""
    try:
        # Create test image
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add content
        draw.text((20, 20), "VLM Temperature Test", fill='black')
        draw.text((20, 50), "Testing configurable temperature", fill='blue')
        draw.text((20, 80), "Current setting: 0.0 (deterministic)", fill='red')
        
        # Add some UI elements
        draw.rectangle([20, 120, 200, 150], outline='blue', width=2)
        draw.text((30, 130), "Test Button", fill='blue')
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Failed to create test image: {e}")
        return None


def test_vlm_temperature():
    """Test VLM processing with current temperature setting."""
    logger.info("Testing VLM temperature configuration...")
    
    # Get configuration
    config = get_config()
    logger.info(f"Current VLM temperature: {config.VLM_TEMPERATURE}")
    
    # Create test image
    test_image = create_test_image()
    if not test_image:
        logger.error("Failed to create test image")
        return False
    
    try:
        # Initialize VLM processor
        processor = SmartVLMProcessor()
        
        # Process image
        logger.info("Processing test image...")
        start_time = time.time()
        
        result = processor.process_image(
            image_path=test_image,
            window_title="Temperature Test Window",
            priority="normal"
        )
        
        processing_time = time.time() - start_time
        
        if result:
            logger.info(f"✓ VLM processing successful in {processing_time:.2f}s")
            logger.info(f"Result type: {type(result)}")
            
            # Print key parts of result
            if isinstance(result, dict):
                if 'description' in result:
                    description = result['description'][:200] + "..." if len(result['description']) > 200 else result['description']
                    logger.info(f"Description: {description}")
                if 'tasks' in result:
                    logger.info(f"Extracted task: {result['tasks']}")
                if 'category' in result:
                    logger.info(f"Category: {result['category']}")
            
            return True
        else:
            logger.error("✗ VLM processing failed - no result returned")
            return False
            
    except Exception as e:
        logger.error(f"✗ VLM processing failed with error: {e}")
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
    logger.info("Starting VLM temperature configuration test...")
    
    try:
        # Test current temperature setting
        success = test_vlm_temperature()
        
        if success:
            print("✓ VLM temperature configuration test PASSED")
            print("Temperature setting is working correctly")
            return 0
        else:
            print("✗ VLM temperature configuration test FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"✗ Test failed with error: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)