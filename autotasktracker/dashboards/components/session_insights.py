"""Session insights component for displaying dual-model session analysis."""

import streamlit as st
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SessionInsightsComponent:
    """Component for displaying session-level insights from dual-model processing."""
    
    @staticmethod
    def render(tasks: List[Dict[str, Any]], show_session_analysis: bool = True) -> None:
        """Render session insights for a group of tasks.
        
        Args:
            tasks: List of task dictionaries with metadata
            show_session_analysis: Whether to show detailed session analysis
        """
        if not tasks:
            return
            
        # Extract session data from tasks
        session_data = SessionInsightsComponent._extract_session_data(tasks)
        
        if not session_data:
            return
            
        # Group by session ID
        sessions = SessionInsightsComponent._group_by_session(session_data)
        
        if not sessions:
            return
            
        # Render session insights
        with st.expander("🧠 Session Insights", expanded=show_session_analysis):
            SessionInsightsComponent._render_session_summary(sessions)
            
            if show_session_analysis:
                SessionInsightsComponent._render_detailed_analysis(sessions)
    
    @staticmethod
    def _extract_session_data(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract session-related data from tasks."""
        session_data = []
        
        for task in tasks:
            if not isinstance(task, dict) or 'metadata' not in task:
                continue
                
            metadata = task.get('metadata', {})
            if not metadata:
                continue
                
            # Check if this task has dual-model processing
            if not metadata.get('dual_model_processed'):
                continue
                
            session_info = {
                'task_id': task.get('id'),
                'session_id': metadata.get('session_id'),
                'timestamp': task.get('timestamp'),
                'llama3_session_result': metadata.get('llama3_session_result'),
                'workflow_analysis': metadata.get('workflow_analysis'),
                'dual_model_version': metadata.get('dual_model_version'),
                'window_title': task.get('window_title', ''),
                'category': task.get('category', 'Other')
            }
            
            # Only include if we have session ID
            if session_info['session_id']:
                session_data.append(session_info)
                
        return session_data
    
    @staticmethod
    def _group_by_session(session_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group session data by session ID."""
        sessions = {}
        
        for item in session_data:
            session_id = item['session_id']
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(item)
            
        # Sort tasks within each session by timestamp
        for session_id in sessions:
            sessions[session_id].sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min)
            
        return sessions
    
    @staticmethod
    def _render_session_summary(sessions: Dict[str, List[Dict[str, Any]]]) -> None:
        """Render a summary of all sessions."""
        if not sessions:
            st.info("No dual-model session data available")
            return
            
        # Calculate summary metrics
        total_sessions = len(sessions)
        total_analyzed_tasks = sum(len(tasks) for tasks in sessions.values())
        
        # Get workflow types from session analysis
        workflow_types = []
        session_durations = []
        
        for session_id, tasks in sessions.items():
            # Get latest analysis for this session
            latest_analysis = None
            for task in reversed(tasks):  # Check from latest
                if task.get('llama3_session_result'):
                    latest_analysis = task['llama3_session_result']
                    break
                if task.get('workflow_analysis'):
                    latest_analysis = task['workflow_analysis']
                    break
                    
            if latest_analysis and isinstance(latest_analysis, dict):
                workflow_type = latest_analysis.get('workflow_type', 'unknown')
                workflow_types.append(workflow_type)
                
            # Calculate session duration
            if len(tasks) > 1:
                start_time = tasks[0]['timestamp']
                end_time = tasks[-1]['timestamp']
                if start_time and end_time:
                    duration = (end_time - start_time).total_seconds() / 60  # minutes
                    session_durations.append(duration)
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Sessions", total_sessions)
            
        with col2:
            st.metric("AI-Analyzed Tasks", total_analyzed_tasks)
            
        with col3:
            if session_durations:
                avg_duration = sum(session_durations) / len(session_durations)
                st.metric("Avg Session", f"{avg_duration:.1f} min")
            else:
                st.metric("Avg Session", "N/A")
                
        with col4:
            if workflow_types:
                most_common = max(set(workflow_types), key=workflow_types.count)
                st.metric("Common Workflow", most_common.title())
            else:
                st.metric("Common Workflow", "N/A")
        
        # Show workflow type distribution if we have data
        if workflow_types:
            workflow_counts = {}
            for wf_type in workflow_types:
                workflow_counts[wf_type] = workflow_counts.get(wf_type, 0) + 1
                
            st.write("**Workflow Distribution:**")
            workflow_text = " • ".join([f"{wf_type.title()}: {count}" for wf_type, count in workflow_counts.items()])
            st.caption(workflow_text)
    
    @staticmethod
    def _render_detailed_analysis(sessions: Dict[str, List[Dict[str, Any]]]) -> None:
        """Render detailed analysis for each session."""
        st.divider()
        st.write("**Detailed Session Analysis:**")
        
        # Sort sessions by most recent first
        sorted_sessions = sorted(
            sessions.items(),
            key=lambda x: max(task['timestamp'] for task in x[1] if task['timestamp']),
            reverse=True
        )
        
        for session_id, tasks in sorted_sessions[:5]:  # Show top 5 most recent
            SessionInsightsComponent._render_single_session(session_id, tasks)
    
    @staticmethod
    def _render_single_session(session_id: str, tasks: List[Dict[str, Any]]) -> None:
        """Render analysis for a single session."""
        if not tasks:
            return
            
        # Get session timeframe
        start_time = tasks[0]['timestamp']
        end_time = tasks[-1]['timestamp']
        duration_mins = (end_time - start_time).total_seconds() / 60 if start_time and end_time else 0
        
        # Get latest analysis
        latest_analysis = None
        workflow_analysis = None
        
        for task in reversed(tasks):
            if not latest_analysis and task.get('llama3_session_result'):
                latest_analysis = task['llama3_session_result']
            if not workflow_analysis and task.get('workflow_analysis'):
                workflow_analysis = task['workflow_analysis']
            if latest_analysis and workflow_analysis:
                break
        
        # Format session header
        time_str = start_time.strftime("%H:%M") if start_time else "Unknown"
        header = f"**{session_id}** ({len(tasks)} tasks, {duration_mins:.1f} min) - {time_str}"
        
        with st.expander(header, expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Show session analysis if available
                if latest_analysis and isinstance(latest_analysis, dict):
                    st.write("**Session Analysis:**")
                    
                    workflow_type = latest_analysis.get('workflow_type', 'unknown')
                    st.write(f"• **Workflow Type:** {workflow_type.title()}")
                    
                    if 'main_activities' in latest_analysis:
                        activities = latest_analysis['main_activities']
                        if isinstance(activities, list):
                            st.write(f"• **Activities:** {', '.join(activities)}")
                    
                    if 'efficiency' in latest_analysis:
                        efficiency = latest_analysis['efficiency']
                        st.write(f"• **Efficiency:** {efficiency.title()}")
                    
                    if 'focus_level' in latest_analysis:
                        focus = latest_analysis['focus_level']
                        st.write(f"• **Focus Level:** {focus.title()}")
                    
                    if 'summary' in latest_analysis:
                        summary = latest_analysis['summary']
                        st.write(f"• **Summary:** {summary}")
                
                # Show workflow analysis if available and different
                if workflow_analysis and isinstance(workflow_analysis, dict) and workflow_analysis != latest_analysis:
                    st.write("**Workflow Analysis:**")
                    if 'primary_workflow' in workflow_analysis:
                        st.write(f"• **Primary Workflow:** {workflow_analysis['primary_workflow'].title()}")
                    if 'unique_activities' in workflow_analysis:
                        st.write(f"• **Unique Activities:** {workflow_analysis['unique_activities']}")
            
            with col2:
                # Show task categories and windows
                categories = [task['category'] for task in tasks]
                windows = [task['window_title'][:30] + '...' if len(task['window_title']) > 30 else task['window_title'] 
                          for task in tasks if task['window_title']]
                
                if categories:
                    unique_categories = list(set(categories))
                    st.write("**Categories:**")
                    for cat in unique_categories:
                        count = categories.count(cat)
                        st.caption(f"• {cat} ({count})")
                
                if windows:
                    st.write("**Windows:**")
                    unique_windows = list(dict.fromkeys(windows))  # Preserve order, remove duplicates
                    for window in unique_windows[:3]:  # Show top 3
                        st.caption(f"• {window}")
                    if len(unique_windows) > 3:
                        st.caption(f"• ... and {len(unique_windows) - 3} more")


class WorkflowVisualizationComponent:
    """Component for visualizing workflow patterns."""
    
    @staticmethod
    def render_workflow_timeline(sessions: Dict[str, List[Dict[str, Any]]]) -> None:
        """Render a timeline of workflow transitions."""
        if not sessions:
            return
            
        st.write("**Workflow Timeline:**")
        
        # Create timeline data
        timeline_data = []
        
        for session_id, tasks in sessions.items():
            if not tasks:
                continue
                
            # Get session workflow type
            workflow_type = "unknown"
            for task in reversed(tasks):
                analysis = task.get('llama3_session_result')
                if analysis and isinstance(analysis, dict):
                    workflow_type = analysis.get('workflow_type', 'unknown')
                    break
            
            start_time = tasks[0]['timestamp']
            end_time = tasks[-1]['timestamp']
            
            if start_time and end_time:
                timeline_data.append({
                    'session_id': session_id,
                    'workflow_type': workflow_type,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': (end_time - start_time).total_seconds() / 60,
                    'task_count': len(tasks)
                })
        
        # Sort by start time
        timeline_data.sort(key=lambda x: x['start_time'])
        
        # Display timeline
        for item in timeline_data:
            start_str = item['start_time'].strftime("%H:%M")
            end_str = item['end_time'].strftime("%H:%M")
            
            workflow_emoji = {
                'coding': '💻',
                'meeting': '👥', 
                'research': '📚',
                'communication': '💬',
                'planning': '📋',
                'mixed': '🔄'
            }.get(item['workflow_type'], '❓')
            
            st.write(f"{workflow_emoji} **{item['workflow_type'].title()}** "
                    f"({start_str}-{end_str}, {item['duration']:.1f}m, {item['task_count']} tasks)")