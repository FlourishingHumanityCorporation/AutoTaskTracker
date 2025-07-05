import logging
logger = logging.getLogger(__name__)

"""
Example implementation showing how to integrate VLM data into AutoTaskTracker.
This demonstrates the minimal changes needed to support VLM descriptions.
"""

import pandas as pd
from typing import Optional
from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.vlm_integration import get_enhanced_task, get_enhanced_category


class VLMEnabledDatabaseManager(DatabaseManager):
    """Extended DatabaseManager that includes VLM data in queries."""
    
    def fetch_tasks_with_vlm(self, 
                            start_date: Optional[pd.Timestamp] = None,
                            end_date: Optional[pd.Timestamp] = None,
                            limit: int = 100,
                            offset: int = 0) -> pd.DataFrame:
        """
        Fetch tasks including VLM descriptions from the database.
        
        Returns:
            DataFrame with task data including VLM descriptions
        """
        query = """
        SELECT
            e.id,
            e.filepath,
            e.filename,
            datetime(e.created_at, 'localtime') as created_at,
            e.file_created_at,
            e.last_scan_at,
            me.value as ocr_text,
            me2.value as active_window,
            me3.value as vlm_description
        FROM
            entities e
            LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = "ocr_result"
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "active_window"
            LEFT JOIN metadata_entries me3 ON e.id = me3.entity_id AND me3.key = "vlm_structured"
        WHERE
            e.file_type_group = 'image'
        """
        
        params = []
        
        if start_date:
            query += " AND datetime(e.created_at, 'localtime') >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND datetime(e.created_at, 'localtime') <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                
                # Process the dataframe to add enhanced tasks and categories
                if not df.empty and 'vlm_description' in df.columns:
                    df['enhanced_task'] = df.apply(
                        lambda row: get_enhanced_task(
                            row["active_window"], 
                            row["ocr_result"], 
                            row['vlm_description']
                        ), 
                        axis=1
                    )
                    
                    df['enhanced_category'] = df.apply(
                        lambda row: get_enhanced_category(
                            row["active_window"],
                            row["ocr_result"],
                            row['vlm_description']
                        ),
                        axis=1
                    )
                
                return df
        except pd.io.sql.DatabaseError as e:
            print(f"Error fetching tasks with VLM: {e}")
            # Fall back to regular fetch
            return self.fetch_tasks(start_date, end_date, limit, offset)
    
    def get_vlm_coverage_stats(self) -> dict:
        """
        Get statistics about VLM coverage in the database.
        
        Returns:
            Dictionary with VLM coverage statistics
        """
        query = """
        SELECT 
            COUNT(DISTINCT e.id) as total_screenshots,
            COUNT(DISTINCT CASE WHEN me_ocr.value IS NOT NULL THEN e.id END) as with_ocr,
            COUNT(DISTINCT CASE WHEN me_vlm.value IS NOT NULL THEN e.id END) as with_vlm,
            COUNT(DISTINCT CASE WHEN me_ocr.value IS NULL AND me_vlm.value IS NOT NULL THEN e.id END) as vlm_only
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr.key = "ocr_result"
        LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm.key = "vlm_structured"
        WHERE e.file_type_group = 'image'
        AND date(e.created_at, 'localtime') >= date('now', '-7 days')
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                
                if result:
                    total = result['total_screenshots']
                    return {
                        'total_screenshots': total,
                        'with_ocr': result['with_ocr'],
                        'with_vlm': result['with_vlm'],
                        'vlm_only': result['vlm_only'],
                        'ocr_coverage_pct': (result['with_ocr'] / total * 100) if total > 0 else 0,
                        'vlm_coverage_pct': (result['with_vlm'] / total * 100) if total > 0 else 0,
                        'vlm_exclusive_pct': (result['vlm_only'] / total * 100) if total > 0 else 0
                    }
        except Exception as e:
            print(f"Error getting VLM coverage stats: {e}")
        
        return {
            'total_screenshots': 0,
            'with_ocr': 0,
            'with_vlm': 0,
            'vlm_only': 0,
            'ocr_coverage_pct': 0,
            'vlm_coverage_pct': 0,
            'vlm_exclusive_pct': 0
        }


def display_vlm_enhanced_tasks():
    """Example function showing how to display VLM-enhanced tasks."""
    db = VLMEnabledDatabaseManager()
    
    # Get VLM coverage statistics
    stats = db.get_vlm_coverage_stats()
    print("VLM Coverage Statistics (Last 7 Days)")
    print("-" * 40)
    print(f"Total Screenshots: {stats['total_screenshots']}")
    print(f"With OCR: {stats['with_ocr']} ({stats['ocr_coverage_pct']:.1f}%)")
    print(f"With VLM: {stats['with_vlm']} ({stats['vlm_coverage_pct']:.1f}%)")
    print(f"VLM Only (no OCR): {stats['vlm_only']} ({stats['vlm_exclusive_pct']:.1f}%)")
    print()
    
    # Fetch recent tasks with VLM data
    tasks_df = db.fetch_tasks_with_vlm(limit=10)
    
    if not tasks_df.empty:
        print("Recent Tasks with VLM Enhancement")
        print("-" * 80)
        
        for _, row in tasks_df.iterrows():
            print(f"\nTime: {row['created_at']}")
            
            # Show original vs enhanced task
            from autotasktracker.core.task_extractor import get_task_extractor
            extractor = get_task_extractor()
            original_task = extractor.extract_task(row["active_window"], row["ocr_result"])
            
            print(f"Original Task: {original_task}")
            
            if 'enhanced_task' in row:
                print(f"Enhanced Task: {row['enhanced_task']}")
            
            if 'enhanced_category' in row:
                print(f"Category: {row['enhanced_category']}")
            
            # Show VLM description if available
            if row.get('vlm_description'):
                print(f"VLM Description: {row['vlm_description'][:100]}...")
            
            print("-" * 80)


def compare_task_quality():
    """Compare task extraction quality with and without VLM."""
    db = VLMEnabledDatabaseManager()
    
    # Get samples where we have both OCR and VLM
    query = """
    SELECT 
        e.filepath,
        me_window.value as active_window,
        me_ocr.value as ocr_text,
        me_vlm.value as vlm_description
    FROM entities e
    JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr.key = "ocr_result"
    JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm.key = "vlm_structured"
    LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id AND me_window.key = "active_window"
    WHERE e.file_type_group = 'image'
    ORDER BY e.created_at DESC
    LIMIT 20
    """
    
    try:
        with db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                print("Task Extraction Quality Comparison")
                print("=" * 100)
                
                generic_count_without_vlm = 0
                generic_count_with_vlm = 0
                
                for _, row in df.iterrows():
                    # Extract without VLM
                    from autotasktracker.core.task_extractor import get_task_extractor
                    extractor = get_task_extractor()
                    task_without_vlm = extractor.extract_task(row["active_window"], row["ocr_result"])
                    
                    # Extract with VLM
                    task_with_vlm = get_enhanced_task(
                        row["active_window"], 
                        row["ocr_result"],
                        row['vlm_description']
                    )
                    
                    # Count generic tasks
                    if task_without_vlm in ['Activity Captured', 'Web browsing', 'Other']:
                        generic_count_without_vlm += 1
                    
                    if task_with_vlm in ['Activity Captured', 'Web browsing', 'Other']:
                        generic_count_with_vlm += 1
                    
                    # Show improvement
                    if task_without_vlm != task_with_vlm:
                        print(f"\nImproved Task Detection:")
                        print(f"  Before (OCR only): {task_without_vlm}")
                        print(f"  After (with VLM):  {task_with_vlm}")
                        print(f"  VLM insight: {row['vlm_description'][:80]}...")
                
                print(f"\n\nSummary:")
                print(f"Generic tasks without VLM: {generic_count_without_vlm}/{len(df)} ({generic_count_without_vlm/len(df)*100:.1f}%)")
                print(f"Generic tasks with VLM: {generic_count_with_vlm}/{len(df)} ({generic_count_with_vlm/len(df)*100:.1f}%)")
                
                improvement = generic_count_without_vlm - generic_count_with_vlm
                if improvement > 0:
                    print(f"Improvement: {improvement} fewer generic tasks ({improvement/len(df)*100:.1f}% better)")
            
    except Exception as e:
        print(f"Error comparing task quality: {e}")


if __name__ == "__main__":
    # Run examples
    print("AutoTaskTracker VLM Integration Examples\n")
    
    # Show VLM coverage
    display_vlm_enhanced_tasks()
    
    print("\n" + "="*100 + "\n")
    
    # Compare task quality
    compare_task_quality()