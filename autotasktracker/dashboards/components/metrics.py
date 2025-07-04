"""Metrics display components for dashboards."""

import streamlit as st
from typing import Dict, Any, Optional, List, Union


class MetricsCard:
    """Single metric card component."""
    
    @staticmethod
    def render(
        label: str, 
        value: Union[str, int, float],
        delta: Optional[Union[str, int, float]] = None,
        delta_color: str = "normal",
        help_text: Optional[str] = None
    ):
        """Render a single metric card.
        
        Args:
            label: Metric label
            value: Metric value
            delta: Optional change value
            delta_color: Color for delta ("normal", "inverse", "off")
            help_text: Optional help tooltip
        """
        st.metric(
            label=label,
            value=value,
            delta=delta,
            delta_color=delta_color,
            help=help_text
        )
        

class MetricsRow:
    """Row of metrics cards."""
    
    @staticmethod
    def render(
        metrics: Dict[str, Any],
        columns: Optional[int] = None,
        with_delta: bool = False
    ):
        """Render a row of metrics.
        
        Args:
            metrics: Dict of label: value or label: (value, delta)
            columns: Number of columns (auto if None)
            with_delta: Whether metrics include delta values
        """
        if columns is None:
            columns = min(len(metrics), 4)
            
        cols = st.columns(columns)
        
        for i, (label, data) in enumerate(metrics.items()):
            with cols[i % columns]:
                if with_delta and isinstance(data, tuple):
                    value, delta = data
                    MetricsCard.render(label, value, delta)
                else:
                    MetricsCard.render(label, data)
                    

class MetricsSummary:
    """Summary metrics component with categories."""
    
    @staticmethod
    def render(
        total_items: int,
        time_range: str,
        categories: Optional[Dict[str, int]] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """Render a metrics summary section.
        
        Args:
            total_items: Total number of items
            time_range: Time range description
            categories: Optional category breakdown
            additional_metrics: Optional additional metrics to display
        """
        # Main metrics row
        main_metrics = {
            "Total Items": total_items,
            "Time Range": time_range
        }
        
        if additional_metrics:
            main_metrics.update(additional_metrics)
            
        MetricsRow.render(main_metrics)
        
        # Category breakdown if provided
        if categories:
            st.markdown("### 📊 Category Breakdown")
            
            # Sort categories by count
            sorted_categories = sorted(
                categories.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Display as columns
            cols = st.columns(min(len(sorted_categories), 3))
            for i, (category, count) in enumerate(sorted_categories):
                with cols[i % len(cols)]:
                    st.metric(category, count)