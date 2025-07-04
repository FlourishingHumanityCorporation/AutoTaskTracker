# Functional Tests

This directory contains **real functional tests** that validate actual AutoTaskTracker functionality instead of using mocks.

## What These Tests Do

### 🎯 **Real OCR Processing** (`test_real_ocr_processing.py`)
- Uses actual Tesseract OCR on real images
- Tests OCR enhancement with generated screenshots
- Validates text extraction quality and error handling
- **Catches**: OCR configuration issues, text extraction failures, image processing problems

### 🗄️ **Real Database Workflows** (`test_real_database_workflows.py`)
- Tests actual SQLite database operations
- Validates schema integrity and data consistency
- Tests concurrent access and performance
- **Catches**: Database schema changes, connection issues, data corruption

### 🤖 **Real AI Processing** (`test_real_ai_processing.py`)
- Tests actual AI models and inference (when available)
- Validates embeddings, VLM, and task classification
- Tests AI performance and quality metrics
- **Catches**: AI model loading failures, inference quality degradation, performance issues

### 🔄 **Full Pipeline Integration** (`test_full_pipeline_integration.py`)
- Tests complete workflows from screenshot to dashboard
- Validates end-to-end data flow
- Tests performance characteristics under load
- **Catches**: Pipeline breaks, data flow issues, integration failures

## Running the Tests

### Run All Functional Tests
```bash
pytest tests/functional/ -v
```

### Run Specific Test Categories
```bash
# OCR functionality
pytest tests/functional/test_real_ocr_processing.py -v

# Database operations
pytest tests/functional/test_real_database_workflows.py -v

# AI processing
pytest tests/functional/test_real_ai_processing.py -v

# Full pipeline
pytest tests/functional/test_full_pipeline_integration.py -v
```

### Run with Detailed Output
```bash
pytest tests/functional/ -v -s --tb=short
```

## Test Requirements

### Prerequisites
- **Tesseract OCR**: Required for OCR tests
- **Virtual Environment**: Tests use `venv/bin/python` for Pensieve/memos
- **Test Assets**: Generated screenshots and sample data

### Optional Dependencies
- **sentence-transformers**: For embeddings tests
- **Ollama + minicpm-v**: For VLM tests
- **Pensieve/memos**: For full pipeline tests

### Test Data
Tests use realistic generated data:
- `assets/realistic_code_editor.png`: Generated VS Code screenshot
- `assets/sample_screenshot.png`: Provided test image
- Temporary databases with realistic activity data

## What Makes These Tests "Real"

### ❌ **Old Approach (Mocked)**
```python
# Fake OCR that never touches real images
class MockOCR:
    def process(self, image):
        return [["fake", "text", 0.9]]

# Fake Streamlit that doesn't test UI
class MockStreamlit:
    def title(self, text):
        print(f"TITLE: {text}")
```

### ✅ **New Approach (Real)**
```python
# Real OCR using actual Tesseract
result = subprocess.run([
    'python', '-c', 
    'from memos.entities.recognition import optical_character_recognition; '
    f'print(optical_character_recognition("{image_path}"))'
])

# Real database operations
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT * FROM entities WHERE file_type_group = 'image'")
actual_data = cursor.fetchall()
```

## Test Coverage

### ✅ **What IS Tested**
- Real OCR text extraction from images
- Actual database schema and operations
- Real AI model inference (when available)
- Complete data pipelines with real data
- Performance under realistic loads
- Error handling with real failure modes

### ⚠️ **Test Limitations**
- Some tests skip if dependencies unavailable (graceful degradation)
- VLM tests require Ollama setup
- Screenshot capture tests need GUI environment
- AI tests depend on model availability

## Test Categories

### **Fast Tests** (< 5 seconds)
- Database operations
- Task extraction
- Basic AI functionality

### **Moderate Tests** (5-30 seconds)
- OCR processing
- AI model inference
- Database workflows

### **Slow Tests** (30+ seconds)
- Full pipeline integration
- Performance benchmarks
- Large dataset processing

## Success Criteria

### **Tests Pass When:**
- All core functionality works with real data
- Performance meets acceptable thresholds
- Error handling works correctly
- Data integrity is maintained

### **Tests Skip When:**
- Dependencies are unavailable
- Environment doesn't support feature
- Optional components not configured

### **Tests Fail When:**
- Core functionality is broken
- Data corruption occurs
- Performance degrades significantly
- Required dependencies fail

## Maintenance

### Adding New Tests
1. Create test file in `tests/functional/`
2. Use real components, not mocks
3. Include performance assertions
4. Handle missing dependencies gracefully
5. Update this README

### Test Data Management
- Generate test data programmatically
- Use temporary files/databases
- Clean up resources in fixtures
- Document test asset requirements

---

**These tests validate that AutoTaskTracker actually works in real-world scenarios, not just in theory.**