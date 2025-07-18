"""Reusable UI components for dashboards."""

from .filters import TimeFilterComponent, CategoryFilterComponent
from .metrics import MetricsCard, MetricsRow
from .data_display import TaskGroup, ActivityCard, NoDataMessage, DataTable, EnhancedSearch
from .ai_task_display import AITaskDisplay
from .visualizations import (
    CategoryPieChart, TimelineChart, HourlyActivityChart,
    ProductivityHeatmap, TaskDurationChart, TrendChart, ComparisonChart
)
from .base_component import BaseComponent, StatelessComponent
from .export import ExportComponent
from .realtime_status import RealtimeStatusComponent
from .task_summary_table import TaskSummaryTable
from .ai_insights import AIInsightsComponent, InsightType, InsightPriority
from .timetracker_components import TimeTrackerTimeline, TimeTrackerMetrics, TimeTrackerTaskList
from .vlm_components import (
    VLMCoverageGauge, VLMSystemStatus, VLMProcessingTimeline,
    VLMRecentResults, VLMHourlyChart, VLMConfigDisplay
)
from .realtime_components import (
    RealtimeMetricsRow, LiveActivityFeed, SmartSearchInterface,
    SystemStatusDisplay, PerformanceMetricsDisplay, EventProcessorControl
)
from .dashboard_header import DashboardHeader
from .raw_data_viewer import RawDataViewer
from .period_stats import PeriodStats
from .session_controls import SessionControlsComponent
from .smart_defaults import SmartDefaultsComponent
from .timeline_visualization import TimelineVisualizationComponent
from .session_insights import SessionInsightsComponent, WorkflowVisualizationComponent

__all__ = [
    'TimeFilterComponent',
    'CategoryFilterComponent', 
    'MetricsCard',
    'MetricsRow',
    'TaskGroup',
    'ActivityCard',
    'NoDataMessage',
    'DataTable',
    'EnhancedSearch',
    'AITaskDisplay',
    'CategoryPieChart',
    'TimelineChart', 
    'HourlyActivityChart',
    'ProductivityHeatmap',
    'TaskDurationChart',
    'TrendChart',
    'ComparisonChart',
    'BaseComponent',
    'StatelessComponent',
    'ExportComponent',
    'RealtimeStatusComponent',
    'TaskSummaryTable',
    'AIInsightsComponent',
    'InsightType',
    'InsightPriority',
    'TimeTrackerTimeline',
    'TimeTrackerMetrics',
    'TimeTrackerTaskList',
    'VLMCoverageGauge',
    'VLMSystemStatus',
    'VLMProcessingTimeline',
    'VLMRecentResults',
    'VLMHourlyChart',
    'VLMConfigDisplay',
    'RealtimeMetricsRow',
    'LiveActivityFeed',
    'SmartSearchInterface',
    'SystemStatusDisplay',
    'PerformanceMetricsDisplay',
    'EventProcessorControl',
    'DashboardHeader',
    'RawDataViewer',
    'PeriodStats',
    'SessionControlsComponent',
    'SmartDefaultsComponent',
    'TimelineVisualizationComponent',
    'SessionInsightsComponent',
    'WorkflowVisualizationComponent'
]