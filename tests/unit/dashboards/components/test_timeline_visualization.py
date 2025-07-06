"""Tests for TimelineVisualizationComponent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

import streamlit as st
from autotasktracker.dashboards.components.timeline_visualization import TimelineVisualizationComponent


class TestTimelineVisualizationComponent:
    """Test suite for TimelineVisualizationComponent."""
    
    @pytest.fixture
    def sample_activities(self):
        """Create sample activity data."""
        now = datetime.now()
        return [
            {
                'start': now,
                'end': now + timedelta(minutes=30),
                'task': 'Task 1',
                'category': 'Work'
            },
            {
                'start': now + timedelta(minutes=45),
                'end': now + timedelta(minutes=75),
                'task': 'Task 2', 
                'category': 'Personal'
            }
        ]
    
    @pytest.fixture
    def sample_time_data(self):
        """Create sample time data for task timeline."""
        now = datetime.now()
        return {
            'Task A': [
                {
                    'start': now,
                    'end': now + timedelta(minutes=20),
                    'duration': 20.0,
                    'category': 'Work'
                }
            ],
            'Task B': [
                {
                    'start': now + timedelta(minutes=30),
                    'end': now + timedelta(minutes=50),
                    'duration': 20.0,
                    'category': 'Personal'
                }
            ]
        }
    
    @pytest.fixture
    def sample_gantt_tasks(self):
        """Create sample Gantt task data."""
        now = datetime.now()
        return [
            {
                'task': 'Project Phase 1',
                'start': now,
                'end': now + timedelta(days=7),
                'category': 'Development',
                'progress': 0.7
            },
            {
                'task': 'Project Phase 2',
                'start': now + timedelta(days=5),
                'end': now + timedelta(days=14),
                'category': 'Testing',
                'progress': 0.3
            }
        ]
    
    def test_render_activity_timeline_empty_data(self):
        """Test activity timeline with empty data."""
        with patch('streamlit.info') as mock_info:
            TimelineVisualizationComponent.render_activity_timeline([])
            mock_info.assert_called_once_with("📊 No timeline data to display")
    
    def test_render_activity_timeline_without_plotly(self, sample_activities):
        """Test activity timeline fallback when Plotly unavailable."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', False):
            with patch('streamlit.subheader') as mock_subheader:
                with patch('streamlit.info') as mock_info:
                    with patch('streamlit.write') as mock_write:
                        TimelineVisualizationComponent.render_activity_timeline(sample_activities)
                        
                        mock_subheader.assert_called_once_with("Activity Timeline")
                        mock_info.assert_called_once()
                        assert mock_write.call_count >= 1
    
    @patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', True)
    def test_render_activity_timeline_with_plotly(self, sample_activities):
        """Test activity timeline with Plotly available."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.px') as mock_px:
            mock_fig = MagicMock()
            mock_px.timeline.return_value = mock_fig
            
            with patch('streamlit.plotly_chart') as mock_chart:
                TimelineVisualizationComponent.render_activity_timeline(sample_activities)
                
                mock_px.timeline.assert_called_once()
                mock_chart.assert_called_once_with(mock_fig, use_container_width=True)
    
    def test_render_task_timeline_empty_data(self):
        """Test task timeline with empty data."""
        with patch('streamlit.info') as mock_info:
            TimelineVisualizationComponent.render_task_timeline({})
            mock_info.assert_called_once_with("📊 No task timeline data to display")
    
    def test_render_task_timeline_without_plotly(self, sample_time_data):
        """Test task timeline fallback when Plotly unavailable."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', False):
            with patch('streamlit.subheader') as mock_subheader:
                with patch('streamlit.info') as mock_info:
                    with patch('streamlit.write') as mock_write:
                        TimelineVisualizationComponent.render_task_timeline(sample_time_data)
                        
                        mock_subheader.assert_called_once_with("Task Timeline")
                        mock_info.assert_called_once()
                        assert mock_write.call_count >= 1
    
    @patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', True)
    def test_render_task_timeline_with_plotly(self, sample_time_data):
        """Test task timeline with Plotly available."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.go') as mock_go:
            mock_fig = MagicMock()
            mock_go.Figure.return_value = mock_fig
            mock_go.Bar = MagicMock()
            
            with patch('streamlit.plotly_chart') as mock_chart:
                TimelineVisualizationComponent.render_task_timeline(sample_time_data)
                
                mock_go.Figure.assert_called_once()
                mock_chart.assert_called_once_with(mock_fig, use_container_width=True)
    
    def test_render_gantt_chart_empty_data(self):
        """Test Gantt chart with empty data."""
        with patch('streamlit.info') as mock_info:
            TimelineVisualizationComponent.render_gantt_chart([])
            mock_info.assert_called_once_with("📊 No Gantt chart data to display")
    
    def test_render_gantt_chart_without_plotly(self, sample_gantt_tasks):
        """Test Gantt chart fallback when Plotly unavailable."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', False):
            with patch('streamlit.subheader') as mock_subheader:
                with patch('streamlit.info') as mock_info:
                    with patch('streamlit.write') as mock_write:
                        TimelineVisualizationComponent.render_gantt_chart(sample_gantt_tasks)
                        
                        mock_subheader.assert_called_once_with("Project Gantt Chart")
                        mock_info.assert_called_once()
                        assert mock_write.call_count >= 1
    
    def test_render_timeline_summary_with_metrics(self):
        """Test timeline summary with metrics."""
        timeline_data = {
            'metrics': {
                'total_duration': 120.5,
                'active_periods': 5,
                'avg_session': 24.1,
                'efficiency': 0.85
            }
        }
        
        with patch('streamlit.subheader') as mock_subheader:
            with patch('streamlit.columns') as mock_columns:
                with patch('streamlit.metric') as mock_metric:
                    # Create mock columns with context manager support
                    mock_cols = []
                    for _ in range(4):
                        mock_col = MagicMock()
                        mock_col.__enter__ = MagicMock(return_value=mock_col)
                        mock_col.__exit__ = MagicMock(return_value=None)
                        mock_cols.append(mock_col)
                    mock_columns.return_value = mock_cols
                    
                    TimelineVisualizationComponent.render_timeline_summary(timeline_data)
                    
                    mock_subheader.assert_called_with("📊 Timeline Metrics")
                    assert mock_metric.call_count == 4
    
    def test_render_timeline_summary_with_gaps(self):
        """Test timeline summary with gap analysis."""
        timeline_data = {
            'gaps': [
                {
                    'duration': 15.0,
                    'start': '10:30',
                    'end': '10:45'
                },
                {
                    'duration': 30.0,
                    'start': '14:00',
                    'end': '14:30'
                }
            ]
        }
        
        with patch('streamlit.subheader') as mock_subheader:
            with patch('streamlit.write') as mock_write:
                TimelineVisualizationComponent.render_timeline_summary(
                    timeline_data, 
                    show_metrics=False,
                    show_gaps=True
                )
                
                mock_subheader.assert_called_with("⏸️ Timeline Gaps")
                assert mock_write.call_count >= 2  # One for each gap
    
    def test_render_timeline_summary_with_patterns(self):
        """Test timeline summary with pattern analysis."""
        timeline_data = {
            'patterns': {
                'Most Active Hour': '10:00 AM - 11:00 AM',
                'Peak Productivity': 'Morning sessions',
                'Common Break Time': '15 minutes between tasks'
            }
        }
        
        with patch('streamlit.subheader') as mock_subheader:
            with patch('streamlit.write') as mock_write:
                TimelineVisualizationComponent.render_timeline_summary(
                    timeline_data,
                    show_metrics=False,
                    show_gaps=False,
                    show_patterns=True
                )
                
                mock_subheader.assert_called_with("🔍 Activity Patterns")
                assert mock_write.call_count >= 3  # One for each pattern
    
    def test_get_color_map(self):
        """Test color mapping generation."""
        time_data = {
            'Task 1': [{'category': 'Work'}],
            'Task 2': [{'category': 'Personal'}],
            'Task 3': [{'category': 'Work'}]
        }
        
        color_map = TimelineVisualizationComponent._get_color_map(time_data, 'category')
        
        assert len(color_map) == 2  # Work and Personal
        assert 'Work' in color_map
        assert 'Personal' in color_map
        assert color_map['Work'] != color_map['Personal']
    
    def test_get_duration_color(self):
        """Test duration-based color selection."""
        # Test different duration ranges
        assert TimelineVisualizationComponent._get_duration_color(3) == '#ffffcc'  # < 5 min
        assert TimelineVisualizationComponent._get_duration_color(10) == '#c7e9b4'  # 5-15 min
        assert TimelineVisualizationComponent._get_duration_color(20) == '#7fcdbb'  # 15-30 min
        assert TimelineVisualizationComponent._get_duration_color(45) == '#41b6c4'  # 30-60 min
        assert TimelineVisualizationComponent._get_duration_color(90) == '#2c7fb8'  # > 60 min
    
    def test_create_hover_text(self):
        """Test hover text creation."""
        now = datetime.now()
        period = {
            'start': now,
            'end': now + timedelta(minutes=30),
            'duration': 30.0,
            'category': 'Work',
            'confidence': 0.95
        }
        
        hover_text = TimelineVisualizationComponent._create_hover_text('Test Task', period)
        
        assert 'Test Task' in hover_text
        assert '30.0 min' in hover_text
        assert 'Work' in hover_text
        assert '0.95' in hover_text
    
    def test_render_quick_timeline_activity(self, sample_activities):
        """Test quick timeline with activity type."""
        with patch.object(TimelineVisualizationComponent, 'render_activity_timeline') as mock_render:
            TimelineVisualizationComponent.render_quick_timeline(
                sample_activities,
                timeline_type="activity"
            )
            mock_render.assert_called_once_with(sample_activities, "Activity Timeline")
    
    def test_render_quick_timeline_task(self, sample_time_data):
        """Test quick timeline with task type."""
        with patch.object(TimelineVisualizationComponent, 'render_task_timeline') as mock_render:
            TimelineVisualizationComponent.render_quick_timeline(
                sample_time_data,
                timeline_type="task"
            )
            mock_render.assert_called_once_with(sample_time_data, "Task Timeline")
    
    def test_render_quick_timeline_gantt(self, sample_gantt_tasks):
        """Test quick timeline with Gantt type."""
        with patch.object(TimelineVisualizationComponent, 'render_gantt_chart') as mock_render:
            TimelineVisualizationComponent.render_quick_timeline(
                sample_gantt_tasks,
                timeline_type="gantt"
            )
            mock_render.assert_called_once_with(sample_gantt_tasks, "Gantt Timeline")
    
    def test_render_quick_timeline_invalid_type(self, sample_activities):
        """Test quick timeline with invalid type."""
        with patch('streamlit.error') as mock_error:
            TimelineVisualizationComponent.render_quick_timeline(
                sample_activities,
                timeline_type="invalid"
            )
            mock_error.assert_called_once_with("Unknown timeline type: invalid")
    
    def test_error_handling_in_activity_timeline(self, sample_activities):
        """Test error handling in activity timeline."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', True):
            with patch('autotasktracker.dashboards.components.timeline_visualization.px') as mock_px:
                mock_px.timeline.side_effect = Exception("Plotly error")
                
                with patch('streamlit.error') as mock_error:
                    TimelineVisualizationComponent.render_activity_timeline(sample_activities)
                    mock_error.assert_called_once()
    
    def test_error_handling_in_task_timeline(self, sample_time_data):
        """Test error handling in task timeline."""
        with patch('autotasktracker.dashboards.components.timeline_visualization.PLOTLY_AVAILABLE', True):
            with patch('autotasktracker.dashboards.components.timeline_visualization.go') as mock_go:
                mock_go.Figure.side_effect = Exception("Plotly error")
                
                with patch('streamlit.error') as mock_error:
                    TimelineVisualizationComponent.render_task_timeline(sample_time_data)
                    mock_error.assert_called_once()