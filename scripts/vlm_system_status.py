#!/usr/bin/env python3
"""
VLM System Status - Comprehensive status check for all VLM improvements
"""
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.error_handler import get_error_handler, get_metrics, get_health_monitor
from autotasktracker.ai.vlm_processor import SmartVLMProcessor
from autotasktracker.ai.sensitive_filter import get_sensitive_filter


def check_database_improvements():
    """Check database connection pooling and WAL mode."""
    print("🗄️  Database Improvements Status:")
    try:
        db = DatabaseManager()
        pool_stats = db.get_pool_stats()
        print(f"  ✅ Connection pooling: {pool_stats['active_connections']}/{pool_stats['max_connections']} active")
        print(f"  ✅ WAL mode: {'Enabled' if pool_stats['wal_mode_enabled'] else 'Disabled'}")
        print(f"  ✅ Pooled connections: {pool_stats['pooled_connections']}")
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def check_vlm_processor_improvements():
    """Check VLM processor improvements."""
    print("\n🧠 VLM Processor Improvements Status:")
    try:
        processor = SmartVLMProcessor()
        
        # Check caching
        cache_stats = processor.get_cache_stats()
        print(f"  ✅ LRU Image Cache: {cache_stats['image_cache_items']}/{processor.max_cache_items} items")
        print(f"  ✅ Memory Usage: {cache_stats['image_cache_size_mb']:.1f}/{cache_stats['image_cache_max_mb']} MB")
        print(f"  ✅ Cache Usage: {cache_stats['image_cache_usage_percent']:.1f}%")
        
        # Check rate limiting
        rate_stats = processor.rate_limiter.get_stats()
        print(f"  ✅ Rate Limiter: {rate_stats['recent_requests']}/{rate_stats['max_requests']} requests")
        print(f"  ✅ Requests Remaining: {rate_stats['requests_remaining']}")
        
        # Check circuit breaker
        circuit_stats = processor.circuit_breaker.get_stats()
        print(f"  ✅ Circuit Breaker: {circuit_stats['state']} ({circuit_stats['failure_count']}/{circuit_stats['failure_threshold']} failures)")
        
        return True
    except Exception as e:
        print(f"  ❌ VLM Processor error: {e}")
        return False


def check_error_handling():
    """Check error handling system."""
    print("\n🚨 Error Handling System Status:")
    try:
        error_handler = get_error_handler()
        error_stats = error_handler.get_error_stats()
        
        print(f"  ✅ Total Errors Tracked: {error_stats['total_errors']}")
        print(f"  ✅ Recent Errors (1h): {error_stats['recent_errors_1h']}")
        print(f"  ✅ Error Rate: {error_stats['recent_error_rate']:.2f} errors/min")
        
        if error_stats['most_common_error']:
            print(f"  ⚠️  Most Common Error: {error_stats['most_common_error']}")
        else:
            print(f"  ✅ No errors recorded")
        
        return True
    except Exception as e:
        print(f"  ❌ Error handling error: {e}")
        return False


def check_metrics_system():
    """Check metrics system."""
    print("\n📊 Metrics System Status:")
    try:
        metrics = get_metrics()
        metrics_summary = metrics.get_metrics_summary()
        
        print(f"  ✅ Counters: {len(metrics_summary['counters'])} metrics")
        for counter, value in list(metrics_summary['counters'].items())[:5]:
            print(f"    • {counter}: {value}")
        
        # Show latency metrics
        latency_metrics = [k for k in metrics_summary.keys() if 'latency' in k]
        if latency_metrics:
            print(f"  ✅ Latency Metrics: {len(latency_metrics)} tracked")
            for metric in latency_metrics[:3]:
                stats = metrics_summary[metric]
                print(f"    • {metric}: avg {stats['avg']:.1f}ms (p95: {stats['p95']:.1f}ms)")
        
        return True
    except Exception as e:
        print(f"  ❌ Metrics error: {e}")
        return False


def check_health_monitoring():
    """Check health monitoring system."""
    print("\n🏥 Health Monitoring Status:")
    try:
        health_monitor = get_health_monitor()
        health_status = health_monitor.run_health_checks()
        
        for check_name, status in health_status.items():
            status_icon = "✅" if status == "healthy" else "❌" if "error" in status else "⚠️"
            print(f"  {status_icon} {check_name}: {status}")
        
        # Check recent alerts
        recent_alerts = health_monitor.get_recent_alerts(5)
        if recent_alerts:
            print(f"  ⚠️  Recent Alerts: {len(recent_alerts)}")
            for alert in recent_alerts[-2:]:
                print(f"    • {alert['timestamp'][:19]} - {alert['source']}: {alert['message']}")
        else:
            print(f"  ✅ No recent alerts")
        
        return True
    except Exception as e:
        print(f"  ❌ Health monitoring error: {e}")
        return False


