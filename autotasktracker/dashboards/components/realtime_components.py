"""Real-time dashboard specific components."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

from .base_component import StatelessComponent

logger = logging.getLogger(__name__)


class RealtimeMetricsRow(StatelessComponent):
    """Real-time metrics display row."""
    
    @staticmethod
    def render(
        event_stats: Dict[str, Any],
        health_status: Dict[str, Any],
        last_activity_time: datetime,
        backend_type: str,
        recent_events: List[Dict[str, Any]]
    ):
        """Render real-time metrics row.
        
        Args:
            event_stats: Event processor statistics
            health_status: Health monitor status
            last_activity_time: Last activity timestamp
            backend_type: Database backend type
            recent_events: Recent events list
        """
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Events Processed",
                event_stats.get('events_processed', 0),
                delta=f"+{len(recent_events)}"
            )
        
        with col2:
            response_time = health_status.get('metrics', {}).get('response_time_ms', 0)
            st.metric(
                "API Response",
                f"{response_time:.1f}ms",
                delta=f"{'✅' if response_time < 100 else '⚠️'}"
            )
        
        with col3:
            seconds_ago = (datetime.now() - last_activity_time).total_seconds()
            st.metric(
                "Last Activity",
                f"{int(seconds_ago)}s ago",
                delta="🟢" if seconds_ago < 30 else "🟡"
            )
        
        with col4:
            backend_emoji = {"pgvector": "🐘", "postgresql": "🗄️", "sqlite": "📁"}
            st.metric(
                "Database Backend",
                backend_type.replace('_', ' ').title(),
                delta=backend_emoji.get(backend_type, "📁")
            )
        
        with col5:
            # Processing rate
            total_time = event_stats.get('total_time', 0.001)
            events_processed = event_stats.get('events_processed', 0)
            rate = events_processed / total_time if total_time > 0 else 0
            st.metric(
                "Processing Rate",
                f"{rate:.1f}/s",
                delta="⚡"
            )


class LiveActivityFeed(StatelessComponent):
    """Live activity feed display."""
    
    @staticmethod
    def render(
        events: List[Dict[str, Any]], 
        auto_refresh: bool = False,
        poll_interval: int = 5,
        show_entity_callback: Optional[callable] = None
    ):
        """Render live activity feed.
        
        Args:
            events: List of event dictionaries
            auto_refresh: Whether auto-refresh is enabled
            poll_interval: Poll interval in seconds
            show_entity_callback: Callback for viewing entity details
        """
        if not events:
            st.info("No recent activity. Events will appear here in real-time.")
            return
        
        # Convert to DataFrame for easier handling
        events_df = pd.DataFrame(events)
        events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
        events_df = events_df.sort_values('timestamp', ascending=False)
        
        # Display events with nice formatting
        for idx, event in events_df.head(10).iterrows():
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    st.caption(event['timestamp'].strftime('%H:%M:%S'))
                
                with col2:
                    if event['type'] == 'New Screenshot':
                        st.write(f"📸 {event['type']} - Entity {event['entity_id']}")
                    else:
                        st.write(f"⚡ {event['type']} - Entity {event['entity_id']}")
                
                with col3:
                    if show_entity_callback and st.button(
                        f"View", 
                        key=f"view_{event['entity_id']}_{idx}"
                    ):
                        show_entity_callback(event['entity_id'])
        
        # Auto-refresh indicator
        if auto_refresh and len(events_df) > 0:
            st.success(f"🔄 Auto-refreshing every {poll_interval}s")


class SmartSearchInterface(StatelessComponent):
    """Enhanced smart search interface."""
    
    @staticmethod
    def render(
        backend_capabilities: Dict[str, Any],
        search_callback: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Render smart search interface.
        
        Args:
            backend_capabilities: Backend capability info
            search_callback: Callback for executing search
            
        Returns:
            Search parameters if search button clicked
        """
        st.subheader("🔍 Enhanced Smart Search")
        
        # Show backend capabilities
        backend_type = backend_capabilities.get('performance_tier', 'sqlite')
        if backend_type == 'pgvector':
            st.info("🐘 **pgvector enabled** - Advanced semantic search with vector similarity")
        elif backend_type == 'postgresql':
            st.info("🗄️ **PostgreSQL enabled** - Enhanced performance for large datasets")
        else:
            st.info("📁 **SQLite mode** - Basic search capabilities")
        
        # Search input
        search_query = st.text_input(
            "Search screenshots, tasks, and activities",
            placeholder="e.g., 'Python coding', 'email', 'meeting notes'"
        )
        
        # Search options
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            use_semantic = st.checkbox("Semantic Search", value=True, 
                                     help="AI-powered semantic similarity")
        with col2:
            use_keyword = st.checkbox("Keyword Search", value=True,
                                    help="Traditional keyword matching")
        with col3:
            similarity_threshold = st.slider("Similarity", 0.1, 1.0, 0.7, 0.1,
                                           help="Minimum similarity score")
        with col4:
            max_results = st.number_input("Max Results", min_value=5, max_value=100, value=20)
        
        # Advanced options for pgvector
        search_radius = 0.3
        enable_clustering = False
        
        if backend_capabilities.get('pgvector_available', False):
            with st.expander("🔧 Advanced Vector Search Options"):
                col1, col2 = st.columns(2)
                with col1:
                    search_radius = st.slider("Search Radius", 0.1, 1.0, 0.3, 0.1,
                                            help="Neighborhood search radius")
                with col2:
                    enable_clustering = st.checkbox("Semantic Clustering", value=True,
                                                   help="Group similar results")
        
        if search_query and st.button("🔍 Enhanced Search"):
            search_params = {
                'query': search_query,
                'use_semantic': use_semantic,
                'use_keyword': use_keyword,
                'similarity_threshold': similarity_threshold,
                'max_results': max_results,
                'search_radius': search_radius,
                'enable_clustering': enable_clustering,
                'backend_type': backend_type
            }
            
            if search_callback:
                search_callback(search_params)
            
            return search_params
        
        return None


