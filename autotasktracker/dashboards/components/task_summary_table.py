"""Generic task summary table component for dashboards."""

from typing import List, Dict, Any, Optional, Union, Callable
import pandas as pd
import streamlit as st
from datetime import datetime
import logging

from .base_component import StatelessComponent

logger = logging.getLogger(__name__)


class TaskSummaryTable(StatelessComponent):
    """Flexible task summary table with customizable columns and features."""
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "show_confidence": True,
            "show_category": True,
            "show_timestamps": True,
            "show_export": True,
            "show_help": True,
            "max_task_length": 50,
            "sort_by": "duration",
            "sort_ascending": False,
            "use_container_width": True,
            "hide_index": True,
            "export_format": "csv",
            "confidence_thresholds": {
                "high": 0.8,
                "medium": 0.5
            },
            "confidence_icons": {
                "high": "🟢",
                "medium": "🟡",
                "low": "🔴"
            }
        }
    
    def render(self, data: Any, **kwargs) -> None:
        """Render method not used for static component."""
        pass
    
    @staticmethod
    def render(
        tasks: Union[List[Dict[str, Any]], pd.DataFrame, Dict[str, Dict[str, Any]]],
        columns: Optional[List[str]] = None,
        column_config: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        help_content: Optional[str] = None,
        export_filename: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        custom_formatters: Optional[Dict[str, Callable]] = None
    ) -> Optional[pd.DataFrame]:
        """Render task summary table.
        
        Args:
            tasks: Task data (list of dicts, DataFrame, or dict of task metrics)
            columns: Specific columns to display (None = all)
            column_config: Streamlit column configuration
            title: Optional table title
            help_content: Custom help content
            export_filename: Custom export filename
            config: Configuration overrides
            custom_formatters: Custom column formatters
            
        Returns:
            DataFrame that was displayed (for further processing)
        """
        # Merge configuration
        display_config = TaskSummaryTable.get_default_config()
        if config:
            display_config.update(config)
        
        # Convert data to DataFrame
        df = TaskSummaryTable._prepare_dataframe(tasks, columns, display_config, custom_formatters)
        
        if df.empty:
            st.info("No tasks to display")
            return None
        
        # Display title if provided
        if title:
            st.subheader(title)
        
        # Prepare column configuration
        final_column_config = TaskSummaryTable._prepare_column_config(
            df, column_config, display_config
        )
        
        # Display the dataframe
        st.dataframe(
            df,
            use_container_width=display_config["use_container_width"],
            hide_index=display_config["hide_index"],
            column_config=final_column_config
        )
        
        # Help section
        if display_config["show_help"] and help_content:
            with st.expander("ℹ️ About This Table"):
                st.markdown(help_content)
        
        # Export functionality
        if display_config["show_export"]:
            TaskSummaryTable._render_export(df, export_filename, display_config)
        
        return df
    
    @staticmethod
    def _prepare_dataframe(
        tasks: Union[List[Dict[str, Any]], pd.DataFrame, Dict[str, Dict[str, Any]]],
        columns: Optional[List[str]],
        config: Dict[str, Any],
        custom_formatters: Optional[Dict[str, Callable]]
    ) -> pd.DataFrame:
        """Convert various input formats to DataFrame."""
        # Convert to DataFrame
        if isinstance(tasks, pd.DataFrame):
            df = tasks.copy()
        elif isinstance(tasks, dict):
            # Handle dict of task metrics (like from TimeTracker)
            df = TaskSummaryTable._convert_task_metrics_to_df(tasks, config)
        elif isinstance(tasks, list):
            df = pd.DataFrame(tasks)
        else:
            raise ValueError(f"Unsupported tasks type: {type(tasks)}")
        
        # Apply custom formatters
        if custom_formatters:
            for col, formatter in custom_formatters.items():
                if col in df.columns:
                    df[col] = df[col].apply(formatter)
        
        # Filter columns if specified
        if columns:
            available_cols = [col for col in columns if col in df.columns]
            df = df[available_cols]
        
        # Sort data
        sort_col = config.get("sort_by")
        if sort_col and sort_col in df.columns:
            df = df.sort_values(sort_col, ascending=config["sort_ascending"])
        
        return df
    
    @staticmethod
    def _convert_task_metrics_to_df(
        task_metrics: Dict[str, Dict[str, Any]],
        config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Convert task metrics dict to DataFrame."""
        rows = []
        
        for task_name, metrics in task_metrics.items():
            row = {"Task": task_name}
            
            # Truncate long task names
            max_length = config["max_task_length"]
            if len(task_name) > max_length:
                row["Task"] = task_name[:max_length] + "..."
            
            # Add duration metrics
            if "total_minutes" in metrics:
                row["Duration"] = f"{metrics['total_minutes']:.1f} min"
                row["Duration_raw"] = metrics['total_minutes']  # For sorting
            
            if "active_minutes" in metrics:
                row["Active Time"] = f"{metrics['active_minutes']:.1f} min"
            
            # Add session info
            if "session_count" in metrics:
                row["Sessions"] = metrics['session_count']
            
            # Add confidence with icons
            if config["show_confidence"] and "average_confidence" in metrics:
                conf_value = metrics['average_confidence']
                if conf_value >= config["confidence_thresholds"]["high"]:
                    icon = config["confidence_icons"]["high"]
                elif conf_value >= config["confidence_thresholds"]["medium"]:
                    icon = config["confidence_icons"]["medium"]
                else:
                    icon = config["confidence_icons"]["low"]
                row["Confidence"] = f"{icon} {conf_value:.2f}"
            
            # Add category
            if config["show_category"] and "category" in metrics:
                row["Category"] = metrics["category"]
            
            # Add timestamps
            if config["show_timestamps"]:
                if "first_seen" in metrics and metrics["first_seen"]:
                    row["First Seen"] = metrics["first_seen"].strftime("%H:%M")
                if "last_seen" in metrics and metrics["last_seen"]:
                    row["Last Seen"] = metrics["last_seen"].strftime("%H:%M")
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Sort by duration if available
        if "Duration_raw" in df.columns:
            df = df.sort_values("Duration_raw", ascending=False)
            df = df.drop("Duration_raw", axis=1)  # Remove sorting column
        
        return df
    
    @staticmethod
    def _prepare_column_config(
        df: pd.DataFrame,
        user_config: Optional[Dict[str, Any]],
        display_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare Streamlit column configuration."""
        column_config = {}
        
        # Default configurations for common columns
        default_configs = {
            "Task": st.column_config.TextColumn(
                "Task",
                help="Task or window title",
                max_chars=display_config["max_task_length"] + 3
            ),
            "Duration": st.column_config.TextColumn(
                "Duration",
                help="Total time spent on task"
            ),
            "Active Time": st.column_config.TextColumn(
                "Active Time",
                help="Time excluding idle periods"
            ),
            "Sessions": st.column_config.NumberColumn(
                "Sessions",
                format="%d",
                help="Number of work sessions"
            ),
            "Confidence": st.column_config.TextColumn(
                "Confidence",
                help=f"{display_config['confidence_icons']['high']} High ({display_config['confidence_thresholds']['high']}+), "
                     f"{display_config['confidence_icons']['medium']} Medium ({display_config['confidence_thresholds']['medium']}+), "
                     f"{display_config['confidence_icons']['low']} Low (<{display_config['confidence_thresholds']['medium']})"
            ),
            "Category": st.column_config.TextColumn(
                "Category",
                help="Task category"
            ),
            "First Seen": st.column_config.TextColumn(
                "First Seen",
                help="First occurrence time"
            ),
            "Last Seen": st.column_config.TextColumn(
                "Last Seen",
                help="Last occurrence time"
            )
        }
        
        # Apply default configs for columns that exist
        for col in df.columns:
            if col in default_configs:
                column_config[col] = default_configs[col]
        
        # Override with user config
        if user_config:
            column_config.update(user_config)
        
        return column_config
    
    @staticmethod
    def _render_export(
        df: pd.DataFrame,
        filename: Optional[str],
        config: Dict[str, Any]
    ) -> None:
        """Render export functionality."""
        export_format = config["export_format"].lower()
        
        if export_format == "csv":
            data = df.to_csv(index=False)
            mime = "text/csv"
            extension = "csv"
        elif export_format == "json":
            data = df.to_json(orient="records", indent=2)
            mime = "application/json"
            extension = "json"
        else:
            logger.warning(f"Unsupported export format: {export_format}")
            return
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"task_summary_{timestamp}.{extension}"
        elif not filename.endswith(f".{extension}"):
            filename = f"{filename}.{extension}"
        
        st.download_button(
            label=f"📥 Download Summary ({export_format.upper()})",
            data=data,
            file_name=filename,
            mime=mime
        )
    
    @staticmethod
    def render_compact(
        tasks: Union[List[Dict[str, Any]], pd.DataFrame],
        max_rows: int = 5,
        columns: Optional[List[str]] = None
    ) -> None:
        """Render a compact version of the table.
        
        Args:
            tasks: Task data
            max_rows: Maximum rows to display
            columns: Columns to show (defaults to key columns)
        """
        if columns is None:
            columns = ["Task", "Duration", "Category"]
        
        config = {
            "show_export": False,
            "show_help": False,
            "show_timestamps": False
        }
        
        df = TaskSummaryTable.render(
            tasks=tasks,
            columns=columns,
            config=config
        )
        
        if df is not None and len(df) > max_rows:
            st.caption(f"Showing top {max_rows} of {len(df)} tasks")