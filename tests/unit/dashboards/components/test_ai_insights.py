"""Tests for the AI Insights component."""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call

from autotasktracker.dashboards.components.ai_insights import (
    AIInsightsComponent, InsightType, InsightPriority
)


class TestAIInsightsComponent(unittest.TestCase):
    """Test cases for AIInsightsComponent."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_insights = [
            {
                "content": "High usage of development tools detected",
                "type": InsightType.INFO,
                "priority": InsightPriority.MEDIUM,
                "category": "Productivity",
                "confidence": 0.85
            },
            {
                "content": "Excessive context switching detected",
                "type": InsightType.WARNING,
                "priority": InsightPriority.HIGH,
                "category": "Efficiency",
                "confidence": 0.92,
                "metadata": {
                    "switches_per_hour": 12,
                    "recommendation": "Try focusing on one task for longer periods"
                }
            },
            {
                "content": "Peak productivity hours: 9 AM - 11 AM",
                "type": InsightType.PATTERN,
                "priority": InsightPriority.LOW,
                "category": "Patterns",
                "confidence": 0.78
            }
        ]
        
        self.sample_recommendations = [
            {
                "title": "Reduce Context Switching",
                "description": "You switch between tasks frequently. Try time-blocking.",
                "impact": "high",
                "effort": "low",
                "actions": [
                    "Use 25-minute focus blocks",
                    "Close unnecessary tabs",
                    "Turn off notifications"
                ]
            },
            {
                "title": "Optimize Meeting Schedule",
                "description": "Meetings fragment your productive hours.",
                "impact": "medium",
                "effort": "medium",
                "actions": [
                    "Batch meetings in the afternoon",
                    "Keep mornings for deep work"
                ]
            }
        ]
        
        self.sample_patterns = [
            {
                "name": "Morning Productivity Peak",
                "description": "Your most productive hours are 9-11 AM",
                "confidence": 0.85,
                "trend": "stable",
                "data": {"hours": [9, 10, 11], "productivity": [85, 90, 88]}
            },
            {
                "name": "Friday Slowdown",
                "description": "Productivity drops 30% on Fridays",
                "confidence": 0.72,
                "trend": "down",
                "data": {"days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "scores": [85, 82, 80, 78, 56]}
            }
        ]
    
    def test_default_config(self):
        """Test default configuration."""
        config = AIInsightsComponent.get_default_config()
        
        self.assertTrue(config['show_timestamp'])
        self.assertTrue(config['show_priority'])
        self.assertTrue(config['expandable'])
        self.assertEqual(config['max_insights'], 10)
        self.assertIn(InsightType.INFO, config['icons'])
        self.assertIn(InsightPriority.HIGH, config['priority_colors'])
    
    def test_process_insights(self):
        """Test insight processing and filtering."""
        config = {"max_insights": 2}
        
        processed = AIInsightsComponent._process_insights(
            self.sample_insights, config
        )
        
        # Should limit to 2 insights
        self.assertEqual(len(processed), 2)
        
        # Should sort by priority (HIGH first)
        self.assertEqual(processed[0]["priority"], InsightPriority.HIGH)
    
    @patch('streamlit.info')
    def test_render_insights_empty(self, mock_info):
        """Test rendering with no insights."""
        AIInsightsComponent.render_insights([])
        
        mock_info.assert_called_once_with("No insights available at this time.")
    
    @patch('streamlit.subheader')
    @patch('streamlit.markdown')
    def test_render_flat_insights(self, mock_markdown, mock_subheader):
        """Test rendering insights in flat list."""
        AIInsightsComponent.render_insights(
            self.sample_insights,
            title="Test Insights",
            config={"expandable": False, "group_by_category": False}
        )
        
        mock_subheader.assert_called_once_with("Test Insights")
        
        # Should render each insight
        self.assertEqual(mock_markdown.call_count, len(self.sample_insights))
    
    @patch('streamlit.subheader')
    @patch('streamlit.expander')
    def test_render_grouped_insights(self, mock_expander, mock_subheader):
        """Test rendering insights grouped by category."""
        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        AIInsightsComponent.render_insights(
            self.sample_insights,
            config={"group_by_category": True, "expandable": False}
        )
        
        # Should create expanders for each category
        categories = set(insight.get("category", "General") for insight in self.sample_insights)
        self.assertEqual(mock_expander.call_count, len(categories))
    
    def test_get_impact_emoji(self):
        """Test impact/effort emoji mapping."""
        # Quick win
        self.assertEqual(
            AIInsightsComponent._get_impact_emoji("high", "low"),
            "🎯"
        )
        
        # Avoid
        self.assertEqual(
            AIInsightsComponent._get_impact_emoji("low", "high"),
            "❌"
        )
        
        # Standard
        self.assertEqual(
            AIInsightsComponent._get_impact_emoji("medium", "medium"),
            "📊"
        )
    
    @patch('streamlit.subheader')
    @patch('streamlit.selectbox')
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    def test_render_recommendations_with_matrix(
        self, mock_columns, mock_markdown, mock_selectbox, mock_subheader
    ):
        """Test rendering recommendations with impact matrix."""
        # Mock columns with context manager support
        mock_col1 = MagicMock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        
        mock_col2 = MagicMock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        
        mock_columns.return_value = [mock_col1, mock_col2]
        
        # Mock selectbox to return first recommendation
        mock_selectbox.return_value = self.sample_recommendations[0]
        
        AIInsightsComponent.render_recommendations(
            self.sample_recommendations,
            show_impact=True
        )
        
        mock_subheader.assert_called_once_with("Recommendations")
        mock_selectbox.assert_called_once()
    
    @patch('streamlit.subheader')
    @patch('streamlit.expander')
    def test_render_recommendations_expanded(self, mock_expander, mock_subheader):
        """Test rendering recommendations in expandable format."""
        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        AIInsightsComponent.render_recommendations(
            self.sample_recommendations,
            show_impact=False
        )
        
        # Should create expander for each recommendation
        self.assertEqual(mock_expander.call_count, len(self.sample_recommendations))
        
        # Check expander titles
        expected_titles = [f"💡 {rec['title']}" for rec in self.sample_recommendations]
        actual_titles = [call[0][0] for call in mock_expander.call_args_list]
        self.assertEqual(actual_titles, expected_titles)
    
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    @patch('streamlit.caption')
    @patch('streamlit.metric')
    def test_render_pattern_analysis(
        self, mock_metric, mock_caption, mock_markdown, mock_columns, mock_subheader
    ):
        """Test pattern analysis rendering."""
        # Mock columns with context manager support
        def create_mock_columns(sizes):
            mock_cols = []
            for _ in sizes:
                mock_col = MagicMock()
                mock_col.__enter__ = Mock(return_value=mock_col)
                mock_col.__exit__ = Mock(return_value=None)
                mock_cols.append(mock_col)
            return mock_cols
        
        mock_columns.side_effect = lambda sizes: create_mock_columns(sizes)
        
        AIInsightsComponent.render_pattern_analysis(
            self.sample_patterns,
            show_visualizations=True
        )
        
        mock_subheader.assert_called_once_with("Pattern Analysis")
        
        # Should create columns for each pattern
        self.assertEqual(mock_columns.call_count, len(self.sample_patterns))
        
        # Should show metrics (confidence and trend)
        self.assertEqual(mock_metric.call_count, len(self.sample_patterns) * 2)
    
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    def test_render_insight_summary(self, mock_metric, mock_columns):
        """Test insight summary rendering."""
        # Create proper mock columns with context manager support
        mock_cols = []
        for _ in range(4):
            mock_col = MagicMock()
            mock_col.__enter__ = Mock(return_value=mock_col)
            mock_col.__exit__ = Mock(return_value=None)
            mock_cols.append(mock_col)
        
        mock_columns.return_value = mock_cols
        
        AIInsightsComponent.render_insight_summary(
            self.sample_insights,
            show_stats=True
        )
        
        # Should show 4 metrics
        self.assertEqual(mock_metric.call_count, 4)
        
        # Check metric labels
        metric_labels = [call[0][0] for call in mock_metric.call_args_list]
        self.assertIn("Total Insights", metric_labels)
        self.assertIn("High Priority", metric_labels)
        self.assertIn("Warnings", metric_labels)
        self.assertIn("Recommendations", metric_labels)
    
    @patch('streamlit.markdown')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    def test_render_insight_actions(self, mock_columns, mock_button, mock_markdown):
        """Test rendering insight with actions."""
        insight_with_actions = {
            "content": "Test insight",
            "type": InsightType.INFO,
            "actions": [
                {"label": "Fix Now", "key": "fix_1", "help": "Apply fix"},
                {"label": "Ignore", "key": "ignore_1", "help": "Dismiss"}
            ]
        }
        
        # Mock columns with context manager support for action buttons
        mock_cols = []
        for _ in range(2):
            mock_col = MagicMock()
            mock_col.__enter__ = Mock(return_value=mock_col)
            mock_col.__exit__ = Mock(return_value=None)
            mock_cols.append(mock_col)
        
        mock_columns.return_value = mock_cols
        
        AIInsightsComponent.render_insights(
            [insight_with_actions],
            config={"enable_actions": True, "expandable": False}
        )
        
        # Should create buttons for actions
        self.assertEqual(mock_button.call_count, 2)
        
        # Check button parameters
        button_calls = mock_button.call_args_list
        self.assertEqual(button_calls[0][0][0], "Fix Now")
        self.assertEqual(button_calls[1][0][0], "Ignore")
    
    def test_insight_type_enum(self):
        """Test InsightType enum values."""
        self.assertEqual(InsightType.INFO.value, "info")
        self.assertEqual(InsightType.WARNING.value, "warning")
        self.assertEqual(InsightType.RECOMMENDATION.value, "recommendation")
    
    def test_insight_priority_enum(self):
        """Test InsightPriority enum values."""
        self.assertEqual(InsightPriority.HIGH.value, "high")
        self.assertEqual(InsightPriority.MEDIUM.value, "medium")
        self.assertEqual(InsightPriority.LOW.value, "low")


if __name__ == '__main__':
    unittest.main()