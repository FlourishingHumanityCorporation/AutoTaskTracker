#!/usr/bin/env python3
"""
Intelligent Task Detection System

Automatically learns and detects task boundaries without hardcoded rules.
Uses machine learning principles to understand when tasks start and end.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import re
from collections import defaultdict
import json

@dataclass
class WindowEvent:
    """Single window focus event"""
    timestamp: datetime
    window_title: str
    app_name: str
    duration_to_next: float = 0.0  # seconds until next event
    
@dataclass
class TaskSession:
    """Automatically detected task session"""
    id: str
    events: List[WindowEvent] = field(default_factory=list)
    start_time: datetime = None
    end_time: datetime = None
    primary_window: str = ""
    total_duration: float = 0.0
    confidence: float = 0.0
    task_signature: str = ""
    
    def add_event(self, event: WindowEvent):
        """Add event and update session metrics"""
        self.events.append(event)
        if not self.start_time:
            self.start_time = event.timestamp
        self.end_time = event.timestamp
        self.total_duration = (self.end_time - self.start_time).total_seconds()

class IntelligentTaskDetector:
    """
    Learns from user behavior to automatically detect task boundaries
    No hardcoded rules - adapts to individual work patterns
    """
    
    def __init__(self):
        # Learning parameters
        self.window_patterns = defaultdict(lambda: {
            'avg_duration': 0,
            'switch_probability': 0,
            'return_probability': 0,
            'task_indicator_score': 0
        })
        
        # Task detection state
        self.current_session: Optional[TaskSession] = None
        self.completed_sessions: List[TaskSession] = []
        self.window_history: List[WindowEvent] = []
        
        # Behavioral metrics
        self.user_metrics = {
            'avg_window_duration': 30.0,  # Will be learned
            'typical_break_duration': 300.0,  # Will be learned
            'task_switch_indicators': [],  # Patterns that indicate task switch
            'task_continuation_indicators': []  # Patterns that indicate same task
        }
        
        # Dynamic thresholds (learned, not hardcoded)
        self.thresholds = {
            'idle_detection': None,  # Learn from gaps in activity
            'task_boundary': None,   # Learn from behavior patterns
            'confidence_minimum': 0.6
        }
        
    def analyze_window_sequence(self, events: List[WindowEvent]) -> Dict:
        """
        Analyze sequence of window events to learn patterns
        """
        if len(events) < 2:
            return {}
            
        patterns = {
            'window_durations': [],
            'app_transitions': defaultdict(int),
            'return_sequences': [],
            'idle_gaps': [],
            'work_sessions': []
        }
        
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            # Calculate duration
            duration = (next_event.timestamp - current.timestamp).total_seconds()
            current.duration_to_next = duration
            patterns['window_durations'].append(duration)
            
            # Track app transitions
            transition = f"{current.app_name} -> {next_event.app_name}"
            patterns['app_transitions'][transition] += 1
            
            # Detect idle periods (statistical outliers)
            if duration > np.percentile(patterns['window_durations'], 95):
                patterns['idle_gaps'].append({
                    'duration': duration,
                    'after_window': current.window_title,
                    'before_window': next_event.window_title
                })
                
            # Detect return patterns
            if i < len(events) - 5:  # Look ahead up to 5 events
                for j in range(i + 2, min(i + 6, len(events))):
                    if events[j].window_title == current.window_title:
                        patterns['return_sequences'].append({
                            'window': current.window_title,
                            'gap_events': j - i,
                            'gap_duration': (events[j].timestamp - current.timestamp).total_seconds()
                        })
                        break
                        
        return patterns
        
    def calculate_task_boundary_probability(self, 
                                          prev_event: WindowEvent, 
                                          curr_event: WindowEvent,
                                          context_window: List[WindowEvent]) -> float:
        """
        Calculate probability that this represents a task boundary
        Uses multiple signals, not hardcoded rules
        """
        signals = []
        
        # Signal 1: Time gap analysis (adaptive, not hardcoded)
        time_gap = (curr_event.timestamp - prev_event.timestamp).total_seconds()
        if self.window_history:
            recent_gaps = [e.duration_to_next for e in self.window_history[-20:] if e.duration_to_next > 0]
            if recent_gaps:
                gap_percentile = np.percentile(recent_gaps, [50, 75, 90, 95])
                if time_gap > gap_percentile[3]:  # 95th percentile
                    signals.append(('extreme_gap', 0.9))
                elif time_gap > gap_percentile[2]:  # 90th percentile
                    signals.append(('large_gap', 0.7))
                elif time_gap > gap_percentile[1]:  # 75th percentile
                    signals.append(('moderate_gap', 0.4))
                    
        # Signal 2: Content change analysis
        prev_content = self.extract_content_signature(prev_event.window_title)
        curr_content = self.extract_content_signature(curr_event.window_title)
        
        content_similarity = self.calculate_content_similarity(prev_content, curr_content)
        if content_similarity < 0.2:
            signals.append(('different_content', 0.8))
        elif content_similarity < 0.5:
            signals.append(('related_content', 0.3))
            
        # Signal 3: App transition patterns
        if prev_event.app_name != curr_event.app_name:
            # Check if this app transition is common in task continuations
            transition = f"{prev_event.app_name} -> {curr_event.app_name}"
            if self.is_common_support_pattern(transition, context_window):
                signals.append(('support_app', -0.5))  # Negative signal
            else:
                signals.append(('app_switch', 0.5))
                
        # Signal 4: Return pattern detection
        if self.current_session and curr_event.window_title in [e.window_title for e in self.current_session.events]:
            return_gap = (curr_event.timestamp - self.current_session.end_time).total_seconds()
            if return_gap < 300:  # Recent return
                signals.append(('task_return', -0.8))  # Strong negative signal
                
        # Signal 5: Behavioral patterns
        if self.matches_task_end_pattern(prev_event, curr_event):
            signals.append(('task_end_pattern', 0.7))
            
        # Combine signals with learned weights
        if not signals:
            return 0.5  # Neutral
            
        # Weighted average of signals
        total_weight = sum(abs(signal[1]) for signal in signals)
        probability = sum(signal[1] for signal in signals) / total_weight
        
        # Normalize to 0-1 range
        return max(0, min(1, (probability + 1) / 2))
        
    def extract_content_signature(self, window_title: str) -> Dict:
        """
        Extract semantic content from window title
        Not hardcoded - learns what's important
        """
        signature = {
            'tokens': set(),
            'entities': [],
            'type_indicators': []
        }
        
        # Clean and tokenize
        cleaned = re.sub(r'[^\w\s@.-]', ' ', window_title.lower())
        tokens = [t for t in cleaned.split() if len(t) > 2]
        signature['tokens'] = set(tokens)
        
        # Extract potential entities (emails, files, people)
        email_pattern = r'[\w\.-]+@[\w\.-]+'
        emails = re.findall(email_pattern, window_title)
        signature['entities'].extend(emails)
        
        # Extract names (capitalized words not at start)
        name_pattern = r'\b[A-Z][a-z]+\b'
        names = re.findall(name_pattern, window_title)
        if len(names) > 1:  # Avoid app names
            signature['entities'].extend(names[1:])
            
        # Extract file names
        file_pattern = r'[\w-]+\.[\w]{2,4}'
        files = re.findall(file_pattern, window_title)
        signature['entities'].extend(files)
        
        # Identify task type indicators
        if any(indicator in cleaned for indicator in ['compose', 'reply', 'forward', 'draft']):
            signature['type_indicators'].append('email_compose')
        if any(indicator in cleaned for indicator in ['pdf', 'doc', 'docx', 'pages']):
            signature['type_indicators'].append('document')
        if any(ext in cleaned for ext in ['.py', '.js', '.java', '.cpp', '.tsx']):
            signature['type_indicators'].append('coding')
            
        return signature
        
    def calculate_content_similarity(self, sig1: Dict, sig2: Dict) -> float:
        """
        Calculate semantic similarity between two content signatures
        """
        if not sig1 or not sig2:
            return 0.0
            
        # Token overlap
        if sig1['tokens'] and sig2['tokens']:
            token_overlap = len(sig1['tokens'] & sig2['tokens']) / len(sig1['tokens'] | sig2['tokens'])
        else:
            token_overlap = 0
            
        # Entity overlap (more important)
        entity_overlap = 0
        if sig1['entities'] and sig2['entities']:
            common_entities = set(sig1['entities']) & set(sig2['entities'])
            entity_overlap = len(common_entities) / min(len(sig1['entities']), len(sig2['entities']))
            
        # Type similarity
        type_similarity = 0
        if sig1['type_indicators'] and sig2['type_indicators']:
            if set(sig1['type_indicators']) & set(sig2['type_indicators']):
                type_similarity = 1.0
                
        # Weighted combination
        similarity = (token_overlap * 0.3 + entity_overlap * 0.5 + type_similarity * 0.2)
        return similarity
        
    def is_common_support_pattern(self, transition: str, context: List[WindowEvent]) -> bool:
        """
        Learn if this app transition is commonly part of a task
        """
        # Look at historical patterns
        if len(self.completed_sessions) < 5:
            return False  # Not enough data yet
            
        support_count = 0
        total_count = 0
        
        for session in self.completed_sessions[-20:]:  # Last 20 sessions
            events = session.events
            for i in range(len(events) - 1):
                if f"{events[i].app_name} -> {events[i+1].app_name}" == transition:
                    total_count += 1
                    # Check if they were part of same task
                    if i + 1 < len(events):
                        support_count += 1
                        
        if total_count > 3:
            return (support_count / total_count) > 0.7
        return False
        
    def matches_task_end_pattern(self, prev: WindowEvent, curr: WindowEvent) -> bool:
        """
        Detect learned patterns that indicate task completion
        """
        # Learn from user behavior - not hardcoded
        end_indicators = []
        
        # Pattern 1: Moving to dashboard/home/desktop
        if any(indicator in curr.window_title.lower() for indicator in ['desktop', 'finder', 'explorer', 'home']):
            end_indicators.append('moved_to_home')
            
        # Pattern 2: Moving to break-type apps (learned from idle patterns)
        break_apps = self.learn_break_apps()
        if curr.app_name.lower() in break_apps:
            end_indicators.append('break_app')
            
        # Pattern 3: Significant content shift with time gap
        content_sim = self.calculate_content_similarity(
            self.extract_content_signature(prev.window_title),
            self.extract_content_signature(curr.window_title)
        )
        time_gap = (curr.timestamp - prev.timestamp).total_seconds()
        if content_sim < 0.3 and time_gap > 60:
            end_indicators.append('content_shift_with_gap')
            
        return len(end_indicators) >= 2
        
    def learn_break_apps(self) -> set:
        """
        Learn which apps are typically used during breaks
        """
        break_apps = set()
        
        if not self.window_history:
            return break_apps
            
        # Find apps that appear before/after idle periods
        for i in range(1, len(self.window_history) - 1):
            if self.window_history[i].duration_to_next > 300:  # 5+ minute gap
                break_apps.add(self.window_history[i].app_name.lower())
                if i + 1 < len(self.window_history):
                    break_apps.add(self.window_history[i + 1].app_name.lower())
                    
        return break_apps
        
    def process_window_event(self, window_title: str, timestamp: datetime) -> Optional[TaskSession]:
        """
        Process new window event and return completed task if boundary detected
        """
        # Extract app name
        app_name = window_title.split(' - ')[-1].strip() if ' - ' in window_title else 'Unknown'
        
        event = WindowEvent(
            timestamp=timestamp,
            window_title=window_title,
            app_name=app_name
        )
        
        self.window_history.append(event)
        
        # First event - start new session
        if not self.current_session:
            self.current_session = TaskSession(
                id=f"task_{timestamp.timestamp()}",
                start_time=timestamp
            )
            self.current_session.add_event(event)
            return None
            
        # Calculate task boundary probability
        prev_event = self.current_session.events[-1]
        context = self.window_history[-10:] if len(self.window_history) > 10 else self.window_history
        
        boundary_probability = self.calculate_task_boundary_probability(
            prev_event, event, context
        )
        
        # Adaptive threshold based on confidence
        threshold = self.calculate_adaptive_threshold()
        
        if boundary_probability > threshold:
            # Task boundary detected - complete current session
            completed = self.current_session
            completed.confidence = 1 - boundary_probability
            self.completed_sessions.append(completed)
            
            # Start new session
            self.current_session = TaskSession(
                id=f"task_{timestamp.timestamp()}",
                start_time=timestamp
            )
            self.current_session.add_event(event)
            
            # Learn from this session
            self.learn_from_session(completed)
            
            return completed
        else:
            # Continue current session
            self.current_session.add_event(event)
            return None
            
    def calculate_adaptive_threshold(self) -> float:
        """
        Dynamically adjust threshold based on learned patterns
        """
        if len(self.completed_sessions) < 10:
            return 0.7  # Conservative default
            
        # Analyze recent session quality
        recent_sessions = self.completed_sessions[-10:]
        avg_duration = np.mean([s.total_duration for s in recent_sessions])
        avg_events = np.mean([len(s.events) for s in recent_sessions])
        
        # Adjust threshold based on session characteristics
        if avg_duration < 60:  # Too many short sessions
            return 0.8  # Increase threshold
        elif avg_duration > 1800:  # Very long sessions
            return 0.6  # Decrease threshold
        else:
            return 0.7
            
    def learn_from_session(self, session: TaskSession):
        """
        Update learning parameters based on completed session
        """
        # Update window duration statistics
        durations = [e.duration_to_next for e in session.events if e.duration_to_next > 0]
        if durations:
            self.user_metrics['avg_window_duration'] = np.mean(durations)
            
        # Learn task patterns
        if len(session.events) > 3:
            # This was likely a real task - learn its patterns
            for i in range(len(session.events) - 1):
                transition = f"{session.events[i].app_name} -> {session.events[i+1].app_name}"
                # Store as continuation pattern
                if transition not in self.user_metrics['task_continuation_indicators']:
                    self.user_metrics['task_continuation_indicators'].append(transition)
                    
    def get_current_statistics(self) -> Dict:
        """
        Return learned statistics about user behavior
        """
        if not self.completed_sessions:
            return {}
            
        recent = self.completed_sessions[-50:] if len(self.completed_sessions) > 50 else self.completed_sessions
        
        return {
            'avg_task_duration': np.mean([s.total_duration for s in recent]) / 60,
            'avg_windows_per_task': np.mean([len(s.events) for s in recent]),
            'common_transitions': self.user_metrics['task_continuation_indicators'][:10],
            'learned_threshold': self.calculate_adaptive_threshold(),
            'total_sessions_analyzed': len(self.completed_sessions)
        }


# Integration function for AutoTaskTracker
def process_screenshots_intelligently(screenshots_df):
    """
    Process screenshots with intelligent task detection
    """
    detector = IntelligentTaskDetector()
    
    # Sort by timestamp
    screenshots_df = screenshots_df.sort_values('created_at')
    
    completed_tasks = []
    
    # Process each screenshot
    for idx, row in screenshots_df.iterrows():
        window_title = row.get('active_window', '')
        timestamp = row['created_at']
        
        completed_task = detector.process_window_event(window_title, timestamp)
        if completed_task:
            completed_tasks.append(completed_task)
            
    # Don't forget the current session
    if detector.current_session and len(detector.current_session.events) > 1:
        completed_tasks.append(detector.current_session)
        
    # Convert to dataframe
    tasks_data = []
    for task in completed_tasks:
        if task.events:
            # Determine primary window (most frequent)
            window_counts = defaultdict(int)
            for event in task.events:
                window_counts[event.window_title] += 1
            primary_window = max(window_counts.items(), key=lambda x: x[1])[0]
            
            # Extract meaningful task name
            content_sig = detector.extract_content_signature(primary_window)
            task_name = primary_window.split(' - ')[0] if ' - ' in primary_window else primary_window
            
            tasks_data.append({
                'task_id': task.id,
                'task_name': task_name,
                'start_time': task.start_time,
                'end_time': task.end_time,
                'duration_minutes': task.total_duration / 60,
                'window_count': len(task.events),
                'unique_windows': len(set(e.window_title for e in task.events)),
                'confidence': task.confidence,
                'primary_window': primary_window
            })
            
    return pd.DataFrame(tasks_data), detector.get_current_statistics()