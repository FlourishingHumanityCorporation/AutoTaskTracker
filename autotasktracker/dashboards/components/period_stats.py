"""Period statistics component for time-based analytics and comparisons."""

import streamlit as st
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Tuple, Optional, Callable
import pandas as pd

from .base_component import StatelessComponent
from .metrics import MetricsRow


class PeriodStats(StatelessComponent):
    """Component for displaying period-based statistics and comparisons."""
    
    # Common period definitions
    PERIODS = {
        "Today": lambda: (date.today(), date.today()),
        "Yesterday": lambda: (date.today() - timedelta(days=1), date.today() - timedelta(days=1)),
        "Last 7 Days": lambda: (date.today() - timedelta(days=6), date.today()),
        "Last 30 Days": lambda: (date.today() - timedelta(days=29), date.today()),
        "This Week": lambda: PeriodStats._get_week_range(),
        "Last Week": lambda: PeriodStats._get_week_range(-1),
        "This Month": lambda: PeriodStats._get_month_range(),
        "Last Month": lambda: PeriodStats._get_month_range(-1),
        "Previous Period": None,  # Calculated based on primary period
        "Custom": None  # Handled separately
    }
    
    @staticmethod
    def _get_week_range(offset: int = 0) -> Tuple[date, date]:
        """Get start and end date for a week."""
        today = date.today()
        # Find Monday of the week
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday - (offset * 7))
        sunday = monday + timedelta(days=6)
        return (monday, min(sunday, date.today()))
    
    @staticmethod
    def _get_month_range(offset: int = 0) -> Tuple[date, date]:
        """Get start and end date for a month."""
        today = date.today()
        if offset == 0:
            # This month
            first_day = date(today.year, today.month, 1)
            return (first_day, today)
        else:
            # Previous months
            first_day = date(today.year, today.month, 1)
            for _ in range(abs(offset)):
                first_day = first_day - timedelta(days=1)
                first_day = date(first_day.year, first_day.month, 1)
            # Last day of that month
            if first_day.month == 12:
                last_day = date(first_day.year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(first_day.year, first_day.month + 1, 1) - timedelta(days=1)
            return (first_day, last_day)
    
    @staticmethod
    def render_period_selector(
        key: str = "period_select",
        default_period: str = "Last 7 Days",
        allow_comparison: bool = False,
        custom_periods: Optional[Dict[str, Callable]] = None
    ) -> Dict[str, Any]:
        """Render period selection controls.
        
        Args:
            key: Unique key for session state
            default_period: Default period selection
            allow_comparison: Whether to show comparison period selection
            custom_periods: Additional custom periods to include
            
        Returns:
            Dict with 'period', 'start_date', 'end_date', and optionally
            'compare_period', 'compare_start', 'compare_end'
        """
        # Merge custom periods if provided
        periods = PeriodStats.PERIODS.copy()
        if custom_periods:
            periods.update(custom_periods)
        
        col1, col2 = st.columns(2) if allow_comparison else (st.container(), None)
        
        with col1:
            if allow_comparison:
                st.markdown("**Primary Period**")
            
            selected_period = st.selectbox(
                "Select Period",
                options=list(periods.keys()),
                index=list(periods.keys()).index(default_period),
                key=f"{key}_primary",
                label_visibility="collapsed" if not allow_comparison else "visible"
            )
            
            if selected_period == "Custom":
                start_date = st.date_input(
                    "Start Date",
                    value=date.today() - timedelta(days=6),
                    key=f"{key}_start"
                )
                end_date = st.date_input(
                    "End Date",
                    value=date.today(),
                    key=f"{key}_end"
                )
            else:
                start_date, end_date = periods[selected_period]()
        
        result = {
            'period': selected_period,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Comparison period selection
        if allow_comparison and col2:
            with col2:
                st.markdown("**Comparison Period**")
                
                compare_enabled = st.checkbox(
                    "Enable Comparison",
                    key=f"{key}_compare_enabled"
                )
                
                if compare_enabled:
                    compare_period = st.selectbox(
                        "Compare With",
                        options=list(periods.keys()),
                        index=list(periods.keys()).index("Previous Period"),
                        key=f"{key}_compare",
                        label_visibility="collapsed"
                    )
                    
                    if compare_period == "Custom":
                        compare_start = st.date_input(
                            "Compare Start",
                            value=start_date - timedelta(days=7),
                            key=f"{key}_compare_start"
                        )
                        compare_end = st.date_input(
                            "Compare End",
                            value=end_date - timedelta(days=7),
                            key=f"{key}_compare_end"
                        )
                    elif compare_period == "Previous Period":
                        # Calculate previous period based on primary period
                        period_length = (end_date - start_date).days + 1
                        compare_start = start_date - timedelta(days=period_length)
                        compare_end = end_date - timedelta(days=period_length)
                    else:
                        compare_start, compare_end = periods[compare_period]()
                    
                    result.update({
                        'compare_enabled': True,
                        'compare_period': compare_period,
                        'compare_start': compare_start,
                        'compare_end': compare_end
                    })
                else:
                    result['compare_enabled'] = False
        
        return result
    
    @staticmethod
    def render_period_statistics(
        stats: Dict[str, Any],
        compare_stats: Optional[Dict[str, Any]] = None,
        title: str = "Period Statistics",
        metrics_to_show: Optional[List[str]] = None,
        format_functions: Optional[Dict[str, Callable]] = None
    ):
        """Render period statistics with optional comparison.
        
        Args:
            stats: Primary period statistics
            compare_stats: Comparison period statistics (optional)
            title: Section title
            metrics_to_show: List of metric keys to display (all if None)
            format_functions: Dict of metric_key: format_function
        """
        st.subheader(title)
        
        # Default metrics if none specified
        if metrics_to_show is None:
            metrics_to_show = list(stats.keys())
        
        # Default formatters
        default_formatters = {
            'total_activities': lambda x: f"{x:,}",
            'active_days': lambda x: f"{x}",
            'daily_average': lambda x: f"{x:.1f}",
            'productivity_rate': lambda x: f"{x:.1f}%",
            'efficiency_score': lambda x: f"{x:.1f}/100"
        }
        
        if format_functions:
            default_formatters.update(format_functions)
        
        # Calculate number of columns needed
        num_metrics = len(metrics_to_show)
        cols_per_row = min(4, num_metrics)
        
        # Render metrics in rows
        for i in range(0, num_metrics, cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, col in enumerate(cols):
                if i + j < num_metrics:
                    metric_key = metrics_to_show[i + j]
                    if metric_key in stats:
                        with col:
                            # Get formatter
                            formatter = default_formatters.get(
                                metric_key,
                                lambda x: str(x)
                            )
                            
                            # Format display name
                            display_name = metric_key.replace('_', ' ').title()
                            
                            # Calculate delta if comparison available
                            if compare_stats and metric_key in compare_stats:
                                current_val = stats[metric_key]
                                compare_val = compare_stats[metric_key]
                                
                                # Calculate percentage change for numeric values
                                if isinstance(current_val, (int, float)) and isinstance(compare_val, (int, float)):
                                    if compare_val != 0:
                                        delta_pct = ((current_val - compare_val) / compare_val) * 100
                                        delta_str = f"{delta_pct:+.1f}%"
                                    else:
                                        delta_str = "+∞" if current_val > 0 else "0%"
                                else:
                                    delta_str = None
                                
                                st.metric(
                                    display_name,
                                    formatter(current_val),
                                    delta=delta_str,
                                    help=f"Previous: {formatter(compare_val)}"
                                )
                            else:
                                st.metric(
                                    display_name,
                                    formatter(stats[metric_key])
                                )
    
    @staticmethod
    def render_period_comparison_chart(
        data: pd.DataFrame,
        metric_column: str,
        period_column: str = "period",
        title: str = "Period Comparison",
        chart_type: str = "bar",
        height: int = 400
    ):
        """Render a comparison chart between periods.
        
        Args:
            data: DataFrame with period data
            metric_column: Column name for the metric to compare
            period_column: Column name identifying the period
            title: Chart title
            chart_type: Type of chart ('bar', 'line')
            height: Chart height in pixels
        """
        # Import here to avoid circular dependency
        from .visualizations import ComparisonChart, TrendChart
        
        if chart_type == "bar":
            # Convert to format expected by ComparisonChart
            metrics = {metric_column: {}}
            for _, row in data.iterrows():
                metrics[metric_column][row[period_column]] = row[metric_column]
            
            ComparisonChart.render(
                metrics=metrics,
                title=title,
                height=height
            )
        else:
            # Use TrendChart for line charts
            TrendChart.render(
                data=data,
                date_col=period_column,
                value_col=metric_column,
                title=title,
                height=height
            )
    
    @staticmethod
    def calculate_period_stats(
        data: pd.DataFrame,
        group_by: Optional[str] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calculate statistics for a period of data.
        
        Args:
            data: DataFrame with the period's data
            group_by: Optional column to group by
            metrics: List of metrics to calculate
            
        Returns:
            Dictionary of calculated statistics
        """
        if data.empty:
            return {
                'total_records': 0,
                'period_days': 0,
                'daily_average': 0
            }
        
        stats = {
            'total_records': len(data),
            'period_days': data['date'].nunique() if 'date' in data.columns else 1,
        }
        
        # Calculate daily average
        stats['daily_average'] = stats['total_records'] / max(stats['period_days'], 1)
        
        # Additional metrics if specified
        if metrics:
            for metric in metrics:
                if metric in data.columns:
                    if data[metric].dtype in ['int64', 'float64']:
                        stats[f'{metric}_sum'] = data[metric].sum()
                        stats[f'{metric}_avg'] = data[metric].mean()
                        stats[f'{metric}_max'] = data[metric].max()
                        stats[f'{metric}_min'] = data[metric].min()
        
        # Group by analysis if specified
        if group_by and group_by in data.columns:
            stats[f'unique_{group_by}'] = data[group_by].nunique()
            stats[f'top_{group_by}'] = data[group_by].value_counts().index[0] if len(data) > 0 else None
        
        return stats