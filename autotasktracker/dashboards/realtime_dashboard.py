"""Real-time dashboard with Pensieve event-driven updates."""

import streamlit as st
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd

from autotasktracker.dashboards import BaseDashboard
from autotasktracker.pensieve.event_processor import get_event_processor, PensieveEvent
from autotasktracker.pensieve.advanced_search import get_advanced_search, SearchQuery
from autotasktracker.pensieve.vector_search import get_enhanced_vector_search, VectorSearchQuery
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class RealTimeDashboard(BaseDashboard):
    """Real-time dashboard with event-driven updates from Pensieve."""
    
    def __init__(self):
        super().__init__(title="Real-Time AutoTaskTracker", icon="⚡", port=get_config().NOTIFICATIONS_PORT)
        
        # Event processing
        self.event_processor = get_event_processor()
        self.advanced_search = get_advanced_search()
        self.enhanced_vector_search = get_enhanced_vector_search()
        self.pg_adapter = get_postgresql_adapter()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Dashboard state
        if 'realtime_events' not in st.session_state:
            st.session_state.realtime_events = []
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
        if 'last_activity_time' not in st.session_state:
            st.session_state.last_activity_time = datetime.now()
    
    def _setup_event_handlers(self):
        """Setup event handlers for real-time updates."""
        # Register handlers for different event types
        self.event_processor.register_event_handler('frame_added', self._handle_new_frame)
        self.event_processor.register_event_handler('frame_processed', self._handle_frame_processed)
        
        # Start event processing if not already running
        if not self.event_processor.running:
            self.event_processor.start_processing()
            logger.info("Started real-time event processing for dashboard")
    
    def _handle_new_frame(self, event: PensieveEvent):
        """Handle new frame events."""
        # Add to session state for display
        if len(st.session_state.realtime_events) > 50:
            st.session_state.realtime_events = st.session_state.realtime_events[-49:]
        
        st.session_state.realtime_events.append({
            'timestamp': event.timestamp,
            'type': 'New Screenshot',
            'entity_id': event.entity_id,
            'data': event.data
        })
        
        st.session_state.last_activity_time = datetime.now()
        
        # Trigger dashboard refresh if auto-refresh enabled
        if st.session_state.auto_refresh:
            st.rerun()
    
    def _handle_frame_processed(self, event: PensieveEvent):
        """Handle frame processed events."""
        st.session_state.realtime_events.append({
            'timestamp': event.timestamp,
            'type': 'Processing Complete',
            'entity_id': event.entity_id,
            'data': event.data
        })
        
        st.session_state.last_activity_time = datetime.now()
        
        if st.session_state.auto_refresh:
            st.rerun()
    
    def render(self):
        """Render the real-time dashboard."""
        # Header with real-time status
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            st.title("⚡ Real-Time AutoTaskTracker")
        
        with col2:
            # Auto-refresh toggle
            auto_refresh = st.toggle("Auto Refresh", value=st.session_state.auto_refresh)
            st.session_state.auto_refresh = auto_refresh
        
        with col3:
            # Manual refresh button
            if st.button("🔄 Refresh"):
                st.rerun()
        
        with col4:
            # Event processor status
            if self.event_processor.running:
                st.success("🟢 Live")
            else:
                st.error("🔴 Offline")
        
        # Real-time metrics row
        self._render_realtime_metrics()
        
        # Main content tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Live Activity", 
            "🔍 Smart Search", 
            "📈 Performance", 
            "⚙️ System Status"
        ])
        
        with tab1:
            self._render_live_activity()
        
        with tab2:
            self._render_smart_search()
        
        with tab3:
            self._render_performance_metrics()
        
        with tab4:
            self._render_system_status()
    
    def _render_realtime_metrics(self):
        """Render real-time metrics."""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Get current statistics
        event_stats = self.event_processor.get_statistics()
        health_status = get_health_monitor().get_health_summary()
        
        with col1:
            st.metric(
                "Events Processed",
                event_stats['events_processed'],
                delta=f"+{len(st.session_state.realtime_events)}"
            )
        
        with col2:
            response_time = health_status.get('metrics', {}).get('response_time_ms', 0)
            st.metric(
                "API Response",
                f"{response_time:.1f}ms",
                delta=f"{'✅' if response_time < 100 else '⚠️'}"
            )
        
        with col3:
            last_activity = st.session_state.last_activity_time
            seconds_ago = (datetime.now() - last_activity).total_seconds()
            st.metric(
                "Last Activity",
                f"{int(seconds_ago)}s ago",
                delta="🟢" if seconds_ago < 30 else "🟡"
            )
        
        with col4:
            # Database backend type
            backend_type = self.pg_adapter.capabilities.performance_tier
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
    
    def _render_live_activity(self):
        """Render live activity feed."""
        st.subheader("📊 Live Activity Feed")
        
        if not st.session_state.realtime_events:
            st.info("No recent activity. Events will appear here in real-time.")
            return
        
        # Show recent events
        events_df = pd.DataFrame(st.session_state.realtime_events)
        events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
        events_df = events_df.sort_values('timestamp', ascending=False)
        
        # Display events with nice formatting
        for _, event in events_df.head(10).iterrows():
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
                    if st.button(f"View {event['entity_id']}", key=f"view_{event['entity_id']}"):
                        # Show details about this entity
                        self._show_entity_details(event['entity_id'])
        
        # Auto-scroll to latest (if enabled)
        if st.session_state.auto_refresh and len(events_df) > 0:
            st.success(f"🔄 Auto-refreshing every {self.event_processor.poll_interval}s")
    
    def _render_smart_search(self):
        """Render enhanced smart search interface with PostgreSQL capabilities."""
        st.subheader("🔍 Enhanced Smart Search")
        
        # Show backend capabilities
        backend_type = self.pg_adapter.capabilities.performance_tier
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
        if self.pg_adapter.capabilities.pgvector_available:
            with st.expander("🔧 Advanced Vector Search Options"):
                col1, col2 = st.columns(2)
                with col1:
                    search_radius = st.slider("Search Radius", 0.1, 1.0, 0.3, 0.1,
                                            help="Neighborhood search radius")
                with col2:
                    enable_clustering = st.checkbox("Semantic Clustering", value=True,
                                                   help="Group similar results")
        else:
            search_radius = 0.3
            enable_clustering = False
        
        if search_query and st.button("🔍 Enhanced Search"):
            with st.spinner(f"Searching with {backend_type.replace('_', ' ')}..."):
                try:
                    # Use enhanced vector search if available
                    if self.pg_adapter.capabilities.performance_tier in ['pgvector', 'postgresql']:
                        search_obj = VectorSearchQuery(
                            text=search_query,
                            use_semantic=use_semantic,
                            use_keyword=use_keyword,
                            similarity_threshold=similarity_threshold,
                            max_results=max_results,
                            search_radius=search_radius
                        )
                        
                        # Streamlit doesn't support async, so run in thread
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        results = loop.run_until_complete(self.enhanced_vector_search.search(search_obj))
                        loop.close()
                        search_type = "Enhanced Vector Search"
                    else:
                        # Fallback to basic search
                        search_obj = SearchQuery(
                            text=search_query,
                            use_semantic=use_semantic,
                            use_keyword=use_keyword,
                            max_results=max_results
                        )
                        
                        results = self.advanced_search.search(search_obj)
                        search_type = "Basic Search"
                    
                    if results:
                        st.success(f"Found {len(results)} results using {search_type}")
                        
                        for result in results:
                            # Enhanced display for vector search results
                            if hasattr(result, 'vector_similarity_score'):
                                title_suffix = f"Vector: {result.vector_similarity_score:.2f} | Relevance: {result.relevance_score:.2f}"
                            else:
                                title_suffix = f"Relevance: {result.relevance_score:.2f}"
                            
                            with st.expander(
                                f"📸 {result.window_title[:50]} - {title_suffix}",
                                expanded=False
                            ):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.write(f"**Window:** {result.window_title}")
                                    if result.extracted_tasks:
                                        st.write(f"**Tasks:** {', '.join(result.extracted_tasks[:3])}")
                                    if result.activity_category:
                                        st.write(f"**Category:** {result.activity_category}")
                                    
                                    # Enhanced vector search info
                                    if hasattr(result, 'semantic_cluster') and result.semantic_cluster:
                                        st.write(f"**Semantic Cluster:** {result.semantic_cluster}")
                                    if hasattr(result, 'similar_activities') and result.similar_activities:
                                        st.write(f"**Similar Activities:** {', '.join(result.similar_activities)}")
                                    
                                    if result.highlights:
                                        st.write("**Highlights:**")
                                        for highlight in result.highlights:
                                            st.write(f"- {highlight}")
                                
                                with col2:
                                    st.metric("Relevance", f"{result.relevance_score:.2%}")
                                    
                                    # Enhanced metrics for vector search
                                    if hasattr(result, 'vector_similarity_score'):
                                        st.metric("Vector Similarity", f"{result.vector_similarity_score:.2%}")
                                        
                                        # Embedding quality indicator
                                        if hasattr(result, 'embedding_quality'):
                                            quality_colors = {"high": "🟢", "medium": "🟡", "low": "🔴", "unknown": "⚪"}
                                            quality_color = quality_colors.get(result.embedding_quality, "⚪")
                                            st.caption(f"Embedding: {quality_color} {result.embedding_quality}")
                                    
                                    st.caption(f"Method: {result.search_method}")
                                    st.caption(f"Time: {result.timestamp.strftime('%Y-%m-%d %H:%M')}")
                        
                        # Show search performance info
                        if self.pg_adapter.capabilities.performance_tier == 'pgvector':
                            st.info("🐘 **pgvector optimization** - Native vector similarity search used")
                        elif self.pg_adapter.capabilities.performance_tier == 'postgresql':
                            st.info("🗄️ **PostgreSQL optimization** - Enhanced database performance")
                    else:
                        st.warning("No results found. Try a different search term or lower the similarity threshold.")
                
                except Exception as e:
                    st.error(f"Search failed: {e}")
    
    def _render_performance_metrics(self):
        """Render enhanced performance metrics with PostgreSQL info."""
        st.subheader("📈 Performance Metrics")
        
        # Database backend information
        st.write("**Database Backend Capabilities**")
        backend_info = {
            'Backend Type': self.pg_adapter.capabilities.performance_tier,
            'PostgreSQL Enabled': self.pg_adapter.capabilities.postgresql_enabled,
            'pgvector Available': self.pg_adapter.capabilities.pgvector_available,
            'Vector Dimensions': self.pg_adapter.capabilities.vector_dimensions,
            'Max Vectors Supported': f"{self.pg_adapter.capabilities.max_vectors:,}",
            'Scale Estimate': self.pg_adapter._get_scale_estimate()
        }
        st.json(backend_info)
        
        # Performance comparison
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Event Processing**")
            event_stats = self.event_processor.get_statistics()
            metrics_data = {
                'Events Processed': event_stats['events_processed'],
                'Events Failed': event_stats['events_failed'],
                'Last Processed ID': event_stats['last_processed_id'],
                'Poll Interval': f"{event_stats['poll_interval']}s"
            }
            st.json(metrics_data)
        
        with col2:
            st.write("**Search Performance**")
            if st.button("🔬 Run Search Benchmark"):
                with st.spinner("Running search performance test..."):
                    try:
                        # Run async search performance test
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        search_metrics = loop.run_until_complete(
                            self.enhanced_vector_search.get_search_performance_metrics()
                        )
                        loop.close()
                        st.json(search_metrics)
                    except Exception as e:
                        st.error(f"Benchmark failed: {e}")
            else:
                # Show cached search stats
                search_stats = self.advanced_search.get_search_statistics()
                st.json(search_stats)
        
        with col3:
            st.write("**Database Performance**")
            if st.button("🗄️ Run DB Benchmark"):
                with st.spinner("Running database performance test..."):
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        db_metrics = loop.run_until_complete(
                            self.pg_adapter.get_performance_metrics()
                        )
                        loop.close()
                        st.json(db_metrics)
                    except Exception as e:
                        st.error(f"DB benchmark failed: {e}")
        
        # Migration recommendations
        st.write("**Migration Recommendations**")
        recommendations = self.pg_adapter.get_migration_recommendations()
        
        if recommendations['recommendations']:
            for rec in recommendations['recommendations']:
                priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                priority_emoji = priority_color.get(rec['priority'], "⚪")
                
                with st.expander(f"{priority_emoji} {rec['action']} ({rec['priority']} priority)"):
                    st.write(f"**Benefit:** {rec['benefit']}")
                    if rec['command'] != 'N/A':
                        st.code(rec['command'], language='bash')
        else:
            st.success("✅ Database configuration is optimal")
        
        # Health monitoring details
        health_status = get_health_monitor().get_health_summary()
        
        st.write("**System Health**")
        st.json(health_status)
    
    def _render_system_status(self):
        """Render system status and controls."""
        st.subheader("⚙️ System Status & Controls")
        
        # Event processor controls
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Event Processing**")
            
            if self.event_processor.running:
                st.success("✅ Event processor is running")
                if st.button("🛑 Stop Event Processing"):
                    self.event_processor.stop_processing()
                    st.rerun()
            else:
                st.warning("⚠️ Event processor is stopped")
                if st.button("▶️ Start Event Processing"):
                    self.event_processor.start_processing()
                    st.rerun()
        
        with col2:
            st.write("**Dashboard Settings**")
            
            # Polling interval adjustment
            new_interval = st.number_input(
                "Poll Interval (seconds)",
                min_value=0.5,
                max_value=10.0,
                value=self.event_processor.poll_interval,
                step=0.5
            )
            
            if new_interval != self.event_processor.poll_interval:
                self.event_processor.poll_interval = new_interval
                st.success(f"Updated poll interval to {new_interval}s")
        
        # Clear events button
        if st.button("🗑️ Clear Event History"):
            st.session_state.realtime_events = []
            st.success("Event history cleared")
            st.rerun()
    
    def _show_entity_details(self, entity_id: int):
        """Show details for a specific entity."""
        try:
            # Get entity details via Pensieve API
            client = self.pensieve_client
            if client and client.is_healthy():
                frame = client.get_frame(entity_id)
                if frame:
                    metadata = client.get_metadata(entity_id)
                    ocr_text = client.get_ocr_result(entity_id)
                    
                    st.write(f"**Entity {entity_id} Details:**")
                    st.write(f"- **File:** {frame.filepath}")
                    st.write(f"- **Timestamp:** {frame.timestamp}")
                    st.write(f"- **Window Title:** {metadata.get('active_window', 'N/A')}")
                    if ocr_text:
                        st.write(f"- **OCR Text:** {ocr_text[:200]}...")
                    
                    tasks = metadata.get('extracted_tasks', {}).get("tasks", [])
                    if tasks:
                        st.write(f"- **Tasks:** {', '.join(tasks)}")
        
        except Exception as e:
            st.error(f"Failed to load entity details: {e}")


def main():
    """Main entry point for real-time dashboard."""
    dashboard = RealTimeDashboard()
    dashboard.render()


if __name__ == "__main__":
    main()