"""Smart defaults component for intelligent parameter selection."""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime, timedelta
import logging

from .base_component import StatelessComponent
from autotasktracker.core import DatabaseManager

logger = logging.getLogger(__name__)


class SmartDefaultsComponent(StatelessComponent):
    """Component for providing intelligent default values based on data analysis."""
    
    @staticmethod
    def get_time_period_default(db_manager: Optional[DatabaseManager] = None) -> str:
        """Get smart default time period based on data availability.
        
        Args:
            db_manager: Database manager for data analysis
            
        Returns:
            Optimal time period string
        """
        if db_manager is None:
            return "Last 7 Days"
        
        try:
            now = datetime.now()
            
            # Define time periods to check
            time_periods = [
                ("Today", now.replace(hour=0, minute=0, second=0, microsecond=0), now),
                ("Yesterday", 
                 (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                 (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)),
                ("Last 7 Days", now - timedelta(days=7), now),
                ("Last 30 Days", now - timedelta(days=30), now),
                ("Last 90 Days", now - timedelta(days=90), now)
            ]
            
            # Analyze data availability and quality for each period
            period_analysis = []
            for period_name, start_date, end_date in time_periods:
                try:
                    tasks_df = db_manager.fetch_tasks(
                        start_date=start_date, 
                        end_date=end_date, 
                        limit=100
                    )
                    
                    # Calculate score based on multiple factors
                    task_count = len(tasks_df)
                    recency_factor = SmartDefaultsComponent._calculate_recency_factor(period_name)
                    diversity_factor = SmartDefaultsComponent._calculate_diversity_factor(tasks_df)
                    
                    score = (task_count * 0.5 + diversity_factor * 30 + recency_factor * 20)
                    
                    period_analysis.append({
                        'period': period_name,
                        'score': score,
                        'task_count': task_count,
                        'has_minimum_data': task_count >= 5
                    })
                except Exception as e:
                    logger.warning(f"Error analyzing period {period_name}: {e}")
                    period_analysis.append({
                        'period': period_name,
                        'score': 0,
                        'task_count': 0,
                        'has_minimum_data': False
                    })
            
            # Select best period
            valid_periods = [p for p in period_analysis if p['has_minimum_data']]
            if valid_periods:
                best_period = max(valid_periods, key=lambda x: x['score'])
                return best_period['period']
            
            # If no period has enough data, default to Last 7 Days
            return "Last 7 Days"
            
        except Exception as e:
            logger.error(f"Error in smart time period detection: {e}")
            return "Last 7 Days"
    
    @staticmethod
    def _calculate_recency_factor(period_name: str) -> float:
        """Calculate recency factor for scoring."""
        recency_weights = {
            "Today": 1.0,
            "Yesterday": 0.9,
            "Last 7 Days": 0.7,
            "Last 30 Days": 0.5,
            "Last 90 Days": 0.3
        }
        return recency_weights.get(period_name, 0.5)
    
    @staticmethod
    def _calculate_diversity_factor(tasks_df: pd.DataFrame) -> float:
        """Calculate diversity factor based on task variety."""
        if tasks_df.empty:
            return 0.0
        
        try:
            # Check variety in window titles
            unique_windows = tasks_df['window_title'].nunique() if 'window_title' in tasks_df.columns else 0
            # Check variety in apps
            unique_apps = tasks_df['extracted_app'].nunique() if 'extracted_app' in tasks_df.columns else 0
            
            # Normalize to 0-1 range
            window_diversity = min(unique_windows / 10, 1.0)
            app_diversity = min(unique_apps / 5, 1.0)
            
            return (window_diversity + app_diversity) / 2
        except Exception as e:
            logger.warning(f"Error calculating diversity factor: {e}")
            return 0.5
    
    @staticmethod
    def get_category_defaults(
        db_manager: Optional[DatabaseManager] = None,
        time_period: Optional[str] = None
    ) -> List[str]:
        """Get smart default categories based on recent activity.
        
        Args:
            db_manager: Database manager
            time_period: Time period to analyze
            
        Returns:
            List of recommended categories
        """
        if db_manager is None:
            return []
        
        try:
            # Parse time period
            start_date, end_date = SmartDefaultsComponent._parse_time_period(time_period)
            
            # Fetch recent tasks
            tasks_df = db_manager.fetch_tasks(
                start_date=start_date,
                end_date=end_date,
                limit=500
            )
            
            if tasks_df.empty:
                return []
            
            # Analyze most active categories
            if 'extracted_category' in tasks_df.columns:
                category_counts = tasks_df['extracted_category'].value_counts()
                
                # Select top categories that represent at least 10% of activity
                total_tasks = len(tasks_df)
                significant_categories = []
                
                for category, count in category_counts.items():
                    if count / total_tasks >= 0.1 and category:
                        significant_categories.append(category)
                    if len(significant_categories) >= 3:  # Limit to top 3
                        break
                
                return significant_categories
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting category defaults: {e}")
            return []
    
    @staticmethod
    def _parse_time_period(period: Optional[str]) -> Tuple[datetime, datetime]:
        """Parse time period string to datetime range."""
        now = datetime.now()
        
        if period == "Today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "Yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
        elif period == "Last 7 Days":
            start = now - timedelta(days=7)
            end = now
        elif period == "Last 30 Days":
            start = now - timedelta(days=30)
            end = now
        elif period == "Last 90 Days":
            start = now - timedelta(days=90)
            end = now
        else:
            # Default to last 7 days
            start = now - timedelta(days=7)
            end = now
        
        return start, end
    
    @staticmethod
    def render_smart_defaults_button(
        db_manager: Optional[DatabaseManager] = None,
        apply_callback: Optional[Callable] = None,
        show_explanation: bool = True,
        button_label: str = "🎯 Smart Defaults",
        button_help: str = "Apply intelligent defaults based on your data"
    ):
        """Render smart defaults button with optional explanation.
        
        Args:
            db_manager: Database manager for analysis
            apply_callback: Callback to apply defaults
            show_explanation: Whether to show explanation of selections
            button_label: Custom button label
            button_help: Custom button help text
        """
        if st.button(button_label, help=button_help):
            # Get smart defaults
            time_period = SmartDefaultsComponent.get_time_period_default(db_manager)
            categories = SmartDefaultsComponent.get_category_defaults(db_manager, time_period)
            
            # Create defaults dict
            defaults = {
                'time_period': time_period,
                'categories': categories,
                'timestamp': datetime.now()
            }
            
            # Apply defaults
            if apply_callback:
                apply_callback(defaults)
            else:
                # Default behavior - update session state
                st.session_state.time_filter = time_period
                if categories:
                    st.session_state.category_filter = categories
            
            # Show explanation if enabled
            if show_explanation:
                with st.expander("📊 Smart Defaults Applied", expanded=True):
                    st.write(f"**Time Period:** {time_period}")
                    if categories:
                        st.write(f"**Active Categories:** {', '.join(categories)}")
                    st.caption("Based on your recent activity patterns")
            
            st.rerun()
    
    @staticmethod
    def get_smart_defaults_info(
        db_manager: Optional[DatabaseManager] = None
    ) -> Dict[str, Any]:
        """Get comprehensive smart defaults information.
        
        Args:
            db_manager: Database manager
            
        Returns:
            Dictionary with all smart default recommendations
        """
        try:
            time_period = SmartDefaultsComponent.get_time_period_default(db_manager)
            categories = SmartDefaultsComponent.get_category_defaults(db_manager, time_period)
            
            # Additional analysis
            start_date, end_date = SmartDefaultsComponent._parse_time_period(time_period)
            
            info = {
                'time_period': time_period,
                'categories': categories,
                'reasoning': SmartDefaultsComponent._generate_reasoning(
                    db_manager, time_period, categories
                ),
                'data_summary': SmartDefaultsComponent._get_data_summary(
                    db_manager, start_date, end_date
                )
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting smart defaults info: {e}")
            return {
                'time_period': 'Last 7 Days',
                'categories': [],
                'reasoning': 'Using safe defaults',
                'data_summary': {}
            }
    
    @staticmethod
    def _generate_reasoning(
        db_manager: Optional[DatabaseManager],
        time_period: str,
        categories: List[str]
    ) -> str:
        """Generate human-readable reasoning for selections."""
        reasons = []
        
        if time_period == "Today":
            reasons.append("Focusing on today's activity for real-time insights")
        elif time_period == "Yesterday":
            reasons.append("Yesterday has the most complete recent data")
        elif time_period == "Last 7 Days":
            reasons.append("Last 7 days provides a balanced view of recent activity")
        elif time_period == "Last 30 Days":
            reasons.append("Last 30 days shows longer-term patterns")
        
        if categories:
            reasons.append(f"Selected {len(categories)} most active categories")
        
        return ". ".join(reasons)
    
    @staticmethod
    def _get_data_summary(
        db_manager: Optional[DatabaseManager],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get summary statistics for the period."""
        try:
            tasks_df = db_manager.fetch_tasks(
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            return {
                'total_tasks': len(tasks_df),
                'unique_apps': tasks_df['extracted_app'].nunique() if 'extracted_app' in tasks_df.columns else 0,
                'unique_categories': tasks_df['extracted_category'].nunique() if 'extracted_category' in tasks_df.columns else 0,
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }
        except Exception as e:
            logger.warning(f"Error getting data summary: {e}")
            return {'total_tasks': 0}