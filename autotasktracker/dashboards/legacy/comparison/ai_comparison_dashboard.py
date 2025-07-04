"""
AI Processing Comparison Dashboard for AutoTaskTracker.
Compare different AI processing methods on the same screenshots.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
from PIL import Image
import json

# Import from our package structure

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.core.categorizer import ActivityCategorizer
from autotasktracker.ai.enhanced_task_extractor import AIEnhancedTaskExtractor
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from autotasktracker.ai.vlm_integration import VLMTaskExtractor

# Page config
st.set_page_config(
    page_title="AI Processing Comparison - AutoTaskTracker",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔬 AI Processing Comparison Dashboard")
st.markdown("Compare different AI processing methods on the same screenshots")

@st.cache_data
def load_screenshots_with_ai_data(limit=50):
    """Load screenshots that have multiple types of AI data."""
    db = DatabaseManager()
    
    # Get screenshots with both OCR and potential VLM data
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
    AND (me_ocr.value IS NOT NULL OR me_vlm.value IS NOT NULL)
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

def process_screenshot_comparison(screenshot_data):
    """Process a single screenshot with all different methods."""
    results = {}
    
    # Basic data
    window_title = screenshot_data.get('active_window', '')
    ocr_text = screenshot_data.get('ocr_text', '')
    vlm_description = screenshot_data.get('vlm_description', '')
    entity_id = screenshot_data.get('id')
    
    # 1. Basic Pattern Matching (Original)
    basic_extractor = TaskExtractor()
    basic_task = basic_extractor.extract_task(window_title) if window_title else "Unknown Activity"
    basic_category = ActivityCategorizer.categorize(window_title, ocr_text)
    
    results['basic'] = {
        'method': 'Basic Pattern Matching',
        'task': basic_task,
        'category': basic_category,
        'confidence': 0.5,  # Fixed confidence for basic method
        'features_used': ['Window Title'],
        'description': 'Uses window title patterns and keyword matching'
    }
    
    # 2. OCR Enhanced
    if ocr_text:
        ocr_enhancer = OCREnhancer()
        ocr_enhancement = ocr_enhancer.enhance_task_with_ocr(ocr_text, basic_task)
        
        results['ocr_enhanced'] = {
            'method': 'OCR Enhanced',
            'task': ocr_enhancement.get('task', basic_task),
            'category': basic_category,
            'confidence': ocr_enhancement.get('confidence', 0.5),
            'ocr_quality': ocr_enhancement.get('ocr_quality', 'unknown'),
            'features_used': ['Window Title', 'OCR Text', 'Layout Analysis'],
            'description': f"OCR Quality: {ocr_enhancement.get('ocr_quality', 'unknown')}, Text Regions: {ocr_enhancement.get('text_regions', {})}"
        }
    else:
        results['ocr_enhanced'] = {
            'method': 'OCR Enhanced',
            'task': basic_task,
            'category': basic_category,
            'confidence': 0.3,
            'ocr_quality': 'no_text',
            'features_used': ['Window Title'],
            'description': 'No OCR text available'
        }
    
    # 3. VLM Enhanced
    if vlm_description:
        vlm_extractor = VLMTaskExtractor()
        vlm_task = vlm_extractor.extract_from_vlm_description(vlm_description, window_title, ocr_text)
        
        if vlm_task:
            results['vlm_enhanced'] = {
                'method': 'VLM Enhanced',
                'task': vlm_task.task_title,
                'category': vlm_task.category,
                'confidence': vlm_task.confidence,
                'ui_state': vlm_task.ui_state,
                'visual_context': vlm_task.visual_context,
                'features_used': ['Window Title', 'Visual Analysis', 'Scene Understanding'],
                'description': f"UI State: {vlm_task.ui_state}, Visual: {vlm_task.visual_context}, Subtasks: {len(vlm_task.subtasks)}"
            }
        else:
            results['vlm_enhanced'] = {
                'method': 'VLM Enhanced',
                'task': 'VLM processing failed',
                'category': basic_category,
                'confidence': 0.0,
                'features_used': ['Window Title'],
                'description': 'VLM extraction failed'
            }
    else:
        results['vlm_enhanced'] = {
            'method': 'VLM Enhanced',
            'task': basic_task,
            'category': basic_category,
            'confidence': 0.3,
            'features_used': ['Window Title'],
            'description': 'No VLM description available'
        }
    
    # 4. Full AI Enhanced (All features combined)
    db_manager = DatabaseManager()
    ai_extractor = AIEnhancedTaskExtractor(db_manager.db_path)
    
    enhanced_result = ai_extractor.extract_enhanced_task(
        window_title=window_title,
        ocr_text=ocr_text,
        vlm_description=vlm_description,
        entity_id=entity_id
    )
    
    features_used = ['Window Title']
    if ocr_text:
        features_used.append('OCR Analysis')
    if vlm_description:
        features_used.extend(['VLM Description', 'Visual Context'])
    if enhanced_result.get('similar_tasks'):
        features_used.append('Semantic Similarity')
    
    results['ai_full'] = {
        'method': 'Full AI Enhanced',
        'task': enhanced_result['task'],
        'category': enhanced_result['category'],
        'confidence': enhanced_result['confidence'],
        'ai_features': enhanced_result.get('ai_features', {}),
        'similar_tasks_count': len(enhanced_result.get('similar_tasks', [])),
        'features_used': features_used,
        'description': f"Uses all available AI features, {len(enhanced_result.get('similar_tasks', []))} similar tasks found"
    }
    
    return results

def display_comparison_table(results):
    """Display comparison results in a table format."""
    comparison_data = []
    
    for method_key, result in results.items():
        comparison_data.append({
            'Method': result['method'],
            'Task': result['task'],
            'Category': result['category'],
            'Confidence': f"{result['confidence']:.0%}",
            'Features Used': ', '.join(result['features_used']),
            'Notes': result['description']
        })
    
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def display_detailed_comparison(results):
    """Display detailed comparison in columns."""
    cols = st.columns(len(results))
    
    for i, (method_key, result) in enumerate(results.items()):
        with cols[i]:
            # Color code by confidence
            confidence = result['confidence']
            if confidence >= 0.8:
                confidence_color = "🟢"
            elif confidence >= 0.6:
                confidence_color = "🟡"
            else:
                confidence_color = "🔴"
            
            st.markdown(f"### {confidence_color} {result['method']}")
            st.markdown(f"**Task:** {result['task']}")
            st.markdown(f"**Category:** {result['category']}")
            st.markdown(f"**Confidence:** {result['confidence']:.0%}")
            
            with st.expander("Details"):
                st.markdown(f"**Features Used:**")
                for feature in result['features_used']:
                    st.markdown(f"• {feature}")
                st.markdown(f"**Description:** {result['description']}")
                
                # Method-specific details
                if 'ocr_quality' in result:
                    st.markdown(f"**OCR Quality:** {result['ocr_quality']}")
                
                if 'ui_state' in result and result['ui_state']:
                    st.markdown(f"**UI State:** {result['ui_state']}")
                
                if 'similar_tasks_count' in result:
                    st.markdown(f"**Similar Tasks:** {result['similar_tasks_count']}")

def main():
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Controls")
        
        screenshot_limit = st.slider(
            "Screenshots to analyze",
            min_value=10,
            max_value=100,
            value=20,
            help="Number of recent screenshots to load"
        )
        
        show_images = st.checkbox(
            "Show screenshot thumbnails",
            value=True,
            help="Display thumbnail images"
        )
        
        filter_method = st.selectbox(
            "Filter by data availability",
            ["All screenshots", "With OCR only", "With VLM only", "With both OCR and VLM"],
            help="Filter screenshots by available AI data"
        )
    
    # Load data
    with st.spinner("Loading screenshots..."):
        screenshots_df = load_screenshots_with_ai_data(screenshot_limit)
    
    if screenshots_df.empty:
        st.warning("No screenshots found with AI data. Make sure Memos is running and processing screenshots.")
        return
    
    # Apply filters
    filtered_df = screenshots_df.copy()
    
    if filter_method == "With OCR only":
        filtered_df = filtered_df[filtered_df['ocr_text'].notna() & filtered_df['vlm_description'].isna()]
    elif filter_method == "With VLM only":
        filtered_df = filtered_df[filtered_df['vlm_description'].notna() & filtered_df['ocr_text'].isna()]
    elif filter_method == "With both OCR and VLM":
        filtered_df = filtered_df[filtered_df['ocr_text'].notna() & filtered_df['vlm_description'].notna()]
    
    st.subheader(f"📊 Analysis Results ({len(filtered_df)} screenshots)")
    
    if filtered_df.empty:
        st.info(f"No screenshots match the filter '{filter_method}'. Try a different filter.")
        return
    
    # Screenshot selector
    if len(filtered_df) > 1:
        selected_idx = st.selectbox(
            "Select screenshot to analyze",
            range(len(filtered_df)),
            format_func=lambda x: f"{filtered_df.iloc[x]['filename']} - {filtered_df.iloc[x]['created_at']}"
        )
    else:
        selected_idx = 0
    
    selected_screenshot = filtered_df.iloc[selected_idx]
    
    # Display screenshot info
    col1, col2 = st.columns([2, 1])
    
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
        
        st.markdown(f"**Available Data:** {' | '.join(indicators)}")
    
    with col2:
        # Show screenshot thumbnail
        if show_images and selected_screenshot['filepath'] and os.path.exists(selected_screenshot['filepath']):
            try:
                image = Image.open(selected_screenshot['filepath'])
                image.thumbnail((300, 200))
                st.image(image, caption="Screenshot", use_column_width=True)
            except Exception as e:
                st.error(f"Could not load image: {e}")
    
    st.divider()
    
    # Process with different methods
    with st.spinner("Processing with different AI methods..."):
        comparison_results = process_screenshot_comparison(selected_screenshot)
    
    # Display results
    st.subheader("🔍 Method Comparison")
    
    # Summary table
    display_comparison_table(comparison_results)
    
    st.subheader("📋 Detailed Comparison")
    
    # Detailed comparison
    display_detailed_comparison(comparison_results)
    
    # Raw data inspection
    with st.expander("🔬 Raw Data Inspection"):
        st.subheader("OCR Text")
        if pd.notna(selected_screenshot['ocr_text']):
            try:
                ocr_data = json.loads(selected_screenshot['ocr_text'])
                if isinstance(ocr_data, list):
                    for i, item in enumerate(ocr_data[:10]):  # Show first 10 items
                        if isinstance(item, list) and len(item) >= 3:
                            text = item[1]
                            confidence = item[2] if len(item) > 2 else 0
                            st.write(f"{i+1}. {text} (confidence: {confidence:.2f})")
                else:
                    st.text(str(selected_screenshot['ocr_text'])[:1000])
            except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
                st.text(str(selected_screenshot['ocr_text'])[:1000] if selected_screenshot['ocr_text'] else "No OCR text")
        else:
            st.text("No OCR text available")
        
        st.subheader("VLM Description")
        if pd.notna(selected_screenshot['vlm_description']):
            st.text(selected_screenshot['vlm_description'])
        else:
            st.text("No VLM description available")
        
        st.subheader("Window Title")
        st.text(selected_screenshot['active_window'] if selected_screenshot['active_window'] else "No window title")
    
    # Performance comparison
    st.subheader("📈 Performance Analysis")
    
    confidence_scores = {method: result['confidence'] for method, result in comparison_results.items()}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Confidence Scores**")
        for method, confidence in confidence_scores.items():
            method_name = comparison_results[method]['method']
            st.progress(confidence, text=f"{method_name}: {confidence:.0%}")
    
    with col2:
        st.markdown("**Feature Usage**")
        all_features = set()
        for result in comparison_results.values():
            all_features.update(result['features_used'])
        
        for feature in sorted(all_features):
            methods_using = [
                result['method'] for result in comparison_results.values() 
                if feature in result['features_used']
            ]
            st.write(f"**{feature}:** {', '.join(methods_using)}")

if __name__ == "__main__":
    main()