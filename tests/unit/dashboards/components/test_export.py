"""Tests for the Export component."""

import unittest
from datetime import datetime
import pandas as pd
import json
from unittest.mock import Mock, patch

from autotasktracker.dashboards.components.export import ExportComponent


class TestExportComponent(unittest.TestCase):
    """Test cases for ExportComponent."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'task': ['Task 1', 'Task 2'],
            'duration': [30, 45]
        })
        
        self.sample_dict_list = [
            {'name': 'Item 1', 'value': 100},
            {'name': 'Item 2', 'value': 200}
        ]
        
        self.mock_task_group = Mock()
        self.mock_task_group.start_time = datetime(2024, 1, 1, 9, 0)
        self.mock_task_group.end_time = datetime(2024, 1, 1, 9, 30)
        self.mock_task_group.duration_minutes = 30
        self.mock_task_group.window_title = "Test App"
        self.mock_task_group.category = "Work"
        
        mock_task = Mock()
        mock_task.title = "Test Task"
        self.mock_task_group.tasks = [mock_task]
    
    def test_default_config(self):
        """Test default configuration."""
        config = ExportComponent.get_default_config()
        
        self.assertEqual(config['csv_delimiter'], ',')
        self.assertEqual(config['csv_encoding'], 'utf-8')
        self.assertEqual(config['date_format'], '%Y-%m-%d')
        self.assertEqual(config['time_format'], '%H:%M')
        self.assertTrue(config['include_headers'])
    
    def test_to_csv_string_dataframe(self):
        """Test CSV conversion from DataFrame."""
        result = ExportComponent._to_csv_string(self.sample_df)
        
        self.assertIn('date,task,duration', result)
        self.assertIn('2024-01-01,Task 1,30', result)
        self.assertIn('2024-01-02,Task 2,45', result)
    
    def test_to_csv_string_dict_list(self):
        """Test CSV conversion from list of dicts."""
        result = ExportComponent._to_csv_string(self.sample_dict_list)
        
        self.assertIn('name,value', result)
        self.assertIn('Item 1,100', result)
        self.assertIn('Item 2,200', result)
    
    def test_to_csv_string_with_columns(self):
        """Test CSV conversion with specific columns."""
        result = ExportComponent._to_csv_string(self.sample_df, columns=['task', 'duration'])
        
        self.assertIn('task,duration', result)
        self.assertNotIn('date', result)
    
    def test_to_json_string_dict(self):
        """Test JSON conversion from dict."""
        data = {'key': 'value', 'number': 42}
        result = ExportComponent._to_json_string(data)
        parsed = json.loads(result)
        
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['number'], 42)
    
    def test_to_json_string_dataframe(self):
        """Test JSON conversion from DataFrame."""
        result = ExportComponent._to_json_string(self.sample_df)
        parsed = json.loads(result)
        
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['task'], 'Task 1')
        self.assertEqual(parsed[1]['task'], 'Task 2')
    
    def test_calculate_confidence(self):
        """Test confidence level calculation."""
        self.assertEqual(ExportComponent._calculate_confidence(3), "High")
        self.assertEqual(ExportComponent._calculate_confidence(1.5), "Medium")
        self.assertEqual(ExportComponent._calculate_confidence(0.5), "Low")
    
    def test_generate_filename(self):
        """Test filename generation."""
        # Without date
        filename = ExportComponent._generate_filename("export", "csv", include_date=False)
        self.assertEqual(filename, "export.csv")
        
        # With date
        filename = ExportComponent._generate_filename("data", "json", include_date=True)
        self.assertTrue(filename.startswith("data_"))
        self.assertTrue(filename.endswith(".json"))
    
    def test_format_task_export(self):
        """Test task export formatting."""
        task_groups = [self.mock_task_group]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = ExportComponent.format_task_export(task_groups, start_date, end_date)
        
        # Check header
        self.assertIn("Date,Task Group,Duration", result)
        
        # Check data
        self.assertIn("2024-01-01", result)
        self.assertIn("Test App", result)
        self.assertIn("30min", result)
        self.assertIn("09:00", result)
        self.assertIn("09:30", result)
        self.assertIn("Work", result)
        self.assertIn("Test Task", result)
    
    def test_format_task_export_custom_config(self):
        """Test task export with custom configuration."""
        task_groups = [self.mock_task_group]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        custom_config = {
            'date_format': '%m/%d/%Y',
            'time_format': '%I:%M %p',
            'csv_delimiter': ';'
        }
        
        result = ExportComponent.format_task_export(
            task_groups, start_date, end_date, config=custom_config
        )
        
        # Check custom date format
        self.assertIn("01/01/2024", result)
        # Check custom time format
        self.assertIn("09:00 AM", result)
        # Check custom delimiter
        self.assertIn(";", result)
    
    @patch('streamlit.download_button')
    def test_render_csv_button(self, mock_download):
        """Test CSV download button rendering."""
        mock_download.return_value = True
        
        result = ExportComponent.render_csv_button(
            self.sample_df,
            filename="test.csv",
            label="Download"
        )
        
        self.assertTrue(result)
        mock_download.assert_called_once()
        
        # Check call arguments
        call_args = mock_download.call_args
        self.assertEqual(call_args.kwargs['label'], "Download")
        self.assertEqual(call_args.kwargs['file_name'], "test.csv")
        self.assertEqual(call_args.kwargs['mime'], "text/csv")
    
    @patch('streamlit.download_button')
    def test_render_json_button(self, mock_download):
        """Test JSON download button rendering."""
        mock_download.return_value = True
        
        result = ExportComponent.render_json_button(
            self.sample_dict_list,
            filename="test.json",
            label="Download JSON"
        )
        
        self.assertTrue(result)
        mock_download.assert_called_once()
        
        # Check call arguments
        call_args = mock_download.call_args
        self.assertEqual(call_args.kwargs['label'], "Download JSON")
        self.assertEqual(call_args.kwargs['file_name'], "test.json")
        self.assertEqual(call_args.kwargs['mime'], "application/json")


if __name__ == '__main__':
    unittest.main()