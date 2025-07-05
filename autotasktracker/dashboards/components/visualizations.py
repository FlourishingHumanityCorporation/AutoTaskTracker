"""Visualization components for dashboards."""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging

# Optional plotly imports with graceful degradation
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None

logger = logging.getLogger(__name__)


def _fallback_chart(title: str, message: str = "Interactive charts require plotly installation"):
    """Show fallback message when plotly is not available."""
    st.info(f"📊 **{title}**\n\n{message}\n\nTo enable interactive charts, install plotly: `pip install plotly`")
    return None


class CategoryPieChart:
    """Category distribution pie chart."""
    
    @staticmethod
    def render(
        category_data: Dict[str, int],
        title: str = "Category Distribution",
        height: int = 400,
        show_values: bool = True
    ):
        """Render category pie chart.
        
        Args:
            category_data: Dict of category: count
            title: Chart title
            height: Chart height
            show_values: Whether to show values on chart
        """
        if not category_data:
            st.info("No category data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        fig = go.Figure(data=[go.Pie(
            labels=list(category_data.keys()),
            values=list(category_data.values()),
            hole=0.3,
            textinfo='label+percent' if show_values else 'percent'
        )])
        
        fig.update_layout(
            title=title,
            height=height,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        

class TimelineChart:
    """Activity timeline visualization."""
    
    @staticmethod
    def render(
        activities: List[Dict[str, Any]],
        title: str = "Activity Timeline",
        height: int = 400,
        color_by: str = "category"
    ):
        """Render activity timeline.
        
        Args:
            activities: List of activity dicts with 'start', 'end', "tasks", "category"
            title: Chart title
            height: Chart height
            color_by: Field to color by
        """
        if not activities:
            st.info("No timeline data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(activities)
        
        fig = px.timeline(
            df,
            x_start="start",
            x_end="end",
            y="tasks",
            color=color_by,
            title=title,
            height=height
        )
        
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Tasks",
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        

class HourlyActivityChart:
    """Hourly activity distribution chart."""
    
    @staticmethod
    def render(
        hourly_data: Dict[int, int],
        title: str = "Hourly Activity",
        height: int = 300,
        chart_type: str = "bar"
    ):
        """Render hourly activity chart.
        
        Args:
            hourly_data: Dict of hour: count
            title: Chart title
            height: Chart height
            chart_type: 'bar' or 'line'
        """
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        # Ensure all hours are represented
        hours = list(range(24))
        counts = [hourly_data.get(h, 0) for h in hours]
        
        if chart_type == "bar":
            fig = go.Figure(data=[
                go.Bar(
                    x=hours,
                    y=counts,
                    text=counts,
                    textposition='auto',
                    marker_color='lightblue'
                )
            ])
        else:  # line
            fig = go.Figure(data=[
                go.Scatter(
                    x=hours,
                    y=counts,
                    mode='lines+markers',
                    line=dict(color='blue', width=2),
                    marker=dict(size=8)
                )
            ])
            
        fig.update_layout(
            title=title,
            xaxis_title="Hour of Day",
            yaxis_title="Activity Count",
            height=height,
            xaxis=dict(
                tickmode='linear',
                tick0=0,
                dtick=1,
                tickformat='%d'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        

class ProductivityHeatmap:
    """Productivity heatmap visualization."""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        title: str = "Productivity Heatmap",
        height: int = 400
    ):
        """Render productivity heatmap.
        
        Args:
            data: DataFrame with 'date', 'hour', 'productivity_score'
            title: Chart title
            height: Chart height
        """
        if data.empty:
            st.info("No productivity data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        # Pivot data for heatmap
        pivot = data.pivot_table(
            index='hour',
            columns='date',
            values='productivity_score',
            aggfunc='mean'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale='Viridis',
            showscale=True
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Hour of Day",
            height=height
        )
        
        st.plotly_chart(fig, use_container_width=True)
        

class TaskDurationChart:
    """Task duration distribution chart."""
    
    @staticmethod
    def render(
        durations: List[float],
        title: str = "Task Duration Distribution",
        bins: int = 20,
        height: int = 400
    ):
        """Render task duration histogram.
        
        Args:
            durations: List of durations in minutes
            title: Chart title
            bins: Number of histogram bins
            height: Chart height
        """
        if not durations:
            st.info("No duration data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        fig = go.Figure(data=[
            go.Histogram(
                x=durations,
                nbinsx=bins,
                marker_color='lightgreen',
                name='Duration'
            )
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title="Duration (minutes)",
            yaxis_title="Count",
            height=height,
            showlegend=False
        )
        
        # Add average line
        avg_duration = sum(durations) / len(durations)
        fig.add_vline(
            x=avg_duration,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Avg: {avg_duration:.1f} min"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        

class TrendChart:
    """Trend visualization over time."""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        date_col: str,
        value_col: str,
        title: str = "Trend Over Time",
        height: int = 400,
        show_trend_line: bool = True
    ):
        """Render trend chart.
        
        Args:
            data: DataFrame with trend data
            date_col: Date column name
            value_col: Value column name
            title: Chart title
            height: Chart height
            show_trend_line: Whether to show trend line
        """
        if data.empty:
            st.info("No trend data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        fig = go.Figure()
        
        # Main line
        fig.add_trace(go.Scatter(
            x=data[date_col],
            y=data[value_col],
            mode='lines+markers',
            name='Value',
            line=dict(color='blue', width=2)
        ))
        
        # Add trend line if requested
        if show_trend_line and len(data) > 1:
            z = np.polyfit(range(len(data)), data[value_col], 1)
            p = np.poly1d(z)
            fig.add_trace(go.Scatter(
                x=data[date_col],
                y=p(range(len(data))),
                mode='lines',
                name='Trend',
                line=dict(color='red', width=2, dash='dash')
            ))
            
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Value",
            height=height,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        

class ComparisonChart:
    """Comparison chart for multiple metrics."""
    
    @staticmethod
    def render(
        metrics: Dict[str, Dict[str, float]],
        title: str = "Metric Comparison",
        height: int = 400,
        chart_type: str = "grouped"
    ):
        """Render comparison chart.
        
        Args:
            metrics: Dict of {metric_name: {category: value}}
            title: Chart title
            height: Chart height
            chart_type: 'grouped' or 'stacked'
        """
        if not metrics:
            st.info("No comparison data to display")
            return
            
        if not PLOTLY_AVAILABLE:
            _fallback_chart(title)
            return
            
        # Prepare data for plotly
        categories = set()
        for metric_data in metrics.values():
            categories.update(metric_data.keys())
        categories = sorted(list(categories))
        
        fig = go.Figure()
        
        for metric_name, metric_data in metrics.items():
            values = [metric_data.get(cat, 0) for cat in categories]
            fig.add_trace(go.Bar(
                name=metric_name,
                x=categories,
                y=values
            ))
            
        fig.update_layout(
            title=title,
            xaxis_title="Category",
            yaxis_title="Value",
            height=height,
            barmode=chart_type
        )
        
        st.plotly_chart(fig, use_container_width=True)