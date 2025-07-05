#!/usr/bin/env python3
"""
Process screenshots with OCR to generate text data.
This script runs OCR on unprocessed screenshots and stores the results.
"""
import sys
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def process_screenshots_with_ocr(limit=100):
    """Process screenshots using OCR and store results."""
    from autotasktracker.core import DatabaseManager
    
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Find unprocessed screenshots
        cursor.execute("""
            SELECT e.id, e.filepath 
            FROM entities e
            WHERE e.file_type_group = 'image'
            AND NOT EXISTS (
                SELECT 1 FROM metadata_entries 
                WHERE entity_id = e.id 
                AND key IN ("ocr_result", "ocr_result")
            )
            LIMIT ?
        """, (limit,))
        
        unprocessed = cursor.fetchall()
        logger.info(f"Found {len(unprocessed)} unprocessed screenshots")
        
        if not unprocessed:
            logger.info("No unprocessed screenshots found")
            return
        
        # Try different OCR methods
        ocr_available = False
        ocr_method = None
        
        # Try ocrmac Python module first (macOS)
        try:
            import ocrmac
            ocr_available = True
            ocr_method = 'ocrmac_python'
            logger.info("Using ocrmac Python module for OCR")
        except ImportError:
            pass
        
        # Try pytesseract as fallback
        if not ocr_available:
            try:
                import pytesseract
                from PIL import Image
                ocr_available = True
                ocr_method = 'pytesseract'
                logger.info("Using pytesseract for OCR")
            except ImportError:
                pass
        
        if not ocr_available:
            logger.error("No OCR capability available. Install ocrmac or pytesseract.")
            return
        
        processed_count = 0
        for entity_id, filepath in unprocessed:
            if not os.path.exists(filepath):
                logger.warning(f"File not found: {filepath}")
                continue
            
            try:
                ocr_text = None
                
                if ocr_method == 'ocrmac_python':
                    # Use ocrmac Python module
                    import ocrmac.ocrmac
                    ocr_obj = ocrmac.ocrmac.OCR(filepath)
                    ocr_obj.recognize()
                    # Extract text from results
                    text_parts = []
                    if hasattr(ocr_obj, 'res') and ocr_obj.res:
                        for item in ocr_obj.res:
                            if isinstance(item, tuple) and len(item) >= 1:
                                # First element is the text
                                text_parts.append(str(item[0]))
                    ocr_text = ' '.join(text_parts) if text_parts else None
                
                elif ocr_method == 'pytesseract':
                    # Use pytesseract
                    from PIL import Image
                    img = Image.open(filepath)
                    ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text:
                    # Store OCR result
                    cursor.execute("""
                        INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, source, data_type, created_at, updated_at)
                        VALUES (?, "ocr_result", ?, 'plugin', 'manual_ocr', 'text', datetime('now'), datetime('now'))
                    """, (entity_id, ocr_text))
                    
                    # Also mark as processed by OCR plugin
                    cursor.execute("""
                        INSERT OR REPLACE INTO entity_plugin_status 
                        (entity_id, plugin_id, processed_at)
                        VALUES (?, 2, datetime('now'))
                    """, (entity_id,))
                    
                    conn.commit()
                    processed_count += 1
                    
                    # Show preview
                    preview = ' '.join(ocr_text.split()[:10]) + "..." if ocr_text else "No text"
                    logger.info(f"Processed {filepath}: {preview}")
                    
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                continue
        
        logger.info(f"Successfully processed {processed_count} screenshots with OCR")
        
        # Show updated stats
        cursor.execute("""
            SELECT COUNT(DISTINCT entity_id) 
            FROM metadata_entries 
            WHERE key = "ocr_result"
        """)
        total_with_ocr = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM entities WHERE file_type_group = 'image'")
        total_screenshots = cursor.fetchone()[0]
        
        percentage = (total_with_ocr / total_screenshots * 100) if total_screenshots > 0 else 0
        logger.info(f"OCR coverage: {total_with_ocr}/{total_screenshots} ({percentage:.1f}%)")
        
        # Connection closed automatically by with statement


def run_task_extraction():
    """Run task extraction on screenshots with OCR text."""
    from autotasktracker.core import DatabaseManager
    from autotasktracker.core.task_extractor import get_task_extractor
    from autotasktracker.core import ActivityCategorizer
    
    db = DatabaseManager()
    task_extractor = get_task_extractor()
    categorizer = ActivityCategorizer()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Find entities with OCR but no tasks
        cursor.execute("""
            SELECT DISTINCT e.id, me1.value as window_title, me2.value as ocr_text
            FROM entities e
            JOIN metadata_entries me1 ON e.id = me1.entity_id AND me1.key = "active_window"
            LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "ocr_result"
            LEFT JOIN metadata_entries me3 ON e.id = me3.entity_id AND me3.key = "tasks"
            WHERE me3.id IS NULL
            AND e.file_type_group = 'image'
            LIMIT 100
        """)
        
        unprocessed = cursor.fetchall()
        logger.info(f"Found {len(unprocessed)} screenshots without task extraction")
        
        processed = 0
        for entity_id, window_title, ocr_text in unprocessed:
            if not window_title:
                continue
            
            # Extract task from window title and OCR text
            task = task_extractor.extract_task(window_title)
            if not task and ocr_text:
                # Try to extract from OCR text
                lines = ocr_text.split('\n')[:5]  # First 5 lines
                for line in lines:
                    if len(line) > 10:  # Meaningful line
                        task = line.strip()
                        break
            
            if not task:
                task = "Unknown Activity"
            
            # Get category
            category = categorizer.categorize(window_title)
            
            # Store results
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, "tasks", ?, 'task_processor', 'text', datetime('now'), datetime('now'))
            """, (entity_id, task))
            
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, "category", ?, 'task_processor', 'text', datetime('now'), datetime('now'))
            """, (entity_id, category))
            
            processed += 1
        
        conn.commit()
        logger.info(f"Processed {processed} screenshots with task extraction")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process screenshots with OCR")
    parser.add_argument('--limit', type=int, default=50, help='Number of screenshots to process')
    parser.add_argument('--skip-ocr', action='store_true', help='Skip OCR processing')
    parser.add_argument('--skip-tasks', action='store_true', help='Skip task extraction')
    
    args = parser.parse_args()
    
    if not args.skip_ocr:
        logger.info("=== Running OCR Processing ===")
        process_screenshots_with_ocr(limit=args.limit)
    
    if not args.skip_tasks:
        logger.info("\n=== Running Task Extraction ===")
        run_task_extraction()
    
    logger.info("\n✅ Processing complete!")


if __name__ == "__main__":
    main()