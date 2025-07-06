"""Timeline visualization component for activity and task timelines."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Literal
from collections import defaultdict
import logging

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None

from .base_component import StatelessComponent

logger = logging.getLogger(__name__)


class TimelineVisualizationComponent(StatelessComponent):
    """Comprehensive timeline visualization component for various dashboard needs."""
    
    @staticmethod
    def render_activity_timeline(
        activities: List[Dict[str, Any]],
        title: str = "Activity Timeline",
        height: int = 400,
        color_by: str = "category",
        show_gaps: bool = True,
        time_format: str = "%H:%M"
    ):
        """Render activity timeline using Plotly timeline chart.
        
        Args:
            activities: List of activity dicts with 'start', 'end', 'task', 'category'
            title: Chart title
            height: Chart height in pixels
            color_by: Field to color timeline segments by
            show_gaps: Whether to highlight gaps between activities
            time_format: Time format for hover text
        """
        if not activities:
            st.info("📊 No timeline data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            TimelineVisualizationComponent._render_fallback_timeline(activities, title)
            return
            
        try:
            # Convert to DataFrame and ensure datetime columns
            df = pd.DataFrame(activities)
            df['start'] = pd.to_datetime(df['start'])
            df['end'] = pd.to_datetime(df['end'])
            df['duration'] = (df['end'] - df['start']).dt.total_seconds() / 60  # Minutes
            
            # Create timeline chart
            fig = px.timeline(
                df,
                x_start="start",
                x_end="end",
                y="task" if "task" in df.columns else "category",
                color=color_by if color_by in df.columns else "category",
                title=title,
                height=height,
                hover_data=['duration']
            )
            
            # Customize layout
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Tasks/Activities",
                showlegend=True,
                hovermode='closest'
            )
            
            # Add gap visualization if requested
            if show_gaps and len(df) > 1:
                TimelineVisualizationComponent._add_gap_visualization(fig, df)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering activity timeline: {e}")
            st.error(f"Timeline rendering error: {str(e)}")
    
    @staticmethod
    def render_task_timeline(
        time_data: Dict[str, List[Dict[str, Any]]],
        title: str = "Task Timeline",
        height_per_task: int = 50,
        min_height: int = 400,
        show_duration_labels: bool = True,
        color_scheme: str = "category"
    ):
        """Render horizontal bar timeline for tasks with multiple periods.
        
        Args:
            time_data: Dict of task_name: list of periods
                      Each period has: start, end, duration, category, color (optional)
            title: Chart title
            height_per_task: Height per task row in pixels
            min_height: Minimum chart height
            show_duration_labels: Whether to show duration text on bars
            color_scheme: How to color bars ('category', 'duration', 'custom')
        """
        if not time_data:
            st.info("📊 No task timeline data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            TimelineVisualizationComponent._render_fallback_task_timeline(time_data, title)
            return
            
        try:
            fig = go.Figure()
            
            # Color mapping for categories
            color_map = TimelineVisualizationComponent._get_color_map(time_data, color_scheme)
            
            # Create horizontal bars for each task period
            for task_name, periods in time_data.items():
                for i, period in enumerate(periods):
                    # Determine color
                    if 'color' in period:
                        color = period['color']
                    elif color_scheme == "category":
                        color = color_map.get(period.get('category', 'Unknown'), 'lightblue')
                    elif color_scheme == "duration":
                        color = TimelineVisualizationComponent._get_duration_color(period['duration'])
                    else:
                        color = 'lightblue'
                    
                    # Create hover text
                    hover_text = TimelineVisualizationComponent._create_hover_text(task_name, period)
                    
                    fig.add_trace(go.Bar(
                        x=[period['duration']],
                        y=[f"{task_name}_{i}" if len(periods) > 1 else task_name],
                        orientation='h',
                        name=period.get('category', task_name),
                        text=f"{period['duration']:.1f} min" if show_duration_labels else "",
                        textposition='inside',
                        hovertemplate=hover_text + "<extra></extra>",
                        showlegend=i == 0,  # Only show legend for first occurrence
                        marker_color=color,
                        base=0
                    ))
            
            # Update layout
            chart_height = max(min_height, len(time_data) * height_per_task)
            fig.update_layout(
                title=title,
                xaxis_title="Duration (minutes)",
                yaxis_title="Tasks",
                barmode='stack',
                height=chart_height,
                showlegend=True,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering task timeline: {e}")
            st.error(f"Task timeline rendering error: {str(e)}")
    
    @staticmethod
    def render_gantt_chart(
        tasks: List[Dict[str, Any]],
        title: str = "Project Gantt Chart",
        height: int = 500,
        group_by: Optional[str] = None,
        show_progress: bool = False
    ):
        """Render Gantt chart for project-style timeline visualization.
        
        Args:
            tasks: List of task dicts with 'task', 'start', 'end', 'progress' (optional)
            title: Chart title
            height: Chart height
            group_by: Field to group tasks by (creates sub-charts)
            show_progress: Whether to show progress bars within tasks
        """
        if not tasks:
            st.info("📊 No Gantt chart data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            TimelineVisualizationComponent._render_fallback_gantt(tasks, title)
            return
            
        try:
            df = pd.DataFrame(tasks)
            df['start'] = pd.to_datetime(df['start'])
            df['end'] = pd.to_datetime(df['end'])
            
            if group_by and group_by in df.columns:
                # Create subplot for each group
                groups = df[group_by].unique()
                fig = make_subplots(
                    rows=len(groups),
                    cols=1,
                    subplot_titles=[f"{group_by}: {group}" for group in groups],
                    shared_xaxes=True,
                    vertical_spacing=0.1
                )
                
                for i, group in enumerate(groups):
                    group_data = df[df[group_by] == group]
                    TimelineVisualizationComponent._add_gantt_traces(
                        fig, group_data, row=i+1, show_progress=show_progress
                    )
            else:
                # Single Gantt chart
                fig = go.Figure()
                TimelineVisualizationComponent._add_gantt_traces(
                    fig, df, show_progress=show_progress
                )
            
            fig.update_layout(
                title=title,
                height=height,
                xaxis_title="Timeline",
                showlegend=True,
                barmode='overlay'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering Gantt chart: {e}")
            st.error(f"Gantt chart rendering error: {str(e)}")
    
    @staticmethod
    def render_timeline_summary(
        timeline_data: Dict[str, Any],
        show_metrics: bool = True,
        show_gaps: bool = True,
        show_patterns: bool = True
    ):
        """Render summary information about timeline data.
        
        Args:
            timeline_data: Dict with timeline statistics and analysis
            show_metrics: Whether to show timeline metrics
            show_gaps: Whether to show gap analysis
            show_patterns: Whether to show pattern analysis
        """
        if show_metrics and 'metrics' in timeline_data:
            st.subheader("📊 Timeline Metrics")
            metrics = timeline_data['metrics']
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Duration", f"{metrics.get('total_duration', 0):.1f} min")
            with col2:
                st.metric("Active Periods", metrics.get('active_periods', 0))
            with col3:
                st.metric("Average Session", f"{metrics.get('avg_session', 0):.1f} min")
            with col4:
                st.metric("Efficiency", f"{metrics.get('efficiency', 0):.1%}")
        
        if show_gaps and 'gaps' in timeline_data:
            st.subheader("⏸️ Timeline Gaps")
            gaps = timeline_data['gaps']
            if gaps:
                for gap in gaps[:5]:  # Show top 5 gaps
                    st.write(f"• {gap['duration']:.1f} min gap from {gap['start']} to {gap['end']}")
            else:
                st.info("No significant gaps detected")
        
        if show_patterns and 'patterns' in timeline_data:
            st.subheader("🔍 Activity Patterns")
            patterns = timeline_data['patterns']
            for pattern_name, pattern_info in patterns.items():
                st.write(f"**{pattern_name}**: {pattern_info}")
    
    @staticmethod
    def _add_gap_visualization(fig, df: pd.DataFrame) -> None:
        """Add gap visualization to timeline chart."""
        gaps = []
        for i in range(len(df) - 1):
            gap_start = df.iloc[i]['end']
            gap_end = df.iloc[i + 1]['start']
            gap_duration = (gap_end - gap_start).total_seconds() / 60
            
            if gap_duration > 5:  # Only show gaps > 5 minutes
                gaps.append({
                    'start': gap_start,
                    'end': gap_end,
                    'duration': gap_duration
                })
        
        # Add gap indicators
        for gap in gaps:
            fig.add_vrect(
                x0=gap['start'],
                x1=gap['end'],
                fillcolor="rgba(255,0,0,0.1)",
                layer="below",
                line_width=0,
                annotation_text=f"Gap: {gap['duration']:.0f}m"
            )
    
    @staticmethod
    def _get_color_map(time_data: Dict, color_scheme: str) -> Dict[str, str]:
        """Generate color mapping for timeline visualization."""
        categories = set()
        for periods in time_data.values():
            for period in periods:
                categories.add(period.get('category', 'Unknown'))
        
        # Default color palette
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        
        return {cat: colors[i % len(colors)] for i, cat in enumerate(sorted(categories))}
    
    @staticmethod
    def _get_duration_color(duration: float) -> str:
        """Get color based on duration (heatmap style)."""
        if duration < 5:
            return '#ffffcc'
        elif duration < 15:
            return '#c7e9b4'
        elif duration < 30:
            return '#7fcdbb'
        elif duration < 60:
            return '#41b6c4'
        else:
            return '#2c7fb8'
    
    @staticmethod
    def _create_hover_text(task_name: str, period: Dict[str, Any]) -> str:
        """Create detailed hover text for timeline elements."""
        hover_lines = [
            f"<b>{task_name}</b>",
            f"Start: {period['start'].strftime('%H:%M')}",
            f"End: {period['end'].strftime('%H:%M')}",
            f"Duration: {period['duration']:.1f} min"
        ]
        
        # Add optional fields
        if 'category' in period:
            hover_lines.append(f"Category: {period['category']}")
        if 'confidence' in period:
            hover_lines.append(f"Confidence: {period['confidence']:.2f}")
        if 'active_duration' in period:
            hover_lines.append(f"Active: {period['active_duration']:.1f} min")
        
        return "<br>".join(hover_lines)
    
    @staticmethod
    def _add_gantt_traces(fig, df: pd.DataFrame, row: int = None, show_progress: bool = False):
        """Add Gantt chart traces to figure."""
        for _, task in df.iterrows():
            # Main task bar
            fig.add_trace(
                go.Bar(
                    x=[task['end'] - task['start']],
                    y=[task['task']],
                    base=task['start'],
                    orientation='h',
                    name=task.get('category', 'Task'),
                    hovertemplate=(
                        f"<b>{task['task']}</b><br>"
                        f"Start: {task['start']}<br>"
                        f"End: {task['end']}<br>"
                        f"Duration: {(task['end'] - task['start']).days} days"
                        "<extra></extra>"
                    ),
                    marker_color='lightblue',
                    showlegend=False
                ),
                row=row, col=1 if row else None
            )
            
            # Progress bar if requested
            if show_progress and 'progress' in task:
                progress_duration = (task['end'] - task['start']) * task['progress']
                fig.add_trace(
                    go.Bar(
                        x=[progress_duration],
                        y=[task['task']],
                        base=task['start'],
                        orientation='h',
                        name=f"Progress ({task['progress']:.1%})",
                        marker_color='darkblue',
                        showlegend=False
                    ),
                    row=row, col=1 if row else None
                )
    
    @staticmethod
    def _render_fallback_timeline(activities: List[Dict], title: str):
        """Render simple fallback timeline when Plotly unavailable."""
        st.subheader(title)
        st.info("📊 Interactive timeline requires plotly installation")
        
        for activity in activities[:10]:  # Show first 10
            start = activity.get('start', 'Unknown')
            end = activity.get('end', 'Unknown')
            task = activity.get('task', activity.get('category', 'Task'))
            st.write(f"• **{task}**: {start} → {end}")
    
    @staticmethod
    def _render_fallback_task_timeline(time_data: Dict, title: str):
        """Render simple fallback task timeline when Plotly unavailable."""
        st.subheader(title)
        st.info("📊 Interactive timeline requires plotly installation")
        
        for task, periods in time_data.items():
            total_duration = sum(p['duration'] for p in periods)
            st.write(f"• **{task}**: {total_duration:.1f} minutes ({len(periods)} periods)")
    
    @staticmethod
    def _render_fallback_gantt(tasks: List[Dict], title: str):
        """Render simple fallback Gantt chart when Plotly unavailable."""
        st.subheader(title)
        st.info("📊 Interactive Gantt chart requires plotly installation")
        
        for task in tasks:
            task_name = task.get('task', 'Unknown')
            start = task.get('start', 'Unknown')
            end = task.get('end', 'Unknown')
            st.write(f"• **{task_name}**: {start} → {end}")
    
    @staticmethod
    def render_quick_timeline(
        data: Union[List[Dict], Dict[str, List[Dict]]],
        timeline_type: Literal["activity", "task", "gantt"] = "activity",
        title: Optional[str] = None,
        **kwargs
    ):
        """Quick timeline rendering with automatic type detection.
        
        Args:
            data: Timeline data (format depends on timeline_type)
            timeline_type: Type of timeline to render
            title: Chart title (auto-generated if None)
            **kwargs: Additional arguments for specific timeline types
        """
        if title is None:
            title = f"{timeline_type.title()} Timeline"
        
        if timeline_type == "activity":
            TimelineVisualizationComponent.render_activity_timeline(data, title, **kwargs)
        elif timeline_type == "task":
            TimelineVisualizationComponent.render_task_timeline(data, title, **kwargs)
        elif timeline_type == "gantt":
            TimelineVisualizationComponent.render_gantt_chart(data, title, **kwargs)
        else:
            st.error(f"Unknown timeline type: {timeline_type}")