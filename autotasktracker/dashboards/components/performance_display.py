"""
Performance metrics display components for dashboards.
Shows cache hit rates, response times, and system performance.
"""

import streamlit as st
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

# Heavy imports moved to function level for conditional loading

logger = logging.getLogger(__name__)

# Import performance monitoring (with fallback)
try:
    from autotasktracker.pensieve.performance_monitor import get_performance_monitor, get_performance_metrics
    PERFORMANCE_MONITORING_AVAILABLE = True
except ImportError:
    logger.debug("Performance monitoring not available")
    PERFORMANCE_MONITORING_AVAILABLE = False
    
    def get_performance_monitor():
        return None
    
    def get_performance_metrics():
        return None


class PerformanceMetricsDisplay:
    """Display component for performance metrics."""
    
    @staticmethod
    def render_cache_metrics(show_details: bool = False):
        """Render cache performance metrics.
        
        Args:
            show_details: Whether to show detailed breakdown
        """
        if not PERFORMANCE_MONITORING_AVAILABLE:
            st.info("📊 Performance monitoring not available")
            return
        
        monitor = get_performance_monitor()
        if not monitor:
            st.warning("Performance monitor not initialized")
            return
        
        st.subheader("🚀 Cache Performance")
        
        # Get cache metrics for different cache types
        cache_types = ["memory", "disk", "default"]
        cache_metrics = {}
        
        for cache_type in cache_types:
            metrics = monitor.get_cache_metrics(cache_type)
            if metrics["total_operations"] > 0:
                cache_metrics[cache_type] = metrics
        
        if not cache_metrics:
            st.info("No cache operations recorded yet")
            return
        
        # Display overall cache performance
        cols = st.columns(len(cache_metrics))
        
        for i, (cache_type, metrics) in enumerate(cache_metrics.items()):
            with cols[i]:
                hit_rate = metrics["hit_rate"]
                
                # Color code based on performance
                if hit_rate >= 80:
                    color = "normal"
                elif hit_rate >= 60:
                    color = "off"
                else:
                    color = "inverse"
                
                st.metric(
                    label=f"{cache_type.title()} Cache",
                    value=f"{hit_rate:.1f}%",
                    delta=f"{metrics['hits']} hits",
                    delta_color=color
                )
        
        # Show detailed breakdown if requested
        if show_details and cache_metrics:
            st.subheader("Cache Details")
            
            # Create DataFrame for detailed view
            details_data = []
            for cache_type, metrics in cache_metrics.items():
                details_data.append({
                    "Cache Type": cache_type.title(),
                    "Hit Rate": f"{metrics['hit_rate']:.1f}%",
                    "Hits": metrics['hits'],
                    "Misses": metrics['misses'],
                    "Total Operations": metrics['total_operations']
                })
            
            if details_data:
                import pandas as pd
                df = pd.DataFrame(details_data)
                st.dataframe(df, use_container_width=True)
    
    @staticmethod
    def render_response_time_metrics():
        """Render response time metrics."""
        if not PERFORMANCE_MONITORING_AVAILABLE:
            return
        
        monitor = get_performance_monitor()
        if not monitor:
            return
        
        st.subheader("⚡ Response Times")
        
        # Get response time metrics for different operations
        operations = [
            ("database_query_ms", "Database Queries"),
            ("search_duration_ms", "Search Operations"),
            ("response_time_ms", "General Response")
        ]
        
        has_data = False
        cols = st.columns(len(operations))
        
        for i, (metric_name, display_name) in enumerate(operations):
            metrics = monitor.get_response_time_metrics(metric_name)
            
            if metrics["avg"] > 0:
                has_data = True
                with cols[i]:
                    avg_time = metrics["avg"]
                    p95_time = metrics["p95"]
                    
                    # Color code based on performance
                    if avg_time < 100:  # < 100ms
                        delta_color = "normal"
                    elif avg_time < 500:  # < 500ms
                        delta_color = "off"
                    else:
                        delta_color = "inverse"
                    
                    st.metric(
                        label=display_name,
                        value=f"{avg_time:.1f}ms",
                        delta=f"P95: {p95_time:.1f}ms",
                        delta_color=delta_color
                    )
        
        if not has_data:
            st.info("No response time data available yet")
    
    @staticmethod
    def render_comprehensive_metrics():
        """Render comprehensive performance overview."""
        if not PERFORMANCE_MONITORING_AVAILABLE:
            st.warning("📊 Performance monitoring not available")
            return
        
        try:
            metrics = get_performance_metrics()
            if not metrics:
                st.info("No performance data available")
                return
            
            st.subheader("📊 System Performance Overview")
            
            # Top-level metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Cache Hit Rate",
                    f"{metrics.cache_hit_rate:.1f}%",
                    delta=f"{metrics.total_requests} requests"
                )
            
            with col2:
                st.metric(
                    "Avg Response",
                    f"{metrics.avg_response_time_ms:.1f}ms",
                    delta=f"P95: {metrics.p95_response_time_ms:.1f}ms"
                )
            
            with col3:
                st.metric(
                    "DB Queries",
                    f"{metrics.database_query_time_ms:.1f}ms",
                    delta="avg time"
                )
            
            with col4:
                if metrics.websocket_connections > 0:
                    st.metric(
                        "WebSocket",
                        f"{metrics.websocket_connections}",
                        delta="active connections"
                    )
                else:
                    st.metric(
                        "Errors/min",
                        f"{metrics.errors_per_minute:.1f}",
                        delta="error rate"
                    )
            
            # Additional metrics in expander
            with st.expander("📈 Detailed Metrics"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Response Time Percentiles**")
                    st.write(f"• Average: {metrics.avg_response_time_ms:.1f}ms")
                    st.write(f"• 95th percentile: {metrics.p95_response_time_ms:.1f}ms")
                    st.write(f"• 99th percentile: {metrics.p99_response_time_ms:.1f}ms")
                    
                    if metrics.search_response_time_ms > 0:
                        st.write(f"• Search avg: {metrics.search_response_time_ms:.1f}ms")
                
                with col2:
                    st.write("**System Resources**")
                    if metrics.memory_usage_mb > 0:
                        st.write(f"• Memory usage: {metrics.memory_usage_mb:.1f}MB")
                    st.write(f"• Error rate: {metrics.errors_per_minute:.2f}/min")
                    st.write(f"• WebSocket connections: {metrics.websocket_connections}")
                    
                    # Show last updated
                    last_updated = datetime.fromtimestamp(metrics.last_updated)
                    st.caption(f"Last updated: {last_updated.strftime('%H:%M:%S')}")
        
        except Exception as e:
            logger.error(f"Error rendering performance metrics: {e}")
            st.error(f"Error loading performance data: {e}")
    
    @staticmethod
    def render_performance_chart(hours: int = 1):
        """Render performance trend chart.
        
        Args:
            hours: Number of hours of history to show
        """
        if not PERFORMANCE_MONITORING_AVAILABLE:
            return
        
        monitor = get_performance_monitor()
        if not monitor:
            return
        
        st.subheader(f"📈 Performance Trends ({hours}h)")
        
        try:
            import plotly.graph_objects as go
            
            # Get historical data for key metrics
            metrics_to_show = [
                ("database_query_ms", "Database Query Time (ms)", "blue"),
                ("search_duration_ms", "Search Time (ms)", "green"),
                ("response_time_ms", "Response Time (ms)", "red")
            ]
            
            fig = go.Figure()
            has_data = False
            
            for metric_name, display_name, color in metrics_to_show:
                history = monitor.get_metric_history(metric_name, hours)
                
                if history:
                    has_data = True
                    timestamps, values = zip(*history)
                    # Convert timestamps to datetime
                    datetimes = [datetime.fromtimestamp(ts) for ts in timestamps]
                    
                    fig.add_trace(go.Scatter(
                        x=datetimes,
                        y=values,
                        mode='lines+markers',
                        name=display_name,
                        line=dict(color=color)
                    ))
            
            if has_data:
                fig.update_layout(
                    title="Performance Metrics Over Time",
                    xaxis_title="Time",
                    yaxis_title="Duration (ms)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No performance trend data available for the last {hours} hour(s)")
        
        except Exception as e:
            logger.error(f"Error rendering performance chart: {e}")
            st.error(f"Error creating performance chart: {e}")
    
    @staticmethod
    def render_cache_hit_rate_chart():
        """Render cache hit rate visualization."""
        if not PERFORMANCE_MONITORING_AVAILABLE:
            return
        
        monitor = get_performance_monitor()
        if not monitor:
            return
        
        # Get cache metrics for visualization
        cache_types = ["memory", "disk", "default"]
        chart_data = []
        
        for cache_type in cache_types:
            metrics = monitor.get_cache_metrics(cache_type)
            if metrics["total_operations"] > 0:
                chart_data.append({
                    "Cache Type": cache_type.title(),
                    "Hit Rate": metrics["hit_rate"],
                    "Hits": metrics["hits"],
                    "Misses": metrics["misses"]
                })
        
        if chart_data:
            import pandas as pd
            import plotly.express as px
            
            st.subheader("🎯 Cache Hit Rates")
            
            df = pd.DataFrame(chart_data)
            
            # Create bar chart
            fig = px.bar(
                df,
                x="Cache Type",
                y="Hit Rate",
                title="Cache Hit Rates by Type",
                color="Hit Rate",
                color_continuous_scale="RdYlGn",
                range_color=[0, 100]
            )
            
            fig.update_layout(
                yaxis_title="Hit Rate (%)",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show hits vs misses
            col1, col2 = st.columns(2)
            
            with col1:
                fig_hits = px.pie(
                    df,
                    values="Hits",
                    names="Cache Type",
                    title="Cache Hits Distribution"
                )
                st.plotly_chart(fig_hits, use_container_width=True)
            
            with col2:
                fig_misses = px.pie(
                    df,
                    values="Misses",
                    names="Cache Type",
                    title="Cache Misses Distribution"
                )
                st.plotly_chart(fig_misses, use_container_width=True)


def render_performance_sidebar():
    """Render performance metrics in sidebar."""
    if not PERFORMANCE_MONITORING_AVAILABLE:
        return
    
    with st.sidebar:
        st.subheader("📊 Performance")
        
        try:
            metrics = get_performance_metrics()
            if metrics:
                # Cache performance
                if metrics.cache_hit_rate > 0:
                    if metrics.cache_hit_rate >= 80:
                        st.success(f"🚀 Cache: {metrics.cache_hit_rate:.0f}%")
                    elif metrics.cache_hit_rate >= 60:
                        st.warning(f"⚡ Cache: {metrics.cache_hit_rate:.0f}%")
                    else:
                        st.error(f"🐌 Cache: {metrics.cache_hit_rate:.0f}%")
                
                # Response time
                if metrics.avg_response_time_ms > 0:
                    if metrics.avg_response_time_ms < 100:
                        st.caption(f"⚡ Response: {metrics.avg_response_time_ms:.0f}ms")
                    elif metrics.avg_response_time_ms < 500:
                        st.caption(f"🟡 Response: {metrics.avg_response_time_ms:.0f}ms")
                    else:
                        st.caption(f"🔴 Response: {metrics.avg_response_time_ms:.0f}ms")
                
                # WebSocket status
                if metrics.websocket_connections > 0:
                    st.caption(f"🔌 WebSocket: {metrics.websocket_connections} active")
        
        except Exception as e:
            logger.debug(f"Error showing sidebar performance: {e}")


def render_mini_performance_status():
    """Render compact performance status for dashboard headers."""
    if not PERFORMANCE_MONITORING_AVAILABLE:
        return
    
    try:
        metrics = get_performance_metrics()
        if metrics and (metrics.cache_hit_rate > 0 or metrics.avg_response_time_ms > 0):
            
            status_parts = []
            
            # Cache status
            if metrics.cache_hit_rate > 0:
                if metrics.cache_hit_rate >= 80:
                    status_parts.append(f"🚀 {metrics.cache_hit_rate:.0f}%")
                elif metrics.cache_hit_rate >= 60:
                    status_parts.append(f"⚡ {metrics.cache_hit_rate:.0f}%")
                else:
                    status_parts.append(f"🔴 {metrics.cache_hit_rate:.0f}%")
            
            # Response time status
            if metrics.avg_response_time_ms > 0:
                if metrics.avg_response_time_ms < 100:
                    status_parts.append(f"⚡ {metrics.avg_response_time_ms:.0f}ms")
                else:
                    status_parts.append(f"{metrics.avg_response_time_ms:.0f}ms")
            
            if status_parts:
                st.caption(" | ".join(status_parts))
    
    except Exception as e:
        logger.debug(f"Error showing mini performance status: {e}")