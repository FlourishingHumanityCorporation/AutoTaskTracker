"""
Refactored VLM Processing Monitor Dashboard using component architecture
Real-time monitoring of Vision Language Model processing
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import subprocess
import json
import logging

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components import (
    VLMCoverageGauge,
    VLMSystemStatus,
    VLMProcessingTimeline,
    VLMRecentResults,
    VLMHourlyChart,
    VLMConfigDisplay,
    MetricsRow
)
from autotasktracker.dashboards.components.common_sidebar import CommonSidebar, SidebarSection
from autotasktracker.dashboards.data.repositories import BaseRepository
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class VLMRepository(BaseRepository):
    """Repository for VLM-specific data access."""
    
    def get_vlm_stats(self):
        """Get comprehensive VLM processing statistics."""
        # Basic AI coverage stats
        stats = self.db_manager.get_ai_coverage_stats()
        
        # Get hourly VLM processing for last 24 hours
        hourly_query = """
        SELECT 
            strftime('%Y-%m-%d %H:00', datetime(e.created_at, 'localtime')) as hour,
            COUNT(*) as vlm_count
        FROM entities e
        JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
        WHERE e.created_at >= datetime('now', '-24 hours')
        GROUP BY hour
        ORDER BY hour
        """
        
        with self.db_manager.get_connection() as conn:
            hourly_df = pd.read_sql_query(hourly_query, conn)
        
        # Get recent VLM processing details
        recent_query = """
        SELECT 
            e.id,
            datetime(e.created_at, 'localtime') as created_at,
            me.value as vlm_description,
            me2.value as active_window,
            LENGTH(me.value) as description_length
        FROM entities e
        JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
        ORDER BY e.created_at DESC
        LIMIT 50
        """
        
        with self.db_manager.get_connection() as conn:
            recent_df = pd.read_sql_query(recent_query, conn)
        
        # Get processing rate over time
        rate_query = """
        SELECT 
            datetime(e.created_at, 'localtime') as timestamp,
            'vlm' as type
        FROM entities e
        JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
        WHERE e.created_at >= datetime('now', '-2 hours')
        UNION ALL
        SELECT 
            datetime(created_at, 'localtime') as timestamp,
            'screenshot' as type
        FROM entities
        WHERE file_type_group = 'image' AND created_at >= datetime('now', '-2 hours')
        ORDER BY timestamp
        """
        
        with self.db_manager.get_connection() as conn:
            rate_df = pd.read_sql_query(rate_query, conn)
        
        return stats, hourly_df, recent_df, rate_df


class VLMMonitorDashboard(BaseDashboard):
    """Refactored VLM processing monitor dashboard."""
    
    def __init__(self):
        super().__init__(
            title="VLM Processing Monitor",
            icon="👁️",
            port=get_config().DAILY_SUMMARY_PORT
        )
        self.vlm_repo = VLMRepository(self.db_manager)
        
    def check_ollama_status(self):
        """Check Ollama server status."""
        try:
            result = subprocess.run(
                ['curl', '-s', f'{get_config().get_ollama_url()}/api/tags'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                models = [m.get('name', '') for m in data.get('models', [])]
                minicpm_installed = any('minicpm-v' in m for m in models)
                return True, minicpm_installed, models
            return False, False, []
        except Exception:
            return False, False, []
    
    def check_memos_watch_status(self):
        """Check memos watch service status."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'memos watch'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                return True, len(pids)
            return False, 0
        except Exception:
            return False, 0
    
    def calculate_recent_rate(self, rate_df):
        """Calculate recent processing rate."""
        if rate_df.empty:
            return None
            
        recent_vlm = len(rate_df[rate_df['type'] == 'vlm'])
        recent_total = len(rate_df[rate_df['type'] == 'screenshot'])
        return (recent_vlm / recent_total * 100) if recent_total > 0 else 0
    
    def render_sidebar(self):
        """Render sidebar controls using common sidebar component."""
        # Define custom sections for VLM monitor
        def render_configuration():
            VLMConfigDisplay.render(str(get_config().MEMOS_CONFIG_PATH))
            return None
            
        def render_quick_actions():
            if st.button("🔧 Run VLM Optimizer"):
                st.info("Run in terminal: `python scripts/vlm_optimizer.py`")
            
            if st.button("📊 Check Logs"):
                log_path = get_config().memos_dir / "logs" / "watch.log"
                st.info(f"Run in terminal: `tail -f {log_path}`")
            
            if st.button("🔄 Restart Watch Service"):
                st.info("Run in terminal: `python scripts/vlm_optimizer.py --restart`")
            return None
            
        # Custom sections for VLM monitor
        custom_sections = [
            SidebarSection("⚙️ Configuration", render_configuration),
            SidebarSection("🚀 Quick Actions", render_quick_actions)
        ]
        
        # Render common sidebar with custom sections
        CommonSidebar.render(
            header_title="VLM Monitor",
            header_icon="🔬",
            db_manager=self.db_manager,
            enable_time_filter=False,
            enable_category_filter=False,
            enable_smart_defaults=False,
            custom_sections=custom_sections
        )
    
    def run(self):
        """Main dashboard execution."""
        # Check database connection
        if not self.ensure_connection():
            return
            
        # Header
        st.title("👁️ VLM Processing Monitor")
        st.write("Real-time monitoring of Vision Language Model processing")
        
        # Auto-refresh
        st.markdown(
            '<meta http-equiv="refresh" content="30">',
            unsafe_allow_html=True
        )
        
        # Render sidebar
        self.render_sidebar()
        
        # Get data
        stats, hourly_df, recent_df, rate_df = self.vlm_repo.get_vlm_stats()
        
        # System Status
        st.header("🔧 System Status")
        VLMSystemStatus.render(
            ollama_status=self.check_ollama_status(),
            watch_status=self.check_memos_watch_status(),
            coverage_stats=stats,
            recent_rate=self.calculate_recent_rate(rate_df)
        )
        
        # Coverage Metrics
        st.header("📊 Coverage Metrics")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Coverage gauge
            VLMCoverageGauge.render(stats['vlm_percentage'])
            
            # Key metrics using MetricsRow component
            metrics_data = {
                "Total Screenshots": f"{stats['total_screenshots']:,}",
                "VLM Processed": f"{stats['vlm_count']:,}",
                "OCR Coverage": f"{stats['ocr_percentage']:.1f}%"
            }
            for label, value in metrics_data.items():
                st.metric(label, value)
        
        with col2:
            # Hourly processing chart
            VLMHourlyChart.render(hourly_df)
        
        # Processing Timeline
        st.header("⏱️ Processing Timeline")
        VLMProcessingTimeline.render(rate_df)
        
        # Recent VLM Results
        st.header("🔍 Recent VLM Results")
        VLMRecentResults.render(recent_df)


def main():
    """Run the refactored VLM monitor dashboard."""
    dashboard = VLMMonitorDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()