"""Dashboard templates for rapid development using the refactored architecture."""

from typing import Dict, List, Any
import streamlit as st
from datetime import datetime
import logging

from .base import BaseDashboard
from .components import (
    TimeFilterComponent,
    CategoryFilterComponent, 
    MetricsRow,
    CategoryPieChart,
    HourlyActivityChart,
    NoDataMessage,
    DataTable
)
from .components.common_sidebar import CommonSidebar, SidebarSection
from .data import TaskRepository, MetricsRepository
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class DashboardTemplate:
    """Base template for creating new dashboards quickly."""
    
    @staticmethod
    def create_simple_dashboard(
        title: str,
        icon: str,
        port: int,
        metrics_config: Dict[str, Any] = None,
        charts_config: List[str] = None,
        custom_features: List[str] = None
    ):
        """Create a simple dashboard from configuration.
        
        Args:
            title: Dashboard title
            icon: Dashboard icon
            port: Port number
            metrics_config: Configuration for metrics display
            charts_config: List of charts to include
            custom_features: List of custom features to enable
        """
        
        class GeneratedDashboard(BaseDashboard):
            def __init__(self):
                super().__init__(title, icon, port)
                self.metrics_config = metrics_config or {}
                self.charts_config = charts_config or []
                self.custom_features = custom_features or []
                
            def render_sidebar(self):
                """Render sidebar controls using common sidebar component."""
                # Define custom sections based on configuration
                custom_sections = []
                
                # Chart options section if configured
                if self.charts_config:
                    def render_chart_options():
                        chart_options = {}
                        for chart in self.charts_config:
                            chart_options[chart] = st.checkbox(
                                chart.replace('_', ' ').title(),
                                value=True,
                                key=f"show_{chart}"
                            )
                        return {'chart_options': chart_options}
                    custom_sections.append(SidebarSection("Charts", render_chart_options))
                
                # Custom features section if configured
                if self.custom_features:
                    # Filter out category_filter as it's handled by common sidebar
                    other_features = [f for f in self.custom_features if f != 'category_filter']
                    if other_features:
                        def render_feature_options():
                            feature_options = {}
                            for feature in other_features:
                                feature_options[feature] = st.checkbox(
                                    feature.replace('_', ' ').title(),
                                    key=f"enable_{feature}"
                                )
                            return {'feature_options': feature_options}
                        custom_sections.append(SidebarSection("Features", render_feature_options))
                
                # Render common sidebar with dynamic configuration
                results = CommonSidebar.render(
                    header_title=f"{title.split(' -')[0]} Settings",
                    header_icon=icon,
                    db_manager=self.db_manager,
                    enable_category_filter='category_filter' in self.custom_features,
                    custom_sections=custom_sections
                )
                
                # Extract results for backwards compatibility
                time_filter = results.get('time_filter')
                categories = results.get('categories')
                chart_options = results.get('chart_options', {}).get('chart_options', {})
                feature_options = results.get('feature_options', {}).get('feature_options', {})
                
                return time_filter, categories, chart_options, feature_options
                    
            def run(self):
                if not self.ensure_connection():
                    return
                    
                st.title(f"{icon} {title}")
                
                # Get settings
                time_filter, categories, chart_options, feature_options = self.render_sidebar()
                start_date, end_date = TimeFilterComponent.get_time_range(time_filter)
                
                # Initialize repositories
                task_repo = TaskRepository(self.db_manager)
                metrics_repo = MetricsRepository(self.db_manager)
                
                # Get data
                tasks = task_repo.get_tasks_for_period(start_date, end_date)
                summary = metrics_repo.get_metrics_summary(start_date, end_date)
                
                if not tasks:
                    NoDataMessage.render("No data available for the selected period")
                    return
                
                # Render metrics
                if self.metrics_config:
                    metrics = {}
                    if 'total_tasks' in self.metrics_config:
                        metrics["Total Tasks"] = len(tasks)
                    if 'total_duration' in self.metrics_config:
                        total_duration = sum(t.duration_minutes for t in tasks)
                        metrics["Total Duration"] = f"{total_duration:.0f} min"
                    if 'avg_duration' in self.metrics_config:
                        avg_duration = sum(t.duration_minutes for t in tasks) / len(tasks)
                        metrics["Avg Duration"] = f"{avg_duration:.1f} min"
                    if 'unique_windows' in self.metrics_config:
                        metrics["Unique Windows"] = summary['unique_windows']
                        
                    MetricsRow.render(metrics)
                
                # Render charts
                if chart_options.get('category_pie', False):
                    categories_data = {}
                    for task in tasks:
                        categories_data[task.category] = categories_data.get(task.category, 0) + 1
                    CategoryPieChart.render(categories_data, "Tasks by Category")
                
                if chart_options.get('hourly_activity', False):
                    hourly_data = {}
                    for task in tasks:
                        hour = task.timestamp.hour
                        hourly_data[hour] = hourly_data.get(hour, 0) + 1
                    HourlyActivityChart.render(hourly_data, "Activity by Hour")
                
                # Render data table if requested
                if feature_options.get('data_table', False):
                    st.subheader("📋 Task Details")
                    df_data = []
                    for task in tasks[:100]:  # Limit to 100 for performance
                        df_data.append({
                            'Window': task.window_title,
                            'Category': task.category,
                            'Duration (min)': f"{task.duration_minutes:.1f}",
                            'Time': task.timestamp.strftime('%H:%M')
                        })
                    
                    if df_data:
                        import pandas as pd
                        df = pd.DataFrame(df_data)
                        DataTable.render(df)
        
        return GeneratedDashboard


