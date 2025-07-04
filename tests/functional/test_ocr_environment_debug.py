#!/usr/bin/env python3
"""
Debug OCR environment issues to understand why OCR commands are failing.
This helps diagnose and fix OCR extraction on real screenshots.
"""

import json
import os
import sys
import subprocess
from pathlib import Path

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def test_tesseract_installation():
    """Check if Tesseract is properly installed."""
    print("\n🔍 Checking Tesseract Installation:")
    
    # Check tesseract command
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("   ✅ Tesseract is installed")
            print(f"   Version info:\n{result.stdout}")
        else:
            print("   ❌ Tesseract command failed")
            print(f"   Error: {result.stderr}")
            
    except FileNotFoundError:
        print("   ❌ Tesseract not found in PATH")
        print("   Install with: brew install tesseract (macOS)")
    except subprocess.TimeoutExpired:
        print("   ❌ Tesseract command timed out")


def test_python_environments():
    """Check Python environments for memos/pensieve."""
    print("\n🔍 Checking Python Environments:")
    
    # System Python
    print(f"   Current Python: {sys.executable}")
    print(f"   Version: {sys.version}")
    
    # Check venv Python
    venv_python = REPO_ROOT / "venv" / "bin" / "python"
    if venv_python.exists():
        print(f"\n   ✅ Venv Python found: {venv_python}")
        
        # Check venv Python version
        try:
            result = subprocess.run([str(venv_python), '--version'], 
                                  capture_output=True, text=True)
            print(f"   Venv Python version: {result.stdout.strip()}")
        except:
            print("   ⚠️ Could not get venv Python version")
    else:
        print("   ❌ Venv Python not found")
    
    # Check if memos is importable
    print("\n   Checking memos import:")
    
    # Try current Python
    try:
        import memos
        print(f"   ✅ memos importable in current Python")
    except ImportError:
        print(f"   ❌ memos not importable in current Python")
    
    # Try venv Python
    if venv_python.exists():
        cmd = [str(venv_python), "-c", "import memos; print('memos found')"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ memos importable in venv Python")
            else:
                print(f"   ❌ memos not importable in venv Python")
                print(f"   Error: {result.stderr}")
        except:
            print(f"   ❌ Failed to check memos in venv")


def test_memos_ocr_module():
    """Test importing the memos OCR module directly."""
    print("\n🔍 Testing memos OCR module:")
    
    # Test with different Python interpreters
    pythons_to_test = [
        ("Current Python", sys.executable),
        ("Venv Python", str(REPO_ROOT / "venv" / "bin" / "python"))
    ]
    
    for name, python_path in pythons_to_test:
        if not Path(python_path).exists():
            continue
            
        print(f"\n   Testing with {name}:")
        
        cmd = [python_path, "-c", """
import sys
try:
    from memos.entities.recognition import optical_character_recognition
    print("✅ OCR module imported successfully")
    print(f"OCR function: {optical_character_recognition}")
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
"""]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"   {result.stdout}")
            if result.stderr:
                print(f"   Stderr: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("   ❌ Command timed out")
        except Exception as e:
            print(f"   ❌ Failed to run: {e}")


def test_ocr_on_test_image():
    """Test OCR on a test image if available."""
    print("\n🔍 Testing OCR on test image:")
    
    # Look for test images
    test_images = [
        REPO_ROOT / "tests" / "assets" / "realistic_code_editor.png",
        REPO_ROOT / "tests" / "assets" / "sample_screenshot.png"
    ]
    
    test_image = None
    for img in test_images:
        if img.exists():
            test_image = img
            break
    
    if not test_image:
        print("   ⚠️ No test image found")
        return
    
    print(f"   Using test image: {test_image.name}")
    
    # Try OCR with different methods
    
    # Method 1: Direct Tesseract
    print("\n   Method 1: Direct Tesseract")
    try:
        cmd = ['tesseract', str(test_image), 'stdout', '-l', 'eng']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            text = result.stdout.strip()
            print(f"   ✅ OCR successful, extracted {len(text)} characters")
            if text:
                print(f"   Sample: {text[:100]}...")
        else:
            print(f"   ❌ OCR failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Tesseract error: {e}")
    
    # Method 2: Through memos module
    print("\n   Method 2: Through memos module")
    
    venv_python = REPO_ROOT / "venv" / "bin" / "python"
    if venv_python.exists():
        cmd = [str(venv_python), "-c", f"""
import sys
import json
sys.path.insert(0, '{REPO_ROOT}')
try:
    from memos.entities.recognition import optical_character_recognition
    result = optical_character_recognition('{test_image}')
    print(json.dumps({{'success': True, 'regions': len(result)}}, indent=2))
    if result and len(result) > 0:
        print(f'First region: {{result[0]}}')
except Exception as e:
    print(json.dumps({{'success': False, 'error': str(e)}}, indent=2))
"""]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            print(f"   Output: {result.stdout}")
            if result.stderr:
                print(f"   Stderr: {result.stderr}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")


def test_ocr_command_variations():
    """Test different OCR command variations to find what works."""
    print("\n🔍 Testing OCR command variations:")
    
    test_image = REPO_ROOT / "tests" / "assets" / "realistic_code_editor.png"
    if not test_image.exists():
        # Create a simple test image
        print("   Creating test image...")
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), "Test OCR Text", fill='black')
            draw.text((50, 100), "AutoTaskTracker", fill='blue')
            test_image = REPO_ROOT / "tests" / "assets" / "test_ocr_image.png"
            test_image.parent.mkdir(parents=True, exist_ok=True)
            img.save(test_image)
            print(f"   ✅ Created test image: {test_image}")
        except Exception as e:
            print(f"   ❌ Could not create test image: {e}")
            return
    
    # Different Python paths to try
    python_variations = [
        ("System Python", sys.executable),
        ("Venv Python", str(REPO_ROOT / "venv" / "bin" / "python")),
        ("Python3", "python3"),
        ("Python", "python")
    ]
    
    for py_name, py_path in python_variations:
        if py_path and (py_path == sys.executable or Path(py_path).exists() or not py_path.startswith('/')):
            print(f"\n   Trying with {py_name} ({py_path}):")
            
            # Simple import test
            cmd = [py_path, "-c", "import sys; print(f'Python {sys.version.split()[0]}')"]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"      Python version: {result.stdout.strip()}")
                    
                    # Try memos import
                    cmd = [py_path, "-c", """
try:
    import memos
    print('      ✅ memos module found')
except ImportError:
    print('      ❌ memos module not found')
"""]
                    subprocess.run(cmd, timeout=5)
                    
            except Exception as e:
                print(f"      ❌ Failed: {e}")


