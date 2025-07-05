"""
Adapter to bridge Pensieve's minimal schema with AutoTaskTracker's expectations.
This allows the existing codebase to work with Pensieve's actual database structure.
"""

import sqlite3
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
import logging
import os
from pathlib import Path

from autotasktracker.core.database import DatabaseManager

logger = logging.getLogger(__name__)


class PensieveSchemaAdapter:
    """Adapts Pensieve's minimal schema to AutoTaskTracker's expected schema."""
    
    @staticmethod
    def adapt_entity_row(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert Pensieve entity row to expected format.
        
        Pensieve schema: (id, created_at, filepath)
        Expected schema: (id, filepath, filename, file_type, file_type_group, created_at, ...)
        """
        # Extract filename from filepath
        filepath = row['filepath']
        filename = os.path.basename(filepath) if filepath else None
        
        # Determine file type from extension
        file_ext = Path(filepath).suffix.lower() if filepath else ''
        file_type = file_ext[1:] if file_ext else 'unknown'  # Remove the dot
        
        # Group screenshots as images
        file_type_group = 'image' if file_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'] else 'other'
        
        return {
            'id': row['id'],
            'filepath': filepath,
            'filename': filename,
            'file_type': file_type,
            'file_type_group': file_type_group,
            'created_at': row['created_at'],
            'file_created_at': row['created_at'],  # Use same as created_at
            'last_scan_at': row['created_at'],  # Use same as created_at
            'deleted': 0  # Assume not deleted
        }
    
    @staticmethod
    def adapt_fetch_tasks_query() -> str:
        """Return adapted query for fetching tasks that works with Pensieve schema."""
        return """
        SELECT
            e.id,
            e.filepath,
            e.created_at,
            me1.value as ocr_text,
            me2.value as active_window
        FROM
            entities e
            LEFT JOIN metadata_entries me1 ON e.id = me1.entity_id AND me1.key = "ocr_result"
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "active_window"
        WHERE
            e.filepath LIKE '%.png' 
            OR e.filepath LIKE '%.jpg' 
            OR e.filepath LIKE '%.jpeg'
            OR e.filepath LIKE '%.webp'
        """
    
    @staticmethod
    def adapt_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Add missing columns to dataframe to match expected schema."""
        if df.empty:
            # Return empty dataframe with expected columns
            return pd.DataFrame(columns=[
                'id', 'filepath', 'filename', 'created_at', 
                'file_created_at', 'last_scan_at', "ocr_result", "active_window"
            ])
        
        # Add filename column if missing
        if 'filename' not in df.columns and 'filepath' in df.columns:
            df['filename'] = df['filepath'].apply(lambda x: os.path.basename(x) if x else None)
        
        # Add file_created_at and last_scan_at if missing
        if 'file_created_at' not in df.columns and 'created_at' in df.columns:
            df['file_created_at'] = df['created_at']
        
        if 'last_scan_at' not in df.columns and 'created_at' in df.columns:
            df['last_scan_at'] = df['created_at']
        
        return df
    
    @staticmethod
    def get_screenshot_count_query() -> str:
        """Return query for counting screenshots that works with Pensieve schema."""
        return """
        SELECT COUNT(*) as count
        FROM entities 
        WHERE (filepath LIKE '%.png' OR filepath LIKE '%.jpg' OR filepath LIKE '%.jpeg' OR filepath LIKE '%.webp')
        AND date(created_at, 'localtime') = date(?, 'localtime')
        """
    
    @staticmethod
    def get_unique_applications_query() -> str:
        """Return query for getting unique applications."""
        return """
        SELECT DISTINCT me.value as active_window
        FROM entities e
        JOIN metadata_entries me ON e.id = me.entity_id AND me.key = "active_window"
        WHERE (e.filepath LIKE '%.png' OR e.filepath LIKE '%.jpg' OR e.filepath LIKE '%.jpeg')
        AND datetime(e.created_at, 'localtime') BETWEEN ? AND ?
        AND me.value IS NOT NULL
        """
    
    @staticmethod
    def get_activity_summary_query() -> str:
        """Return query for activity summary."""
        return """
        SELECT 
            MIN(datetime(created_at, 'localtime')) as first_activity,
            MAX(datetime(created_at, 'localtime')) as last_activity
        FROM entities
        WHERE (filepath LIKE '%.png' OR filepath LIKE '%.jpg' OR filepath LIKE '%.jpeg')
        AND date(created_at, 'localtime') = date(?, 'localtime')
        """
    
    @staticmethod
    def get_ai_coverage_query() -> str:
        """Return query for AI coverage stats that works with Pensieve schema."""
        return """
        SELECT 
            COUNT(DISTINCT e.id) as total_screenshots,
            COUNT(DISTINCT me_ocr.entity_id) as with_ocr,
            COUNT(DISTINCT me_vlm.entity_id) as with_vlm,
            COUNT(DISTINCT me_emb.entity_id) as with_embeddings
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr.key = "ocr_result"
        LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm.key IN ('minicpm_v_result', "vlm_structured")
        LEFT JOIN metadata_entries me_emb ON e.id = me_emb.entity_id AND me_emb.key = 'embedding'
        WHERE (e.filepath LIKE '%.png' OR e.filepath LIKE '%.jpg' OR e.filepath LIKE '%.jpeg')
        """
    
    @staticmethod
    def get_search_activities_query() -> str:
        """Return query for searching activities."""
        return """
        SELECT
            e.id,
            e.filepath,
            datetime(e.created_at, 'localtime') as created_at,
            me.value as ocr_text,
            me2.value as active_window
        FROM entities e
        LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = "ocr_result"
        LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "active_window"
        WHERE (e.filepath LIKE '%.png' OR e.filepath LIKE '%.jpg' OR e.filepath LIKE '%.jpeg')
        AND (
            me.value LIKE ? OR 
            me2.value LIKE ?
        )
        ORDER BY e.created_at DESC
        LIMIT ?
        """


class PensieveQueryExecutor:
    """Executes Pensieve schema queries using DatabaseManager."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
    
    def get_screenshot_count(self, date_str: str) -> int:
        """Get screenshot count for a specific date."""
        query = PensieveSchemaAdapter.get_screenshot_count_query()
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date_str,))
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error getting screenshot count: {e}")
            return 0
    
    def get_unique_applications(self, start_date: str, end_date: str) -> List[str]:
        """Get unique applications for a date range."""
        query = PensieveSchemaAdapter.get_unique_applications_query()
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (start_date, end_date))
                results = cursor.fetchall()
                return [row['active_window'] for row in results if row['active_window']]
        except Exception as e:
            logger.error(f"Error getting unique applications: {e}")
            return []
    
    def get_activity_summary(self, date_str: str) -> Dict[str, Any]:
        """Get activity summary for a specific date."""
        query = PensieveSchemaAdapter.get_activity_summary_query()
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date_str,))
                result = cursor.fetchone()
                if result:
                    return {
                        'first_activity': result['first_activity'],
                        'last_activity': result['last_activity']
                    }
                return {}
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return {}
    
    def get_ai_coverage_stats(self) -> Dict[str, int]:
        """Get AI coverage statistics."""
        query = PensieveSchemaAdapter.get_ai_coverage_query()
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    return {
                        'total_screenshots': result['total_screenshots'],
                        'with_ocr': result['with_ocr'],
                        'with_vlm': result['with_vlm'],
                        'with_embeddings': result['with_embeddings']
                    }
                return {}
        except Exception as e:
            logger.error(f"Error getting AI coverage stats: {e}")
            return {}
    
    def search_activities(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search activities by text content."""
        query = PensieveSchemaAdapter.get_search_activities_query()
        search_pattern = f"%{search_term}%"
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (search_pattern, search_pattern, limit))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error searching activities: {e}")
            return []