class DashboardTemplates:
    """Collection of pre-built dashboard templates."""
    
    @staticmethod
    def simple_overview():
        """Create a simple overview dashboard."""
        return DashboardTemplate.create_simple_dashboard(
            title="Overview Dashboard - AutoTaskTracker",
            icon="📊",
            port=get_config().OVERVIEW_PORT,
            metrics_config={
                'total_tasks': True,
                'total_duration': True,
                'avg_duration': True,
                'unique_windows': True
            },
            charts_config=['category_pie', 'hourly_activity'],
            custom_features=['category_filter', 'data_table']
        )
    
    @staticmethod
    def focus_tracker():
        """Create a focus tracking dashboard."""
        return DashboardTemplate.create_simple_dashboard(
            title="Focus Tracker - AutoTaskTracker",
            icon="🎯",
            port=get_config().FOCUS_TRACKER_PORT,
            metrics_config={
                'total_tasks': True,
                'total_duration': True,
                'avg_duration': True
            },
            charts_config=['hourly_activity'],
            custom_features=['category_filter']
        )
    
    @staticmethod
    def daily_summary():
        """Create a daily summary dashboard."""
        return DashboardTemplate.create_simple_dashboard(
            title="Daily Summary - AutoTaskTracker",
            icon="📅",
            port=get_config().DAILY_SUMMARY_PORT,
            metrics_config={
                'total_tasks': True,
                'total_duration': True,
                'unique_windows': True
            },
            charts_config=['category_pie'],
            custom_features=['data_table']
        )


