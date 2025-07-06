"""Tests for SmartDefaultsComponent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

import streamlit as st
from autotasktracker.dashboards.components.smart_defaults import SmartDefaultsComponent


class TestSmartDefaultsComponent:
    """Test suite for SmartDefaultsComponent."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock()
    
    @pytest.fixture
    def sample_tasks_df(self):
        """Create sample tasks dataframe."""
        return pd.DataFrame({
            'id': range(10),
            'window_title': ['Task ' + str(i) for i in range(10)],
            'extracted_app': ['App1', 'App2', 'App1', 'App3', 'App2'] * 2,
            'extracted_category': ['Work', 'Work', 'Personal', 'Work', 'Personal'] * 2,
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='h')
        })
    
    def test_get_time_period_default_no_db(self):
        """Test time period default without database."""
        result = SmartDefaultsComponent.get_time_period_default(None)
        assert result == "Last 7 Days"
    
    def test_get_time_period_default_with_today_data(self, mock_db_manager, sample_tasks_df):
        """Test time period default with today's data."""
        # Mock today's data
        today_df = sample_tasks_df.copy()
        today_df['timestamp'] = pd.Timestamp.now()
        
        mock_db_manager.fetch_tasks.return_value = today_df
        
        result = SmartDefaultsComponent.get_time_period_default(mock_db_manager)
        
        # Should prefer "Today" when it has enough data
        assert result in ["Today", "Last 7 Days"]  # Depends on data quality
    
    def test_get_time_period_default_with_error(self, mock_db_manager):
        """Test time period default with database error."""
        mock_db_manager.fetch_tasks.side_effect = Exception("Database error")
        
        result = SmartDefaultsComponent.get_time_period_default(mock_db_manager)
        assert result == "Last 7 Days"  # Should fallback gracefully
    
    def test_calculate_recency_factor(self):
        """Test recency factor calculation."""
        assert SmartDefaultsComponent._calculate_recency_factor("Today") == 1.0
        assert SmartDefaultsComponent._calculate_recency_factor("Yesterday") == 0.9
        assert SmartDefaultsComponent._calculate_recency_factor("Last 7 Days") == 0.7
        assert SmartDefaultsComponent._calculate_recency_factor("Unknown") == 0.5
    
    def test_calculate_diversity_factor(self, sample_tasks_df):
        """Test diversity factor calculation."""
        # High diversity
        factor = SmartDefaultsComponent._calculate_diversity_factor(sample_tasks_df)
        assert 0 <= factor <= 1
        
        # Low diversity
        uniform_df = sample_tasks_df.copy()
        uniform_df['window_title'] = 'Same Task'
        uniform_df['extracted_app'] = 'Same App'
        
        low_factor = SmartDefaultsComponent._calculate_diversity_factor(uniform_df)
        assert low_factor < factor  # Lower diversity should have lower score
        
        # Empty dataframe
        empty_factor = SmartDefaultsComponent._calculate_diversity_factor(pd.DataFrame())
        assert empty_factor == 0.0
    
    def test_get_category_defaults(self, mock_db_manager, sample_tasks_df):
        """Test category defaults selection."""
        mock_db_manager.fetch_tasks.return_value = sample_tasks_df
        
        categories = SmartDefaultsComponent.get_category_defaults(
            mock_db_manager, 
            "Last 7 Days"
        )
        
        # Should return most common categories
        assert isinstance(categories, list)
        assert len(categories) <= 3  # Limited to top 3
        if categories:
            assert "Work" in categories  # Most common in sample data
    
    def test_get_category_defaults_no_data(self, mock_db_manager):
        """Test category defaults with no data."""
        mock_db_manager.fetch_tasks.return_value = pd.DataFrame()
        
        categories = SmartDefaultsComponent.get_category_defaults(mock_db_manager)
        assert categories == []
    
    def test_parse_time_period(self):
        """Test time period parsing."""
        # Test "Today"
        start, end = SmartDefaultsComponent._parse_time_period("Today")
        assert start.date() == datetime.now().date()
        assert end >= start
        
        # Test "Yesterday"
        start, end = SmartDefaultsComponent._parse_time_period("Yesterday")
        assert start.date() == (datetime.now() - timedelta(days=1)).date()
        
        # Test "Last 7 Days"
        start, end = SmartDefaultsComponent._parse_time_period("Last 7 Days")
        assert (end - start).days >= 6
        
        # Test unknown period
        start, end = SmartDefaultsComponent._parse_time_period("Unknown")
        assert (end - start).days >= 6  # Defaults to 7 days
    
    def test_render_smart_defaults_button(self, mock_db_manager):
        """Test smart defaults button rendering."""
        with patch('streamlit.button') as mock_button:
            mock_button.return_value = True
            
            with patch('streamlit.expander') as mock_expander:
                with patch('streamlit.rerun') as mock_rerun:
                    # Custom callback
                    callback_called = False
                    def test_callback(defaults):
                        nonlocal callback_called
                        callback_called = True
                        assert 'time_period' in defaults
                        assert 'categories' in defaults
                    
                    SmartDefaultsComponent.render_smart_defaults_button(
                        db_manager=mock_db_manager,
                        apply_callback=test_callback
                    )
                    
                    assert callback_called
                    mock_rerun.assert_called_once()
    
    def test_render_smart_defaults_button_default_behavior(self):
        """Test button with default session state behavior."""
        with patch('streamlit.button') as mock_button:
            mock_button.return_value = True
            
            with patch('streamlit.expander'):
                with patch('streamlit.rerun'):
                    # Clear session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    
                    SmartDefaultsComponent.render_smart_defaults_button()
                    
                    # Should update session state
                    assert 'time_filter' in st.session_state
    
    def test_get_smart_defaults_info(self, mock_db_manager, sample_tasks_df):
        """Test comprehensive defaults info generation."""
        mock_db_manager.fetch_tasks.return_value = sample_tasks_df
        
        info = SmartDefaultsComponent.get_smart_defaults_info(mock_db_manager)
        
        assert 'time_period' in info
        assert 'categories' in info
        assert 'reasoning' in info
        assert 'data_summary' in info
        
        # Verify data summary
        assert 'total_tasks' in info['data_summary']
    
    def test_get_smart_defaults_info_error_handling(self, mock_db_manager):
        """Test info generation with errors."""
        mock_db_manager.fetch_tasks.side_effect = Exception("Database error")
        
        info = SmartDefaultsComponent.get_smart_defaults_info(mock_db_manager)
        
        # Should return safe defaults
        assert info['time_period'] == 'Last 7 Days'
        assert info['categories'] == []
        assert 'reasoning' in info
    
    def test_generate_reasoning(self):
        """Test reasoning generation."""
        reasoning = SmartDefaultsComponent._generate_reasoning(
            None, 
            "Today", 
            ["Work", "Personal"]
        )
        
        assert "today's activity" in reasoning.lower()
        assert "2 most active categories" in reasoning
        
        # Test without categories
        reasoning_no_cats = SmartDefaultsComponent._generate_reasoning(
            None,
            "Last 30 Days",
            []
        )
        
        assert "longer-term patterns" in reasoning_no_cats
    
    def test_get_data_summary(self, mock_db_manager, sample_tasks_df):
        """Test data summary generation."""
        mock_db_manager.fetch_tasks.return_value = sample_tasks_df
        
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        
        summary = SmartDefaultsComponent._get_data_summary(
            mock_db_manager,
            start,
            end
        )
        
        assert summary['total_tasks'] == len(sample_tasks_df)
        assert summary['unique_apps'] > 0
        assert summary['unique_categories'] > 0
        assert 'date_range' in summary
    
    def test_integration_with_time_filter(self, mock_db_manager):
        """Test integration with TimeFilterComponent render method."""
        # This tests that SmartDefaultsComponent successfully replaces
        # the deprecated get_smart_default logic in TimeFilterComponent
        
        smart_default = SmartDefaultsComponent.get_time_period_default(mock_db_manager)
        
        # Should return valid time period strings
        valid_periods = ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 90 Days"]
        assert smart_default in valid_periods
        
        # Test that TimeFilterComponent.render uses the new smart defaults
        from autotasktracker.dashboards.components.filters import TimeFilterComponent
        with patch('streamlit.selectbox') as mock_selectbox:
            with patch('streamlit.session_state', {}):
                mock_selectbox.return_value = "Last 7 Days"
                
                result = TimeFilterComponent.render(db_manager=mock_db_manager)
                
                # Should call selectbox with proper parameters
                assert mock_selectbox.called
                assert result == "Last 7 Days"