class SystemStatusDisplay(StatelessComponent):
    """System status and health display."""
    
    @staticmethod
    def render(
        health_summary: Dict[str, Any],
        event_processor_status: Dict[str, Any],
        backend_info: Dict[str, Any]
    ):
        """Render system status display.
        
        Args:
            health_summary: Health monitor summary
            event_processor_status: Event processor status
            backend_info: Backend information
        """
        st.subheader("⚙️ System Status")
        
        # Overall health
        health_score = health_summary.get('health_score', 0)
        if health_score >= 90:
            st.success(f"✅ System Health: {health_score}%")
        elif health_score >= 70:
            st.warning(f"⚠️ System Health: {health_score}%")
        else:
            st.error(f"❌ System Health: {health_score}%")
        
        # Service status grid
        st.markdown("### Service Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Core Services**")
            services = health_summary.get('services', {})
            for service, status in services.items():
                icon = "🟢" if status == 'healthy' else "🔴"
                st.write(f"{icon} {service}: {status}")
        
        with col2:
            st.markdown("**Event Processing**")
            st.write(f"🔄 Running: {event_processor_status.get('running', False)}")
            st.write(f"📊 Queue Size: {event_processor_status.get('queue_size', 0)}")
            st.write(f"⏱️ Avg Process Time: {event_processor_status.get('avg_process_time', 0):.2f}s")
        
        with col3:
            st.markdown("**Database Backend**")
            st.write(f"🗄️ Type: {backend_info.get('type', 'Unknown')}")
            st.write(f"💾 Size: {backend_info.get('size_mb', 0):.1f} MB")
            st.write(f"📈 Performance Tier: {backend_info.get('performance_tier', 'basic')}")


class PerformanceMetricsDisplay(StatelessComponent):
    """Performance metrics visualization."""
    
    @staticmethod
    def render(
        event_stats: Dict[str, Any],
        health_metrics: Dict[str, Any],
        time_window: str = "1h"
    ):
        """Render performance metrics.
        
        Args:
            event_stats: Event processing statistics
            health_metrics: Health monitoring metrics
            time_window: Time window for metrics
        """
        st.subheader("📈 Performance Metrics")
        
        # Key performance indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            throughput = event_stats.get('events_per_second', 0)
            st.metric("Throughput", f"{throughput:.2f} events/s")
        
        with col2:
            latency = health_metrics.get('avg_latency_ms', 0)
            st.metric("Avg Latency", f"{latency:.1f} ms")
        
        with col3:
            error_rate = event_stats.get('error_rate', 0) * 100
            st.metric("Error Rate", f"{error_rate:.1f}%")
        
        with col4:
            uptime_pct = health_metrics.get('uptime_percentage', 100)
            st.metric("Uptime", f"{uptime_pct:.1f}%")
        
        # Performance chart placeholder
        st.info(f"📊 Performance trends for last {time_window} would be displayed here")


class EventProcessorControl(StatelessComponent):
    """Event processor control panel."""
    
    @staticmethod
    def render(
        processor_running: bool,
        start_callback: Optional[callable] = None,
        stop_callback: Optional[callable] = None,
        restart_callback: Optional[callable] = None
    ):
        """Render event processor controls.
        
        Args:
            processor_running: Whether processor is running
            start_callback: Start processor callback
            stop_callback: Stop processor callback
            restart_callback: Restart processor callback
        """
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if processor_running:
                if st.button("⏸️ Stop Processor") and stop_callback:
                    stop_callback()
            else:
                if st.button("▶️ Start Processor") and start_callback:
                    start_callback()
        
        with col2:
            if st.button("🔄 Restart Processor") and restart_callback:
                restart_callback()
        
        with col3:
            status = "🟢 Running" if processor_running else "🔴 Stopped"
            st.write(f"Status: {status}")