class CustomDashboardBuilder:
    """Interactive dashboard builder for creating custom dashboards."""
    
    def __init__(self):
        self.config = {}
        
    def configure_basics(self):
        """Configure basic dashboard settings."""
        st.header("🏗️ Dashboard Builder")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Dashboard Title", value="My Custom Dashboard")
            icon = st.selectbox("Icon", ["📊", "📈", "📋", "🎯", "⚡", "🔍", "💡", "🚀"])
            
        with col2:
            port = st.number_input("Port Number", min_value=8500, max_value=8600, value=8511)
            
        return title, icon, port
        
    def configure_metrics(self):
        """Configure metrics to display."""
        st.subheader("📊 Metrics Configuration")
        
        metrics_config = {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            metrics_config['total_tasks'] = st.checkbox("Total Tasks", value=True)
            metrics_config['total_duration'] = st.checkbox("Total Duration", value=True)
            
        with col2:
            metrics_config['avg_duration'] = st.checkbox("Average Duration", value=True)
            metrics_config['unique_windows'] = st.checkbox("Unique Windows", value=True)
            
        return {k: v for k, v in metrics_config.items() if v}
        
    def configure_charts(self):
        """Configure charts to include."""
        st.subheader("📈 Charts Configuration")
        
        charts_config = []
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.checkbox("Category Pie Chart", value=True):
                charts_config.append('category_pie')
                
        with col2:
            if st.checkbox("Hourly Activity Chart", value=True):
                charts_config.append('hourly_activity')
                
        return charts_config
        
    def configure_features(self):
        """Configure additional features."""
        st.subheader("⚙️ Features Configuration")
        
        features = []
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.checkbox("Category Filter", value=True):
                features.append('category_filter')
                
        with col2:
            if st.checkbox("Data Table", value=False):
                features.append('data_table')
                
        return features
        
    def generate_code(self, title, icon, port, metrics_config, charts_config, custom_features):
        """Generate Python code for the custom dashboard."""
        code = f'''"""Custom dashboard generated by AutoTaskTracker Dashboard Builder."""

from autotasktracker.dashboards.templates import DashboardTemplate

def main():
    """Run the custom dashboard."""
    DashboardClass = DashboardTemplate.create_simple_dashboard(
        title="{title}",
        icon="{icon}",
        port={port},
        metrics_config={metrics_config},
        charts_config={charts_config},
        custom_features={custom_features}
    )
    
    dashboard = DashboardClass()
    dashboard.run()

if __name__ == "__main__":
    main()
'''
        return code
        
    def build_dashboard(self):
        """Interactive dashboard builder interface."""
        st.title("🏗️ Custom Dashboard Builder")
        st.markdown("Build your own dashboard using the refactored architecture components!")
        
        # Configuration steps
        title, icon, port = self.configure_basics()
        
        st.divider()
        
        metrics_config = self.configure_metrics()
        
        st.divider()
        
        charts_config = self.configure_charts()
        
        st.divider()
        
        custom_features = self.configure_features()
        
        st.divider()
        
        # Preview and generation
        st.subheader("🔍 Preview Configuration")
        
        config_preview = {
            "Title": title,
            "Icon": icon,
            "Port": port,
            "Metrics": list(metrics_config.keys()),
            "Charts": charts_config,
            "Features": custom_features
        }
        
        st.json(config_preview)
        
        # Generate code
        if st.button("🚀 Generate Dashboard Code"):
            code = self.generate_code(title, icon, port, metrics_config, charts_config, custom_features)
            
            st.subheader("📝 Generated Code")
            st.code(code, language='python')
            
            # Create download button
            st.download_button(
                label="📥 Download Dashboard Code",
                data=code,
                file_name=f"{title.lower().replace(' ', '_')}_dashboard.py",
                mime="text/plain"
            )
        
        # Live preview
        if st.button("👀 Preview Dashboard"):
            try:
                DashboardClass = DashboardTemplate.create_simple_dashboard(
                    title=title,
                    icon=icon,
                    port=port,
                    metrics_config=metrics_config,
                    charts_config=charts_config,
                    custom_features=custom_features
                )
                
                st.success(f"✅ Dashboard created successfully! Run on port {port}")
                st.info(f"To run: streamlit run your_dashboard.py --server.port {port}")
                
            except Exception as e:
                st.error(f"❌ Error creating dashboard: {e}")


def demo_templates():
    """Demonstrate the template system."""
    st.title("📋 Dashboard Templates Demo")
    
    st.markdown("""
    The refactored architecture makes it incredibly easy to create new dashboards!
    Choose a template below to see how quickly you can build functionality:
    """)
    
    template_choice = st.selectbox(
        "Select Template",
        ["Simple Overview", "Focus Tracker", "Daily Summary", "Custom Builder"]
    )
    
    if template_choice == "Simple Overview":
        st.subheader("📊 Simple Overview Template")
        st.markdown("""
        **Features included:**
        - Total tasks, duration, and window metrics
        - Category pie chart
        - Hourly activity chart
        - Category filtering
        - Data table view
        """)
        
        if st.button("🚀 Create Simple Overview Dashboard"):
            st.code("""
# Just one line to create a full dashboard!
dashboard_class = DashboardTemplates.simple_overview()
dashboard = dashboard_class()
dashboard.run()
            """)
            
    elif template_choice == "Focus Tracker":
        st.subheader("🎯 Focus Tracker Template")
        st.markdown("""
        **Features included:**
        - Focus-oriented metrics
        - Hourly activity patterns
        - Category filtering for deep work
        """)
        
    elif template_choice == "Daily Summary":
        st.subheader("📅 Daily Summary Template")
        st.markdown("""
        **Features included:**
        - Daily overview metrics
        - Category distribution
        - Detailed task table
        """)
        
    elif template_choice == "Custom Builder":
        st.subheader("🏗️ Custom Dashboard Builder")
        builder = CustomDashboardBuilder()
        builder.build_dashboard()


if __name__ == "__main__":
    demo_templates()