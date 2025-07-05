#!/usr/bin/env python3
"""
Process screenshots into meaningful work sessions.
Groups related activities and calculates accurate time tracking.
"""
import sys
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.core.time_tracker import TimeTracker, TaskSession
from autotasktracker.config import get_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class SessionProcessor:
    """Process screenshots into work sessions."""
    
    def __init__(self, screenshot_interval: int = 4):
        self.db_path = get_config().get_db_path()
        self.time_tracker = TimeTracker(screenshot_interval)
        
    def get_screenshots_for_period(self, start: datetime, end: datetime) -> List[Dict]:
        """Get screenshots with tasks for a time period."""
        from autotasktracker.core import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    e.id,
                    e.created_at,
                    m_window.value as window_title,
                    m_task.value as task,
                    m_category.value as category,
                    m_ocr.value as ocr_text
                FROM entities e
                LEFT JOIN metadata_entries m_window ON e.id = m_window.entity_id AND m_window.key = "active_window"
                LEFT JOIN metadata_entries m_task ON e.id = m_task.entity_id AND m_task.key = "tasks"
                LEFT JOIN metadata_entries m_category ON e.id = m_category.entity_id AND m_category.key = "category"
                LEFT JOIN metadata_entries m_ocr ON e.id = m_ocr.entity_id AND m_ocr.key = "ocr_result"
                WHERE e.created_at >= ? AND e.created_at <= ?
                ORDER BY e.created_at
            """, (start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')))
            
            screenshots = []
            for row in cursor.fetchall():
                screenshots.append({
                    'id': row[0],
                    'created_at': row[1],
                    "active_window": json.dumps({
                        'title': row[2] or 'Unknown',
                        'app': self._extract_app_name(row[2])
                    }),
                    "tasks": row[3],
                    "category": row[4],
                    "ocr_result": row[5]
                })
            
            return screenshots
    
    def _extract_app_name(self, window_title: str) -> str:
        """Extract application name from window title."""
        if not window_title:
            return 'Unknown'
        
        # Common patterns
        if 'Visual Studio Code' in window_title:
            return 'VSCode'
        elif 'Chrome' in window_title:
            return 'Chrome'
        elif 'Terminal' in window_title:
            return 'Terminal'
        elif 'claude' in window_title.lower():
            return 'Claude'
        elif 'Zoom' in window_title:
            return 'Zoom'
        elif 'Slack' in window_title:
            return 'Slack'
        
        # Try to extract from window title pattern
        parts = window_title.split(' - ')
        if len(parts) > 1:
            return parts[-1].strip()
        
        return window_title.split()[0] if window_title else 'Unknown'
    
    def process_sessions(self, start: datetime, end: datetime) -> List[TaskSession]:
        """Process screenshots into sessions for a time period."""
        screenshots = self.get_screenshots_for_period(start, end)
        
        if not screenshots:
            logger.info(f"No screenshots found between {start} and {end}")
            return []
        
        # Convert to pandas DataFrame format expected by TimeTracker
        import pandas as pd
        df = pd.DataFrame(screenshots)
        
        # Track sessions
        sessions = self.time_tracker.track_sessions(df)
        
        logger.info(f"Found {len(sessions)} sessions from {len(screenshots)} screenshots")
        
        return sessions
    
    def save_sessions_to_db(self, sessions: List[TaskSession]):
        """Save processed sessions to database."""
        from autotasktracker.core import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create sessions table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    active_time_seconds INTEGER NOT NULL,
                    screenshot_count INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    gaps TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Save each session
            for session in sessions:
                cursor.execute("""
                    INSERT INTO work_sessions 
                    (task_name, category, start_time, end_time, duration_seconds, 
                     active_time_seconds, screenshot_count, confidence, gaps)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.task_name,
                    session.category,
                    session.start_time,
                    session.end_time,
                    session.duration_seconds,
                    session.active_time_seconds,
                    session.screenshot_count,
                    session.confidence,
                    json.dumps(session.gaps)
                ))
            
            conn.commit()
            logger.info(f"Saved {len(sessions)} sessions to database")
    
    def get_daily_summary(self, date: datetime) -> Dict:
        """Get summary of work sessions for a specific day."""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        sessions = self.process_sessions(start, end)
        
        if not sessions:
            return {
                'date': date.strftime('%Y-%m-%d'),
                'total_sessions': 0,
                'total_time_hours': 0,
                'active_time_hours': 0,
                "category": {},
                'top_tasks': []
            }
        
        # Calculate summary
        total_time = sum(s.duration_seconds for s in sessions)
        active_time = sum(s.active_time_seconds for s in sessions)
        
        # Category breakdown
        from collections import defaultdict
        category_time = defaultdict(int)
        task_time = defaultdict(int)
        
        for session in sessions:
            category_time[session.category] += session.duration_seconds
            task_time[session.task_name] += session.duration_seconds
        
        # Top tasks
        top_tasks = sorted(task_time.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'date': date.strftime('%Y-%m-%d'),
            'total_sessions': len(sessions),
            'total_time_hours': total_time / 3600,
            'active_time_hours': active_time / 3600,
            'idle_percentage': ((total_time - active_time) / total_time * 100) if total_time > 0 else 0,
            "category": {cat: time/3600 for cat, time in category_time.items()},
            'top_tasks': [(task, time/3600) for task, time in top_tasks],
            'average_session_minutes': (total_time / len(sessions) / 60) if sessions else 0,
            'high_confidence_sessions': sum(1 for s in sessions if s.confidence >= 0.8)
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process work sessions from screenshots')
    parser.add_argument('--date', type=str, help='Process specific date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=1, help='Number of days to process')
    parser.add_argument('--save', action='store_true', help='Save sessions to database')
    parser.add_argument('--summary', action='store_true', help='Show daily summary')
    
    args = parser.parse_args()
    
    processor = SessionProcessor()
    
    # Determine date range
    if args.date:
        start_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Process each day
    for day_offset in range(args.days):
        current_date = start_date - timedelta(days=day_offset)
        
        if args.summary:
            # Show summary
            summary = processor.get_daily_summary(current_date)
            
            print(f"\n=== {summary['date']} Summary ===")
            print(f"Sessions: {summary['total_sessions']}")
            print(f"Total time: {summary['total_time_hours']:.1f} hours")
            print(f"Active time: {summary['active_time_hours']:.1f} hours")
            print(f"Idle: {summary['idle_percentage']:.1f}%")
            print(f"Average session: {summary['average_session_minutes']:.1f} minutes")
            print(f"High confidence: {summary['high_confidence_sessions']} sessions")
            
            print("\nCategory breakdown:")
            for cat, hours in sorted(summary["category"].items(), key=lambda x: x[1], reverse=True):
                print(f"  {cat}: {hours:.1f} hours")
            
            print("\nTop tasks:")
            for task, hours in summary['top_tasks'][:5]:
                print(f"  {task}: {hours:.1f} hours")
        
        else:
            # Process sessions
            end_date = current_date + timedelta(days=1)
            sessions = processor.process_sessions(current_date, end_date)
            
            print(f"\n=== Sessions for {current_date.strftime('%Y-%m-%d')} ===")
            print(f"Found {len(sessions)} sessions")
            
            # Show sample sessions
            for i, session in enumerate(sessions[:10], 1):
                print(f"\n{i}. {session.task_name}")
                print(f"   Time: {session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}")
                print(f"   Duration: {session.duration_minutes:.1f} min (active: {session.active_time_seconds/60:.1f} min)")
                print(f"   Category: {session.category}")
                print(f"   Confidence: {session.confidence_indicator}")
            
            if args.save:
                processor.save_sessions_to_db(sessions)


if __name__ == "__main__":
    main()