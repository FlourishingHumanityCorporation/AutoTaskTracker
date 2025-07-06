"""Unit tests for PeriodStats component."""

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import date, datetime, timedelta
import pandas as pd

from autotasktracker.dashboards.components.period_stats import PeriodStats


class TestPeriodStats(unittest.TestCase):
    """Test cases for PeriodStats component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_st = MagicMock()
        self.patch_st = patch('autotasktracker.dashboards.components.period_stats.st', self.mock_st)
        self.patch_st.start()
        
        # Mock columns
        self.mock_col1 = MagicMock()
        self.mock_col2 = MagicMock()
        self.mock_st.columns.return_value = [self.mock_col1, self.mock_col2]
        
        # Mock container
        self.mock_container = MagicMock()
        self.mock_st.container.return_value = self.mock_container
        
    def tearDown(self):
        """Clean up after tests."""
        self.patch_st.stop()
        
    def test_get_week_range(self):
        """Test week range calculation."""
        with patch('autotasktracker.dashboards.components.period_stats.date') as mock_date:
            # Mock today as Friday, Jan 3, 2025
            mock_date.today.return_value = date(2025, 1, 3)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            
            # This week (should be Mon-Fri, capped at today)
            start, end = PeriodStats._get_week_range(0)
            self.assertEqual(start, date(2024, 12, 30))  # Monday
            self.assertEqual(end, date(2025, 1, 3))      # Today (Friday, capped)
            
            # Last week (Dec 23-29, 2024)
            start, end = PeriodStats._get_week_range(-1)
            self.assertEqual(start, date(2024, 12, 23))  # Monday of last week
            self.assertEqual(end, date(2024, 12, 29))    # Sunday of last week
            
    def test_get_month_range(self):
        """Test month range calculation."""
        with patch('autotasktracker.dashboards.components.period_stats.date') as mock_date:
            # Mock today as Jan 15, 2025
            mock_date.today.return_value = date(2025, 1, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            
            # This month
            start, end = PeriodStats._get_month_range(0)
            self.assertEqual(start, date(2025, 1, 1))
            self.assertEqual(end, date(2025, 1, 15))
            
            # Last month
            start, end = PeriodStats._get_month_range(-1)
            self.assertEqual(start, date(2024, 12, 1))
            self.assertEqual(end, date(2024, 12, 31))
            
    def test_render_period_selector_simple(self):
        """Test simple period selector without comparison."""
        # Mock selectbox to return "Last 7 Days"
        self.mock_st.selectbox.return_value = "Last 7 Days"
        
        with patch('autotasktracker.dashboards.components.period_stats.date') as mock_date:
            mock_date.today.return_value = date(2025, 1, 6)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            
            result = PeriodStats.render_period_selector(
                key="test",
                default_period="Last 7 Days",
                allow_comparison=False
            )
            
        # Should have period info
        self.assertEqual(result['period'], "Last 7 Days")
        self.assertEqual(result['start_date'], date(2024, 12, 31))
        self.assertEqual(result['end_date'], date(2025, 1, 6))
        
        # Should not have comparison info
        self.assertNotIn('compare_enabled', result)
        
    def test_render_period_selector_with_comparison(self):
        """Test period selector with comparison enabled."""
        # Mock selectbox calls
        self.mock_st.selectbox.side_effect = ["Last 7 Days", "Previous Period"]
        self.mock_st.checkbox.return_value = True  # Enable comparison
        
        # Set up column context managers
        for col in [self.mock_col1, self.mock_col2]:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=None)
        
        with patch('autotasktracker.dashboards.components.period_stats.date') as mock_date:
            mock_date.today.return_value = date(2025, 1, 6)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            
            result = PeriodStats.render_period_selector(
                key="test",
                default_period="Last 7 Days",
                allow_comparison=True
            )
            
        # Should have comparison info
        self.assertTrue(result['compare_enabled'])
        self.assertEqual(result['compare_period'], "Previous Period")
        # Previous 7 days before the main period
        self.assertEqual(result['compare_start'], date(2024, 12, 24))
        self.assertEqual(result['compare_end'], date(2024, 12, 30))
        
    def test_render_period_selector_custom_period(self):
        """Test period selector with custom date range."""
        # Mock selectbox to return "Custom"
        self.mock_st.selectbox.return_value = "Custom"
        # Mock date inputs
        self.mock_st.date_input.side_effect = [
            date(2025, 1, 1),  # Start date
            date(2025, 1, 5)   # End date
        ]
        
        result = PeriodStats.render_period_selector(key="test")
        
        self.assertEqual(result['period'], "Custom")
        self.assertEqual(result['start_date'], date(2025, 1, 1))
        self.assertEqual(result['end_date'], date(2025, 1, 5))
        
    def test_render_period_statistics_simple(self):
        """Test rendering simple period statistics."""
        stats = {
            'total_activities': 150,
            'active_days': 7,
            'daily_average': 21.4,
            'productivity_rate': 68.5
        }
        
        # Mock columns for metrics
        mock_metric_cols = [MagicMock() for _ in range(4)]
        self.mock_st.columns.return_value = mock_metric_cols
        
        PeriodStats.render_period_statistics(
            stats=stats,
            title="Test Period Stats"
        )
        
        # Should render title
        self.mock_st.subheader.assert_called_once_with("Test Period Stats")
        
        # Should create columns
        self.mock_st.columns.assert_called_with(4)
        
        # Should render metrics
        self.assertEqual(self.mock_st.metric.call_count, 4)
        
    def test_render_period_statistics_with_comparison(self):
        """Test rendering period statistics with comparison."""
        stats = {
            'total_activities': 150,
            'active_days': 7
        }
        compare_stats = {
            'total_activities': 120,
            'active_days': 6
        }
        
        # Mock columns
        mock_cols = [MagicMock() for _ in range(2)]
        self.mock_st.columns.return_value = mock_cols
        
        # Set up column context managers
        for col in mock_cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=None)
            col.metric = self.mock_st.metric
        
        PeriodStats.render_period_statistics(
            stats=stats,
            compare_stats=compare_stats,
            metrics_to_show=['total_activities', 'active_days']
        )
        
        # Check metrics were called with deltas
        metric_calls = self.mock_st.metric.call_args_list
        self.assertEqual(len(metric_calls), 2)
        
        # First metric should show +25% change (150 vs 120)
        first_call = metric_calls[0]
        self.assertEqual(first_call[0][0], "Total Activities")
        self.assertEqual(first_call[0][1], "150")
        self.assertIn("+25.0%", first_call[1]['delta'])
        
    def test_calculate_period_stats_empty_data(self):
        """Test calculating stats for empty dataframe."""
        df = pd.DataFrame()
        stats = PeriodStats.calculate_period_stats(df)
        
        self.assertEqual(stats['total_records'], 0)
        self.assertEqual(stats['period_days'], 0)
        self.assertEqual(stats['daily_average'], 0)
        
    def test_calculate_period_stats_with_data(self):
        """Test calculating stats for dataframe with data."""
        df = pd.DataFrame({
            'date': [date(2025, 1, 1), date(2025, 1, 1), date(2025, 1, 2)],
            'category': ['Work', 'Personal', 'Work'],
            'duration': [30, 45, 60]
        })
        
        stats = PeriodStats.calculate_period_stats(
            df,
            group_by='category',
            metrics=['duration']
        )
        
        self.assertEqual(stats['total_records'], 3)
        self.assertEqual(stats['period_days'], 2)
        self.assertEqual(stats['daily_average'], 1.5)
        self.assertEqual(stats['unique_category'], 2)
        self.assertEqual(stats['top_category'], 'Work')
        self.assertEqual(stats['duration_sum'], 135)
        self.assertEqual(stats['duration_avg'], 45)
        
    def test_render_period_comparison_chart(self):
        """Test rendering period comparison chart."""
        # Create test data
        data = pd.DataFrame({
            'period': ['Current', 'Previous'],
            'activities': [150, 120]
        })
        
        # Mock the ComparisonChart from visualizations module
        with patch('autotasktracker.dashboards.components.visualizations.ComparisonChart') as mock_chart:
            PeriodStats.render_period_comparison_chart(
                data=data,
                metric_column='activities',
                title='Activity Comparison'
            )
            
            # Should call ComparisonChart.render
            mock_chart.render.assert_called_once()
            call_args = mock_chart.render.call_args
            
            # Check the metrics format
            metrics = call_args[1]['metrics']
            self.assertIn('activities', metrics)
            self.assertEqual(metrics['activities']['Current'], 150)
            self.assertEqual(metrics['activities']['Previous'], 120)
            
    def test_custom_periods(self):
        """Test period selector with custom periods."""
        custom_periods = {
            "Last 3 Days": lambda: (date.today() - timedelta(days=2), date.today()),
            "Last Quarter": lambda: (date.today() - timedelta(days=90), date.today())
        }
        
        # Mock selectbox to include custom periods
        available_periods = list(PeriodStats.PERIODS.keys()) + list(custom_periods.keys())
        self.mock_st.selectbox.return_value = "Last 3 Days"
        
        with patch('autotasktracker.dashboards.components.period_stats.date') as mock_date:
            mock_date.today.return_value = date(2025, 1, 6)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            
            result = PeriodStats.render_period_selector(
                custom_periods=custom_periods
            )
            
            # Should use custom period
            self.assertEqual(result['period'], "Last 3 Days")
            # The custom period function uses date.today() which we didn't fully mock
            # So let's just check it's a recent date range
            self.assertEqual((result['end_date'] - result['start_date']).days, 2)


if __name__ == '__main__':
    unittest.main()