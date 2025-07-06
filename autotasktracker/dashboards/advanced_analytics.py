"""Advanced Analytics Dashboard - Showcasing the power of the refactored architecture."""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import logging

from .base import BaseDashboard
from .components import (
    TimeFilterComponent, 
    CategoryFilterComponent,
    MetricsRow,
    CategoryPieChart,
    HourlyActivityChart,
    TrendChart,
    ComparisonChart,
    NoDataMessage
)
from .data import TaskRepository, MetricsRepository
from .cache import cached_data, MetricsCache
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class AdvancedAnalyticsDashboard(BaseDashboard):
    """Advanced analytics dashboard showcasing the new architecture capabilities."""
    
    def __init__(self):
        super().__init__(
            title="Advanced Analytics - AutoTaskTracker",
            icon="🧠",
            port=get_config().ADVANCED_ANALYTICS_PORT
        )
        
    def init_session_state(self):
        """Initialize advanced analytics session state."""
        super().init_session_state()
        
        if 'analysis_type' not in st.session_state:
            st.session_state.analysis_type = 'productivity'
        if 'comparison_mode' not in st.session_state:
            st.session_state.comparison_mode = False
        if 'ai_insights_enabled' not in st.session_state:
            st.session_state.ai_insights_enabled = True
            
    def render_sidebar(self):
        """Render advanced sidebar controls."""
        with st.sidebar:
            st.header("🧠 Advanced Analytics")
            
            # Analysis type selector
            analysis_type = st.selectbox(
                "Analysis Type",
                ["productivity", "patterns", "predictions", "comparisons"],
                index=["productivity", "patterns", "predictions", "comparisons"].index(
                    st.session_state.analysis_type
                ),
                key="analysis_type"
            )
            
            # Time filter with custom ranges
            time_filter = TimeFilterComponent.render()
            
            # Advanced options
            st.subheader("Advanced Options")
            comparison_mode = st.checkbox(
                "Comparison Mode",
                value=st.session_state.comparison_mode,
                key="comparison_mode",
                help="Compare multiple time periods"
            )
            
            ai_insights = st.checkbox(
                "AI Insights",
                value=st.session_state.ai_insights_enabled,
                key="ai_insights_enabled",
                help="Enable AI-powered insights and recommendations"
            )
            
            # Analysis parameters
            st.subheader("Parameters")
            confidence_threshold = st.slider(
                "Confidence Threshold",
                min_value=0.1,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Minimum confidence for including data points"
            )
            
            smoothing_window = st.slider(
                "Smoothing Window (days)",
                min_value=1,
                max_value=14,
                value=3,
                help="Moving average window for trend smoothing"
            )
            
            # Export options
            st.subheader("Export")
            if st.button("📊 Export Analysis Report"):
                self.export_analysis_report(analysis_type, time_filter)
                
            # Session controls
            from .components.session_controls import SessionControlsComponent
            SessionControlsComponent.render_minimal(position="sidebar")
            
            return analysis_type, time_filter, comparison_mode, ai_insights, confidence_threshold, smoothing_window
            
    @cached_data(ttl_seconds=600, key_prefix="advanced_productivity")
    def get_productivity_analysis(self, start_date, end_date, confidence_threshold):
        """Get advanced productivity analysis."""
        task_repo = TaskRepository(self.db_manager)
        task_groups = task_repo.get_task_groups(start_date, end_date, min_duration_minutes=1)
        
        if not task_groups:
            return None
            
        # Calculate productivity metrics
        analysis = {
            'total_time': sum(g.duration_minutes for g in task_groups),
            'productive_time': sum(g.duration_minutes for g in task_groups if g.category in ['Development', 'Productivity']),
            'focus_sessions': len([g for g in task_groups if g.duration_minutes >= 25]),  # Pomodoro-style
            'context_switches': self._calculate_context_switches(task_groups),
            'peak_productivity_hours': self._find_peak_hours(task_groups),
            'efficiency_score': self._calculate_efficiency_score(task_groups),
        }
        
        analysis['productivity_rate'] = (analysis['productive_time'] / max(analysis['total_time'], 1)) * 100
        analysis['focus_rate'] = (len([g for g in task_groups if g.duration_minutes >= 25]) / max(len(task_groups), 1)) * 100
        
        return analysis
        
    def _calculate_context_switches(self, task_groups):
        """Calculate context switching frequency."""
        if len(task_groups) < 2:
            return 0
            
        switches = 0
        prev_category = None
        
        for group in sorted(task_groups, key=lambda x: x.start_time):
            if prev_category and prev_category != group.category:
                switches += 1
            prev_category = group.category
            
        return switches
        
    def _find_peak_hours(self, task_groups):
        """Find peak productivity hours."""
        hourly_productivity = {}
        
        for group in task_groups:
            hour = group.start_time.hour
            if group.category in ['Development', 'Productivity']:
                hourly_productivity[hour] = hourly_productivity.get(hour, 0) + group.duration_minutes
                
        if not hourly_productivity:
            return []
            
        # Get top 3 productive hours
        top_hours = sorted(hourly_productivity.items(), key=lambda x: x[1], reverse=True)[:3]
        return [hour for hour, _ in top_hours]
        
    def _calculate_efficiency_score(self, task_groups):
        """Calculate overall efficiency score (0-100)."""
        if not task_groups:
            return 0
            
        # Factors: focus time, minimal context switching, productive categories
        total_time = sum(g.duration_minutes for g in task_groups)
        productive_time = sum(g.duration_minutes for g in task_groups if g.category in ['Development', 'Productivity'])
        focus_time = sum(g.duration_minutes for g in task_groups if g.duration_minutes >= 25)
        
        switches = self._calculate_context_switches(task_groups)
        switch_penalty = min(switches * 2, 30)  # Max 30 point penalty
        
        # Calculate score
        productivity_score = (productive_time / total_time) * 40 if total_time > 0 else 0
        focus_score = (focus_time / total_time) * 40 if total_time > 0 else 0
        consistency_score = max(0, 20 - switch_penalty)
        
        return min(100, productivity_score + focus_score + consistency_score)
        
    @cached_data(ttl_seconds=600, key_prefix="advanced_patterns")
    def get_pattern_analysis(self, start_date, end_date, smoothing_window):
        """Get advanced pattern analysis."""
        task_repo = TaskRepository(self.db_manager)
        
        # Get daily data for pattern analysis
        current_date = start_date
        daily_data = []
        
        while current_date <= end_date:
            day_tasks = task_repo.get_task_groups(
                current_date.replace(hour=0, minute=0, second=0),
                current_date.replace(hour=23, minute=59, second=59)
            )
            
            if day_tasks:
                day_analysis = {
                    'date': current_date,
                    'total_time': sum(g.duration_minutes for g in day_tasks),
                    'productive_time': sum(g.duration_minutes for g in day_tasks if g.category in ['Development', 'Productivity']),
                    'tasks_count': len(day_tasks),
                    'avg_task_duration': np.mean([g.duration_minutes for g in day_tasks]),
                    'peak_hour': max([g.start_time.hour for g in day_tasks], key=lambda h: sum(g.duration_minutes for g in day_tasks if g.start_time.hour == h)),
                }
                daily_data.append(day_analysis)
                
            current_date += timedelta(days=1)
            
        if not daily_data:
            return None
            
        df = pd.DataFrame(daily_data)
        
        # Apply smoothing
        df['total_time_smooth'] = df['total_time'].rolling(window=smoothing_window, center=True).mean()
        df['productive_time_smooth'] = df['productive_time'].rolling(window=smoothing_window, center=True).mean()
        
        # Detect patterns
        patterns = {
            'weekly_pattern': self._detect_weekly_pattern(df),
            'trend_direction': self._detect_trend(df),
            'anomalies': self._detect_anomalies(df),
            'correlations': self._find_correlations(df),
        }
        
        return df, patterns
        
    def _detect_weekly_pattern(self, df):
        """Detect weekly productivity patterns."""
        df['weekday'] = df['date'].dt.day_name()
        weekly_avg = df.groupby('weekday')['productive_time'].mean()
        
        return {
            'most_productive_day': weekly_avg.idxmax(),
            'least_productive_day': weekly_avg.idxmin(),
            'weekend_vs_weekday': weekly_avg[['Saturday', 'Sunday']].mean() / weekly_avg[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']].mean()
        }
        
    def _detect_trend(self, df):
        """Detect productivity trend."""
        if len(df) < 3:
            return 'insufficient_data'
            
        x = np.arange(len(df))
        y = df['productive_time'].values
        
        # Linear regression
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 5:
            return 'improving'
        elif slope < -5:
            return 'declining'
        else:
            return 'stable'
            
    def _detect_anomalies(self, df):
        """Detect anomalous days."""
        if len(df) < 7:
            return []
            
        # Use Z-score to detect anomalies
        z_scores = np.abs((df['productive_time'] - df['productive_time'].mean()) / df['productive_time'].std())
        anomalies = df[z_scores > 2].copy()
        
        return anomalies[['date', 'productive_time']].to_dict('records')
        
    def _find_correlations(self, df):
        """Find correlations between metrics."""
        correlations = df[['total_time', 'productive_time', 'tasks_count', 'avg_task_duration']].corr()
        
        # Find strongest correlations
        strong_correlations = []
        for i, col1 in enumerate(correlations.columns):
            for j, col2 in enumerate(correlations.columns):
                if i < j:  # Avoid duplicates
                    corr_value = correlations.iloc[i, j]
                    if abs(corr_value) > 0.5:
                        strong_correlations.append({
                            'metric1': col1,
                            'metric2': col2,
                            'correlation': corr_value
                        })
                        
        return strong_correlations
        
    def render_productivity_analysis(self, analysis, ai_insights):
        """Render productivity analysis section."""
        if not analysis:
            NoDataMessage.render("No productivity data available")
            return
            
        st.subheader("🎯 Productivity Analysis")
        
        # Main metrics
        MetricsRow.render({
            "Efficiency Score": f"{analysis['efficiency_score']:.1f}/100",
            "Productivity Rate": f"{analysis['productivity_rate']:.1f}%",
            "Focus Sessions": analysis['focus_sessions'],
            "Context Switches": analysis['context_switches']
        })
        
        # Productivity gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = analysis['efficiency_score'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Efficiency Score"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # AI Insights
        if ai_insights:
            self.render_ai_insights(analysis)
            
    def render_pattern_analysis(self, df, patterns, ai_insights):
        """Render pattern analysis section."""
        if df is None:
            NoDataMessage.render("No pattern data available")
            return
            
        st.subheader("📈 Pattern Analysis")
        
        # Trend visualization
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Productivity Trend', 'Task Volume'),
            vertical_spacing=0.1
        )
        
        # Productivity trend
        fig.add_trace(
            go.Scatter(
                x=df['date'], 
                y=df['productive_time'],
                mode='lines+markers',
                name='Daily Productive Time',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'], 
                y=df['productive_time_smooth'],
                mode='lines',
                name='Smoothed Trend',
                line=dict(color='red', width=3)
            ),
            row=1, col=1
        )
        
        # Task volume
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['tasks_count'],
                name='Daily Tasks',
                marker_color='lightblue'
            ),
            row=2, col=1
        )
        
        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # Pattern insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔍 Detected Patterns")
            st.write(f"**Trend**: {patterns['trend_direction'].replace('_', ' ').title()}")
            st.write(f"**Most Productive Day**: {patterns['weekly_pattern']['most_productive_day']}")
            st.write(f"**Least Productive Day**: {patterns['weekly_pattern']['least_productive_day']}")
            
        with col2:
            st.markdown("### ⚠️ Anomalies")
            if patterns['anomalies']:
                for anomaly in patterns['anomalies'][:3]:
                    date_str = anomaly['date'].strftime('%Y-%m-%d')
                    st.write(f"**{date_str}**: {anomaly['productive_time']:.1f} min")
            else:
                st.write("No significant anomalies detected")
                
    def render_ai_insights(self, analysis):
        """Render AI-powered insights and recommendations."""
        st.subheader("🤖 AI Insights & Recommendations")
        
        insights = []
        
        # Efficiency insights
        if analysis['efficiency_score'] < 50:
            insights.append({
                'type': 'warning',
                'title': 'Low Efficiency Detected',
                'message': f"Your efficiency score is {analysis['efficiency_score']:.1f}/100. Consider reducing context switches and focusing on longer work sessions.",
                'action': 'Try the Pomodoro Technique (25-minute focused sessions)'
            })
        elif analysis['efficiency_score'] > 80:
            insights.append({
                'type': 'success',
                'title': 'Excellent Efficiency!',
                'message': f"Your efficiency score of {analysis['efficiency_score']:.1f}/100 is excellent. Keep up the great work!",
                'action': 'Maintain your current productivity patterns'
            })
            
        # Context switching insights
        if analysis['context_switches'] > 20:
            insights.append({
                'type': 'warning',
                'title': 'High Context Switching',
                'message': f"You switched contexts {analysis['context_switches']} times. This can reduce productivity.",
                'action': 'Try batching similar tasks together'
            })
            
        # Focus session insights
        if analysis['focus_sessions'] == 0:
            insights.append({
                'type': 'info',
                'title': 'No Deep Focus Sessions',
                'message': "No sessions longer than 25 minutes detected. Deep work is crucial for productivity.",
                'action': 'Schedule dedicated focus blocks in your calendar'
            })
            
        # Peak hours insights
        if analysis['peak_productivity_hours']:
            hours_str = ', '.join([f"{h:02d}:00" for h in analysis['peak_productivity_hours']])
            insights.append({
                'type': 'info',
                'title': 'Peak Productivity Hours',
                'message': f"You're most productive at: {hours_str}",
                'action': 'Schedule your most important work during these hours'
            })
            
        # Display insights
        for insight in insights:
            if insight['type'] == 'warning':
                st.warning(f"**{insight['title']}**\n\n{insight['message']}\n\n💡 **Recommendation**: {insight['action']}")
            elif insight['type'] == 'success':
                st.success(f"**{insight['title']}**\n\n{insight['message']}\n\n✅ **Keep it up**: {insight['action']}")
            else:
                st.info(f"**{insight['title']}**\n\n{insight['message']}\n\n💡 **Suggestion**: {insight['action']}")
                
    def export_analysis_report(self, analysis_type, time_filter):
        """Export comprehensive analysis report."""
        st.info("Analysis report export functionality would be implemented here")
        # This would generate a PDF or detailed CSV report
        
    def run(self):
        """Main dashboard execution."""
        if not self.ensure_connection():
            return
            
        # Header
        st.title("🧠 Advanced Analytics")
        st.markdown("Deep insights into your productivity patterns and behaviors")
        
        # Render sidebar and get settings
        analysis_type, time_filter, comparison_mode, ai_insights, confidence_threshold, smoothing_window = self.render_sidebar()
        
        # Get time range
        start_date, end_date = TimeFilterComponent.get_time_range(time_filter)
        
        # Main content based on analysis type
        if analysis_type == 'productivity':
            analysis = self.get_productivity_analysis(start_date, end_date, confidence_threshold)
            self.render_productivity_analysis(analysis, ai_insights)
            
        elif analysis_type == 'patterns':
            df, patterns = self.get_pattern_analysis(start_date, end_date, smoothing_window)
            self.render_pattern_analysis(df, patterns, ai_insights)
            
        elif analysis_type == 'predictions':
            st.subheader("🔮 Predictive Analytics")
            st.info("Predictive analytics features coming soon! This would include productivity forecasting and trend predictions.")
            
        elif analysis_type == 'comparisons':
            st.subheader("⚖️ Comparative Analytics")
            st.info("Comparative analytics features coming soon! This would include period-over-period comparisons and benchmarking.")


def main():
    """Run the advanced analytics dashboard."""
    dashboard = AdvancedAnalyticsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()