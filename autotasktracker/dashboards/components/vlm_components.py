"""VLM monitor specific components."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import subprocess
import json

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None

from .base_component import StatelessComponent


class VLMCoverageGauge(StatelessComponent):
    """VLM coverage gauge visualization."""
    
    @staticmethod
    def render(coverage_pct: float, target: float = 33.3, height: int = 300):
        """Render VLM coverage gauge.
        
        Args:
            coverage_pct: Current coverage percentage
            target: Target coverage percentage
            height: Chart height
        """
        if not PLOTLY_AVAILABLE:
            st.info(f"📊 VLM Coverage: {coverage_pct:.1f}% (Target: {target}%)")
            return
            
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=coverage_pct,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "VLM Coverage %"},
            delta={'reference': target, 'relative': False},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 10], 'color': "lightgray"},
                    {'range': [10, 30], 'color': "gray"},
                    {'range': [30, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target
                }
            }
        ))
        fig.update_layout(height=height)
        st.plotly_chart(fig, use_container_width=True)


class VLMSystemStatus(StatelessComponent):
    """VLM system status display."""
    
    @staticmethod
    def render(
        ollama_status: Tuple[bool, bool, List[str]],
        watch_status: Tuple[bool, int],
        coverage_stats: Dict[str, Any],
        recent_rate: Optional[float] = None
    ):
        """Render system status.
        
        Args:
            ollama_status: (is_running, has_minicpm, model_list)
            watch_status: (is_running, worker_count)
            coverage_stats: Coverage statistics
            recent_rate: Recent processing rate
        """
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ollama_ok, minicpm_ok, models = ollama_status
            if ollama_ok and minicpm_ok:
                st.success("✅ Ollama + minicpm-v")
            elif ollama_ok:
                st.warning("⚠️ Ollama OK, minicpm-v missing")
            else:
                st.error("❌ Ollama not running")
        
        with col2:
            watch_ok, watch_count = watch_status
            if watch_ok:
                st.success(f"✅ Watch service ({watch_count} workers)")
            else:
                st.error("❌ Watch service not running")
        
        with col3:
            vlm_pct = coverage_stats.get('vlm_percentage', 0)
            if vlm_pct > 20:
                st.success(f"✅ Coverage: {vlm_pct:.1f}%")
            elif vlm_pct > 10:
                st.warning(f"⚠️ Coverage: {vlm_pct:.1f}%")
            else:
                st.error(f"❌ Coverage: {vlm_pct:.1f}%")
        
        with col4:
            if recent_rate is not None:
                if recent_rate > 20:
                    st.success(f"✅ Recent rate: {recent_rate:.0f}%")
                else:
                    st.warning(f"⚠️ Recent rate: {recent_rate:.0f}%")
            else:
                st.info("📊 No recent data")


class VLMProcessingTimeline(StatelessComponent):
    """VLM processing timeline visualization."""
    
    @staticmethod
    def render(rate_df: pd.DataFrame, title: str = "Real-time Processing (Last 2 Hours)"):
        """Render processing timeline.
        
        Args:
            rate_df: DataFrame with timestamp and type columns
            title: Chart title
        """
        if rate_df.empty:
            st.info("No processing data available")
            return
            
        if not PLOTLY_AVAILABLE:
            st.info("Processing timeline requires plotly installation")
            return
            
        # Convert to timeline visualization
        rate_df['timestamp'] = pd.to_datetime(rate_df['timestamp'])
        rate_df['minute'] = rate_df['timestamp'].dt.floor('T')
        
        # Count by minute and type
        timeline = rate_df.groupby(['minute', 'type']).size().reset_index(name='count')
        timeline_pivot = timeline.pivot(index='minute', columns='type', values='count').fillna(0)
        
        if 'screenshot' in timeline_pivot.columns and 'vlm' in timeline_pivot.columns:
            timeline_pivot['coverage_rate'] = (timeline_pivot['vlm'] / timeline_pivot['screenshot'] * 100)
            
            fig = go.Figure()
            
            # Screenshots bar
            fig.add_trace(go.Bar(
                x=timeline_pivot.index,
                y=timeline_pivot['screenshot'],
                name='Screenshots',
                marker_color='lightblue',
                yaxis='y'
            ))
            
            # VLM bar
            fig.add_trace(go.Bar(
                x=timeline_pivot.index,
                y=timeline_pivot['vlm'],
                name='VLM Processed',
                marker_color='darkblue',
                yaxis='y'
            ))
            
            # Coverage rate line
            fig.add_trace(go.Scatter(
                x=timeline_pivot.index,
                y=timeline_pivot['coverage_rate'],
                name='Coverage %',
                mode='lines+markers',
                marker_color='red',
                yaxis='y2'
            ))
            
            fig.update_layout(
                title=title,
                xaxis_title='Time',
                yaxis=dict(title='Count', side='left'),
                yaxis2=dict(title='Coverage %', side='right', overlaying='y', range=[0, 100]),
                hovermode='x unified',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)


class VLMRecentResults(StatelessComponent):
    """Display recent VLM processing results."""
    
    @staticmethod
    def render(recent_df: pd.DataFrame, max_results: int = 5):
        """Render recent VLM results.
        
        Args:
            recent_df: DataFrame with VLM results
            max_results: Maximum results to display
        """
        if recent_df.empty:
            st.info("No recent VLM results")
            return
            
        # Add quality indicators
        recent_df['quality'] = recent_df['description_length'].apply(
            lambda x: '🟢 High' if x > 1000 else '🟡 Medium' if x > 500 else '🔴 Low'
        )
        
        # Display recent results
        for idx, row in recent_df.head(max_results).iterrows():
            with st.expander(f"{row['created_at']} - {row['active_window'][:50]}..."):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**VLM Description** ({row['description_length']} chars):")
                    desc = row['vlm_description']
                    st.write(desc[:500] + "..." if len(desc) > 500 else desc)
                with col2:
                    st.write(f"**Quality**: {row['quality']}")
                    st.write(f"**ID**: {row['id']}")


class VLMHourlyChart(StatelessComponent):
    """VLM hourly processing chart."""
    
    @staticmethod
    def render(hourly_df: pd.DataFrame, title: str = "VLM Processing by Hour (Last 24h)"):
        """Render hourly processing chart.
        
        Args:
            hourly_df: DataFrame with hour and vlm_count columns
            title: Chart title
        """
        if hourly_df.empty:
            st.info("No VLM processing in last 24 hours")
            return
            
        if not PLOTLY_AVAILABLE:
            st.info("Hourly chart requires plotly installation")
            return
            
        hourly_df['hour'] = pd.to_datetime(hourly_df['hour'])
        
        fig = px.bar(
            hourly_df, 
            x='hour', 
            y='vlm_count',
            title=title,
            labels={'vlm_count': 'VLM Processed', 'hour': 'Hour'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


class VLMConfigDisplay(StatelessComponent):
    """Display VLM configuration settings."""
    
    @staticmethod
    def render(config_path: str):
        """Render VLM configuration.
        
        Args:
            config_path: Path to memos config file
        """
        import yaml
        
        try:
            with open(config_path, 'r') as f:
                memos_config = yaml.safe_load(f)
            
            watch_config = memos_config.get('watch', {})
            st.write("**Watch Settings:**")
            st.write(f"- Processing Interval: {watch_config.get('processing_interval', 'N/A')}")
            st.write(f"- Sparsity Factor: {watch_config.get('sparsity_factor', 'N/A')}")
            st.write(f"- Rate Window: {watch_config.get('rate_window_size', 'N/A')}")
            
            vlm_config = memos_config.get('vlm', {})
            st.write("\n**VLM Settings:**")
            st.write(f"- Enabled: {vlm_config.get('enabled', False)}")
            st.write(f"- Model: {vlm_config.get('modelname', 'N/A')}")
            st.write(f"- Endpoint: {vlm_config.get('endpoint', 'N/A')}")
        except Exception as e:
            st.error(f"Could not load config: {e}")