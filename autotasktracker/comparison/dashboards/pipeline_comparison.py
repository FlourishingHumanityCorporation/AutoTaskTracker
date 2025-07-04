"""
Clean pipeline comparison dashboard using the new organized structure.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PIL import Image
import json

from autotasktracker.core.database import DatabaseManager
from autotasktracker.comparison.pipelines import BasicPipeline, OCRPipeline, AIFullPipeline

# Page config
st.set_page_config(
    page_title="Pipeline Comparison - AutoTaskTracker",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚖️ AI Pipeline Comparison")
st.markdown("Compare different AI processing pipelines side-by-side")

@st.cache_data
def load_screenshot_data(limit=50):
    """Load screenshots with AI data for comparison."""
    db = DatabaseManager()
    
    query = """
    SELECT 
        e.id,
        e.filepath,
        e.filename,
        datetime(e.created_at, 'localtime') as created_at,
        me_ocr.value as ocr_text,
        me_window.value as active_window,
        me_vlm.value as vlm_description,
        CASE WHEN me_emb.value IS NOT NULL THEN 1 ELSE 0 END as has_embedding
    FROM entities e
    LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr."key" = 'ocr_result'
    LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id AND me_window."key" = 'active_window'
    LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm."key" = 'vlm_result'
    LEFT JOIN metadata_entries me_emb ON e.id = me_emb.entity_id AND me_emb."key" = 'embedding'
    WHERE e.file_type_group = 'image'
    AND me_window.value IS NOT NULL
    ORDER BY e.created_at DESC
    LIMIT ?
    """
    
    try:
        with db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[limit])
            return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def render_pipeline_interface(pipeline, screenshots_df, tab_name):
    """Render the interface for a specific pipeline."""
    
    # Pipeline info
    st.markdown(f"### 🔧 {pipeline.name}")
    st.markdown(f"*{pipeline.description}*")
    
    # Screenshot selector
    if len(screenshots_df) > 1:
        selected_idx = st.selectbox(
            "Select screenshot to analyze",
            range(len(screenshots_df)),
            format_func=lambda x: f"{screenshots_df.iloc[x]['filename']} - {screenshots_df.iloc[x]['created_at']}",
            key=f"screenshot_selector_{tab_name}"
        )
    else:
        selected_idx = 0
    
    if len(screenshots_df) == 0:
        st.warning("No screenshots available for analysis")
        return
    
    selected_screenshot = screenshots_df.iloc[selected_idx]
    
    # Display screenshot info
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"**File:** {selected_screenshot['filename']}")
        st.markdown(f"**Time:** {selected_screenshot['created_at']}")
        st.markdown(f"**Window:** {selected_screenshot['active_window'][:100]}...")
        
        # Data availability indicators
        indicators = []
        if pd.notna(selected_screenshot['ocr_text']):
            indicators.append("📝 OCR")
        if pd.notna(selected_screenshot['vlm_description']):
            indicators.append("👁️ VLM")
        if selected_screenshot['has_embedding']:
            indicators.append("🧠 Embedding")
        
        st.markdown(f"**Available Data:** {' | '.join(indicators) if indicators else 'Window title only'}")
    
    with col2:
        # Show screenshot thumbnail
        if selected_screenshot['filepath'] and os.path.exists(selected_screenshot['filepath']):
            try:
                image = Image.open(selected_screenshot['filepath'])
                image.thumbnail((300, 200))
                st.image(image, caption="Screenshot", use_container_width=True)
            except Exception as e:
                st.error(f"Could not load image: {e}")
    
    st.divider()
    
    # Process with pipeline
    with st.spinner(f"Processing with {pipeline.name}..."):
        screenshot_data = {
            'active_window': selected_screenshot.get('active_window', ''),
            'ocr_text': selected_screenshot.get('ocr_text', ''),
            'vlm_description': selected_screenshot.get('vlm_description', ''),
            'id': selected_screenshot.get('id')
        }
        result = pipeline.process_screenshot(screenshot_data)
    
    # Display results
    st.subheader("📊 Analysis Results")
    
    # Main results in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Color code by confidence
        confidence = result['confidence']
        if confidence >= 0.8:
            confidence_color = "🟢"
        elif confidence >= 0.6:
            confidence_color = "🟡"
        else:
            confidence_color = "🔴"
        
        st.metric(
            label="Confidence Score",
            value=f"{confidence:.0%}",
            help="AI confidence in the task identification"
        )
        st.markdown(f"{confidence_color} Confidence Level")
    
    with col2:
        st.metric(
            label="Detected Task",
            value=result['task'][:30] + "..." if len(result['task']) > 30 else result['task'],
            help=f"Full task: {result['task']}"
        )
    
    with col3:
        st.metric(
            label="Category",
            value=result['category'],
            help="Activity category classification"
        )
    
    # Detailed breakdown
    st.subheader("🔍 Processing Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Features Used:**")
        for feature in result['features_used']:
            st.markdown(f"• {feature}")
    
    with col2:
        st.markdown("**Processing Details:**")
        for key, value in result['details'].items():
            if isinstance(value, dict):
                st.markdown(f"• **{key.replace('_', ' ').title()}:** {len(value)} items")
            else:
                st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")

def main():
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Controls")
        
        screenshot_limit = st.slider(
            "Screenshots to load",
            min_value=10,
            max_value=100,
            value=30,
            help="Number of recent screenshots to load"
        )
        
        st.markdown("---")
        st.markdown("### Pipeline Information")
        st.markdown("**🔤 Basic:** Pattern matching only")
        st.markdown("**📝 OCR:** Enhanced with text analysis")
        st.markdown("**🤖 AI Full:** Complete AI features")
        
        st.markdown("---")
        st.markdown("### Quick Tips")
        st.markdown("• Select the same screenshot in each tab")
        st.markdown("• Compare confidence scores")
        st.markdown("• Note feature differences")
        st.markdown("• Check processing details")
    
    # Load data
    with st.spinner("Loading screenshots..."):
        screenshots_df = load_screenshot_data(screenshot_limit)
    
    if screenshots_df.empty:
        st.warning("No screenshots found. Make sure Memos is running and capturing screenshots.")
        return
    
    st.success(f"Loaded {len(screenshots_df)} screenshots for comparison")
    
    # Create tabs for different pipelines
    tab1, tab2, tab3 = st.tabs(["🔤 Basic Pipeline", "📝 OCR Pipeline", "🤖 AI Full Pipeline"])
    
    # Initialize pipelines
    basic_pipeline = BasicPipeline()
    ocr_pipeline = OCRPipeline()
    ai_pipeline = AIFullPipeline()
    
    with tab1:
        render_pipeline_interface(basic_pipeline, screenshots_df, "basic")
    
    with tab2:
        render_pipeline_interface(ocr_pipeline, screenshots_df, "ocr")
    
    with tab3:
        render_pipeline_interface(ai_pipeline, screenshots_df, "ai")

if __name__ == "__main__":
    main()