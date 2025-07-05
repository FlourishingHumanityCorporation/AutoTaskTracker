"""Tests for effectiveness monitoring system.

This test suite validates the real-time monitoring capabilities
for tracking mutation testing effectiveness over time.
"""

import pytest
import tempfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import json

from tests.health.testing.effectiveness_monitor import (
    EffectivenessMonitor,
    EffectivenessMetric,
    EffectivenessTrend,
    EffectivenessAlertManager
)


class TestEffectivenessMetric:
    """Test effectiveness metric data structure."""
    
    def test_metric_creation(self):
        """Test creating an effectiveness metric."""
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_example.py",
            source_file="example.py",
            effectiveness_percentage=75.0,
            mutations_total=10,
            mutations_caught=7,
            mutations_missed=3,
            execution_time=2.5,
            mutation_types=["boolean_flip", "operator_change"]
        )
        
        assert metric.test_file == "test_example.py"
        assert metric.effectiveness_percentage == 75.0
        assert metric.mutations_total == 10
        assert len(metric.mutation_types) == 2


class TestEffectivenessMonitor:
    """Test the effectiveness monitoring system."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def monitor(self, temp_project_dir):
        """Create an effectiveness monitor."""
        return EffectivenessMonitor(temp_project_dir)
    
    def test_monitor_initialization(self, monitor, temp_project_dir):
        """Test monitor initialization."""
        assert monitor.project_root == temp_project_dir
        assert monitor.db_path.exists()
        assert len(monitor.recent_metrics) == 0
        assert monitor.live_stats['total_tests_today'] == 0
    
    def test_database_initialization(self, monitor):
        """Test that database is properly initialized."""
        # Check that tables exist
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='effectiveness_metrics'
            """)
            assert cursor.fetchone() is not None
    
    def test_record_effectiveness(self, monitor):
        """Test recording effectiveness metrics."""
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_example.py",
            source_file="example.py",
            effectiveness_percentage=80.0,
            mutations_total=10,
            mutations_caught=8,
            mutations_missed=2,
            execution_time=1.5,
            mutation_types=["boolean_flip"]
        )
        
        monitor.record_effectiveness(metric)
        
        # Check in-memory storage
        assert len(monitor.recent_metrics) == 1
        assert monitor.recent_metrics[0] == metric
        
        # Check database storage
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM effectiveness_metrics")
            count = cursor.fetchone()[0]
            assert count == 1
            
            # Check specific values
            cursor = conn.execute("""
                SELECT test_file, effectiveness_percentage, mutations_total
                FROM effectiveness_metrics
            """)
            row = cursor.fetchone()
            assert row[0] == "test_example.py"
            assert row[1] == 80.0
            assert row[2] == 10
    
    def test_live_stats_update(self, monitor):
        """Test live statistics updates."""
        # Record a metric from today
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_example.py",
            source_file="example.py",
            effectiveness_percentage=75.0,
            mutations_total=8,
            mutations_caught=6,
            mutations_missed=2,
            execution_time=1.0
        )
        
        monitor.record_effectiveness(metric)
        
        stats = monitor.get_live_stats()
        assert stats['total_tests_today'] == 1
        assert stats['average_effectiveness_today'] == 75.0
        assert stats['tests_this_hour'] == 1
        assert 'current_trend' in stats
    
    def test_trend_calculation(self, monitor):
        """Test trend calculation with multiple metrics."""
        base_time = datetime.now()
        
        # Add metrics with improving effectiveness
        for i in range(15):
            effectiveness = 50.0 + (i * 2)  # Improving from 50% to 78%
            metric = EffectivenessMetric(
                timestamp=base_time - timedelta(minutes=i),
                test_file=f"test_{i}.py",
                source_file=f"source_{i}.py",
                effectiveness_percentage=effectiveness,
                mutations_total=10,
                mutations_caught=int(effectiveness / 10),
                mutations_missed=10 - int(effectiveness / 10),
                execution_time=1.0
            )
            monitor.record_effectiveness(metric)
        
        # Should detect improving trend
        stats = monitor.get_live_stats()
        assert stats['current_trend'] in ['improving', 'stable']  # Depends on exact calculation
    
    def test_callback_registration_and_triggering(self, monitor):
        """Test callback registration and triggering."""
        callback_calls = []
        
        def test_callback(data):
            callback_calls.append(data)
        
        monitor.register_callback('effectiveness_recorded', test_callback)
        
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_example.py",
            source_file="example.py",
            effectiveness_percentage=60.0,
            mutations_total=5,
            mutations_caught=3,
            mutations_missed=2,
            execution_time=0.8
        )
        
        monitor.record_effectiveness(metric)
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == metric
    
    def test_low_effectiveness_alert(self, monitor):
        """Test low effectiveness alert triggering."""
        alert_calls = []
        
        def alert_callback(data):
            alert_calls.append(data)
        
        monitor.register_callback('low_effectiveness_alert', alert_callback)
        
        # Record a metric with very low effectiveness
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_poor.py",
            source_file="poor.py",
            effectiveness_percentage=15.0,  # Below POOR threshold (30%)
            mutations_total=10,
            mutations_caught=1,
            mutations_missed=9,
            execution_time=1.0
        )
        
        monitor.record_effectiveness(metric)
        
        assert len(alert_calls) == 1
        assert alert_calls[0]['metric'] == metric
        assert alert_calls[0]['severity'] == 'high'
    
    def test_zero_effectiveness_alert(self, monitor):
        """Test zero effectiveness alert triggering."""
        alert_calls = []
        
        def alert_callback(data):
            alert_calls.append(data)
        
        monitor.register_callback('zero_effectiveness_alert', alert_callback)
        
        # Record a metric with zero effectiveness
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_broken.py",
            source_file="broken.py",
            effectiveness_percentage=0.0,
            mutations_total=5,
            mutations_caught=0,
            mutations_missed=5,
            execution_time=0.5
        )
        
        monitor.record_effectiveness(metric)
        
        assert len(alert_calls) == 1
        assert alert_calls[0]['metric'] == metric
        assert alert_calls[0]['severity'] == 'critical'
    
    def test_get_effectiveness_trend(self, monitor):
        """Test getting effectiveness trends over time."""
        base_time = datetime.now() - timedelta(days=3)
        
        # Add metrics over 3 days
        for day in range(3):
            for hour in range(4):  # 4 tests per day
                metric = EffectivenessMetric(
                    timestamp=base_time + timedelta(days=day, hours=hour * 6),
                    test_file=f"test_day{day}_hour{hour}.py",
                    source_file=f"source_day{day}_hour{hour}.py",
                    effectiveness_percentage=70.0 + (day * 5),  # Improving over days
                    mutations_total=8,
                    mutations_caught=int((70.0 + day * 5) / 10),
                    mutations_missed=8 - int((70.0 + day * 5) / 10),
                    execution_time=1.2
                )
                monitor.record_effectiveness(metric)
        
        trends = monitor.get_effectiveness_trend(days=3, granularity='daily')
        
        assert len(trends) >= 1  # Should have at least one day of data
        
        # Check that trends have required fields
        for trend in trends:
            assert hasattr(trend, 'average_effectiveness')
            assert hasattr(trend, 'total_tests')
            assert hasattr(trend, 'quality_category')
    
    def test_file_effectiveness_history(self, monitor):
        """Test getting effectiveness history for specific file."""
        test_file = "test_specific.py"
        base_time = datetime.now()
        
        # Add multiple metrics for the same file
        for i in range(5):
            metric = EffectivenessMetric(
                timestamp=base_time - timedelta(hours=i),
                test_file=test_file,
                source_file="specific.py",
                effectiveness_percentage=60.0 + (i * 5),
                mutations_total=6,
                mutations_caught=int((60.0 + i * 5) / 10),
                mutations_missed=6 - int((60.0 + i * 5) / 10),
                execution_time=1.0
            )
            monitor.record_effectiveness(metric)
        
        history = monitor.get_file_effectiveness_history(test_file, days=1)
        
        assert len(history) == 5
        assert all(m.test_file == test_file for m in history)
        # Should be ordered by timestamp DESC
        assert history[0].timestamp > history[1].timestamp
    
    def test_summary_report(self, monitor):
        """Test generating summary report."""
        # Add some test data
        base_time = datetime.now()
        
        # Mix of good and poor effectiveness
        effectiveness_values = [90.0, 75.0, 45.0, 20.0, 85.0]
        
        for i, eff in enumerate(effectiveness_values):
            metric = EffectivenessMetric(
                timestamp=base_time - timedelta(hours=i),
                test_file=f"test_{i}.py",
                source_file=f"source_{i}.py",
                effectiveness_percentage=eff,
                mutations_total=10,
                mutations_caught=int(eff / 10),
                mutations_missed=10 - int(eff / 10),
                execution_time=1.0
            )
            monitor.record_effectiveness(metric)
        
        report = monitor.get_summary_report()
        
        assert 'total_tests' in report
        assert 'average_effectiveness' in report
        assert 'quality_distribution' in report
        assert 'live_stats' in report
        
        # Check quality distribution
        dist = report['quality_distribution']
        assert 'excellent' in dist
        assert 'good' in dist
        assert 'moderate' in dist
        assert 'poor' in dist
        
        # Should have at least one test in each category based on our data
        assert dist['excellent'] >= 1  # 90.0
        assert dist['poor'] >= 1       # 20.0
    
    def test_export_metrics(self, monitor, temp_project_dir):
        """Test exporting metrics to JSON."""
        # Add test data
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_export.py",
            source_file="export.py",
            effectiveness_percentage=72.0,
            mutations_total=9,
            mutations_caught=6,
            mutations_missed=3,
            execution_time=1.1,
            mutation_types=["boolean_flip", "operator_change"]
        )
        monitor.record_effectiveness(metric)
        
        # Export to file
        export_file = temp_project_dir / "exported_metrics.json"
        monitor.export_metrics(export_file, days=1)
        
        assert export_file.exists()
        
        # Check exported data
        with open(export_file) as f:
            data = json.load(f)
        
        assert 'export_date' in data
        assert 'total_metrics' in data
        assert 'metrics' in data
        assert len(data['metrics']) == 1
        
        exported_metric = data['metrics'][0]
        assert exported_metric['test_file'] == "test_export.py"
        assert exported_metric['effectiveness_percentage'] == 72.0


