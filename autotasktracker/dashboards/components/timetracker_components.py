"""Time tracker specific components."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Plotly imports moved to timeline_visualization component

from .base_component import StatelessComponent
from .timeline_visualization import TimelineVisualizationComponent
from .export import ExportComponent
from .metrics import MetricsRow


class TimeTrackerTimeline(StatelessComponent):
    """Timeline chart specifically for time tracker dashboard."""
    
    @staticmethod
    def render(
        time_data: Dict[str, List[Dict[str, Any]]],
        title: str = "Task Timeline",
        height_per_task: int = 50,
        min_height: int = 400
    ):
        """Render time tracker timeline chart using TimelineVisualizationComponent.
        
        Args:
            time_data: Dict of task_name: list of periods
                      Each period has: start, end, duration, color
            title: Chart title
            height_per_task: Height per task row
            min_height: Minimum chart height
        """
        # Delegate to consolidated timeline component
        TimelineVisualizationComponent.render_task_timeline(
            time_data=time_data,
            title=title,
            height_per_task=height_per_task,
            min_height=min_height,
            show_duration_labels=True,
            color_scheme="custom"  # Use custom colors from period['color']
        )


class TimeTrackerMetrics(StatelessComponent):
    """Enhanced metrics display for time tracker."""
    
    @staticmethod
    def render(daily_summary: Dict[str, Any], category_times: Dict[str, float]):
        """Render time tracker metrics using MetricsRow component.
        
        Args:
            daily_summary: Summary from TimeTracker.get_daily_summary()
            category_times: Dict of category: total_minutes
        """
        # Prepare first row metrics with deltas
        total_time = daily_summary['total_time_minutes']
        time_display = f"{total_time:.1f} min" if total_time < 120 else f"{total_time/60:.1f} hours"
        
        first_row_metrics = {
            "Total Time": time_display,
            "Active Time": (f"{daily_summary['active_time_minutes']:.1f} min", 
                           f"-{daily_summary['idle_percentage']:.1f}% idle"),
            "Focus Score": f"{daily_summary['focus_score']}/100",
            "Sessions": (daily_summary['sessions_count'], 
                        f"{daily_summary['average_session_minutes']:.1f} min avg")
        }
        
        # Render first row using MetricsRow
        MetricsRow.render(first_row_metrics, columns=4, with_delta=True)
        
        # Prepare second row metrics
        high_conf = daily_summary['high_confidence_sessions']
        total_sessions = daily_summary['sessions_count']
        conf_pct = (high_conf / total_sessions * 100) if total_sessions > 0 else 0
        most_used = max(category_times.items(), key=lambda x: x[1])[0] if category_times else "N/A"
        
        second_row_metrics = {
            "Unique Tasks": daily_summary['unique_tasks'],
            "Longest Session": f"{daily_summary['longest_session_minutes']:.1f} min",
            "High Confidence": (f"{high_conf}/{total_sessions}", f"{conf_pct:.0f}%"),
            "Top Category": most_used
        }
        
        # Render second row using MetricsRow
        MetricsRow.render(second_row_metrics, columns=4, with_delta=True)


class TimeTrackerTaskList(StatelessComponent):
    """Enhanced task list for time tracker."""
    
    @staticmethod
    def render(task_groups: Dict[str, Dict[str, Any]], selected_date: datetime):
        """Render time tracker task list.
        
        Args:
            task_groups: Task groups from TimeTracker.group_by_task()
            selected_date: Date for the export filename
        """
        if not task_groups:
            st.info("No tasks to display")
            return
            
        # Create enhanced task summary dataframe
        task_summaries = []
        for task_name, metrics in task_groups.items():
            confidence_icon = "🟢" if metrics['average_confidence'] > 0.8 else "🟡" if metrics['average_confidence'] > 0.5 else "🔴"
            
            task_summaries.append({
                'Task': task_name[:50] + '...' if len(task_name) > 50 else task_name,
                'Total Time (min)': f"{metrics['total_minutes']:.1f}",
                'Active Time (min)': f"{metrics['active_minutes']:.1f}",
                'Sessions': metrics['session_count'],
                'Confidence': f"{confidence_icon} {metrics['average_confidence']:.2f}",
                'Category': metrics["category"],
                'First Seen': metrics['first_seen'].strftime('%H:%M') if metrics['first_seen'] else 'N/A',
                'Last Seen': metrics['last_seen'].strftime('%H:%M') if metrics['last_seen'] else 'N/A'
            })
        
        task_df = pd.DataFrame(task_summaries)
        task_df = task_df.sort_values('Total Time (min)', ascending=False)
        
        # Display dataframe with enhanced formatting
        st.dataframe(
            task_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Time (min)": st.column_config.NumberColumn(
                    "Total Time (min)",
                    format="%.1f",
                    help="Total time including gaps"
                ),
                "Active Time (min)": st.column_config.NumberColumn(
                    "Active Time (min)", 
                    format="%.1f",
                    help="Time excluding long gaps"
                ),
                "Sessions": st.column_config.NumberColumn(
                    "Sessions",
                    format="%d",
                    help="Number of separate work sessions"
                ),
                "Confidence": st.column_config.TextColumn(
                    "Confidence",
                    help="🟢 High (0.8+), 🟡 Medium (0.5+), 🔴 Low (<0.5)"
                )
            }
        )
        
        # Add information about the enhanced metrics
        with st.expander("ℹ️ About Enhanced Time Tracking"):
            st.markdown("""
            **Enhanced Features:**
            - **Active Time**: Excludes idle gaps longer than 5 minutes
            - **Confidence Score**: Based on screenshot density and gap patterns
            - **Smart Session Detection**: Accounts for 4-second screenshot intervals
            - **Category-Aware Gaps**: Different gap thresholds for different activities
            
            **Confidence Levels:**
            - 🟢 **High (0.8+)**: Dense screenshots, few gaps - very accurate
            - 🟡 **Medium (0.5-0.8)**: Some gaps detected - mostly accurate  
            - 🔴 **Low (<0.5)**: Many gaps or sparse data - estimate only
            """)
        
        # Export button using ExportComponent
        ExportComponent.render_csv_button(
            data=task_df,
            filename=f"time_tracking_{selected_date.strftime('%Y%m%d')}.csv",
            label="📥 Download Task Report (CSV)",
            help_text="Download detailed time tracking report"
        )