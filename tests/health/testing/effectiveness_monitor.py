"""Real-time monitoring for mutation testing effectiveness.

This module provides monitoring capabilities to track the effectiveness
of mutation testing over time and identify trends in test quality.
"""

import asyncio
import json
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set
import sqlite3

from .constants import EffectivenessThresholds

logger = logging.getLogger(__name__)


@dataclass
class EffectivenessMetric:
    """Single effectiveness measurement."""
    
    timestamp: datetime
    test_file: str
    source_file: str
    effectiveness_percentage: float
    mutations_total: int
    mutations_caught: int
    mutations_missed: int
    execution_time: float
    mutation_types: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class EffectivenessTrend:
    """Trend analysis for effectiveness over time."""
    
    period_start: datetime
    period_end: datetime
    average_effectiveness: float
    total_tests: int
    total_mutations: int
    improvement_rate: float  # Percentage change from previous period
    quality_category: str  # excellent, good, moderate, poor
    top_performing_files: List[str] = field(default_factory=list)
    underperforming_files: List[str] = field(default_factory=list)


class EffectivenessMonitor:
    """Real-time monitor for mutation testing effectiveness."""
    
    def __init__(self, 
                 project_root: Path,
                 db_path: Optional[Path] = None,
                 max_history_days: int = 30):
        self.project_root = project_root
        self.db_path = db_path or (project_root / ".autotask" / "effectiveness.db")
        self.max_history_days = max_history_days
        
        # In-memory metrics for real-time monitoring
        self.recent_metrics: deque = deque(maxlen=1000)
        self.live_stats = {
            'total_tests_today': 0,
            'average_effectiveness_today': 0.0,
            'tests_this_hour': 0,
            'current_trend': 'stable'
        }
        
        # Thresholds for categorization
        self.thresholds = EffectivenessThresholds()
        
        # Event callbacks
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Background monitoring
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize the monitoring database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS effectiveness_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    test_file TEXT NOT NULL,
                    source_file TEXT,
                    effectiveness_percentage REAL NOT NULL,
                    mutations_total INTEGER NOT NULL,
                    mutations_caught INTEGER NOT NULL,
                    mutations_missed INTEGER NOT NULL,
                    execution_time REAL NOT NULL,
                    mutation_types TEXT,  -- JSON array
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_effectiveness_timestamp 
                ON effectiveness_metrics(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_effectiveness_file 
                ON effectiveness_metrics(test_file)
            """)
    
    def record_effectiveness(self, metric: EffectivenessMetric):
        """Record a new effectiveness measurement."""
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO effectiveness_metrics 
                (timestamp, test_file, source_file, effectiveness_percentage,
                 mutations_total, mutations_caught, mutations_missed, 
                 execution_time, mutation_types, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.test_file,
                metric.source_file,
                metric.effectiveness_percentage,
                metric.mutations_total,
                metric.mutations_caught,
                metric.mutations_missed,
                metric.execution_time,
                json.dumps(metric.mutation_types),
                metric.error_message
            ))
        
        # Update in-memory metrics
        self.recent_metrics.append(metric)
        self._update_live_stats(metric)
        
        # Trigger callbacks
        self._trigger_callbacks('effectiveness_recorded', metric)
        
        # Check for alerts
        self._check_alerts(metric)
    
    def _update_live_stats(self, metric: EffectivenessMetric):
        """Update live statistics."""
        today = datetime.now().date()
        
        if metric.timestamp.date() == today:
            self.live_stats['total_tests_today'] += 1
            
            # Update today's average
            current_avg = self.live_stats['average_effectiveness_today']
            total_tests = self.live_stats['total_tests_today']
            
            new_avg = ((current_avg * (total_tests - 1)) + metric.effectiveness_percentage) / total_tests
            self.live_stats['average_effectiveness_today'] = new_avg
        
        # Update hourly count
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        recent_this_hour = [m for m in self.recent_metrics 
                           if m.timestamp >= hour_ago]
        self.live_stats['tests_this_hour'] = len(recent_this_hour)
        
        # Update trend
        self._update_trend()
    
    def _update_trend(self):
        """Update the current effectiveness trend."""
        if len(self.recent_metrics) < 10:
            self.live_stats['current_trend'] = 'insufficient_data'
            return
        
        # Compare recent vs earlier effectiveness
        recent_10 = list(self.recent_metrics)[-10:]
        earlier_10 = list(self.recent_metrics)[-20:-10] if len(self.recent_metrics) >= 20 else []
        
        if not earlier_10:
            self.live_stats['current_trend'] = 'stable'
            return
        
        recent_avg = sum(m.effectiveness_percentage for m in recent_10) / len(recent_10)
        earlier_avg = sum(m.effectiveness_percentage for m in earlier_10) / len(earlier_10)
        
        improvement = recent_avg - earlier_avg
        
        if improvement > 5:
            self.live_stats['current_trend'] = 'improving'
        elif improvement < -5:
            self.live_stats['current_trend'] = 'declining'
        else:
            self.live_stats['current_trend'] = 'stable'
    
    def _check_alerts(self, metric: EffectivenessMetric):
        """Check if alerts should be triggered."""
        # Low effectiveness alert
        if metric.effectiveness_percentage < self.thresholds.POOR:
            self._trigger_callbacks('low_effectiveness_alert', {
                'metric': metric,
                'threshold': self.thresholds.POOR,
                'severity': 'high'
            })
        
        # Zero effectiveness alert (critical)
        if metric.effectiveness_percentage == 0:
            self._trigger_callbacks('zero_effectiveness_alert', {
                'metric': metric,
                'severity': 'critical'
            })
        
        # Error alert
        if metric.error_message:
            self._trigger_callbacks('error_alert', {
                'metric': metric,
                'error': metric.error_message,
                'severity': 'medium'
            })
        
        # Trend decline alert
        if self.live_stats['current_trend'] == 'declining':
            recent_count = len([m for m in self.recent_metrics 
                              if m.timestamp >= datetime.now() - timedelta(hours=1)])
            if recent_count >= 5:  # Only alert if we have sufficient recent data
                self._trigger_callbacks('trend_decline_alert', {
                    'trend': 'declining',
                    'recent_tests': recent_count,
                    'severity': 'medium'
                })
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for specific events.
        
        Event types:
        - effectiveness_recorded: New metric recorded
        - low_effectiveness_alert: Effectiveness below threshold
        - zero_effectiveness_alert: No mutations caught
        - error_alert: Error during testing
        - trend_decline_alert: Declining effectiveness trend
        """
        self.callbacks[event_type].append(callback)
    
    def _trigger_callbacks(self, event_type: str, data: Any):
        """Trigger all callbacks for an event type."""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {e}")
    
    def get_live_stats(self) -> Dict[str, Any]:
        """Get current live statistics."""
        return self.live_stats.copy()
    
    def get_effectiveness_trend(self, 
                                days: int = 7,
                                granularity: str = 'daily') -> List[EffectivenessTrend]:
        """Get effectiveness trends over time."""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, test_file, effectiveness_percentage, 
                       mutations_total, mutations_caught
                FROM effectiveness_metrics 
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            """, (start_time, end_time))
            
            rows = cursor.fetchall()
        
        if not rows:
            return []
        
        # Group by time period
        if granularity == 'daily':
            period_hours = 24
        elif granularity == 'hourly':
            period_hours = 1
        else:
            period_hours = 24
        
        trends = []
        current_period_start = start_time
        
        while current_period_start < end_time:
            period_end = current_period_start + timedelta(hours=period_hours)
            
            # Get metrics for this period
            period_metrics = [
                row for row in rows 
                if current_period_start <= datetime.fromisoformat(row[0]) < period_end
            ]
            
            if period_metrics:
                effectiveness_values = [row[2] for row in period_metrics]
                avg_effectiveness = sum(effectiveness_values) / len(effectiveness_values)
                
                # Categorize quality
                if avg_effectiveness >= self.thresholds.EXCELLENT:
                    quality = 'excellent'
                elif avg_effectiveness >= self.thresholds.GOOD:
                    quality = 'good'
                elif avg_effectiveness >= self.thresholds.MODERATE:
                    quality = 'moderate'
                else:
                    quality = 'poor'
                
                # Find top and under-performing files
                file_effectiveness = defaultdict(list)
                for row in period_metrics:
                    file_effectiveness[row[1]].append(row[2])
                
                file_averages = {
                    file: sum(values) / len(values) 
                    for file, values in file_effectiveness.items()
                }
                
                sorted_files = sorted(file_averages.items(), key=lambda x: x[1], reverse=True)
                top_files = [f[0] for f in sorted_files[:3]]
                under_files = [f[0] for f in sorted_files[-3:] if f[1] < self.thresholds.MODERATE]
                
                trend = EffectivenessTrend(
                    period_start=current_period_start,
                    period_end=period_end,
                    average_effectiveness=avg_effectiveness,
                    total_tests=len(period_metrics),
                    total_mutations=sum(row[3] for row in period_metrics),
                    improvement_rate=0.0,  # Calculate separately
                    quality_category=quality,
                    top_performing_files=top_files,
                    underperforming_files=under_files
                )
                
                trends.append(trend)
            
            current_period_start = period_end
        
        # Calculate improvement rates
        for i in range(1, len(trends)):
            prev_avg = trends[i-1].average_effectiveness
            curr_avg = trends[i].average_effectiveness
            if prev_avg > 0:
                improvement = ((curr_avg - prev_avg) / prev_avg) * 100
                trends[i].improvement_rate = improvement
        
        return trends
    
    def get_file_effectiveness_history(self, test_file: str, days: int = 30) -> List[EffectivenessMetric]:
        """Get effectiveness history for a specific test file."""
        start_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, test_file, source_file, effectiveness_percentage,
                       mutations_total, mutations_caught, mutations_missed,
                       execution_time, mutation_types, error_message
                FROM effectiveness_metrics 
                WHERE test_file = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (test_file, start_time))
            
            rows = cursor.fetchall()
        
        metrics = []
        for row in rows:
            mutation_types = json.loads(row[8]) if row[8] else []
            metric = EffectivenessMetric(
                timestamp=datetime.fromisoformat(row[0]),
                test_file=row[1],
                source_file=row[2],
                effectiveness_percentage=row[3],
                mutations_total=row[4],
                mutations_caught=row[5],
                mutations_missed=row[6],
                execution_time=row[7],
                mutation_types=mutation_types,
                error_message=row[9]
            )
            metrics.append(metric)
        
        return metrics
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Generate a comprehensive effectiveness summary."""
        with sqlite3.connect(self.db_path) as conn:
            # Overall stats
            cursor = conn.execute("""
                SELECT COUNT(*), AVG(effectiveness_percentage), 
                       SUM(mutations_total), SUM(mutations_caught)
                FROM effectiveness_metrics 
                WHERE timestamp >= datetime('now', '-7 days')
            """)
            total_tests, avg_effectiveness, total_mutations, caught_mutations = cursor.fetchone()
            
            # Quality distribution
            cursor = conn.execute("""
                SELECT 
                    SUM(CASE WHEN effectiveness_percentage >= ? THEN 1 ELSE 0 END) as excellent,
                    SUM(CASE WHEN effectiveness_percentage >= ? AND effectiveness_percentage < ? THEN 1 ELSE 0 END) as good,
                    SUM(CASE WHEN effectiveness_percentage >= ? AND effectiveness_percentage < ? THEN 1 ELSE 0 END) as moderate,
                    SUM(CASE WHEN effectiveness_percentage < ? THEN 1 ELSE 0 END) as poor
                FROM effectiveness_metrics 
                WHERE timestamp >= datetime('now', '-7 days')
            """, (
                self.thresholds.EXCELLENT,
                self.thresholds.GOOD, self.thresholds.EXCELLENT,
                self.thresholds.MODERATE, self.thresholds.GOOD,
                self.thresholds.MODERATE
            ))
            excellent, good, moderate, poor = cursor.fetchone()
        
        return {
            'period': '7 days',
            'total_tests': total_tests or 0,
            'average_effectiveness': avg_effectiveness or 0.0,
            'total_mutations': total_mutations or 0,
            'mutations_caught': caught_mutations or 0,
            'catch_rate': (caught_mutations / total_mutations * 100) if total_mutations else 0,
            'quality_distribution': {
                'excellent': excellent or 0,
                'good': good or 0,
                'moderate': moderate or 0,
                'poor': poor or 0
            },
            'live_stats': self.get_live_stats(),
            'last_updated': datetime.now().isoformat()
        }
    
    def start_monitoring(self):
        """Start background monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Effectiveness monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join()
        logger.info("Effectiveness monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Cleanup old data
                cutoff_date = datetime.now() - timedelta(days=self.max_history_days)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "DELETE FROM effectiveness_metrics WHERE timestamp < ?",
                        (cutoff_date,)
                    )
                
                # Sleep for 1 hour
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Sleep for 1 minute on error
    
    def export_metrics(self, output_file: Path, days: int = 30):
        """Export metrics to JSON file."""
        start_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM effectiveness_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (start_time,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        
        # Convert to list of dictionaries
        metrics = []
        for row in rows:
            metric_dict = dict(zip(columns, row))
            if metric_dict['mutation_types']:
                metric_dict['mutation_types'] = json.loads(metric_dict['mutation_types'])
            metrics.append(metric_dict)
        
        # Export to file
        export_data = {
            'export_date': datetime.now().isoformat(),
            'period_days': days,
            'total_metrics': len(metrics),
            'metrics': metrics
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(metrics)} metrics to {output_file}")


class EffectivenessAlertManager:
    """Manages alerts and notifications for effectiveness monitoring."""
    
    def __init__(self, monitor: EffectivenessMonitor):
        self.monitor = monitor
        self.alert_history: List[Dict] = []
        self.alert_suppression: Dict[str, datetime] = {}
        
        # Register for all alert types
        self.monitor.register_callback('low_effectiveness_alert', self._handle_low_effectiveness)
        self.monitor.register_callback('zero_effectiveness_alert', self._handle_zero_effectiveness)
        self.monitor.register_callback('error_alert', self._handle_error)
        self.monitor.register_callback('trend_decline_alert', self._handle_trend_decline)
    
    def _handle_low_effectiveness(self, data: Dict):
        """Handle low effectiveness alerts."""
        alert_key = f"low_effectiveness_{data['metric'].test_file}"
        
        if self._should_suppress_alert(alert_key, minutes=30):
            return
        
        alert = {
            'type': 'low_effectiveness',
            'timestamp': datetime.now(),
            'test_file': data['metric'].test_file,
            'effectiveness': data['metric'].effectiveness_percentage,
            'threshold': data['threshold'],
            'severity': data['severity'],
            'message': f"Test {data['metric'].test_file} has low effectiveness: {data['metric'].effectiveness_percentage:.1f}%"
        }
        
        self._record_alert(alert)
        logger.warning(alert['message'])
    
    def _handle_zero_effectiveness(self, data: Dict):
        """Handle zero effectiveness alerts."""
        alert = {
            'type': 'zero_effectiveness',
            'timestamp': datetime.now(),
            'test_file': data['metric'].test_file,
            'severity': data['severity'],
            'message': f"CRITICAL: Test {data['metric'].test_file} caught zero mutations!"
        }
        
        self._record_alert(alert)
        logger.critical(alert['message'])
    
    def _handle_error(self, data: Dict):
        """Handle error alerts."""
        alert_key = f"error_{data['metric'].test_file}"
        
        if self._should_suppress_alert(alert_key, minutes=15):
            return
        
        alert = {
            'type': 'error',
            'timestamp': datetime.now(),
            'test_file': data['metric'].test_file,
            'error': data['error'],
            'severity': data['severity'],
            'message': f"Error in mutation testing for {data['metric'].test_file}: {data['error']}"
        }
        
        self._record_alert(alert)
        logger.error(alert['message'])
    
    def _handle_trend_decline(self, data: Dict):
        """Handle trend decline alerts."""
        if self._should_suppress_alert('trend_decline', minutes=60):
            return
        
        alert = {
            'type': 'trend_decline',
            'timestamp': datetime.now(),
            'trend': data['trend'],
            'recent_tests': data['recent_tests'],
            'severity': data['severity'],
            'message': f"Effectiveness is declining - {data['recent_tests']} recent tests show downward trend"
        }
        
        self._record_alert(alert)
        logger.warning(alert['message'])
    
    def _should_suppress_alert(self, alert_key: str, minutes: int) -> bool:
        """Check if alert should be suppressed to avoid spam."""
        if alert_key in self.alert_suppression:
            last_alert = self.alert_suppression[alert_key]
            if datetime.now() - last_alert < timedelta(minutes=minutes):
                return True
        
        self.alert_suppression[alert_key] = datetime.now()
        return False
    
    def _record_alert(self, alert: Dict):
        """Record alert in history."""
        self.alert_history.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get alerts from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert['timestamp'] >= cutoff]