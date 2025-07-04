"""
AI-Enhanced Task Board for AutoTaskTracker.
Shows tasks with AI-powered insights from VLM, embeddings, and enhanced OCR.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from PIL import Image
import json

from autotasktracker.core.database import DatabaseManager
from autotasktracker.ai.enhanced_task_extractor import AIEnhancedTaskExtractor
from autotasktracker.ai.embeddings_search import EmbeddingStats
from autotasktracker.core.categorizer import ActivityCategorizer


# Page config
st.set_page_config(
    page_title="AI-Enhanced Task Board - AutoTaskTracker",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .task-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 4px solid #1f77b4;
    }
    .ai-insight {
        background-color: #e8f4f8;
        border-radius: 5px;
        padding: 10px;
        margin-top: 10px;
        border-left: 3px solid #00a0dc;
    }
    .confidence-high {
        color: #28a745;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .confidence-low {
        color: #dc3545;
        font-weight: bold;
    }
    .similarity-badge {
        background-color: #6c757d;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'selected_time_filter' not in st.session_state:
        st.session_state.selected_time_filter = "Last Hour"
    if 'show_ai_insights' not in st.session_state:
        st.session_state.show_ai_insights = True
    if 'group_similar' not in st.session_state:
        st.session_state.group_similar = False


def format_confidence(confidence: float) -> str:
    """Format confidence score with color coding."""
    if confidence >= 0.8:
        css_class = "confidence-high"
        label = "High"
    elif confidence >= 0.6:
        css_class = "confidence-medium"
        label = "Medium"
    else:
        css_class = "confidence-low"
        label = "Low"
    
    return f'<span class="{css_class}">{label} ({confidence:.0%})</span>'


def show_ai_coverage_stats(db_manager: DatabaseManager):
    """Display AI feature coverage statistics."""
    stats = db_manager.get_ai_coverage_stats()
    
    if stats:
        cols = st.columns(4)
        
        with cols[0]:
            st.metric(
                "Total Screenshots",
                f"{stats['total_screenshots']:,}",
                help="Total number of screenshots captured"
            )
        
        with cols[1]:
            st.metric(
                "OCR Coverage",
                f"{stats['ocr_percentage']:.1f}%",
                f"{stats['ocr_count']:,} processed",
                help="Percentage of screenshots with OCR text extraction"
            )
        
        with cols[2]:
            st.metric(
                "VLM Coverage",
                f"{stats['vlm_percentage']:.1f}%",
                f"{stats['vlm_count']:,} processed",
                help="Percentage of screenshots with VLM descriptions"
            )
        
        with cols[3]:
            st.metric(
                "Embedding Coverage",
                f"{stats['embedding_percentage']:.1f}%",
                f"{stats['embedding_count']:,} processed",
                help="Percentage of screenshots with embeddings for similarity search"
            )


def display_task_with_ai_insights(task: dict, ai_extractor: AIEnhancedTaskExtractor):
    """Display a task card with AI insights."""
    # Extract enhanced task info
    enhanced_task = ai_extractor.extract_enhanced_task(
        window_title=task.get('active_window'),
        ocr_text=task.get('ocr_text'),
        vlm_description=task.get('vlm_description'),
        entity_id=task.get('id')
    )
    
    # Task card container
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Task title with confidence
            st.markdown(f"### {enhanced_task['task']}")
            
            # Metadata row
            metadata_parts = []
            metadata_parts.append(f"📁 {enhanced_task['category']}")
            metadata_parts.append(f"🕐 {task['created_at']}")
            
            # Add confidence indicator
            confidence_html = format_confidence(enhanced_task['confidence'])
            metadata_parts.append(f"Confidence: {confidence_html}")
            
            st.markdown(" | ".join(metadata_parts), unsafe_allow_html=True)
            
            # AI Features indicators
            ai_features = enhanced_task['ai_features']
            feature_badges = []
            
            if ai_features.get('ocr_quality'):
                quality = ai_features['ocr_quality']
                emoji = "✅" if quality in ['excellent', 'good'] else "⚠️" if quality == 'fair' else "❌"
                feature_badges.append(f"{emoji} OCR: {quality}")
            
            if ai_features.get('vlm_available'):
                conf = ai_features.get('vlm_confidence', 0)
                emoji = "✅" if conf > 0.7 else "⚠️"
                feature_badges.append(f"{emoji} VLM: {conf:.0%}")
            
            if ai_features.get('embeddings_available'):
                feature_badges.append("🔍 Similar tasks found")
            
            if feature_badges:
                st.markdown("**AI Features:** " + " | ".join(feature_badges))
            
            # Show AI insights if enabled
            if st.session_state.show_ai_insights:
                if enhanced_task.get('ui_state'):
                    st.info(f"**UI State:** {enhanced_task['ui_state']}")
                
                if enhanced_task.get('subtasks'):
                    with st.expander("📋 Detected Subtasks"):
                        for subtask in enhanced_task['subtasks'][:5]:
                            st.write(f"• {subtask}")
                
                if enhanced_task.get('similar_tasks'):
                    with st.expander(f"🔗 Similar Tasks ({len(enhanced_task['similar_tasks'])})"):
                        for similar in enhanced_task['similar_tasks']:
                            st.write(f"• {similar['task']} "
                                   f"*({similar['similarity']:.0%} similar, {similar['time']})*")
        
        with col2:
            # Screenshot thumbnail
            if task.get('filepath') and os.path.exists(task['filepath']):
                try:
                    image = Image.open(task['filepath'])
                    # Create thumbnail
                    image.thumbnail((200, 150))
                    st.image(image, use_column_width=True)
                except Exception as e:
                    st.error(f"Could not load image: {e}")
            
            # Quick stats
            if enhanced_task.get('text_regions'):
                regions = enhanced_task['text_regions']
                st.caption(f"📝 {sum(regions.values())} text regions")
                if regions.get('code', 0) > 0:
                    st.caption(f"💻 {regions['code']} code blocks")
        
        st.divider()


def main():
    init_session_state()
    
    st.title("🤖 AI-Enhanced Task Board")
    st.markdown("Discover your daily activities with advanced AI insights")
    
    # Initialize components
    db_manager = DatabaseManager()
    ai_extractor = AIEnhancedTaskExtractor(db_manager.db_path)
    
    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Time filter
        time_filter = st.selectbox(
            "Time Range",
            ["Last 15 Minutes", "Last Hour", "Today", "Last 24 Hours", "Last 7 Days"],
            index=1,
            key="time_filter_select"
        )
        st.session_state.selected_time_filter = time_filter
        
        # AI features toggles
        st.subheader("AI Features")
        st.session_state.show_ai_insights = st.checkbox(
            "Show AI Insights",
            value=st.session_state.show_ai_insights,
            help="Display VLM descriptions, similar tasks, and other AI insights"
        )
        
        st.session_state.group_similar = st.checkbox(
            "Group Similar Tasks",
            value=st.session_state.group_similar,
            help="Use embeddings to group similar activities together"
        )
        
        # Category filter
        all_categories = list(ActivityCategorizer.CATEGORIES.keys())
        selected_categories = st.multiselect(
            "Filter by Category",
            options=[ActivityCategorizer.CATEGORIES[cat][0] for cat in all_categories],
            default=None
        )
        
        # Search
        search_term = st.text_input("🔍 Search tasks", placeholder="Type to search...")
    
    # Main content area
    # Show AI coverage stats
    st.subheader("📊 AI Coverage Statistics")
    show_ai_coverage_stats(db_manager)
    
    st.divider()
    
    # Fetch tasks with AI data
    tasks_df = db_manager.fetch_tasks_with_ai(
        start_date=datetime.now() - timedelta(hours=24) if time_filter == "Last 24 Hours" else None,
        limit=100
    )
    
    if tasks_df.empty:
        st.warning("No tasks found. Make sure Pensieve is running and capturing screenshots.")
        return
    
    # Convert to list of dicts for easier processing
    tasks = tasks_df.to_dict('records')
    
    # Apply search filter
    if search_term:
        tasks = [
            t for t in tasks
            if search_term.lower() in str(t.get('active_window', '')).lower() or
               search_term.lower() in str(t.get('ocr_text', '')).lower() or
               search_term.lower() in str(t.get('vlm_description', '')).lower()
        ]
    
    # Apply category filter
    if selected_categories:
        tasks = [
            t for t in tasks
            if ActivityCategorizer.categorize(t.get('active_window', '')) in selected_categories
        ]
    
    # Group similar tasks if enabled
    if st.session_state.group_similar and len(tasks) > 1:
        st.subheader(f"📋 Grouped Activities ({len(tasks)} screenshots)")
        
        # Group tasks
        task_groups = ai_extractor.group_similar_tasks(tasks)
        
        for i, group in enumerate(task_groups):
            if len(group) > 1:
                with st.expander(f"🔗 Task Group {i+1} ({len(group)} similar activities)", expanded=True):
                    for task in group:
                        display_task_with_ai_insights(task, ai_extractor)
            else:
                # Single task, display normally
                display_task_with_ai_insights(group[0], ai_extractor)
    else:
        # Display tasks without grouping
        st.subheader(f"📋 Recent Activities ({len(tasks)} tasks)")
        
        for task in tasks:
            display_task_with_ai_insights(task, ai_extractor)
    
    # Footer
    st.divider()
    st.caption("🤖 Powered by Pensieve AI: OCR, VLM, and Embeddings")


if __name__ == "__main__":
    main()