"""
VLM Processing Monitor Dashboard
Real-time monitoring of Vision Language Model processing
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import subprocess
import json

from autotasktracker import DatabaseManager, AutoTaskSettings, get_config

# Initialize configuration
config = get_config()


def get_vlm_stats():
    """Get comprehensive VLM processing statistics."""
    db = DatabaseManager(use_pensieve_api=True)
    
    # Basic AI coverage stats
    stats = db.get_ai_coverage_stats()
    
    # Get hourly VLM processing for last 24 hours
    query = """
    SELECT 
        strftime('%Y-%m-%d %H:00', datetime(e.created_at, 'localtime')) as hour,
        COUNT(*) as vlm_count
    FROM entities e
    JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'minicpm_v_result'
    WHERE e.created_at >= datetime('now', '-24 hours')
    GROUP BY hour
    ORDER BY hour
    """
    
    with db.get_connection() as conn:
        hourly_df = pd.read_sql_query(query, conn)
    
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
    LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "active_window"
    ORDER BY e.created_at DESC
    LIMIT 50
    """
    
    with db.get_connection() as conn:
        recent_df = pd.read_sql_query(query, conn)
    
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
    
    with db.get_connection() as conn:
        rate_df = pd.read_sql_query(rate_query, conn)
    
    return stats, hourly_df, recent_df, rate_df


def check_ollama_status():
    """Check Ollama server status."""
    try:
        result = subprocess.run(
            ['curl', '-s', f'{config.get_ollama_url()}/api/tags'],
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


def check_memos_watch_status():
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


def create_coverage_gauge(coverage_pct):
    """Create a gauge chart for VLM coverage."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=coverage_pct,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "VLM Coverage %"},
        delta={'reference': 33.3, 'relative': False},  # Target is 33.3% (every 3rd)
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
                'value': 33.3
            }
        }
    ))
    fig.update_layout(height=300)
    return fig


def main():
    """Main dashboard function."""
    st.set_page_config(
        layout="wide",
        page_title="VLM Processing Monitor",
        page_icon="👁️"
    )
    
    st.title("👁️ VLM Processing Monitor")
    st.write("Real-time monitoring of Vision Language Model processing")
    
    # Auto-refresh
    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True
    )
    
    # Get data
    stats, hourly_df, recent_df, rate_df = get_vlm_stats()
    
    # System Status Row
    st.header("🔧 System Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ollama_ok, minicpm_ok, models = check_ollama_status()
        if ollama_ok and minicpm_ok:
            st.success("✅ Ollama + minicpm-v")
        elif ollama_ok:
            st.warning("⚠️ Ollama OK, minicpm-v missing")
        else:
            st.error("❌ Ollama not running")
    
    with col2:
        watch_ok, watch_count = check_memos_watch_status()
        if watch_ok:
            st.success(f"✅ Watch service ({watch_count} workers)")
        else:
            st.error("❌ Watch service not running")
    
    with col3:
        if stats['vlm_percentage'] > 20:
            st.success(f"✅ Coverage: {stats['vlm_percentage']:.1f}%")
        elif stats['vlm_percentage'] > 10:
            st.warning(f"⚠️ Coverage: {stats['vlm_percentage']:.1f}%")
        else:
            st.error(f"❌ Coverage: {stats['vlm_percentage']:.1f}%")
    
    with col4:
        # Recent processing rate
        if not rate_df.empty:
            recent_vlm = len(rate_df[rate_df['type'] == 'vlm'])
            recent_total = len(rate_df[rate_df['type'] == 'screenshot'])
            recent_rate = (recent_vlm / recent_total * 100) if recent_total > 0 else 0
            if recent_rate > 20:
                st.success(f"✅ Recent rate: {recent_rate:.0f}%")
            else:
                st.warning(f"⚠️ Recent rate: {recent_rate:.0f}%")
        else:
            st.info("📊 No recent data")
    
    # Coverage Metrics Row
    st.header("📊 Coverage Metrics")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Coverage gauge
        fig = create_coverage_gauge(stats['vlm_percentage'])
        st.plotly_chart(fig, use_container_width=True)
        
        # Key metrics
        st.metric("Total Screenshots", f"{stats['total_screenshots']:,}")
        st.metric("VLM Processed", f"{stats['vlm_count']:,}")
        st.metric("OCR Coverage", f"{stats['ocr_percentage']:.1f}%")
    
    with col2:
        # Hourly processing chart
        if not hourly_df.empty:
            hourly_df['hour'] = pd.to_datetime(hourly_df['hour'])
            
            fig = px.bar(
                hourly_df, 
                x='hour', 
                y='vlm_count',
                title='VLM Processing by Hour (Last 24h)',
                labels={'vlm_count': 'VLM Processed', 'hour': 'Hour'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No VLM processing in last 24 hours")
    
    # Processing Timeline
    st.header("⏱️ Processing Timeline")
    
    if not rate_df.empty:
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
                title='Real-time Processing (Last 2 Hours)',
                xaxis_title='Time',
                yaxis=dict(title='Count', side='left'),
                yaxis2=dict(title='Coverage %', side='right', overlaying='y', range=[0, 100]),
                hovermode='x unified',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent VLM Results
    st.header("🔍 Recent VLM Results")
    
    if not recent_df.empty:
        # Add quality indicators
        recent_df['quality'] = recent_df['description_length'].apply(
            lambda x: '🟢 High' if x > 1000 else '🟡 Medium' if x > 500 else '🔴 Low'
        )
        
        # Display recent results
        for idx, row in recent_df.head(5).iterrows():
            with st.expander(f"{row['created_at']} - {row['active_window'][:50]}..."):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**VLM Description** ({row['description_length']} chars):")
                    st.write(row['vlm_description'][:500] + "..." if len(row['vlm_description']) > 500 else row['vlm_description'])
                with col2:
                    st.write(f"**Quality**: {row['quality']}")
                    st.write(f"**ID**: {row['id']}")
    else:
        st.info("No recent VLM results")
    
    # Configuration Info
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Load current config
        import yaml
        try:
            with open(config.MEMOS_CONFIG_PATH, 'r') as f:
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
        
        st.divider()
        
        # Quick actions
        st.header("🚀 Quick Actions")
        
        if st.button("🔧 Run VLM Optimizer"):
            st.info("Run in terminal: `python scripts/vlm_optimizer.py`")
        
        if st.button("📊 Check Logs"):
            log_path = config.memos_dir / "logs" / "watch.log"
            st.info(f"Run in terminal: `tail -f {log_path}`")
        
        if st.button("🔄 Restart Watch Service"):
            st.info("Run in terminal: `python scripts/vlm_optimizer.py --restart`")


if __name__ == "__main__":
    main()