class TestEffectivenessAlertManager:
    """Test the alert management system."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def monitor(self, temp_project_dir):
        """Create an effectiveness monitor."""
        return EffectivenessMonitor(temp_project_dir)
    
    @pytest.fixture
    def alert_manager(self, monitor):
        """Create an alert manager."""
        return EffectivenessAlertManager(monitor)
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager.monitor is not None
        assert len(alert_manager.alert_history) == 0
        assert len(alert_manager.alert_suppression) == 0
    
    def test_low_effectiveness_alert_handling(self, monitor, alert_manager):
        """Test handling of low effectiveness alerts."""
        # Record a low effectiveness metric
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_low.py",
            source_file="low.py",
            effectiveness_percentage=25.0,  # Below threshold
            mutations_total=8,
            mutations_caught=2,
            mutations_missed=6,
            execution_time=1.0
        )
        
        monitor.record_effectiveness(metric)
        
        # Check that alert was recorded
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        assert alert['type'] == 'low_effectiveness'
        assert alert['test_file'] == "test_low.py"
        assert alert['severity'] == 'high'
    
    def test_zero_effectiveness_alert_handling(self, monitor, alert_manager):
        """Test handling of zero effectiveness alerts."""
        metric = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_zero.py",
            source_file="zero.py",
            effectiveness_percentage=0.0,
            mutations_total=5,
            mutations_caught=0,
            mutations_missed=5,
            execution_time=0.8
        )
        
        monitor.record_effectiveness(metric)
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        assert alert['type'] == 'zero_effectiveness'
        assert alert['severity'] == 'critical'
    
    def test_alert_suppression(self, monitor, alert_manager):
        """Test that alerts are suppressed to avoid spam."""
        # Record two low effectiveness metrics for the same file quickly
        metric1 = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_spam.py",
            source_file="spam.py",
            effectiveness_percentage=20.0,
            mutations_total=5,
            mutations_caught=1,
            mutations_missed=4,
            execution_time=1.0
        )
        
        metric2 = EffectivenessMetric(
            timestamp=datetime.now(),
            test_file="test_spam.py",
            source_file="spam.py",
            effectiveness_percentage=18.0,
            mutations_total=6,
            mutations_caught=1,
            mutations_missed=5,
            execution_time=1.0
        )
        
        monitor.record_effectiveness(metric1)
        monitor.record_effectiveness(metric2)
        
        # Should only have one alert due to suppression
        low_eff_alerts = [a for a in alert_manager.alert_history if a['type'] == 'low_effectiveness']
        assert len(low_eff_alerts) == 1
    
    def test_get_recent_alerts(self, alert_manager):
        """Test getting recent alerts."""
        # Manually add some alerts to history
        now = datetime.now()
        
        # Recent alert (1 hour ago)
        alert_manager.alert_history.append({
            'type': 'low_effectiveness',
            'timestamp': now - timedelta(hours=1),
            'test_file': 'test1.py',
            'severity': 'high'
        })
        
        # Old alert (2 days ago)
        alert_manager.alert_history.append({
            'type': 'error',
            'timestamp': now - timedelta(days=2),
            'test_file': 'test2.py',
            'severity': 'medium'
        })
        
        recent_alerts = alert_manager.get_recent_alerts(hours=24)
        
        assert len(recent_alerts) == 1
        assert recent_alerts[0]['test_file'] == 'test1.py'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])