"""
Pipeline Comparison Dashboard for AutoTaskTracker.
Three identical tabs using different AI processing pipelines for easy comparison.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
from PIL import Image
import json

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.core.categorizer import ActivityCategorizer
from autotasktracker.ai.enhanced_task_extractor import AIEnhancedTaskExtractor
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from autotasktracker.ai.vlm_integration import VLMTaskExtractor

# Page config
st.set_page_config(
    page_title="Pipeline Comparison - AutoTaskTracker",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚖️ AI Pipeline Comparison Dashboard")
st.markdown("Compare different AI processing pipelines side-by-side using identical interfaces")

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

class BasicPipeline:
    """Basic pattern matching pipeline."""
    
    def __init__(self):
        self.extractor = TaskExtractor()
        self.name = "Basic Pattern Matching"
        self.description = "Original method using window title patterns and keyword matching"
    
    def process_screenshot(self, screenshot_data):
        window_title = screenshot_data.get('active_window', '')
        ocr_text = screenshot_data.get('ocr_text', '')
        
        task = self.extractor.extract_task(window_title) if window_title else "Unknown Activity"
        category = ActivityCategorizer.categorize(window_title, ocr_text)
        
        return {
            'task': task,
            'category': category,
            'confidence': 0.5,
            'features_used': ['Window Title'],
            'details': {
                'method': 'Pattern matching on window title',
                'data_sources': ['Window title only'],
                'processing_time': 'Instant'
            }
        }

class OCRPipeline:
    """OCR-enhanced pipeline."""
    
    def __init__(self):
        self.extractor = TaskExtractor()
        self.ocr_enhancer = OCREnhancer()
        self.name = "OCR Enhanced"
        self.description = "Enhanced with OCR text analysis and confidence scoring"
    
    def process_screenshot(self, screenshot_data):
        window_title = screenshot_data.get('active_window', '')
        ocr_text = screenshot_data.get('ocr_text', '')
        
        basic_task = self.extractor.extract_task(window_title) if window_title else "Unknown Activity"
        category = ActivityCategorizer.categorize(window_title, ocr_text)
        
        if ocr_text:
            ocr_enhancement = self.ocr_enhancer.enhance_task_with_ocr(ocr_text, basic_task)
            task = ocr_enhancement.get('task', basic_task)
            confidence = ocr_enhancement.get('confidence', 0.5)
            ocr_quality = ocr_enhancement.get('ocr_quality', 'unknown')
            features_used = ['Window Title', 'OCR Text', 'Layout Analysis']
            
            details = {
                'method': 'OCR-enhanced analysis',
                'ocr_quality': ocr_quality,
                'text_regions': ocr_enhancement.get('text_regions', {}),
                'data_sources': ['Window title', 'OCR text', 'Layout analysis'],
                'processing_time': 'Fast (~100ms)'
            }
        else:
            task = basic_task
            confidence = 0.3
            features_used = ['Window Title']
            details = {
                'method': 'Fallback to basic (no OCR)',
                'ocr_quality': 'no_text',
                'data_sources': ['Window title only'],
                'processing_time': 'Instant'
            }
        
        return {
            'task': task,
            'category': category,
            'confidence': confidence,
            'features_used': features_used,
            'details': details
        }

class AIPipeline:
    """Full AI-enhanced pipeline."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.ai_extractor = AIEnhancedTaskExtractor(self.db_manager.db_path)
        self.vlm_extractor = VLMTaskExtractor()
        self.name = "Full AI Enhanced"
        self.description = "Complete AI pipeline with semantic similarity and VLM analysis"
    
    def process_screenshot(self, screenshot_data):
        window_title = screenshot_data.get('active_window', '')
        ocr_text = screenshot_data.get('ocr_text', '')
        vlm_description = screenshot_data.get('vlm_description', '')
        entity_id = screenshot_data.get('id')
        
        enhanced_result = self.ai_extractor.extract_enhanced_task(
            window_title=window_title,
            ocr_text=ocr_text,
            vlm_description=vlm_description,
            entity_id=entity_id
        )
        
        features_used = ['Window Title']
        data_sources = ['Window title']
        
        if ocr_text:
            features_used.extend(['OCR Analysis', 'Text Layout'])
            data_sources.extend(['OCR text', 'Layout analysis'])
        
        if vlm_description:
            features_used.extend(['VLM Description', 'Visual Context'])
            data_sources.extend(['Visual analysis', 'Scene understanding'])
        
        similar_tasks = enhanced_result.get('similar_tasks', [])
        if similar_tasks:
            features_used.append('Semantic Similarity')
            data_sources.append('Historical patterns')
        
        return {
            'task': enhanced_result['task'],
            'category': enhanced_result['category'],
            'confidence': enhanced_result['confidence'],
            'features_used': features_used,
            'details': {
                'method': 'Full AI enhancement',
                'similar_tasks_count': len(similar_tasks),
                'ai_features': enhanced_result.get('ai_features', {}),
                'data_sources': data_sources,
                'processing_time': 'Medium (~500ms)'
            }
        }

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
        result = pipeline.process_screenshot(selected_screenshot)
    
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
    
    # Raw data inspection
    with st.expander("🔬 Raw Data"):
        st.subheader("Window Title")
        st.text(selected_screenshot['active_window'] if selected_screenshot['active_window'] else "No window title")
        
        st.subheader("OCR Text")
        if pd.notna(selected_screenshot['ocr_text']):
            try:
                ocr_data = json.loads(selected_screenshot['ocr_text'])
                if isinstance(ocr_data, list):
                    st.write("OCR Results (first 10):")
                    for i, item in enumerate(ocr_data[:10]):
                        if isinstance(item, list) and len(item) >= 3:
                            text = item[1]
                            confidence = item[2] if len(item) > 2 else 0
                            st.write(f"{i+1}. {text} (confidence: {confidence:.2f})")
                else:
                    st.text(str(selected_screenshot['ocr_text'])[:500])
            except:
                st.text(str(selected_screenshot['ocr_text'])[:500] if selected_screenshot['ocr_text'] else "No OCR text")
        else:
            st.text("No OCR text available")
        
        st.subheader("VLM Description")
        if pd.notna(selected_screenshot['vlm_description']):
            st.text(selected_screenshot['vlm_description'])
        else:
            st.text("No VLM description available")

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
        st.markdown("### Pipeline Comparison")
        st.markdown("Each tab uses a different AI processing pipeline:")
        st.markdown("• **Basic:** Pattern matching only")
        st.markdown("• **OCR:** Enhanced with text analysis")
        st.markdown("• **AI Full:** Complete AI features")
        
        st.markdown("---")
        st.markdown("### Usage Tips")
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
    ai_pipeline = AIPipeline()
    
    with tab1:
        render_pipeline_interface(basic_pipeline, screenshots_df, "basic")
    
    with tab2:
        render_pipeline_interface(ocr_pipeline, screenshots_df, "ocr")
    
    with tab3:
        render_pipeline_interface(ai_pipeline, screenshots_df, "ai")

if __name__ == "__main__":
    main()