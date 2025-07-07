"""
Llama Session Processor for AutoTaskTracker Dual-Model Architecture.

This module provides session-level reasoning using Llama 3 for workflow analysis
and temporal task understanding across multiple screenshots.
"""
import logging
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

from autotasktracker.config import get_config
from autotasktracker.core.error_handler import measure_latency, get_error_handler, get_metrics

logger = logging.getLogger(__name__)


@dataclass
class SessionBoundary:
    """Represents a detected session boundary."""
    start_time: datetime
    end_time: datetime
    session_id: str
    confidence: float
    boundary_type: str  # 'activity_change', 'time_gap', 'application_switch'
    description: str


@dataclass
class WorkflowPattern:
    """Represents an identified workflow pattern."""
    pattern_id: str
    pattern_type: str  # 'coding_session', 'research_task', 'meeting_workflow', etc.
    steps: List[str]
    duration: timedelta
    confidence: float
    context: Dict[str, Any]


class LlamaSessionProcessor:
    """
    Session-level reasoning engine using Llama 3 for workflow analysis.
    
    This processor analyzes sequences of VLM results to identify:
    - Session boundaries and transitions
    - Workflow patterns and task sequences
    - Temporal relationships between activities
    - High-level task categorization and insights
    """
    
    def __init__(self, cache_dir: str = None):
        """Initialize the session processor."""
        self.config = get_config()
        self.llama_model = self.config.LLAMA3_MODEL_NAME
        self.ollama_port = self.config.OLLAMA_PORT
        self.server_host = self.config.SERVER_HOST
        self.base_url = f"http://{self.server_host}:{self.ollama_port}"
        
        # Initialize error handling and metrics
        self.error_handler = get_error_handler()
        self.metrics = get_metrics()
        
        # Session analysis configuration
        self.session_gap_threshold = 300  # 5 minutes in seconds
        self.min_session_length = 30    # 30 seconds minimum
        self.max_chunk_size = 20        # Max screenshots per analysis chunk
        
        # Initialize session state
        self.session_cache = {}
        self.pattern_templates = self._initialize_pattern_templates()
        
        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def _initialize_pattern_templates(self) -> Dict[str, Dict]:
        """Initialize workflow pattern templates for recognition."""
        return {
            'coding_session': {
                'keywords': ['code', 'programming', 'debug', 'test', 'git', 'IDE', 'terminal'],
                'applications': ['IDE', 'Terminal', 'Browser'],
                'sequence_patterns': ['edit_code', 'run_test', 'debug', 'commit'],
                'min_duration_minutes': 5
            },
            'research_task': {
                'keywords': ['documentation', 'search', 'reading', 'research', 'tutorial'],
                'applications': ['Browser', 'Document'],
                'sequence_patterns': ['search', 'read', 'compare', 'bookmark'],
                'min_duration_minutes': 3
            },
            'meeting_workflow': {
                'keywords': ['meeting', 'video call', 'presentation', 'conference'],
                'applications': ['Meeting', 'Chat'],
                'sequence_patterns': ['join_meeting', 'presentation', 'discussion'],
                'min_duration_minutes': 10
            },
            'content_creation': {
                'keywords': ['writing', 'document', 'editing', 'presentation'],
                'applications': ['Document', 'Browser'],
                'sequence_patterns': ['create', 'edit', 'review', 'format'],
                'min_duration_minutes': 5
            }
        }
    
    def _call_llama3(self, prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> Optional[str]:
        """Call Llama 3 for text-only analysis."""
        try:
            payload = {
                'model': self.llama_model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': temperature,
                    'top_p': 0.9,
                    'num_predict': max_tokens,
                    'num_ctx': 4096
                }
            }
            
            logger.debug(f"Making Llama3 request with prompt length: {len(prompt)}")
            
            response = self.session.post(
                f'{self.base_url}/api/generate',
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'response' in result:
                return result['response'].strip()
            else:
                logger.error(f"No response in Llama3 result: {result}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Llama3 request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Llama3")
            return None
        except Exception as e:
            logger.error(f"Llama3 request failed: {e}")
            return None
    
    def detect_session_boundaries(self, screenshot_sequence: List[Dict]) -> List[SessionBoundary]:
        """
        Detect session boundaries in a sequence of screenshot data.
        
        Args:
            screenshot_sequence: List of screenshot metadata with timestamps and VLM results
            
        Returns:
            List of detected session boundaries
        """
        if len(screenshot_sequence) < 2:
            return []
        
        boundaries = []
        current_session_start = None
        
        for i, screenshot in enumerate(screenshot_sequence):
            timestamp = screenshot.get('timestamp')
            if not timestamp:
                continue
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Check for time gaps
            if i > 0:
                prev_timestamp = screenshot_sequence[i-1].get('timestamp')
                if isinstance(prev_timestamp, str):
                    prev_timestamp = datetime.fromisoformat(prev_timestamp.replace('Z', '+00:00'))
                
                time_gap = (timestamp - prev_timestamp).total_seconds()
                
                if time_gap > self.session_gap_threshold:
                    # End previous session and start new one
                    if current_session_start:
                        boundaries.append(SessionBoundary(
                            start_time=current_session_start,
                            end_time=prev_timestamp,
                            session_id=f"session_{len(boundaries)}",
                            confidence=0.9,
                            boundary_type='time_gap',
                            description=f"Time gap of {time_gap/60:.1f} minutes"
                        ))
                    current_session_start = timestamp
            else:
                current_session_start = timestamp
        
        # Close final session
        if current_session_start and screenshot_sequence:
            final_timestamp = screenshot_sequence[-1].get('timestamp')
            if isinstance(final_timestamp, str):
                final_timestamp = datetime.fromisoformat(final_timestamp.replace('Z', '+00:00'))
            
            boundaries.append(SessionBoundary(
                start_time=current_session_start,
                end_time=final_timestamp,
                session_id=f"session_{len(boundaries)}",
                confidence=0.8,
                boundary_type='session_end',
                description="Final session boundary"
            ))
        
        return boundaries
    
    def analyze_session_workflow(self, session_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze workflow patterns within a session using Llama 3.
        
        Args:
            session_data: List of screenshot data for a single session
            
        Returns:
            Dictionary containing workflow analysis results
        """
        if not session_data:
            return {'error': 'No session data provided'}
        
        # Prepare context summary for Llama 3
        context_summary = self._prepare_session_context(session_data)
        
        # Create analysis prompt
        prompt = f"""Analyze the following user workflow session and identify patterns:

SESSION CONTEXT:
{context_summary}

Please analyze this session and provide:
1. Main workflow type (coding, research, meeting, content_creation, mixed)
2. Key activities performed (list 3-5 main activities)
3. Workflow efficiency assessment (high/medium/low)
4. Identified task sequence or pattern
5. Session focus level (focused/scattered/interrupted)
6. Recommendations for improvement (optional)

Respond with ONLY valid JSON, no additional text or explanation:
{{
    "workflow_type": "coding",
    "main_activities": ["editing_code", "testing", "debugging"],
    "efficiency": "high",
    "task_sequence": ["open_ide", "edit_code", "run_tests"],
    "focus_level": "focused",
    "duration_minutes": 30,
    "recommendations": ["take_breaks", "use_version_control"]
}}"""
        
        # Get Llama 3 analysis
        start_time = time.time()
        llama_response = self._call_llama3(prompt, temperature=0.0, max_tokens=800)
        analysis_time = time.time() - start_time
        
        if not llama_response:
            logger.error("Failed to get Llama3 workflow analysis")
            return {'error': 'Llama3 analysis failed'}
        
        # Parse JSON response
        try:
            analysis_result = json.loads(llama_response)
            
            # Add metadata
            analysis_result.update({
                'session_id': session_data[0].get('session_id', 'unknown'),
                'analysis_timestamp': datetime.now().isoformat(),
                'analysis_duration': analysis_time,
                'screenshot_count': len(session_data),
                'llama_response_raw': llama_response
            })
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Llama3 JSON response: {e}")
            return {
                'error': 'JSON parsing failed',
                'raw_response': llama_response,
                'analysis_duration': analysis_time
            }
    
    def _prepare_session_context(self, session_data: List[Dict]) -> str:
        """Prepare session context summary for Llama 3 analysis."""
        if not session_data:
            return "No session data available"
        
        # Extract key information
        applications = []
        activities = []
        timestamps = []
        
        for item in session_data:
            # Get VLM results
            vlm_result = item.get('vlm_result', {})
            if isinstance(vlm_result, str):
                try:
                    vlm_result = json.loads(vlm_result)
                except json.JSONDecodeError:
                    vlm_result = {}
            
            # Extract application type
            app_type = vlm_result.get('app_type', 'Unknown')
            if app_type not in applications:
                applications.append(app_type)
            
            # Extract task/activity
            task = vlm_result.get('tasks', '')
            if task and task not in activities:
                activities.append(task)
            
            # Extract timestamp
            timestamp = item.get('timestamp')
            if timestamp:
                timestamps.append(timestamp)
        
        # Calculate session duration
        if len(timestamps) >= 2:
            start_time = timestamps[0]
            end_time = timestamps[-1]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            duration = (end_time - start_time).total_seconds() / 60  # minutes
        else:
            duration = 0
        
        # Build context summary
        context = f"""
Session Duration: {duration:.1f} minutes
Applications Used: {', '.join(applications[:5])}
Activities Observed: {', '.join(activities[:10])}
Screenshot Count: {len(session_data)}

Detailed Timeline:"""
        
        # Add timeline details (limit to prevent prompt from being too long)
        for i, item in enumerate(session_data[:15]):  # Limit to 15 items
            vlm_result = item.get('vlm_result', {})
            if isinstance(vlm_result, str):
                try:
                    vlm_result = json.loads(vlm_result)
                except json.JSONDecodeError:
                    vlm_result = {}
            
            timestamp = item.get('timestamp', 'Unknown')
            app_type = vlm_result.get('app_type', 'Unknown')
            task = vlm_result.get('tasks', 'Unknown activity')
            description = vlm_result.get('description', '')[:100]  # First 100 chars
            
            context += f"\n{i+1}. {timestamp} - {app_type}: {task}"
            if description:
                context += f" ({description}...)"
        
        if len(session_data) > 15:
            context += f"\n... and {len(session_data) - 15} more screenshots"
        
        return context
    
    def chunk_and_summarize_workflow(self, screenshot_sequence: List[Dict]) -> Dict[str, Any]:
        """
        Process large sequences of screenshots using chunk-and-summarize strategy.
        
        Args:
            screenshot_sequence: Complete sequence of screenshot data
            
        Returns:
            Comprehensive workflow analysis
        """
        if not screenshot_sequence:
            return {'error': 'No screenshots to analyze'}
        
        logger.info(f"Processing workflow for {len(screenshot_sequence)} screenshots")
        
        # Step 1: Detect session boundaries
        session_boundaries = self.detect_session_boundaries(screenshot_sequence)
        logger.info(f"Detected {len(session_boundaries)} session boundaries")
        
        # Step 2: Analyze each session separately
        session_analyses = []
        for boundary in session_boundaries:
            # Extract screenshots for this session
            session_screenshots = [
                s for s in screenshot_sequence
                if self._is_in_session_timeframe(s, boundary)
            ]
            
            if len(session_screenshots) >= 2:  # Minimum session size
                analysis = self.analyze_session_workflow(session_screenshots)
                analysis['session_boundary'] = {
                    'session_id': boundary.session_id,
                    'start_time': boundary.start_time.isoformat(),
                    'end_time': boundary.end_time.isoformat(),
                    'duration_minutes': (boundary.end_time - boundary.start_time).total_seconds() / 60
                }
                session_analyses.append(analysis)
        
        # Step 3: Create overall summary
        overall_summary = self._create_overall_summary(session_analyses, screenshot_sequence)
        
        return {
            'overall_summary': overall_summary,
            'session_analyses': session_analyses,
            'session_boundaries': [
                {
                    'session_id': b.session_id,
                    'start_time': b.start_time.isoformat(),
                    'end_time': b.end_time.isoformat(),
                    'boundary_type': b.boundary_type,
                    'confidence': b.confidence,
                    'description': b.description
                }
                for b in session_boundaries
            ],
            'total_screenshots': len(screenshot_sequence),
            'total_sessions': len(session_boundaries),
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _is_in_session_timeframe(self, screenshot: Dict, boundary: SessionBoundary) -> bool:
        """Check if screenshot falls within session boundary timeframe."""
        timestamp = screenshot.get('timestamp')
        if not timestamp:
            return False
        
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return boundary.start_time <= timestamp <= boundary.end_time
    
    def _create_overall_summary(self, session_analyses: List[Dict], all_screenshots: List[Dict]) -> Dict:
        """Create overall workflow summary from individual session analyses."""
        if not session_analyses:
            return {'error': 'No valid sessions to summarize'}
        
        # Aggregate data across sessions
        all_workflow_types = [s.get('workflow_type', 'unknown') for s in session_analyses if 'workflow_type' in s]
        all_activities = []
        total_duration = 0
        
        for analysis in session_analyses:
            if 'main_activities' in analysis:
                all_activities.extend(analysis['main_activities'])
            if 'duration_minutes' in analysis:
                total_duration += analysis['duration_minutes']
        
        # Count workflow types
        workflow_type_counts = defaultdict(int)
        for wt in all_workflow_types:
            workflow_type_counts[wt] += 1
        
        # Determine primary workflow type
        primary_workflow = max(workflow_type_counts.items(), key=lambda x: x[1])[0] if workflow_type_counts else 'mixed'
        
        # Create summary
        summary = {
            'primary_workflow_type': primary_workflow,
            'workflow_distribution': dict(workflow_type_counts),
            'total_duration_minutes': total_duration,
            'total_sessions': len(session_analyses),
            'unique_activities': list(set(all_activities)),
            'activity_count': len(set(all_activities)),
            'average_session_duration': total_duration / len(session_analyses) if session_analyses else 0,
            'productivity_indicators': {
                'session_count': len(session_analyses),
                'activity_diversity': len(set(all_activities)),
                'average_focus_time': total_duration / len(session_analyses) if session_analyses else 0
            }
        }
        
        return summary
    
    def get_processing_stats(self) -> Dict:
        """Get session processor statistics."""
        return {
            'llama_model': self.llama_model,
            'session_gap_threshold': self.session_gap_threshold,
            'max_chunk_size': self.max_chunk_size,
            'pattern_templates': len(self.pattern_templates),
            'cached_sessions': len(self.session_cache)
        }


# Convenience functions for external use
def create_session_processor() -> LlamaSessionProcessor:
    """Create and return a new session processor instance."""
    return LlamaSessionProcessor()


def analyze_workflow_sequence(screenshots: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function to analyze a sequence of screenshots for workflow patterns.
    
    Args:
        screenshots: List of screenshot data with VLM results and timestamps
        
    Returns:
        Workflow analysis results
    """
    processor = create_session_processor()
    return processor.chunk_and_summarize_workflow(screenshots)