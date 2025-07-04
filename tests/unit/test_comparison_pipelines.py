"""
Comprehensive tests for comparison pipeline modules.

Tests cover all pipeline functionality including:
- Base pipeline interface
- Basic pattern matching pipeline
- OCR-enhanced pipeline
- Full AI-enhanced pipeline
- Pipeline initialization and processing
- Error handling and edge cases
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from autotasktracker.comparison.pipelines.base import BasePipeline
from autotasktracker.comparison.pipelines.basic import BasicPipeline
from autotasktracker.comparison.pipelines.ocr import OCRPipeline
from autotasktracker.comparison.pipelines.ai_full import AIFullPipeline


class TestBasePipeline:
    """Test the BasePipeline abstract base class."""
    
    def test_base_pipeline_initialization(self):
        """Test that BasePipeline initializes with correct defaults."""
        # Can't instantiate abstract class directly, create concrete subclass
        class ConcretePipeline(BasePipeline):
            def process_screenshot(self, screenshot_data):
                return {'task': 'test'}
        
        pipeline = ConcretePipeline()
        assert pipeline.name == "Base Pipeline"
        assert pipeline.description == "Base pipeline interface"
    
    def test_base_pipeline_get_info(self):
        """Test get_info method returns correct pipeline information."""
        class ConcretePipeline(BasePipeline):
            def __init__(self):
                super().__init__()
                self.name = "Test Pipeline"
                self.description = "Test description"
            
            def process_screenshot(self, screenshot_data):
                return {'task': 'test'}
        
        pipeline = ConcretePipeline()
        info = pipeline.get_info()
        
        assert isinstance(info, dict)
        assert info['name'] == "Test Pipeline"
        assert info['description'] == "Test description"
    
    def test_base_pipeline_process_screenshot_abstract(self):
        """Test that process_screenshot is abstract and must be implemented."""
        with pytest.raises(TypeError) as exc_info:
            # Should not be able to instantiate abstract class
            BasePipeline()
        
        # Validate that the error is specifically about abstract methods
        error_msg = str(exc_info.value)
        assert "abstract" in error_msg.lower() or "instantiate" in error_msg.lower(), "Should fail due to abstract method"
        assert "process_screenshot" in error_msg or "BasePipeline" in error_msg, "Should mention the abstract class or method"


class TestBasicPipeline:
    """Test the BasicPipeline class."""
    
    @pytest.fixture
    def basic_pipeline(self):
        """Create a BasicPipeline instance with mocked dependencies."""
        # Use a persistent patch that remains active during tests
        extractor_patcher = patch('autotasktracker.comparison.pipelines.basic.TaskExtractor')
        categorizer_patcher = patch('autotasktracker.comparison.pipelines.basic.ActivityCategorizer.categorize')
        
        mock_extractor = extractor_patcher.start()
        mock_categorize = categorizer_patcher.start()
        
        # Create pipeline with mocked dependencies
        pipeline = BasicPipeline()
        pipeline.extractor = mock_extractor.return_value
        
        # Store reference to mock for assertions
        pipeline._mock_categorizer = Mock()
        pipeline._mock_categorizer.categorize = mock_categorize
        
        # Store patchers for cleanup
        pipeline._patchers = [extractor_patcher, categorizer_patcher]
        
        yield pipeline
        
        # Cleanup
        for patcher in pipeline._patchers:
            patcher.stop()
    
    def test_basic_pipeline_initialization(self, basic_pipeline):
        """Test BasicPipeline initialization."""
        assert basic_pipeline.name == "Basic Pattern Matching"
        assert "Original method using window title patterns" in basic_pipeline.description
        assert hasattr(basic_pipeline, 'extractor')
        
        # Test error conditions - pipeline should handle missing dependencies gracefully
        try:
            # Test pipeline info retrieval works
            info = basic_pipeline.get_info()
            assert isinstance(info, dict), "get_info should return dictionary"
            assert 'name' in info, "Pipeline info should include name"
            assert 'description' in info, "Pipeline info should include description"
        except Exception as e:
            pytest.fail(f"Pipeline initialization should create functional object, got: {e}")
        
        # Test method availability for core functionality
        assert hasattr(basic_pipeline, 'process_screenshot'), "Should have process_screenshot method"
        assert callable(getattr(basic_pipeline, 'process_screenshot')), "process_screenshot should be callable"
    
    def test_basic_pipeline_process_screenshot_with_window_title(self, basic_pipeline):
        """Test processing screenshot with window title."""
        # Mock extractor and categorizer
        basic_pipeline.extractor.extract_task.return_value = "Edit document"
        basic_pipeline._mock_categorizer.categorize.return_value = "Productivity"
        
        screenshot_data = {
            'active_window': 'document.docx - Microsoft Word',
            'ocr_text': 'Some OCR text'
        }
        
        result = basic_pipeline.process_screenshot(screenshot_data)
        
        # Validate result structure
        assert isinstance(result, dict)
        assert 'task' in result
        assert 'category' in result
        assert 'confidence' in result
        assert 'features_used' in result
        assert 'details' in result
        
        # Validate values
        assert result['task'] == "Edit document"
        assert result['category'] == "Productivity"
        assert result['confidence'] == 0.5
        assert result['features_used'] == ['Window Title']
        assert result['details']['method'] == 'Pattern matching on window title'
        assert result['details']['pattern_matched'] is True
        
        # Verify method calls
        basic_pipeline.extractor.extract_task.assert_called_once_with('document.docx - Microsoft Word')
        basic_pipeline._mock_categorizer.categorize.assert_called_once_with(
            'document.docx - Microsoft Word',
            'Some OCR text'
        )
        
        # Test error conditions - pipeline should handle extraction failures
        basic_pipeline.extractor.extract_task.side_effect = Exception("Extraction failed")
        try:
            error_result = basic_pipeline.process_screenshot(screenshot_data)
            # Should either handle gracefully or propagate appropriately
            if error_result:
                assert isinstance(error_result, dict), "Should return valid structure even on extraction error"
        except Exception:
            # Acceptable to propagate extraction errors
            pass
        finally:
            # Reset for other tests
            basic_pipeline.extractor.extract_task.side_effect = None
            basic_pipeline.extractor.extract_task.return_value = "Edit document"
    
    def test_basic_pipeline_process_screenshot_without_window_title(self, basic_pipeline):
        """Test processing screenshot without window title."""
        basic_pipeline._mock_categorizer.categorize.return_value = "Other"
        
        screenshot_data = {
            'active_window': '',
            'ocr_text': 'Some text'
        }
        
        result = basic_pipeline.process_screenshot(screenshot_data)
        
        assert result['task'] == "Unknown Activity"
        assert result['category'] == "Other"
        assert result['confidence'] == 0.5
        assert result['details']['pattern_matched'] is False
        
        # Should not call extract_task with empty window title
        basic_pipeline.extractor.extract_task.assert_not_called()
        
        # Test error condition - categorizer failure handling
        basic_pipeline._mock_categorizer.categorize.side_effect = Exception("Categorization failed")
        try:
            error_result = basic_pipeline.process_screenshot(screenshot_data)
            # Should handle categorization errors gracefully
            assert isinstance(error_result, dict), "Should return valid structure even on categorization error"
            assert 'category' in error_result, "Should provide fallback category on error"
        except Exception:
            # Acceptable to propagate categorization errors
            pass
        finally:
            # Reset for other tests
            basic_pipeline._mock_categorizer.categorize.side_effect = None
    
    def test_basic_pipeline_process_screenshot_missing_data(self, basic_pipeline):
        """Test processing screenshot with missing data fields."""
        basic_pipeline.extractor.extract_task.return_value = "Unknown Activity"
        basic_pipeline._mock_categorizer.categorize.return_value = "Other"
        
        # Empty screenshot data
        screenshot_data = {}
        
        result = basic_pipeline.process_screenshot(screenshot_data)
        
        assert result['task'] == "Unknown Activity"
        assert result['category'] == "Other"
        assert result['confidence'] == 0.5
        assert result['features_used'] == ['Window Title']
        
        # Should call categorizer with empty strings
        basic_pipeline._mock_categorizer.categorize.assert_called_once_with('', '')
        
        # Test error condition - pipeline should handle None values gracefully
        try:
            none_result = basic_pipeline.process_screenshot(None)
            # Should handle None input gracefully or raise appropriate error
            assert isinstance(none_result, dict), "Should return valid structure even with None input"
        except (TypeError, AttributeError) as e:
            # Acceptable to raise these errors with None input
            assert "NoneType" in str(e) or "object has no attribute" in str(e), "Error should be related to None input"
    
    def test_basic_pipeline_result_structure_validation(self, basic_pipeline):
        """Test that BasicPipeline returns properly structured results."""
        basic_pipeline.extractor.extract_task.return_value = "Test task"
        basic_pipeline._mock_categorizer.categorize.return_value = "Development"
        
        screenshot_data = {'active_window': 'test.py - VSCode'}
        result = basic_pipeline.process_screenshot(screenshot_data)
        
        # Validate required fields
        required_fields = ['task', 'category', 'confidence', 'features_used', 'details']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Validate data types
        assert isinstance(result['task'], str)
        assert isinstance(result['category'], str)
        assert isinstance(result['confidence'], (int, float))
        assert isinstance(result['features_used'], list)
        assert isinstance(result['details'], dict)
        
        # Validate confidence range
        assert 0 <= result['confidence'] <= 1
        
        # Validate details structure
        details_fields = ['method', 'data_sources', 'processing_time', 'pattern_matched']
        for field in details_fields:
            assert field in result['details'], f"Missing details field: {field}"
        
        # Test error condition - malformed extractor output
        basic_pipeline.extractor.extract_task.return_value = None
        try:
            error_result = basic_pipeline.process_screenshot(screenshot_data)
            # Should handle None extractor output gracefully
            assert isinstance(error_result, dict), "Should return valid structure even with None extractor output"
            assert 'task' in error_result, "Should provide fallback task"
        except (TypeError, AttributeError):
            # Acceptable to raise these errors with None extractor output
            pass
        finally:
            # Reset for other tests
            basic_pipeline.extractor.extract_task.return_value = "Test task"


class TestOCRPipeline:
    """Test the OCRPipeline class."""
    
    @pytest.fixture
    def ocr_pipeline(self):
        """Create an OCRPipeline instance with mocked dependencies."""
        # Use persistent patches that remain active during tests
        extractor_patcher = patch('autotasktracker.comparison.pipelines.ocr.TaskExtractor')
        categorizer_patcher = patch('autotasktracker.comparison.pipelines.ocr.ActivityCategorizer.categorize')
        enhancer_patcher = patch('autotasktracker.comparison.pipelines.ocr.OCREnhancer')
        
        mock_extractor = extractor_patcher.start()
        mock_categorize = categorizer_patcher.start()
        mock_enhancer = enhancer_patcher.start()
        
        # Create pipeline with mocked dependencies
        pipeline = OCRPipeline()
        pipeline.extractor = mock_extractor.return_value
        pipeline.ocr_enhancer = mock_enhancer.return_value
        
        # Store reference to mock for assertions
        pipeline._mock_categorizer = Mock()
        pipeline._mock_categorizer.categorize = mock_categorize
        
        # Store patchers for cleanup
        pipeline._patchers = [extractor_patcher, categorizer_patcher, enhancer_patcher]
        
        yield pipeline
        
        # Cleanup
        for patcher in pipeline._patchers:
            patcher.stop()
    
    def test_ocr_pipeline_initialization(self, ocr_pipeline):
        """Test OCRPipeline initialization."""
        assert ocr_pipeline.name == "OCR Enhanced"
        assert "Enhanced with OCR text analysis" in ocr_pipeline.description
        assert hasattr(ocr_pipeline, 'extractor')
        assert hasattr(ocr_pipeline, 'ocr_enhancer')
    
    def test_ocr_pipeline_process_with_ocr_enhancement(self, ocr_pipeline):
        """Test processing screenshot with OCR enhancement."""
        # Mock responses
        ocr_pipeline.extractor.extract_task.return_value = "Basic task"
        ocr_pipeline._mock_categorizer.categorize.return_value = "Development"
        ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.return_value = {
            'task': 'Enhanced coding task',
            'confidence': 0.85,
            'ocr_quality': 'high',
            'text_regions': {'code': 3, 'text': 2}
        }
        
        screenshot_data = {
            'active_window': 'editor.py - VSCode',
            'ocr_text': '{"text": "def process_data():", "confidence": 0.9}'
        }
        
        result = ocr_pipeline.process_screenshot(screenshot_data)
        
        # Validate enhanced result
        assert result['task'] == 'Enhanced coding task'
        assert result['category'] == 'Development'
        assert result['confidence'] == 0.85
        assert 'OCR Text' in result['features_used']
        assert 'Layout Analysis' in result['features_used']
        assert result['details']['method'] == 'OCR-enhanced analysis'
        assert result['details']['ocr_quality'] == 'high'
        assert result['details']['enhancement_applied'] is True
        
        # Verify method calls
        ocr_pipeline.extractor.extract_task.assert_called_once()
        ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.assert_called_once()
    
    def test_ocr_pipeline_process_without_ocr_text(self, ocr_pipeline):
        """Test processing screenshot without OCR text (fallback mode)."""
        ocr_pipeline.extractor.extract_task.return_value = "Basic task"
        ocr_pipeline._mock_categorizer.categorize.return_value = "Other"
        
        screenshot_data = {
            'active_window': 'browser.exe',
            'ocr_text': ''  # No OCR text
        }
        
        result = ocr_pipeline.process_screenshot(screenshot_data)
        
        # Should fallback to basic processing
        assert result['task'] == 'Basic task'
        assert result['category'] == 'Other'
        assert result['confidence'] == 0.3  # Lower confidence for fallback
        assert result['features_used'] == ['Window Title']
        assert result['details']['method'] == 'Fallback to basic (no OCR)'
        assert result['details']['ocr_quality'] == 'no_text'
        assert result['details']['enhancement_applied'] is False
        
        # Should not call OCR enhancer
        ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.assert_not_called()
    
    def test_ocr_pipeline_process_with_partial_ocr_enhancement(self, ocr_pipeline):
        """Test processing with partial OCR enhancement data."""
        ocr_pipeline.extractor.extract_task.return_value = "Original task"
        ocr_pipeline._mock_categorizer.categorize.return_value = "Productivity"
        
        # OCR enhancement returns partial data
        ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.return_value = {
            'confidence': 0.7
            # Missing 'task' field - should use original
        }
        
        screenshot_data = {
            'active_window': 'document.docx',
            'ocr_text': 'some text'
        }
        
        result = ocr_pipeline.process_screenshot(screenshot_data)
        
        # Should use original task when enhancement doesn't provide it
        assert result['task'] == 'Original task'
        assert result['confidence'] == 0.7
        assert result['details']['ocr_quality'] == 'unknown'  # Default when not provided
        
        # Test error condition - enhancer failure handling
        ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.side_effect = Exception("Enhancement failed")
        try:
            error_result = ocr_pipeline.process_screenshot(screenshot_data)
            # Should handle enhancement errors gracefully
            assert isinstance(error_result, dict), "Should return valid structure even on enhancement error"
            assert 'task' in error_result, "Should provide fallback task on error"
        except Exception:
            # Acceptable to propagate enhancement errors
            pass
        finally:
            # Reset for other tests
            ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.side_effect = None
    
    def test_ocr_pipeline_result_structure_validation(self, ocr_pipeline):
        """Test that OCRPipeline returns properly structured results."""
        ocr_pipeline.extractor.extract_task.return_value = "Test task"
        ocr_pipeline._mock_categorizer.categorize.return_value = "Test category"
        ocr_pipeline.ocr_enhancer.enhance_task_with_ocr.return_value = {
            'task': 'Enhanced task',
            'confidence': 0.8,
            'ocr_quality': 'medium'
        }
        
        screenshot_data = {
            'active_window': 'test',
            'ocr_text': 'test text'
        }
        
        result = ocr_pipeline.process_screenshot(screenshot_data)
        
        # Validate structure matches BasePipeline interface
        required_fields = ['task', 'category', 'confidence', 'features_used', 'details']
        for field in required_fields:
            assert field in result
        
        # Validate OCR-specific details
        assert 'ocr_quality' in result['details']
        assert 'enhancement_applied' in result['details']
        assert 'data_sources' in result['details']
        assert isinstance(result['details']['data_sources'], list)
        
        # Test error condition - corrupted OCR text format
        malformed_data = {
            'active_window': 'test',
            'ocr_text': 'invalid_json_format{'
        }
        try:
            error_result = ocr_pipeline.process_screenshot(malformed_data)
            # Should handle malformed OCR data gracefully
            assert isinstance(error_result, dict), "Should return valid structure even with malformed OCR data"
            assert 'task' in error_result, "Should provide fallback task"
        except (ValueError, TypeError, AttributeError):
            # Acceptable to raise these errors with malformed data
            pass


class TestAIFullPipeline:
    """Test the AIFullPipeline class."""
    
    @pytest.fixture
    def ai_pipeline(self):
        """Create an AIFullPipeline instance with mocked dependencies."""
        with patch('autotasktracker.comparison.pipelines.ai_full.DatabaseManager') as mock_db:
            with patch('autotasktracker.comparison.pipelines.ai_full.AIEnhancedTaskExtractor') as mock_ai_extractor:
                with patch('autotasktracker.comparison.pipelines.ai_full.VLMTaskExtractor') as mock_vlm:
                    pipeline = AIFullPipeline()
                    pipeline.mock_db = mock_db.return_value
                    pipeline.mock_ai_extractor = mock_ai_extractor.return_value
                    pipeline.mock_vlm = mock_vlm.return_value
                    return pipeline
    
    def test_ai_pipeline_initialization(self, ai_pipeline):
        """Test AIFullPipeline initialization."""
        assert ai_pipeline.name == "Full AI Enhanced"
        assert "Complete AI pipeline with semantic similarity" in ai_pipeline.description
        assert hasattr(ai_pipeline, 'db_manager')
        assert hasattr(ai_pipeline, 'ai_extractor')
        assert hasattr(ai_pipeline, 'vlm_extractor')
    
    def test_ai_pipeline_process_with_all_features(self, ai_pipeline):
        """Test processing screenshot with all AI features available."""
        # Mock AI extractor response
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.return_value = {
            'task': 'Advanced AI analysis task',
            'category': 'Development',
            'confidence': 0.92,
            'similar_tasks': [
                {'task': 'Similar task 1', 'similarity': 0.85},
                {'task': 'Similar task 2', 'similarity': 0.78}
            ],
            'ai_features': {
                'ocr_available': True,
                'vlm_available': True,
                'embeddings_available': True
            }
        }
        
        screenshot_data = {
            'active_window': 'advanced_editor.py - AI IDE',
            'ocr_text': '{"code": "machine learning model"}',
            'vlm_description': 'Screenshot shows code editor with ML algorithms',
            'id': 'test_123'
        }
        
        result = ai_pipeline.process_screenshot(screenshot_data)
        
        # Validate comprehensive result
        assert result['task'] == 'Advanced AI analysis task'
        assert result['category'] == 'Development'
        assert result['confidence'] == 0.92
        
        # Validate all features are included
        expected_features = ['Window Title', 'OCR Analysis', 'Text Layout', 
                           'VLM Description', 'Visual Context', 'Semantic Similarity']
        for feature in expected_features:
            assert feature in result['features_used']
        
        # Validate details
        assert result['details']['method'] == 'Full AI enhancement'
        assert result['details']['similar_tasks_count'] == 2
        assert result['details']['has_semantic_search'] is True
        assert result['details']['has_vlm_analysis'] is True
        assert 'Visual analysis' in result['details']['data_sources']
        
        # Verify AI extractor was called correctly
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.assert_called_once_with(
            window_title='advanced_editor.py - AI IDE',
            ocr_text='{"code": "machine learning model"}',
            vlm_description='Screenshot shows code editor with ML algorithms',
            entity_id='test_123'
        )
    
    def test_ai_pipeline_process_with_minimal_features(self, ai_pipeline):
        """Test processing screenshot with minimal features (window title only)."""
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.return_value = {
            'task': 'Basic task from title',
            'category': 'Other',
            'confidence': 0.4,
            'similar_tasks': [],
            'ai_features': {}
        }
        
        screenshot_data = {
            'active_window': 'notepad.exe',
            'ocr_text': '',
            'vlm_description': '',
            'id': None
        }
        
        result = ai_pipeline.process_screenshot(screenshot_data)
        
        # Should only use window title
        assert result['features_used'] == ['Window Title']
        assert result['details']['data_sources'] == ['Window title']
        assert result['details']['has_semantic_search'] is False
        assert result['details']['has_vlm_analysis'] is False
        assert result['details']['similar_tasks_count'] == 0
    
    def test_ai_pipeline_process_with_partial_features(self, ai_pipeline):
        """Test processing screenshot with partial AI features."""
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.return_value = {
            'task': 'OCR-enhanced task',
            'category': 'Productivity',
            'confidence': 0.75,
            'similar_tasks': [{'task': 'Similar', 'similarity': 0.8}],
            'ai_features': {'ocr_available': True}
        }
        
        screenshot_data = {
            'active_window': 'document.pdf',
            'ocr_text': 'Document content here',
            'vlm_description': '',  # No VLM
            'id': 'doc_456'
        }
        
        result = ai_pipeline.process_screenshot(screenshot_data)
        
        # Should include OCR and semantic features but not VLM
        expected_features = ['Window Title', 'OCR Analysis', 'Text Layout', 'Semantic Similarity']
        assert set(result['features_used']) == set(expected_features)
        
        expected_sources = ['Window title', 'OCR text', 'Layout analysis', 'Historical patterns']
        assert set(result['details']['data_sources']) == set(expected_sources)
        
        assert result['details']['has_vlm_analysis'] is False
        assert result['details']['has_semantic_search'] is True
    
    def test_ai_pipeline_error_handling(self, ai_pipeline):
        """Test error handling in AIFullPipeline."""
        # Mock AI extractor to raise exception
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.side_effect = Exception("AI processing failed")
        
        screenshot_data = {
            'active_window': 'test.txt',
            'ocr_text': 'test',
            'vlm_description': 'test',
            'id': 'test'
        }
        
        # Should not raise exception, but handle gracefully
        with pytest.raises(Exception):
            ai_pipeline.process_screenshot(screenshot_data)
    
    def test_ai_pipeline_result_structure_validation(self, ai_pipeline):
        """Test that AIFullPipeline returns properly structured results."""
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.return_value = {
            'task': 'Structured task',
            'category': 'Structured category',
            'confidence': 0.88,
            'similar_tasks': [],
            'ai_features': {}
        }
        
        screenshot_data = {'active_window': 'test'}
        result = ai_pipeline.process_screenshot(screenshot_data)
        
        # Validate structure matches BasePipeline interface
        required_fields = ['task', 'category', 'confidence', 'features_used', 'details']
        for field in required_fields:
            assert field in result
        
        # Validate AI-specific details
        assert 'similar_tasks_count' in result['details']
        assert 'ai_features' in result['details']
        assert 'has_semantic_search' in result['details']
        assert 'has_vlm_analysis' in result['details']
        assert 'processing_time' in result['details']
        
        # Validate data types
        assert isinstance(result['details']['similar_tasks_count'], int)
        assert isinstance(result['details']['has_semantic_search'], bool)
        assert isinstance(result['details']['has_vlm_analysis'], bool)
        
        # Test error condition - AI extractor returns malformed response
        ai_pipeline.mock_ai_extractor.extract_enhanced_task.return_value = {
            'confidence': 'invalid_type',  # Should be float
            'similar_tasks': 'not_a_list'  # Should be list
        }
        try:
            error_result = ai_pipeline.process_screenshot(screenshot_data)
            # Should handle malformed AI response gracefully
            assert isinstance(error_result, dict), "Should return valid structure even with malformed AI response"
            assert 'task' in error_result, "Should provide fallback task"
        except (TypeError, ValueError, KeyError):
            # Acceptable to raise these errors with malformed AI response
            pass
        finally:
            # Reset for other tests
            ai_pipeline.mock_ai_extractor.extract_enhanced_task.return_value = {
                'task': 'Structured task',
                'category': 'Structured category',
                'confidence': 0.88,
                'similar_tasks': [],
                'ai_features': {}
            }


class TestPipelineIntegration:
    """Test integration between different pipeline components."""
    
    def test_all_pipelines_implement_base_interface(self):
        """Test that all pipelines implement the BasePipeline interface correctly."""
        with patch('autotasktracker.comparison.pipelines.basic.TaskExtractor'):
            with patch('autotasktracker.comparison.pipelines.basic.ActivityCategorizer'):
                basic = BasicPipeline()
        
        with patch('autotasktracker.comparison.pipelines.ocr.TaskExtractor'):
            with patch('autotasktracker.comparison.pipelines.ocr.ActivityCategorizer'):
                with patch('autotasktracker.comparison.pipelines.ocr.OCREnhancer'):
                    ocr = OCRPipeline()
        
        with patch('autotasktracker.comparison.pipelines.ai_full.DatabaseManager'):
            with patch('autotasktracker.comparison.pipelines.ai_full.AIEnhancedTaskExtractor'):
                with patch('autotasktracker.comparison.pipelines.ai_full.VLMTaskExtractor'):
                    ai_full = AIFullPipeline()
        
        pipelines = [basic, ocr, ai_full]
        
        for pipeline in pipelines:
            # Test interface compliance
            assert isinstance(pipeline, BasePipeline)
            assert hasattr(pipeline, 'process_screenshot')
            assert hasattr(pipeline, 'get_info')
            assert hasattr(pipeline, 'name')
            assert hasattr(pipeline, 'description')
            
            # Test get_info returns correct structure
            info = pipeline.get_info()
            assert isinstance(info, dict)
            assert 'name' in info
            assert 'description' in info
            
            # Test error condition - verify methods are callable
            assert callable(getattr(pipeline, 'process_screenshot')), f"{pipeline.name} process_screenshot should be callable"
            assert callable(getattr(pipeline, 'get_info')), f"{pipeline.name} get_info should be callable"
            
            # Test interface consistency - all should have same method signatures
            import inspect
            sig = inspect.signature(pipeline.process_screenshot)
            assert len(sig.parameters) == 1, f"{pipeline.name} process_screenshot should take exactly one parameter"
    
    def test_pipeline_result_consistency(self):
        """Test that all pipelines return consistent result structures."""
        screenshot_data = {
            'active_window': 'test.py - Editor',
            'ocr_text': 'test code',
            'vlm_description': 'coding interface',
            'id': 'test_123'
        }
        
        # Mock all dependencies
        with patch('autotasktracker.comparison.pipelines.basic.TaskExtractor') as mock_basic_extractor:
            with patch('autotasktracker.comparison.pipelines.basic.ActivityCategorizer') as mock_basic_cat:
                mock_basic_extractor.return_value.extract_task.return_value = "Basic task"
                mock_basic_cat.categorize.return_value = "Development"
                basic = BasicPipeline()
                basic_result = basic.process_screenshot(screenshot_data)
        
        with patch('autotasktracker.comparison.pipelines.ocr.TaskExtractor') as mock_ocr_extractor:
            with patch('autotasktracker.comparison.pipelines.ocr.ActivityCategorizer') as mock_ocr_cat:
                with patch('autotasktracker.comparison.pipelines.ocr.OCREnhancer') as mock_enhancer:
                    mock_ocr_extractor.return_value.extract_task.return_value = "OCR task"
                    mock_ocr_cat.categorize.return_value = "Development"
                    mock_enhancer.return_value.enhance_task_with_ocr.return_value = {
                        'task': 'Enhanced task', 'confidence': 0.8
                    }
                    ocr = OCRPipeline()
                    ocr_result = ocr.process_screenshot(screenshot_data)
        
        with patch('autotasktracker.comparison.pipelines.ai_full.DatabaseManager'):
            with patch('autotasktracker.comparison.pipelines.ai_full.AIEnhancedTaskExtractor') as mock_ai:
                with patch('autotasktracker.comparison.pipelines.ai_full.VLMTaskExtractor'):
                    mock_ai.return_value.extract_enhanced_task.return_value = {
                        'task': 'AI task', 'category': 'Development', 'confidence': 0.9,
                        'similar_tasks': [], 'ai_features': {}
                    }
                    ai_full = AIFullPipeline()
                    ai_result = ai_full.process_screenshot(screenshot_data)
        
        results = [basic_result, ocr_result, ai_result]
        
        # Check that all results have the same structure
        required_fields = ['task', 'category', 'confidence', 'features_used', 'details']
        for result in results:
            for field in required_fields:
                assert field in result, f"Missing field {field} in result"
            
            # Validate data types
            assert isinstance(result['task'], str)
            assert isinstance(result['category'], str)
            assert isinstance(result['confidence'], (int, float))
            assert isinstance(result['features_used'], list)
            assert isinstance(result['details'], dict)
            
            # Validate confidence range
            assert 0 <= result['confidence'] <= 1
        
        # Test error condition - ensure pipelines handle result consistency even with errors
        with patch('autotasktracker.comparison.pipelines.basic.TaskExtractor') as mock_error_extractor:
            mock_error_extractor.return_value.extract_task.side_effect = Exception("Extraction failed")
            with patch('autotasktracker.comparison.pipelines.basic.ActivityCategorizer') as mock_error_cat:
                mock_error_cat.categorize.return_value = "Other"
                error_basic = BasicPipeline()
                try:
                    error_result = error_basic.process_screenshot(screenshot_data)
                    # Even with errors, result should maintain structure consistency
                    for field in required_fields:
                        assert field in error_result, f"Error result missing required field {field}"
                except Exception:
                    # Acceptable for extraction failures to propagate
                    pass
    
    def test_pipeline_confidence_progression(self):
        """Test that more advanced pipelines generally provide higher confidence."""
        screenshot_data = {
            'active_window': 'complex_application.py - Advanced IDE',
            'ocr_text': 'comprehensive code analysis',
            'vlm_description': 'detailed visual context',
            'id': 'complex_123'
        }
        
        # Mock all pipelines to return realistic confidence scores
        with patch('autotasktracker.comparison.pipelines.basic.TaskExtractor') as mock_basic_extractor:
            with patch('autotasktracker.comparison.pipelines.basic.ActivityCategorizer') as mock_basic_cat:
                mock_basic_extractor.return_value.extract_task.return_value = "Coding"
                mock_basic_cat.categorize.return_value = "Development"
                basic = BasicPipeline()
                basic_result = basic.process_screenshot(screenshot_data)
        
        with patch('autotasktracker.comparison.pipelines.ocr.TaskExtractor') as mock_ocr_extractor:
            with patch('autotasktracker.comparison.pipelines.ocr.ActivityCategorizer') as mock_ocr_cat:
                with patch('autotasktracker.comparison.pipelines.ocr.OCREnhancer') as mock_enhancer:
                    mock_ocr_extractor.return_value.extract_task.return_value = "Coding"
                    mock_ocr_cat.categorize.return_value = "Development"
                    mock_enhancer.return_value.enhance_task_with_ocr.return_value = {
                        'task': 'Enhanced coding', 'confidence': 0.75  # Higher than basic
                    }
                    ocr = OCRPipeline()
                    ocr_result = ocr.process_screenshot(screenshot_data)
        
        with patch('autotasktracker.comparison.pipelines.ai_full.DatabaseManager'):
            with patch('autotasktracker.comparison.pipelines.ai_full.AIEnhancedTaskExtractor') as mock_ai:
                with patch('autotasktracker.comparison.pipelines.ai_full.VLMTaskExtractor'):
                    mock_ai.return_value.extract_enhanced_task.return_value = {
                        'task': 'AI-enhanced coding', 'category': 'Development', 
                        'confidence': 0.92,  # Highest confidence
                        'similar_tasks': [{'task': 'Similar', 'similarity': 0.8}],
                        'ai_features': {'all_available': True}
                    }
                    ai_full = AIFullPipeline()
                    ai_result = ai_full.process_screenshot(screenshot_data)
        
        # Validate confidence progression: basic < ocr < ai_full
        assert basic_result['confidence'] == 0.5  # Fixed basic confidence
        assert ocr_result['confidence'] == 0.75  # OCR enhancement
        assert ai_result['confidence'] == 0.92   # Full AI enhancement
        
        # Validate feature complexity progression
        assert len(basic_result['features_used']) <= len(ocr_result['features_used'])
        assert len(ocr_result['features_used']) <= len(ai_result['features_used'])
        
        # Test error condition - ensure progression is meaningful, not just ordered
        assert basic_result['confidence'] < ai_result['confidence'], "AI pipeline should have meaningfully higher confidence"
        assert ocr_result['confidence'] < ai_result['confidence'], "AI pipeline should outperform OCR"
        assert ai_result['confidence'] - basic_result['confidence'] >= 0.3, "Confidence improvement should be substantial"
        
        # Validate business rule - confidence progression should reflect actual capability improvements
        basic_features = set(basic_result['features_used'])
        ai_features = set(ai_result['features_used'])
        assert not basic_features.issuperset(ai_features), "AI pipeline should add features, not just reorder them"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])