def test_alternative_ocr_approach():
    """Test alternative OCR approach using pytesseract if available."""
    print("\n🔍 Testing alternative OCR approach:")
    
    try:
        import pytesseract
        from PIL import Image
        
        print("   ✅ pytesseract is available")
        
        # Test on a simple image
        test_image = REPO_ROOT / "tests" / "assets" / "realistic_code_editor.png"
        if test_image.exists():
            try:
                img = Image.open(test_image)
                text = pytesseract.image_to_string(img)
                
                print(f"   ✅ pytesseract OCR successful")
                print(f"   Extracted {len(text)} characters")
                if text.strip():
                    print(f"   Sample: {text[:100].strip()}...")
                else:
                    print("   ⚠️ No text extracted")
                    
            except Exception as e:
                print(f"   ❌ pytesseract OCR failed: {e}")
        else:
            print("   ⚠️ Test image not found")
            
    except ImportError:
        print("   ⚠️ pytesseract not installed")
        print("   Install with: pip install pytesseract pillow")


if __name__ == "__main__":
    print("=== OCR Environment Debugging ===")
    
    test_tesseract_installation()
    test_python_environments()
    test_memos_ocr_module()
    test_ocr_on_test_image()
    test_ocr_command_variations()
    test_alternative_ocr_approach()
    
    print("\n=== Debugging Complete ===")
    print("\nRecommendations:")
    print("1. Ensure Tesseract is installed: brew install tesseract")
    print("2. Use venv Python for memos commands: /path/to/venv/bin/python")
    print("3. Consider using pytesseract as fallback: pip install pytesseract")
    print("4. Check that memos module is properly installed in venv")