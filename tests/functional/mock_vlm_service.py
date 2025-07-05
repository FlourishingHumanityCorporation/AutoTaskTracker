#!/usr/bin/env python3
"""
Mock VLM service for testing when Ollama is not available.
This allows VLM tests to run without requiring actual Ollama installation.
"""

import json
import time
import random
from typing import Dict, Any, Optional
from pathlib import Path
import numpy as np
from PIL import Image


class MockVLMService:
    """Mock VLM service that simulates Ollama's minicpm-v model."""
    
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "minicpm-v"
        self.is_running = True
        self.response_cache = {}
        
    def check_availability(self) -> bool:
        """Simulate checking if Ollama is available."""
        return self.is_running
    
    def describe_screenshot(self, image_path: str, window_title: str, 
                          prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate a mock VLM description based on image and window title."""
        
        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.3))
        
        # Generate description based on window title patterns
        window_lower = window_title.lower() if window_title else ""
        
        # Detect content type
        if 'code' in window_lower or 'visual studio' in window_lower:
            content_type = "IDE"
            description = f"The image shows a code editor with Python code visible. Multiple files are open in tabs. The main editor displays a class definition with several methods. Syntax highlighting is applied with different colors for keywords, strings, and comments."
            main_activity = "Software development"
            ui_elements = ["code editor", "file tabs", "syntax highlighting", "line numbers"]
            
        elif 'terminal' in window_lower or 'console' in window_lower:
            content_type = "Terminal"
            description = f"The image shows a terminal window with command line output. Several commands have been executed and their output is displayed. The prompt indicates the current directory and user."
            main_activity = "Command line operations"
            ui_elements = ["terminal prompt", "command output", "text display"]
            
        elif 'chrome' in window_lower or 'firefox' in window_lower or 'browser' in window_lower:
            content_type = "Browser"
            description = f"The image shows a web browser with multiple tabs open. The active tab displays a webpage with text content and some images. The address bar and browser controls are visible at the top."
            main_activity = "Web browsing"
            ui_elements = ["browser tabs", "address bar", "webpage content", "navigation buttons"]
            
        elif 'zoom' in window_lower or 'teams' in window_lower or 'meet' in window_lower:
            content_type = "Meeting"
            description = f"The image shows a video conferencing application with multiple participant windows in a grid layout. Meeting controls are visible at the bottom including mute, video, and screen sharing options."
            main_activity = "Video conference"
            ui_elements = ["participant grid", "meeting controls", "video feeds", "chat panel"]
            
        elif 'slack' in window_lower or 'discord' in window_lower:
            content_type = "Chat"
            description = f"The image shows a chat application with multiple channels listed on the left. The main area displays a conversation with several messages. User avatars and timestamps are visible."
            main_activity = "Team communication"
            ui_elements = ["channel list", "message area", "user avatars", "input field"]
            
        else:
            content_type = "Application"
            description = f"The image shows an application window with various UI elements. The window title indicates '{window_title}'. The interface contains standard application controls and content area."
            main_activity = "General application usage"
            ui_elements = ["window controls", "menu bar", "content area", "status bar"]
        
        # Add some variation
        if random.random() > 0.5:
            description += " The overall layout is clean and organized."
        
        # Create structured result
        result = {
            "description": description,
            "content_type": content_type,
            "main_activity": main_activity,
            "ui_elements": ui_elements,
            "confidence": random.uniform(0.85, 0.95),
            "processing_time": time.time(),
            "model": self.model
        }
        
        return result
    
    def compute_perceptual_hash(self, image_path: str) -> str:
        """Generate a mock perceptual hash."""
        try:
            # Get image size for hash
            img = Image.open(image_path)
            size = img.size[0] * img.size[1]
            
            # Generate deterministic hash based on file path
            import hashlib
            path_hash = hashlib.md5(str(image_path).encode()).hexdigest()[:16]
            
            # Format: size_hash
            return f"{size}_{path_hash}"
            
        except Exception:
            # Fallback hash
            return f"0_{random.randint(1000000, 9999999)}"
    
    def process_image(self, image_path: str, entity_id: str, window_title: str,
                     ocr_text: Optional[str] = None) -> Dict[str, Any]:
        """Process image and return VLM results."""
        
        # Check cache
        cache_key = f"{image_path}_{window_title}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]
        
        # Generate result
        result = self.describe_screenshot(image_path, window_title)
        
        # Add entity-specific data
        result['entity_id'] = entity_id
        result['image_path'] = str(image_path)
        result["active_window"] = window_title
        
        # Cache result
        self.response_cache[cache_key] = result
        
        return result


# Global mock instance
_mock_vlm = None

def get_mock_vlm() -> MockVLMService:
    """Get or create mock VLM service instance."""
    global _mock_vlm
    if _mock_vlm is None:
        _mock_vlm = MockVLMService()
    return _mock_vlm


def patch_vlm_processor():
    """Patch VLMProcessor to use mock service when Ollama is not available."""
    import sys
    from unittest.mock import patch
    
    # Create mock methods
    mock_vlm = get_mock_vlm()
    
    def mock_check_availability(self):
        return mock_vlm.check_availability()
    
    def mock_describe_screenshot(self, image_path, window_title, prompt=None):
        result = mock_vlm.describe_screenshot(image_path, window_title, prompt)
        return result['description']
    
    def mock_compute_perceptual_hash(self, image_path):
        return mock_vlm.compute_perceptual_hash(image_path)
    
    def mock_process_image(self, image_path, entity_id, window_title, ocr_text=None):
        return mock_vlm.process_image(image_path, entity_id, window_title, ocr_text)
    
    # Apply patches
    patches = [
        patch('autotasktracker.ai.vlm_processor.SmartVLMProcessor.check_availability', mock_check_availability),
        patch('autotasktracker.ai.vlm_processor.SmartVLMProcessor.describe_screenshot', mock_describe_screenshot),
        patch('autotasktracker.ai.vlm_processor.SmartVLMProcessor.compute_perceptual_hash', mock_compute_perceptual_hash),
        patch('autotasktracker.ai.vlm_processor.SmartVLMProcessor.process_image', mock_process_image),
    ]
    
    return patches


if __name__ == "__main__":
    # Test the mock service
    mock = MockVLMService()
    
    print("Testing Mock VLM Service:")
    print(f"Available: {mock.check_availability()}")
    
    # Test different window types
    test_cases = [
        ("test.png", "main.py - Visual Studio Code"),
        ("test.png", "Terminal - bash"),
        ("test.png", "AutoTaskTracker - Google Chrome"),
        ("test.png", "Team Meeting - Zoom"),
        ("test.png", "general - Slack"),
    ]
    
    for image, window in test_cases:
        result = mock.describe_screenshot(image, window)
        print(f"\nWindow: {window}")
        print(f"Type: {result['content_type']}")
        print(f"Description: {result['description'][:100]}...")
        print(f"Confidence: {result['confidence']:.2f}")