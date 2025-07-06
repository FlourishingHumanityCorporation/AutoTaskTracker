"""Raw data viewer component for displaying and exploring dataframes."""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import io

from .base_component import StatelessComponent
from .export import ExportComponent


class RawDataViewer(StatelessComponent):
    """Component for viewing, searching, and exporting raw data with pagination."""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        title: str = "Raw Data",
        key_prefix: str = "raw_data",
        page_size: int = 50,
        enable_search: bool = True,
        enable_export: bool = True,
        enable_column_selection: bool = True,
        column_config: Optional[Dict[str, Any]] = None,
        default_columns: Optional[List[str]] = None,
        show_row_count: bool = True,
        expandable: bool = True,
        expanded_by_default: bool = False
    ) -> pd.DataFrame:
        """Render raw data viewer with pagination, search, and export.
        
        Args:
            data: DataFrame to display
            title: Title for the data viewer
            key_prefix: Unique key prefix for session state
            page_size: Number of rows per page
            enable_search: Whether to enable search functionality
            enable_export: Whether to enable export functionality
            enable_column_selection: Whether to allow column selection
            column_config: Column configuration for st.dataframe
            default_columns: Default columns to display (all if None)
            show_row_count: Whether to show total row count
            expandable: Whether to put viewer in an expander
            expanded_by_default: Whether expander starts expanded
            
        Returns:
            The filtered/paginated dataframe being displayed
        """
        if data.empty:
            st.info(f"No data available for {title}")
            return data
            
        # Initialize session state
        if f"{key_prefix}_page" not in st.session_state:
            st.session_state[f"{key_prefix}_page"] = 0
        if f"{key_prefix}_search" not in st.session_state:
            st.session_state[f"{key_prefix}_search"] = ""
        if f"{key_prefix}_columns" not in st.session_state:
            st.session_state[f"{key_prefix}_columns"] = default_columns or list(data.columns)
            
        # Container for the viewer
        if expandable:
            container = st.expander(f"🗂️ {title}", expanded=expanded_by_default)
        else:
            container = st.container()
            if title:
                container.subheader(f"🗂️ {title}")
                
        with container:
            # Top controls row
            control_cols = st.columns([2, 2, 1, 1])
            
            # Search functionality
            filtered_data = data.copy()
            search_query = ""
            
            with control_cols[0]:
                if enable_search:
                    search_query = st.text_input(
                        "Search",
                        value=st.session_state[f"{key_prefix}_search"],
                        key=f"{key_prefix}_search_input",
                        placeholder="🔍 Search all columns...",
                        label_visibility="collapsed"
                    )
                    st.session_state[f"{key_prefix}_search"] = search_query
                    
                    if search_query:
                        # Search across all string columns
                        mask = pd.Series([False] * len(filtered_data))
                        for col in filtered_data.select_dtypes(include=['object']).columns:
                            mask |= filtered_data[col].astype(str).str.contains(
                                search_query, case=False, na=False
                            )
                        filtered_data = filtered_data[mask]
                        
            # Column selection
            with control_cols[1]:
                if enable_column_selection and len(data.columns) > 1:
                    selected_columns = st.multiselect(
                        "Columns",
                        options=list(data.columns),
                        default=st.session_state[f"{key_prefix}_columns"],
                        key=f"{key_prefix}_column_select",
                        label_visibility="collapsed"
                    )
                    if selected_columns:
                        st.session_state[f"{key_prefix}_columns"] = selected_columns
                        filtered_data = filtered_data[selected_columns]
                else:
                    selected_columns = st.session_state[f"{key_prefix}_columns"]
                    if selected_columns and set(selected_columns).issubset(set(filtered_data.columns)):
                        filtered_data = filtered_data[selected_columns]
                        
            # Row count
            with control_cols[2]:
                if show_row_count:
                    total_rows = len(data)
                    filtered_rows = len(filtered_data)
                    if search_query:
                        st.metric("Rows", f"{filtered_rows}/{total_rows}", 
                                 delta=f"-{total_rows - filtered_rows}")
                    else:
                        st.metric("Rows", total_rows)
                        
            # Export button
            with control_cols[3]:
                if enable_export and not filtered_data.empty:
                    from .export import ExportComponent
                    ExportComponent.render_csv_button(
                        data=filtered_data,
                        filename=f"{title.lower().replace(' ', '_')}.csv",
                        label="📥 Export"
                    )
                    
            # Pagination controls
            if len(filtered_data) > page_size:
                total_pages = (len(filtered_data) - 1) // page_size + 1
                
                col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
                
                with col1:
                    if st.button("⏮️ First", key=f"{key_prefix}_first", 
                               disabled=st.session_state[f"{key_prefix}_page"] == 0):
                        st.session_state[f"{key_prefix}_page"] = 0
                        
                with col2:
                    if st.button("◀️ Prev", key=f"{key_prefix}_prev",
                               disabled=st.session_state[f"{key_prefix}_page"] == 0):
                        st.session_state[f"{key_prefix}_page"] -= 1
                        
                with col3:
                    st.write(f"Page {st.session_state[f'{key_prefix}_page'] + 1} of {total_pages}")
                    
                with col4:
                    if st.button("Next ▶️", key=f"{key_prefix}_next",
                               disabled=st.session_state[f"{key_prefix}_page"] >= total_pages - 1):
                        st.session_state[f"{key_prefix}_page"] += 1
                        
                with col5:
                    if st.button("Last ⏭️", key=f"{key_prefix}_last",
                               disabled=st.session_state[f"{key_prefix}_page"] >= total_pages - 1):
                        st.session_state[f"{key_prefix}_page"] = total_pages - 1
                        
                # Calculate page slice
                start_idx = st.session_state[f"{key_prefix}_page"] * page_size
                end_idx = min(start_idx + page_size, len(filtered_data))
                page_data = filtered_data.iloc[start_idx:end_idx]
            else:
                page_data = filtered_data
                
            # Display the data
            st.dataframe(
                page_data,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                height=min(400, (len(page_data) + 1) * 35 + 20)  # Dynamic height
            )
            
            # Additional info
            if enable_search and search_query and filtered_rows == 0:
                st.warning(f"No results found for '{search_query}'")
                if st.button("Clear search", key=f"{key_prefix}_clear_search"):
                    st.session_state[f"{key_prefix}_search"] = ""
                    st.rerun()
                    
        return page_data
    
    @staticmethod
    def render_simple(
        data: pd.DataFrame,
        title: str = "Data",
        key_prefix: str = "simple_data"
    ) -> pd.DataFrame:
        """Simplified version with minimal options.
        
        Args:
            data: DataFrame to display
            title: Title for the viewer
            key_prefix: Unique key prefix
            
        Returns:
            The displayed dataframe
        """
        return RawDataViewer.render(
            data=data,
            title=title,
            key_prefix=key_prefix,
            enable_column_selection=False,
            expandable=False,
            page_size=100
        )