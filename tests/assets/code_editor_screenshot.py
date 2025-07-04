#!/usr/bin/env python3
"""
Generate a realistic code editor screenshot for testing OCR and AI functionality.
This creates a PNG image that looks like a real VS Code window with Python code.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_code_editor_screenshot():
    """Create a realistic code editor screenshot for testing."""
    # Create a 1200x800 image (typical screenshot size)
    img = Image.new('RGB', (1200, 800), color='#1e1e1e')  # VS Code dark theme
    draw = ImageDraw.Draw(img)
    
    # Try to use a monospace font, fall back to default
    try:
        # Common monospace fonts on different systems
        font_paths = [
            '/System/Library/Fonts/Monaco.ttc',  # macOS
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',  # Linux
            'C:/Windows/Fonts/consola.ttf',  # Windows
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, 14)
                    break
                except:
                    continue
        
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw VS Code-like interface
    # Title bar
    draw.rectangle([0, 0, 1200, 30], fill='#2d2d30')
    draw.text((10, 8), "task_extractor.py - Visual Studio Code", fill='#cccccc', font=font)
    
    # Tab bar
    draw.rectangle([0, 30, 1200, 60], fill='#252526')
    draw.rectangle([0, 30, 150, 60], fill='#1e1e1e')  # Active tab
    draw.text((10, 38), "task_extractor.py", fill='#ffffff', font=font)
    draw.text((160, 38), "main.py", fill='#969696', font=font)
    
    # Sidebar
    draw.rectangle([0, 60, 250, 800], fill='#252526')
    draw.text((10, 80), "EXPLORER", fill='#cccccc', font=font)
    draw.text((10, 110), "📁 autotasktracker", fill='#cccccc', font=font)
    draw.text((25, 130), "📁 core", fill='#cccccc', font=font)
    draw.text((40, 150), "📄 task_extractor.py", fill='#ffffff', font=font)
    draw.text((40, 170), "📄 database.py", fill='#cccccc', font=font)
    
    # Main code area
    draw.rectangle([250, 60, 1200, 800], fill='#1e1e1e')
    
    # Line numbers
    line_numbers = [
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"
    ]
    
    y_start = 80
    line_height = 18
    
    for i, line_num in enumerate(line_numbers):
        y = y_start + (i * line_height)
        draw.text((260, y), line_num, fill='#858585', font=font)
    
    # Python code with syntax highlighting colors
    code_lines = [
        ('"""', '#6a9955'),  # Green for comments
        ('AutoTaskTracker - AI-powered task extraction', '#6a9955'),
        ('"""', '#6a9955'),
        ('', '#ffffff'),
        ('import os', '#c586c0'),  # Purple for keywords
        ('import json', '#c586c0'),
        ('from typing import Dict, List, Optional', '#c586c0'),
        ('', '#ffffff'),
        ('class TaskExtractor:', '#4ec9b0'),  # Teal for class names
        ('    """Extract tasks from screenshots."""', '#6a9955'),
        ('    ', '#ffffff'),
        ('    def __init__(self, db_path: str):', '#dcdcaa'),  # Yellow for function names
        ('        self.db_path = db_path', '#ffffff'),
        ('        self.ocr_engine = OCREngine()', '#ffffff'),
        ('    ', '#ffffff'),
        ('    def extract_task(self, window_title: str) -> Dict:', '#dcdcaa'),
        ('        """Extract task from window title."""', '#6a9955'),
        ('        if "code" in window_title.lower():', '#c586c0'),
        ('            return {"task": "Coding", "category": "Development"}', '#ffffff'),
        ('        return {"task": "Unknown", "category": "Other"}', '#ffffff'),
    ]
    
    for i, (code, color) in enumerate(code_lines[:20]):
        y = y_start + (i * line_height)
        draw.text((290, y), code, fill=color, font=font)
    
    # Status bar
    draw.rectangle([0, 770, 1200, 800], fill='#007acc')
    draw.text((10, 778), "✓ Python 3.11.5", fill='#ffffff', font=font)
    draw.text((150, 778), "UTF-8", fill='#ffffff', font=font)
    draw.text((200, 778), "Ln 12, Col 25", fill='#ffffff', font=font)
    
    return img

def save_screenshot():
    """Save the generated screenshot to the assets directory."""
    img = create_code_editor_screenshot()
    
    # Ensure assets directory exists
    assets_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(assets_dir, exist_ok=True)
    
    # Save the image
    output_path = os.path.join(assets_dir, 'realistic_code_editor.png')
    img.save(output_path, 'PNG')
    print(f"Created realistic code editor screenshot: {output_path}")
    return output_path

if __name__ == "__main__":
    save_screenshot()