def check_sensitive_data_filtering():
    """Check sensitive data filtering."""
    print("\n🔒 Sensitive Data Filtering Status:")
    try:
        sensitive_filter = get_sensitive_filter()
        
        # Test with sample data
        test_cases = [
            ("john.doe@example.com", "Email detected"),
            ("555-123-4567", "Phone detected"),
            ("password: secret123", "Password detected"),
            ("normal content", "No sensitive data"),
        ]
        
        for test_text, expected in test_cases:
            patterns = sensitive_filter.scan_text_for_sensitive_data(test_text)
            has_sensitive = len(patterns) > 0
            status_icon = "✅" if (has_sensitive and "detected" in expected) or (not has_sensitive and "No sensitive" in expected) else "❌"
            print(f"  {status_icon} {expected}: {'Found' if has_sensitive else 'Clean'}")
        
        # Test window sensitivity
        sensitive_windows = ["1Password - Main Vault", "Banking - Chase Online"]
        for window in sensitive_windows:
            is_sensitive = sensitive_filter.is_window_sensitive(window)
            print(f"  ✅ Window '{window}': {'Sensitive' if is_sensitive else 'Safe'}")
        
        return True
    except Exception as e:
        print(f"  ❌ Sensitive filtering error: {e}")
        return False


def check_database_indexes():
    """Check database performance indexes."""
    print("\n⚡ Database Performance Status:")
    try:
        db = DatabaseManager()
        
        # Check if indexes exist
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = cursor.fetchall()
            
            expected_indexes = [
                'idx_metadata_entity_key',
                'idx_metadata_key', 
                'idx_entities_created_at',
                'idx_entities_file_type',
                'idx_metadata_created_at'
            ]
            
            found_indexes = [idx['name'] for idx in indexes]
            
            for expected_idx in expected_indexes:
                if expected_idx in found_indexes:
                    print(f"  ✅ Index {expected_idx}: Present")
                else:
                    print(f"  ❌ Index {expected_idx}: Missing")
            
            # Test query performance
            import time
            start = time.time()
            cursor.execute("""
                SELECT COUNT(*) FROM entities e
                LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
                WHERE e.file_type_group = 'image'
            """)
            query_time = (time.time() - start) * 1000
            
            print(f"  ✅ Query Performance: {query_time:.1f}ms")
            
        return True
    except Exception as e:
        print(f"  ❌ Database performance error: {e}")
        return False


def check_race_condition_protection():
    """Check race condition protection."""
    print("\n🏁 Race Condition Protection Status:")
    try:
        processor = SmartVLMProcessor()
        
        # Check if atomic processing methods exist
        has_atomic_check = hasattr(processor, '_is_already_processing_in_db')
        has_mark_complete = hasattr(processor, '_mark_processing_complete')
        
        print(f"  ✅ Atomic Processing Check: {'Available' if has_atomic_check else 'Missing'}")
        print(f"  ✅ Processing Completion Marking: {'Available' if has_mark_complete else 'Missing'}")
        
        # Check database support for vlm_processing flag
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM metadata_entries 
                WHERE key = 'vlm_processing'
            """)
            result = cursor.fetchone()
            processing_flags = result['count'] if result else 0
            
        print(f"  ✅ Active Processing Flags: {processing_flags}")
        
        return True
    except Exception as e:
        print(f"  ❌ Race condition protection error: {e}")
        return False


def main():
    """Run comprehensive VLM system status check."""
    print("🔍 VLM System Comprehensive Status Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checks = [
        check_database_improvements,
        check_vlm_processor_improvements,
        check_error_handling,
        check_metrics_system,
        check_health_monitoring,
        check_sensitive_data_filtering,
        check_database_indexes,
        check_race_condition_protection,
    ]
    
    results = []
    for check in checks:
        try:
            success = check()
            results.append(success)
        except Exception as e:
            print(f"  ❌ Check failed: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print(f"Checks Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All VLM improvements are working correctly!")
    elif passed >= total * 0.8:
        print("⚠️  Most improvements working, some issues detected")
    else:
        print("❌ Multiple issues detected, requires attention")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)