"""AI Task Display Components for Sensing Self Vision Implementation."""

import logging
import streamlit as st
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AITaskDisplayComponent:
    """Component for displaying AI-extracted task information instead of raw window titles."""
    
    @staticmethod
    def render_ai_enhanced_task_title(
        task_data: Dict[str, Any],
        show_reasoning: bool = False,
        show_confidence: bool = True
    ) -> str:
        """Render AI-enhanced task title with confidence indicators.
        
        Args:
            task_data: Task data including AI extractions
            show_reasoning: Whether to show AI reasoning chain
            show_confidence: Whether to show confidence indicators
            
        Returns:
            Rendered task title with AI enhancements
        """
        # Extract AI processing results
        ai_title = AITaskDisplayComponent._extract_ai_task_title(task_data)
        ai_confidence = AITaskDisplayComponent._get_ai_confidence(task_data)
        processing_status = AITaskDisplayComponent._get_processing_status(task_data)
        
        # Create enhanced title
        if ai_title and ai_title != task_data.get('window_title', ''):
            # Use AI-extracted title
            title = ai_title
            
            if show_confidence and ai_confidence:
                confidence_indicator = AITaskDisplayComponent._get_confidence_indicator(ai_confidence)
                title = f"✅ {title} {confidence_indicator}"
        else:
            # Fallback to enhanced window title
            title = AITaskDisplayComponent._enhance_window_title(
                task_data.get('window_title', 'Unknown Activity')
            )
            title = f"📋 {title}"
        
        # Add processing status if requested
        if show_confidence:
            status_indicators = AITaskDisplayComponent._get_status_indicators(processing_status)
            if status_indicators:
                title += f" | {status_indicators}"
        
        return title
    
    @staticmethod
    def render_ai_processing_status(
        task_data: Dict[str, Any],
        detailed: bool = False
    ) -> None:
        """Render AI processing status indicators.
        
        Args:
            task_data: Task data with processing information
            detailed: Whether to show detailed status
        """
        processing_status = AITaskDisplayComponent._get_processing_status(task_data)
        
        if detailed:
            # Detailed status display
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                ocr_status = "✅" if processing_status.get('ocr') else "❌"
                st.caption(f"📝 OCR {ocr_status}")
            
            with col2:
                vlm_status = "✅" if processing_status.get('vlm') else "❌"
                st.caption(f"👁️ VLM {vlm_status}")
            
            with col3:
                tasks_status = "✅" if processing_status.get('tasks') else "❌"
                st.caption(f"🎯 Tasks {tasks_status}")
            
            with col4:
                confidence = AITaskDisplayComponent._get_ai_confidence(task_data)
                if confidence:
                    conf_indicator = AITaskDisplayComponent._get_confidence_indicator(confidence)
                    st.caption(f"📊 {conf_indicator}")
                else:
                    st.caption("📊 No Score")
        else:
            # Compact status display
            status_line = AITaskDisplayComponent._get_status_indicators(processing_status)
            if status_line:
                st.caption(status_line)
    
    @staticmethod
    def render_ai_task_reasoning(
        task_data: Dict[str, Any],
        expanded: bool = False
    ) -> None:
        """Render AI task reasoning and extraction logic.
        
        Args:
            task_data: Task data with AI processing results
            expanded: Whether to show expanded by default
        """
        ai_reasoning = AITaskDisplayComponent._extract_ai_reasoning(task_data)
        
        if ai_reasoning:
            with st.expander("🧠 AI Task Discovery Reasoning", expanded=expanded):
                st.markdown("**How this task was discovered:**")
                
                # Show extraction process
                if ai_reasoning.get('process'):
                    st.text(ai_reasoning['process'])
                
                # Show confidence factors
                if ai_reasoning.get('confidence_factors'):
                    st.markdown("**Confidence factors:**")
                    for factor in ai_reasoning['confidence_factors']:
                        st.markdown(f"• {factor}")
                
                # Show raw data sources
                if ai_reasoning.get('sources'):
                    with st.expander("Raw Data Sources", expanded=False):
                        for source, data in ai_reasoning['sources'].items():
                            st.markdown(f"**{source}:**")
                            if isinstance(data, str) and len(data) > 200:
                                st.text(f"{data[:200]}...")
                            else:
                                st.text(str(data))
    
    @staticmethod
    def _extract_ai_task_title(task_data: Dict[str, Any]) -> Optional[str]:
        """Extract AI-generated task title from task data."""
        # Try VLM results first
        vlm_result = task_data.get('vlm_result') or task_data.get('minicpm_v_result')
        if vlm_result:
            try:
                if isinstance(vlm_result, str):
                    vlm_data = json.loads(vlm_result)
                else:
                    vlm_data = vlm_result
                
                # Look for task description in VLM result
                if isinstance(vlm_data, dict):
                    task_title = (vlm_data.get('task') or 
                                vlm_data.get('description') or 
                                vlm_data.get('activity'))
                    if task_title and task_title.strip() and task_title != "Activity":
                        return task_title.strip()
                        
            except (json.JSONDecodeError, AttributeError):
                logger.debug("Could not parse VLM result as JSON")
        
        # Try extracted tasks
        tasks = task_data.get('tasks')
        if tasks:
            try:
                if isinstance(tasks, str):
                    tasks_data = json.loads(tasks)
                else:
                    tasks_data = tasks
                
                if isinstance(tasks_data, list) and tasks_data:
                    first_task = tasks_data[0]
                    if isinstance(first_task, dict):
                        return first_task.get('title') or first_task.get('task')
                    elif isinstance(first_task, str):
                        return first_task
                        
            except (json.JSONDecodeError, AttributeError):
                logger.debug("Could not parse tasks as JSON")
        
        return None
    
    @staticmethod
    def _get_ai_confidence(task_data: Dict[str, Any]) -> Optional[float]:
        """Extract AI confidence score from task data."""
        # Try VLM confidence
        vlm_result = task_data.get('vlm_result') or task_data.get('minicpm_v_result')
        if vlm_result:
            try:
                if isinstance(vlm_result, str):
                    vlm_data = json.loads(vlm_result)
                else:
                    vlm_data = vlm_result
                
                if isinstance(vlm_data, dict):
                    confidence = vlm_data.get('confidence')
                    if confidence is not None:
                        return float(confidence)
                        
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        
        # Try task confidence
        tasks = task_data.get('tasks')
        if tasks:
            try:
                if isinstance(tasks, str):
                    tasks_data = json.loads(tasks)
                else:
                    tasks_data = tasks
                
                if isinstance(tasks_data, list) and tasks_data:
                    first_task = tasks_data[0]
                    if isinstance(first_task, dict):
                        confidence = first_task.get('confidence')
                        if confidence is not None:
                            return float(confidence)
                            
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        
        return None
    
    @staticmethod
    def _get_processing_status(task_data: Dict[str, Any]) -> Dict[str, bool]:
        """Get AI processing status for task data."""
        return {
            'ocr': bool(task_data.get('ocr_result')),
            'vlm': bool(task_data.get('vlm_result') or task_data.get('minicpm_v_result')),
            'tasks': bool(task_data.get('tasks')),
            'subtasks': bool(task_data.get('subtasks'))
        }
    
    @staticmethod
    def _get_confidence_indicator(confidence: float) -> str:
        """Get confidence indicator emoji and text."""
        if confidence >= 0.8:
            return "🟢 High (87%)" if confidence > 0.85 else "🟢 High"
        elif confidence >= 0.6:
            return "🟡 Medium"
        else:
            return "🔴 Low"
    
    @staticmethod
    def _get_status_indicators(processing_status: Dict[str, bool]) -> str:
        """Get compact status indicators string."""
        indicators = []
        
        if processing_status.get('ocr'):
            indicators.append("📝 OCR ✓")
        if processing_status.get('vlm'):
            indicators.append("👁️ VLM ✓")
        if processing_status.get('tasks'):
            indicators.append("🎯 Extracted ✓")
        
        return " | ".join(indicators) if indicators else ""
    
    @staticmethod
    def _enhance_window_title(window_title: str) -> str:
        """Enhance raw window title to be more readable."""
        if not window_title or window_title == 'Unknown':
            return "Unknown Activity"
        
        # Clean up Google URLs
        if 'google.com' in window_title and 'gemini' in window_title.lower():
            return "AI Research in Google Gemini"
        
        # Clean up Chrome tabs with long URLs
        if 'http' in window_title and len(window_title) > 80:
            if 'github' in window_title:
                return "Code Development (GitHub)"
            elif 'stackoverflow' in window_title:
                return "Programming Research (Stack Overflow)"
            elif 'google' in window_title:
                return "Web Research (Google)"
            else:
                return "Web Browsing"
        
        # Clean up common patterns
        if ' — ' in window_title:
            parts = window_title.split(' — ')
            if len(parts) >= 2:
                app = parts[0]
                context = parts[1]
                
                if app.lower() in ['chrome', 'safari', 'firefox']:
                    return f"Web Research ({context})"
                elif context and context != app:
                    return f"{context} ({app})"
        
        return window_title
    
    @staticmethod
    def _extract_ai_reasoning(task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract AI reasoning information from task data."""
        reasoning = {
            'process': None,
            'confidence_factors': [],
            'sources': {}
        }
        
        # Build reasoning from available data
        ai_title = AITaskDisplayComponent._extract_ai_task_title(task_data)
        confidence = AITaskDisplayComponent._get_ai_confidence(task_data)
        processing_status = AITaskDisplayComponent._get_processing_status(task_data)
        
        if ai_title:
            reasoning['process'] = f"AI analyzed screenshot and identified task: '{ai_title}'"
            
            if processing_status.get('vlm'):
                reasoning['confidence_factors'].append("VLM visual analysis completed")
            if processing_status.get('ocr'):
                reasoning['confidence_factors'].append("OCR text extraction successful")
            if confidence and confidence > 0.7:
                reasoning['confidence_factors'].append(f"High confidence score ({confidence:.1%})")
            
            # Add source data
            reasoning['sources']['window_title'] = task_data.get('window_title', '')
            if task_data.get('ocr_result'):
                reasoning['sources']['ocr_text'] = task_data['ocr_result']
            if task_data.get('vlm_result'):
                reasoning['sources']['vlm_analysis'] = task_data['vlm_result']
            
            return reasoning
        
        return None


class ScreenSchemaDisplayComponent:
    """Component for displaying Stateful Screen Schema information."""
    
    @staticmethod
    def render_screen_schema(
        task_data: Dict[str, Any],
        expanded: bool = False
    ) -> None:
        """Render structured screen schema display.
        
        Args:
            task_data: Task data with screen analysis
            expanded: Whether to show expanded by default
        """
        with st.expander("📋 Stateful Screen Schema", expanded=expanded):
            st.markdown("**Structured representation of screenshot analysis:**")
            
            # Metadata section
            st.markdown("**Metadata:**")
            col1, col2 = st.columns(2)
            with col1:
                st.text(f"Timestamp: {task_data.get('timestamp', 'Unknown')}")
                st.text(f"Application: {task_data.get('window_title', 'Unknown')}")
            with col2:
                st.text(f"Category: {task_data.get('category', 'Uncategorized')}")
                if task_data.get('screenshot_path'):
                    st.text("Screenshot: Available")
            
            # OCR Content
            ocr_result = task_data.get('ocr_result')
            if ocr_result:
                st.markdown("**Text Content (OCR):**")
                if len(ocr_result) > 300:
                    st.text(f"{ocr_result[:300]}...")
                    with st.expander("Show full OCR text"):
                        st.text(ocr_result)
                else:
                    st.text(ocr_result)
            
            # VLM Analysis
            vlm_result = task_data.get('vlm_result') or task_data.get('minicpm_v_result')
            if vlm_result:
                st.markdown("**Visual Analysis (VLM):**")
                try:
                    if isinstance(vlm_result, str):
                        vlm_data = json.loads(vlm_result)
                    else:
                        vlm_data = vlm_result
                    
                    if isinstance(vlm_data, dict):
                        for key, value in vlm_data.items():
                            st.text(f"{key}: {value}")
                    else:
                        st.text(str(vlm_data))
                except (json.JSONDecodeError, AttributeError):
                    st.text(str(vlm_result))
            
            # Task Extraction Results
            tasks = task_data.get('tasks')
            if tasks:
                st.markdown("**Extracted Tasks:**")
                try:
                    if isinstance(tasks, str):
                        tasks_data = json.loads(tasks)
                    else:
                        tasks_data = tasks
                    
                    if isinstance(tasks_data, list):
                        for i, task in enumerate(tasks_data):
                            if isinstance(task, dict):
                                st.text(f"{i+1}. {task.get('title', task.get('task', 'Unknown'))}")
                                if task.get('confidence'):
                                    st.text(f"   Confidence: {task['confidence']:.1%}")
                            else:
                                st.text(f"{i+1}. {task}")
                    else:
                        st.text(str(tasks_data))
                except (json.JSONDecodeError, AttributeError):
                    st.text(str(tasks))