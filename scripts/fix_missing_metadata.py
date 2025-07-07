#!/usr/bin/env python
"""Fix missing metadata by processing screenshots with OCR and window title extraction."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime, timedelta
from ocrmac import ocrmac
import re
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_window_info_from_ocr(ocr_text):
    """Extract window title from OCR text."""
    if not ocr_text:
        return None
        
    # Common patterns for window titles in macOS menu bar
    lines = ocr_text.split('\n')
    
    # Look for app names in first few lines (menu bar area)
    for line in lines[:5]:
        # Common app patterns
        if any(app in line for app in ['Chrome', 'Terminal', 'Code', 'Safari', 'Finder', 'VS Code', 'Visual Studio']):
            return line.strip()
            
        # Tab titles often have — or | separators
        if '—' in line or '|' in line:
            return line.strip()
    
    # Look for terminal prompts
    for line in lines:
        if '~' in line and ('$' in line or '%' in line):
            return "Terminal"
        if 'git' in line.lower() or 'python' in line.lower():
            return "Terminal - Development"
            
    return None

def categorize_window(window_title, ocr_text):
    """Categorize based on window title and content."""
    if not window_title:
        # Try to infer from OCR content
        text_lower = (ocr_text or '').lower()
        if any(keyword in text_lower for keyword in ['def ', 'class ', 'import ', 'function', 'const ', 'let ']):
            return 'Development'
        elif any(keyword in text_lower for keyword in ['email', 'slack', 'teams', 'zoom']):
            return 'Communication'
        elif any(keyword in text_lower for keyword in ['docs', 'sheets', 'word', 'excel']):
            return 'Productivity'
        return 'Other'
        
    window_lower = window_title.lower()
    
    if any(dev in window_lower for dev in ['code', 'terminal', 'pycharm', 'intellij', 'sublime']):
        return 'Development'
    elif any(browser in window_lower for browser in ['chrome', 'safari', 'firefox', 'edge']):
        return 'Web Browsing'
    elif any(comm in window_lower for comm in ['slack', 'teams', 'zoom', 'mail']):
        return 'Communication'
    elif any(prod in window_lower for prod in ['docs', 'sheets', 'word', 'excel', 'notion']):
        return 'Productivity'
    else:
        return 'Other'

def process_entity(conn, entity_id, filepath):
    """Process a single entity to extract metadata."""
    try:
        # Run OCR
        logger.info(f"Processing entity {entity_id}: {os.path.basename(filepath)}")
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}")
            return False
            
        # Run macOS OCR
        ocr_instance = ocrmac.OCR(filepath)
        ocr_results = ocr_instance.recognize()
        
        # Extract text
        ocr_text = ""
        if ocr_results:
            # ocrmac returns list of results 
            if hasattr(ocr_results, '__iter__'):
                ocr_text = '\n'.join([str(result) for result in ocr_results])
            else:
                ocr_text = str(ocr_results)
        
        # Extract window title from OCR
        window_title = extract_window_info_from_ocr(ocr_text)
        
        # If no window title found, try to infer from filename
        if not window_title:
            filename = os.path.basename(filepath)
            if 'studio_display' in filename:
                window_title = "Studio Display Screen"
            elif 'color_lcd' in filename:
                window_title = "MacBook Screen"
            else:
                window_title = "Unknown Activity"
        
        # Categorize
        category = categorize_window(window_title, ocr_text)
        
        # Insert metadata
        cursor = conn.cursor()
        
        # Check if metadata already exists
        cursor.execute("""
            SELECT COUNT(*) FROM metadata_entries 
            WHERE entity_id = %s AND key = 'active_window'
        """, (entity_id,))
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            logger.info(f"  Metadata already exists for entity {entity_id}, skipping")
            return True
            
        # Get next ID for metadata_entries
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM metadata_entries")
        next_id = cursor.fetchone()[0]
        
        # Insert OCR text
        if ocr_text:
            cursor.execute("""
                INSERT INTO metadata_entries (id, entity_id, key, value)
                VALUES (%s, %s, 'ocr_text', %s)
            """, (next_id, entity_id, ocr_text[:10000]))  # Limit text length
            next_id += 1
        
        # Insert window title
        cursor.execute("""
            INSERT INTO metadata_entries (id, entity_id, key, value)
            VALUES (%s, %s, 'active_window', %s)
        """, (next_id, entity_id, window_title))
        next_id += 1
        
        # Insert category
        cursor.execute("""
            INSERT INTO metadata_entries (id, entity_id, key, value)
            VALUES (%s, %s, 'category', %s)
        """, (next_id, entity_id, category))
        
        conn.commit()
        logger.info(f"  Window: {window_title}")
        logger.info(f"  Category: {category}")
        logger.info(f"  OCR text length: {len(ocr_text)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing entity {entity_id}: {e}")
        conn.rollback()
        return False

def main():
    """Process entities missing metadata."""
    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database="autotasktracker",
        user="postgres",
        password="mysecretpassword"
    )
    
    cursor = conn.cursor()
    
    # Find ALL entities without metadata (not just last 2 hours)
    cursor.execute("""
        SELECT e.id, e.filepath
        FROM entities e
        WHERE NOT EXISTS (
            SELECT 1 FROM metadata_entries m
            WHERE m.entity_id = e.id AND m.key = 'active_window'
        )
        AND e.filepath IS NOT NULL
        AND e.filepath LIKE '%.webp'
        ORDER BY e.id DESC
        LIMIT 500
    """)
    
    entities = cursor.fetchall()
    print(f"\nFound {len(entities)} entities without metadata\n")
    
    success_count = 0
    for entity_id, filepath in entities:
        if process_entity(conn, entity_id, filepath):
            success_count += 1
    
    print(f"\nProcessed {success_count}/{len(entities)} entities successfully")
    
    # Show sample of results
    cursor.execute("""
        SELECT COUNT(DISTINCT e.id) as total,
               COUNT(DISTINCT CASE WHEN m.key = 'active_window' THEN e.id END) as with_window,
               COUNT(DISTINCT CASE WHEN m.key = 'ocr_text' THEN e.id END) as with_ocr
        FROM entities e
        LEFT JOIN metadata_entries m ON e.id = m.entity_id
        WHERE COALESCE(e.created_at, e.file_created_at) >= NOW() - INTERVAL '2 hours'
    """)
    
    stats = cursor.fetchone()
    print(f"\nMetadata stats (last 2 hours):")
    print(f"  Total entities: {stats[0]}")
    print(f"  With window title: {stats[1]}")
    print(f"  With OCR text: {stats[2]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()