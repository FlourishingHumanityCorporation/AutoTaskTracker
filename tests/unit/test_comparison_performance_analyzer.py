"""
Comprehensive tests for performance analyzer module.

Tests cover all performance analysis functionality including:
- PerformanceAnalyzer initialization
- Screenshot loading and filtering
- Single screenshot processing
- Batch analysis operations
- Report generation
- Improvement analysis
- Export functionality
- Error handling and edge cases
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import os

from autotasktracker.comparison.analysis.performance_analyzer import PerformanceAnalyzer


class TestPerformanceAnalyzer:
    """Test the PerformanceAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a PerformanceAnalyzer instance with mocked dependencies."""
        with patch('autotasktracker.comparison.analysis.performance_analyzer.DatabaseManager') as mock_db:
            with patch('autotasktracker.comparison.analysis.performance_analyzer.BasicPipeline') as mock_basic:
                with patch('autotasktracker.comparison.analysis.performance_analyzer.OCRPipeline') as mock_ocr:
                    with patch('autotasktracker.comparison.analysis.performance_analyzer.AIFullPipeline') as mock_ai:
                        analyzer = PerformanceAnalyzer()
                        analyzer.mock_db = mock_db.return_value
                        analyzer.mock_basic = mock_basic.return_value
                        analyzer.mock_ocr = mock_ocr.return_value
                        analyzer.mock_ai = mock_ai.return_value
                        return analyzer
    
    def test_performance_analyzer_initialization(self, analyzer):
        """Test PerformanceAnalyzer initialization."""
        assert hasattr(analyzer, 'db_manager')
        assert hasattr(analyzer, 'pipelines')
        
        # Validate pipeline dictionary structure
        assert 'basic' in analyzer.pipelines
        assert 'ocr' in analyzer.pipelines
        assert 'ai_full' in analyzer.pipelines
        assert len(analyzer.pipelines) == 3
        
        # Validate pipeline instances
        assert analyzer.pipelines['basic'] is not None
        assert analyzer.pipelines['ocr'] is not None
        assert analyzer.pipelines['ai_full'] is not None
    
    def test_load_test_screenshots_all_filter(self, analyzer):
        """Test loading screenshots with 'all' filter."""
        # Mock database response
        mock_data = pd.DataFrame({
            'id': [1, 2, 3],
            'filepath': ['/path/1.png', '/path/2.png', '/path/3.png'],
            'filename': ['screenshot1.png', 'screenshot2.png', 'screenshot3.png'],
            'created_at': ['2024-01-01 10:00:00', '2024-01-01 11:00:00', '2024-01-01 12:00:00'],
            'ocr_text': ['OCR text 1', None, 'OCR text 3'],
            'active_window': ['Window 1', 'Window 2', 'Window 3'],
            'vlm_description': [None, 'VLM desc 2', 'VLM desc 3'],
            'has_embedding': [0, 1, 1]
        })
        
        analyzer.mock_db.get_connection.return_value.__enter__.return_value = Mock()
        
        with patch('pandas.read_sql_query', return_value=mock_data):
            result = analyzer.load_test_screenshots(limit=50, filter_type="all")
        
        # Validate result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert 'id' in result.columns
        assert 'ocr_text' in result.columns
        assert 'vlm_description' in result.columns
        
        # Verify SQL query construction
        analyzer.mock_db.get_connection.assert_called_once()
    
    def test_load_test_screenshots_with_filters(self, analyzer):
        """Test loading screenshots with various filter types."""
        mock_data = pd.DataFrame({
            'id': [1, 2],
            'filepath': ['/path/1.png', '/path/2.png'],
            'filename': ['screenshot1.png', 'screenshot2.png'],
            'created_at': ['2024-01-01 10:00:00', '2024-01-01 11:00:00'],
            'ocr_text': ['OCR text 1', 'OCR text 2'],
            'active_window': ['Window 1', 'Window 2'],
            'vlm_description': ['VLM desc 1', 'VLM desc 2'],
            'has_embedding': [1, 1]
        })
        
        analyzer.mock_db.get_connection.return_value.__enter__.return_value = Mock()
        
        # Test different filter types
        filter_types = ["ocr_only", "vlm_only", "both", "any_ai"]
        
        for filter_type in filter_types:
            with patch('pandas.read_sql_query', return_value=mock_data):
                result = analyzer.load_test_screenshots(limit=10, filter_type=filter_type)
                assert isinstance(result, pd.DataFrame)
    
    def test_load_test_screenshots_database_error(self, analyzer):
        """Test handling of database errors when loading screenshots."""
        analyzer.mock_db.get_connection.side_effect = Exception("Database connection failed")
        
        with patch('builtins.print') as mock_print:
            result = analyzer.load_test_screenshots()
        
        # Should return empty DataFrame on error
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        
        # Should print error message
        mock_print.assert_called_with("Error loading screenshots: Database connection failed")
    
    def test_process_single_screenshot_complete_data(self, analyzer):
        """Test processing single screenshot with complete data."""
        # Mock pipeline responses
        analyzer.mock_basic.process_screenshot.return_value = {
            'task': 'Basic task',
            'category': 'Development',
            'confidence': 0.5,
            'features_used': ['Window Title'],
            'details': {'method': 'basic'}
        }
        
        analyzer.mock_ocr.process_screenshot.return_value = {
            'task': 'OCR enhanced task',
            'category': 'Development',
            'confidence': 0.75,
            'features_used': ['Window Title', 'OCR'],
            'details': {'method': 'ocr_enhanced'}
        }
        
        analyzer.mock_ai.process_screenshot.return_value = {
            'task': 'AI enhanced task',
            'category': 'Development',
            'confidence': 0.92,
            'features_used': ['Window Title', 'OCR', 'VLM'],
            'details': {'method': 'ai_full'}
        }
        
        # Test data
        row_data = pd.Series({
            'id': 123,
            'filename': 'test_screenshot.png',
            'created_at': '2024-01-01 10:00:00',
            'active_window': 'editor.py - VSCode',
            'ocr_text': 'def process_data():',
            'vlm_description': 'Code editor with Python function',
            'has_embedding': 1
        })
        
        result = analyzer.process_single_screenshot(row_data)
        
        # Validate result structure
        assert isinstance(result, dict)
        assert 'screenshot_id' in result
        assert 'filename' in result
        assert 'created_at' in result
        assert 'has_ocr' in result
        assert 'has_vlm' in result
        assert 'has_embedding' in result
        assert 'basic' in result
        assert 'ocr' in result
        assert 'ai_full' in result
        
        # Validate metadata
        assert result['screenshot_id'] == 123
        assert result['filename'] == 'test_screenshot.png'
        assert result['has_ocr'] is True
        assert result['has_vlm'] is True
        assert result['has_embedding'] is True
        
        # Validate pipeline results
        assert result['basic']['task'] == 'Basic task'
        assert result['ocr']['confidence'] == 0.75
        assert result['ai_full']['features_used'] == ['Window Title', 'OCR', 'VLM']
        
        # Verify all pipelines were called
        analyzer.mock_basic.process_screenshot.assert_called_once()
        analyzer.mock_ocr.process_screenshot.assert_called_once()
        analyzer.mock_ai.process_screenshot.assert_called_once()
    
    def test_process_single_screenshot_missing_data(self, analyzer):
        """Test processing single screenshot with missing data fields."""
        # Mock pipeline responses
        analyzer.mock_basic.process_screenshot.return_value = {
            'task': 'Unknown task',
            'category': 'Other',
            'confidence': 0.3,
            'features_used': ['Window Title'],
            'details': {}
        }
        
        # Test data with missing fields
        row_data = pd.Series({
            'id': 456,
            'filename': 'minimal_screenshot.png'
            # Missing: created_at, active_window, ocr_text, vlm_description, has_embedding
        })
        
        result = analyzer.process_single_screenshot(row_data)
        
        # Should handle missing data gracefully
        assert result['screenshot_id'] == 456
        assert result['filename'] == 'minimal_screenshot.png'
        assert result['created_at'] == ''  # Default for missing data
        assert result['has_ocr'] is False
        assert result['has_vlm'] is False
        assert result['has_embedding'] is False
        
        # Should still call pipelines with empty data
        expected_screenshot_data = {
            'active_window': '',
            'ocr_text': '',
            'vlm_description': '',
            'id': 456
        }
        analyzer.mock_basic.process_screenshot.assert_called_with(expected_screenshot_data)
    
    def test_process_single_screenshot_pipeline_error(self, analyzer):
        """Test handling of pipeline processing errors."""
        # Mock one pipeline to raise an error
        analyzer.mock_basic.process_screenshot.side_effect = Exception("Basic pipeline failed")
        analyzer.mock_ocr.process_screenshot.return_value = {'task': 'OCR task', 'category': 'Cat', 'confidence': 0.8, 'features_used': []}
        analyzer.mock_ai.process_screenshot.return_value = {'task': 'AI task', 'category': 'Cat', 'confidence': 0.9, 'features_used': []}
        
        row_data = pd.Series({'id': 789, 'filename': 'error_test.png'})
        
        with patch('builtins.print') as mock_print:
            result = analyzer.process_single_screenshot(row_data)
        
        # Should handle error gracefully
        assert 'basic' in result
        assert result['basic']['task'] == 'Processing failed'
        assert result['basic']['category'] == 'Error'
        assert result['basic']['confidence'] == 0.0
        assert result['basic']['features_used'] == []
        assert 'error' in result['basic']['details']
        
        # Should still process other pipelines
        assert result['ocr']['task'] == 'OCR task'
        assert result['ai_full']['task'] == 'AI task'
        
        # Should print error message
        mock_print.assert_called_with("Error processing with basic: Basic pipeline failed")
    
    def test_analyze_batch(self, analyzer):
        """Test batch analysis of screenshots."""
        # Mock screenshot data
        screenshots_df = pd.DataFrame({
            'id': [1, 2, 3],
            'filename': ['shot1.png', 'shot2.png', 'shot3.png'],
            'active_window': ['app1', 'app2', 'app3'],
            'ocr_text': ['text1', 'text2', 'text3'],
            'vlm_description': ['desc1', 'desc2', 'desc3'],
            'has_embedding': [1, 0, 1]
        })
        
        # Mock process_single_screenshot to return consistent results
        def mock_process_single(row):
            return {
                'screenshot_id': row['id'],
                'filename': row['filename'],
                'has_ocr': bool(row['ocr_text']),
                'has_vlm': bool(row['vlm_description']),
                'has_embedding': bool(row['has_embedding']),
                'basic': {'confidence': 0.5},
                'ocr': {'confidence': 0.7},
                'ai_full': {'confidence': 0.9}
            }
        
        with patch.object(analyzer, 'process_single_screenshot', side_effect=mock_process_single) as mock_process:
            with patch.object(analyzer, 'generate_analysis_report') as mock_report:
                with patch('builtins.print'):  # Suppress progress prints
                    mock_report.return_value = {'test': 'report'}
                    
                    result = analyzer.analyze_batch(screenshots_df)
        
        # Should call process_single_screenshot for each row
        assert mock_process.call_count == 3
        
        # Should call generate_analysis_report with results
        mock_report.assert_called_once()
        args = mock_report.call_args[0][0]
        assert len(args) == 3  # 3 processed results
        
        assert result == {'test': 'report'}
    
    def test_analyze_batch_with_processing_errors(self, analyzer):
        """Test batch analysis with some processing errors."""
        screenshots_df = pd.DataFrame({
            'id': [1, 2, 3],
            'filename': ['shot1.png', 'shot2.png', 'shot3.png']
        })
        
        # Mock process_single_screenshot to fail on second item
        def mock_process_single(row):
            if row['id'] == 2:
                raise Exception("Processing failed for screenshot 2")
            return {'screenshot_id': row['id'], 'test': 'data'}
        
        with patch.object(analyzer, 'process_single_screenshot', side_effect=mock_process_single):
            with patch.object(analyzer, 'generate_analysis_report') as mock_report:
                with patch('builtins.print'):  # Suppress error prints
                    mock_report.return_value = {'processed': 2}
                    
                    result = analyzer.analyze_batch(screenshots_df)
        
        # Should call generate_analysis_report with successful results only
        mock_report.assert_called_once()
        args = mock_report.call_args[0][0]
        assert len(args) == 2  # Only 2 successful results
        
        assert result == {'processed': 2}
    
    def test_generate_analysis_report(self, analyzer):
        """Test analysis report generation."""
        # Mock analysis results
        results = [
            {
                'screenshot_id': 1,
                'has_ocr': True,
                'has_vlm': False,
                'has_embedding': True,
                'basic': {'confidence': 0.5, 'task': 'Task A', 'category': 'Cat1'},
                'ocr': {'confidence': 0.7, 'task': 'Task B', 'category': 'Cat1'},
                'ai_full': {'confidence': 0.9, 'task': 'Task C', 'category': 'Cat2'}
            },
            {
                'screenshot_id': 2,
                'has_ocr': False,
                'has_vlm': True,
                'has_embedding': False,
                'basic': {'confidence': 0.4, 'task': 'Task D', 'category': 'Cat2'},
                'ocr': {'confidence': 0.6, 'task': 'Task E', 'category': 'Cat1'},
                'ai_full': {'confidence': 0.8, 'task': 'Task F', 'category': 'Cat3'}
            }
        ]
        
        with patch('autotasktracker.comparison.analysis.performance_analyzer.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = '2024-01-01T10:00:00'
            
            report = analyzer.generate_analysis_report(results)
        
        # Validate report structure
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'method_performance' in report
        assert 'confidence_analysis' in report
        assert 'task_diversity' in report
        assert 'category_distribution' in report
        
        # Validate summary
        summary = report['summary']
        assert summary['total_screenshots'] == 2
        assert summary['with_ocr'] == 1
        assert summary['with_vlm'] == 1
        assert summary['with_embeddings'] == 1
        assert summary['analysis_timestamp'] == '2024-01-01T10:00:00'
        
        # Validate method performance
        method_perf = report['method_performance']
        assert 'basic' in method_perf
        assert 'ocr' in method_perf
        assert 'ai_full' in method_perf
        
        # Check confidence calculations
        basic_perf = method_perf['basic']
        assert basic_perf['avg_confidence'] == 0.45  # (0.5 + 0.4) / 2
        assert basic_perf['min_confidence'] == 0.4
        assert basic_perf['max_confidence'] == 0.5
        assert basic_perf['unique_tasks'] == 2  # Task A, Task D
        assert basic_perf['unique_categories'] == 2  # Cat1, Cat2
        
        # Validate confidence analysis
        conf_analysis = report['confidence_analysis']
        assert 'method_ranking' in conf_analysis
        assert 'confidence_improvements' in conf_analysis
        
        # AI_full should rank highest in confidence
        assert conf_analysis['method_ranking'][0] == 'ai_full'
    
    def test_generate_analysis_report_empty_results(self, analyzer):
        """Test analysis report generation with empty results."""
        report = analyzer.generate_analysis_report([])
        
        assert report == {"error": "No results to analyze"}
    
    def test_analyze_confidence_improvements(self, analyzer):
        """Test confidence improvement analysis."""
        results = [
            {
                'basic': {'confidence': 0.4},
                'ai_full': {'confidence': 0.8}  # +0.4 improvement
            },
            {
                'basic': {'confidence': 0.6},
                'ai_full': {'confidence': 0.7}  # +0.1 improvement
            },
            {
                'basic': {'confidence': 0.8},
                'ai_full': {'confidence': 0.6}  # -0.2 degradation
            },
            {
                'ocr': {'confidence': 0.5}  # Missing basic - should be skipped
            }
        ]
        
        improvements = analyzer._analyze_confidence_improvements(results)
        
        # Should analyze 3 valid comparisons
        expected_improvements = [0.4, 0.1, -0.2]
        
        assert abs(improvements['avg_improvement'] - sum(expected_improvements)/3) < 0.001
        assert improvements['positive_improvements'] == 2
        assert improvements['negative_improvements'] == 1
        assert improvements['no_change'] == 0
        assert improvements['max_improvement'] == 0.4
        assert abs(improvements['min_improvement'] - (-0.2)) < 0.001
    
    def test_analyze_confidence_improvements_no_data(self, analyzer):
        """Test confidence improvement analysis with no valid data."""
        results = [
            {'ocr': {'confidence': 0.5}},  # Missing basic and ai_full
            {'basic': {'confidence': 0.6}}  # Missing ai_full
        ]
        
        improvements = analyzer._analyze_confidence_improvements(results)
        assert improvements == {}
    
    def test_export_detailed_results(self, analyzer):
        """Test exporting detailed results to CSV."""
        results = [
            {
                'screenshot_id': 1,
                'filename': 'shot1.png',
                'created_at': '2024-01-01 10:00:00',
                'has_ocr': True,
                'has_vlm': False,
                'has_embedding': True,
                'basic': {
                    'task': 'Basic Task 1',
                    'category': 'Development',
                    'confidence': 0.5,
                    'features_used': ['Window Title']
                },
                'ocr': {
                    'task': 'OCR Task 1',
                    'category': 'Development',
                    'confidence': 0.75,
                    'features_used': ['Window Title', 'OCR Text']
                }
            },
            {
                'screenshot_id': 2,
                'filename': 'shot2.png',
                'created_at': '2024-01-01 11:00:00',
                'has_ocr': False,
                'has_vlm': True,
                'has_embedding': False,
                'basic': {
                    'task': 'Basic Task 2',
                    'category': 'Browser',
                    'confidence': 0.4,
                    'features_used': ['Window Title']
                }
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            with patch('builtins.print') as mock_print:
                analyzer.export_detailed_results(results, temp_filename)
            
            # Verify file was created and contains expected data
            assert os.path.exists(temp_filename)
            
            # Read and validate CSV content
            exported_df = pd.read_csv(temp_filename)
            
            # Should have 3 rows (2 screenshots × pipelines present)
            assert len(exported_df) == 3  # 2 basic + 1 ocr
            
            # Validate columns
            expected_columns = ['screenshot_id', 'filename', 'created_at', 'has_ocr', 
                               'has_vlm', 'has_embedding', 'pipeline', 'task', 
                               'category', 'confidence', 'features_used']
            for col in expected_columns:
                assert col in exported_df.columns
            
            # Validate data
            basic_rows = exported_df[exported_df['pipeline'] == 'basic']
            assert len(basic_rows) == 2
            assert basic_rows.iloc[0]['task'] == 'Basic Task 1'
            assert basic_rows.iloc[1]['confidence'] == 0.4
            
            ocr_rows = exported_df[exported_df['pipeline'] == 'ocr']
            assert len(ocr_rows) == 1
            assert ocr_rows.iloc[0]['features_used'] == 'Window Title, OCR Text'
            
            # Verify print message
            mock_print.assert_called_with(f"Detailed results exported to {temp_filename}")
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


class TestPerformanceAnalyzerIntegration:
    """Test integration scenarios for performance analyzer."""
    
    def test_end_to_end_analysis_workflow(self):
        """Test complete end-to-end analysis workflow."""
        with patch('autotasktracker.comparison.analysis.performance_analyzer.DatabaseManager') as mock_db:
            with patch('autotasktracker.comparison.analysis.performance_analyzer.BasicPipeline') as mock_basic:
                with patch('autotasktracker.comparison.analysis.performance_analyzer.OCRPipeline') as mock_ocr:
                    with patch('autotasktracker.comparison.analysis.performance_analyzer.AIFullPipeline') as mock_ai:
                        
                        # Setup analyzer
                        analyzer = PerformanceAnalyzer()
                        
                        # Mock database data
                        mock_screenshots = pd.DataFrame({
                            'id': [1, 2],
                            'filename': ['test1.png', 'test2.png'],
                            'active_window': ['Code Editor', 'Browser'],
                            'ocr_text': ['code content', 'web page'],
                            'vlm_description': ['coding interface', 'web interface'],
                            'has_embedding': [1, 0]
                        })
                        
                        # Mock pipeline responses
                        mock_basic.return_value.process_screenshot.return_value = {
                            'task': 'Basic task', 'category': 'Development', 
                            'confidence': 0.5, 'features_used': ['Window']
                        }
                        mock_ocr.return_value.process_screenshot.return_value = {
                            'task': 'OCR task', 'category': 'Development', 
                            'confidence': 0.7, 'features_used': ['Window', 'OCR']
                        }
                        mock_ai.return_value.process_screenshot.return_value = {
                            'task': 'AI task', 'category': 'Development', 
                            'confidence': 0.9, 'features_used': ['Window', 'OCR', 'VLM']
                        }
                        
                        # Execute workflow
                        with patch.object(analyzer, 'load_test_screenshots', return_value=mock_screenshots):
                            with patch('builtins.print'):  # Suppress progress output
                                report = analyzer.analyze_batch(mock_screenshots)
                        
                        # Validate complete workflow
                        assert isinstance(report, dict)
                        assert 'summary' in report
                        assert 'method_performance' in report
                        assert report['summary']['total_screenshots'] == 2
                        
                        # Validate that all pipelines were used
                        assert 'basic' in report['method_performance']
                        assert 'ocr' in report['method_performance']
                        assert 'ai_full' in report['method_performance']
                        
                        # Validate confidence ranking (AI should be highest)
                        ranking = report['confidence_analysis']['method_ranking']
                        assert ranking[0] == 'ai_full'
                        assert ranking[-1] == 'basic'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])