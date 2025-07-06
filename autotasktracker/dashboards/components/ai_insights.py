"""AI Insights display component for dashboards."""

from typing import List, Dict, Any, Optional, Union, Tuple
import streamlit as st
from datetime import datetime
import logging
from enum import Enum

from .base_component import StatelessComponent

logger = logging.getLogger(__name__)


class InsightType(Enum):
    """Types of insights."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    RECOMMENDATION = "recommendation"
    PATTERN = "pattern"
    ANOMALY = "anomaly"


class InsightPriority(Enum):
    """Priority levels for insights."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AIInsightsComponent(StatelessComponent):
    """Component for displaying AI-generated insights and recommendations."""
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "show_timestamp": True,
            "show_priority": True,
            "show_category": True,
            "expandable": True,
            "max_insights": 10,
            "group_by_category": False,
            "show_confidence": True,
            "enable_actions": True,
            "icons": {
                InsightType.INFO: "ℹ️",
                InsightType.SUCCESS: "✅",
                InsightType.WARNING: "⚠️",
                InsightType.ERROR: "❌",
                InsightType.RECOMMENDATION: "💡",
                InsightType.PATTERN: "📊",
                InsightType.ANOMALY: "🔍"
            },
            "priority_colors": {
                InsightPriority.HIGH: "#ff4b4b",
                InsightPriority.MEDIUM: "#ffa724",
                InsightPriority.LOW: "#0068c9"
            }
        }
    
    def render(self, data: Any, **kwargs) -> None:
        """Render method not used for static component."""
        pass
    
    @staticmethod
    def render_insights(
        insights: List[Dict[str, Any]],
        title: str = "AI Insights",
        config: Optional[Dict[str, Any]] = None,
        container=None
    ) -> None:
        """Render a list of AI insights.
        
        Args:
            insights: List of insight dictionaries with keys:
                - content: The insight text
                - type: InsightType enum value
                - priority: InsightPriority enum value (optional)
                - category: Category string (optional)
                - confidence: Confidence score 0-1 (optional)
                - metadata: Additional metadata dict (optional)
                - actions: List of action buttons (optional)
            title: Section title
            config: Configuration overrides
            container: Streamlit container to render in
        """
        # Merge configuration
        display_config = AIInsightsComponent.get_default_config()
        if config:
            display_config.update(config)
        
        # Use provided container or current position
        target = container or st
        
        if not insights:
            target.info("No insights available at this time.")
            return
        
        # Display title
        target.subheader(title)
        
        # Filter and sort insights
        processed_insights = AIInsightsComponent._process_insights(
            insights, display_config
        )
        
        # Group by category if enabled
        if display_config["group_by_category"]:
            AIInsightsComponent._render_grouped_insights(
                target, processed_insights, display_config
            )
        else:
            AIInsightsComponent._render_flat_insights(
                target, processed_insights, display_config
            )
    
    @staticmethod
    def render_recommendations(
        recommendations: List[Dict[str, Any]],
        title: str = "Recommendations",
        show_impact: bool = True,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Render AI recommendations in a structured format.
        
        Args:
            recommendations: List of recommendation dicts with:
                - title: Recommendation title
                - description: Detailed description
                - impact: Expected impact (high/medium/low)
                - effort: Implementation effort (high/medium/low)
                - actions: List of action items
            title: Section title
            show_impact: Show impact/effort matrix
            config: Configuration overrides
        """
        if not recommendations:
            st.info("No recommendations available.")
            return
        
        st.subheader(title)
        
        if show_impact:
            # Create impact/effort matrix
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Impact vs Effort")
                # Simple text-based matrix
                for rec in recommendations:
                    impact = rec.get("impact", "medium")
                    effort = rec.get("effort", "medium")
                    emoji = AIInsightsComponent._get_impact_emoji(impact, effort)
                    st.write(f"{emoji} {rec['title'][:30]}...")
            
            with col2:
                st.markdown("### Details")
                selected_rec = st.selectbox(
                    "Select recommendation",
                    recommendations,
                    format_func=lambda x: x["title"],
                    label_visibility="collapsed"
                )
                
                if selected_rec:
                    AIInsightsComponent._render_recommendation_detail(selected_rec)
        else:
            # Render all recommendations
            for rec in recommendations:
                with st.expander(f"💡 {rec['title']}", expanded=False):
                    AIInsightsComponent._render_recommendation_detail(rec)
    
    @staticmethod
    def render_pattern_analysis(
        patterns: List[Dict[str, Any]],
        title: str = "Pattern Analysis",
        show_visualizations: bool = True
    ) -> None:
        """Render detected patterns with optional visualizations.
        
        Args:
            patterns: List of pattern dicts with:
                - name: Pattern name
                - description: Pattern description
                - confidence: Detection confidence
                - data: Pattern data for visualization
                - trend: Trend direction (up/down/stable)
            title: Section title
            show_visualizations: Show pattern visualizations
        """
        if not patterns:
            return
        
        st.subheader(title)
        
        # Sort by confidence
        sorted_patterns = sorted(
            patterns,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        
        for pattern in sorted_patterns:
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{pattern['name']}**")
                st.caption(pattern['description'])
            
            with col2:
                confidence = pattern.get("confidence", 0)
                st.metric("Confidence", f"{confidence:.0%}")
            
            with col3:
                trend = pattern.get("trend", "stable")
                trend_icon = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend, "")
                st.metric("Trend", trend_icon)
            
            if show_visualizations and "data" in pattern:
                # Placeholder for pattern visualization
                st.caption("Pattern visualization would appear here")
    
    @staticmethod
    def render_insight_summary(
        insights: List[Dict[str, Any]],
        title: str = "Insight Summary",
        show_stats: bool = True
    ) -> None:
        """Render a summary of insights with statistics.
        
        Args:
            insights: List of insights
            title: Summary title
            show_stats: Show insight statistics
        """
        if not insights:
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Count by type
        type_counts = {}
        priority_counts = {}
        
        for insight in insights:
            insight_type = insight.get("type", InsightType.INFO)
            type_counts[insight_type] = type_counts.get(insight_type, 0) + 1
            
            priority = insight.get("priority", InsightPriority.MEDIUM)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        with col1:
            st.metric("Total Insights", len(insights))
        
        with col2:
            high_priority = priority_counts.get(InsightPriority.HIGH, 0)
            st.metric("High Priority", high_priority)
        
        with col3:
            warnings = type_counts.get(InsightType.WARNING, 0)
            st.metric("Warnings", warnings)
        
        with col4:
            recommendations = type_counts.get(InsightType.RECOMMENDATION, 0)
            st.metric("Recommendations", recommendations)
    
    # Helper methods
    @staticmethod
    def _process_insights(
        insights: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process and filter insights."""
        # Limit number of insights
        processed = insights[:config["max_insights"]]
        
        # Sort by priority
        priority_order = {
            InsightPriority.HIGH: 0,
            InsightPriority.MEDIUM: 1,
            InsightPriority.LOW: 2
        }
        
        processed.sort(
            key=lambda x: priority_order.get(x.get("priority", InsightPriority.MEDIUM), 1)
        )
        
        return processed
    
    @staticmethod
    def _render_flat_insights(
        container,
        insights: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> None:
        """Render insights in a flat list."""
        for insight in insights:
            AIInsightsComponent._render_single_insight(container, insight, config)
    
    @staticmethod
    def _render_grouped_insights(
        container,
        insights: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> None:
        """Render insights grouped by category."""
        # Group by category
        grouped = {}
        for insight in insights:
            category = insight.get("category", "General")
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(insight)
        
        # Render each group
        for category, category_insights in grouped.items():
            with container.expander(f"{category} ({len(category_insights)})", expanded=True):
                for insight in category_insights:
                    AIInsightsComponent._render_single_insight(st, insight, config)
    
    @staticmethod
    def _render_single_insight(
        container,
        insight: Dict[str, Any],
        config: Dict[str, Any]
    ) -> None:
        """Render a single insight."""
        insight_type = insight.get("type", InsightType.INFO)
        icon = config["icons"].get(insight_type, "ℹ️")
        
        # Build insight header
        header_parts = [f"{icon} **{insight['content']}**"]
        
        if config["show_priority"] and "priority" in insight:
            priority = insight["priority"]
            color = config["priority_colors"].get(priority, "#000000")
            header_parts.append(f"<span style='color: {color}'>●</span>")
        
        if config["show_confidence"] and "confidence" in insight:
            confidence = insight["confidence"]
            header_parts.append(f"({confidence:.0%} confidence)")
        
        # Render insight
        if config["expandable"] and "metadata" in insight:
            with container.expander(" ".join(header_parts), expanded=False):
                AIInsightsComponent._render_insight_details(insight, config)
        else:
            container.markdown(" ".join(header_parts), unsafe_allow_html=True)
            
            # Render actions if available
            if config["enable_actions"] and "actions" in insight:
                AIInsightsComponent._render_insight_actions(container, insight["actions"])
    
    @staticmethod
    def _render_insight_details(insight: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Render detailed insight information."""
        metadata = insight.get("metadata", {})
        
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                st.json(value)
            else:
                st.write(f"**{key}**: {value}")
        
        if config["show_timestamp"] and "timestamp" in insight:
            st.caption(f"Generated: {insight['timestamp']}")
    
    @staticmethod
    def _render_insight_actions(container, actions: List[Dict[str, Any]]) -> None:
        """Render action buttons for an insight."""
        cols = container.columns(len(actions))
        
        for col, action in zip(cols, actions):
            with col:
                if st.button(
                    action.get("label", "Action"),
                    key=action.get("key"),
                    help=action.get("help")
                ):
                    # Action callback would be handled by parent
                    st.session_state[f"action_{action.get('key')}"] = True
    
    @staticmethod
    def _render_recommendation_detail(recommendation: Dict[str, Any]) -> None:
        """Render detailed recommendation information."""
        st.markdown(recommendation["description"])
        
        if "actions" in recommendation:
            st.markdown("**Action Items:**")
            for i, action in enumerate(recommendation["actions"], 1):
                st.write(f"{i}. {action}")
        
        if "impact" in recommendation and "effort" in recommendation:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Expected Impact", recommendation["impact"].title())
            with col2:
                st.metric("Implementation Effort", recommendation["effort"].title())
    
    @staticmethod
    def _get_impact_emoji(impact: str, effort: str) -> str:
        """Get emoji for impact/effort combination."""
        matrix = {
            ("high", "low"): "🎯",    # High impact, low effort - Quick win
            ("high", "medium"): "⭐",  # High impact, medium effort - Strategic
            ("high", "high"): "🏔️",   # High impact, high effort - Major project
            ("medium", "low"): "✅",   # Medium impact, low effort - Good to have
            ("medium", "medium"): "📊", # Medium impact, medium effort - Standard
            ("medium", "high"): "🤔",  # Medium impact, high effort - Question value
            ("low", "low"): "🔧",      # Low impact, low effort - Fill time
            ("low", "medium"): "📝",   # Low impact, medium effort - Maybe later
            ("low", "high"): "❌"      # Low impact, high effort - Avoid
        }
        return matrix.get((impact, effort), "📌")