"""Refactored Real-time dashboard using component architecture."""

import streamlit as st
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
import asyncio

from autotasktracker.dashboards.base import BaseDashboard
from autotasktracker.dashboards.components import (
    RealtimeMetricsRow,
    LiveActivityFeed,
    SmartSearchInterface,
    SystemStatusDisplay,
    PerformanceMetricsDisplay,
    EventProcessorControl,
    NoDataMessage
)
from autotasktracker.pensieve.event_processor import get_event_processor, PensieveEvent
from autotasktracker.pensieve.advanced_search import get_advanced_search, SearchQuery
from autotasktracker.pensieve.vector_search import get_enhanced_vector_search, VectorSearchQuery
from autotasktracker.pensieve.postgresql_adapter import get_postgresql_adapter
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class RealTimeDashboard(BaseDashboard):
    """Refactored real-time dashboard with event-driven updates from Pensieve."""
    
    def __init__(self):
        super().__init__(
            title="Real-Time AutoTaskTracker", 
            icon="⚡", 
            port=get_config().NOTIFICATIONS_PORT
        )
        
        # Event processing
        self.event_processor = get_event_processor()
        self.advanced_search = get_advanced_search()
        self.enhanced_vector_search = get_enhanced_vector_search()
        self.pg_adapter = get_postgresql_adapter()
        self.health_monitor = get_health_monitor()
        
        # Setup event handlers
        self._setup_event_handlers()
        
    def init_session_state(self):
        """Initialize real-time dashboard session state."""
        super().init_session_state()
        
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
    
    def _show_entity_details(self, entity_id: str):
        """Show details for a specific entity."""
        st.info(f"Entity details for {entity_id} would be displayed here")
    
    def _handle_search(self, search_params: Dict[str, Any]):
        """Handle search execution."""
        backend_type = search_params['backend_type']
        
        with st.spinner(f"Searching with {backend_type.replace('_', ' ')}..."):
            try:
                # Use enhanced vector search if available
                if backend_type in ['pgvector', 'postgresql']:
                    search_obj = VectorSearchQuery(
                        text=search_params['query'],
                        use_semantic=search_params['use_semantic'],
                        use_keyword=search_params['use_keyword'],
                        similarity_threshold=search_params['similarity_threshold'],
                        max_results=search_params['max_results'],
                        search_radius=search_params['search_radius']
                    )
                    
                    # Run async search
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(self.enhanced_vector_search.search(search_obj))
                    loop.close()
                    search_type = "Enhanced Vector Search"
                else:
                    # Fallback to basic search
                    search_obj = SearchQuery(
                        text=search_params['query'],
                        use_semantic=search_params['use_semantic'],
                        use_keyword=search_params['use_keyword'],
                        min_relevance=search_params['similarity_threshold'],
                        limit=search_params['max_results']
                    )
                    results = self.advanced_search.search(search_obj)
                    search_type = "Advanced Search"
                
                # Display results
                st.success(f"Found {len(results)} results using {search_type}")
                
                for i, result in enumerate(results[:10]):
                    with st.expander(f"Result {i+1}: {result.entity.file_path.name}"):
                        st.write(f"**Score**: {result.score:.3f}")
                        st.write(f"**Created**: {result.entity.created_at}")
                        if hasattr(result, 'search_type'):
                            st.write(f"**Match Type**: {result.search_type}")
                        if result.entity.screenshot_path:
                            st.image(str(result.entity.screenshot_path), width=300)
                        
            except Exception as e:
                st.error(f"Search failed: {str(e)}")
    
    def render_sidebar(self):
        """Render sidebar controls."""
        with st.sidebar:
            st.header("⚡ Real-Time Controls")
            
            # Auto-refresh toggle
            auto_refresh = st.toggle("Auto Refresh", value=st.session_state.auto_refresh)
            st.session_state.auto_refresh = auto_refresh
            
            # Manual refresh button
            if st.button("🔄 Refresh Now"):
                st.rerun()
            
            # Event processor controls
            st.subheader("Event Processor")
            EventProcessorControl.render(
                processor_running=self.event_processor.running,
                start_callback=self.event_processor.start_processing,
                stop_callback=self.event_processor.stop_processing,
                restart_callback=lambda: (
                    self.event_processor.stop_processing(),
                    time.sleep(1),
                    self.event_processor.start_processing()
                )
            )
            
            # Session controls
            from .components.session_controls import SessionControlsComponent
            SessionControlsComponent.render_minimal(position="sidebar")
    
    def run(self):
        """Main dashboard execution."""
        # Check database connection
        if not self.ensure_connection():
            return
        
        # Header with real-time status
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.title("⚡ Real-Time AutoTaskTracker")
        
        with col2:
            # Event processor status
            if self.event_processor.running:
                st.success("🟢 Live")
            else:
                st.error("🔴 Offline")
        
        # Render sidebar
        self.render_sidebar()
        
        # Real-time metrics row
        event_stats = self.event_processor.get_statistics()
        health_status = self.health_monitor.get_health_summary()
        
        RealtimeMetricsRow.render(
            event_stats=event_stats,
            health_status=health_status,
            last_activity_time=st.session_state.last_activity_time,
            backend_type=self.pg_adapter.capabilities.performance_tier,
            recent_events=st.session_state.realtime_events
        )
        
        # Main content tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Live Activity", 
            "🔍 Smart Search", 
            "📈 Performance", 
            "⚙️ System Status"
        ])
        
        with tab1:
            st.subheader("📊 Live Activity Feed")
            LiveActivityFeed.render(
                events=st.session_state.realtime_events,
                auto_refresh=st.session_state.auto_refresh,
                poll_interval=self.event_processor.poll_interval,
                show_entity_callback=self._show_entity_details
            )
        
        with tab2:
            SmartSearchInterface.render(
                backend_capabilities=self.pg_adapter.capabilities.__dict__,
                search_callback=self._handle_search
            )
        
        with tab3:
            PerformanceMetricsDisplay.render(
                event_stats=event_stats,
                health_metrics=health_status.get('metrics', {}),
                time_window="1h"
            )
        
        with tab4:
            backend_info = {
                'type': self.pg_adapter.capabilities.backend_type,
                'performance_tier': self.pg_adapter.capabilities.performance_tier,
                'size_mb': self.db_manager.get_database_size() / (1024 * 1024)
            }
            
            SystemStatusDisplay.render(
                health_summary=health_status,
                event_processor_status={
                    'running': self.event_processor.running,
                    'queue_size': event_stats.get('queue_size', 0),
                    'avg_process_time': event_stats.get('avg_process_time', 0)
                },
                backend_info=backend_info
            )


def main():
    """Run the refactored real-time dashboard."""
    dashboard = RealTimeDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()