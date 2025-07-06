"""Export component for dashboard data export functionality."""

import io
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import streamlit as st
import logging

from .base_component import StatelessComponent

logger = logging.getLogger(__name__)


class ExportComponent(StatelessComponent):
    """Unified export functionality for all dashboards."""
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default export configuration."""
        return {
            "csv_delimiter": ",",
            "csv_encoding": "utf-8",
            "date_format": "%Y-%m-%d",
            "time_format": "%H:%M",
            "datetime_format": "%Y-%m-%d %H:%M",
            "include_headers": True,
            "max_description_length": 100
        }
    
    def render(self, data: Any, **kwargs) -> None:
        """Render export component - not used for static component."""
        pass
    
    @staticmethod
    def render_csv_button(
        data: Union[pd.DataFrame, List[Dict], str],
        filename: str = "export.csv",
        label: str = "📥 Download CSV",
        columns: Optional[List[str]] = None,
        help_text: Optional[str] = None
    ) -> bool:
        """Render CSV export button.
        
        Args:
            data: Data to export (DataFrame, list of dicts, or CSV string)
            filename: Export filename
            label: Button label
            columns: Specific columns to export (for DataFrame/dict data)
            help_text: Optional help text for button
            
        Returns:
            True if download was triggered
        """
        # Convert data to CSV string
        csv_data = ExportComponent._to_csv_string(data, columns)
        
        # Render download button
        return st.download_button(
            label=label,
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            help=help_text
        )
    
    @staticmethod
    def render_json_button(
        data: Union[Dict, List, pd.DataFrame],
        filename: str = "export.json",
        label: str = "📥 Download JSON",
        indent: int = 2,
        help_text: Optional[str] = None
    ) -> bool:
        """Render JSON export button.
        
        Args:
            data: Data to export
            filename: Export filename
            label: Button label
            indent: JSON indentation
            help_text: Optional help text
            
        Returns:
            True if download was triggered
        """
        # Convert data to JSON string
        json_data = ExportComponent._to_json_string(data, indent)
        
        # Render download button
        return st.download_button(
            label=label,
            data=json_data,
            file_name=filename,
            mime="application/json",
            help=help_text
        )
    
    @staticmethod
    def format_task_export(
        task_groups: List[Any],
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format task data for professional CSV export.
        
        Args:
            task_groups: List of TaskGroup objects
            start_date: Export start date
            end_date: Export end date
            config: Optional configuration overrides
            
        Returns:
            CSV formatted string
        """
        # Merge with default config
        export_config = ExportComponent.get_default_config()
        if config:
            export_config.update(config)
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=export_config["csv_delimiter"])
        
        # Write header
        if export_config["include_headers"]:
            writer.writerow([
                "Date", "Task Group", "Duration", "Start Time", "End Time",
                "Category", "Description", "Activities", "Confidence"
            ])
        
        # Process task groups
        for group in task_groups:
            try:
                # Format date and times
                date_str = group.start_time.strftime(export_config["date_format"])
                start_time_str = group.start_time.strftime(export_config["time_format"])
                end_time_str = group.end_time.strftime(export_config["time_format"])
                
                # Format duration
                duration_str = f"{group.duration_minutes}min"
                
                # Build description from tasks
                activities = []
                for task in group.tasks[:3]:  # First 3 tasks
                    if hasattr(task, 'title') and task.title:
                        activities.append(task.title.strip())
                    elif hasattr(task, 'description') and task.description:
                        activities.append(task.description.strip())
                
                description = "; ".join(activities)
                if len(description) > export_config["max_description_length"]:
                    description = description[:export_config["max_description_length"]] + "..."
                
                # Determine confidence level
                confidence = ExportComponent._calculate_confidence(group.duration_minutes)
                
                # Write row
                writer.writerow([
                    date_str,
                    group.window_title or "Unknown",
                    duration_str,
                    start_time_str,
                    end_time_str,
                    group.category or "Uncategorized",
                    description,
                    len(group.tasks),
                    confidence
                ])
                
            except Exception as e:
                logger.error(f"Error formatting task group: {e}")
                continue
        
        return output.getvalue()
    
    @staticmethod
    def render_export_section(
        export_type: str = "csv",
        data_callback: callable = None,
        filename_prefix: str = "export",
        include_date_range: bool = True,
        additional_formats: Optional[List[str]] = None
    ) -> None:
        """Render complete export section with multiple format options.
        
        Args:
            export_type: Primary export type (csv, json)
            data_callback: Function to get export data
            filename_prefix: Prefix for export filename
            include_date_range: Include date range in filename
            additional_formats: Additional export formats to show
        """
        with st.expander("📥 Export Options", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Export Format")
                format_options = ["CSV", "JSON"]
                if additional_formats:
                    format_options.extend(additional_formats)
                
                selected_format = st.selectbox(
                    "Select format",
                    format_options,
                    label_visibility="collapsed"
                )
            
            with col2:
                st.markdown("### Export Data")
                if st.button("Generate Export", type="primary"):
                    if data_callback:
                        try:
                            data = data_callback()
                            filename = ExportComponent._generate_filename(
                                filename_prefix,
                                selected_format.lower(),
                                include_date_range
                            )
                            
                            if selected_format == "CSV":
                                ExportComponent.render_csv_button(
                                    data, filename, "Download CSV"
                                )
                            elif selected_format == "JSON":
                                ExportComponent.render_json_button(
                                    data, filename, "Download JSON"
                                )
                            else:
                                st.warning(f"{selected_format} export not yet implemented")
                                
                        except Exception as e:
                            st.error(f"Export failed: {str(e)}")
                            logger.error(f"Export error: {e}", exc_info=True)
    
    # Helper methods
    @staticmethod
    def _to_csv_string(data: Union[pd.DataFrame, List[Dict], str], columns: Optional[List[str]] = None) -> str:
        """Convert various data types to CSV string."""
        if isinstance(data, str):
            return data
        elif isinstance(data, pd.DataFrame):
            if columns:
                data = data[columns]
            return data.to_csv(index=False)
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            df = pd.DataFrame(data)
            if columns:
                df = df[columns]
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Unsupported data type for CSV export: {type(data)}")
    
    @staticmethod
    def _to_json_string(data: Union[Dict, List, pd.DataFrame], indent: int = 2) -> str:
        """Convert various data types to JSON string."""
        if isinstance(data, pd.DataFrame):
            data = data.to_dict(orient='records')
        return json.dumps(data, indent=indent, default=str)
    
    @staticmethod
    def _calculate_confidence(duration_minutes: float) -> str:
        """Calculate confidence level based on duration."""
        if duration_minutes >= 2:
            return "High"
        elif duration_minutes >= 1:
            return "Medium"
        else:
            return "Low"
    
    @staticmethod
    def _generate_filename(prefix: str, extension: str, include_date: bool = True) -> str:
        """Generate export filename."""
        filename = prefix
        if include_date:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{date_str}"
        return f"{filename}.{extension}"