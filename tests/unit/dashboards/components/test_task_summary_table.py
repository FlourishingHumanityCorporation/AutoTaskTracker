"""Tests for the TaskSummaryTable component."""

import unittest
from datetime import datetime
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

from autotasktracker.dashboards.components.task_summary_table import TaskSummaryTable


class TestTaskSummaryTable(unittest.TestCase):
    """Test cases for TaskSummaryTable component."""
    
    def setUp(self):
        """Set up test data."""
        # Sample task list data
        self.sample_tasks = [
            {
                "Task": "Code Review",
                "Duration": "45.5 min",
                "Category": "Development",
                "Sessions": 3,
                "Confidence": 0.85
            },
            {
                "Task": "Email",
                "Duration": "30.0 min",
                "Category": "Communication",
                "Sessions": 2,
                "Confidence": 0.65
            }
        ]
        
        # Sample task metrics dict (from TimeTracker)
        self.sample_metrics = {
            "Code Review": {
                "total_minutes": 45.5,
                "active_minutes": 40.0,
                "session_count": 3,
                "average_confidence": 0.85,
                "category": "Development",
                "first_seen": datetime(2024, 1, 1, 9, 0),
                "last_seen": datetime(2024, 1, 1, 10, 30)
            },
            "Email": {
                "total_minutes": 30.0,
                "active_minutes": 28.0,
                "session_count": 2,
                "average_confidence": 0.65,
                "category": "Communication",
                "first_seen": datetime(2024, 1, 1, 11, 0),
                "last_seen": datetime(2024, 1, 1, 11, 30)
            }
        }
        
        self.sample_df = pd.DataFrame(self.sample_tasks)
    
    def test_default_config(self):
        """Test default configuration."""
        config = TaskSummaryTable.get_default_config()
        
        self.assertTrue(config['show_confidence'])
        self.assertTrue(config['show_category'])
        self.assertTrue(config['show_timestamps'])
        self.assertTrue(config['show_export'])
        self.assertEqual(config['max_task_length'], 50)
        self.assertEqual(config['sort_by'], 'duration')
        self.assertFalse(config['sort_ascending'])
    
    def test_prepare_dataframe_from_list(self):
        """Test DataFrame preparation from list."""
        df = TaskSummaryTable._prepare_dataframe(
            self.sample_tasks,
            columns=None,
            config=TaskSummaryTable.get_default_config(),
            custom_formatters=None
        )
        
        self.assertEqual(len(df), 2)
        self.assertIn("Task", df.columns)
        self.assertIn("Duration", df.columns)
        self.assertIn("Category", df.columns)
    
    def test_prepare_dataframe_from_dict(self):
        """Test DataFrame preparation from metrics dict."""
        df = TaskSummaryTable._prepare_dataframe(
            self.sample_metrics,
            columns=None,
            config=TaskSummaryTable.get_default_config(),
            custom_formatters=None
        )
        
        self.assertEqual(len(df), 2)
        self.assertIn("Task", df.columns)
        self.assertIn("Duration", df.columns)
        self.assertIn("Active Time", df.columns)
        self.assertIn("Confidence", df.columns)
        
        # Check confidence formatting
        confidence_values = df["Confidence"].tolist()
        self.assertTrue(any("🟢" in str(conf) for conf in confidence_values))  # High confidence
        self.assertTrue(any("🟡" in str(conf) for conf in confidence_values))  # Medium confidence
    
    def test_prepare_dataframe_with_columns_filter(self):
        """Test DataFrame preparation with column filtering."""
        df = TaskSummaryTable._prepare_dataframe(
            self.sample_tasks,
            columns=["Task", "Category"],
            config=TaskSummaryTable.get_default_config(),
            custom_formatters=None
        )
        
        self.assertEqual(len(df.columns), 2)
        self.assertIn("Task", df.columns)
        self.assertIn("Category", df.columns)
        self.assertNotIn("Duration", df.columns)
    
    def test_convert_task_metrics_to_df(self):
        """Test conversion of task metrics to DataFrame."""
        config = TaskSummaryTable.get_default_config()
        df = TaskSummaryTable._convert_task_metrics_to_df(self.sample_metrics, config)
        
        self.assertEqual(len(df), 2)
        
        # Check first row
        first_row = df.iloc[0]
        self.assertEqual(first_row["Task"], "Code Review")
        self.assertEqual(first_row["Duration"], "45.5 min")
        self.assertEqual(first_row["Active Time"], "40.0 min")
        self.assertEqual(first_row["Sessions"], 3)
        self.assertIn("🟢", first_row["Confidence"])  # High confidence
        self.assertEqual(first_row["Category"], "Development")
        self.assertEqual(first_row["First Seen"], "09:00")
        self.assertEqual(first_row["Last Seen"], "10:30")
    
    def test_task_name_truncation(self):
        """Test long task name truncation."""
        long_task_name = "A" * 60  # Longer than default max_length of 50
        metrics = {
            long_task_name: {
                "total_minutes": 10.0,
                "category": "Test"
            }
        }
        
        config = TaskSummaryTable.get_default_config()
        df = TaskSummaryTable._convert_task_metrics_to_df(metrics, config)
        
        task_name = df.iloc[0]["Task"]
        self.assertEqual(len(task_name), 53)  # 50 chars + "..."
        self.assertTrue(task_name.endswith("..."))
    
    def test_confidence_icon_mapping(self):
        """Test confidence level icon mapping."""
        metrics = {
            "High Conf": {"average_confidence": 0.9},
            "Med Conf": {"average_confidence": 0.6},
            "Low Conf": {"average_confidence": 0.3}
        }
        
        config = TaskSummaryTable.get_default_config()
        df = TaskSummaryTable._convert_task_metrics_to_df(metrics, config)
        
        # Find rows by task name
        high_row = df[df["Task"] == "High Conf"].iloc[0]
        med_row = df[df["Task"] == "Med Conf"].iloc[0]
        low_row = df[df["Task"] == "Low Conf"].iloc[0]
        
        self.assertIn("🟢", high_row["Confidence"])
        self.assertIn("🟡", med_row["Confidence"])
        self.assertIn("🔴", low_row["Confidence"])
    
    def test_custom_formatters(self):
        """Test custom column formatters."""
        def duration_formatter(val):
            return f"⏱️ {val}"
        
        custom_formatters = {"Duration": duration_formatter}
        
        df = TaskSummaryTable._prepare_dataframe(
            self.sample_tasks,
            columns=None,
            config=TaskSummaryTable.get_default_config(),
            custom_formatters=custom_formatters
        )
        
        # Check formatter was applied
        duration_values = df["Duration"].tolist()
        self.assertTrue(all(val.startswith("⏱️") for val in duration_values))
    
    @patch('streamlit.dataframe')
    @patch('streamlit.info')
    def test_render_empty_data(self, mock_info, mock_dataframe):
        """Test rendering with empty data."""
        TaskSummaryTable.render(tasks=[])
        
        mock_info.assert_called_once_with("No tasks to display")
        mock_dataframe.assert_not_called()
    
    @patch('streamlit.subheader')
    @patch('streamlit.dataframe')
    @patch('streamlit.download_button')
    def test_render_with_title(self, mock_download, mock_dataframe, mock_subheader):
        """Test rendering with custom title."""
        TaskSummaryTable.render(
            tasks=self.sample_tasks,
            title="My Task Summary"
        )
        
        mock_subheader.assert_called_once_with("My Task Summary")
        mock_dataframe.assert_called_once()
    
    @patch('streamlit.expander')
    @patch('streamlit.markdown')
    @patch('streamlit.dataframe')
    def test_render_with_help_content(self, mock_dataframe, mock_markdown, mock_expander):
        """Test rendering with help content."""
        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        help_text = "This is helpful information"
        TaskSummaryTable.render(
            tasks=self.sample_tasks,
            help_content=help_text,
            config={"show_help": True}
        )
        
        mock_expander.assert_called_once_with("ℹ️ About This Table")
        # The markdown is called within the expander context
        mock_markdown.assert_called_once_with(help_text)
    
    @patch('streamlit.download_button')
    @patch('streamlit.dataframe')
    def test_render_export_csv(self, mock_dataframe, mock_download):
        """Test CSV export functionality."""
        TaskSummaryTable.render(
            tasks=self.sample_tasks,
            export_filename="test_export.csv",
            config={"show_export": True, "export_format": "csv"}
        )
        
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        
        self.assertEqual(call_args.kwargs['label'], "📥 Download Summary (CSV)")
        self.assertEqual(call_args.kwargs['file_name'], "test_export.csv")
        self.assertEqual(call_args.kwargs['mime'], "text/csv")
    
    @patch('streamlit.download_button')
    @patch('streamlit.dataframe')
    def test_render_export_json(self, mock_dataframe, mock_download):
        """Test JSON export functionality."""
        TaskSummaryTable.render(
            tasks=self.sample_tasks,
            export_filename="test_export.json",
            config={"show_export": True, "export_format": "json"}
        )
        
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        
        self.assertEqual(call_args.kwargs['label'], "📥 Download Summary (JSON)")
        self.assertEqual(call_args.kwargs['file_name'], "test_export.json")
        self.assertEqual(call_args.kwargs['mime'], "application/json")
    
    @patch('streamlit.caption')
    @patch('streamlit.dataframe')
    def test_render_compact(self, mock_dataframe, mock_caption):
        """Test compact rendering mode."""
        # Create more tasks than max_rows
        many_tasks = self.sample_tasks * 5  # 10 tasks
        
        TaskSummaryTable.render_compact(
            tasks=many_tasks,
            max_rows=5,
            columns=["Task", "Duration"]
        )
        
        mock_dataframe.assert_called_once()
        mock_caption.assert_called_once_with("Showing top 5 of 10 tasks")
    
    def test_prepare_column_config(self):
        """Test column configuration preparation."""
        df = pd.DataFrame(self.sample_tasks)
        config = TaskSummaryTable._prepare_column_config(
            df,
            user_config=None,
            display_config=TaskSummaryTable.get_default_config()
        )
        
        # Check that configs are created for existing columns
        self.assertIn("Task", config)
        self.assertIn("Duration", config)
        self.assertIn("Category", config)
        
        # Check column types (Streamlit column config objects)
        # Just verify they exist and are properly configured
        self.assertIsNotNone(config["Task"])
        self.assertIsNotNone(config["Category"])


if __name__ == '__main__':
    unittest.main()