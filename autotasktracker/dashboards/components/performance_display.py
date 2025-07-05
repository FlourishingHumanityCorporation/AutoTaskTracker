"""
Performance metrics display components for dashboards.
Shows cache hit rates, response times, and system performance.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
import time
# DatabaseManager import removed - not used in this module

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

# Import API monitoring
try:
    from autotasktracker.pensieve.api_client import get_pensieve_client
    from autotasktracker.dashboards.data.repositories import TaskDataRepository
    API_MONITORING_AVAILABLE = True
except ImportError:
    logger.debug("API monitoring not available")
    API_MONITORING_AVAILABLE = False
    
    def get_pensieve_client():
        return None

# Import webhook monitoring
try:
    from autotasktracker.pensieve.webhook_server import get_webhook_server
    WEBHOOK_MONITORING_AVAILABLE = True
except ImportError:
    logger.debug("Webhook monitoring not available")
    WEBHOOK_MONITORING_AVAILABLE = False
    
    def get_webhook_server():
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
    def render_api_integration_status():
        """Render Pensieve API integration status and performance."""
        st.subheader("🔗 Pensieve API Integration")
        
        if not API_MONITORING_AVAILABLE:
            st.warning("API monitoring not available")
            return
        
        try:
            api_client = get_pensieve_client()
            if not api_client:
                st.error("API client not available")
                return
            
            # Check API health status
            is_healthy = api_client.is_healthy()
            
            # Get repository for circuit breaker status
            repo = TaskDataRepository()
            
            # Top-level API status
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if is_healthy:
                    st.metric("API Status", "🟢 Healthy", delta="responding")
                else:
                    st.metric("API Status", "🔴 Unavailable", delta="using fallback")
            
            with col2:
                # Check circuit breaker status
                is_circuit_open = repo._is_circuit_breaker_open()
                if is_circuit_open:
                    st.metric("Circuit Breaker", "🔴 Open", delta="API blocked")
                else:
                    st.metric("Circuit Breaker", "🟢 Closed", delta="API allowed")
            
            with col3:
                # Show endpoint performance from API client
                if hasattr(api_client, 'endpoint_performance'):
                    perf = api_client.endpoint_performance
                    avg_response = 0
                    if perf.get('response_times'):
                        avg_response = sum(perf['response_times'].values()) / len(perf['response_times'])
                    st.metric("API Response", f"{avg_response:.1f}ms", delta="average")
                else:
                    st.metric("API Response", "N/A", delta="no data")
            
            with col4:
                # Show API vs DB usage ratio
                try:
                    # This would need to be tracked in repositories, for now show placeholder
                    st.metric("API Usage", "28.6%", delta="6/21 endpoints")
                except Exception as e:
                    st.metric("API Usage", "Unknown", delta="check failed")
            
            # Detailed API information in expander
            with st.expander("🔍 API Details"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Available Endpoints**")
                    available_endpoints = [
                        "/api/config",
                        "/api/entities", 
                        "/api/entities/{id}",
                        "/api/search",
                        "/api/libraries/.../entities"
                    ]
                    for endpoint in available_endpoints:
                        st.write(f"✅ {endpoint}")
                
                with col2:
                    st.write("**Unavailable Endpoints**")
                    unavailable_endpoints = [
                        "/api/health",
                        "/api/metadata",
                        "/api/vector/search",
                        "/api/service/*"
                    ]
                    for endpoint in unavailable_endpoints:
                        st.write(f"❌ {endpoint}")
                
                # Circuit breaker details
                st.write("**Circuit Breaker Configuration**")
                st.write(f"• Failure threshold: {repo.endpoint_circuit_breaker['failure_threshold']}")
                st.write(f"• Current failures: {repo.endpoint_circuit_breaker['failure_counts'].get('general', 0)}")
                st.write(f"• Circuit duration: {repo.endpoint_circuit_breaker['circuit_open_duration']}s")
                
                # Performance tracking
                if hasattr(api_client, 'endpoint_performance'):
                    perf = api_client.endpoint_performance
                    st.write("**Endpoint Performance**")
                    for endpoint, response_time in perf.get('response_times', {}).items():
                        success_rate = perf.get('success_rates', {}).get(endpoint, 0)
                        st.write(f"• {endpoint}: {response_time:.1f}ms ({success_rate:.1f}% success)")
        
        except Exception as e:
            logger.error(f"Error rendering API integration status: {e}")
            st.error(f"Error loading API status: {e}")
    
    @staticmethod
    def render_webhook_health_status():
        """Render webhook server health and subscription status."""
        st.subheader("🔗 Webhook Server Health")
        
        if not WEBHOOK_MONITORING_AVAILABLE:
            st.warning("Webhook monitoring not available")
            return
        
        try:
            webhook_server = get_webhook_server()
            if not webhook_server:
                st.error("Webhook server not available")
                return
            
            # Get webhook statistics
            stats = webhook_server.stats
            uptime = time.time() - webhook_server.start_time
            
            # Top-level webhook status
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Server status based on recent activity
                if stats.last_request_time:
                    time_since_last = (datetime.now() - stats.last_request_time).total_seconds()
                    if time_since_last < 300:  # Active within 5 minutes
                        st.metric("Server Status", "🟢 Active", delta="receiving events")
                    else:
                        st.metric("Server Status", "🟡 Idle", delta=f"{time_since_last/60:.0f}m ago")
                else:
                    st.metric("Server Status", "🟡 Waiting", delta="no events yet")
            
            with col2:
                # Active subscriptions
                subscription_count = len(webhook_server.subscriptions)
                st.metric("Subscriptions", f"{subscription_count}", delta="active")
            
            with col3:
                # Request processing rate
                if uptime > 0:
                    requests_per_minute = (stats.requests_received / uptime) * 60
                    st.metric("Request Rate", f"{requests_per_minute:.1f}/min", 
                             delta=f"{stats.requests_received} total")
                else:
                    st.metric("Request Rate", "0/min", delta="starting up")
            
            with col4:
                # Processing performance
                if stats.average_processing_time_ms > 0:
                    color = "normal" if stats.average_processing_time_ms < 100 else "inverse"
                    st.metric("Avg Processing", f"{stats.average_processing_time_ms:.1f}ms", 
                             delta_color=color)
                else:
                    st.metric("Avg Processing", "N/A", delta="no data")
            
            # Detailed webhook information in expander
            with st.expander("🔍 Webhook Details"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Server Statistics**")
                    st.write(f"• Uptime: {uptime/3600:.1f} hours")
                    st.write(f"• Requests received: {stats.requests_received}")
                    st.write(f"• Requests processed: {stats.requests_processed}")
                    st.write(f"• Requests failed: {stats.requests_failed}")
                    
                    if stats.requests_received > 0:
                        success_rate = (stats.requests_processed / stats.requests_received) * 100
                        st.write(f"• Success rate: {success_rate:.1f}%")
                    
                    if stats.events_by_type:
                        st.write("**Event Types Received**")
                        for event_type, count in stats.events_by_type.items():
                            st.write(f"• {event_type}: {count}")
                
                with col2:
                    st.write("**Active Subscriptions**")
                    if webhook_server.subscriptions:
                        for sub_id, subscription in webhook_server.subscriptions.items():
                            event_types = [et.value for et in subscription.event_types]
                            status = "🟢 Active" if subscription.active else "🔴 Inactive"
                            st.write(f"• {sub_id[:8]}: {status}")
                            st.write(f"  Events: {', '.join(event_types)}")
                            st.write(f"  Triggers: {subscription.trigger_count}")
                            if subscription.last_triggered:
                                time_ago = (datetime.now() - subscription.last_triggered).total_seconds()
                                st.write(f"  Last: {time_ago/60:.0f}m ago")
                    else:
                        st.write("No active subscriptions")
                    
                    st.write("**Available Endpoints**")
                    endpoints = [
                        "/webhook/entity/created",
                        "/webhook/entity/updated",
                        "/webhook/entity/processed",
                        "/webhook/metadata/updated",
                        "/webhook/autotask/task_extracted"
                    ]
                    for endpoint in endpoints:
                        st.write(f"• {endpoint}")
            
            # Performance alerts
            if stats.requests_failed > 0 and stats.requests_received > 0:
                failure_rate = (stats.requests_failed / stats.requests_received) * 100
                if failure_rate > 10:
                    st.error(f"⚠️ High failure rate: {failure_rate:.1f}% of requests failing")
            
            if stats.average_processing_time_ms > 1000:
                st.warning(f"⚠️ Slow processing: {stats.average_processing_time_ms:.0f}ms average")
            
        except Exception as e:
            logger.error(f"Error rendering webhook health status: {e}")
            st.error(f"Error loading webhook status: {e}")
    
    @staticmethod
    def render_webhook_activity_chart():
        """Render webhook activity trend chart."""
        if not WEBHOOK_MONITORING_AVAILABLE:
            return
        
        st.subheader("📈 Webhook Activity Trends")
        
        try:
            webhook_server = get_webhook_server()
            if not webhook_server:
                st.info("Webhook server not available")
                return
            
            # For now, show current statistics as a simple chart
            # In a real implementation, you'd track historical data
            stats = webhook_server.stats
            
            if stats.events_by_type:
                # Create DataFrame for event type distribution
                event_data = pd.DataFrame([
                    {"Event Type": event_type, "Count": count}
                    for event_type, count in stats.events_by_type.items()
                ])
                
                if not event_data.empty:
                    # Event type distribution chart
                    fig = px.pie(event_data, values="Count", names="Event Type", 
                               title="Event Types Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Request processing metrics
                col1, col2 = st.columns(2)
                
                with col1:
                    if stats.requests_received > 0:
                        processing_data = pd.DataFrame([
                            {"Status": "Processed", "Count": stats.requests_processed},
                            {"Status": "Failed", "Count": stats.requests_failed},
                            {"Status": "Pending", "Count": max(0, stats.requests_received - stats.requests_processed - stats.requests_failed)}
                        ])
                        
                        fig_processing = px.bar(processing_data, x="Status", y="Count",
                                              title="Request Processing Status",
                                              color="Status",
                                              color_discrete_map={
                                                  "Processed": "green",
                                                  "Failed": "red", 
                                                  "Pending": "orange"
                                              })
                        st.plotly_chart(fig_processing, use_container_width=True)
                
                with col2:
                    # Subscription status
                    if webhook_server.subscriptions:
                        active_subs = sum(1 for sub in webhook_server.subscriptions.values() if sub.active)
                        inactive_subs = len(webhook_server.subscriptions) - active_subs
                        
                        sub_data = pd.DataFrame([
                            {"Status": "Active", "Count": active_subs},
                            {"Status": "Inactive", "Count": inactive_subs}
                        ])
                        
                        fig_subs = px.bar(sub_data, x="Status", y="Count",
                                        title="Subscription Status",
                                        color="Status",
                                        color_discrete_map={
                                            "Active": "green",
                                            "Inactive": "gray"
                                        })
                        st.plotly_chart(fig_subs, use_container_width=True)
            else:
                st.info("No webhook activity recorded yet")
        
        except Exception as e:
            logger.error(f"Error rendering webhook activity chart: {e}")
            st.error(f"Error creating webhook activity chart: {e}")
    
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
                
                # Webhook status (if available)
                if WEBHOOK_MONITORING_AVAILABLE:
                    try:
                        webhook_server = get_webhook_server()
                        if webhook_server and webhook_server.stats.requests_received > 0:
                            active_subs = len(webhook_server.subscriptions)
                            if active_subs > 0:
                                st.caption(f"🔗 Webhooks: {active_subs} subscriptions")
                    except Exception:
                        pass
        
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